import unittest
from unittest.mock import Mock

from cloud.service import CloudGrades, ServiceError


def snapshot(score, term="2026-2027-1"):
    return {"semester_id": term, "semester_name": term, "grades": [{
        "grade_id": term + ":FAKE_COURSE", "semester_id": term, "semester_name": term,
        "course_name": "测试课程", "score": str(score), "snapshot_hash": str(score),
    }]}


class GradeCloudTest(unittest.TestCase):
    def setUp(self):
        self.state = {}
        self.sender = Mock()
        self.service = CloudGrades(self.state, Mock(), self.sender)
        self.scraper = Mock()
        self.term = "2026-2027-1"
        self.scraper.get_current_term.return_value = {"semester_id": self.term, "semester_name": self.term}
        self.scraper.get_semester_list.return_value = [self.scraper.get_current_term.return_value]
        self.scraper.get_term_grades.return_value = snapshot(80)
        self.service._create_scraper = lambda: self.scraper

    def test_first_enable_and_term_switch_only_initialize(self):
        self.assertIn("基线", self.service.check_changes())
        self.sender.assert_not_called()
        self.service.check_changes()
        self.sender.assert_not_called()
        self.scraper.get_current_term.return_value = {"semester_id": "2026-2027-2", "semester_name": "2026-2027-2"}
        self.scraper.get_semester_list.return_value = [self.scraper.get_current_term.return_value]
        self.scraper.get_term_grades.return_value = snapshot(90, "2026-2027-2")
        self.assertIn("基线", self.service.check_changes())
        self.sender.assert_not_called()

    def test_changes_sent_once_after_success(self):
        self.service.check_changes()
        self.scraper.get_term_grades.return_value = snapshot(90)
        self.service.check_changes()
        self.service.check_changes()
        self.sender.assert_called_once()
        self.assertIn("原分数 80", self.sender.call_args.args[0])

    def test_known_failure_retains_baseline_unknown_does_not_repeat(self):
        self.service.check_changes()
        self.scraper.get_term_grades.return_value = snapshot(90)
        self.sender.side_effect = ServiceError("测试失败")
        with self.assertRaises(ServiceError):
            self.service.check_changes()
        baseline = self.service._flatten_grade_map(self.service.load_grade_cache())
        self.assertEqual(next(iter(baseline.values()))["score"], "80")
        self.sender.side_effect = ServiceError("结果待确认", "unknown")
        with self.assertRaises(ServiceError):
            self.service.check_changes()
        self.sender.reset_mock()
        self.sender.side_effect = None
        self.service.check_changes()
        self.sender.assert_not_called()
