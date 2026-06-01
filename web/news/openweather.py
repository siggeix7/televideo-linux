from __future__ import annotations

import json
import logging
import time
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone as datetime_timezone
from urllib.parse import urlencode
from urllib.request import urlopen

from django.conf import settings
from django.utils import timezone

from .models import OpenWeatherCity
from .weather_capitals import REGION_CAPITALS, normalize_name


logger = logging.getLogger(__name__)

OPENWEATHER_FORECAST_URL = "https://api.openweathermap.org/data/2.5/forecast"


def iter_capitals() -> list[dict[str, str]]:
    capitals = []
    seen = set()
    for region_slug, cities in REGION_CAPITALS.items():
        for city in cities:
            key = normalize_name(city)
            if key in seen:
                continue
            seen.add(key)
            capitals.append({"city": city, "region_slug": region_slug, "query": f"{city},IT"})
    return capitals


def sync_openweather_capitals() -> int:
    changed = 0
    existing = {city.city: city for city in OpenWeatherCity.objects.all()}
    for item in iter_capitals():
        city = existing.get(item["city"])
        if not city:
            OpenWeatherCity.objects.create(**item)
            changed += 1
            continue
        if city.region_slug != item["region_slug"] or city.query != item["query"]:
            city.region_slug = item["region_slug"]
            city.query = item["query"]
            city.save(update_fields=("region_slug", "query", "updated_at"))
            changed += 1
    return changed


def fetch_openweather_payload(city: OpenWeatherCity, api_key: str) -> dict:
    params = urlencode({
        "q": city.query,
        "appid": api_key,
        "units": "metric",
        "lang": "it",
    })
    url = f"{OPENWEATHER_FORECAST_URL}?{params}"
    with urlopen(url, timeout=settings.OPENWEATHER_TIMEOUT) as response:
        return json.loads(response.read().decode("utf-8"))


def _rounded(value) -> int | None:
    if value is None:
        return None
    return int(round(float(value)))


def _percent(value) -> int | None:
    if value is None:
        return None
    return int(round(float(value) * 100))


def _utc_datetime(value) -> datetime | None:
    if value is None:
        return None
    return datetime.fromtimestamp(int(value), tz=datetime_timezone.utc)


def _local_datetime(value, offset: int) -> datetime:
    return datetime.fromtimestamp(int(value) + offset, tz=datetime_timezone.utc)


def _condition(entry: dict) -> str:
    weather = entry.get("weather") or []
    if not weather:
        return ""
    return (weather[0].get("description") or "").strip().capitalize()


def _forecast_entry(entry: dict, offset: int) -> dict[str, object]:
    main = entry.get("main") or {}
    wind = entry.get("wind") or {}
    local_dt = _local_datetime(entry["dt"], offset)
    return {
        "time": local_dt.strftime("%H:%M"),
        "date": local_dt.date().isoformat(),
        "condition": _condition(entry),
        "temp": _rounded(main.get("temp")),
        "min": _rounded(main.get("temp_min")),
        "max": _rounded(main.get("temp_max")),
        "rain_probability": _percent(entry.get("pop")),
        "wind": f"{float(wind['speed']):.1f} m/s" if wind.get("speed") is not None else "",
    }


def build_today_forecast(entries: list[dict], offset: int) -> list[dict[str, object]]:
    if not entries:
        return []
    first_day = _local_datetime(entries[0]["dt"], offset).date()
    slots = []
    for entry in entries:
        if _local_datetime(entry["dt"], offset).date() != first_day:
            break
        slots.append(_forecast_entry(entry, offset))
    return slots[:6]


def build_forecast_days(entries: list[dict], offset: int) -> list[dict[str, object]]:
    grouped = defaultdict(list)
    for entry in entries:
        grouped[_local_datetime(entry["dt"], offset).date()].append(entry)

    if not grouped:
        return []

    first_day = min(grouped)
    days = []
    for day in sorted(grouped)[:5]:
        entries_for_day = grouped[day]
        mins = [float((entry.get("main") or {}).get("temp_min")) for entry in entries_for_day if (entry.get("main") or {}).get("temp_min") is not None]
        maxs = [float((entry.get("main") or {}).get("temp_max")) for entry in entries_for_day if (entry.get("main") or {}).get("temp_max") is not None]
        conditions = [_condition(entry) for entry in entries_for_day if _condition(entry)]
        pop_values = [float(entry.get("pop")) for entry in entries_for_day if entry.get("pop") is not None]
        label = day.strftime("%d/%m")
        if day == first_day:
            label = "Oggi"
        elif day == first_day + timedelta(days=1):
            label = "Domani"

        days.append({
            "date": day.isoformat(),
            "label": label,
            "condition": Counter(conditions).most_common(1)[0][0] if conditions else "",
            "min": _rounded(min(mins)) if mins else None,
            "max": _rounded(max(maxs)) if maxs else None,
            "rain_probability": _percent(max(pop_values)) if pop_values else None,
        })
    return days


def store_openweather_payload(city: OpenWeatherCity, payload: dict, now=None) -> OpenWeatherCity:
    now = now or timezone.now()
    entries = payload.get("list") or []
    first = entries[0] if entries else {}
    main = first.get("main") or {}
    wind = payload.get("wind") or {}
    if first:
        wind = first.get("wind") or {}
    city_info = payload.get("city") or {}
    timezone_offset = int(city_info.get("timezone") or 0)
    forecast_days = build_forecast_days(entries, timezone_offset)
    today_forecast = build_today_forecast(entries, timezone_offset)
    today = forecast_days[0] if forecast_days else {}

    city.condition = _condition(first)
    city.temp = _rounded(main.get("temp"))
    city.temp_min = today.get("min") if today else _rounded(main.get("temp_min"))
    city.temp_max = today.get("max") if today else _rounded(main.get("temp_max"))
    city.wind_speed = wind.get("speed")
    city.visibility_m = first.get("visibility")
    city.sunrise_at = _utc_datetime(city_info.get("sunrise"))
    city.sunset_at = _utc_datetime(city_info.get("sunset"))
    city.timezone_offset = timezone_offset
    city.today_forecast = today_forecast
    city.forecast_days = forecast_days
    city.raw = payload
    city.fetched_at = now
    city.last_attempt_at = now
    city.error_message = ""
    city.save(update_fields=(
        "condition", "temp", "temp_min", "temp_max", "wind_speed", "visibility_m",
        "sunrise_at", "sunset_at", "timezone_offset", "today_forecast", "forecast_days",
        "raw", "fetched_at", "last_attempt_at", "error_message", "updated_at",
    ))
    return city


def openweather_cache_by_city() -> dict[str, dict[str, object]]:
    payload = {}
    for city in OpenWeatherCity.objects.exclude(fetched_at__isnull=True):
        payload[normalize_name(city.city)] = openweather_city_payload(city)
    return payload


def openweather_city_payload(city: OpenWeatherCity) -> dict[str, object]:
    wind = ""
    if city.wind_speed is not None:
        wind = f"{float(city.wind_speed):.1f} m/s"

    visibility = ""
    if city.visibility_m is not None:
        visibility = f"{city.visibility_m / 1000:.1f} km"

    sunrise = timezone.localtime(city.sunrise_at).strftime("%H:%M") if city.sunrise_at else ""
    sunset = timezone.localtime(city.sunset_at).strftime("%H:%M") if city.sunset_at else ""

    return {
        "city": city.city,
        "condition": city.condition,
        "temp": _rounded(city.temp),
        "min": _rounded(city.temp_min),
        "max": _rounded(city.temp_max),
        "wind": wind,
        "visibility": visibility,
        "sunrise": sunrise,
        "sunset": sunset,
        "today_forecast": city.today_forecast or [],
        "forecast_days": city.forecast_days or [],
        "source_label": "OpenWeatherMap",
        "source_at": city.fetched_at,
    }


def latest_openweather_attempt():
    return OpenWeatherCity.objects.exclude(last_attempt_at__isnull=True).order_by("-last_attempt_at").first()


def due_openweather_cities(*, now=None, stale_seconds: int | None = None, force: bool = False) -> list[OpenWeatherCity]:
    now = now or timezone.now()
    stale_seconds = stale_seconds or settings.OPENWEATHER_STALE_SECONDS
    stale_before = now - timedelta(seconds=stale_seconds)
    due = [
        city for city in OpenWeatherCity.objects.all()
        if force or city.fetched_at is None or city.fetched_at <= stale_before
    ]
    oldest = datetime.min.replace(tzinfo=datetime_timezone.utc)
    return sorted(due, key=lambda city: (city.fetched_at or oldest, city.last_attempt_at or oldest, city.city))


def next_due_openweather_city(now=None, stale_seconds: int | None = None) -> OpenWeatherCity | None:
    due = due_openweather_cities(now=now, stale_seconds=stale_seconds)
    return due[0] if due else None


def refresh_openweather_city(city: OpenWeatherCity, api_key: str, now=None) -> dict[str, object]:
    now = now or timezone.now()
    city.last_attempt_at = now
    city.save(update_fields=("last_attempt_at", "updated_at"))

    try:
        payload = fetch_openweather_payload(city, api_key)
        store_openweather_payload(city, payload, now=now)
    except Exception as exc:
        logger.warning("OpenWeather refresh failed for %s", city.city, exc_info=True)
        city.error_message = str(exc)[:1000]
        city.save(update_fields=("error_message", "updated_at"))
        return {"status": "error", "city": city.city, "error": city.error_message}

    return {"status": "updated", "city": city.city, "fetched_at": now}


def refresh_due_openweather_cities(*, max_calls: int | None = None, force: bool = False, now=None, sleep_func=time.sleep) -> dict[str, object]:
    now = now or timezone.now()
    api_key = settings.OPENWEATHER_API_KEY
    sync_openweather_capitals()

    if not api_key:
        return {"status": "disabled", "message": "OPENWEATHER_API_KEY not configured", "results": []}

    due = due_openweather_cities(now=now, force=force)
    if not due:
        return {"status": "fresh", "message": "all cached cities are fresh", "results": []}

    max_calls = max_calls or settings.OPENWEATHER_BATCH_SIZE
    max_calls = max(1, int(max_calls))
    rate_limit = max(1, int(settings.OPENWEATHER_MAX_CALLS_PER_MINUTE))
    delay = 60 / rate_limit
    selected = due[:max_calls]
    results = []

    for index, city in enumerate(selected):
        if index:
            sleep_func(delay)
        results.append(refresh_openweather_city(city, api_key, now=timezone.now()))

    updated = sum(1 for result in results if result["status"] == "updated")
    errors = sum(1 for result in results if result["status"] == "error")
    status = "updated" if updated else "error" if errors else "checked"
    return {"status": status, "updated": updated, "errors": errors, "remaining": max(len(due) - len(selected), 0), "results": results}


def refresh_due_openweather_city(*, force: bool = False, now=None) -> dict[str, object]:
    result = refresh_due_openweather_cities(max_calls=1, force=force, now=now, sleep_func=lambda _seconds: None)
    if result["results"]:
        return result["results"][0]
    return {key: value for key, value in result.items() if key != "results"}
