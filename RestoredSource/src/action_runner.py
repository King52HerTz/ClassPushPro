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
