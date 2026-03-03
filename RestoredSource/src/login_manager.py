import requests
import json
import datetime
from school_adapter import SCHOOL_CONFIG, encrypt_password
from logger import logger

class LoginManager:
    """
    处理教务系统的登录逻辑与Token获取
    """
    
    def __init__(self, config_manager=None):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        })
        self.token = None
        self.user_info = {}
        self.config_manager = config_manager
        self.used_cached_token = False

    def _validate_token(self, token):
        url = f"{SCHOOL_CONFIG['BASE_URL']}/teachingWeek?token={token}"
        try:
            resp = self.session.post(url, timeout=8)
            if resp.status_code >= 500:
                return None
            data = resp.json()
            if isinstance(data, dict) and ("nowWeek" in data):
                return True
            return False
        except requests.RequestException:
            return None
        except Exception:
            return False

    def _try_use_cached_token(self, username):
        if not self.config_manager:
            return False

        cached_username = self.config_manager.get("jw_cached_username", "")
        cached_token = self.config_manager.get("jw_cached_token", "")
        if not cached_token or not isinstance(cached_token, str):
            return False

        if cached_username and cached_username != username:
            self.config_manager.clear_jw_cached_token()
            return False

        cached_cookies = self.config_manager.get("jw_cached_cookies", {})
        if isinstance(cached_cookies, dict) and cached_cookies:
            try:
                self.session.cookies = requests.utils.cookiejar_from_dict(cached_cookies, cookiejar=self.session.cookies, overwrite=True)
            except Exception:
                pass

        valid = self._validate_token(cached_token)
        if valid is True:
            self.token = cached_token
            self.used_cached_token = True
            return True

        if valid is False:
            self.config_manager.clear_jw_cached_token()
            return False

        return False

    def login(self, username, password, use_cache=True):
        """
        执行登录操作
        :param username: 学号
        :param password: 密码
        :return: (success: bool, message: str)
        """
        if not username or not password:
            return False, "用户名或密码不能为空"

        if use_cache and self._try_use_cached_token(username):
            logger.info("教务登录：复用缓存Token")
            return True, "登录成功"

        encrypted_pwd = encrypt_password(password)
        if not encrypted_pwd:
            return False, "密码加密失败"

        # 构建登录URL
        login_url = f"{SCHOOL_CONFIG['LOGIN_URL']}?userNo={username}&pwd={encrypted_pwd}"

        try:
            # 发送登录请求 (POST)
            response = self.session.post(login_url, timeout=10)
            response.raise_for_status()
            
            # 解析响应
            data = response.json()
            msg = data.get("Msg", "")

            if "成功" in msg:
                token_data = data.get("data", {})
                self.token = token_data.get("token")
                
                # 保存用户信息
                self.user_info = {
                    "name": token_data.get("name"),
                    "academyName": token_data.get("academyName"),
                    "clsName": token_data.get("clsName")
                }
                
                if self.token:
                    if self.config_manager:
                        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        cookies_dict = {}
                        try:
                            cookies_dict = self.session.cookies.get_dict()
                        except Exception:
                            cookies_dict = {}
                        self.config_manager.update_jw_cached_token(username, self.token, now_str, cookies_dict=cookies_dict)
                    return True, "登录成功"
                else:
                    return False, "登录成功但未获取到Token"
            elif "错误" in msg:
                if self.config_manager:
                    self.config_manager.clear_jw_cached_token()
                return False, "账号或密码错误"
            else:
                return False, f"登录失败: {msg}"

        except requests.RequestException as e:
            return False, f"网络请求异常: {str(e)}"
        except json.JSONDecodeError:
            return False, "服务器响应解析失败"
        except Exception as e:
            return False, f"未知错误: {str(e)}"

    def get_token(self):
        return self.token

    def get_user_info(self):
        return self.user_info
