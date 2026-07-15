import os
import sys
import json
import base64
import socket
import datetime
import time
import hashlib
import random

# 将当前目录加入 Python 路径，确保能导入同级模块
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from run_job import run_grade_check_task, run_push_task
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

def _get_target_config_path():
    target_dir = os.path.join(os.path.expanduser("~"), ".ClassPush")
    os.makedirs(target_dir, exist_ok=True)
    return os.path.join(target_dir, "config.json")

def _print_config_cache_status(config_path, source_label):
    if not os.path.exists(config_path):
        print(f"Config bootstrap [{source_label}]: 未发现配置文件")
        return

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"Warning: Failed to inspect config cache [{source_label}]: {e}")
        return

    has_jw_token = bool(data.get("jw_cached_token"))
    has_courses_cache = bool(data.get("cached_courses_data"))
    jw_cached_time = data.get("jw_cached_time") or "无"
    print(
        "Config bootstrap [{}]: jw_cached_token={}, cached_courses_data={}, jw_cached_time={}".format(
            source_label,
            "yes" if has_jw_token else "no",
            "yes" if has_courses_cache else "no",
            jw_cached_time,
        )
    )

def _restore_bootstrap_config():
    target_path = _get_target_config_path()
    if os.path.exists(target_path):
        print(f"Config bootstrap: 使用缓存目录中的现有配置 {target_path}")
        _print_config_cache_status(target_path, "existing-cache")
        return

    config_b64 = (os.getenv("CP_CONFIG_JSON_B64") or "").strip()
    if config_b64:
        try:
            decoded_bytes = base64.b64decode(config_b64)
            decoded_text = decoded_bytes.decode("utf-8")
            json.loads(decoded_text)
            with open(target_path, "w", encoding="utf-8") as f:
                f.write(decoded_text)
            print(f"Config bootstrap: 已从 CP_CONFIG_JSON_B64 恢复配置到 {target_path}")
            _print_config_cache_status(target_path, "secret")
            return
        except Exception as e:
            print(f"Warning: Failed to restore config from CP_CONFIG_JSON_B64: {e}")

    print("Config bootstrap: 未发现缓存或 CP_CONFIG_JSON_B64，将使用 GitHub Secrets 在线抓取")

def _probe_school_network():
    host = "jw.hnit.edu.cn"
    port = 443
    print(f"Network probe: 开始检测 {host}:{port}")

    try:
        addr_infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
        ip_list = []
        for item in addr_infos:
            ip = item[4][0]
            if ip not in ip_list:
                ip_list.append(ip)
        if ip_list:
            print(f"Network probe: DNS 解析成功 -> {', '.join(ip_list[:3])}")
        else:
            print("Network probe: DNS 解析成功，但未获取到可用 IP")
    except Exception as e:
        print(f"Warning: Network probe DNS 解析失败: {e}")
        return

    try:
        with socket.create_connection((host, port), timeout=5):
            print("Network probe: TCP 443 连接成功，云端当前具备访问教务的基础网络")
    except Exception as e:
        print(f"Warning: Network probe TCP 连接失败: {e}")

if __name__ == "__main__":
    print("="*50)
    print(f"ClassPush Action Runner - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*50)

    # 1. 检查环境变量
    if not check_env_vars():
        sys.exit(1)

    _maybe_sleep_jitter()
    _restore_bootstrap_config()
    _probe_school_network()

    job_type = (os.getenv("CP_JOB") or "schedule").strip().lower()
    if job_type == "grades":
        success, result = run_grade_check_task()
        msg = result.get("push_result", {}).get("message") or result.get("message") or "成绩检查完成"
    else:
        # force=True: Actions 的晨间/晚间工作流本身已经负责调度。
        success, msg = run_push_task(force=True, source="auto")

    if success:
        print(f"SUCCESS: {msg}")
        sys.exit(0)
    else:
        print(f"FAILED: {msg}")
        sys.exit(1)
