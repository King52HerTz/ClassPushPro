import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from app_paths import get_app_data_dir

# Cloud school-client exceptions may include sensitive request URLs.
IS_CLOUD = os.getenv('CLASSPUSH_CLOUD') == '1'
if IS_CLOUD:
    LOG_DIR = ''
elif getattr(sys, 'frozen', False):
    # 打包后：日志与本学校的配置隔离保存
    LOG_DIR = os.path.join(get_app_data_dir(), "logs")
else:
    # 开发环境：存储在项目目录下的 logs
    LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")

if LOG_DIR and not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

# 日志文件名
LOG_FILE = os.path.join(LOG_DIR, "app.log")

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        *([] if IS_CLOUD else [RotatingFileHandler(LOG_FILE, maxBytes=2 * 1024 * 1024, backupCount=5, encoding='utf-8')]),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger("ClassPush")
if IS_CLOUD:
    logger.disabled = True
