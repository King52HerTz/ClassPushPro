"""One school HTTP lane shared by API and worker; no credentials in its state."""
import math
import time
from email.utils import parsedate_to_datetime

import requests


class ServiceError(Exception):
    def __init__(self, message, status="failed", retry_after=0):
        super().__init__(message)
        self.status, self.retry_after = status, retry_after


class SchoolGate:
    INTERVAL = 3
    QUEUE_TIMEOUT = 15

    def __init__(self, store, clock=time.time, sleep=time.sleep):
        self.store, self.clock, self.sleep = store, clock, sleep

    def retry_seconds(self, value):
        try:
            seconds = int(value)
        except (TypeError, ValueError, OverflowError):
            try:
                seconds = math.ceil(parsedate_to_datetime(value).timestamp() - self.clock())
            except (TypeError, ValueError, OverflowError):
                seconds = 900
        return max(900, seconds)

    def perform(self, operation):
        try:
            with self.store.lock("school-http", timeout=self.QUEUE_TIMEOUT):
                with self.store.db() as db:
                    state = db.execute("SELECT * FROM school_outbound WHERE id=1").fetchone()
                if state["cooldown_until"] > self.clock():
                    remaining = math.ceil(state["cooldown_until"] - self.clock())
                    raise ServiceError("教务请求保护暂停中，请稍后再试", "deferred", remaining)
                wait = max(0, state["next_request"] - self.clock())
                if wait > self.QUEUE_TIMEOUT:
                    raise ServiceError("教务查询队列繁忙，请稍后再试", "deferred", math.ceil(wait))
                self.sleep(wait)
                with self.store.db() as db:
                    db.execute("UPDATE school_outbound SET next_request=? WHERE id=1", (self.clock() + self.INTERVAL,))
                try:
                    response = operation()
                except requests.RequestException:
                    self.failure()
                    raise ServiceError("教务网络异常，本次查询已停止；请稍后重试", "deferred", 60) from None
                if response.status_code in (403, 429):
                    seconds = 3600 if response.status_code == 403 else self.retry_seconds(response.headers.get("Retry-After"))
                    with self.store.db() as db:
                        db.execute("UPDATE school_outbound SET cooldown_until=? WHERE id=1", (self.clock() + seconds,))
                    raise ServiceError("教务限制访问，已暂停查询；请稍后或联系管理员确认", "deferred", seconds)
                if response.status_code >= 400 or 300 <= response.status_code < 400:
                    self.failure()
                    raise ServiceError("教务响应异常，本次查询已停止", "deferred", 60)
                try:
                    response.json()
                except ValueError:
                    self.failure()
                    raise ServiceError("教务返回非预期页面，本次查询已停止；如需验证码请人工确认", "deferred", 60) from None
                with self.store.db() as db:
                    db.execute("UPDATE school_outbound SET failures=0 WHERE id=1")
                return response
        except TimeoutError:
            raise ServiceError("教务查询队列繁忙，请稍后再试", "deferred", 60) from None

    def failure(self):
        with self.store.db() as db:
            db.execute("UPDATE school_outbound SET failures=failures+1 WHERE id=1")
            db.execute("UPDATE school_outbound SET cooldown_until=? WHERE id=1 AND failures>=3", (self.clock() + 900,))


class SchoolSession(requests.Session):
    def __init__(self, gate):
        super().__init__()
        self.gate = gate
        self.blocked_error = None

    def request(self, method, url, **kwargs):
        if self.blocked_error:
            raise self.blocked_error
        # Redirects would bypass the lane, and retries could turn token failure into a login storm.
        kwargs.update(timeout=(6, 12), allow_redirects=False)
        try:
            return self.gate.perform(lambda: super(SchoolSession, self).request(method, url, **kwargs))
        except ServiceError as exc:
            self.blocked_error = exc
            raise

    def check(self):
        # Legacy scrapers sometimes catch broad exceptions and return empty data.
        if self.blocked_error:
            raise self.blocked_error
