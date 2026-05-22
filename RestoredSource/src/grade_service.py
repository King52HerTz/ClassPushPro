import copy
import json
import os
from datetime import datetime

from config_manager import ConfigManager
from grade_scraper import GradeScraper
from logger import logger
from login_manager import LoginManager
from pusher import Pusher


class GradeService:
    """
    负责成绩缓存、对比检测和推送组装
    """

    def __init__(self, config_manager=None):
        self.config = config_manager if config_manager else ConfigManager()
        base_dir = os.path.dirname(self.config.config_path)
        self.cache_path = os.path.join(base_dir, "grades_cache.json")

    def load_grade_cache(self):
        if not os.path.exists(self.cache_path):
            return self._empty_cache()

        try:
            with open(self.cache_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return self._normalize_cache_shape(data)
        except Exception:
            logger.exception("成绩缓存加载失败")
            return self._empty_cache()

    def save_grade_cache(self, cache_data):
        try:
            normalized = self._normalize_cache_shape(cache_data)
            with open(self.cache_path, "w", encoding="utf-8") as f:
                json.dump(normalized, f, ensure_ascii=False, indent=2)
            return True
        except Exception:
            logger.exception("成绩缓存保存失败")
            return False

    def get_grade_semesters(self):
        try:
            scraper = self._create_scraper()
            current_term = scraper.get_current_term()
            semester_list = scraper.get_semester_list()
            selected_semester = self._resolve_selected_semester(None, current_term, semester_list)
            term_data = scraper.get_term_grades(
                selected_semester["semester_id"],
                selected_semester["semester_name"],
            )

            cache_data = self.load_grade_cache()
            cache_data["current_term"] = current_term
            cache_data["semester_list"] = semester_list
            cache_data["last_check_time"] = self._now_str()
            self._upsert_semester_snapshot(cache_data, term_data)
            self.save_grade_cache(cache_data)

            return {
                "current_term": current_term,
                "semester_list": semester_list,
                "selected_semester": {
                    "semester_id": term_data["semester_id"],
                    "semester_name": term_data["semester_name"],
                },
                "student_info": term_data.get("student_info", {}),
                "summary": term_data.get("summary", {}),
                "grades": term_data.get("grades", []),
                "source": "online",
                "update_time_str": "刚刚",
            }
        except Exception as e:
            logger.warning(f"在线获取成绩学期失败，尝试读取缓存: {e}")
            cache_data = self.load_grade_cache()
            cached_response = self._build_response_from_cache(cache_data, None)
            if cached_response:
                cached_response["source"] = "offline"
                cached_response["update_time_str"] = self._resolve_cached_update_time(
                    cache_data,
                    cached_response.get("selected_semester", {}).get("semester_id", ""),
                )
                return cached_response

            semester_list = self._get_effective_semester_list(cache_data)
            current_term = cache_data.get("current_term", {})
            if semester_list:
                return {
                    "current_term": current_term,
                    "semester_list": semester_list,
                    "source": "offline",
                    "update_time_str": self._format_relative_time(cache_data.get("last_check_time", "")),
                }
            raise

    def get_grades(self, semester_id=None):
        try:
            return self.refresh_grades(semester_id=semester_id)
        except Exception as e:
            logger.warning(f"在线获取成绩失败，尝试读取缓存: {e}")
            cache_data = self.load_grade_cache()
            cached_response = self._build_response_from_cache(cache_data, semester_id)
            if cached_response:
                cached_response["source"] = "offline"
                cached_response["update_time_str"] = self._resolve_cached_update_time(cache_data, semester_id)
                return cached_response
            raise

    def refresh_grades(self, semester_id=None):
        scraper = self._create_scraper()
        current_term = scraper.get_current_term()
        semester_list = scraper.get_semester_list()
        selected_semester = self._resolve_selected_semester(semester_id, current_term, semester_list)
        term_data = scraper.get_term_grades(
            selected_semester["semester_id"],
            selected_semester["semester_name"],
        )

        cache_data = self.load_grade_cache()
        cache_data["current_term"] = current_term
        cache_data["semester_list"] = semester_list
        cache_data["last_check_time"] = self._now_str()
        self._upsert_semester_snapshot(cache_data, term_data)
        self.save_grade_cache(cache_data)

        return {
            "current_term": current_term,
            "semester_list": semester_list,
            "selected_semester": {
                "semester_id": term_data["semester_id"],
                "semester_name": term_data["semester_name"],
            },
            "student_info": term_data.get("student_info", {}),
            "summary": term_data.get("summary", {}),
            "grades": term_data.get("grades", []),
            "source": "online",
            "update_time_str": "刚刚",
        }

    def refresh_all_grades(self):
        scraper = self._create_scraper()
        current_term = scraper.get_current_term()
        semester_list = scraper.get_semester_list()

        new_cache = self._empty_cache()
        new_cache["current_term"] = current_term
        new_cache["semester_list"] = semester_list
        new_cache["last_check_time"] = self._now_str()

        for semester in semester_list:
            term_data = scraper.get_term_grades(
                semester.get("semester_id", ""),
                semester.get("semester_name", ""),
            )
            self._upsert_semester_snapshot(new_cache, term_data)

        old_cache = self.load_grade_cache()
        compare_result = self.compare_grade_snapshots(old_cache, new_cache)
        self.save_grade_cache(new_cache)

        return {
            "current_term": current_term,
            "semester_list": semester_list,
            "new_items": compare_result["new_items"],
            "updated_items": compare_result["updated_items"],
            "semesters": new_cache["semesters"],
        }

    def compare_grade_snapshots(self, old_cache, new_cache):
        old_map = self._flatten_grade_map(old_cache)
        new_map = self._flatten_grade_map(new_cache)

        new_items = []
        updated_items = []

        for grade_id, item in new_map.items():
            old_item = old_map.get(grade_id)
            if not old_item:
                new_items.append(item)
                continue
            if old_item.get("snapshot_hash") != item.get("snapshot_hash"):
                updated_items.append({
                    "before": old_item,
                    "after": item,
                })

        return {
            "new_items": self._sort_grade_items(new_items),
            "updated_items": updated_items,
        }

    def check_new_grades(self, push_enabled=None):
        scraper = self._create_scraper()
        current_term = scraper.get_current_term()
        semester_list = scraper.get_semester_list()
        selected_semester = self._resolve_selected_semester(None, current_term, semester_list)
        latest_term_data = scraper.get_term_grades(
            selected_semester["semester_id"],
            selected_semester["semester_name"],
        )

        old_cache = self.load_grade_cache()
        updated_cache = copy.deepcopy(old_cache)
        updated_cache["current_term"] = current_term
        updated_cache["semester_list"] = semester_list
        updated_cache["last_check_time"] = self._now_str()
        self._upsert_semester_snapshot(updated_cache, latest_term_data)

        compare_result = self.compare_grade_snapshots(old_cache, updated_cache)
        new_items = [
            item for item in compare_result["new_items"]
            if item.get("semester_id") == latest_term_data.get("semester_id")
        ]
        updated_items = [
            item for item in compare_result["updated_items"]
            if item.get("after", {}).get("semester_id") == latest_term_data.get("semester_id")
        ]

        push_result = {
            "attempted": False,
            "success": False,
            "message": "未触发推送",
        }

        should_push = self.config.get("grade_push_enabled", False) if push_enabled is None else bool(push_enabled)
        should_initialize_baseline = should_push and (
            not bool(self.config.get("grade_push_initialized", False)) or not self._has_grade_baseline(old_cache)
        )
        if should_initialize_baseline:
            self.save_grade_cache(updated_cache)
            self.config.update_grade_push_initialized(True)
            push_result = {
                "attempted": True,
                "success": True,
                "message": "首次启用已建立成绩基线，历史成绩不会推送",
            }
            return {
                "current_term": current_term,
                "checked_semester": selected_semester,
                "new_items": [],
                "updated_items": updated_items,
                "push_result": push_result,
            }

        if should_push and new_items:
            push_success, push_message = self._push_new_grades(new_items)
            push_result = {
                "attempted": True,
                "success": push_success,
                "message": push_message,
            }
            if push_success:
                updated_cache["last_push_time"] = self._now_str()
        elif should_push:
            push_result["attempted"] = True
            push_result["message"] = "当前学期暂无新增成绩"

        self.save_grade_cache(updated_cache)

        return {
            "current_term": current_term,
            "checked_semester": selected_semester,
            "new_items": new_items,
            "updated_items": updated_items,
            "push_result": push_result,
        }

    def build_grade_push_message(self, new_items):
        items = self._sort_grade_items(new_items)
        count = len(items)
        if count <= 0:
            return "", "暂无新成绩"

        if count == 1:
            only = items[0]
            summary = f"🎉 小主，新成绩发布啦：{only.get('course_name') or '未知课程'} {only.get('score') or '待公布'}"
        else:
            summary = f"🎉 小主，你有 {count} 门新成绩已发布，快来看看"

        lines = [
            f"# {summary}",
            "",
            "> 检测到当前学期有新的成绩更新，明细如下：",
            "",
            f"> **检测时间**：{self._now_str()}",
            "",
            "---",
            ""
        ]

        for item in items:
            course_name = item.get('course_name') or '未知课程'
            score = item.get('score') or '待公布'
            
            # 使用表情增加可读性
            lines.extend([
                f"### 📖 {course_name}",
                f"- **分数**：`{score}`",
                f"- **绩点**：{item.get('gpa') or '--'}",
                f"- **学分**：{item.get('credit') or '--'}",
                f"- **学期**：{item.get('semester_name') or item.get('semester_id') or '--'}",
                f"- **考核**：{item.get('exam_name') or '--'} ({item.get('examination_nature') or '--'})",
                "",
                "---",
                ""
            ])

        return "\n".join(lines).strip(), summary

    def save_grade_push_settings(self, enable=None, interval_minutes=None, start_time=None, end_time=None):
        return self.config.update_grade_push_settings(
            enabled=enable,
            interval_minutes=interval_minutes,
            start_time=start_time,
            end_time=end_time,
        )

    def _create_scraper(self):
        username = self.config.get("username")
        password = self.config.get("password")
        if not username or not password:
            raise ValueError("请先保存账号密码")

        login_mgr = LoginManager(self.config)
        success, msg = login_mgr.login(username, password, use_cache=True)
        if not success:
            raise RuntimeError(msg)
        return GradeScraper(login_mgr.get_token(), session=login_mgr.session)

    def _normalize_cache_shape(self, data):
        cache = self._empty_cache()
        if not isinstance(data, dict):
            return cache

        cache["last_check_time"] = str(data.get("last_check_time", "") or "").strip()
        cache["last_push_time"] = str(data.get("last_push_time", "") or "").strip()
        current_term = data.get("current_term", {})
        cache["current_term"] = current_term if isinstance(current_term, dict) else {}

        semester_list = data.get("semester_list", [])
        if isinstance(semester_list, list):
            cache["semester_list"] = [
                item for item in semester_list
                if isinstance(item, dict) and item.get("semester_id")
            ]

        semesters = data.get("semesters", [])
        if isinstance(semesters, list):
            normalized_semesters = []
            for semester in semesters:
                if not isinstance(semester, dict):
                    continue
                semester_id = str(semester.get("semester_id", "") or "").strip()
                if not semester_id:
                    continue
                normalized_semesters.append({
                    "semester_id": semester_id,
                    "semester_name": str(semester.get("semester_name", "") or semester_id).strip(),
                    "student_info": semester.get("student_info", {}) if isinstance(semester.get("student_info"), dict) else {},
                    "summary": semester.get("summary", {}) if isinstance(semester.get("summary"), dict) else {},
                    "update_time": str(semester.get("update_time", "") or "").strip(),
                    "grades": [
                        item for item in semester.get("grades", [])
                        if isinstance(item, dict) and item.get("grade_id")
                    ] if isinstance(semester.get("grades"), list) else [],
                })
            cache["semesters"] = normalized_semesters

        if not cache["semester_list"] and cache["semesters"]:
            cache["semester_list"] = [
                {
                    "semester_id": item["semester_id"],
                    "semester_name": item["semester_name"],
                }
                for item in cache["semesters"]
            ]

        return cache

    def _empty_cache(self):
        return {
            "last_check_time": "",
            "last_push_time": "",
            "current_term": {},
            "semester_list": [],
            "semesters": [],
        }

    def _now_str(self):
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _format_relative_time(self, time_str):
        text = str(time_str or "").strip()
        if not text:
            return ""
        try:
            source_time = datetime.strptime(text, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return ""

        seconds = max(int((datetime.now() - source_time).total_seconds()), 0)
        if seconds < 60:
            return "刚刚"
        if seconds < 3600:
            return f"{seconds // 60}分钟前"
        if seconds < 86400:
            return f"{seconds // 3600}小时前"
        return f"{seconds // 86400}天前"

    def _resolve_cached_update_time(self, cache_data, semester_id):
        target_id = str(semester_id or "").strip()
        if target_id:
            for semester in cache_data.get("semesters", []):
                if semester.get("semester_id") == target_id:
                    return self._format_relative_time(semester.get("update_time", ""))

        current_term = cache_data.get("current_term", {})
        current_term_id = current_term.get("semester_id", "") if isinstance(current_term, dict) else ""
        if current_term_id:
            for semester in cache_data.get("semesters", []):
                if semester.get("semester_id") == current_term_id:
                    return self._format_relative_time(semester.get("update_time", ""))

        return self._format_relative_time(cache_data.get("last_check_time", ""))

    def _resolve_selected_semester(self, semester_id, current_term, semester_list):
        semester_list = semester_list if isinstance(semester_list, list) else []
        if isinstance(semester_id, str) and semester_id.strip():
            target_id = semester_id.strip()
            for item in semester_list:
                if item.get("semester_id") == target_id:
                    return item
            return {
                "semester_id": target_id,
                "semester_name": target_id,
            }

        if isinstance(current_term, dict) and current_term.get("semester_id"):
            return current_term
        if semester_list:
            return semester_list[0]
        raise RuntimeError("未获取到可用学期")

    def _upsert_semester_snapshot(self, cache_data, term_data):
        term_record = {
            "semester_id": term_data.get("semester_id", ""),
            "semester_name": term_data.get("semester_name", ""),
            "student_info": term_data.get("student_info", {}),
            "summary": term_data.get("summary", {}),
            "update_time": self._now_str(),
            "grades": self._sort_grade_items(term_data.get("grades", [])),
        }

        semesters = cache_data.get("semesters", [])
        if not isinstance(semesters, list):
            semesters = []

        replaced = False
        for index, item in enumerate(semesters):
            if item.get("semester_id") == term_record["semester_id"]:
                semesters[index] = term_record
                replaced = True
                break

        if not replaced:
            semesters.append(term_record)

        cache_data["semesters"] = semesters

    def _get_effective_semester_list(self, cache_data):
        semester_list = cache_data.get("semester_list", [])
        if semester_list:
            return semester_list
        return [
            {
                "semester_id": item.get("semester_id", ""),
                "semester_name": item.get("semester_name", ""),
            }
            for item in cache_data.get("semesters", [])
            if item.get("semester_id")
        ]

    def _build_response_from_cache(self, cache_data, semester_id):
        semester_list = self._get_effective_semester_list(cache_data)
        current_term = cache_data.get("current_term", {})
        selected_semester = self._resolve_selected_semester(semester_id, current_term, semester_list)

        for semester in cache_data.get("semesters", []):
            if semester.get("semester_id") != selected_semester.get("semester_id"):
                continue
            return {
                "current_term": current_term,
                "semester_list": semester_list,
                "selected_semester": {
                    "semester_id": semester.get("semester_id", ""),
                    "semester_name": semester.get("semester_name", ""),
                },
                "student_info": semester.get("student_info", {}),
                "summary": semester.get("summary", {}),
                "grades": semester.get("grades", []),
            }

        if semester_list:
            return {
                "current_term": current_term,
                "semester_list": semester_list,
                "selected_semester": selected_semester,
                "student_info": {},
                "summary": {},
                "grades": [],
            }
        return None

    def _flatten_grade_map(self, cache_data):
        result = {}
        cache = self._normalize_cache_shape(cache_data)
        for semester in cache.get("semesters", []):
            for item in semester.get("grades", []):
                grade_id = item.get("grade_id")
                if grade_id:
                    result[grade_id] = item
        return result

    def _sort_grade_items(self, items):
        valid_items = [item for item in items if isinstance(item, dict)]
        return sorted(
            valid_items,
            key=lambda x: (
                x.get("semester_id", ""),
                x.get("course_name", ""),
                x.get("grade_id", ""),
            ),
        )

    def _has_grade_baseline(self, cache_data):
        cache = self._normalize_cache_shape(cache_data)
        return bool(cache.get("semesters")) and bool(cache.get("last_check_time"))

    def _push_new_grades(self, new_items):
        app_token = self.config.get("app_token")
        uid = self.config.get("uid")
        if not app_token or not uid:
            return False, "WxPusher 配置不完整"

        content, summary = self.build_grade_push_message(new_items)
        if not content:
            return False, "推送内容为空"

        pusher = Pusher(app_token)
        success, message = pusher.send([uid], content, summary=summary, content_type=3)
        return success, message
