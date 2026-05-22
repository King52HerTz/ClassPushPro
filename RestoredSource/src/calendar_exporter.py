import os
import re
import hashlib
import html
from datetime import datetime, timedelta


def _escape_ics_text(value):
    text = str(value or "")
    text = text.replace("\\", "\\\\")
    text = text.replace(";", r"\;")
    text = text.replace(",", r"\,")
    text = text.replace("\r\n", r"\N").replace("\n", r"\N")
    return text


def _join_description_parts(parts):
    cleaned_parts = [str(part or "").strip() for part in parts if str(part or "").strip()]
    return _escape_ics_text(" | ".join(cleaned_parts))


class CalendarExporter:
    def __init__(
        self,
        semester_start_date,
        time_slots,
        courses,
        current_week="1",
        alarm_minutes=15,
        allowed_weeks=None,
        date_range=None,
    ):
        self.semester_start_date = str(semester_start_date or "").strip()
        self.time_slots = time_slots if isinstance(time_slots, dict) else {}
        self.courses = courses if isinstance(courses, list) else []
        self.current_week = str(current_week or "1")
        self.alarm_minutes = self._normalize_alarm_minutes(alarm_minutes)
        self.allowed_weeks = set(allowed_weeks or []) if allowed_weeks else None
        self.date_range = date_range if isinstance(date_range, tuple) and len(date_range) == 2 else None
        self.exported_event_count = 0
        self.export_timestamp_utc = ""
        self.export_sequence = 0

    def export_to_file(self, file_path):
        content = self.build_ics_content()
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "w", encoding="utf-8", newline="\r\n") as file_obj:
            file_obj.write(content)
        return file_path

    def build_ics_content(self):
        week_one_monday = self._parse_semester_start_date()
        self.exported_event_count = 0
        export_now = datetime.utcnow()
        self.export_timestamp_utc = export_now.strftime("%Y%m%dT%H%M%SZ")
        self.export_sequence = int(export_now.timestamp())
        lines = [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//ClassPush//Course Schedule//CN",
            "CALSCALE:GREGORIAN",
            "METHOD:PUBLISH",
            "X-WR-CALNAME:ClassPush 课表",
            "X-WR-TIMEZONE:Asia/Shanghai",
            "BEGIN:VTIMEZONE",
            "TZID:Asia/Shanghai",
            "X-LIC-LOCATION:Asia/Shanghai",
            "BEGIN:STANDARD",
            "DTSTART:19700101T000000",
            "TZOFFSETFROM:+0800",
            "TZOFFSETTO:+0800",
            "TZNAME:CST",
            "END:STANDARD",
            "END:VTIMEZONE",
        ]

        for course in self.courses:
            for event in self._expand_course_events(course, week_one_monday):
                lines.extend(event)
                self.exported_event_count += 1

        lines.append("END:VCALENDAR")
        return "\r\n".join(lines) + "\r\n"

    def _parse_semester_start_date(self):
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", self.semester_start_date):
            raise ValueError("请先在设置中填写学期第1周周一日期")

        try:
            start_date = datetime.strptime(self.semester_start_date, "%Y-%m-%d").date()
        except ValueError as exc:
            raise ValueError("学期起始日期格式无效") from exc

        if start_date.weekday() != 0:
            raise ValueError("学期起始日期必须是周一")

        return start_date

    def _expand_course_events(self, course, week_one_monday):
        weekday = self._resolve_weekday(course)
        if weekday is None:
            return []

        start_time, end_time = self._resolve_course_time_range(course)
        if not start_time or not end_time:
            return []

        occurrences = []
        for week in self._parse_weeks(course.get("classWeekDetails") or course.get("classWeek")):
            if self.allowed_weeks is not None and week not in self.allowed_weeks:
                continue
            course_date = week_one_monday + timedelta(days=(week - 1) * 7 + (weekday - 1))
            if not self._is_date_in_range(course_date):
                continue
            start_dt = datetime.combine(course_date, datetime.strptime(start_time, "%H:%M").time())
            end_dt = datetime.combine(course_date, datetime.strptime(end_time, "%H:%M").time())
            occurrences.append(self._build_event_lines(course, start_dt, end_dt, week))
        return occurrences

    def _build_event_lines(self, course, start_dt, end_dt, week):
        uid = self._build_stable_uid(course, week)
        course_name = _escape_ics_text(course.get("courseName") or "未命名课程")
        teacher_name_raw = str(course.get("teacherName") or "未填写")
        location_raw = str(course.get("location") or "未填写")
        teacher_name = _escape_ics_text(teacher_name_raw)
        location = _escape_ics_text(location_raw)
        description = _join_description_parts(
            [
                f"教师：{teacher_name_raw}",
                f"地点：{location_raw}",
                f"周次：第{week}周",
                f"节次：{course.get('classTime') or '--'}",
            ]
        )
        html_description = self._build_html_description(course, teacher_name_raw, location_raw, week)
        lines = [
            "BEGIN:VEVENT",
            f"UID:{uid}",
            f"DTSTAMP:{self.export_timestamp_utc}",
            f"CREATED:{self.export_timestamp_utc}",
            f"LAST-MODIFIED:{self.export_timestamp_utc}",
            f"SEQUENCE:{self.export_sequence}",
            f"DTSTART;TZID=Asia/Shanghai:{start_dt.strftime('%Y%m%dT%H%M%S')}",
            f"DTEND;TZID=Asia/Shanghai:{end_dt.strftime('%Y%m%dT%H%M%S')}",
            f"SUMMARY:{course_name}",
            f"LOCATION:{location}",
            f"DESCRIPTION:{description}",
            f"X-ALT-DESC;FMTTYPE=text/html:{html_description}",
            "END:VEVENT",
        ]
        if self.alarm_minutes > 0:
            alarm_text = _escape_ics_text(
                f"{course.get('courseName') or '课程'} 将在 {self.alarm_minutes} 分钟后开始"
            )
            lines[-1:-1] = [
                "BEGIN:VALARM",
                "ACTION:DISPLAY",
                f"TRIGGER:-PT{self.alarm_minutes}M",
                f"DESCRIPTION:{alarm_text}",
                "END:VALARM",
            ]
        return lines

    def _build_stable_uid(self, course, week):
        identity_parts = [
            self.semester_start_date,
            str(course.get("courseName") or "").strip(),
            str(course.get("teacherName") or "").strip(),
            str(course.get("weekday") or course.get("xqmc") or "").strip(),
            str(week),
        ]

        digest = hashlib.sha1("|".join(identity_parts).encode("utf-8")).hexdigest()
        return f"{digest}@classpush"

    def _build_html_description(self, course, teacher_name, location, week):
        html_lines = [
            f"教师：{html.escape(str(teacher_name or '未填写'))}",
            f"地点：{html.escape(str(location or '未填写'))}",
            f"周次：第{week}周",
            f"节次：{html.escape(str(course.get('classTime') or '--'))}",
        ]
        return "<br/>".join(html_lines)

    def _resolve_weekday(self, course):
        weekday = course.get("weekday")
        try:
            weekday_num = int(weekday)
            if 1 <= weekday_num <= 7:
                return weekday_num
        except (TypeError, ValueError):
            pass

        xqmc = str(course.get("xqmc") or "").strip()
        weekday_map = {
            "星期一": 1,
            "星期二": 2,
            "星期三": 3,
            "星期四": 4,
            "星期五": 5,
            "星期六": 6,
            "星期日": 7,
            "周一": 1,
            "周二": 2,
            "周三": 3,
            "周四": 4,
            "周五": 5,
            "周六": 6,
            "周日": 7,
        }
        return weekday_map.get(xqmc)

    def _parse_weeks(self, week_text):
        values = []
        for raw in str(week_text or "").split(","):
            piece = raw.strip()
            if not piece:
                continue
            if "-" in piece:
                start_str, end_str = piece.split("-", 1)
                try:
                    start_week = int(start_str)
                    end_week = int(end_str)
                except ValueError:
                    continue
                if start_week <= end_week:
                    values.extend(range(start_week, end_week + 1))
            else:
                try:
                    values.append(int(piece))
                except ValueError:
                    continue
        return sorted(set(week for week in values if week > 0))

    def _resolve_course_time_range(self, course):
        start_node = course.get("startNode")
        end_node = course.get("endNode")
        try:
            start_node = int(start_node)
            end_node = int(end_node)
            if start_node > 0 and end_node > 0:
                return self._lookup_time_range_by_nodes(start_node, end_node)
        except (TypeError, ValueError):
            pass

        return self._lookup_time_range_by_class_time(course.get("classTime"))

    def _lookup_time_range_by_nodes(self, start_node, end_node):
        start_time = ""
        end_time = ""
        for slot_key, slot_range in self.time_slots.items():
            start_slot, end_slot = self._parse_slot_key(slot_key)
            if start_slot is None or end_slot is None:
                continue
            if start_slot <= start_node <= end_slot and not start_time:
                start_time = str(slot_range[0] or "").strip()
            if start_slot <= end_node <= end_slot:
                end_time = str(slot_range[1] or "").strip()
        return start_time, end_time

    def _lookup_time_range_by_class_time(self, class_time):
        text = str(class_time or "")
        for slot_key, slot_range in self.time_slots.items():
            if slot_key in text:
                return str(slot_range[0] or "").strip(), str(slot_range[1] or "").strip()
        return "", ""

    def _parse_slot_key(self, slot_key):
        match = re.match(r"^\s*(\d+)\s*-\s*(\d+)\s*$", str(slot_key or ""))
        if not match:
            return None, None
        return int(match.group(1)), int(match.group(2))

    def _normalize_alarm_minutes(self, value):
        try:
            minutes = int(value)
        except (TypeError, ValueError):
            return 15
        return max(0, minutes)

    def _is_date_in_range(self, course_date):
        if not self.date_range:
            return True
        range_start, range_end = self.date_range
        return range_start <= course_date <= range_end
