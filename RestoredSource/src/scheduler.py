import sys
import os
import datetime
import time
import ctypes
import win32com.client
from logger import logger

TASK_NAME = "ClassPush_AutoRun"
TASK_FOLDER_NAME = "ClassPush"

# Task Scheduler Constants
TASK_TRIGGER_DAILY = 2
TASK_ACTION_EXEC = 0
TASK_CREATE_OR_UPDATE = 6
TASK_LOGON_INTERACTIVE_TOKEN = 3
TASK_LOGON_GROUP = 4
TASK_RUNLEVEL_LATEST = 0
TASK_RUNLEVEL_HIGHEST = 1

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def run_as_admin(args):
    """请求提权运行"""
    try:
        if getattr(sys, 'frozen', False):
            # 打包环境: ShellExecute runas exe "args"
            exe = sys.executable
            params = args
        else:
            # 开发环境: ShellExecute runas python "script args"
            exe = sys.executable
            script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "main.py")
            params = f'"{script}" {args}'
        
        # 使用 ShellExecute 提权运行
        # 1: SW_SHOWNORMAL
        ret = ctypes.windll.shell32.ShellExecuteW(None, "runas", exe, params, None, 1)
        return ret > 32
    except Exception as e:
        logger.error(f"提权失败: {e}")
        return False

def create_schedule_task(time_str):
    """
    创建 Windows 计划任务 (使用 COM 接口，更稳定且支持更多配置)
    :param time_str: 推送时间 (e.g. "07:00")
    """
    try:
        # 1. 解析时间
        try:
            hour, minute = map(int, time_str.split(':'))
        except ValueError:
            return False, "时间格式错误，应为 HH:mm"

        # 2. 获取运行路径和参数
        if getattr(sys, 'frozen', False):
            # 打包环境
            exe_path = sys.executable
            arguments = "--run-job"
            cwd = os.path.dirname(exe_path)
        else:
            # 开发环境
            exe_path = sys.executable
            script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "main.py")
            arguments = f'"{script_path}" --run-job'
            cwd = os.path.dirname(script_path)

        # 3. 连接任务计划服务
        scheduler = win32com.client.Dispatch("Schedule.Service")
        scheduler.Connect()
        
        root_folder = scheduler.GetFolder("\\")
        task_folder = root_folder
        
        # 尝试创建文件夹，如果失败则静默使用根目录
        try:
            try:
                task_folder = root_folder.GetFolder(f"\\{TASK_FOLDER_NAME}")
            except Exception:
                task_folder = root_folder.CreateFolder(f"\\{TASK_FOLDER_NAME}")
        except Exception:
            # 权限不足无法创建文件夹，直接使用根目录
            task_folder = root_folder

        # 4. 定义任务
        task_def = scheduler.NewTask(0)
        
        # 4.1 注册信息
        task_def.RegistrationInfo.Description = "ClassPush 自动推送任务"
        task_def.RegistrationInfo.Author = "ClassPush"
        
        # 4.2 设置 (关键配置)
        task_def.Settings.Enabled = True
        task_def.Settings.StartWhenAvailable = True  # 错过时间后尽快运行
        task_def.Settings.Hidden = False
        task_def.Settings.DisallowStartIfOnBatteries = False # 允许电池供电运行
        task_def.Settings.StopIfGoingOnBatteries = False     # 切换到电池不停止
        task_def.Settings.MultipleInstances = 3 # TASK_INSTANCES_STOP_EXISTING
        task_def.Settings.AllowDemandStart = True
        
        # 4.3 触发器
        triggers = task_def.Triggers
        trigger = triggers.Create(TASK_TRIGGER_DAILY)
        trigger.DaysInterval = 1
        
        now = datetime.datetime.now()
        start_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        trigger.StartBoundary = start_time.isoformat()
        
        # 4.4 操作
        action = task_def.Actions.Create(TASK_ACTION_EXEC)
        action.Path = exe_path
        action.Arguments = arguments
        action.WorkingDirectory = cwd
        
        # 4.5 主体权限
        principal = task_def.Principal
        principal.LogonType = TASK_LOGON_INTERACTIVE_TOKEN 
        principal.RunLevel = TASK_RUNLEVEL_LATEST

        # 5. 注册任务
        task_folder.RegisterTaskDefinition(
            TASK_NAME,
            task_def,
            TASK_CREATE_OR_UPDATE,
            "", 
            "", 
            TASK_LOGON_INTERACTIVE_TOKEN,
            ""
        )
        
        logger.info(f"计划任务创建成功: {time_str}")
        return True, "任务已创建 (若错过时间将在下次开机登录后运行)"
        
    except Exception as e:
        error_msg = str(e)
        # 检查是否是权限错误 (Access Denied / 拒绝访问 / 0x80070005)
        # -2147024891 == 0x80070005
        is_permission_error = "Access is denied" in error_msg or "拒绝访问" in error_msg or "-2147024891" in error_msg

        if is_permission_error:
             # 尝试提权运行
            if not is_admin():
                logger.warning(f"当前权限不足，尝试请求管理员权限创建任务... (原错: {error_msg})")
                if run_as_admin(f"--create-schedule {time_str}"):
                    # 等待并检查任务是否创建成功
                    for _ in range(10):
                        time.sleep(0.5)
                        if check_task_status():
                            return True, "已请求管理员权限创建任务"
                    return False, "已请求管理员权限，但任务似乎未创建 (用户取消或超时)"
                else:
                    logger.error("请求管理员权限失败")
                    return False, "请求管理员权限失败"
            else:
                logger.error(f"即使以管理员身份运行也无法创建任务，请检查系统策略: {error_msg}")
                return False, "即使以管理员身份运行也无法创建任务，请检查系统策略"
        
        # 其他错误才记录 ERROR
        logger.error(f"创建计划任务失败: {e}")
        return False, f"任务创建异常: {error_msg}"

def delete_schedule_task():
    """删除计划任务"""
    try:
        scheduler = win32com.client.Dispatch("Schedule.Service")
        scheduler.Connect()
        root_folder = scheduler.GetFolder("\\")
        
        # 尝试从专用文件夹删除
        try:
            task_folder = root_folder.GetFolder(f"\\{TASK_FOLDER_NAME}")
            task_folder.DeleteTask(TASK_NAME, 0)
            return True
        except Exception:
            pass
            
        # 尝试从根目录删除 (兼容旧版本)
        try:
            root_folder.DeleteTask(TASK_NAME, 0)
            return True
        except Exception:
            pass
            
        return False
    except Exception as e:
        logger.error(f"删除任务失败: {e}")
        return False

def check_task_status():
    """检查任务是否存在"""
    try:
        scheduler = win32com.client.Dispatch("Schedule.Service")
        scheduler.Connect()
        root_folder = scheduler.GetFolder("\\")
        
        # 检查专用文件夹
        try:
            task_folder = root_folder.GetFolder(f"\\{TASK_FOLDER_NAME}")
            task_folder.GetTask(TASK_NAME)
            return True
        except Exception:
            pass
            
        # 检查根目录
        try:
            root_folder.GetTask(TASK_NAME)
            return True
        except Exception:
            pass
            
        return False
    except Exception:
        return False
