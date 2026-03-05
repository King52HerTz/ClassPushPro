import os
import sys
import datetime

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

if __name__ == "__main__":
    print("="*50)
    print(f"ClassPush Action Runner - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*50)

    # 1. 检查环境变量
    if not check_env_vars():
        sys.exit(1)

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
