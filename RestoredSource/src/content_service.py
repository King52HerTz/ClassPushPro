import json
import os
from datetime import datetime, timedelta

import requests

from logger import logger


OPEN_METEO_FORECAST_API_URL = "https://api.open-meteo.com/v1/forecast"
DEFAULT_WEATHER_CACHE_MINUTES = 120
QWEATHER_DEFAULT_API_HOST = "devapi.qweather.com"
QWEATHER_CREDENTIAL_ID = "KKB338K9PA"
QWEATHER_API_HOST = "nu2tuqcye2.re.qweatherapi.com"
QWEATHER_API_KEY = "f6c0ad8f7fa64f2ba30977de6d691c0f"
SCHOOL_WEATHER_TARGET = {
    "label": "湖南工学院珠晖校区",
    "address": "湖南省衡阳市珠晖区衡花路18号",
    "latitude": 26.88,
    "longitude": 112.62,
}


WEATHER_CODE_MAP = {
    0: "晴",
    1: "基本晴朗",
    2: "局部多云",
    3: "阴",
    45: "有雾",
    48: "雾凇",
    51: "小毛毛雨",
    53: "毛毛雨",
    55: "强毛毛雨",
    56: "冻毛毛雨",
    57: "强冻毛毛雨",
    61: "小雨",
    63: "中雨",
    65: "大雨",
    66: "冻雨",
    67: "强冻雨",
    71: "小雪",
    73: "中雪",
    75: "大雪",
    77: "冰粒",
    80: "阵雨",
    81: "较强阵雨",
    82: "强阵雨",
    85: "阵雪",
    86: "强阵雪",
    95: "雷暴",
    96: "雷暴夹小冰雹",
    99: "雷暴夹大冰雹",
}


class WeatherContentService:
    """负责按课表目标日期获取和缓存天气摘要，不让第三方接口影响主推送流程。"""

    def __init__(self, config):
        self.config = config
        app_data = os.path.join(os.path.expanduser("~"), ".ClassPush")
        os.makedirs(app_data, exist_ok=True)
        self.cache_path = os.path.join(app_data, "weather_cache.json")

    def get_weather_content(self, target_date=None):
        if not self.config.get("weather_enabled", False):
            return None

        target_date_obj = self._normalize_target_date(target_date)
        target_date_str = target_date_obj.strftime("%Y-%m-%d")
        day_label = self._resolve_day_label(target_date_obj)

        try:
            weather_data = self._fetch_weather(target_date_str, day_label)
            if weather_data:
                self._save_cache(weather_data)
                return weather_data
        except Exception as exc:
            logger.warning(f"天气接口请求失败，尝试使用缓存: {exc}")

        cached = self._load_cache(target_date_str)
        if cached:
            cached["is_cached"] = True
            cached["cache_label"] = "校园缓存"
            return cached
        return None

    def _fetch_weather(self, target_date_str, day_label):
        qweather_data = self._fetch_qweather(target_date_str, day_label)
        if qweather_data:
            return qweather_data
        return self._fetch_open_meteo(target_date_str, day_label)

    def _fetch_qweather(self, target_date_str, day_label):
        if not QWEATHER_API_KEY.strip():
            return None

        api_host = self._normalize_api_host(QWEATHER_API_HOST or QWEATHER_DEFAULT_API_HOST)
        qweather_url = f"https://{api_host}/v7/weather/7d"
        response = requests.get(
            qweather_url,
            params={
                "location": self._build_qweather_location(),
                "key": QWEATHER_API_KEY,
                "lang": "zh",
            },
            timeout=8,
        )
        response.raise_for_status()
        payload = response.json()
        if str(payload.get("code")) != "200":
            raise ValueError(f"和风天气返回异常状态: {payload.get('code')}")

        daily_items = payload.get("daily") or []
        daily_item = next((item for item in daily_items if item.get("fxDate") == target_date_str), None)
        if not daily_item:
            raise ValueError("和风天气未返回目标日期的天气预报")

        weather_text = str(daily_item.get("textDay") or daily_item.get("textNight") or "天气未知").strip()
        temp_max = self._format_number(daily_item.get("tempMax"))
        temp_min = self._format_number(daily_item.get("tempMin"))
        precipitation_amount = self._format_number(daily_item.get("precip"))
        humidity = self._format_number(daily_item.get("humidity"))
        wind_speed = self._format_number(daily_item.get("windSpeedDay") or daily_item.get("windSpeedNight"))
        wind_direction = str(daily_item.get("windDirDay") or daily_item.get("windDirNight") or "-").replace(" ", "").strip()
        wind_scale = str(daily_item.get("windScaleDay") or daily_item.get("windScaleNight") or "-").strip()
        uv_index = str(daily_item.get("uvIndex") or "-").strip()
        cloud = self._format_number(daily_item.get("cloud"))
        sunrise = str(daily_item.get("sunrise") or "").strip()
        sunset = str(daily_item.get("sunset") or "").strip()
        suggestion = self._build_weather_suggestion(
            weather_text,
            temp_max,
            temp_min,
            wind_speed,
            precipitation_amount,
            day_label,
        )

        summary_parts = [
            f"{weather_text}，{temp_min}-{temp_max}C",
            f"降水量 {precipitation_amount} mm" if precipitation_amount != "-" else "",
            f"湿度 {humidity}%" if humidity != "-" else "",
            f"{wind_direction}{wind_scale}级" if wind_direction != "-" and wind_scale != "-" else (
                f"风力 {wind_scale}级" if wind_scale != "-" else ""
            ),
        ]
        summary = "，".join(part for part in summary_parts if part)

        extra_parts = []
        if uv_index != "-":
            extra_parts.append(f"紫外线 {uv_index}")
        if cloud != "-":
            extra_parts.append(f"云量 {cloud}%")
        if sunrise:
            extra_parts.append(f"日出 {sunrise}")
        if sunset:
            extra_parts.append(f"日落 {sunset}")

        return {
            "location_label": SCHOOL_WEATHER_TARGET["label"],
            "location_address": SCHOOL_WEATHER_TARGET["address"],
            "weather_date": target_date_str,
            "day_label": day_label,
            "summary": summary,
            "weather_text": weather_text,
            "temperature_max": temp_max,
            "temperature_min": temp_min,
            "precipitation_probability": "-",
            "precipitation_amount": precipitation_amount,
            "humidity": humidity,
            "wind_speed": wind_speed,
            "wind_direction": wind_direction,
            "wind_scale": wind_scale,
            "uv_index": uv_index,
            "cloud": cloud,
            "sunrise": sunrise,
            "sunset": sunset,
            "extra_summary": "，".join(extra_parts),
            "suggestion": suggestion,
            "fetched_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "is_cached": False,
            "cache_label": "和风天气",
            "provider": "qweather",
        }

    def _fetch_open_meteo(self, target_date_str, day_label):
        forecast_response = requests.get(
            OPEN_METEO_FORECAST_API_URL,
            params={
                "latitude": SCHOOL_WEATHER_TARGET["latitude"],
                "longitude": SCHOOL_WEATHER_TARGET["longitude"],
                "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max,wind_speed_10m_max",
                "start_date": target_date_str,
                "end_date": target_date_str,
                "timezone": "auto",
            },
            timeout=8,
        )
        forecast_response.raise_for_status()
        forecast_data = forecast_response.json()
        daily = forecast_data.get("daily") or {}
        weather_code_list = daily.get("weather_code") or []
        temp_max_list = daily.get("temperature_2m_max") or []
        temp_min_list = daily.get("temperature_2m_min") or []
        precipitation_list = daily.get("precipitation_probability_max") or []
        wind_speed_list = daily.get("wind_speed_10m_max") or []
        if not weather_code_list:
            raise ValueError("天气接口未返回目标日期天气预报")

        weather_code = weather_code_list[0]
        weather_text = WEATHER_CODE_MAP.get(weather_code, "天气未知")
        temp_max = self._format_number(temp_max_list[0] if temp_max_list else None)
        temp_min = self._format_number(temp_min_list[0] if temp_min_list else None)
        precipitation_probability = self._format_number(precipitation_list[0] if precipitation_list else None)
        wind_speed = self._format_number(wind_speed_list[0] if wind_speed_list else None)
        suggestion = self._build_weather_suggestion(
            weather_code,
            temp_max,
            temp_min,
            wind_speed,
            precipitation_probability,
            day_label,
        )

        summary = (
            f"{weather_text}，{temp_min}-{temp_max}C，"
            f"降水概率 {precipitation_probability}%，最大风速 {wind_speed} km/h"
        )

        return {
            "location_label": SCHOOL_WEATHER_TARGET["label"],
            "location_address": SCHOOL_WEATHER_TARGET["address"],
            "weather_date": target_date_str,
            "day_label": day_label,
            "summary": summary,
            "weather_text": weather_text,
            "temperature_max": temp_max,
            "temperature_min": temp_min,
            "precipitation_probability": precipitation_probability,
            "precipitation_amount": "-",
            "wind_speed": wind_speed,
            "humidity": "-",
            "wind_direction": "-",
            "wind_scale": "-",
            "uv_index": "-",
            "cloud": "-",
            "sunrise": "",
            "sunset": "",
            "extra_summary": "",
            "suggestion": suggestion,
            "fetched_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "is_cached": False,
            "cache_label": "校园天气",
            "provider": "open_meteo",
        }

    def _load_cache(self, target_date_str):
        if not os.path.exists(self.cache_path):
            return None

        try:
            with open(self.cache_path, "r", encoding="utf-8") as file:
                cache = json.load(file)
        except Exception as exc:
            logger.warning(f"读取天气缓存失败: {exc}")
            return None

        if cache.get("location_label") != SCHOOL_WEATHER_TARGET["label"]:
            return None
        if cache.get("weather_date") != target_date_str:
            return None

        cached_at = cache.get("cached_at")
        if cached_at and not self._is_cache_fresh(cached_at):
            logger.info("天气缓存已过期，忽略旧缓存")
            return None

        return cache

    def _save_cache(self, weather_data):
        cache_payload = dict(weather_data)
        cache_payload["cached_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        try:
            with open(self.cache_path, "w", encoding="utf-8") as file:
                json.dump(cache_payload, file, ensure_ascii=False, indent=2)
        except Exception as exc:
            logger.warning(f"保存天气缓存失败: {exc}")

    def _is_cache_fresh(self, cached_at):
        try:
            cache_time = datetime.strptime(cached_at, "%Y-%m-%d %H:%M:%S")
        except (TypeError, ValueError):
            return False
        return datetime.now() - cache_time <= timedelta(minutes=DEFAULT_WEATHER_CACHE_MINUTES)

    def _format_number(self, value):
        try:
            return str(int(round(float(value))))
        except (TypeError, ValueError):
            return "-"

    def _build_qweather_location(self):
        # 和风天气在中国大陆场景建议使用“经度,纬度”格式，并限制到两位小数。
        longitude = f"{float(SCHOOL_WEATHER_TARGET['longitude']):.2f}"
        latitude = f"{float(SCHOOL_WEATHER_TARGET['latitude']):.2f}"
        return f"{longitude},{latitude}"

    def _normalize_api_host(self, value):
        normalized = str(value or "").strip()
        if normalized.startswith("https://"):
            normalized = normalized[len("https://"):]
        elif normalized.startswith("http://"):
            normalized = normalized[len("http://"):]
        return normalized.rstrip("/") or QWEATHER_DEFAULT_API_HOST

    def _normalize_target_date(self, target_date):
        if isinstance(target_date, datetime):
            return target_date
        if hasattr(target_date, "year") and hasattr(target_date, "month") and hasattr(target_date, "day"):
            return datetime.combine(target_date, datetime.min.time())
        return datetime.now()

    def _resolve_day_label(self, target_date_obj):
        delta_days = (target_date_obj.date() - datetime.now().date()).days
        if delta_days == 0:
            return "今天"
        if delta_days == 1:
            return "明天"
        if delta_days == -1:
            return "昨天"
        return target_date_obj.strftime("%m月%d日")

    def _build_weather_suggestion(self, weather_code, temp_max, temp_min, wind_speed, precipitation_value, day_label):
        try:
            temp_max_val = float(temp_max)
        except (TypeError, ValueError):
            temp_max_val = None

        try:
            temp_min_val = float(temp_min)
        except (TypeError, ValueError):
            temp_min_val = None

        try:
            wind_val = float(wind_speed)
        except (TypeError, ValueError):
            wind_val = None

        try:
            precipitation_val = float(precipitation_value)
        except (TypeError, ValueError):
            precipitation_val = None

        weather_text = str(weather_code or "").strip()
        rainy_keywords = ("雨", "雷", "暴")
        snowy_keywords = ("雪", "冰")
        foggy_keywords = ("雾",)

        if any(keyword in weather_text for keyword in ("雷暴", "暴雨", "大雨")):
            return f"小主，{day_label}雨可能有点大，出门把伞带好，路上看到积水就绕着走。"
        if any(keyword in weather_text for keyword in rainy_keywords):
            return f"小主，{day_label}可能会下雨，出门前看一眼窗外，别把伞忘啦。"
        if any(keyword in weather_text for keyword in snowy_keywords):
            return f"小主，{day_label}会冷一些，外套穿厚点，路上慢慢走。"
        if any(keyword in weather_text for keyword in foggy_keywords):
            return f"小主，{day_label}早上可能有点雾，路上别着急，慢一点更安心。"
        if precipitation_val is not None and precipitation_val >= 20:
            return f"小主，{day_label}天气可能有点闷，包里放把伞。"
        if temp_max_val is not None and temp_max_val >= 35:
            return f"小主，{day_label}会很热，防晒记得做好，水也多喝一点。"
        if temp_max_val is not None and temp_max_val >= 30:
            return f"小主，{day_label}外面会有点晒，出门记得防晒，顺手带瓶水。"
        if temp_max_val is not None and temp_max_val >= 27:
            return f"小主，{day_label}有点热，中午前后少在太阳底下站太久。"
        if temp_min_val is not None and temp_min_val <= 10:
            return f"小主，{day_label}早晚会有点凉，薄外套带上，别着凉了。"
        if wind_val is not None and wind_val >= 25:
            return f"小主，{day_label}风有点大，伞和帽子都拿稳一点。"
        if "晴" in weather_text:
            return f"小主，{day_label}天气挺舒服的，安心出门就好，记得补水。"
        if any(keyword in weather_text for keyword in ("多云", "少云", "晴间多云")):
            return f"小主，{day_label}这天气还挺舒服的，按时出门就好。"
        if "阴" in weather_text:
            return f"小主，{day_label}是阴天，体感会舒服一点，正常穿就行。"
        return f"小主，{day_label}出门前顺手看一眼天气，路上注意安全。"
