import requests
import json
import time
from requests.adapters import HTTPAdapter
from logger import logger

try:
    from urllib3.util.retry import Retry
except Exception:
    Retry = None

class Pusher:
    """
    负责将消息推送到 WxPusher
    """
    BASE_URL = "https://wxpusher.zjiecode.com/api/send/message"

    def __init__(self, app_token):
        self.app_token = app_token
        self.session = requests.Session()

        if Retry:
            # 用 Retry 兜底网络抖动/服务端 5xx，避免一次失败就丢消息
            # 兼容旧版本 urllib3 (使用 method_whitelist 而不是 allowed_methods)
            # 注意：某些极老版本的 urllib3 或被其他库 patch 过的版本，
            # inspect.signature 可能不准确或行为异常。
            # 这里采用更稳妥的 try-except 方式探测。
            
            base_params = {
                "total": 3,
                "connect": 3,
                "read": 3,
                "status": 3,
                "backoff_factor": 1,
                "status_forcelist": (500, 502, 503, 504),
                "raise_on_status": False,
                "respect_retry_after_header": False,
            }
            
            try:
                # 优先尝试新参数名
                retry = Retry(**base_params, allowed_methods=frozenset(["POST"]))
            except TypeError:
                # 如果报错，说明不支持 allowed_methods，尝试旧参数名
                retry = Retry(**base_params, method_whitelist=frozenset(["POST"]))
                
            adapter = HTTPAdapter(max_retries=retry)
            self.session.mount("https://", adapter)
            self.session.mount("http://", adapter)

    def send(self, uids, content, summary="课程提醒", content_type=3):
        """
        发送消息
        :param uids: 用户UID列表 (List[str])
        :param content: 消息内容 (Markdown/HTML)
        :param summary: 摘要
        :param content_type: 内容类型 1=Text, 2=HTML, 3=Markdown
        :return: (success: bool, msg: str)
        """
        if not uids or not content:
            return False, "UID或内容为空"

        if not isinstance(uids, (list, tuple)):
            return False, "UID参数类型无效"
        if not isinstance(content, str) or not content.strip():
            return False, "内容参数无效"

        safe_uids = [u for u in uids if isinstance(u, str) and u.strip()]
        if not safe_uids:
            return False, "UID或内容为空"

        # 增加随机摘要，防止 WxPusher 平台级去重
        # WxPusher 如果在短时间内收到完全相同的 summary 和 content，可能会拦截重复消息
        # 即使我们在 run_job.py 里做了去重，但在强制推送时，内容可能一样
        import random
        random_suffix = f"_{int(time.time())}_{random.randint(100, 999)}"
        # 注意：WxPusher 的 verifyPayLoad 字段如果不一样，就不算重复
        # 或者我们直接在 summary 后面加个不可见字符或随机数（如果是测试模式）
        # 这里直接改 content 也许更稳妥，或者利用 verifyPayType=0 不验证
        
        # 简单方案：在 HTML 尾部追加一个注释时间戳，确保每次 content 不同
        if content_type == 2: # HTML
            content += f"<!-- ts: {random_suffix} -->"
        elif content_type == 3: # Markdown
            content += f"\n\n[ts]: # ({random_suffix})"

        payload = {
            "appToken": self.app_token,
            "content": content,
            "summary": summary,
            "contentType": content_type,
            "uids": safe_uids,
            "verifyPayType": 0 # 0=不验证重复 (默认是0，但显式指定更保险)
        }

        try:
            last_error_msg = ""
            for attempt in range(4):
                try:
                    resp = self.session.post(self.BASE_URL, json=payload, timeout=10)
                except requests.RequestException as e:
                    logger.warning(f"推送失败(网络异常): {e.__class__.__name__}")
                    return False, f"网络错误: {e}"

                if resp.status_code >= 500:
                    logger.warning(f"推送失败(服务端异常): HTTP {resp.status_code}")
                    return False, f"服务端错误: HTTP {resp.status_code}"

                try:
                    data = resp.json()
                    # 记录详细响应以便调试
                    logger.info(f"WxPusher响应: {json.dumps(data, ensure_ascii=False)}")
                except Exception:
                    last_error_msg = "返回解析失败"
                else:
                    if data.get("code") == 1000:
                        # 检查 data 里的具体状态
                        invalid_list = []
                        for item in data.get("data", []):
                            if item.get("code") != 1000:
                                invalid_list.append(f"{item.get('uid')}: {item.get('status')}")
                        
                        if invalid_list:
                            err_detail = "; ".join(invalid_list)
                            logger.warning(f"部分UID推送失败: {err_detail}")
                            return False, f"部分失败: {err_detail}"
                            
                        return True, "发送成功"
                    last_error_msg = str(data.get("msg") or "未知错误")

                # WxPusher 返回非 1000 时也按退避重试，提升瞬时故障成功率
                if attempt < 3:
                    time.sleep(2 ** attempt)

            return False, f"发送失败: {last_error_msg}"
        except Exception as e:
            logger.error(f"推送异常: {e}")
            return False, f"网络错误: {e}"
