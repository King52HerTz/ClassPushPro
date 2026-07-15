import os
import sys
import unittest
from datetime import date


SRC_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from academic_calendar import (  # noqa: E402
    merge_cached_teaching_state,
    normalize_teaching_state,
    week_number_for_date,
)


class AcademicCalendarTests(unittest.TestCase):
    def test_vacation_placeholder_week_is_not_treated_as_week_one(self):
        payload = {
            "isNowWeek": "0",
            "nowWeek": "1",
            "data": [{"week": str(week)} for week in range(2, 20)],
        }
        state = normalize_teaching_state(
            payload,
            {"semester_id": "2025-2026-2"},
            observed_date=date(2026, 7, 16),
        )

        self.assertEqual(state["schedule_status"], "vacation")
        self.assertFalse(state["is_teaching_week"])
        self.assertEqual(state["current_week"], 1)
        self.assertEqual(state["week_one_monday"], "")
        self.assertEqual(state["available_weeks"], list(range(2, 20)))

    def test_active_week_two_infers_official_week_one_monday(self):
        state = normalize_teaching_state(
            {"isNowWeek": "1", "nowWeek": "2", "data": [{"week": "2"}, {"week": "3"}]},
            {"semester_id": "2026-2027-1"},
            observed_date=date(2026, 9, 14),
        )

        self.assertEqual(state["schedule_status"], "active")
        self.assertEqual(state["week_one_monday"], "2026-09-07")
        self.assertEqual(week_number_for_date(state["week_one_monday"], date(2026, 9, 20)), 2)
        self.assertEqual(week_number_for_date(state["week_one_monday"], date(2026, 9, 21)), 3)

    def test_unknown_response_never_defaults_to_active_week_one(self):
        state = normalize_teaching_state({}, {"semester_id": "2026-2027-1"})
        self.assertEqual(state["schedule_status"], "unknown")
        self.assertFalse(state["is_teaching_week"])
        self.assertIsNone(state["current_week"])

    def test_active_cache_expires_after_last_available_week(self):
        cached = {
            "teaching_state": {
                "schedule_status": "active",
                "is_teaching_week": True,
                "current_week": 19,
                "available_weeks": list(range(2, 20)),
                "week_one_monday": "2026-03-02",
                "semester_id": "2025-2026-2",
            }
        }
        state = merge_cached_teaching_state(cached, target_date=date(2026, 7, 20))
        self.assertEqual(state["current_week"], 21)
        self.assertEqual(state["schedule_status"], "vacation")
        self.assertFalse(state["is_teaching_week"])


if __name__ == "__main__":
    unittest.main()
