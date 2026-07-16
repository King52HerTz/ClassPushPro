import json
import os
import base64
import re
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from logger import logger

CONFIG_FILE = "config.json"
# 使用一个本地固定的密钥用于加密配置文件
# 注意：这只是为了防止明文存储，并不是极高强度的安全方案
LOCAL_KEY = b'ClassPushConfigK'  # 16 bytes key

DEFAULT_TIME_SLOTS = {
    "1-2": ["08:30", "10:05"],
    "3-4": ["10:25", "12:00"],
    "5-6": ["14:00", "15:35"],
    "7-8": ["15:55", "17:30"],
    "9-10": ["19:00", "20:35"],
    "11-12": ["20:45", "22:20"],
}

DEFAULT_CALENDAR_ALARM_MINUTES = 15
DEFAULT_GRADE_CHECK_INTERVAL_MINUTES = 30
DEFAULT_GRADE_CHECK_START_TIME = "07:00"
DEFAULT_GRADE_CHECK_END_TIME = "23:00"

class ConfigManager:
    """
    负责配置文件的读写与加密存储
    """
    def __init__(self, config_path=None):
        if config_path:
            self.config_path = config_path
        else:
            # 默认存储在用户目录下的 .ClassPush 文件夹
            app_data = os.path.join(os.path.expanduser("~"), ".ClassPush")
            os.makedirs(app_data, exist_ok=True)
            self.config_path = os.path.join(app_data, CONFIG_FILE)
            
        logger.info(f"Config file path: {self.config_path}")
        
        self.config_data = {}
        self.load_config()

    def _encrypt(self, text):
        if not text: return ""
        try:
            cipher = AES.new(LOCAL_KEY, AES.MODE_ECB)
            encrypted = cipher.encrypt(pad(text.encode('utf-8'), AES.block_size))
            return base64.b64encode(encrypted).decode('utf-8')
        except:
            return text

    def _decrypt(self, text):
        if not text: return ""
        try:
            cipher = AES.new(LOCAL_KEY, AES.MODE_ECB)
            decrypted = unpad(cipher.decrypt(base64.b64decode(text)), AES.block_size)
            return decrypted.decode('utf-8')
        except:
            return text

    def load_config(self):
        if not os.path.exists(self.config_path):
            self.config_data = {}
            return
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                encrypted_data = json.load(f)
            
            # 解密敏感字段
            self.config_data = {
                "username": self._decrypt(encrypted_data.get("username", "")).strip(),
                "password": self._decrypt(encrypted_data.get("password", "")).strip(),
                "app_token": self._decrypt(encrypted_data.get("app_token", "")).strip(),
                "uid": self._decrypt(encrypted_data.get("uid", "")).strip(),
                "push_time": encrypted_data.get("push_time", "07:00"),
                "auto_start": encrypted_data.get("auto_start", False),
                "weather_enabled": encrypted_data.get("weather_enabled", False),
                "weather_city": str(encrypted_data.get("weather_city", "") or "").strip(),
                "weather_credential_id": str(encrypted_data.get("weather_credential_id", "") or "").strip(),
                "weather_api_host": str(encrypted_data.get("weather_api_host", "") or "").strip(),
                "weather_api_key": self._decrypt(encrypted_data.get("weather_api_key", "")).strip(),
                "grade_push_enabled": encrypted_data.get("grade_push_enabled", False),
                "grade_check_interval_minutes": self._normalize_grade_check_interval_minutes(
                    encrypted_data.get("grade_check_interval_minutes", DEFAULT_GRADE_CHECK_INTERVAL_MINUTES)
                ),
                "grade_check_start_time": self._normalize_clock_time(
                    encrypted_data.get("grade_check_start_time", DEFAULT_GRADE_CHECK_START_TIME),
                    DEFAULT_GRADE_CHECK_START_TIME,
                ),
                "grade_check_end_time": self._normalize_clock_time(
                    encrypted_data.get("grade_check_end_time", DEFAULT_GRADE_CHECK_END_TIME),
                    DEFAULT_GRADE_CHECK_END_TIME,
                ),
                "grade_push_initialized": bool(encrypted_data.get("grade_push_initialized", False)),
                "semester_start_date": encrypted_data.get("semester_start_date", ""),
                "time_slots": self._normalize_time_slots(encrypted_data.get("time_slots")),
                "calendar_alarm_minutes": self._normalize_calendar_alarm_minutes(
                    encrypted_data.get("calendar_alarm_minutes", DEFAULT_CALENDAR_ALARM_MINUTES)
                ),
                "last_push_success_time": encrypted_data.get("last_push_success_time", ""),
                "last_auto_push_success_time": encrypted_data.get("last_auto_push_success_time", ""),
                "last_manual_push_success_time": encrypted_data.get("last_manual_push_success_time", ""),
                "successful_schedule_push_keys": self._normalize_schedule_push_keys(
                    encrypted_data.get("successful_schedule_push_keys", [])
                ),
                "last_ignored_push_date": encrypted_data.get("last_ignored_push_date", ""),
                "jw_cached_username": encrypted_data.get("jw_cached_username", ""),
                "jw_cached_token": self._decrypt(encrypted_data.get("jw_cached_token", "")),
                "jw_cached_time": encrypted_data.get("jw_cached_time", ""),
                "jw_cached_cookies": self._decrypt(encrypted_data.get("jw_cached_cookies", "")),
                "cached_courses_data": encrypted_data.get("cached_courses_data", "")
            }

            if isinstance(self.config_data.get("jw_cached_cookies"), str):
                try:
                    self.config_data["jw_cached_cookies"] = json.loads(self.config_data["jw_cached_cookies"] or "{}")
                except Exception:
                    self.config_data["jw_cached_cookies"] = {}
        except Exception as e:
            logger.exception("配置文件加载失败")
            self.config_data = {}

    def save_config(
        self,
        username,
        password,
        app_token,
        uid,
        push_time,
        auto_start,
        semester_start_date="",
        time_slots=None,
        calendar_alarm_minutes=DEFAULT_CALENDAR_ALARM_MINUTES,
        weather_enabled=None,
        weather_city=None,
        weather_credential_id=None,
        weather_api_host=None,
        weather_api_key=None,
        grade_push_enabled=None,
        grade_check_interval_minutes=None,
        grade_check_start_time=None,
        grade_check_end_time=None,
        grade_push_initialized=None,
    ):
        old_username = self.config_data.get("username", "")
        old_password = self.config_data.get("password", "")
        keep_jw_cache = isinstance(username, str) and isinstance(password, str) and (username == old_username) and (password == old_password)
        jw_cached_username = self.config_data.get("jw_cached_username", "") if keep_jw_cache else ""
        jw_cached_token = self.config_data.get("jw_cached_token", "") if keep_jw_cache else ""
        jw_cached_time = self.config_data.get("jw_cached_time", "") if keep_jw_cache else ""
        jw_cached_cookies = self.config_data.get("jw_cached_cookies", {}) if keep_jw_cache else {}
        normalized_time_slots = self._normalize_time_slots(time_slots)
        normalized_alarm_minutes = self._normalize_calendar_alarm_minutes(calendar_alarm_minutes)
        normalized_weather_enabled = self.config_data.get("weather_enabled", False) if weather_enabled is None else bool(weather_enabled)
        normalized_weather_city = (
            str(self.config_data.get("weather_city", "") or "").strip()
            if weather_city is None else str(weather_city or "").strip()
        )
        normalized_weather_credential_id = (
            str(self.config_data.get("weather_credential_id", "") or "").strip()
            if weather_credential_id is None else str(weather_credential_id or "").strip()
        )
        normalized_weather_api_host = (
            str(self.config_data.get("weather_api_host", "") or "").strip()
            if weather_api_host is None else str(weather_api_host or "").strip()
        )
        normalized_weather_api_key = (
            str(self.config_data.get("weather_api_key", "") or "").strip()
            if weather_api_key is None else str(weather_api_key or "").strip()
        )
        normalized_grade_push_enabled = self.config_data.get("grade_push_enabled", False) if grade_push_enabled is None else bool(grade_push_enabled)
        normalized_grade_check_interval = self._normalize_grade_check_interval_minutes(
            self.config_data.get("grade_check_interval_minutes", DEFAULT_GRADE_CHECK_INTERVAL_MINUTES)
            if grade_check_interval_minutes is None else grade_check_interval_minutes
        )
        normalized_grade_check_start = self._normalize_clock_time(
            self.config_data.get("grade_check_start_time", DEFAULT_GRADE_CHECK_START_TIME)
            if grade_check_start_time is None else grade_check_start_time,
            DEFAULT_GRADE_CHECK_START_TIME,
        )
        normalized_grade_check_end = self._normalize_clock_time(
            self.config_data.get("grade_check_end_time", DEFAULT_GRADE_CHECK_END_TIME)
            if grade_check_end_time is None else grade_check_end_time,
            DEFAULT_GRADE_CHECK_END_TIME,
        )
        normalized_grade_push_initialized = (
            bool(self.config_data.get("grade_push_initialized", False))
            if grade_push_initialized is None else bool(grade_push_initialized)
        )

        # 强制兜底：如果前端传了空 Token，且配置文件中没有有效 Token，则自动补上默认的那个真实 Token
        # 这解决了前端界面隐藏 Token 后，保存时把空字符串传过来覆盖掉正确 Token 的问题
        if not app_token:
            # 先尝试用旧配置里的 Token
            current_token = self.config_data.get("app_token", "")
            if current_token:
                app_token = current_token
            else:
                 # 如果旧配置也没有，就用默认的硬编码 Token
                app_token = "AT_Xmbnkx7s8q8SvUiNMtk24FlDnXCKiT9e"

        encrypted_data = {
            "username": self._encrypt(username),
            "password": self._encrypt(password),
            "app_token": self._encrypt(app_token),
            "uid": self._encrypt(uid),
            "push_time": push_time,
            "auto_start": auto_start,
            "weather_enabled": normalized_weather_enabled,
            "weather_city": normalized_weather_city,
            "weather_credential_id": normalized_weather_credential_id,
            "weather_api_host": normalized_weather_api_host,
            "weather_api_key": self._encrypt(normalized_weather_api_key),
            "grade_push_enabled": normalized_grade_push_enabled,
            "grade_check_interval_minutes": normalized_grade_check_interval,
            "grade_check_start_time": normalized_grade_check_start,
            "grade_check_end_time": normalized_grade_check_end,
            "grade_push_initialized": normalized_grade_push_initialized,
            "semester_start_date": str(semester_start_date or "").strip(),
            "time_slots": normalized_time_slots,
            "calendar_alarm_minutes": normalized_alarm_minutes,
            "last_push_success_time": self.config_data.get("last_push_success_time", ""),
            "last_auto_push_success_time": self.config_data.get("last_auto_push_success_time", ""),
            "last_manual_push_success_time": self.config_data.get("last_manual_push_success_time", ""),
            "successful_schedule_push_keys": self._normalize_schedule_push_keys(
                self.config_data.get("successful_schedule_push_keys", [])
            ),
            "last_ignored_push_date": self.config_data.get("last_ignored_push_date", ""),
            "jw_cached_username": jw_cached_username,
            "jw_cached_token": self._encrypt(jw_cached_token),
            "jw_cached_time": jw_cached_time,
            "jw_cached_cookies": self._encrypt(json.dumps(jw_cached_cookies or {}, ensure_ascii=False)),
            "cached_courses_data": self.config_data.get("cached_courses_data", ""),
        }
        
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(encrypted_data, f, indent=4)
            # 更新内存中的配置
            self.load_config()
            return True
        except Exception as e:
            logger.exception("配置文件保存失败")
            return False

    def update_last_push_time(self, timestamp_str):
        """更新上次成功推送时间"""
        self.config_data["last_push_success_time"] = timestamp_str
        self._save_current_config()
        return True

    def update_last_auto_push_time(self, timestamp_str):
        if not isinstance(timestamp_str, str) or not timestamp_str:
            return False
        self.config_data["last_auto_push_success_time"] = timestamp_str
        return self._save_current_config()

    def update_last_manual_push_time(self, timestamp_str):
        if not isinstance(timestamp_str, str) or not timestamp_str:
            return False
        self.config_data["last_manual_push_success_time"] = timestamp_str
        return self._save_current_config()

    @staticmethod
    def _normalize_schedule_push_keys(value):
        if not isinstance(value, list):
            return []
        normalized = []
        for item in value:
            key = str(item or "").strip()
            if re.fullmatch(r"(?:morning|night):\d{4}-\d{2}-\d{2}", key) and key not in normalized:
                normalized.append(key)
        return normalized[-32:]

    def has_successful_schedule_push(self, push_key):
        return push_key in self._normalize_schedule_push_keys(
            self.config_data.get("successful_schedule_push_keys", [])
        )

    def mark_successful_schedule_push(self, push_key):
        normalized_key = str(push_key or "").strip()
        if not re.fullmatch(r"(?:morning|night):\d{4}-\d{2}-\d{2}", normalized_key):
            return False
        keys = self._normalize_schedule_push_keys(
            self.config_data.get("successful_schedule_push_keys", [])
        )
        keys = [key for key in keys if key != normalized_key]
        keys.append(normalized_key)
        self.config_data["successful_schedule_push_keys"] = keys[-32:]
        return self._save_current_config()

    def update_last_ignored_date(self, date_str):
        """更新上次忽略推送的日期 (YYYY-MM-DD)"""
        self.config_data["last_ignored_push_date"] = date_str
        self._save_current_config()
        return True

    def update_grade_push_enabled(self, enabled):
        self.config_data["grade_push_enabled"] = bool(enabled)
        return self._save_current_config()

    def update_grade_push_settings(self, enabled=None, interval_minutes=None, start_time=None, end_time=None):
        if enabled is not None:
            self.config_data["grade_push_enabled"] = bool(enabled)
        if interval_minutes is not None:
            self.config_data["grade_check_interval_minutes"] = self._normalize_grade_check_interval_minutes(interval_minutes)
        if start_time is not None:
            self.config_data["grade_check_start_time"] = self._normalize_clock_time(start_time, DEFAULT_GRADE_CHECK_START_TIME)
        if end_time is not None:
            self.config_data["grade_check_end_time"] = self._normalize_clock_time(end_time, DEFAULT_GRADE_CHECK_END_TIME)
        return self._save_current_config()

    def update_grade_push_initialized(self, initialized):
        self.config_data["grade_push_initialized"] = bool(initialized)
        return self._save_current_config()

    def _save_current_config(self):
        """保存当前内存中的配置到文件"""
        encrypted_data = {
            "username": self._encrypt(self.config_data.get("username", "")),
            "password": self._encrypt(self.config_data.get("password", "")),
            "app_token": self._encrypt(self.config_data.get("app_token", "")),
            "uid": self._encrypt(self.config_data.get("uid", "")),
            "push_time": self.config_data.get("push_time", "07:00"),
            "auto_start": self.config_data.get("auto_start", False),
            "weather_enabled": bool(self.config_data.get("weather_enabled", False)),
            "weather_city": str(self.config_data.get("weather_city", "") or "").strip(),
            "weather_credential_id": str(self.config_data.get("weather_credential_id", "") or "").strip(),
            "weather_api_host": str(self.config_data.get("weather_api_host", "") or "").strip(),
            "weather_api_key": self._encrypt(self.config_data.get("weather_api_key", "")),
            "grade_push_enabled": self.config_data.get("grade_push_enabled", False),
            "grade_check_interval_minutes": self._normalize_grade_check_interval_minutes(
                self.config_data.get("grade_check_interval_minutes", DEFAULT_GRADE_CHECK_INTERVAL_MINUTES)
            ),
            "grade_check_start_time": self._normalize_clock_time(
                self.config_data.get("grade_check_start_time", DEFAULT_GRADE_CHECK_START_TIME),
                DEFAULT_GRADE_CHECK_START_TIME,
            ),
            "grade_check_end_time": self._normalize_clock_time(
                self.config_data.get("grade_check_end_time", DEFAULT_GRADE_CHECK_END_TIME),
                DEFAULT_GRADE_CHECK_END_TIME,
            ),
            "grade_push_initialized": bool(self.config_data.get("grade_push_initialized", False)),
            "semester_start_date": self.config_data.get("semester_start_date", ""),
            "time_slots": self._normalize_time_slots(self.config_data.get("time_slots")),
            "calendar_alarm_minutes": self._normalize_calendar_alarm_minutes(
                self.config_data.get("calendar_alarm_minutes", DEFAULT_CALENDAR_ALARM_MINUTES)
            ),
            "last_push_success_time": self.config_data.get("last_push_success_time", ""),
            "last_auto_push_success_time": self.config_data.get("last_auto_push_success_time", ""),
            "last_manual_push_success_time": self.config_data.get("last_manual_push_success_time", ""),
            "successful_schedule_push_keys": self._normalize_schedule_push_keys(
                self.config_data.get("successful_schedule_push_keys", [])
            ),
            "last_ignored_push_date": self.config_data.get("last_ignored_push_date", ""),
            "jw_cached_username": self.config_data.get("jw_cached_username", ""),
            "jw_cached_token": self._encrypt(self.config_data.get("jw_cached_token", "")),
            "jw_cached_time": self.config_data.get("jw_cached_time", ""),
            "jw_cached_cookies": self._encrypt(json.dumps(self.config_data.get("jw_cached_cookies", {}) or {}, ensure_ascii=False)),
            "cached_courses_data": self.config_data.get("cached_courses_data", "")
        }
        
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(encrypted_data, f, indent=4)
            return True
        except Exception as e:
            logger.exception("配置保存失败")
            return False

    def get(self, key, default=None):
        # 1. 优先尝试从环境变量获取 (适配 GitHub Actions)
        # 环境变量命名规则: CP_大写KEY，例如 CP_USERNAME, CP_PASSWORD
        env_key = f"CP_{key.upper()}"
        env_val = os.getenv(env_key)
        if env_val:
            if key in [
                "username", "password", "app_token", "uid", "push_time",
                "weather_api_key", "weather_api_host", "weather_credential_id",
                "grade_check_start_time", "grade_check_end_time",
            ]:
                return env_val
            if key in ["grade_push_enabled", "weather_enabled"]:
                return env_val.strip().lower() in {"1", "true", "yes", "on"}
            if key in ["grade_check_interval_minutes"]:
                try:
                    return int(env_val)
                except ValueError:
                    pass
        
        # 2. 回退到读取本地配置
        return self.config_data.get(key, default)

    def _normalize_time_slots(self, raw_time_slots=None):
        normalized = {}
        source = raw_time_slots if isinstance(raw_time_slots, dict) else {}

        for slot_key, default_value in DEFAULT_TIME_SLOTS.items():
            candidate = source.get(slot_key, default_value)
            if isinstance(candidate, (list, tuple)) and len(candidate) >= 2:
                start_time = str(candidate[0] or "").strip() or default_value[0]
                end_time = str(candidate[1] or "").strip() or default_value[1]
            else:
                start_time, end_time = default_value
            normalized[slot_key] = [start_time, end_time]

        for slot_key, candidate in source.items():
            if slot_key in normalized:
                continue
            if isinstance(candidate, (list, tuple)) and len(candidate) >= 2:
                normalized[str(slot_key)] = [
                    str(candidate[0] or "").strip(),
                    str(candidate[1] or "").strip(),
                ]

        return normalized

    def _normalize_calendar_alarm_minutes(self, value):
        try:
            minutes = int(value)
        except (TypeError, ValueError):
            return DEFAULT_CALENDAR_ALARM_MINUTES

        if minutes < 0:
            return 0
        if minutes > 24 * 60:
            return 24 * 60
        return minutes

    def _normalize_grade_check_interval_minutes(self, value):
        try:
            minutes = int(value)
        except (TypeError, ValueError):
            return DEFAULT_GRADE_CHECK_INTERVAL_MINUTES

        if minutes <= 0:
            return DEFAULT_GRADE_CHECK_INTERVAL_MINUTES
        return minutes

    def _normalize_clock_time(self, value, fallback):
        text = str(value or "").strip()
        if not re.match(r"^\d{2}:\d{2}$", text):
            return fallback
        hour, minute = map(int, text.split(":"))
        if hour < 0 or hour > 23 or minute < 0 or minute > 59:
            return fallback
        return f"{hour:02d}:{minute:02d}"

    def update_jw_cached_token(self, username, token, time_str, cookies_dict=None):
        if not isinstance(username, str) or not username:
            return False
        if not isinstance(token, str) or not token:
            return False
        if not isinstance(time_str, str) or not time_str:
            return False

        self.config_data["jw_cached_username"] = username
        self.config_data["jw_cached_token"] = token
        self.config_data["jw_cached_time"] = time_str
        if isinstance(cookies_dict, dict):
            self.config_data["jw_cached_cookies"] = cookies_dict
        return self._save_current_config()

    def clear_jw_cached_token(self):
        self.config_data["jw_cached_username"] = ""
        self.config_data["jw_cached_token"] = ""
        self.config_data["jw_cached_time"] = ""
        self.config_data["jw_cached_cookies"] = {}
        return self._save_current_config()

    def save_cached_courses(self, courses, current_week=None, semester_id="", teaching_state=None):
        """保存课表到本地缓存"""
        if not isinstance(courses, list):
            return False
        
        import time
        cache_data = {
            "update_time": int(time.time()),
            "current_week": str(current_week or ""),
            "semester_id": str(semester_id or ""),
            "week_one_monday": str((teaching_state or {}).get("week_one_monday", "")),
            "teaching_state": teaching_state if isinstance(teaching_state, dict) else {},
            "courses": courses
        }
        
        # 加密存储整个结构
        self.config_data["cached_courses_data"] = self._encrypt(json.dumps(cache_data, ensure_ascii=False))
        return self._save_current_config()

    def get_cached_courses(self):
        """获取本地缓存的课表"""
        encrypted = self.config_data.get("cached_courses_data", "")
        if not encrypted:
            return None
            
        try:
            json_str = self._decrypt(encrypted)
            if not json_str:
                return None
            return json.loads(json_str)
        except Exception:
            return None
