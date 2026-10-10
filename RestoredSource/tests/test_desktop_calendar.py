import os
import sys
import tempfile
import unittest
from datetime import datetime, date
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))
from api import Api
from calendar_exporter import CalendarExporter
from config_manager import ConfigManager, DEFAULT_TIME_SLOTS
from push_content import filter_courses, generate_push_content


COURSE = {"courseName": "测试<script>", "classTime": "1-2", "startNode": 1,
          "endNode": 2, "location": "测试教室", "teacherName": "测试老师",
          "weekday": 1, "xqmc": "星期一", "classWeekDetails": "2,3", "classWeek": "2-3周"}


class DesktopCalendarTest(unittest.TestCase):
    def test_official_week_two_and_no_false_full_term(self):
        exporter = CalendarExporter('2026-08-31', DEFAULT_TIME_SLOTS, [COURSE], allowed_weeks={2})
        content = exporter.build_ics_content()
        self.assertIn('DTSTART;TZID=Asia/Shanghai:20260907T083000', content)
        self.assertEqual(exporter.exported_event_count, 1)
        empty = CalendarExporter('2026-08-31', DEFAULT_TIME_SLOTS, [COURSE], allowed_weeks=set())
        empty.build_ics_content()
        self.assertEqual(empty.exported_event_count, 0)

    def test_ics_crlf_reminder_and_missing_anchor(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, 'test.ics')
            CalendarExporter('2026-08-31', DEFAULT_TIME_SLOTS, [COURSE], alarm_minutes=15).export_to_file(path)
            with open(path, 'rb') as handle:
                content = handle.read()
            self.assertIn(b'\r\n', content)
            self.assertNotIn(b'\r\r\n', content)
            self.assertIn(b'TRIGGER:-PT15M', content)
        with self.assertRaises(ValueError):
            CalendarExporter('', DEFAULT_TIME_SLOTS, [COURSE]).build_ics_content()

    def test_switch_account_invalidates_cache_and_legacy_token(self):
        with tempfile.TemporaryDirectory() as directory:
            config = ConfigManager(os.path.join(directory, 'config.json'))
            config.save_config('FAKE_STUDENT_A', 'FAKE_PASSWORD_A')
            config.save_cached_courses([COURSE], 2, '2026-2027-1', {'week_one_monday': '2026-08-31'})
            self.assertIsNotNone(config.get_cached_courses())
            config.config_data['app_token'] = 'FAKE_TOKEN_ONLY'
            config.save_config('FAKE_STUDENT_B', 'FAKE_PASSWORD_B')
            self.assertIsNone(config.get_cached_courses())
            self.assertIsNone(config.get('app_token'))
            with open(config.config_path, encoding='utf-8') as handle:
                self.assertNotIn('FAKE_PASSWORD', handle.read())

    def test_actual_calendar_week_before_start_is_empty(self):
        fake = Api.__new__(Api)
        with patch('api.datetime') as clock:
            clock.now.return_value = datetime(2026, 8, 20)
            result = fake._resolve_export_constraints('current_week', 1, '2026-08-31')
        self.assertEqual(result['allowed_weeks'], set())

    def test_cloud_filter_uses_target_week_and_escapes_html(self):
        selected = filter_courses([COURSE], date(2026, 9, 7), 2)
        self.assertEqual(len(selected), 1)
        self.assertFalse(filter_courses([COURSE], date(2026, 9, 8), 2))
        self.assertFalse(filter_courses([COURSE], date(2026, 9, 7), None))
        content, _ = generate_push_content(selected, '09月07日', '星期一')
        self.assertIn('&lt;script&gt;', content)
        self.assertNotIn('<script>', content)
