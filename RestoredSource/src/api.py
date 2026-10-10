import json
import re
import os
import requests
from urllib.parse import unquote, urlparse
from datetime import datetime, timedelta
from logger import logger
from calendar_exporter import CalendarExporter
from config_manager import ConfigManager
from grade_service import GradeService
from login_manager import LoginManager
from real_scraper import CourseScraper
from academic_calendar import merge_cached_teaching_state

class Api:
    def __init__(self):
        self.config = ConfigManager()
        self.grade_service = GradeService(self.config)

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
        from academic_calendar import week_number_for_date
        current_week_num = week_number_for_date(semester_start_date, datetime.now().date())
        normalized_scope = str(scope or "term").strip().lower()

        if normalized_scope == "current_week":
            return {
                "scope": "current_week",
                "scope_label": "本周",
                "allowed_weeks": {current_week_num} if current_week_num else set(),
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


    def get_config(self):
        return {
            "status": "success",
            "data": {**{key: value for key, value in self.config.config_data.items()
                     if key in {"username", "semester_start_date", "time_slots", "calendar_alarm_minutes"}},
                     "has_password": bool(self.config.get("password"))}
        }

    def save_config(self, data):
        """Local queries and calendar preferences only; never enable a push task."""
        try:
            old_username = self.config.get("username", "")
            username = data.get("username", old_username)
            password = data.get("password", self.config.get("password", ""))
            success = self.config.save_config(
                username, password,
                data.get("semester_start_date", self.config.get("semester_start_date", "")),
                data.get("time_slots", self.config.get("time_slots")),
                data.get("calendar_alarm_minutes", self.config.get("calendar_alarm_minutes", 15)),
            )
            if success and username != old_username:
                self.config.config_data["cached_courses_data"] = ""
                self.config._save_current_config()
                # A grade snapshot from another student is never an offline fallback.
                self.grade_service.save_grade_cache(self.grade_service._empty_cache())
            return {"status": "success" if success else "error", "message": "已保存" if success else "保存失败"}
        except Exception:
            return {"status": "error", "message": "保存失败，请检查本地数据目录权限"}

    def open_cloud_portal(self):
        import webbrowser
        webbrowser.open("https://classpush.eliauk312.top/cloud.html")
        return {"status": "success", "message": "已打开官网云端管理"}

    def open_calendar_guide(self):
        import webbrowser
        webbrowser.open("https://classpush.eliauk312.top/calendar.html")
        return {"status": "success"}

    def open_export_folder(self):
        folder = os.path.join(os.path.expanduser("~"), "Downloads", "ClassPush")
        if os.path.isdir(folder):
            os.startfile(folder)
            return {"status": "success"}
        return {"status": "error", "message": "请先导出日历"}

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
            preview_result = self.get_preview_courses()
            if preview_result.get("status") != "success":
                return preview_result
            cached_data = self.config.get_cached_courses()
            if not cached_data:
                preview_result = self.get_preview_courses()
                if preview_result.get("status") != "success":
                    return {"status": "error", "message": preview_result.get("message", "课表数据不可用")}
                cached_data = {
                    "current_week": preview_result.get("data", {}).get("currentWeek", "1"),
                    "courses": preview_result.get("data", {}).get("courses", []),
                    "week_one_monday": preview_result.get("data", {}).get("weekOneMonday", ""),
                }

            courses = cached_data.get("courses", [])
            current_week = cached_data.get("current_week", "1")
            if not courses:
                return {"status": "error", "message": "暂无可导出的课表数据"}

            semester_start_date = (
                cached_data.get("week_one_monday", "")
            )
            if not self._parse_semester_start_date(semester_start_date):
                return {"status": "error", "message": "学期第一周日期尚未确认，请先刷新课表；不会猜测日期导出"}
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
                    "source": preview_result.get("data", {}).get("source", "online"),
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





