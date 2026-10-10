"""Retire only this school's legacy Windows tasks, never other school profiles."""
import sys
from pathlib import Path

from logger import logger


def is_hnit_legacy_task(task):
    """Generic names existed before school isolation; verify the target, not its name."""
    for action in task.Definition.Actions:
        executable = Path(getattr(action, "Path", "").strip('"'))
        if getattr(sys, "frozen", False) and executable.resolve() == Path(sys.executable).resolve():
            return True
        for relative in ("_internal/src/app_paths.py", "src/app_paths.py"):
            try:
                if '".ClassPush_HNIT"' in (executable.parent / relative).read_text(encoding="utf-8"):
                    return True
            except (OSError, UnicodeError):
                continue
    return False


def missing_task(exc):
    # A missing task/folder is normal; access denial must produce a warning.
    return isinstance(exc, (FileNotFoundError, KeyError)) or getattr(exc, "hresult", None) in (-2147024894, -2147024893)


def retire_local_push():
    if sys.platform != "win32":
        return ""
    try:
        # Dynamic dispatch does not depend on a machine-specific generated COM cache.
        from win32com.client.dynamic import Dispatch
        service = Dispatch("Schedule.Service")
        service.Connect()
        unresolved = False
        for folder_name in ("\\ClassPush_HNIT", "\\ClassPush", "\\"):
            try:
                folder = service.GetFolder(folder_name)
            except Exception as exc:
                if missing_task(exc):
                    continue
                raise
            for name in ("ClassPush_HNIT_AutoRun", "ClassPush_HNIT_GradeCheck",
                         "ClassPush_AutoRun", "ClassPush_GradeCheck"):
                try:
                    task = folder.GetTask(name)
                except Exception as exc:
                    if not missing_task(exc):
                        raise
                    continue
                if not task.Enabled:
                    continue
                if not name.startswith("ClassPush_HNIT_") and not is_hnit_legacy_task(task):
                    unresolved = True
                    continue
                # Keep the task for inspection/recovery; never delete another school's tasks.
                task.Enabled = False
        if unresolved:
            return "发现早期 ClassPush 通用任务，无法确认学校，未自动修改。请在 Windows 任务计划程序中确认所属学校，仅停用湖南工学院旧任务，避免重复推送"
        return ""
    except Exception:
        logger.warning("旧版本校推送任务停用失败，请检查 Windows 任务计划程序")
        return "无法停用旧版本校计划任务。请以管理员身份打开 Windows 任务计划程序，检查 ClassPush_HNIT、ClassPush 文件夹及根目录，仅停用湖南工学院旧任务后再开启云端推送"
