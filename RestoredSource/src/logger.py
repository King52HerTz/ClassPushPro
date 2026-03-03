import logging
import os
import sys
from logging.handlers import RotatingFileHandler

# 确保日志目录存在
if getattr(sys, 'frozen', False):
    # 打包后：日志存储在用户主目录下的 .ClassPush/logs
    LOG_DIR = os.path.join(os.path.expanduser("~"), ".ClassPush", "logs")
else:
    # 开发环境：存储在项目目录下的 logs
    LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")

if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

# 日志文件名
LOG_FILE = os.path.join(LOG_DIR, "app.log")

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        RotatingFileHandler(LOG_FILE, maxBytes=2 * 1024 * 1024, backupCount=5, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger("ClassPush")
