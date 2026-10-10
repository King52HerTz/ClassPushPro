"""Inspect the real Chinese wizard, cancelling at Ready without installing."""
import ctypes
from ctypes import wintypes
import subprocess
import time
from pathlib import Path

user32 = ctypes.WinDLL("user32", use_last_error=True)
callback = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
user32.SendMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.SendMessageW.restype = wintypes.LPARAM
user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.IsWindowVisible.argtypes = [wintypes.HWND]
user32.IsWindowEnabled.argtypes = [wintypes.HWND]
user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]


def windows(parent=None):
    result = []

    @callback
    def collect(hwnd, _):
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value in process_ids and user32.IsWindowVisible(hwnd):
            label = ctypes.create_unicode_buffer(4096)
            user32.SendMessageW(hwnd, 0x000D, len(label), ctypes.cast(label, ctypes.c_void_p).value)
            result.append((hwnd, label.value))
        return True

    if parent:
        user32.EnumChildWindows(parent, collect, 0)
    else:
        user32.EnumWindows(collect, 0)
    return result


def controls():
    return [item for hwnd, _ in windows() for item in windows(hwnd)]


def wait_text(text):
    for _ in range(100):
        if any(text in label for _, label in controls()):
            return
        time.sleep(0.1)
    raise AssertionError(f"Wizard page missing: {text}")


def click(text):
    hwnd = next(hwnd for hwnd, label in controls() if label.startswith(text) and user32.IsWindowEnabled(hwnd))
    user32.PostMessageW(hwnd, 0x00F5, 0, 0)  # BM_CLICK, asynchronous for modal dialogs
    time.sleep(0.3)


repo = Path(__file__).resolve().parents[1]
exe = repo / "private/packages/ClassPush_Setup_3.0.0.exe"
process = subprocess.Popen([str(exe), "/LANG=chinesesimplified"], creationflags=subprocess.CREATE_NO_WINDOW)
process_ids = {process.pid}
try:
    # Inno Setup starts a temporary child process that owns the wizard.
    for _ in range(50):
        raw = subprocess.check_output([
            "powershell.exe", "-NoProfile", "-Command",
            f"Get-CimInstance Win32_Process -Filter 'ParentProcessId={process.pid}' | Select-Object -ExpandProperty ProcessId",
        ], creationflags=subprocess.CREATE_NO_WINDOW, text=True)
        process_ids.update(int(line.strip()) for line in raw.splitlines() if line.strip().isdigit())
        if any("ClassPush" in label for _, label in windows()):
            break
        time.sleep(0.1)
    wait_text("欢迎使用")
    click("下一步")
    wait_text("选择目标位置")
    # Set a non-existent test folder; only wizard state is changed.
    class_name = ctypes.create_unicode_buffer(128)
    for hwnd, _ in controls():
        user32.GetClassNameW(wintypes.HWND(hwnd), class_name, len(class_name))
        if "Edit" in class_name.value:
            value = ctypes.create_unicode_buffer(r"E:\ClassPush-Wizard-Test")
            user32.SendMessageW(hwnd, 0x000C, 0, ctypes.cast(value, ctypes.c_void_p).value)
            break
    else:
        raise AssertionError("Directory edit field missing")
    click("下一步")
    wait_text("选择附加任务")
    task_classes = []
    for hwnd, _ in controls():
        user32.GetClassNameW(wintypes.HWND(hwnd), class_name, len(class_name))
        task_classes.append(class_name.value)
    assert "TNewCheckListBox" in task_classes, "Shortcut checkbox list missing"
    click("下一步")
    wait_text("准备安装")
    wait_text(r"E:\ClassPush-Wizard-Test")
    wait_text("创建桌面快捷方式")
    click("取消")
    # The cancellation confirmation uses the stock Yes button identifier.
    for _ in range(20):
        yes = [(hwnd, label) for hwnd, label in controls() if "是(" in label or label in ("是", "Yes", "&Yes")]
        if yes:
            user32.SendMessageW(yes[0][0], 0x00F5, 0, 0)
            break
        time.sleep(0.1)
    process.wait(timeout=10)
    assert not Path(r"E:\ClassPush-Wizard-Test").exists(), "Wizard test must not install files"
    print("Installer wizard passed: Chinese Welcome, editable E: directory, desktop shortcut task, Ready summary; cancelled without installing.")
finally:
    if process.poll() is None:
        subprocess.run(["taskkill.exe", "/PID", str(process.pid), "/T", "/F"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW)
