import os
import sys
import tempfile
import unittest
from datetime import datetime
from unittest.mock import patch


SRC_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from config_manager import ConfigManager  # noqa: E402
from run_job import _generate_non_teaching_push_content, _schedule_push_key, run_push_task  # noqa: E402


class SchedulePushDedupeTests(unittest.TestCase):
    def test_push_key_distinguishes_morning_and_night_targets(self):
        target = datetime(2026, 9, 7, 7, 0)

        self.assertEqual(_schedule_push_key(True, target), "morning:2026-09-07")
        self.assertEqual(_schedule_push_key(False, target.date()), "night:2026-09-07")

    def test_successful_keys_survive_config_reload_without_duplicates(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = os.path.join(temp_dir, "config.json")
            config = ConfigManager(config_path=config_path)

            self.assertTrue(config.mark_successful_schedule_push("morning:2026-09-07"))
            self.assertTrue(config.mark_successful_schedule_push("night:2026-09-08"))
            self.assertTrue(config.mark_successful_schedule_push("morning:2026-09-07"))

            restored = ConfigManager(config_path=config_path)
            self.assertTrue(restored.has_successful_schedule_push("morning:2026-09-07"))
            self.assertTrue(restored.has_successful_schedule_push("night:2026-09-08"))
            self.assertEqual(
                restored.get("successful_schedule_push_keys"),
                ["night:2026-09-08", "morning:2026-09-07"],
            )

    def test_invalid_push_key_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config = ConfigManager(config_path=os.path.join(temp_dir, "config.json"))

            self.assertFalse(config.mark_successful_schedule_push("2026-09-07"))
            self.assertFalse(config.has_successful_schedule_push("2026-09-07"))

    def test_successful_retry_slot_skips_before_school_login(self):
        class ExistingSuccessConfig:
            def __init__(self):
                self.checked_key = ""

            def get(self, key, default=None):
                values = {
                    "username": "student",
                    "password": "secret",
                    "app_token": "token",
                    "uid": "uid",
                    "push_time": "07:00",
                    "last_push_success_time": "",
                }
                return values.get(key, default)

            def get_cached_courses(self):
                return None

            def has_successful_schedule_push(self, push_key):
                self.checked_key = push_key
                return True

        config = ExistingSuccessConfig()
        with (
            patch("run_job.ConfigManager", return_value=config),
            patch("run_job.LoginManager") as login_manager,
            patch.dict(os.environ, {"CP_PUSH_TIME": "07:00", "CP_PUSH_SLOT": "morning"}),
        ):
            success, message = run_push_task(force=False, source="auto")

        self.assertTrue(success)
        self.assertTrue(config.checked_key.startswith("morning:"))
        self.assertIn("已推送", message)
        login_manager.assert_not_called()

    def test_vacation_manual_message_keeps_xiaozhu_tone(self):
        content, summary = _generate_non_teaching_push_content("vacation", "当前是假期")

        self.assertIn("小主", summary)
        self.assertIn("今日课程：0 节", content)
        self.assertIn("根本没有早八", content)
        self.assertIn("课程也集体去度假", content)


if __name__ == "__main__":
    unittest.main()
