import winreg
import sys
import os

KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_NAME = "ClassPush"

def set_autostart(enable=True):
    """
    设置或取消开机自启
    """
    try:
        # 获取当前运行路径
        if getattr(sys, 'frozen', False):
            exe_path = sys.executable
            # 如果是打包后的exe，直接运行exe
            cmd_args = f'"{exe_path}"'
        else:
            exe_path = sys.executable
            # 找到 main.py
            script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "main.py")
            cmd_args = f'"{exe_path}" "{script_path}"'
        
        # 打开注册表键
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, KEY, 0, winreg.KEY_ALL_ACCESS)
        
        if enable:
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, cmd_args)
            winreg.CloseKey(key)
            return True, "自启动设置成功"
        else:
            try:
                winreg.DeleteValue(key, APP_NAME)
                winreg.CloseKey(key)
                return True, "自启动已取消"
            except FileNotFoundError:
                return True, "自启动本来就未设置"
    except Exception as e:
        return False, f"注册表操作失败: {e}"

def check_autostart():
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, KEY, 0, winreg.KEY_READ)
        value, _ = winreg.QueryValueEx(key, APP_NAME)
        winreg.CloseKey(key)
        return True
    except FileNotFoundError:
        return False
    except Exception:
        return False
