from datetime import date, datetime, timedelta


SCHEDULE_STATUS_ACTIVE = "active"
SCHEDULE_STATUS_VACATION = "vacation"
SCHEDULE_STATUS_UNKNOWN = "unknown"


def _safe_positive_int(value):
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None
    return number if number > 0 else None


def _normalize_observed_date(value=None):
    if value is None:
        return date.today()
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return datetime.strptime(str(value), "%Y-%m-%d").date()


def monday_of(value):
    current = _normalize_observed_date(value)
    return current - timedelta(days=current.weekday())


def normalize_teaching_state(payload, semester_info=None, observed_date=None):
    """把强智 teachingWeek 响应转换成明确的教学状态。

    教务系统在假期仍可能返回 nowWeek=1。isNowWeek 才是当前是否处于
    教学周的状态位，因此不能仅凭 nowWeek 判断当前周次。
    """
    raw = payload if isinstance(payload, dict) else {}
    semester = semester_info if isinstance(semester_info, dict) else {}
    raw_flag = str(raw.get("isNowWeek", "")).strip()
    raw_week = _safe_positive_int(raw.get("nowWeek"))

    available_weeks = []
    for item in raw.get("data", []) if isinstance(raw.get("data"), list) else []:
        if not isinstance(item, dict):
            continue
        week = _safe_positive_int(item.get("week"))
        if week is not None and week not in available_weeks:
            available_weeks.append(week)
    available_weeks.sort()

    if raw_flag == "1" and raw_week is not None:
        status = SCHEDULE_STATUS_ACTIVE
        is_teaching_week = True
    elif raw_flag == "0":
        status = SCHEDULE_STATUS_VACATION
        is_teaching_week = False
    else:
        status = SCHEDULE_STATUS_UNKNOWN
        is_teaching_week = False

    observed = _normalize_observed_date(observed_date)
    week_one_monday = ""
    if status == SCHEDULE_STATUS_ACTIVE:
        anchor = monday_of(observed) - timedelta(weeks=raw_week - 1)
        week_one_monday = anchor.isoformat()

    semester_id = str(
        semester.get("semester_id")
        or semester.get("xnxq01id")
        or ""
    ).strip()
    semester_name = str(
        semester.get("semester_name")
        or semester.get("xqmc")
        or semester_id
    ).strip()

    if status == SCHEDULE_STATUS_ACTIVE:
        message = f"当前为第{raw_week}教学周"
    elif status == SCHEDULE_STATUS_VACATION:
        message = "当前处于非教学周，新学期课表发布后会自动更新"
    else:
        message = "暂时无法确认当前教学周"

    return {
        "schedule_status": status,
        "is_teaching_week": is_teaching_week,
        "current_week": raw_week,
        "raw_current_week": str(raw.get("nowWeek", "")).strip(),
        "available_weeks": available_weeks,
        "semester_id": semester_id,
        "semester_name": semester_name,
        "week_one_monday": week_one_monday,
        "observed_date": observed.isoformat(),
        "message": message,
    }


def week_number_for_date(week_one_monday, target_date):
    if not week_one_monday:
        return None
    anchor = _normalize_observed_date(week_one_monday)
    target = _normalize_observed_date(target_date)
    days = (target - anchor).days
    if days < 0:
        return None
    return (days // 7) + 1


def merge_cached_teaching_state(cached_data):
    """兼容旧缓存；旧缓存没有状态时返回 unknown，避免把假期当第1周。"""
    cached = cached_data if isinstance(cached_data, dict) else {}
    state = cached.get("teaching_state")
    if isinstance(state, dict):
        return state
    return {
        "schedule_status": SCHEDULE_STATUS_UNKNOWN,
        "is_teaching_week": False,
        "current_week": None,
        "raw_current_week": str(cached.get("current_week", "")).strip(),
        "available_weeks": [],
        "semester_id": str(cached.get("semester_id", "")).strip(),
        "semester_name": "",
        "week_one_monday": str(cached.get("week_one_monday", "")).strip(),
        "observed_date": "",
        "message": "旧课表缓存缺少教学周状态，请联网刷新后再使用",
    }
