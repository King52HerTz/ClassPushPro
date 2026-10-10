import base64
import hmac
import os
import re
import secrets
import time
from functools import wraps

from flask import Flask, g, jsonify, request
from werkzeug.exceptions import HTTPException

from .service import SchoolService, ServiceError, StateConfig, WxSender, masked
from .store import Store

PREFIX = "/api/cloud"
COOKIE = "classpush_cloud"
SESSION_SECONDS = 30 * 86400


def create_app(store=None, school=None, sender=None, clock=time.time, origin=None):
    app = Flask(__name__)
    app.config.update(MAX_CONTENT_LENGTH=8192)
    origin = origin or os.environ.get("CLOUD_ORIGIN", "https://classpush.eliauk312.top")
    if store is None:
        store = Store(os.environ.get("CLOUD_DATA_DIR", "/var/lib/classpush"),
                      base64.b64decode(os.environ["CLOUD_DATA_KEY"], validate=True))
    school = school or SchoolService()
    sender = sender or WxSender(os.environ.get("WXPUSHER_APP_TOKEN"))
    app.extensions.update(cloud_store=store, cloud_school=school, cloud_sender=sender)

    def fail(message, status=400):
        return jsonify(message=message), status

    @app.before_request
    def protect():
        if request.method in {"POST", "PATCH", "DELETE"}:
            if request.headers.get("Origin") != origin or not request.is_json:
                return fail("请求来源无效，请从官网重新打开管理页", 403)

    @app.after_request
    def headers(response):
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    @app.errorhandler(ServiceError)
    def service_error(exc):
        return fail(str(exc), 502)

    @app.errorhandler(Exception)
    def unexpected(exc):
        if isinstance(exc, HTTPException):
            return fail("请求无效", exc.code)
        # Exception strings from school HTTP libraries can contain credentials.
        app.logger.error("Cloud operation failed (%s)", type(exc).__name__)
        return fail("服务暂时不可用，请稍后重试", 503)

    def data():
        value = request.get_json(silent=True)
        return value if isinstance(value, dict) else {}

    def limited(key, count=5, period=600):
        # Nginx must replace X-Real-IP; direct listener is loopback only.
        ip = request.headers.get("X-Real-IP") if request.remote_addr == "127.0.0.1" else request.remote_addr
        return (store.rate_limit("ip:" + str(ip), clock(), 30, 600)
                and store.rate_limit(key, clock(), count, period))

    def authorized(fn):
        @wraps(fn)
        def inner(*args, **kwargs):
            with store.db() as db:
                session = db.execute("SELECT account FROM sessions WHERE token=? AND expires>?",
                                     (store.digest(request.cookies.get(COOKIE, "")), clock())).fetchone()
            if not session:
                return fail("请先登录云端管理", 401)
            account = store.account(session["account"])
            if not account:
                return fail("账号已删除，请重新登录", 401)
            with store.lock(account["subject"]):
                g.account = store.account(account["id"])
                if not g.account:
                    return fail("账号已删除", 401)
                return fn(*args, **kwargs)
        return inner

    @app.get(PREFIX + "/health")
    def health():
        with store.db() as db:
            db.execute("SELECT 1")
        return jsonify(status="ok", version="3.0.0")

    @app.post(PREFIX + "/auth/request")
    def request_code():
        body = data()
        username = str(body.get("username", "")).strip()
        password = body.get("password")
        uid = str(body.get("uid", "")).strip()
        if (not re.fullmatch(r"[A-Za-z0-9]{6,24}", username) or not isinstance(password, str)
                or not 1 <= len(password) <= 128 or body.get("consent") is not True):
            return fail("请填写正确的本校学号、密码，并同意云端托管")
        subject = store.digest("student:" + username)
        if not limited("login:" + subject, 3, 600):
            return fail("操作过于频繁，请十分钟后重试", 429)
        with store.lock(subject):
            existing = store.account(subject=subject)
            if existing:
                uid = existing["state"]["uid"]
            if not re.fullmatch(r"UID_[A-Za-z0-9]{8,100}", uid):
                return fail("请填写本校 WxPusher 应用的 UID")
            if not store.rate_limit("uid:" + uid, clock(), 3, 600):
                return fail("验证码发送过于频繁，请十分钟后重试", 429)
            state = {"username": username, "password": password, "uid": uid}
            school.verify(state)
            challenge = secrets.token_urlsafe(32)
            code = f"{secrets.randbelow(1000000):06d}"
            sender.send(uid, f"ClassPush 云端管理验证码：{code}。5 分钟内有效，请勿转发。", "ClassPush 登录验证码", 1)
            with store.db() as db:
                db.execute("DELETE FROM challenges WHERE subject=?", (subject,))
                db.execute("INSERT INTO challenges(id,subject,code,state,expires) VALUES(?,?,?,?,?)",
                           (challenge, subject, store.digest(challenge + code), store.seal(state, challenge), clock() + 300))
            return jsonify(challenge=challenge, message="验证码已提交到绑定的 WxPusher，请在 App 中查看并在 5 分钟内输入")

    @app.post(PREFIX + "/auth/confirm")
    def confirm():
        body = data()
        challenge = str(body.get("challenge", ""))
        code = str(body.get("code", ""))
        if len(challenge) > 100 or not re.fullmatch(r"\d{6}", code):
            return fail("请输入六位验证码")
        if not limited("confirm:" + challenge, 10, 300):
            return fail("验证码尝试过多，请重新获取", 429)
        with store.db() as db:
            row = db.execute("SELECT * FROM challenges WHERE id=?", (challenge,)).fetchone()
        if not row:
            return fail("验证码已失效，请重新获取")
        with store.lock(row["subject"]):
            with store.db() as db:
                db.execute("BEGIN IMMEDIATE")
                row = db.execute("SELECT * FROM challenges WHERE id=?", (challenge,)).fetchone()
                if not row or row["expires"] <= clock() or row["attempts"] >= 5:
                    return fail("验证码已失效，请重新获取")
                if not hmac.compare_digest(row["code"], store.digest(challenge + code)):
                    db.execute("UPDATE challenges SET attempts=attempts+1 WHERE id=?", (challenge,))
                    return fail("验证码错误")
                existing = db.execute("SELECT id,state FROM accounts WHERE subject=?", (row["subject"],)).fetchone()
                state = store.open(row["state"], challenge)
                account_id = existing["id"] if existing else secrets.token_hex(16)
                if existing:
                    previous = store.open(existing["state"], account_id)
                    previous.update(state)
                    state = previous
                    db.execute("UPDATE accounts SET state=?,needs_auth=0,notice='' WHERE id=?",
                               (store.seal(state, account_id), account_id))
                else:
                    db.execute("INSERT INTO accounts(id,subject,state,created) VALUES(?,?,?,?)",
                               (account_id, row["subject"], store.seal(state, account_id), clock()))
                token = secrets.token_urlsafe(48)
                db.execute("INSERT INTO sessions VALUES(?,?,?)", (store.digest(token), account_id, clock() + SESSION_SECONDS))
                db.execute("DELETE FROM challenges WHERE subject=?", (row["subject"],))
            response = jsonify(message="登录成功，请选择推送时段并保存")
            response.set_cookie(COOKIE, token, max_age=SESSION_SECONDS, secure=True, httponly=True,
                                samesite="Strict", path=PREFIX)
            return response

    @app.post(PREFIX + "/auth/logout")
    def logout():
        with store.db() as db:
            db.execute("DELETE FROM sessions WHERE token=?", (store.digest(request.cookies.get(COOKIE, "")),))
        response = jsonify(message="已退出云端管理，已有推送设置保持不变")
        response.delete_cookie(COOKIE, path=PREFIX, secure=True, httponly=True, samesite="Strict")
        return response

    @app.get(PREFIX + "/account")
    @authorized
    def get_account():
        account = g.account
        with store.db() as db:
            jobs = db.execute("SELECT kind,status,message,created FROM jobs WHERE account=? ORDER BY created DESC LIMIT 20",
                              (account["id"],)).fetchall()
        result = {key: bool(account[key]) for key in ("morning", "evening", "grades", "paused", "needs_auth")}
        result.update(username=account["state"]["username"], uid=masked(account["state"]["uid"]),
                      notice=account["notice"], jobs=[dict(row) for row in jobs])
        return jsonify(result)

    @app.patch(PREFIX + "/account")
    @authorized
    def settings():
        body = data()
        if set(body) != {"morning", "evening", "grades", "paused"} or any(type(value) is not bool for value in body.values()):
            return fail("推送设置格式不正确")
        account = g.account
        since = {}
        for kind in ("morning", "evening", "grades"):
            since[kind] = clock() if body[kind] and (not account[kind] or (account["paused"] and not body["paused"])) else account[kind + "_since"]
        if body["grades"] and not account["grades"]:
            account["state"]["grade_push_initialized"] = False
            store.save_state(account)
        with store.db() as db:
            db.execute("""UPDATE accounts SET morning=?,evening=?,grades=?,paused=?,
                       morning_since=?,evening_since=?,grades_since=? WHERE id=?""",
                       (*[int(body[key]) for key in ("morning", "evening", "grades", "paused")],
                        *[since[key] for key in ("morning", "evening", "grades")], account["id"]))
        return jsonify(message="已保存。新启用或恢复的时段从下一批次生效")

    @app.post(PREFIX + "/account/password")
    @authorized
    def password():
        value = data().get("password")
        if not isinstance(value, str) or not 1 <= len(value) <= 128:
            return fail("请输入教务密码")
        if not limited("password:" + g.account["id"], 3, 600):
            return fail("尝试过于频繁，请稍后重试", 429)
        state = dict(g.account["state"])
        state["password"] = value
        StateConfig(state).clear_jw_cached_token()
        school.verify(state)
        g.account["state"] = state
        store.save_state(g.account)
        with store.db() as db:
            db.execute("UPDATE accounts SET needs_auth=0,notice='' WHERE id=?", (g.account["id"],))
        return jsonify(message="密码已验证并更新")

    @app.post(PREFIX + "/account/test")
    @authorized
    def test_message():
        if not limited("test:" + g.account["id"], 2, 600):
            return fail("测试过于频繁，请十分钟后再试", 429)
        sender.send(g.account["state"]["uid"], "ClassPush 云端连接测试成功。此消息不代表定时推送已开启，请在管理页检查开关。", "ClassPush 云端测试", 1)
        if "订阅" in g.account["notice"]:
            with store.db() as db:
                db.execute("UPDATE accounts SET needs_auth=0,notice='' WHERE id=?", (g.account["id"],))
        return jsonify(message="测试消息已提交 WxPusher，请在独立 App 中查看，并检查通知权限")

    @app.delete(PREFIX + "/account")
    @authorized
    def delete_account():
        if data().get("confirm") != "DELETE":
            return fail("请确认删除")
        with store.db() as db:
            db.execute("DELETE FROM challenges WHERE subject=?", (g.account["subject"],))
            db.execute("DELETE FROM accounts WHERE id=?", (g.account["id"],))
        response = jsonify(message="已关闭推送并删除在线账号、凭据、缓存和任务记录")
        response.delete_cookie(COOKIE, path=PREFIX, secure=True, httponly=True, samesite="Strict")
        return response

    return app
