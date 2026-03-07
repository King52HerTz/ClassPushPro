import argparse
import sys
import datetime
from logger import logger
from config_manager import ConfigManager
from login_manager import LoginManager
from real_scraper import CourseScraper
from pusher import Pusher

WEEKDAYS = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]

def run_push_task(force=False, source="auto"):
    """
    执行一次完整的推送任务
    包含智能补发与过期处理机制
    :param force: 是否强制推送 (忽略今日已推检查)
    """
    if source not in ("auto", "manual"):
        source = "auto"
    logger.info(f"开始执行推送任务 (Force={force})")
    
    # 1. 加载配置
    config = ConfigManager()
    username = config.get("username")
    password = config.get("password")
    app_token = config.get("app_token")
    uid = config.get("uid")
    push_time_str = config.get("push_time", "20:00")
    last_push_time_str = config.get("last_push_success_time", "")
    last_auto_push_time_str = config.get("last_auto_push_success_time", "")
    
    if not all([username, password, app_token, uid]):
        logger.error("配置不完整，跳过推送")
        return False, "配置不完整"

    # ---- 智能补发逻辑判断 ----
    now = datetime.datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    
    # 检查是否今日已推送 (仅在非强制模式下检查)
    today_guard_time_str = last_auto_push_time_str if source == "auto" else last_push_time_str
    if not force and today_guard_time_str:
        try:
            last_push_dt = datetime.datetime.strptime(today_guard_time_str, "%Y-%m-%d %H:%M:%S")
            if last_push_dt.date() == now.date():
                # 默认跳过
                should_skip = True
                
                # 特殊逻辑：如果是自动任务，尝试检测是否为“修改时间后的重新触发”
                if source == "auto":
                    try:
                        # 1. 解析配置的目标时间
                        ph, pm = map(int, push_time_str.split(':'))
                        # 构造今天的目标时间点
                        target_dt = now.replace(hour=ph, minute=pm, second=0, microsecond=0)
                        
                        # 2. 检查当前时间是否在目标时间的“正点范围”内 (比如前后5分钟)
                        # 这意味着任务是按计划准时启动的
                        time_diff = abs((now - target_dt).total_seconds())
                        is_on_time = time_diff < 300 # 5分钟内

                        # 3. 检查上次推送距离现在多久
                        # 如果上次推送就在刚才(10分钟内)，那肯定是重复触发，必须跳过
                        last_push_diff = (now - last_push_dt).total_seconds()
                        is_just_pushed = last_push_diff < 600 

                        if is_on_time and not is_just_pushed:
                            should_skip = False
                            logger.info(f"检测到正点运行({push_time_str})且上次推送已久，允许再次推送")
                    except Exception as e:
                        logger.warning(f"防重逻辑解析异常: {e}")

                if should_skip:
                    logger.info(f"今日已执行过推送({today_guard_time_str})，跳过")
                    return True, "今日已推送"
        except Exception:
            pass # 解析失败则忽略，继续执行

    # 解析设定的推送时间
    try:
        push_hour = int(push_time_str.split(':')[0])
    except:
        push_hour = 20 # 默认晚上
    
    # 判断是“晨间推送”还是“晚间推送”
    # 晨间推送 (04:00 - 13:59): 意图是看“今天”的课表
    # 晚间推送 (14:00 - 03:59): 意图是看“明天”的课表
    is_morning_push = 4 <= push_hour < 14
    
    target_date = None
    is_delayed = False
    
    if is_morning_push:
        # 晨间推送：默认目标是今天
        target_date = now
        
        # 检查是否迟到 (当前时间 > 设定时间 + 1小时)
        # 例如设定 07:00，现在 10:00 -> 迟到
        if now.hour > push_hour + 1:
            is_delayed = True
            logger.info(f"检测到延迟推送 (设定: {push_time_str}, 当前: {now.strftime('%H:%M')})")
    else:
        # 晚间推送：默认目标是明天
        target_date = now + datetime.timedelta(days=1)
        # 晚间推送一般不需要“延迟”概念，因为即使晚了也是推明天的

    # 3. 抓取课表
    courses = []
    current_week = "1"
    
    try:
        login_mgr = LoginManager(config)
        success, msg = login_mgr.login(username, password, use_cache=True)
        
        if success:
            token = login_mgr.get_token()
            scraper = CourseScraper(token, session=login_mgr.session)
            courses = scraper.fetch_course_data()
            current_week = scraper.fetch_current_week()
            
            if courses:
                # 成功获取，更新缓存
                config.save_cached_courses(courses, current_week)
            else:
                logger.warning("未获取到课程数据或课表为空")
        else:
            logger.warning(f"登录失败: {msg}，尝试使用本地缓存")
            
    except Exception as e:
        logger.error(f"在线抓取异常: {e}，尝试使用本地缓存")

    # 如果在线获取失败，尝试读取缓存
    is_offline_mode = False
    if not courses:
        cached_data = config.get_cached_courses()
        if cached_data:
            courses = cached_data.get("courses", [])
            current_week = cached_data.get("current_week", "1")
            
            # 智能周次推算逻辑
            # 如果缓存中有上次更新时间，尝试推算当前周次
            last_update_str = config.get("jw_cached_time")
            if last_update_str:
                try:
                    last_dt = datetime.datetime.strptime(last_update_str, "%Y-%m-%d %H:%M:%S")
                    # 计算两个日期相差的天数
                    days_diff = (now - last_dt).days
                    # 计算相差的周数 (向下取整)
                    weeks_diff = days_diff // 7
                    
                    if weeks_diff > 0:
                        old_week = int(current_week)
                        new_week = old_week + weeks_diff
                        logger.info(f"离线模式: 根据时间差({days_diff}天)自动推算周次: {old_week} -> {new_week}")
                        current_week = str(new_week)
                except Exception as e:
                    logger.warning(f"离线周次推算失败: {e}")

            # 特殊处理：如果是学校没有第一周，默认修正为2
            # if current_week == "1":
            #      logger.info("检测到周次为1，根据学校特性修正为2")
            #      current_week = "2"

            is_offline_mode = True
            logger.info(f"已切换至离线模式，使用本地缓存课表 (当前周次: {current_week})")
        else:
            logger.error("在线抓取失败且无本地缓存，无法推送")
            return False, "获取课表失败"
    
    # ---- 智能切换目标日期 (仅针对延迟的晨间推送) ----
    if is_delayed and is_morning_push:
        # 如果是延迟的晨间推送，检查今天是否还有课
        # 如果今天的课都上完了，就改推明天的
        today_courses = _filter_courses(courses, now, scraper.fetch_current_week())
        if _are_all_courses_finished(today_courses):
            logger.info("今日课程已全部结束，智能切换为推送明日课表")
            target_date = now + datetime.timedelta(days=1)
            is_delayed = False # 既然推明天了，就不算延迟提醒了
        else:
            logger.info("今日仍有课程，继续推送今日课表 (带延迟标记)")

    # 4. 筛选目标日期课程
    target_weekday = target_date.weekday()
    target_xqmc = WEEKDAYS[target_weekday]
    target_date_str = target_date.strftime("%m月%d日")
    
    # 智能跨周逻辑：如果目标日期是下一周（周一），且当前周次未更新，需要 +1
    # 场景：周日(第1周)推送周一(第2周)的课
    # 判断标准：target_date 的 ISO 周数 > now 的 ISO 周数
    # 或者简单点：如果 target_weekday 是 0 (周一) 且 now 是周日，说明跨周了
    if target_weekday == 0 and now.weekday() == 6:
        try:
            old_week = int(current_week)
            current_week = str(old_week + 1)
            logger.info(f"检测到跨周推送 (周日->周一)，周次自动+1: {old_week} -> {current_week}")
        except:
            pass

    # current_week 已在上面获取 (在线或缓存)
    logger.info(f"当前周次: {current_week}，目标日期: {target_date_str} ({target_xqmc})")
    
    target_courses = _filter_courses(courses, target_date, current_week)
    logger.info(f"目标课程数: {len(target_courses)}")
    
    # 5. 生成推送内容
    content, title = _generate_push_content(target_courses, target_date_str, target_xqmc, is_delayed, is_offline_mode)
    
    # 6. 推送
    pusher = Pusher(app_token)
    success, msg = pusher.send([uid], content, summary=title, content_type=2)
    
    if success:
        logger.info("推送成功")
        now_str = now.strftime("%Y-%m-%d %H:%M:%S")
        config.update_last_push_time(now_str)
        if source == "auto":
            config.update_last_auto_push_time(now_str)
        else:
            config.update_last_manual_push_time(now_str)
        return True, "推送成功"
    else:
        logger.error(f"推送失败: {msg}")
        return False, f"推送失败: {msg}"

def _filter_courses(all_courses, target_date, current_week):
    """筛选指定日期的课程"""
    target_weekday = target_date.weekday()
    target_xqmc = WEEKDAYS[target_weekday]
    
    filtered = []
    logger.info(f"开始筛选课程: 目标星期={target_xqmc}, 目标周次={current_week}")
    
    for c in all_courses:
        # 调试日志：打印每节课的关键信息
        c_name = c.get("courseName", "未知课程")
        c_xqmc = c.get("xqmc", "")
        c_weeks = c.get("classWeekDetails", "")
        
        if c.get("xqmc") != target_xqmc:
            # logger.debug(f"跳过课程[{c_name}]: 星期不匹配 ({c_xqmc} != {target_xqmc})")
            continue
            
        week_details = c.get("classWeekDetails", "")
        if week_details:
            weeks = week_details.split(",")
            if str(current_week) not in weeks:
                logger.info(f"跳过课程[{c_name}]: 周次不匹配 (当前第{current_week}周, 该课{c_weeks}周)")
                continue
        
        logger.info(f"命中课程: {c_name} (地点:{c.get('location')}, 节次:{c.get('classTime')})")
        filtered.append(c)
    
    return filtered

def _are_all_courses_finished(courses):
    """判断给定课程列表是否都已结束"""
    if not courses:
        return True
        
    now = datetime.datetime.now()
    current_total_minutes = now.hour * 60 + now.minute
    
    # 简单估算：第1节=08:00, 第12节=21:00
    # 只要 endNode 对应的时间 < 当前时间，就算结束
    # 粗略映射: 节次 * 50分钟 + 8:00? 不太准
    # 使用保守策略：如果当前超过22:00，肯定结束。如果超过12:00，早上的课结束。
    # 这里为了简单，假设一节课结束时间映射表 (参考常见高校时间)
    # 1-2: 09:40, 3-4: 11:40, 5-6: 15:40, 7-8: 17:40, 9-10: 20:20, 11-12: 22:00
    end_time_map = {
        2: 9*60 + 50,
        4: 11*60 + 50,
        6: 15*60 + 50,
        8: 17*60 + 50,
        10: 20*60 + 30,
        12: 22*60 + 0
    }
    
    for c in courses:
        end_node = c.get("endNode", 0)
        # 找到最接近的结束时间
        threshold = 22*60 # 默认很晚
        for node, time_val in end_time_map.items():
            if end_node <= node:
                threshold = time_val
                break
        
        if current_total_minutes < threshold:
            return False # 还有课没结束
            
    return True

def _generate_push_content(courses, date_str, weekday_str, is_delayed=False, is_offline_mode=False):
    """
    生成精美 HTML 推送内容
    """
    generate_time = datetime.datetime.now().strftime("%m-%d %H:%M:%S")
    
    # 基础样式 (保持原有)
    style = """
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; line-height: 1.6; color: #333; background-color: #f7f7f7; margin: 0; padding: 0; }
        .container { max-width: 600px; margin: 0 auto; background: #fff; padding: 20px; border-radius: 12px; }
        .header { margin-bottom: 20px; }
        .title { font-size: 22px; font-weight: bold; color: #262626; margin: 0 0 8px 0; }
        .subtitle { font-size: 14px; color: #8c8c8c; }
        .date-badge { display: inline-block; font-size: 18px; font-weight: bold; color: #ff7875; margin: 20px 0; }
        .date-icon { margin-right: 5px; }
        .course-card { background: #fff; border-radius: 8px; padding: 15px; margin-bottom: 15px; box-shadow: 0 2px 8px rgba(0,0,0,0.05); border-left: 5px solid #ff7875; }
        .course-name { font-size: 18px; font-weight: bold; color: #333; margin-bottom: 10px; display: flex; align-items: center; }
        .course-info { font-size: 14px; color: #666; margin-bottom: 5px; display: flex; align-items: center; }
        .icon { margin-right: 8px; width: 16px; text-align: center; }
        .no-course { text-align: center; padding: 40px 20px; }
        .emoji-lg { font-size: 60px; margin-bottom: 20px; display: block; }
        .relax-text { color: #40a9ff; font-size: 16px; margin-bottom: 30px; }
        .wish-text { color: #faad14; font-size: 14px; }
        .footer { margin-top: 30px; padding-top: 20px; border-top: 1px dashed #eee; font-size: 12px; color: #999; text-align: center; }
        .warning { background: #fffbe6; border: 1px solid #ffe58f; color: #d48806; padding: 10px; border-radius: 4px; font-size: 13px; margin-top: 20px; }
        .delayed-badge { background: #fff1f0; border: 1px solid #ffa39e; color: #cf1322; padding: 2px 6px; border-radius: 4px; font-size: 12px; margin-left: 10px; vertical-align: middle; }
        .offline-badge { background: #fff7e6; border: 1px solid #ffd591; color: #d46b08; padding: 2px 6px; border-radius: 4px; font-size: 12px; margin-left: 10px; vertical-align: middle; }
    </style>
    """
    
    html = f"<!DOCTYPE html><html><head><meta charset='utf-8'>{style}</head><body><div class='container'>"
    summary_title = ""
    
    day_label = "明天"
    # 简单判断：如果 target_date_str 与今天日期一致，则显示“今天”
    today_str_check = datetime.datetime.now().strftime("%m月%d日")
    if date_str == today_str_check:
        day_label = "今天"

    offline_html = "<span class='offline-badge'>离线模式</span>" if is_offline_mode else ""
    offline_text = "[离线] " if is_offline_mode else ""

    if not courses:
        summary_title = f"{offline_text}小主，{day_label}全天没课，好好休息吧 🛌"
        html += f"""
        <div class="header">
            <div class="title">{summary_title}</div>
            <div class="subtitle">ClassPush {generate_time} {offline_html}</div>
        </div>
        
        <div class="date-badge">
            <span class="date-icon">🗓️</span>{date_str} {weekday_str}
        </div>
        
        <div class="no-course">
            <span class="emoji-lg">🎈</span>
            <div class="relax-text">自由时光，做点喜欢的事吧~</div>
            <div class="wish-text">祝你有美好的一天 ✨</div>
        </div>
        """
    else:
        course_count = len(courses)
        delayed_text = "[延迟提醒] " if is_delayed else ""
        summary_title = f"{offline_text}{delayed_text}小主，{day_label}有 {course_count} 节课，记得按时上课哟 🍬"
        
        html_title = f"小主，{day_label}有 <span style='color: #ff4d4f'>{course_count}</span> 节课，记得按时上课哟 🍬"
        if is_delayed:
            html_title += "<span class='delayed-badge'>延迟提醒</span>"
        if is_offline_mode:
            html_title += "<span class='offline-badge'>离线模式</span>"
        
        html += f"""
        <div class="header">
            <div class="title">{html_title}</div>
            <div class="subtitle">ClassPush {generate_time}</div>
        </div>
        
        <div class="date-badge">
            <span class="date-icon">🗓️</span>{date_str} {weekday_str}
        </div>
        """
        
        courses.sort(key=lambda x: x.get("classTime", ""))
        
        # 时间映射表
        time_map = {
            "1-2": "08:30-10:05",
            "3-4": "10:25-12:00",
            "5-6": "14:00-15:35",
            "7-8": "15:55-17:30",
            "9-10": "19:00-20:35"
        }

        for course in courses:
            raw_time_slot = course.get('classTime', '')
            # 移除可能存在的“节”字
            clean_time_slot = raw_time_slot.replace('节', '')
            
            # 获取具体时间段，如果没有匹配到则显示原节次
            display_time = time_map.get(clean_time_slot, f"{clean_time_slot}节")
            
            html += f"""
            <div class="course-card">
                <div class="course-name">📖 {course['courseName']}</div>
                <div class="course-info">
                    <span class="icon">📍</span> {course['location']}
                </div>
                <div class="course-info">
                    <span class="icon">⏰</span> {display_time}
                </div>
                <div class="course-info">
                    <span class="icon">🧑‍🏫</span> {course['teacherName']}
                </div>
            </div>
            """
            
    html += "</div></body></html>"
    return html, summary_title

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--silent", action="store_true", help="静默模式")
    parser.add_argument("--force", action="store_true", help="强制推送")
    args = parser.parse_args()
    
    run_push_task(force=args.force, source="manual")
