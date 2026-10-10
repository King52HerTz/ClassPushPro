"""Cloud timetable filtering and HTML rendering; no local scheduled execution."""
import html


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


def generate_push_content(courses, date_str, weekday_str):
    title = f"{date_str} {weekday_str} · {len(courses)} 门课程" if courses else f"{date_str} {weekday_str} · 今天没有课"
    cards = []
    for course in courses:
        name, place, teacher, period = (html.escape(str(course.get(k) or "待确认"))
                                        for k in ("courseName", "location", "teacherName", "classTime"))
        cards.append(f'<div style="border:1px solid #d6e4ff;border-left:4px solid #1677ff;border-radius:10px;padding:16px;margin:12px 0">'
                     f'<strong style="font-size:18px">{name}</strong><p>{period} · {place}</p><div>{teacher}</div></div>')
    body = "".join(cards) or "<p>今天没有课程安排，祝你度过愉快的一天。</p>"
    return (f'<div style="font-family:system-ui,sans-serif;max-width:620px;margin:auto;padding:20px;color:#182230">'
            f'<p style="color:#1677ff">ClassPush · 湖南工学院</p><h2>{html.escape(title)}</h2>{body}'
            '<p style="font-size:12px;color:#667085">数据来自教务系统，请以学校最新调课通知为准。</p></div>', title)
