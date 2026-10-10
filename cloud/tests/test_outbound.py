import multiprocessing
import tempfile
import threading
import time
import unittest
from datetime import datetime, timezone
from contextlib import nullcontext
from email.utils import format_datetime
from unittest.mock import Mock, patch

import requests

from cloud.outbound import SchoolGate, SchoolSession, ServiceError
from cloud.store import Store
from cloud.service import SchoolService, CloudGrades, BEIJING
from cloud.worker import Worker, due_slots, stagger_seconds
from cloud.tests import test_cloud as fixtures


def hold_lane(directory, ready, release):
    store = Store(directory, b"K" * 32)
    with store.lock("school-http"):
        ready.set()
        release.wait(5)


class Clock:
    def __init__(self):
        self.now = 10000.0

    def __call__(self):
        return self.now

    def sleep(self, seconds):
        self.now += seconds


class OutboundTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = Store(self.temp.name, b"K" * 32)
        self.clock = Clock()
        self.gate = SchoolGate(self.store, clock=self.clock, sleep=self.clock.sleep)

    def response(self, status=200, retry=None):
        return Mock(status_code=status, headers={"Retry-After": retry} if retry else {})

    def test_spacing_shared_by_separate_instances(self):
        starts = []
        def request():
            starts.append(self.clock())
            return self.response()
        self.gate.perform(request)
        other = SchoolGate(Store(self.temp.name, b"K" * 32), self.clock, self.clock.sleep)
        other.perform(request)
        self.gate.perform(request)
        self.assertEqual(starts, [10000, 10003, 10006])

    def test_spacing_wait_uses_remaining_queue_budget(self):
        with self.store.db() as db:
            db.execute('UPDATE school_outbound SET next_request=? WHERE id=1', (self.clock() + 2,))
        request = Mock()
        with patch.object(self.store, 'lock', return_value=nullcontext()), \
                patch('cloud.outbound.time.monotonic', side_effect=[100, 114]):
            with self.assertRaises(ServiceError):
                self.gate.perform(request)
        request.assert_not_called()

    def test_cross_process_queue_timeout(self):
        context = multiprocessing.get_context("spawn")
        ready, release = context.Event(), context.Event()
        child = context.Process(target=hold_lane, args=(self.temp.name, ready, release))
        child.start()
        try:
            self.assertTrue(ready.wait(5))
            self.gate.QUEUE_TIMEOUT = 0.1
            request = Mock()
            with self.assertRaises(ServiceError) as error:
                self.gate.perform(request)
            self.assertEqual(error.exception.status, "deferred")
            request.assert_not_called()
        finally:
            release.set()
            child.join(5)
            if child.is_alive():
                child.terminate()
                child.join()

    def test_concurrent_requests_do_not_overlap(self):
        other = SchoolGate(Store(self.temp.name, b"K" * 32))
        self.gate.INTERVAL = other.INTERVAL = 0
        entered, release, second = threading.Event(), threading.Event(), threading.Event()
        def first():
            entered.set()
            release.wait(3)
            return self.response()
        a = threading.Thread(target=lambda: self.gate.perform(first))
        b = threading.Thread(target=lambda: other.perform(lambda: (second.set(), self.response())[1]))
        a.start()
        self.assertTrue(entered.wait(1))
        b.start()
        self.assertFalse(second.wait(0.1))
        release.set()
        a.join(3)
        b.join(3)
        self.assertTrue(second.is_set())

    def test_retry_after_and_restart_cooldown(self):
        with self.assertRaises(ServiceError) as error:
            self.gate.perform(lambda: self.response(429, "1800"))
        self.assertEqual(error.exception.retry_after, 1800)
        other = SchoolGate(Store(self.temp.name, b"K" * 32), self.clock, self.clock.sleep)
        request = Mock(return_value=self.response())
        with self.assertRaises(ServiceError):
            other.perform(request)
        request.assert_not_called()
        self.clock.now += 1801
        other.perform(request)
        self.assertEqual(request.call_count, 1)
        date = format_datetime(datetime.fromtimestamp(self.clock() + 2400, timezone.utc), usegmt=True)
        self.assertEqual(self.gate.retry_seconds(date), 2400)
        self.assertEqual(self.gate.retry_seconds("invalid"), 900)
        self.assertEqual(self.gate.retry_seconds("-1"), 900)

    def test_forbidden_and_consecutive_failures(self):
        for _ in range(3):
            with self.assertRaises(ServiceError):
                self.gate.perform(Mock(side_effect=requests.ReadTimeout()))
        request = Mock(return_value=self.response())
        with self.assertRaises(ServiceError):
            self.gate.perform(request)
        request.assert_not_called()
        self.clock.now += 901
        self.gate.perform(request)
        with self.store.db() as db:
            self.assertEqual(db.execute("SELECT failures FROM school_outbound").fetchone()[0], 0)
        with self.assertRaises(ServiceError) as error:
            self.gate.perform(lambda: self.response(403))
        self.assertEqual(error.exception.retry_after, 3600)

    @patch("requests.Session.request")
    def test_no_retry_or_redirect_after_transport_error(self, request):
        request.side_effect = requests.ConnectTimeout()
        session = SchoolSession(self.gate)
        for _ in range(2):
            with self.assertRaises(ServiceError):
                session.post("https://school.test/api")
        self.assertEqual(request.call_count, 1)
        self.assertFalse(request.call_args.kwargs["allow_redirects"])
        self.assertEqual(request.call_args.kwargs["timeout"], (6, 12))
        with self.assertRaises(ServiceError):
            session.check()

    @patch("requests.Session.request", side_effect=requests.ReadTimeout())
    def test_failed_token_check_does_not_send_fresh_login(self, request):
        state = {"username": "20260001", "password": "FAKE_PASSWORD_ONLY",
                 "jw_cached_username": "20260001", "jw_cached_token": "FAKE_TOKEN_ONLY"}
        service = SchoolService(self.store)
        service.gate = self.gate
        with self.assertRaises(ServiceError):
            service.login(state)
        self.assertEqual(request.call_count, 1)

    def test_unexpected_html_activates_failure_protection(self):
        response = self.response()
        response.json.side_effect = ValueError("not json")
        with self.assertRaises(ServiceError):
            self.gate.perform(lambda: response)
        with self.store.db() as db:
            self.assertEqual(db.execute("SELECT failures FROM school_outbound").fetchone()[0], 1)

    def test_additive_schema_migration_preserves_old_jobs(self):
        with self.store.db() as db:
            db.execute("DROP TABLE jobs")
            db.execute("CREATE TABLE jobs(account TEXT, slot TEXT, kind TEXT, status TEXT, message TEXT, created REAL, PRIMARY KEY(account,slot,kind))")
            db.execute("INSERT INTO jobs VALUES('fake-account','fake-slot','morning','done','sent',1000)")
        Store(self.temp.name, b"K" * 32)
        with self.store.db() as db:
            row = db.execute("SELECT status,message,retry_at FROM jobs").fetchone()
            self.assertEqual(tuple(row), ('done', 'sent', 0))


class SnapshotTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.now = datetime(2026, 10, 12, 7, tzinfo=BEIJING).timestamp()
        self.service = SchoolService(Store(self.temp.name, b"K" * 32), clock=lambda: self.now)
        self.state = {"username": "20260001", "course_cache": {
            "username": "20260001", "semester_id": "2026-2027-1", "fetched_at": self.now - 3600,
            "teaching": {"schedule_status": "active", "semester_id": "2026-2027-1",
                         "week_one_monday": "2026-08-31", "available_weeks": list(range(2, 20))},
            "courses": [{"courseName": "合成测试课程", "xqmc": "星期一", "classWeekDetails": "7",
                         "startNode": 1, "classTime": "1-2", "location": "测试教室", "teacherName": "测试教师"}],
        }}

    def test_identity_expiry_and_semester_mismatch_rejected(self):
        self.assertIsNotNone(self.service.valid_cache(self.state))
        cache = self.state["course_cache"]
        cache["username"] = "20260002"
        self.assertIsNone(self.service.valid_cache(self.state))
        cache["username"] = self.state["username"]
        cache["fetched_at"] = self.now - 18 * 3600
        self.assertIsNone(self.service.valid_cache(self.state))
        cache["fetched_at"] = self.now + 1
        self.assertIsNone(self.service.valid_cache(self.state))
        cache["fetched_at"] = self.now
        cache["teaching"]["semester_id"] = "2026-2027-2"
        self.assertIsNone(self.service.valid_cache(self.state))

    def test_send_and_reuse_never_contact_school(self):
        self.service.login = Mock(side_effect=AssertionError("Must use snapshot"))
        self.assertIn("复用", self.service.prepare(self.state))
        send = Mock()
        self.service.run({"state": self.state}, "morning", datetime(2026, 10, 12).date(), send)
        send.assert_called_once()
        self.assertIn("数据时间", send.call_args.args[0])
        self.state["course_cache"]["fetched_at"] = 0
        with self.assertRaises(ServiceError) as error:
            self.service.run({"state": self.state}, "morning", datetime(2026, 10, 12).date(), send)
        self.assertEqual(error.exception.status, "skipped")
        self.assertEqual(send.call_count, 1)

    @patch("cloud.service.CourseScraper")
    def test_prefetch_records_identity_and_time_without_sending(self, scraper_class):
        scraper = scraper_class.return_value
        scraper.fetch_semester_info.return_value = {'currentSemester': '2026-2027-1'}
        scraper.fetch_teaching_state.return_value = self.state['course_cache']['teaching']
        scraper.fetch_course_data.return_value = self.state['course_cache']['courses']
        self.state.pop('course_cache')
        login = Mock()
        self.service.login = Mock(return_value=login)
        send = Mock()
        self.service.run({'state': self.state}, 'prepare_morning', datetime(2026, 10, 12).date(), send)
        send.assert_not_called()
        login.session.close.assert_called_once()
        cache = self.state['course_cache']
        self.assertEqual(cache['username'], self.state['username'])
        self.assertEqual(cache['fetched_at'], self.now)
        self.assertEqual(cache['semester_id'], '2026-2027-1')

    def test_failed_grade_read_cannot_modify_baseline_or_send(self):
        self.state['grade_cache'] = {'test_marker': 'unchanged'}
        login = Mock()
        login.session.check.side_effect = ServiceError('保护暂停', 'deferred', 900)
        send = Mock()
        grades = CloudGrades(self.state, login, send)
        with patch.object(grades, '_create_scraper', return_value=Mock()), \
                patch.object(grades, '_resolve_selected_semester', return_value={'semester_id': '2026-2027-1', 'semester_name': '测试学期'}):
            with self.assertRaises(ServiceError):
                grades.check_changes()
        self.assertEqual(self.state['grade_cache'], {'test_marker': 'unchanged'})
        send.assert_not_called()


class SchedulingTest(unittest.TestCase):
    setUp = fixtures.CloudTest.setUp
    call = fixtures.CloudTest.call
    login = fixtures.CloudTest.login
    enable = fixtures.CloudTest.enable

    def test_busy_login_returns_retry_hint_without_sending_code(self):
        self.school.verify = Mock(side_effect=ServiceError("排队繁忙", "deferred", 60))
        result = self.call("POST", "/auth/request", {"username": "20260001", "password": "FAKE_PASSWORD_ONLY",
                           "uid": "UID_FAKEUSER00001", "consent": True})
        self.assertEqual(result.status_code, 503)
        self.assertEqual(result.headers["Retry-After"], "60")
        self.assertFalse(self.sender.messages)

    def test_three_grade_batches_and_preparation_windows(self):
        grades = []
        for hour in range(24):
            slots = due_slots(datetime(2026, 10, 12, hour, 30, tzinfo=BEIJING).timestamp())
            grades.extend(item for item in slots if item[0] == "grades")
        self.assertEqual(len(grades), 3)
        self.assertEqual([datetime.fromtimestamp(item[2], BEIJING).hour for item in grades], [8, 13, 21])
        slots = due_slots(datetime(2026, 10, 12, 19, 10, tzinfo=BEIJING).timestamp())
        self.assertEqual(slots[0][0], "prepare_evening")
        self.assertEqual(str(slots[0][3]), "2026-10-13")

    def test_deferred_read_retries_only_in_window_and_never_duplicates(self):
        account = self.login()
        self.enable(grades=True)
        start = datetime(2026, 10, 12, 8, 30, tzinfo=BEIJING).timestamp()
        self.now = start + stagger_seconds(account["id"]) + 1
        self.school.run = Mock(side_effect=ServiceError("保护暂停", "deferred", 120))
        worker = Worker(self.store, self.school, self.sender, lambda: self.now)
        worker.tick()
        worker.tick()
        self.assertEqual(self.school.run.call_count, 1)
        self.school.run.side_effect = None
        self.school.run.return_value = "基线已建立"
        self.now += 121
        worker.tick()
        worker.tick()
        self.assertEqual(self.school.run.call_count, 2)
        self.now = start + 2700
        worker.tick()
        self.assertEqual(self.school.run.call_count, 2)

    def test_expired_deferred_job_is_closed_without_requests(self):
        account = self.login()
        self.enable(grades=True)
        start = datetime(2026, 10, 12, 8, 30, tzinfo=BEIJING).timestamp()
        self.now = start + 1000
        self.school.run = Mock(side_effect=ServiceError("保护暂停", "deferred", 3600))
        worker = Worker(self.store, self.school, self.sender, lambda: self.now)
        worker.tick()
        self.now = start + 2700
        worker.tick()
        self.assertEqual(self.school.run.call_count, 1)
        self.assertEqual(self.call("GET", "/account").json["jobs"][0]["status"], "skipped")

    def test_stagger_does_not_begin_early(self):
        account = self.login()
        self.enable(grades=True)
        start = datetime(2026, 10, 12, 13, 30, tzinfo=BEIJING).timestamp()
        worker = Worker(self.store, self.school, self.sender, lambda: self.now)
        self.now = start + stagger_seconds(account["id"]) - 1
        worker.tick()
        self.assertFalse(self.school.calls)
        self.now += 1
        worker.tick()
        self.assertEqual(len(self.school.calls), 1)


if __name__ == "__main__":
    unittest.main()
