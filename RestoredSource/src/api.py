import json
import threading
import re
import os
import requests
from urllib.parse import unquote, urlparse
from datetime import datetime, timedelta
from logger import logger
from calendar_exporter import CalendarExporter
from config_manager import ConfigManager
from content_service import WeatherContentService
from grade_service import GradeService
from login_manager import LoginManager
from real_scraper import CourseScraper
from academic_calendar import merge_cached_teaching_state
from run_job import run_push_task
from autostart import set_autostart, check_autostart
from scheduler import (
    create_grade_schedule_task,
    create_schedule_task,
    delete_grade_schedule_task,
    delete_schedule_task,
    check_grade_task_status,
    check_task_status,
)

class Api:
    def __init__(self):
        self.config = ConfigManager()
        self.grade_service = GradeService(self.config)
        self.weather_service = WeatherContentService(self.config)

    def _looks_like_network_error(self, message):
        text = str(message or "")
        keywords = [
            "网络请求异常",
            "NameResolutionError",
            "getaddrinfo failed",
            "连接",
            "超时",
            "timeout",
        ]
        return any(keyword in text for keyword in keywords)

    def check_update(self):
        """由 Python 请求版本信息，避免 WebView 跨域限制导致前端 fetch 失败。"""
        version_url = "https://classpush.eliauk312.top/version.json"
        try:
            response = requests.get(
                version_url,
                headers={"Cache-Control": "no-cache", "Pragma": "no-cache"},
                timeout=(8, 12),
            )
            response.raise_for_status()
            data = response.json()
            if not isinstance(data, dict) or not data.get("version") or not data.get("download_url"):
                return {"status": "error", "message": "服务器返回的版本信息不完整"}
            return {"status": "success", "data": data}
        except requests.RequestException as e:
            logger.warning(f"检查更新网络请求失败: {e}")
            return {"status": "error", "message": "暂时无法连接更新服务器，请稍后重试"}
        except ValueError:
            logger.warning("检查更新失败: version.json 不是有效 JSON")
            return {"status": "error", "message": "服务器版本信息格式有误"}

    def download_update(self):
        """下载更新包到用户的 Downloads/ClassPush 目录。

        版本配置目前可能给出一个网页下载页（例如蓝奏云），这种地址不能由
        后台直接当作安装包保存，因此交给前端打开网页；如果配置的是直链
        .exe，则由程序直接下载。
        """
        update_result = self.check_update()
        if update_result.get("status") != "success":
            return update_result

        update_data = update_result.get("data") or {}
        download_url = str(update_data.get("download_url") or "").strip()
        parsed_url = urlparse(download_url)
        path_name = os.path.basename(unquote(parsed_url.path or ""))
        if parsed_url.scheme.lower() != "https" or not parsed_url.netloc or not path_name.lower().endswith(".exe"):
            return {
                "status": "error",
                "message": "当前下载源需要在网页中完成下载，请打开官方下载页继续",
                "action": "open_download_page",
                "data": {"download_url": download_url},
            }

        safe_name = re.sub(r"[^0-9A-Za-z._-]", "_", path_name) or "ClassPush_Setup.exe"
        if not safe_name.lower().endswith(".exe"):
            safe_name = "ClassPush_Setup.exe"
        download_dir = os.path.join(os.path.expanduser("~"), "Downloads", "ClassPush")
        file_path = os.path.join(download_dir, safe_name)
        partial_path = f"{file_path}.part"
        max_size = 300 * 1024 * 1024

        try:
            os.makedirs(download_dir, exist_ok=True)
            with requests.get(download_url, stream=True, timeout=(10, 60)) as response:
                response.raise_for_status()
                content_length = int(response.headers.get("Content-Length") or 0)
                if content_length > max_size:
                    return {"status": "error", "message": "更新包超过 300 MB，已停止下载"}

                downloaded = 0
                with open(partial_path, "wb") as output:
                    for chunk in response.iter_content(chunk_size=1024 * 1024):
                        if not chunk:
                            continue
                        downloaded += len(chunk)
                        if downloaded > max_size:
                            raise ValueError("更新包超过 300 MB")
                        output.write(chunk)

            if downloaded < 2:
                raise ValueError("下载内容为空")
            with open(partial_path, "rb") as package_file:
                if package_file.read(2) != b"MZ":
                    raise ValueError("下载内容不是有效的 Windows 安装包")
            os.replace(partial_path, file_path)
            return {
                "status": "success",
                "message": "更新包下载完成",
                "data": {
                    "file_path": file_path,
                    "file_name": safe_name,
                    "version": str(update_data.get("version") or ""),
                },
            }
        except requests.RequestException:
            logger.warning("更新包下载网络请求失败")
            return {"status": "error", "message": "更新包下载失败，请检查网络后重试"}
        except (OSError, ValueError) as e:
            logger.warning(f"更新包保存失败: {e}")
            return {"status": "error", "message": "更新包下载失败，请稍后重试"}
        finally:
            if os.path.exists(partial_path):
                try:
                    os.remove(partial_path)
                except OSError:
                    pass

    def _sync_schedule_tasks(self):
        warning_messages = []

        delete_schedule_task()
        push_time = self.config.get("push_time", "07:00")
        course_success, course_msg = create_schedule_task(push_time)
        if not course_success:
            logger.error(f"课表计划任务创建失败: {course_msg}")
            warning_messages.append(f"课表任务创建失败 - {course_msg}")

        delete_grade_schedule_task()
        if self.config.get("grade_push_enabled", False):
            grade_success, grade_msg = create_grade_schedule_task(
                self.config.get("grade_check_start_time", "07:00"),
                self.config.get("grade_check_interval_minutes", 30),
                self.config.get("grade_check_end_time", "23:00"),
            )
            if not grade_success:
                logger.error(f"成绩计划任务创建失败: {grade_msg}")
                warning_messages.append(f"成绩任务创建失败 - {grade_msg}")

        return warning_messages

    def _safe_week_number(self, value):
        try:
            return max(int(value), 1)
        except (TypeError, ValueError):
            return 1

    def _parse_semester_start_date(self, value):
        text = str(value or "").strip()
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", text):
            return None
        try:
            return datetime.strptime(text, "%Y-%m-%d").date()
        except ValueError:
            return None

    def _resolve_export_constraints(self, scope, current_week, semester_start_date):
        current_week_num = self._safe_week_number(current_week)
        normalized_scope = str(scope or "term").strip().lower()

        if normalized_scope == "current_week":
            return {
                "scope": "current_week",
                "scope_label": "本周",
                "allowed_weeks": {current_week_num},
                "date_range": None,
            }

        if normalized_scope == "next_7_days":
            today = datetime.now().date()
            range_end = today + timedelta(days=6)
            return {
                "scope": "next_7_days",
                "scope_label": "未来 7 天",
                "allowed_weeks": None,
                "date_range": (today, range_end),
            }

        return {
            "scope": "term",
            "scope_label": "全学期",
            "allowed_weeks": None,
            "date_range": None,
        }

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
            weather_enabled = data.get("weather_enabled", False)
            weather_city = data.get("weather_city", "")
            weather_credential_id = data.get("weather_credential_id", "")
            weather_api_host = data.get("weather_api_host", "")
            weather_api_key = data.get("weather_api_key", "")
            grade_push_enabled = data.get("grade_push_enabled", False)
            grade_check_interval_minutes = data.get("grade_check_interval_minutes", 30)
            grade_check_start_time = data.get("grade_check_start_time", "07:00")
            grade_check_end_time = data.get("grade_check_end_time", "23:00")
            semester_start_date = data.get("semester_start_date", "")
            time_slots = data.get("time_slots")
            calendar_alarm_minutes = data.get("calendar_alarm_minutes", 15)
            
            success = self.config.save_config(
                username,
                password,
                app_token,
                uid,
                push_time,
                auto_start,
                semester_start_date,
                time_slots,
                calendar_alarm_minutes,
                weather_enabled=weather_enabled,
                weather_city=weather_city,
                weather_credential_id=weather_credential_id,
                weather_api_host=weather_api_host,
                weather_api_key=weather_api_key,
                grade_push_enabled=grade_push_enabled,
                grade_check_interval_minutes=grade_check_interval_minutes,
                grade_check_start_time=grade_check_start_time,
                grade_check_end_time=grade_check_end_time,
            )
            
            # 更新自启动
            set_autostart(auto_start)
            
            # 更新计划任务
            warning_msg = ""
            if success:
                warning_messages = self._sync_schedule_tasks()
                if warning_messages:
                    warning_msg = " (注意: " + "；".join(warning_messages) + ")"
            
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
                semester_info = scraper.fetch_semester_info()
                teaching_state = scraper.fetch_teaching_state(semester_info)
                current_week = teaching_state.get("current_week")
                semester_id = teaching_state.get("semester_id", "")
                courses = scraper.fetch_course_data(semester_id=semester_id)

                if teaching_state.get("schedule_status") == "active" and not courses:
                    teaching_state = {
                        **teaching_state,
                        "schedule_status": "unpublished",
                        "is_teaching_week": False,
                        "message": "当前学期课表暂未发布，请稍后再试",
                    }

                if courses or teaching_state.get("schedule_status") != "unknown":
                    # 即使处于假期也保存明确状态，避免下次离线误用旧课表。
                    self.config.save_cached_courses(
                        courses,
                        current_week,
                        semester_id=semester_id,
                        teaching_state=teaching_state,
                    )
                    return {
                        "status": "success",
                        "data": {
                            "currentWeek": current_week or "",
                            "courses": courses,
                            "source": "online",
                            "scheduleStatus": teaching_state.get("schedule_status", "unknown"),
                            "isTeachingWeek": bool(teaching_state.get("is_teaching_week", False)),
                            "semesterId": semester_id,
                            "semesterName": teaching_state.get("semester_name", ""),
                            "weekOneMonday": teaching_state.get("week_one_monday", ""),
                            "availableWeeks": teaching_state.get("available_weeks", []),
                            "scheduleMessage": teaching_state.get("message", ""),
                        }
                    }
            except Exception as e:
                logger.warning(f"在线抓取失败，尝试读取缓存: {e}")
        
        # 网络请求失败或登录失败，尝试读取缓存
        cached_data = self.config.get_cached_courses()
        if cached_data:
            teaching_state = merge_cached_teaching_state(cached_data)
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
                    "currentWeek": teaching_state.get("current_week") or "",
                    "courses": cached_data.get("courses", []),
                    "source": "offline",
                    "update_time_str": time_str,
                    "scheduleStatus": teaching_state.get("schedule_status", "unknown"),
                    "isTeachingWeek": bool(teaching_state.get("is_teaching_week", False)),
                    "semesterId": teaching_state.get("semester_id", ""),
                    "semesterName": teaching_state.get("semester_name", ""),
                    "weekOneMonday": teaching_state.get("week_one_monday", ""),
                    "availableWeeks": teaching_state.get("available_weeks", []),
                    "scheduleMessage": teaching_state.get("message", ""),
                },
                "message": f"网络不可用，正在显示{time_str}的本地课表缓存"
            }

        if self._looks_like_network_error(msg):
            return {"status": "error", "message": "当前暂无本地课表缓存，请联网后首次加载"}
        return {"status": "error", "message": f"获取失败: {msg}"}

    def export_calendar_ics(self, scope="term"):
        """导出当前课表为 ICS 文件"""
        try:
            cached_data = self.config.get_cached_courses()
            if not cached_data:
                preview_result = self.get_preview_courses()
                if preview_result.get("status") != "success":
                    return {"status": "error", "message": preview_result.get("message", "课表数据不可用")}
                cached_data = {
                    "current_week": preview_result.get("data", {}).get("currentWeek", "1"),
                    "courses": preview_result.get("data", {}).get("courses", []),
                }

            courses = cached_data.get("courses", [])
            current_week = cached_data.get("current_week", "1")
            if not courses:
                return {"status": "error", "message": "暂无可导出的课表数据"}

            semester_start_date = (
                cached_data.get("week_one_monday", "")
                or self.config.get("semester_start_date", "")
            )
            time_slots = self.config.get("time_slots", {})
            calendar_alarm_minutes = self.config.get("calendar_alarm_minutes", 15)
            export_constraints = self._resolve_export_constraints(scope, current_week, semester_start_date)
            exporter = CalendarExporter(
                semester_start_date,
                time_slots,
                courses,
                current_week=current_week,
                alarm_minutes=calendar_alarm_minutes,
                allowed_weeks=export_constraints["allowed_weeks"],
                date_range=export_constraints["date_range"],
            )

            export_dir = os.path.join(os.path.expanduser("~"), "Downloads", "ClassPush")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            scope_suffix = export_constraints["scope"]
            file_path = os.path.join(export_dir, f"classpush_schedule_{scope_suffix}_{timestamp}.ics")
            exporter.export_to_file(file_path)

            if exporter.exported_event_count <= 0:
                return {
                    "status": "error",
                    "message": f"{export_constraints['scope_label']}内没有可导出的课程，请换一个范围再试",
                }

            return {
                "status": "success",
                "message": "导出成功",
                "data": {
                    "file_path": file_path,
                    "file_name": os.path.basename(file_path),
                    "course_count": exporter.exported_event_count,
                    "export_scope": export_constraints["scope"],
                    "export_scope_label": export_constraints["scope_label"],
                },
            }
        except Exception as e:
            logger.exception("导出 ICS 失败")
            return {"status": "error", "message": f"导出 ICS 失败: {e}"}

    def get_grade_semesters(self):
        """获取成绩学期列表"""
        try:
            result = self.grade_service.get_grade_semesters()
            return {"status": "success", "data": result}
        except Exception as e:
            logger.exception("获取成绩学期列表失败")
            return {"status": "error", "message": f"获取成绩学期失败: {e}"}

    def get_grades(self, semester_id=None):
        """获取某学期成绩"""
        try:
            result = self.grade_service.get_grades(semester_id=semester_id)
            return {"status": "success", "data": result}
        except Exception as e:
            logger.exception("获取成绩失败")
            return {"status": "error", "message": f"获取成绩失败: {e}"}

    def refresh_grades(self, semester_id=None):
        """强制刷新某学期成绩"""
        try:
            result = self.grade_service.refresh_grades(semester_id=semester_id)
            return {"status": "success", "data": result, "message": "刷新成功"}
        except Exception as e:
            logger.exception("刷新成绩失败")
            return {"status": "error", "message": f"刷新成绩失败: {e}"}

    def check_new_grades(self):
        """检查当前学期是否有新增成绩"""
        try:
            result = self.grade_service.check_new_grades()
            new_count = len(result.get("new_items", []))
            push_message = result.get("push_result", {}).get("message", "")
            if new_count > 0:
                message = f"检查完成，发现 {new_count} 条新增成绩"
            else:
                message = push_message or "检查完成，当前没有新增成绩"
            return {"status": "success", "data": result, "message": message}
        except Exception as e:
            logger.exception("检查新成绩失败")
            return {"status": "error", "message": f"检查新成绩失败: {e}"}

    def manual_grade_push(self):
        """手动发送当前学期全部成绩，不修改成绩检测基线"""
        try:
            success, message = self.grade_service.send_current_term_grades()
            return {
                "status": "success" if success else "error",
                "message": "本学期成绩已发送，请检查手机" if success else message,
            }
        except Exception as e:
            logger.exception("手动发送本学期成绩失败")
            return {"status": "error", "message": f"成绩推送失败: {e}"}

    def save_grade_push_settings(self, enable):
        """保存成绩自动推送开关"""
        try:
            success = self.grade_service.save_grade_push_settings(enable=enable)
            warning_msg = ""
            if success:
                if enable:
                    task_success, task_msg = create_grade_schedule_task(
                        self.config.get("grade_check_start_time", "07:00"),
                        self.config.get("grade_check_interval_minutes", 30),
                        self.config.get("grade_check_end_time", "23:00"),
                    )
                    if not task_success:
                        warning_msg = f" (注意: 成绩任务创建失败 - {task_msg})"
                else:
                    delete_grade_schedule_task()
            return {
                "status": "success" if success else "error",
                "message": ("保存成功" + warning_msg) if success else "保存失败",
            }
        except Exception as e:
            logger.exception("保存成绩推送设置失败")
            return {"status": "error", "message": str(e)}

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
                message = str(msg or "未知错误")
                if not message.startswith("推送失败"):
                    message = f"推送失败: {message}"
                return {"status": "error", "message": message}
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
                enable,
                current_config.get("semester_start_date", ""),
                current_config.get("time_slots"),
                current_config.get("calendar_alarm_minutes", 15),
                weather_enabled=current_config.get("weather_enabled", False),
                weather_city=current_config.get("weather_city", ""),
                weather_credential_id=current_config.get("weather_credential_id", ""),
                weather_api_host=current_config.get("weather_api_host", ""),
                weather_api_key=current_config.get("weather_api_key", ""),
                grade_push_enabled=current_config.get("grade_push_enabled", False),
                grade_check_interval_minutes=current_config.get("grade_check_interval_minutes", 30),
                grade_check_start_time=current_config.get("grade_check_start_time", "07:00"),
                grade_check_end_time=current_config.get("grade_check_end_time", "23:00"),
                grade_push_initialized=current_config.get("grade_push_initialized", False),
            )
            return {"status": "success" if success else "error", "message": msg}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def toggle_scheduler(self, enable):
        """开启或停止自动推送"""
        try:
            if enable:
                warning_messages = self._sync_schedule_tasks()
                if warning_messages:
                    return {"status": "error", "message": "开启失败: " + "；".join(warning_messages)}
                return {"status": "success", "message": "自动推送已开启"}
            else:
                delete_schedule_task()
                delete_grade_schedule_task()
                if not check_task_status() and not check_grade_task_status():
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
                "scheduler_active": check_task_status(),
                "grade_scheduler_active": check_grade_task_status(),
            }
        }
