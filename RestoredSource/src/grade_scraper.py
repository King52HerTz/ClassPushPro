import hashlib
import json
import os
import random
import time
from urllib.parse import urlencode

import requests

from logger import logger
from school_adapter import SCHOOL_CONFIG


def _get_env_int(name, default_val):
    raw = (os.getenv(name) or "").strip()
    if not raw:
        return default_val
    try:
        return int(raw)
    except Exception:
        return default_val


def _get_env_float(name, default_val):
    raw = (os.getenv(name) or "").strip()
    if not raw:
        return default_val
    try:
        return float(raw)
    except Exception:
        return default_val


def _get_timeout(connect_default, read_default):
    connect = _get_env_float("CP_HTTP_CONNECT_TIMEOUT", connect_default)
    read = _get_env_float("CP_HTTP_READ_TIMEOUT", read_default)
    if connect <= 0:
        connect = connect_default
    if read <= 0:
        read = read_default
    return (connect, read)


class GradeScraper:
    """
    负责从教务系统抓取并规范化成绩数据
    """

    def __init__(self, token, session=None):
        self.token = token
        self.session = session if session else requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        })

    def _post_with_retry(self, url, timeout, retries, headers=None):
        last_exc = None
        for attempt in range(max(0, retries) + 1):
            try:
                return self.session.post(url, timeout=timeout, headers=headers)
            except requests.RequestException as e:
                last_exc = e
                if attempt >= retries:
                    raise
                base = _get_env_float("CP_HTTP_RETRY_BACKOFF_SECONDS", 1.5)
                sleep_seconds = (base * (2 ** attempt)) + random.random()
                time.sleep(sleep_seconds)
        if last_exc:
            raise last_exc

    def _build_grade_headers(self):
        return {
            "token": self.token,
            "Accept": "application/json, text/plain, */*",
            "Origin": "https://jw.hnit.edu.cn",
            "Referer": "https://jw.hnit.edu.cn/",
            "X-Requested-With": "XMLHttpRequest",
        }

    def _request_json(self, path, query=None, timeout=None, retries=None):
        if not self.token:
            raise ValueError("成绩抓取缺少 token")

        timeout = timeout or _get_timeout(10, 15)
        retries = _get_env_int("CP_HTTP_RETRIES", 2) if retries is None else retries

        url = f"{SCHOOL_CONFIG['BASE_URL'].rstrip('/')}/{path.lstrip('/')}"
        if query:
            url = f"{url}?{urlencode(query)}"

        response = self._post_with_retry(
            url,
            timeout=timeout,
            retries=retries,
            headers=self._build_grade_headers(),
        )
        response.raise_for_status()

        payload = response.json()
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except Exception:
                pass
        return payload

    def _extract_data_list(self, payload):
        if isinstance(payload, list):
            return payload
        if isinstance(payload, dict):
            data = payload.get("data", [])
            if isinstance(data, list):
                return data
            if isinstance(data, dict):
                return [data]
        return []

    def _normalize_semester(self, item):
        if not isinstance(item, dict):
            return {}

        semester_id = str(item.get("semesterId") or item.get("semesterName") or "").strip()
        semester_name = str(item.get("semesterName") or semester_id).strip()
        if not semester_id:
            return {}

        return {
            "semester_id": semester_id,
            "semester_name": semester_name,
        }

    def get_current_term(self):
        payload = self._request_json("currentTerm", timeout=_get_timeout(8, 12), retries=1)
        items = self._extract_data_list(payload)
        for item in items:
            semester = self._normalize_semester(item)
            if semester:
                return semester
        return {}

    def get_semester_list(self):
        payload = self._request_json("semesterList", timeout=_get_timeout(8, 12), retries=1)
        items = self._extract_data_list(payload)
        semesters = []
        seen = set()

        for item in items:
            semester = self._normalize_semester(item)
            semester_id = semester.get("semester_id")
            if not semester_id or semester_id in seen:
                continue
            seen.add(semester_id)
            semesters.append(semester)

        return semesters

    def get_term_grades(self, semester_id, semester_name=""):
        if not isinstance(semester_id, str) or not semester_id.strip():
            raise ValueError("semester_id 不能为空")

        semester_id = semester_id.strip()
        payload = self._request_json(
            "student/termGPA",
            query={"semester": semester_id, "type": 1},
            timeout=_get_timeout(10, 18),
            retries=2,
        )

        data_list = self._extract_data_list(payload)
        first_block = data_list[0] if data_list and isinstance(data_list[0], dict) else {}
        raw_grades = first_block.get("achievement", [])
        if not isinstance(raw_grades, list):
            raw_grades = []

        resolved_semester_name = str(
            semester_name
            or first_block.get("semesterName")
            or first_block.get("xnxq")
            or semester_id
        ).strip()

        grades = []
        for raw_grade in raw_grades:
            if not isinstance(raw_grade, dict):
                continue
            grades.append(self.normalize_grade_item(raw_grade, semester_id, resolved_semester_name))

        return {
            "semester_id": semester_id,
            "semester_name": resolved_semester_name or semester_id,
            "student_info": self._extract_student_info(first_block),
            "summary": self._extract_summary(first_block),
            "grades": grades,
        }

    def normalize_grade_item(self, raw_grade, semester_id, semester_name):
        if not isinstance(raw_grade, dict):
            raise ValueError("raw_grade 必须是字典")

        course_name = self._to_text(raw_grade.get("courseName"))
        exam_name = self._to_text(raw_grade.get("examName"))
        examination_nature = self._to_text(raw_grade.get("examinationNature"))
        course_code = self._to_text(raw_grade.get("kcbh"))

        grade_id = self._to_text(raw_grade.get("cj0708id"))
        if not grade_id:
            grade_id = self._build_fallback_grade_id(
                semester_id=semester_id,
                course_name=course_name,
                exam_name=exam_name,
                examination_nature=examination_nature,
                course_code=course_code,
            )

        normalized = {
            "grade_id": grade_id,
            "semester_id": semester_id,
            "semester_name": semester_name or semester_id,
            "course_name": course_name,
            "score": self._to_text(raw_grade.get("fraction")),
            "credit": self._to_text(raw_grade.get("credit")),
            "gpa": self._to_text(raw_grade.get("jd")),
            "exam_name": exam_name,
            "examination_nature": examination_nature,
            "course_nature": self._to_text(raw_grade.get("courseNature")),
            "curriculum_attributes": self._to_text(raw_grade.get("curriculumAttributes")),
            "course_code": course_code,
            "pass_status": self._to_text(raw_grade.get("sfjg")),
            "publish_time": self._to_text(
                raw_grade.get("publishTime")
                or raw_grade.get("fbsj")
                or raw_grade.get("createTime")
            ),
        }
        normalized["snapshot_hash"] = self._build_snapshot_hash(normalized)
        return normalized

    def _extract_student_info(self, first_block):
        if not isinstance(first_block, dict):
            return {}

        field_candidates = {
            "student_name": ["studentName", "name", "xm"],
            "student_no": ["studentNo", "xh", "userNo"],
            "class_name": ["clsName", "className", "bjmc"],
            "academy_name": ["academyName", "departmentName", "yxmc"],
        }

        info = {}
        for target_key, candidates in field_candidates.items():
            for source_key in candidates:
                value = self._to_text(first_block.get(source_key))
                if value:
                    info[target_key] = value
                    break
        return info

    def _extract_summary(self, first_block):
        if not isinstance(first_block, dict):
            return {}

        summary = {}
        for key, value in first_block.items():
            if key == "achievement":
                continue
            if isinstance(value, (dict, list)):
                continue
            text = self._to_text(value)
            if text:
                summary[key] = text
        return summary

    def _build_fallback_grade_id(self, semester_id, course_name, exam_name, examination_nature, course_code):
        raw = "|".join([
            semester_id or "",
            course_name or "",
            exam_name or "",
            examination_nature or "",
            course_code or "",
        ])
        return hashlib.md5(raw.encode("utf-8")).hexdigest().upper()

    def _build_snapshot_hash(self, item):
        raw = "|".join([
            item.get("semester_id", ""),
            item.get("course_name", ""),
            item.get("score", ""),
            item.get("credit", ""),
            item.get("gpa", ""),
            item.get("exam_name", ""),
            item.get("examination_nature", ""),
            item.get("pass_status", ""),
        ])
        return hashlib.md5(raw.encode("utf-8")).hexdigest()

    def _to_text(self, value):
        if value is None:
            return ""
        return str(value).strip()
