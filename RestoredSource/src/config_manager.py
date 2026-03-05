import json
import os
import base64
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from logger import logger

CONFIG_FILE = "config.json"
# 使用一个本地固定的密钥用于加密配置文件
# 注意：这只是为了防止明文存储，并不是极高强度的安全方案
LOCAL_KEY = b'ClassPushConfigK'  # 16 bytes key

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
                "last_push_success_time": encrypted_data.get("last_push_success_time", ""),
                "last_auto_push_success_time": encrypted_data.get("last_auto_push_success_time", ""),
                "last_manual_push_success_time": encrypted_data.get("last_manual_push_success_time", ""),
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

    def save_config(self, username, password, app_token, uid, push_time, auto_start):
        old_username = self.config_data.get("username", "")
        old_password = self.config_data.get("password", "")
        keep_jw_cache = isinstance(username, str) and isinstance(password, str) and (username == old_username) and (password == old_password)
        jw_cached_username = self.config_data.get("jw_cached_username", "") if keep_jw_cache else ""
        jw_cached_token = self.config_data.get("jw_cached_token", "") if keep_jw_cache else ""
        jw_cached_time = self.config_data.get("jw_cached_time", "") if keep_jw_cache else ""
        jw_cached_cookies = self.config_data.get("jw_cached_cookies", {}) if keep_jw_cache else {}

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
            "last_push_success_time": self.config_data.get("last_push_success_time", ""),
            "last_auto_push_success_time": self.config_data.get("last_auto_push_success_time", ""),
            "last_manual_push_success_time": self.config_data.get("last_manual_push_success_time", ""),
            "last_ignored_push_date": self.config_data.get("last_ignored_push_date", ""),
            "jw_cached_username": jw_cached_username,
            "jw_cached_token": self._encrypt(jw_cached_token),
            "jw_cached_time": jw_cached_time,
            "jw_cached_cookies": self._encrypt(json.dumps(jw_cached_cookies or {}, ensure_ascii=False))
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

    def update_last_ignored_date(self, date_str):
        """更新上次忽略推送的日期 (YYYY-MM-DD)"""
        self.config_data["last_ignored_push_date"] = date_str
        self._save_current_config()
        return True

    def _save_current_config(self):
        """保存当前内存中的配置到文件"""
        encrypted_data = {
            "username": self._encrypt(self.config_data.get("username", "")),
            "password": self._encrypt(self.config_data.get("password", "")),
            "app_token": self._encrypt(self.config_data.get("app_token", "")),
            "uid": self._encrypt(self.config_data.get("uid", "")),
            "push_time": self.config_data.get("push_time", "07:00"),
            "auto_start": self.config_data.get("auto_start", False),
            "last_push_success_time": self.config_data.get("last_push_success_time", ""),
            "last_auto_push_success_time": self.config_data.get("last_auto_push_success_time", ""),
            "last_manual_push_success_time": self.config_data.get("last_manual_push_success_time", ""),
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
            # 只有 username, password, app_token, uid 这几个核心字段支持从环境变量读取
            if key in ["username", "password", "app_token", "uid", "push_time"]:
                return env_val
        
        # 2. 回退到读取本地配置
        return self.config_data.get(key, default)

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

    def save_cached_courses(self, courses, current_week):
        """保存课表到本地缓存"""
        if not isinstance(courses, list):
            return False
        
        import time
        cache_data = {
            "update_time": int(time.time()),
            "current_week": str(current_week),
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
