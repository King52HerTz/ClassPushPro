import json
import threading
import re
from logger import logger
from config_manager import ConfigManager
from login_manager import LoginManager
from real_scraper import CourseScraper
from run_job import run_push_task
from autostart import set_autostart, check_autostart
from scheduler import create_schedule_task, delete_schedule_task, check_task_status

class Api:
    def __init__(self):
        self.config = ConfigManager()

    def ignore_missed_push(self, date_str):
        """标记某天的补发提醒为已忽略 (YYYY-MM-DD)"""
        try:
            if not isinstance(date_str, str) or not date_str:
                return {"status": "error", "message": "参数无效"}

            if not re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
                return {"status": "error", "message": "日期格式无效"}

            ok = self.config.update_last_ignored_date(date_str)
            return {"status": "success" if ok else "error", "message": "已忽略" if ok else "保存失败"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def get_config(self):
        return {
            "status": "success",
            "data": self.config.config_data
        }

    def save_config(self, data):
        """保存配置"""
        try:
            username = data.get("username")
            password = data.get("password")
            app_token = data.get("app_token")
            uid = data.get("uid")
            push_time = data.get("push_time", "07:00")
            auto_start = data.get("auto_start", False)
            
            success = self.config.save_config(
                username, password, app_token, uid, push_time, auto_start
            )
            
            # 更新自启动
            set_autostart(auto_start)
            
            # 更新计划任务
            warning_msg = ""
            if success:
                delete_schedule_task()
                task_success, task_msg = create_schedule_task(push_time)
                if not task_success:
                    logger.error(f"计划任务创建失败: {task_msg}")
                    warning_msg = f" (注意: 自动推送任务创建失败 - {task_msg})"
            
            return {
                "status": "success" if success else "error", 
                "message": ("保存成功" + warning_msg) if success else "保存失败"
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def login_test(self, username, password):
        """测试登录"""
        mgr = LoginManager()
        success, msg = mgr.login(username, password)
        return {
            "status": "success" if success else "error", 
            "message": msg,
            "data": mgr.get_user_info() if success else {}
        }

    def get_preview_courses(self):
        """获取课表预览数据"""
        username = self.config.get("username")
        password = self.config.get("password")
        
        if not username or not password:
            return {"status": "error", "message": "请先保存账号密码"}
            
        mgr = LoginManager(self.config)
        success, msg = mgr.login(username, password, use_cache=True)
        
        # 尝试网络请求
        if success:
            try:
                scraper = CourseScraper(mgr.get_token(), session=mgr.session)
                current_week = scraper.fetch_current_week()
                courses = scraper.fetch_course_data()
                
                if courses:
                    # 成功获取到数据，更新缓存
                    self.config.save_cached_courses(courses, current_week)
                    return {
                        "status": "success",
                        "data": {
                            "currentWeek": current_week,
                            "courses": courses,
                            "source": "online"
                        }
                    }
            except Exception as e:
                logger.warning(f"在线抓取失败，尝试读取缓存: {e}")
        
        # 网络请求失败或登录失败，尝试读取缓存
        cached_data = self.config.get_cached_courses()
        if cached_data:
            import time
            update_time = cached_data.get("update_time", 0)
            time_diff = int(time.time()) - update_time
            time_str = "刚刚"
            if time_diff > 60:
                time_str = f"{time_diff // 60}分钟前"
            if time_diff > 3600:
                time_str = f"{time_diff // 3600}小时前"
            if time_diff > 86400:
                time_str = f"{time_diff // 86400}天前"
                
            return {
                "status": "success",
                "data": {
                    "currentWeek": cached_data.get("current_week", "1"),
                    "courses": cached_data.get("courses", []),
                    "source": "offline",
                    "update_time_str": time_str
                },
                "message": f"网络连接失败，已加载缓存数据 ({time_str})"
            }
            
        return {"status": "error", "message": f"获取失败: {msg} 且无本地缓存"}

    def check_today_pushed(self):
        """检查今日是否已成功推送"""
        # 强制从文件重新加载最新配置，因为后台任务可能修改了配置文件
        self.config.load_config()
        
        last_push_time = self.config.get("last_push_success_time", "")
        logger.info(f"[Check] last_push_success_time: {last_push_time}")
        
        if not last_push_time:
            logger.info("[Check] Result: False (No last_push_time)")
            return {"status": "success", "pushed": False}
            
        try:
            from datetime import datetime
            last_dt = datetime.strptime(last_push_time, "%Y-%m-%d %H:%M:%S")
            is_today = last_dt.date() == datetime.now().date()
            logger.info(f"[Check] Result: {is_today} (Last: {last_dt.date()}, Today: {datetime.now().date()})")
            return {"status": "success", "pushed": is_today, "last_time": last_push_time}
        except Exception as e:
            logger.error(f"[Check] Error parsing date: {e}")
            return {"status": "success", "pushed": False}

    def manual_push(self, force=True):
        """手动触发推送 (同步执行)"""
        try:
            success, msg = run_push_task(force=force, source="manual")
            # 任务执行完毕后，强制刷新内存中的配置，确保下次 check 准确
            self.config.load_config()
            
            if success:
                return {"status": "success", "message": "推送成功，请查看手机消息"}
            else:
                return {"status": "error", "message": f"推送失败: {msg}"}
        except Exception as e:
            return {"status": "error", "message": f"推送异常: {e}"}

    def set_autostart(self, enable):
        """独立设置自启动状态"""
        try:
            success, msg = set_autostart(enable)
            # 同时更新配置文件中的状态
            current_config = self.config.config_data
            self.config.save_config(
                current_config.get("username", ""),
                current_config.get("password", ""),
                current_config.get("app_token", ""),
                current_config.get("uid", ""),
                current_config.get("push_time", "07:00"),
                enable
            )
            return {"status": "success" if success else "error", "message": msg}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def toggle_scheduler(self, enable):
        """开启或停止自动推送"""
        try:
            if enable:
                push_time = self.config.get("push_time", "07:00")
                delete_schedule_task() # 先删除旧的
                success, msg = create_schedule_task(push_time)
                if success:
                    return {"status": "success", "message": "自动推送已开启"}
                else:
                    return {"status": "error", "message": f"开启失败: {msg}"}
            else:
                if delete_schedule_task():
                    return {"status": "success", "message": "自动推送已停止"}
                else:
                    # 如果任务本来就不存在，也算成功
                    if not check_task_status():
                        return {"status": "success", "message": "自动推送已停止"}
                    return {"status": "error", "message": "停止失败"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def get_system_status(self):
        """获取系统状态"""
        return {
            "status": "success",
            "data": {
                "autostart": check_autostart(),
                "scheduler_active": check_task_status()
            }
        }
