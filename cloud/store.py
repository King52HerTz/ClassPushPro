import base64
import hashlib
import hmac
import json
import os
import sqlite3
import threading
import time
import errno
from contextlib import contextmanager
from pathlib import Path

from Crypto.Cipher import AES


class Store:
    """SQLite transactions are short; account locks may span bounded HTTP calls."""

    def __init__(self, directory, key):
        if len(key) != 32:
            raise ValueError("CLOUD_DATA_KEY 必须为 32 字节的 base64 密钥")
        self.key = key
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.path = self.directory / "cloud.sqlite3"
        self._locks = {}
        self._guard = threading.Lock()
        with self.db() as db:
            db.executescript("""
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS accounts (
                    id TEXT PRIMARY KEY, subject TEXT UNIQUE NOT NULL, state TEXT NOT NULL,
                    morning INTEGER NOT NULL DEFAULT 0, evening INTEGER NOT NULL DEFAULT 0,
                    grades INTEGER NOT NULL DEFAULT 0, paused INTEGER NOT NULL DEFAULT 1,
                    needs_auth INTEGER NOT NULL DEFAULT 0, notice TEXT NOT NULL DEFAULT '',
                    morning_since REAL NOT NULL DEFAULT 0, evening_since REAL NOT NULL DEFAULT 0,
                    grades_since REAL NOT NULL DEFAULT 0, created REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS sessions (
                    token TEXT PRIMARY KEY, account TEXT NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
                    expires REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS challenges (
                    id TEXT PRIMARY KEY, subject TEXT NOT NULL, code TEXT NOT NULL, state TEXT NOT NULL,
                    expires REAL NOT NULL, attempts INTEGER NOT NULL DEFAULT 0);
                CREATE TABLE IF NOT EXISTS jobs (
                    account TEXT NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
                    slot TEXT NOT NULL, kind TEXT NOT NULL, status TEXT NOT NULL,
                    message TEXT NOT NULL DEFAULT '', created REAL NOT NULL,
                    retry_at REAL NOT NULL DEFAULT 0,
                    PRIMARY KEY(account, slot, kind));
                CREATE TABLE IF NOT EXISTS limits (
                    key TEXT PRIMARY KEY, start REAL NOT NULL, count INTEGER NOT NULL);
                CREATE TABLE IF NOT EXISTS school_outbound (
                    id INTEGER PRIMARY KEY CHECK(id=1), next_request REAL NOT NULL DEFAULT 0,
                    cooldown_until REAL NOT NULL DEFAULT 0, failures INTEGER NOT NULL DEFAULT 0);
                INSERT OR IGNORE INTO school_outbound(id) VALUES(1);
            """)
            if "retry_at" not in {row[1] for row in db.execute("PRAGMA table_info(jobs)")}:
                db.execute("ALTER TABLE jobs ADD COLUMN retry_at REAL NOT NULL DEFAULT 0")
        if os.name != "nt":
            os.chmod(self.directory, 0o700)
            os.chmod(self.path, 0o600)

    @contextmanager
    def db(self):
        db = sqlite3.connect(self.path, timeout=15)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        try:
            with db:
                yield db
        finally:
            db.close()

    def digest(self, value):
        return hmac.new(self.key, str(value).encode(), hashlib.sha256).hexdigest()

    def seal(self, value, context):
        cipher = AES.new(self.key, AES.MODE_GCM)
        cipher.update(context.encode())
        encrypted, tag = cipher.encrypt_and_digest(json.dumps(value, ensure_ascii=False).encode())
        return base64.b64encode(cipher.nonce + tag + encrypted).decode()

    def open(self, value, context):
        blob = base64.b64decode(value)
        cipher = AES.new(self.key, AES.MODE_GCM, nonce=blob[:16])
        cipher.update(context.encode())
        return json.loads(cipher.decrypt_and_verify(blob[32:], blob[16:32]))

    @contextmanager
    def lock(self, subject, timeout=None):
        # Hash filenames even for internal callers; never include a student id.
        name = self.digest(subject)
        with self._guard:
            thread_lock = self._locks.setdefault(name, threading.RLock())
        deadline = time.monotonic() + timeout if timeout is not None else None
        acquired = thread_lock.acquire() if timeout is None else thread_lock.acquire(timeout=timeout)
        if not acquired:
            raise TimeoutError("Lock queue timeout")
        try:
            with open(self.directory / (name + ".lock"), "a+b") as handle:
                if os.name == "nt":
                    import msvcrt
                    handle.seek(0)
                    handle.write(b"0")
                    handle.flush()
                    handle.seek(0)
                else:
                    import fcntl
                while True:
                    try:
                        if os.name == "nt":
                            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                        else:
                            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
                        break
                    except OSError as exc:
                        if exc.errno not in (errno.EACCES, errno.EAGAIN, errno.EDEADLK):
                            raise
                        if deadline is not None and time.monotonic() >= deadline:
                            raise TimeoutError("Lock queue timeout") from None
                        time.sleep(0.05)
                try:
                    yield
                finally:
                    if os.name == "nt":
                        handle.seek(0)
                        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                    else:
                        fcntl.flock(handle, fcntl.LOCK_UN)
        finally:
            thread_lock.release()

    def account(self, account_id=None, subject=None):
        with self.db() as db:
            if account_id:
                row = db.execute("SELECT * FROM accounts WHERE id=?", (account_id,)).fetchone()
            else:
                row = db.execute("SELECT * FROM accounts WHERE subject=?", (subject,)).fetchone()
        if not row:
            return None
        result = dict(row)
        result["state"] = self.open(result["state"], result["id"])
        return result

    def save_state(self, account):
        with self.db() as db:
            db.execute("UPDATE accounts SET state=? WHERE id=?",
                       (self.seal(account["state"], account["id"]), account["id"]))

    def rate_limit(self, key, now, count=5, period=600):
        key = self.digest("limit:" + key)
        with self.db() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT * FROM limits WHERE key=?", (key,)).fetchone()
            if row and row["start"] + period > now:
                if row["count"] >= count:
                    return False
                db.execute("UPDATE limits SET count=count+1 WHERE key=?", (key,))
            else:
                db.execute("INSERT OR REPLACE INTO limits VALUES(?,?,1)", (key, now))
        return True

    def cleanup(self, now):
        with self.db() as db:
            db.execute("DELETE FROM sessions WHERE expires<=?", (now,))
            db.execute("DELETE FROM challenges WHERE expires<=?", (now,))
            db.execute("DELETE FROM limits WHERE start<?", (now - 86400,))
            db.execute("DELETE FROM jobs WHERE created<?", (now - 30 * 86400,))
