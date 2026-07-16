import os
import sys
import tempfile
import unittest


SRC_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from grade_service import GradeService  # noqa: E402


def grade(score, snapshot_hash, course_name="数据结构"):
    return {
        "grade_id": "2025-2026-2:data-structure",
        "semester_id": "2025-2026-2",
        "semester_name": "2025-2026-2",
        "course_name": course_name,
        "score": str(score),
        "credit": "3",
        "gpa": "3.5",
        "exam_name": "期末考试",
        "examination_nature": "正常考试",
        "pass_status": "通过",
        "snapshot_hash": snapshot_hash,
    }


class FakeConfig:
    def __init__(self, directory):
        self.config_path = os.path.join(directory, "config.json")
        self.values = {
            "username": "student",
            "password": "password",
            "app_token": "test-token",
            "uid": "test-uid",
            "grade_push_enabled": True,
            "grade_push_initialized": True,
        }

    def get(self, key, default=None):
        return self.values.get(key, default)

    def update_grade_push_initialized(self, value):
        self.values["grade_push_initialized"] = bool(value)
        return True


class FakeScraper:
    def __init__(self, latest_grade):
        self.latest_grade = latest_grade

    def get_current_term(self):
        return {"semester_id": "2025-2026-2", "semester_name": "2025-2026-2"}

    def get_semester_list(self):
        return [self.get_current_term()]

    def get_term_grades(self, semester_id, semester_name=""):
        return {
            "semester_id": semester_id,
            "semester_name": semester_name or semester_id,
            "student_info": {},
            "summary": {},
            "grades": [self.latest_grade],
        }


class GradeServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config = FakeConfig(self.temp_dir.name)
        self.service = GradeService(self.config)
        baseline = self.service._empty_cache()
        baseline["last_check_time"] = "2026-07-16 08:00:00"
        baseline["current_term"] = FakeScraper(grade(80, "old")).get_current_term()
        baseline["semester_list"] = [baseline["current_term"]]
        self.service._upsert_semester_snapshot(
            baseline,
            FakeScraper(grade(80, "old")).get_term_grades("2025-2026-2", "2025-2026-2"),
        )
        self.service.save_grade_cache(baseline)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_failed_push_does_not_advance_grade_baseline(self):
        self.service._create_scraper = lambda: FakeScraper(grade(85, "new"))
        self.service._push_grade_changes = lambda new, updated: (False, "network error")

        result = self.service.check_new_grades()

        self.assertEqual(len(result["updated_items"]), 1)
        self.assertFalse(result["push_result"]["success"])
        cached = self.service._flatten_grade_map(self.service.load_grade_cache())
        self.assertEqual(cached["2025-2026-2:data-structure"]["score"], "80")

    def test_score_update_is_pushed_and_saved_after_success(self):
        self.service._create_scraper = lambda: FakeScraper(grade(85, "new"))
        calls = []
        self.service._push_grade_changes = lambda new, updated: (calls.append((new, updated)) is None, "ok")

        result = self.service.check_new_grades()

        self.assertTrue(result["push_result"]["success"])
        self.assertEqual(len(calls[0][1]), 1)
        cached = self.service._flatten_grade_map(self.service.load_grade_cache())
        self.assertEqual(cached["2025-2026-2:data-structure"]["score"], "85")

    def test_html_message_escapes_course_name_and_shows_old_score(self):
        content, summary = self.service.build_grade_push_message(
            [],
            [{"before": grade(55, "old"), "after": grade(65, "new", "Web <script>")}],
        )
        self.assertIn("成绩有更新", summary)
        self.assertIn("Web &lt;script&gt;", content)
        self.assertIn("原分数 55", content)
        self.assertIn("打开教务系统", content)
        self.assertNotIn("Web <script>", content)

    def test_manual_full_term_message_contains_every_grade_and_xiaozhu(self):
        content, summary = self.service.build_grade_push_message(
            [grade(80, "one", "数据结构"), grade(92, "two", "计算机网络")],
            is_manual_full=True,
        )

        self.assertIn("小主", summary)
        self.assertIn("共 2 门", content)
        self.assertIn("数据结构", content)
        self.assertIn("计算机网络", content)
        self.assertIn("不会改变自动检测基线", content)


if __name__ == "__main__":
    unittest.main()
