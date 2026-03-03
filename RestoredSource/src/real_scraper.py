import requests
import json
from datetime import datetime
from school_adapter import SCHOOL_CONFIG
from logger import logger

class CourseScraper:
    """
    负责从教务系统抓取并解析课程表数据
    """
    def __init__(self, token, session=None):
        self.token = token
        self.session = session if session else requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        })

    def fetch_semester_id(self):
        """获取当前学期ID (xnxq01id)"""
        url = f"{SCHOOL_CONFIG['BASE_URL']}/getXnxqList?token={self.token}"
        try:
            resp = self.session.post(url, timeout=10)
            data = resp.json()
            
            # 有时返回的 data 本身可能是字符串形式的JSON，或者是一个字典但结构不同
            if isinstance(data, str):
                try:
                    data = json.loads(data)
                except:
                    pass
            
            # 如果 data 是 list，直接遍历
            if isinstance(data, list):
                items = data
            # 如果 data 是 dict，可能包含 list 在某个 key 下
            elif isinstance(data, dict):
                items = data.get("data", []) # 假设可能有 data 字段
                if not items and "xnxq01id" in data: # 或者本身就是单个对象
                     items = [data]
            else:
                items = []

            # 找到num最大的学期
            max_num = -1
            semester_id = None
            
            for item in items:
                if not isinstance(item, dict):
                    continue
                    
                try:
                    num = int(item.get("num", -1))  # 强制转为int
                except (ValueError, TypeError):
                    num = -1
                    
                if num > max_num:
                    max_num = num
                    semester_id = item.get("xnxq01id")
            
            return semester_id
        except Exception as e:
            logger.exception("获取学期ID失败")
            return None

    def fetch_current_week(self):
        """获取当前周次 (nowWeek)"""
        url = f"{SCHOOL_CONFIG['BASE_URL']}/teachingWeek?token={self.token}"
        try:
            resp = self.session.post(url, timeout=10)
            data = resp.json()
            return data.get("nowWeek", "1")
        except Exception as e:
            logger.warning("获取当前周次失败，降级为第1周", exc_info=True)
            return "1"

    def fetch_schedule_mode(self):
        """获取课程节次模式ID (kbjcmsid)"""
        url = f"{SCHOOL_CONFIG['BASE_URL']}/Get_sjkbms?token={self.token}"
        try:
            resp = self.session.post(url, timeout=10)
            data = resp.json()
            if data and "data" in data and len(data["data"]) > 0:
                return data["data"][0].get("kbjcmsid")
            return None
        except Exception as e:
            logger.exception("获取节次模式失败")
            return None

    def fetch_course_data(self):
        """
        主流程：获取所有必要参数并抓取课表
        :return: 解析后的课程列表或空列表
        """
        semester_id = self.fetch_semester_id()
        if not semester_id:
            return []

        schedule_mode = self.fetch_schedule_mode()
        if not schedule_mode:
            return []

        # 获取完整课表 (week=all)
        url = f"{SCHOOL_CONFIG['BASE_URL']}/student/curriculum?token={self.token}&xnxq01id={semester_id}&kbjcmsid={schedule_mode}&week=all"
        
        try:
            resp = self.session.post(url, timeout=15)
            # 注意：Java代码显示有些接口返回JSON对象，有些返回JSON字符串
            # 这里假设直接返回JSON对象
            raw_data = resp.json()
            return self._parse_course_json(raw_data)
        except Exception as e:
            logger.exception("抓取课表失败")
            return []

    def _parse_course_json(self, json_data):
        """
        解析原始JSON数据为结构化课程列表
        支持高级按位解析 classTime
        """
        courses = []
        try:
            data_array = json_data.get("data", [])
            for data_obj in data_array:
                item_array = data_obj.get("item", [])
                
                # 有些返回结构可能把date放在外面，但根据文档，关键是解析 item 里的 classTime
                
                for item in item_array:
                    raw_class_time = item.get("classTime", "")
                    
                    # 尝试使用高级解析
                    parsed_infos = self._parse_digit_class_time(raw_class_time)
                    
                    if parsed_infos:
                        for info in parsed_infos:
                            # 使用解析出的精准信息
                            course = {
                                "xqmc": info["xqmc"],
                                "weekday": info["weekday"],
                                "classTime": info["display_time"],
                                "startNode": info["start_node"],
                                "endNode": info["end_node"],
                                "courseName": item.get("courseName"),
                                "location": item.get("location"),
                                "teacherName": item.get("teacherName"),
                                "classWeek": item.get("classWeek"),
                                "classWeekDetails": item.get("classWeekDetails", "")
                            }
                            courses.append(course)
                    else:
                        # 降级处理：使用原始数据（如果存在）
                        # 注意：如果 classTime 是 "1-2" 这种格式，这里作为兜底
                        course = {
                            "xqmc": "", # 暂时无法得知星期
                            "weekday": 0,
                            "classTime": raw_class_time,
                            "startNode": 0,
                            "endNode": 0,
                            "courseName": item.get("courseName"),
                            "location": item.get("location"),
                            "teacherName": item.get("teacherName"),
                            "classWeek": item.get("classWeek"),
                            "classWeekDetails": item.get("classWeekDetails", "")
                        }
                        courses.append(course)
        except Exception as e:
            logger.exception("解析课表JSON失败")
        
        return courses

    def _parse_digit_class_time(self, class_time_str):
        """
        解析数字格式的 classTime，如 "701020304"
        7 -> 星期日
        0102 -> 1,2节 (属于一大节)
        0304 -> 3,4节 (属于二大节)
        """
        if not class_time_str or not class_time_str.isdigit() or len(class_time_str) < 3:
            return None
        
        weekday_map = {
            '1': '星期一', '2': '星期二', '3': '星期三', '4': '星期四',
            '5': '星期五', '6': '星期六', '7': '星期日'
        }
        
        try:
            weekday_code = class_time_str[0]
            weekday = weekday_map.get(weekday_code, "")
            
            nodes_str = class_time_str[1:]
            all_nodes = []
            # 每2位是一个节次
            for i in range(0, len(nodes_str), 2):
                if i + 2 <= len(nodes_str):
                    node = int(nodes_str[i:i+2])
                    all_nodes.append(node)
            
            if not all_nodes:
                return None
            
            # 核心改进：按标准大节拆分
            # 标准大节定义：(开始节, 结束节)
            big_slots = [
                (1, 2), (3, 4), (5, 6), (7, 8), (9, 10), (11, 12)
            ]
            
            result_list = []
            nodes_set = set(all_nodes)
            
            for start, end in big_slots:
                # 检查当前大节是否包含在 nodes 中（求交集）
                # 只要当前大节有课，就生成一个记录
                current_slot_nodes = [n for n in range(start, end + 1)]
                intersection = [n for n in current_slot_nodes if n in nodes_set]
                
                if intersection:
                    s_node = min(intersection)
                    e_node = max(intersection)
                    
                    # 为了兼容前端逻辑，startNode 最好对齐大节的起始 (如果是一个完整的大节)
                    # 如果只有第3节课（3-3），startNode=3，前端会在第二大节显示
                    # 如果只有第1节课（1-1），startNode=1，前端会在第一大节显示
                    
                    result_list.append({
                        "weekday": int(weekday_code),
                        "xqmc": weekday,
                        "start_node": s_node,
                        "end_node": e_node,
                        "display_time": f"{s_node}-{e_node}节"
                    })
            
            return result_list
        except:
            return None
