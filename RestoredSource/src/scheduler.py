import sys
import os
import datetime
import time
import ctypes
import win32com.client
from logger import logger

COURSE_TASK_NAME = "ClassPush_AutoRun"
GRADE_TASK_NAME = "ClassPush_GradeCheck"
TASK_FOLDER_NAME = "ClassPush"

# Task Scheduler Constants
TASK_TRIGGER_DAILY = 2
TASK_ACTION_EXEC = 0
TASK_CREATE_OR_UPDATE = 6
TASK_LOGON_INTERACTIVE_TOKEN = 3
TASK_RUNLEVEL_LATEST = 0


def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        return False


def run_as_admin(args):
    """请求提权运行"""
    try:
        if getattr(sys, "frozen", False):
            exe = sys.executable
            params = args
        else:
            exe = sys.executable
            script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "main.py")
            params = f'"{script}" {args}'

        ret = ctypes.windll.shell32.ShellExecuteW(None, "runas", exe, params, None, 1)
        return ret > 32
    except Exception as e:
        logger.error(f"提权失败: {e}")
        return False


def _parse_clock_time(time_str):
    try:
        hour, minute = map(int, str(time_str or "").split(":"))
    except ValueError:
        raise ValueError("时间格式错误，应为 HH:mm")

    if hour < 0 or hour > 23 or minute < 0 or minute > 59:
        raise ValueError("时间格式错误，应为 HH:mm")
    return hour, minute


def _build_repetition_duration(start_time_str, end_time_str):
    start_hour, start_minute = _parse_clock_time(start_time_str)
    end_hour, end_minute = _parse_clock_time(end_time_str)
    start_total = start_hour * 60 + start_minute
    end_total = end_hour * 60 + end_minute
    duration_minutes = end_total - start_total
    if duration_minutes <= 0:
        duration_minutes += 24 * 60
    hours, minutes = divmod(duration_minutes, 60)
    if hours and minutes:
        return f"PT{hours}H{minutes}M"
    if hours:
        return f"PT{hours}H"
    return f"PT{minutes}M"


def _build_interval_text(interval_minutes):
    minutes = max(int(interval_minutes), 1)
    hours, remain_minutes = divmod(minutes, 60)
    if hours and remain_minutes:
        return f"PT{hours}H{remain_minutes}M"
    if hours:
        return f"PT{hours}H"
    return f"PT{remain_minutes}M"


def _resolve_command_arguments(mode):
    if getattr(sys, "frozen", False):
        exe_path = sys.executable
        arguments = mode
        cwd = os.path.dirname(exe_path)
    else:
        exe_path = sys.executable
        script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "main.py")
        arguments = f'"{script_path}" {mode}'
        cwd = os.path.dirname(script_path)
    return exe_path, arguments, cwd


def _connect_task_folder():
    scheduler = win32com.client.Dispatch("Schedule.Service")
    scheduler.Connect()
    root_folder = scheduler.GetFolder("\\")
    task_folder = root_folder

    try:
        try:
            task_folder = root_folder.GetFolder(f"\\{TASK_FOLDER_NAME}")
        except Exception:
            task_folder = root_folder.CreateFolder(f"\\{TASK_FOLDER_NAME}")
    except Exception:
        task_folder = root_folder

    return scheduler, root_folder, task_folder


def _register_daily_task(task_name, description, start_time_str, mode, repetition_interval_minutes=None, repetition_end_time=None):
    start_hour, start_minute = _parse_clock_time(start_time_str)
    exe_path, arguments, cwd = _resolve_command_arguments(mode)
    scheduler, _root_folder, task_folder = _connect_task_folder()

    task_def = scheduler.NewTask(0)
    task_def.RegistrationInfo.Description = description
    task_def.RegistrationInfo.Author = "ClassPush"

    task_def.Settings.Enabled = True
    task_def.Settings.StartWhenAvailable = True
    task_def.Settings.Hidden = False
    task_def.Settings.DisallowStartIfOnBatteries = False
    task_def.Settings.StopIfGoingOnBatteries = False
    task_def.Settings.MultipleInstances = 3
    task_def.Settings.AllowDemandStart = True

    triggers = task_def.Triggers
    trigger = triggers.Create(TASK_TRIGGER_DAILY)
    trigger.DaysInterval = 1

    now = datetime.datetime.now()
    start_time = now.replace(hour=start_hour, minute=start_minute, second=0, microsecond=0)
    if repetition_end_time:
        end_hour, end_minute = _parse_clock_time(repetition_end_time)
        current_minutes = now.hour * 60 + now.minute
        end_minutes = end_hour * 60 + end_minute
        if current_minutes > end_minutes:
            start_time = start_time + datetime.timedelta(days=1)

    trigger.StartBoundary = start_time.isoformat()
    if repetition_interval_minutes:
        trigger.Repetition.Interval = _build_interval_text(repetition_interval_minutes)
        trigger.Repetition.Duration = _build_repetition_duration(start_time_str, repetition_end_time or start_time_str)

    action = task_def.Actions.Create(TASK_ACTION_EXEC)
    action.Path = exe_path
    action.Arguments = arguments
    action.WorkingDirectory = cwd

    principal = task_def.Principal
    principal.LogonType = TASK_LOGON_INTERACTIVE_TOKEN
    principal.RunLevel = TASK_RUNLEVEL_LATEST

    task_folder.RegisterTaskDefinition(
        task_name,
        task_def,
        TASK_CREATE_OR_UPDATE,
        "",
        "",
        TASK_LOGON_INTERACTIVE_TOKEN,
        "",
    )


def _create_task_with_elevation(task_name, create_args, create_callback):
    try:
        create_callback()
        return True, "任务已创建"
    except Exception as e:
        error_msg = str(e)
        is_permission_error = "Access is denied" in error_msg or "拒绝访问" in error_msg or "-2147024891" in error_msg
        if is_permission_error:
            if not is_admin():
                logger.warning(f"当前权限不足，尝试请求管理员权限创建任务... (原错: {error_msg})")
                if run_as_admin(create_args):
                    for _ in range(10):
                        time.sleep(0.5)
                        if check_task_status(task_name):
                            return True, "已请求管理员权限创建任务"
                    return False, "已请求管理员权限，但任务似乎未创建 (用户取消或超时)"
                logger.error("请求管理员权限失败")
                return False, "请求管理员权限失败"

            logger.error(f"即使以管理员身份运行也无法创建任务，请检查系统策略: {error_msg}")
            return False, "即使以管理员身份运行也无法创建任务，请检查系统策略"

        logger.error(f"创建计划任务失败: {e}")
        return False, f"任务创建异常: {error_msg}"


def create_schedule_task(time_str):
    """创建课表自动推送任务。"""

    def _callback():
        _register_daily_task(
            COURSE_TASK_NAME,
            "ClassPush 自动课表推送任务",
            time_str,
            "--run-job",
        )

    success, message = _create_task_with_elevation(COURSE_TASK_NAME, f"--create-schedule {time_str}", _callback)
    if success:
        logger.info(f"课表计划任务创建成功: {time_str}")
        return True, "课表自动推送任务已创建"
    return False, message


def create_grade_schedule_task(start_time_str, interval_minutes=30, end_time_str="23:00"):
    """创建成绩自动轮询任务。"""

    def _callback():
        _register_daily_task(
            GRADE_TASK_NAME,
            "ClassPush 自动成绩轮询任务",
            start_time_str,
            "--run-grade-job",
            repetition_interval_minutes=interval_minutes,
            repetition_end_time=end_time_str,
        )

    create_args = f"--create-grade-schedule {start_time_str} {int(interval_minutes)} {end_time_str}"
    success, message = _create_task_with_elevation(GRADE_TASK_NAME, create_args, _callback)
    if success:
        logger.info(f"成绩计划任务创建成功: {start_time_str} 每 {interval_minutes} 分钟至 {end_time_str}")
        return True, "成绩自动轮询任务已创建"
    return False, message


def delete_schedule_task(task_name=COURSE_TASK_NAME):
    """删除计划任务。"""
    try:
        _scheduler, root_folder, task_folder = _connect_task_folder()
        try:
            task_folder.DeleteTask(task_name, 0)
            return True
        except Exception:
            pass

        try:
            root_folder.DeleteTask(task_name, 0)
            return True
        except Exception:
            pass

        return False
    except Exception as e:
        logger.error(f"删除任务失败: {e}")
        return False


def delete_grade_schedule_task():
    return delete_schedule_task(GRADE_TASK_NAME)


def check_task_status(task_name=COURSE_TASK_NAME):
    """检查计划任务是否存在。"""
    try:
        _scheduler, root_folder, task_folder = _connect_task_folder()
        try:
            task_folder.GetTask(task_name)
            return True
        except Exception:
            pass

        try:
            root_folder.GetTask(task_name)
            return True
        except Exception:
            pass

        return False
    except Exception:
        return False


def check_grade_task_status():
    return check_task_status(GRADE_TASK_NAME)
