"""Retire only this school's legacy Windows tasks, never other school profiles."""
import sys

from logger import logger


def retire_local_push():
    if sys.platform != "win32":
        return ""
    try:
        import win32com.client
        service = win32com.client.Dispatch("Schedule.Service")
        service.Connect()
        for folder_name in ("\\ClassPush_HNIT", "\\"):
            try:
                folder = service.GetFolder(folder_name)
            except Exception:
                continue
            for name in ("ClassPush_HNIT_AutoRun", "ClassPush_HNIT_GradeCheck"):
                try:
                    task = folder.GetTask(name)
                except Exception:
                    continue
                # Disable before deleting: even if deletion is denied it cannot send.
                task.Enabled = False
                folder.DeleteTask(name, 0)
        return ""
    except Exception:
        logger.warning("旧版本校推送任务停用失败，请检查 Windows 任务计划程序")
        return "无法停用旧版本校计划任务，请在 Windows 任务计划程序中关闭 ClassPush_HNIT 文件夹内的任务"
