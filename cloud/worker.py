import base64
import logging
import os
import time
import hashlib
from datetime import datetime, timedelta

from .service import BEIJING, SchoolService, ServiceError, WxSender
from .store import Store

log = logging.getLogger("classpush.cloud.worker")


def due_slots(now):
    local = datetime.fromtimestamp(now, BEIJING)
    result = []
    for kind, hour, minute in [("prepare_morning", 6, 0), ("morning", 7, 0),
                               ("prepare_evening", 19, 0), ("evening", 20, 0),
                               *[("grades", hour, 30) for hour in (8, 13, 21)]]:
        start = local.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if 0 <= now - start.timestamp() < 45 * 60:
            target = local.date() + timedelta(days=kind in ("evening", "prepare_evening"))
            result.append((kind, start.isoformat(), start.timestamp(), target))
    return result


def stagger_seconds(account_id):
    return int.from_bytes(hashlib.sha256(account_id.encode()).digest()[:4], "big") % 900


class Worker:
    def __init__(self, store, school, sender, clock=time.time):
        self.store, self.school, self.sender, self.clock = store, school, sender, clock

    def tick(self):
        # Single dispatcher across processes. A crashed dispatch is never blindly retried.
        with self.store.lock("worker"):
            with self.store.db() as db:
                db.execute("UPDATE jobs SET status='unknown',message='任务执行中断，投递结果待确认，未自动重发' WHERE status='running'")
                db.execute("UPDATE jobs SET status='skipped',message='本批次查询保护等待已超过窗口，未发送过期提醒' WHERE status='deferred' AND CAST(strftime('%s',slot) AS REAL)+2700<=?", (self.clock(),))
                ids = sorted((row["id"] for row in db.execute("SELECT id FROM accounts")), key=stagger_seconds)
            for kind, slot, start, target in due_slots(self.clock()):
                for account_id in ids:
                    self.dispatch(account_id, kind, slot, start, target)
            self.store.cleanup(self.clock())

    def dispatch(self, account_id, kind, slot, start, target):
        account = self.store.account(account_id)
        if not account:
            return
        with self.store.lock(account["subject"]):
            account = self.store.account(account_id)
            setting = kind.removeprefix("prepare_")
            enabled_before = start + 3600 if kind.startswith("prepare_") else start
            if (not account or account["paused"] or account["needs_auth"] or not account[setting]
                    or account[setting + "_since"] > enabled_before or self.clock() >= start + 45 * 60):
                return
            if (kind.startswith("prepare_") or kind == "grades") and self.clock() < start + stagger_seconds(account_id):
                return
            with self.store.db() as db:
                inserted = db.execute("INSERT OR IGNORE INTO jobs(account,slot,kind,status,created) VALUES(?,?,?,'running',?)",
                                      (account_id, slot, kind, self.clock())).rowcount
            if not inserted:
                with self.store.db() as db:
                    resumed = db.execute("UPDATE jobs SET status='running' WHERE account=? AND slot=? AND kind=? AND status='deferred' AND retry_at<=?",
                                         (account_id, slot, kind, self.clock())).rowcount
                if not resumed:
                    return

            def send(content, title):
                latest = self.store.account(account_id)
                if not latest or latest["paused"] or latest["needs_auth"] or not latest[setting]:
                    raise ServiceError("已暂停或取消，本次通知未发送", "skipped")
                if self.clock() >= start + 45 * 60:
                    raise ServiceError("已超过本批次发送窗口，未发送过期提醒", "skipped")
                self.sender.send(account["state"]["uid"], content, title)

            status = "done"
            retry_at = 0
            try:
                message = self.school.run(account, kind, target, send)
            except ServiceError as exc:
                status, message = exc.status, str(exc)
                if status == "deferred":
                    retry_at = self.clock() + max(60, exc.retry_after)
                if status in ("needs_auth", "needs_binding"):
                    with self.store.db() as db:
                        db.execute("UPDATE accounts SET needs_auth=1,notice=? WHERE id=?", (message, account_id))
            except Exception as exc:
                status, message = "failed", "教务获取异常，本批次未完成；请稍后在管理页检查"
                log.error("School job failed (%s)", type(exc).__name__)
            finally:
                self.store.save_state(account)
                with self.store.db() as db:
                    db.execute("UPDATE jobs SET status=?,message=?,retry_at=? WHERE account=? AND slot=? AND kind=?",
                               (status, message, retry_at, account_id, slot, kind))


def main():
    os.umask(0o077)
    store = Store(os.environ.get("CLOUD_DATA_DIR", "/var/lib/classpush"),
                  base64.b64decode(os.environ["CLOUD_DATA_KEY"], validate=True))
    worker = Worker(store, SchoolService(store), WxSender(os.environ.get("WXPUSHER_APP_TOKEN")))
    while True:
        try:
            worker.tick()
        except Exception as exc:
            log.error("Worker scan failed (%s)", type(exc).__name__)
        time.sleep(30)


if __name__ == "__main__":
    main()
