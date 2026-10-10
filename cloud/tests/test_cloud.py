import base64
import json
import re
import tempfile
import threading
import time
import unittest
from datetime import datetime
from unittest.mock import Mock, patch

from cloud.app import PREFIX, create_app
from cloud.service import BEIJING, CloudGrades, SchoolService, ServiceError, WxSender
from cloud.store import Store
from cloud.worker import Worker, due_slots

ORIGIN = "https://classpush.test"


class FakeSchool:
    def __init__(self):
        self.calls = []

    def verify(self, state):
        if state["password"] != "FAKE_PASSWORD_ONLY":
            raise ServiceError("教务账号或密码已失效，请重新登录", "needs_auth")
        state["jw_cached_token"] = "FAKE_SCHOOL_TOKEN_ONLY_" + state["username"]

    def run(self, account, kind, target, send):
        self.calls.append((account["id"], kind, target))
        account["state"]["cache"] = account["state"]["username"]
        send("测试课表", "测试")
        return "已提交"


class FakeSender:
    def __init__(self):
        self.messages = []
        self.error = None

    def send(self, uid, content, title, content_type=2):
        if self.error:
            raise self.error
        self.messages.append((uid, content, title))


class CloudTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = Store(self.temp.name, b"K" * 32)
        self.school, self.sender = FakeSchool(), FakeSender()
        self.now = datetime(2026, 10, 12, 6, 50, tzinfo=BEIJING).timestamp()
        self.app = create_app(self.store, self.school, self.sender, clock=lambda: self.now, origin=ORIGIN)
        self.client = self.app.test_client()

    def call(self, method, path, body=None, client=None):
        return (client or self.client).open(PREFIX + path, method=method, base_url=ORIGIN,
                                            json=body, headers={"Origin": ORIGIN})

    def login(self, username="20260001", uid="UID_FAKEUSER00001", client=None):
        response = self.call("POST", "/auth/request", {"username": username,
            "password": "FAKE_PASSWORD_ONLY", "uid": uid, "consent": True}, client)
        self.assertEqual(response.status_code, 200)
        code = re.search(r"：([0-9]{6})", self.sender.messages[-1][1])[1]
        result = self.call("POST", "/auth/confirm", {"challenge": response.json["challenge"], "code": code}, client)
        self.assertEqual(result.status_code, 200)
        return self.store.account(subject=self.store.digest("student:" + username))

    def enable(self, **changes):
        return self.call("PATCH", "/account", {"morning": True, "evening": True,
                                               "grades": False, "paused": False, **changes})

    def test_auth_consent_origin_and_password(self):
        self.assertEqual(self.call("GET", "/account").status_code, 401)
        bad = self.client.post(PREFIX + "/auth/request", base_url=ORIGIN, json={})
        self.assertEqual(bad.status_code, 403)
        self.assertEqual(self.call("POST", "/auth/request", {}).status_code, 400)
        self.assertEqual(self.call("POST", "/auth/request", {"username": "20260001", "password": "BAD",
                         "uid": "UID_FAKEUSER00001", "consent": True}).status_code, 502)
        self.assertFalse(self.sender.messages)

    def test_code_attempts_expiry_and_reuse(self):
        response = self.call("POST", "/auth/request", {"username": "20260001", "password": "FAKE_PASSWORD_ONLY",
                            "uid": "UID_FAKEUSER00001", "consent": True})
        challenge = response.json["challenge"]
        code = re.search(r"：([0-9]{6})", self.sender.messages[-1][1])[1]
        wrong = "000001" if code != "000001" else "000002"
        for _ in range(5):
            self.assertEqual(self.call("POST", "/auth/confirm", {"challenge": challenge, "code": wrong}).status_code, 400)
        self.assertEqual(self.call("POST", "/auth/confirm", {"challenge": challenge, "code": code}).status_code, 400)
        self.now += 601
        self.login()
        self.assertEqual(self.call("POST", "/auth/confirm", {"challenge": challenge, "code": code}).status_code, 400)

    def test_expired_challenge(self):
        response = self.call("POST", "/auth/request", {"username": "20260001", "password": "FAKE_PASSWORD_ONLY",
                            "uid": "UID_FAKEUSER00001", "consent": True})
        code = re.search(r"：([0-9]{6})", self.sender.messages[-1][1])[1]
        self.now += 301
        self.assertEqual(self.call("POST", "/auth/confirm", {"challenge": response.json["challenge"], "code": code}).status_code, 400)

    def test_isolation_encryption_and_no_rebinding(self):
        a = self.login()
        other = self.app.test_client()
        b = self.login("20260002", "UID_FAKEUSER00002", other)
        self.enable()
        self.assertFalse(self.call("GET", "/account", client=other).json["morning"])
        self.assertNotEqual(a["state"]["jw_cached_token"], b["state"]["jw_cached_token"])
        self.assertNotIn("password", self.call("GET", "/account").json)
        self.login(uid="UID_ATTACKER00001")
        self.assertEqual(self.sender.messages[-1][0], "UID_FAKEUSER00001")
        with self.store.db() as db:
            rows = list(db.execute("SELECT state FROM accounts")) + list(db.execute("SELECT state FROM challenges"))
            for row in rows:
                self.assertNotIn("FAKE_PASSWORD", row["state"])
                self.assertNotIn("FAKE_SCHOOL_TOKEN", row["state"])
        with self.assertRaises(ValueError):
            self.store.open(self.store.seal({"x": 1}, a["id"]), b["id"])

    def test_logout_delete_and_invalid_payload(self):
        account = self.login()
        self.assertEqual(self.call("PATCH", "/account", {"paused": "false"}).status_code, 400)
        self.assertEqual(self.call("DELETE", "/account", {}).status_code, 400)
        self.assertEqual(self.call("DELETE", "/account", {"confirm": "DELETE"}).status_code, 200)
        self.assertEqual(self.call("GET", "/account").status_code, 401)
        self.assertIsNone(self.store.account(account["id"]))
        self.login()
        self.call("POST", "/auth/logout", {})
        self.assertEqual(self.call("GET", "/account").status_code, 401)

    def test_rate_limits_cookie_and_password(self):
        self.login()
        self.assertEqual(self.call("POST", "/account/password", {"password": "FAKE_PASSWORD_ONLY"}).status_code, 200)
        for _ in range(2):
            self.assertEqual(self.call("POST", "/account/test", {}).status_code, 200)
        self.assertEqual(self.call("POST", "/account/test", {}).status_code, 429)
        self.assertFalse(self.call("GET", "/account").json["needs_auth"])
        self.now += 31 * 86400
        self.assertEqual(self.call("GET", "/account").status_code, 401)

    def test_worker_targets_dedupe_pause_and_late_enable(self):
        account = self.login()
        self.enable()
        self.sender.messages.clear()
        worker = Worker(self.store, self.school, self.sender, lambda: self.now)
        self.now = datetime(2026, 10, 12, 7, 1, tzinfo=BEIJING).timestamp()
        worker.tick()
        worker.tick()
        self.assertEqual(len(self.sender.messages), 1)
        self.assertEqual(str(self.school.calls[-1][2]), "2026-10-12")
        self.now = datetime(2026, 10, 12, 20, 1, tzinfo=BEIJING).timestamp()
        worker.tick()
        self.assertEqual(str(self.school.calls[-1][2]), "2026-10-13")
        self.enable(paused=True)
        self.now += 86400
        worker.tick()
        self.assertEqual(len(self.sender.messages), 2)
        self.enable(paused=False)
        worker.tick()  # Do not backfill the already-started evening slot.
        self.assertEqual(len(self.sender.messages), 2)
        self.now += 86400
        worker.tick()
        self.assertEqual(len(self.sender.messages), 3)

    def test_unknown_delivery_and_worker_restart(self):
        account = self.login()
        self.enable()
        self.sender.error = ServiceError("投递结果待确认", "unknown")
        self.now = datetime(2026, 10, 12, 7, 5, tzinfo=BEIJING).timestamp()
        Worker(self.store, self.school, self.sender, lambda: self.now).tick()
        self.sender.error = None
        Worker(self.store, self.school, self.sender, lambda: self.now).tick()
        jobs = self.call("GET", "/account").json["jobs"]
        self.assertEqual(jobs[0]["status"], "unknown")
        self.assertEqual(len(self.school.calls), 1)
        with self.store.db() as db:
            db.execute("UPDATE jobs SET status='running'")
        Worker(self.store, self.school, self.sender, lambda: self.now).tick()
        self.assertEqual(len(self.school.calls), 1)

    def test_auth_failure_disables_other_jobs(self):
        account = self.login()
        self.enable(grades=True)
        self.school.run = Mock(side_effect=ServiceError("请重新登录", "needs_auth"))
        self.now = datetime(2026, 10, 12, 7, 20, tzinfo=BEIJING).timestamp()
        Worker(self.store, self.school, self.sender, lambda: self.now).tick()
        self.assertEqual(self.school.run.call_count, 1)
        self.assertTrue(self.call("GET", "/account").json["needs_auth"])

    def test_pause_waits_for_inflight_account_lock(self):
        account = self.login()
        entered, release = threading.Event(), threading.Event()
        def hold():
            with self.store.lock(account["subject"]):
                entered.set()
                release.wait(3)
        thread = threading.Thread(target=hold)
        thread.start()
        self.assertTrue(entered.wait(1))
        timer = threading.Timer(0.1, release.set)
        timer.start()
        start = time.monotonic()
        self.enable(paused=True)
        self.assertGreaterEqual(time.monotonic() - start, 0.09)
        thread.join()

    def test_beijing_slots_and_cutoff(self):
        now = datetime(2026, 12, 31, 20, 10, tzinfo=BEIJING).timestamp()
        evening = next(item for item in due_slots(now) if item[0] == "evening")
        self.assertEqual(str(evening[3]), "2027-01-01")
        self.assertNotIn("evening", [item[0] for item in due_slots(datetime(2026, 12, 31, 20, 59, tzinfo=BEIJING).timestamp())])
        self.assertFalse(due_slots(datetime(2026, 12, 31, 23, 0, tzinfo=BEIJING).timestamp()))


class TransportTest(unittest.TestCase):
    @patch("cloud.service.requests.post")
    def test_delivery_checked_and_not_retried(self, post):
        import requests
        sender = WxSender("FAKE_TOKEN_ONLY")
        post.side_effect = requests.ReadTimeout()
        with self.assertRaises(ServiceError) as error:
            sender.send("UID_FAKEUSER00001", "x", "y")
        self.assertEqual(error.exception.status, "unknown")
        self.assertEqual(post.call_count, 1)
        post.side_effect = None
        post.return_value = Mock(status_code=200)
        post.return_value.json.return_value = {"code": 1000, "data": [{"code": 1001}]}
        with self.assertRaises(ServiceError) as error:
            sender.send("UID_FAKEUSER00001", "x", "y")
        self.assertEqual(error.exception.status, "needs_binding")


if __name__ == "__main__":
    unittest.main()
