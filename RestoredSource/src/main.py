import os
import sys
import argparse
import threading
import time
from api import Api
from run_job import run_push_task
from logger import logger

def _try_set_windows_icon(window_title: str, icon_path: str):
    if sys.platform != 'win32':
        return
    if not icon_path or not os.path.exists(icon_path):
        return

    try:
        import ctypes
        from ctypes import wintypes
        import time

        user32 = ctypes.windll.user32

        EnumWindows = user32.EnumWindows
        EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
        GetWindowTextW = user32.GetWindowTextW
        GetWindowTextLengthW = user32.GetWindowTextLengthW
        IsWindowVisible = user32.IsWindowVisible

        IMAGE_ICON = 1
        LR_LOADFROMFILE = 0x0010
        LR_DEFAULTSIZE = 0x0040
        WM_SETICON = 0x0080
        ICON_SMALL = 0
        ICON_BIG = 1

        LoadImageW = user32.LoadImageW
        SendMessageW = user32.SendMessageW

        hicon = LoadImageW(None, icon_path, IMAGE_ICON, 0, 0, LR_LOADFROMFILE | LR_DEFAULTSIZE)
        if not hicon:
            try:
                ExtractIconW = ctypes.windll.shell32.ExtractIconW
                hicon = ExtractIconW(None, ctypes.c_wchar_p(icon_path), 0)
            except Exception:
                hicon = None
        if not hicon:
            return

        target_hwnd = None

        def _callback(hwnd, lparam):
            nonlocal target_hwnd
            if not IsWindowVisible(hwnd):
                return True
            length = GetWindowTextLengthW(hwnd)
            if length <= 0:
                return True
            buf = ctypes.create_unicode_buffer(length + 1)
            GetWindowTextW(hwnd, buf, length + 1)
            title = buf.value
            # 精确匹配标题，防止误匹配
            if title == window_title:
                target_hwnd = hwnd
                return False
            return True

        for _ in range(200):
            target_hwnd = None
            EnumWindows(EnumWindowsProc(_callback), 0)
            if target_hwnd:
                SendMessageW(target_hwnd, WM_SETICON, ICON_SMALL, hicon)
                SendMessageW(target_hwnd, WM_SETICON, ICON_BIG, hicon)
                break
            time.sleep(0.2)
    except Exception:
        return

def get_icon_path():
    candidates = []

    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        base = sys._MEIPASS
        candidates.extend([
            os.path.join(base, 'icon.ico'),
            os.path.join(base, 'gui', 'icon.ico'),
        ])

    # 1. 使用绝对路径计算 project_root
    current_script = os.path.abspath(__file__)
    src_dir = os.path.dirname(current_script) # .../RestoredSource/src
    project_root = os.path.dirname(src_dir)   # .../RestoredSource
    
    candidates.extend([
        os.path.join(project_root, 'frontend', 'public', 'icon.ico'),
        os.path.join(project_root, 'frontend', 'dist', 'icon.ico'),
        os.path.join(src_dir, 'gui', 'icon.ico'),
        os.path.join(src_dir, 'icon.ico'),
    ])
    
    # 2. 额外兜底：基于当前工作目录的向上回溯
    try:
        cwd = os.getcwd()
        candidates.extend([
            os.path.join(cwd, 'frontend', 'public', 'icon.ico'), # cwd 在 RestoredSource
            os.path.join(cwd, '..', 'frontend', 'public', 'icon.ico'), # cwd 在 src
        ])
    except Exception:
        pass

    for p in candidates:
        abs_p = os.path.abspath(p)
        if os.path.exists(abs_p):
            return abs_p

    # 扫描搜索兜底 (保留)
    bases = [project_root, src_dir]
    try:
        bases.append(os.getcwd())
    except Exception:
        pass
    for base in bases:
        try:
            for root, dirs, files in os.walk(base):
                if 'icon.ico' in files:
                    return os.path.abspath(os.path.join(root, 'icon.ico'))
        except Exception:
            continue

    try:
        logger.info(f"Icon search bases: project_root={project_root}, src_dir={src_dir}, cwd={os.getcwd()}")
        logger.info(f"Icon candidates tried: {', '.join(candidates)}")
    except Exception:
        pass
    return None

def get_entry_point():
    # 1. 开发模式：优先检查本地开发服务器
    # 注意：这需要确保 frontend 已经通过 npm run dev 启动
    dev_url = "http://localhost:5173"
    try:
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('localhost', 5173))
        sock.close()
        if result == 0:
            logger.info(f"Detected dev server at {dev_url}")
            return dev_url
    except:
        pass

    # 2. 生产模式：打包后的环境
    if getattr(sys, 'frozen', False):
        # PyInstaller 打包后的路径处理
        # --onefile 模式下使用 sys._MEIPASS
        # --onedir 模式下使用 sys.executable 所在目录
        base_dir = sys._MEIPASS if hasattr(sys, '_MEIPASS') else os.path.dirname(sys.executable)
        
        # 检查 spec 中配置的 frontend/dist 路径
        frozen_path = os.path.join(base_dir, "frontend", "dist", "index.html")
        if os.path.exists(frozen_path):
            return frozen_path
            
        # 备用路径检查
        frozen_path_alt = os.path.join(base_dir, "RestoredSource", "frontend", "dist", "index.html")
        if os.path.exists(frozen_path_alt):
            return frozen_path_alt

    # 3. 源码运行模式：查找构建好的静态文件
    # 优先查找开发环境路径
    dev_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "dist", "index.html")
    if os.path.exists(dev_path):
        return os.path.abspath(dev_path)
    
    # 查找同级gui目录 (旧版打包结构)
    prod_path = os.path.join(os.path.dirname(__file__), "gui", "index.html")
    if os.path.exists(prod_path):
        return os.path.abspath(prod_path)
        
    return None

def _open_log_file():
    try:
        project_root = os.path.dirname(os.path.dirname(__file__))
        log_path = os.path.join(project_root, "logs", "app.log")
        if os.path.exists(log_path):
            os.startfile(log_path)
            return
        log_dir = os.path.join(project_root, "logs")
        if os.path.isdir(log_dir):
            os.startfile(log_dir)
            return
        os.startfile(project_root)
    except Exception as e:
        logger.error(f"打开日志失败: {e}")

if __name__ == '__main__':
    # 1. 解析命令行参数
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-job", action="store_true", help="Run push task silently")
    parser.add_argument("--create-schedule", type=str, help="Create schedule task with admin privileges")
    args = parser.parse_args()

    # 2. 如果是运行任务模式
    if args.run_job:
        logger.info("Running push task in silent mode...")
        run_push_task()
        sys.exit(0)
    
    # 3. 如果是创建任务模式 (Admin)
    if args.create_schedule:
        from scheduler import create_schedule_task
        logger.info(f"Creating schedule task for {args.create_schedule}...")
        success, msg = create_schedule_task(args.create_schedule)
        if success:
            logger.info("Task created successfully.")
            sys.exit(0)
        else:
            logger.error(f"Task creation failed: {msg}")
            sys.exit(1)

    # 4. 正常启动 GUI
    import webview
    logger.info("=== Starting ClassPush  GUI (Version: Fix-Reload-Config) ===")
    api = Api()
    entry = get_entry_point()
    icon_path = get_icon_path()
    if icon_path:
        logger.info(f"Icon path: {icon_path}")
    else:
        logger.info("Icon path not found")
    window_title = 'ClassPush'
    
    if not entry:
        # 如果找不到HTML，创建一个临时的错误页面
        html_content = "<h1>Error: Frontend not found</h1><p>Please run 'npm run dev' or 'npm run build' in frontend directory.</p>"
        window_title = 'ClassPush (Restored)'
        window = webview.create_window(window_title, html=html_content)
    else:
        # pywebview 可以智能识别 url 是本地路径还是 http 链接
        # 注意：不要在 create_window 中直接传 icon，某些环境下会导致崩溃或显示问题
        # 改为仅使用 _try_set_windows_icon 后置设置
        window = webview.create_window(window_title, url=entry, width=1024, height=768, resizable=True)
        
    # window.expose(api) # expose is not needed when js_api is used in create_window
    window.expose(
        api.get_config,
        api.save_config,
        api.login_test,
        api.get_preview_courses,
        api.manual_push,
        api.ignore_missed_push,
        api.set_autostart,
        api.get_system_status,
        api.toggle_scheduler,
        api.check_today_pushed
    )

    if icon_path and sys.platform == 'win32':
        threading.Thread(target=_try_set_windows_icon, args=(window_title, icon_path), daemon=True).start()

    # 生产环境关闭 debug 模式，防止出现开发者工具
    webview.start(debug=False)
