import sys
import copy
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
from .outbound import ServiceError, SchoolGate, SchoolSession

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "RestoredSource" / "src"))
os.environ["CLASSPUSH_CLOUD"] = "1"

from academic_calendar import week_number_for_date
from grade_service import GradeService
from login_manager import LoginManager
from real_scraper import CourseScraper
from logger import logger as school_logger

# Legacy school clients log HTTP exception URLs. Never emit those in the cloud.
school_logger.disabled = True

BEIJING = timezone(timedelta(hours=8))


class StateConfig:
    """The existing school client sees only this account's encrypted state."""
    config_path = "unused/grades.json"

    def __init__(self, state):
        self.state = state

    def get(self, key, default=None):
        return self.state.get(key, default)

    def update_jw_cached_token(self, username, token, login_time, cookies_dict=None):
        self.state.update(jw_cached_username=username, jw_cached_token=token,
                          jw_cached_cookies=cookies_dict or {}, jw_cached_time=login_time)

    def clear_jw_cached_token(self):
        for key in ("jw_cached_username", "jw_cached_token", "jw_cached_cookies"):
            self.state.pop(key, None)

    def update_grade_push_initialized(self, value):
        self.state["grade_push_initialized"] = value


class CloudGrades(GradeService):
    def _now_str(self):
        return datetime.now(BEIJING).strftime("%Y-%m-%d %H:%M:%S")

    def __init__(self, state, login, sender):
        super().__init__(StateConfig(state))
        self.login = login
        self.sender = sender

    def load_grade_cache(self):
        return self._normalize_cache_shape(self.config.state.get("grade_cache", self._empty_cache()))

    def save_grade_cache(self, cache):
        self.config.state["grade_cache"] = self._normalize_cache_shape(cache)
        return True

    def _create_scraper(self):
        from grade_scraper import GradeScraper
        return GradeScraper(self.login.token, session=self.login.session)

    def _push_grade_changes(self, new_items, updated_items):
        content, title = self.build_grade_push_message(new_items, updated_items)
        self.sender(content, title)
        return True, "成绩通知已提交 WxPusher"

    def check_changes(self):
        scraper = self._create_scraper()
        term = scraper.get_current_term()
        semesters = scraper.get_semester_list()
        selected = self._resolve_selected_semester(None, term, semesters)
        latest = scraper.get_term_grades(selected["semester_id"], selected["semester_name"])
        self.login.session.check()
        old = self.load_grade_cache()
        cache = copy.deepcopy(old)
        cache.update(current_term=term, semester_list=semesters, last_check_time=self._now_str())
        self._upsert_semester_snapshot(cache, latest)
        known_term = any(item["semester_id"] == latest["semester_id"] for item in old["semesters"])
        if not self.config.get("grade_push_initialized") or not known_term:
            self.config.update_grade_push_initialized(True)
            self.save_grade_cache(cache)
            return "已建立当前学期成绩基线，历史成绩不会推送"
        changes = self.compare_grade_snapshots(old, cache)
        if changes["new_items"] or changes["updated_items"]:
            try:
                self._push_grade_changes(changes["new_items"], changes["updated_items"])
            except ServiceError as exc:
                if exc.status == "unknown":
                    # Avoid resending the same changes on the next check.
                    self.save_grade_cache(cache)
                raise
            message = "成绩通知已提交 WxPusher"
        else:
            message = "当前学期暂无成绩变化"
        self.save_grade_cache(cache)
        return message


class SchoolService:
    CACHE_SECONDS = 18 * 3600

    def __init__(self, store, clock=time.time):
        self.gate = SchoolGate(store, clock=clock)
        self.clock = clock

    def login(self, state, fresh=False):
        manager = LoginManager(StateConfig(state))
        manager.session.close()
        manager.session = SchoolSession(self.gate)
        success, message = manager.login(state["username"], state["password"], use_cache=not fresh)
        try:
            manager.session.check()
        except ServiceError:
            manager.session.close()
            raise
        if not success:
            manager.session.close()
            # Do not propagate URLs, tokens, or arbitrary remote exception text.
            if "账号或密码错误" in message or "验证码" in message:
                raise ServiceError("教务账号、密码或验证码需要人工确认，请重新授权", "needs_auth")
            raise ServiceError("暂时无法登录教务系统，请稍后重试")
        return manager

    def verify(self, state):
        self.login(state, fresh=True).session.close()

    def run(self, account, kind, target, sender):
        state = account["state"]
        if kind == "grades":
            login = self.login(state)
            try:
                result = CloudGrades(state, login, sender).check_changes()
                login.session.check()
                return result
            finally:
                login.session.close()
        if kind.startswith("prepare_"):
            return self.prepare(state)
        cache = self.valid_cache(state)
        if cache is None:
            raise ServiceError("本批次课表未完成预取或数据已过期，未临时集中查询教务", "skipped")
        teaching, courses = cache["teaching"], cache["courses"]
        if teaching.get("schedule_status") != "active":
            return "非教学期或学期日期待确认，本批次未发送课表"
        if not courses:
            return "当前学期课表尚未公布，本批次未发送"
        week = week_number_for_date(teaching["week_one_monday"], target)
        available = teaching.get("available_weeks") or []
        if week is None or (available and week > max(available)):
            return "目标日期不在已确认的教学期，本批次未发送"
        from push_content import filter_courses, generate_push_content
        selected = filter_courses(courses, datetime.combine(target, datetime.min.time()), week)
        content, title = generate_push_content(selected, target.strftime("%m月%d日"),
                                               "星期" + "一二三四五六日"[target.weekday()])
        updated = datetime.fromtimestamp(cache["fetched_at"], BEIJING).strftime("%m-%d %H:%M")
        content += f'<p style="font-size:12px;color:#667085">课表数据时间：{updated}（北京时间）。快照不自动同步即时调课。</p>'
        sender(content, title)
        return "课表通知已提交 WxPusher；数据时间 " + updated

    def valid_cache(self, state):
        cache = state.get("course_cache") or {}
        if (cache.get("username") != state["username"] or not cache.get("semester_id")
                or not 0 <= self.clock() - cache.get("fetched_at", 0) < self.CACHE_SECONDS):
            return None
        teaching = cache.get("teaching", {})
        if teaching.get("semester_id") != cache["semester_id"]:
            return None
        if teaching.get("schedule_status") == "active" and not teaching.get("week_one_monday"):
            return None
        return cache

    def prepare(self, state):
        if self.valid_cache(state) is not None:
            return "已复用本账号有效课表快照，无需请求教务"
        login = self.login(state)
        try:
            return self.fetch_snapshot(state, login)
        finally:
            login.session.close()

    def fetch_snapshot(self, state, login):
        scraper = CourseScraper(login.token, session=login.session)
        info = scraper.fetch_semester_info()
        login.session.check()
        if not info:
            raise ServiceError("无法确认当前学期，本次未更新课表快照")
        teaching = scraper.fetch_teaching_state(info, observed_date=datetime.fromtimestamp(self.clock(), BEIJING).date())
        login.session.check()
        semester = teaching.get("semester_id")
        if not semester or (teaching.get("schedule_status") == "active" and not teaching.get("week_one_monday")):
            raise ServiceError("学校未提供可确认的学期信息，未更新课表快照")
        courses = scraper.fetch_course_data(semester_id=semester) if teaching.get("schedule_status") == "active" else []
        login.session.check()
        if courses is None:
            raise ServiceError("课表获取失败，本次未更新快照")
        state["course_cache"] = {"username": state["username"], "semester_id": semester,
                                 "courses": courses, "teaching": teaching, "fetched_at": self.clock()}
        return "本账号课表已预取，等待对应推送时段"


class WxSender:
    def __init__(self, token):
        if not token:
            raise ValueError("服务器未配置 WXPUSHER_APP_TOKEN")
        self.token = token

    def send(self, uid, content, summary, content_type=2):
        # Exactly one HTTP attempt. A read timeout can mean delivery already happened.
        try:
            response = requests.post("https://wxpusher.zjiecode.com/api/send/message", json={
                "appToken": self.token, "uids": [uid], "content": content,
                "summary": summary, "contentType": content_type, "verifyPayType": 0,
            }, timeout=(8, 12))
            if response.status_code != 200:
                raise ServiceError("推送服务响应异常，投递结果待确认", "unknown")
            result = response.json()
        except (requests.RequestException, ValueError):
            raise ServiceError("网络中断，投递结果待确认；不会自动重发", "unknown") from None
        items = result.get("data") if isinstance(result, dict) else None
        if result.get("code") != 1000 or not isinstance(items, list) or len(items) != 1:
            raise ServiceError("推送服务拒绝请求，请检查本校应用订阅或稍后重试")
        if items[0].get("code") != 1000:
            raise ServiceError("本校应用订阅无效，请重新订阅后再测试", "needs_binding")


def masked(value):
    return value[:3] + "***" + value[-3:] if len(value) > 6 else "***"
