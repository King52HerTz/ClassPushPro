"""Cloud timetable filtering and HTML rendering; no local scheduled execution."""
import html
from config_manager import DEFAULT_TIME_SLOTS


def filter_courses(courses, target_date, week):
    if week is None:
        return []
    weekday = "星期" + "一二三四五六日"[target_date.weekday()]
    result = []
    for course in courses:
        weeks = str(course.get("classWeekDetails") or "").split(",")
        if course.get("xqmc") == weekday and (weeks == [""] or str(week) in [w.strip() for w in weeks]):
            result.append(course)
    return sorted(result, key=lambda c: int(c.get("startNode") or 1))


def generate_push_content(courses, date_str, weekday_str, day_label="今天"):
    title = (f"小主，{day_label}有 {len(courses)} 节课，记得按时上课哟 🍬" if courses
             else f"小主，{day_label}全天没课，好好休息吧 🛌")
    cards = []
    for course in courses:
        name, place, teacher = (html.escape(str(course.get(k) or "待确认"))
                                for k in ("courseName", "location", "teacherName"))
        period = str(course.get("classTime") or "待确认").replace("节", "").strip()
        slot = DEFAULT_TIME_SLOTS.get(period)
        display_time = f"{slot[0]}-{slot[1]}（第{period}节）" if slot else period
        cards.append('<div style="background:#fff;border-left:5px solid #ff7875;border-radius:8px;'
                     'padding:15px;margin:0 0 15px;box-shadow:0 2px 8px rgba(0,0,0,.05)">'
                     f'<div style="font-size:18px;font-weight:bold;color:#333;margin-bottom:10px">📖 {name}</div>'
                     f'<div style="font-size:14px;color:#0984e3;margin-bottom:5px">📍 {place}</div>'
                     f'<div style="font-size:14px;color:#e17055;margin-bottom:5px">⏰ {html.escape(display_time)}</div>'
                     f'<div style="font-size:14px;color:#636e72">🧑‍🏫 {teacher}</div></div>')
    body = "".join(cards) or ('<div style="text-align:center;padding:40px 20px">'
                             '<div style="font-size:60px;margin-bottom:20px">🎈</div>'
                             '<p style="color:#40a9ff;font-size:16px">自由时光，做点喜欢的事吧~</p>'
                             '<p style="color:#faad14;font-size:14px">祝你有美好的一天 ✨</p></div>')
    heading = html.escape(title)
    if courses:
        heading = heading.replace(str(len(courses)), f'<span style="color:#ff4d4f">{len(courses)}</span>', 1)
    return ('<div style="font-family:-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif;'
            'max-width:600px;margin:0 auto;padding:20px;background:#fff;line-height:1.6;'
            'color:#333;overflow-wrap:anywhere;box-sizing:border-box">'
            f'<h2 style="font-size:22px;line-height:1.5;margin:0 0 8px;color:#262626">{heading}</h2>'
            f'<div style="font-size:18px;font-weight:bold;color:#ff7875;margin:20px 0">'
            f'🗓️ {html.escape(date_str)} {html.escape(weekday_str)}</div>{body}'
            '<p style="font-size:12px;color:#999;border-top:1px dashed #eee;padding-top:20px;margin-top:30px">'
            '数据来自教务系统，请以学校最新调课通知为准。</p></div>', title)
