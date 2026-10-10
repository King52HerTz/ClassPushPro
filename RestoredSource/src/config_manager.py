import base64
import json
import os
import re
import time

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from app_paths import get_app_data_dir
from logger import logger

CONFIG_FILE = "config.json"
# Legacy desktop obfuscation only. Cloud credentials use a separate server AES-GCM key.
LOCAL_KEY = b'ClassPushConfigK'
DEFAULT_TIME_SLOTS = {
    "1-2": ["08:30", "10:05"], "3-4": ["10:25", "12:00"],
    "5-6": ["14:00", "15:35"], "7-8": ["15:55", "17:30"],
    "9-10": ["19:00", "20:35"], "11-12": ["20:45", "22:20"],
}
DEFAULT_CALENDAR_ALARM_MINUTES = 15


class ConfigManager:
    def __init__(self, config_path=None):
        self.config_path = config_path or os.path.join(get_app_data_dir(), CONFIG_FILE)
        self.config_data = {}
        self.load_config()

    def _encrypt(self, text):
        if not text:
            return ""
        cipher = AES.new(LOCAL_KEY, AES.MODE_ECB)
        return base64.b64encode(cipher.encrypt(pad(str(text).encode(), AES.block_size))).decode()

    def _decrypt(self, text):
        if not text:
            return ""
        try:
            cipher = AES.new(LOCAL_KEY, AES.MODE_ECB)
            return unpad(cipher.decrypt(base64.b64decode(text)), AES.block_size).decode()
        except (ValueError, UnicodeError):
            return ""

    def load_config(self):
        if not os.path.exists(self.config_path):
            return
        try:
            with open(self.config_path, encoding="utf-8") as handle:
                raw = json.load(handle)
            self.config_data = {
                key: self._decrypt(raw.get(key, ""))
                for key in ("username", "password", "jw_cached_token", "cached_courses_data")
            }
            # Cached courses are already encrypted when stored in memory.
            self.config_data["cached_courses_data"] = raw.get("cached_courses_data", "")
            for key in ("semester_start_date", "jw_cached_username", "jw_cached_time"):
                self.config_data[key] = str(raw.get(key, "") or "")
            cookie_text = self._decrypt(raw.get("jw_cached_cookies", ""))
            self.config_data["jw_cached_cookies"] = json.loads(cookie_text) if cookie_text else {}
            self.config_data["time_slots"] = self._normalize_time_slots(raw.get("time_slots"))
            self.config_data["calendar_alarm_minutes"] = self._normalize_calendar_alarm_minutes(raw.get("calendar_alarm_minutes", 15))
        except (OSError, ValueError, TypeError):
            logger.warning("本地配置读取失败，未使用其他账号缓存")
            self.config_data = {}

    def _save_current_config(self):
        raw = dict(self.config_data)
        for key in ("username", "password", "jw_cached_token"):
            raw[key] = self._encrypt(raw.get(key, ""))
        raw["jw_cached_cookies"] = self._encrypt(json.dumps(raw.get("jw_cached_cookies", {})))
        try:
            os.makedirs(os.path.dirname(os.path.abspath(self.config_path)), exist_ok=True)
            temporary = self.config_path + ".tmp"
            with open(temporary, "w", encoding="utf-8") as handle:
                json.dump(raw, handle, ensure_ascii=False, indent=2)
            os.replace(temporary, self.config_path)
            return True
        except OSError:
            logger.warning("本地配置保存失败")
            return False

    def save_config(self, username, password, semester_start_date="", time_slots=None, calendar_alarm_minutes=15):
        if username != self.get("username", "") or password != self.get("password", ""):
            self.config_data = {}
        self.config_data.update(
            username=username or "", password=password or "",
            semester_start_date=semester_start_date or "",
            time_slots=self._normalize_time_slots(time_slots),
            calendar_alarm_minutes=self._normalize_calendar_alarm_minutes(calendar_alarm_minutes),
        )
        return self._save_current_config()

    def get(self, key, default=None):
        return self.config_data.get(key, default)

    def _normalize_time_slots(self, value=None):
        result = {key: list(slot) for key, slot in DEFAULT_TIME_SLOTS.items()}
        if isinstance(value, dict):
            for key, slot in value.items():
                if isinstance(slot, (list, tuple)) and len(slot) == 2:
                    if all(re.fullmatch(r"(?:[01][0-9]|2[0-3]):[0-5][0-9]", str(clock)) for clock in slot) and slot[0] < slot[1]:
                        result[str(key)] = list(slot)
        return result

    def _normalize_calendar_alarm_minutes(self, value):
        try:
            return max(0, min(1440, int(value)))
        except (ValueError, TypeError):
            return 15

    def update_jw_cached_token(self, username, token, time_str, cookies_dict=None):
        # login_test uses no config, so never save another student's temporary token.
        if username != self.get("username"):
            return False
        self.config_data.update(jw_cached_username=username, jw_cached_token=token,
                                jw_cached_time=time_str, jw_cached_cookies=cookies_dict or {})
        return self._save_current_config()

    def clear_jw_cached_token(self):
        self.config_data.update(jw_cached_username="", jw_cached_token="", jw_cached_time="", jw_cached_cookies={})
        return self._save_current_config()

    def save_cached_courses(self, courses, current_week=None, semester_id="", teaching_state=None):
        if not isinstance(courses, list):
            return False
        state = teaching_state or {}
        snapshot = {
            "owner": self.get("username", ""), "school": "hnit",
            "update_time": int(time.time()), "current_week": str(current_week or ""),
            "semester_id": semester_id or "", "week_one_monday": state.get("week_one_monday", ""),
            "teaching_state": state, "courses": courses,
        }
        self.config_data["cached_courses_data"] = self._encrypt(json.dumps(snapshot, ensure_ascii=False))
        return self._save_current_config()

    def get_cached_courses(self):
        try:
            text = self._decrypt(self.get("cached_courses_data", ""))
            snapshot = json.loads(text) if text else None
            if snapshot and snapshot.get("owner") == self.get("username") and snapshot.get("school") == "hnit":
                return snapshot
        except (ValueError, TypeError):
            pass
        return None
