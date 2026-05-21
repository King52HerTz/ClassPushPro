import os
import sys
import datetime
import time
import hashlib
import random

# 将当前目录加入 Python 路径，确保能导入同级模块
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from run_job import run_push_task
from logger import logger

def check_env_vars():
    """检查必要的环境变量"""
    required_vars = ["CP_USERNAME", "CP_PASSWORD", "CP_APP_TOKEN", "CP_UID"]
    missing = []
    for var in required_vars:
        if not os.getenv(var):
            missing.append(var)
    
    if missing:
        print(f"Error: Missing environment variables: {', '.join(missing)}")
        print("Please configure them in GitHub Repository -> Settings -> Secrets")
        return False
    return True

def _parse_non_negative_int_env(name: str):
    raw = os.getenv(name)
    if raw is None:
        return None
    raw = raw.strip()
    if not raw:
        return None
    try:
        value = int(raw)
    except Exception:
        return None
    if value < 0:
        return None
    return value

def _maybe_sleep_jitter():
    is_github_actions = (os.getenv("GITHUB_ACTIONS") or "").strip().lower() == "true"

    max_seconds = _parse_non_negative_int_env("CP_JITTER_MAX_SECONDS")
    if max_seconds is None:
        max_seconds = 600 if is_github_actions else 0

    if max_seconds <= 0:
        return

    forced_seconds = _parse_non_negative_int_env("CP_JITTER_SECONDS")
    if forced_seconds is not None:
        seconds = min(forced_seconds, max_seconds)
    else:
        default_mode = "hash" if is_github_actions else "none"
        mode = (os.getenv("CP_JITTER_MODE") or default_mode).strip().lower()

        if mode == "none":
            return
        if mode == "random":
            seconds = random.SystemRandom().randint(0, max_seconds)
        else:
            seed = (os.getenv("CP_USERNAME") or "").strip() or "default"
            digest = hashlib.sha256(seed.encode("utf-8")).digest()
            seconds = int.from_bytes(digest[:8], "big") % (max_seconds + 1)

    if seconds <= 0:
        return

    print(f"Jitter sleep: {seconds}s (max={max_seconds})")
    time.sleep(seconds)

if __name__ == "__main__":
    print("="*50)
    print(f"ClassPush Action Runner - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*50)

    # 1. 检查环境变量
    if not check_env_vars():
        sys.exit(1)

    _maybe_sleep_jitter()

    # 1.5 尝试加载仓库中的 config.json (用于云端离线模式)
    # 如果用户上传了 config.json 到仓库根目录，自动将其复制到默认配置路径
    try:
        repo_config_path = os.path.join(current_dir, "..", "config.json")
        if not os.path.exists(repo_config_path):
            repo_config_path = os.path.join(current_dir, "config.json")
            
        if os.path.exists(repo_config_path):
            import shutil
            target_dir = os.path.join(os.path.expanduser("~"), ".ClassPush")
            os.makedirs(target_dir, exist_ok=True)
            target_path = os.path.join(target_dir, "config.json")
            shutil.copy2(repo_config_path, target_path)
            print(f"Loaded config.json from repository to {target_path}")
    except Exception as e:
        print(f"Warning: Failed to load repository config: {e}")

    # 2. 运行推送任务
    # force=True: 强制运行，忽略"今日已推送"的检查 (因为 Actions 本身就是定时的)
    # source="auto": 标记为自动任务
    success, msg = run_push_task(force=True, source="auto")

    if success:
        print(f"SUCCESS: {msg}")
        sys.exit(0)
    else:
        print(f"FAILED: {msg}")
        sys.exit(1)
