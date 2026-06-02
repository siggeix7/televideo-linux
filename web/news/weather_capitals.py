from __future__ import annotations

import re
import unicodedata
from copy import deepcopy


REGION_CAPITALS = {
    "abruzzo": ["L'Aquila", "Chieti", "Pescara", "Teramo"],
    "basilicata": ["Potenza", "Matera"],
    "calabria": ["Catanzaro", "Cosenza", "Crotone", "Reggio Calabria", "Vibo Valentia"],
    "campania": ["Napoli", "Avellino", "Benevento", "Caserta", "Salerno"],
    "emilia": ["Bologna", "Ferrara", "Forli", "Modena", "Parma", "Piacenza", "Ravenna", "Reggio Emilia", "Rimini"],
    "friuli": ["Trieste", "Gorizia", "Pordenone", "Udine"],
    "lazio": ["Roma", "Frosinone", "Latina", "Rieti", "Viterbo"],
    "liguria": ["Genova", "Imperia", "La Spezia", "Savona"],
    "lombardia": ["Milano", "Bergamo", "Brescia", "Como", "Cremona", "Lecco", "Lodi", "Mantova", "Monza", "Pavia", "Sondrio", "Varese"],
    "marche": ["Ancona", "Ascoli Piceno", "Fermo", "Macerata", "Pesaro", "Urbino"],
    "molise": ["Campobasso", "Isernia"],
    "piemonte": ["Torino", "Alessandria", "Asti", "Biella", "Cuneo", "Novara", "Verbania", "Vercelli"],
    "puglia": ["Bari", "Barletta", "Andria", "Trani", "Brindisi", "Foggia", "Lecce", "Taranto"],
    "sardegna": ["Cagliari", "Nuoro", "Oristano", "Sassari", "Carbonia"],
    "sicilia": ["Palermo", "Agrigento", "Caltanissetta", "Catania", "Enna", "Messina", "Ragusa", "Siracusa", "Trapani"],
    "toscana": ["Firenze", "Arezzo", "Grosseto", "Livorno", "Lucca", "Massa", "Pisa", "Pistoia", "Prato", "Siena"],
    "trentino-alto-adige": ["Trento", "Bolzano"],
    "umbria": ["Perugia", "Terni"],
    "aosta": ["Aosta"],
    "veneto": ["Venezia", "Belluno", "Padova", "Rovigo", "Treviso", "Verona", "Vicenza"],
}


CAPITAL_COORDINATES = {
    "L'Aquila": (42.3498, 13.3995),
    "Chieti": (42.3510, 14.1670),
    "Pescara": (42.4643, 14.2142),
    "Teramo": (42.6612, 13.6990),
    "Potenza": (40.6404, 15.8056),
    "Matera": (40.6664, 16.6043),
    "Catanzaro": (38.9054, 16.5944),
    "Cosenza": (39.2983, 16.2537),
    "Crotone": (39.0808, 17.1271),
    "Reggio Calabria": (38.1140, 15.6500),
    "Vibo Valentia": (38.6762, 16.1016),
    "Napoli": (40.8518, 14.2681),
    "Avellino": (40.9149, 14.7908),
    "Benevento": (41.1298, 14.7826),
    "Caserta": (41.0747, 14.3324),
    "Salerno": (40.6824, 14.7681),
    "Bologna": (44.4949, 11.3426),
    "Ferrara": (44.8381, 11.6198),
    "Forli": (44.2227, 12.0407),
    "Modena": (44.6471, 10.9252),
    "Parma": (44.8015, 10.3279),
    "Piacenza": (45.0526, 9.6934),
    "Ravenna": (44.4184, 12.2035),
    "Reggio Emilia": (44.6983, 10.6312),
    "Rimini": (44.0678, 12.5695),
    "Trieste": (45.6495, 13.7768),
    "Gorizia": (45.9409, 13.6217),
    "Pordenone": (45.9564, 12.6600),
    "Udine": (46.0635, 13.2357),
    "Roma": (41.9028, 12.4964),
    "Frosinone": (41.6398, 13.3512),
    "Latina": (41.4676, 12.9037),
    "Rieti": (42.4045, 12.8567),
    "Viterbo": (42.4207, 12.1077),
    "Genova": (44.4056, 8.9463),
    "Imperia": (43.8897, 8.0393),
    "La Spezia": (44.1025, 9.8241),
    "Savona": (44.3091, 8.4772),
    "Milano": (45.4642, 9.1900),
    "Bergamo": (45.6983, 9.6773),
    "Brescia": (45.5416, 10.2118),
    "Como": (45.8081, 9.0852),
    "Cremona": (45.1332, 10.0227),
    "Lecco": (45.8566, 9.3977),
    "Lodi": (45.3097, 9.5037),
    "Mantova": (45.1564, 10.7914),
    "Monza": (45.5845, 9.2744),
    "Pavia": (45.1847, 9.1582),
    "Sondrio": (46.1699, 9.8788),
    "Varese": (45.8206, 8.8251),
    "Ancona": (43.6158, 13.5189),
    "Ascoli Piceno": (42.8536, 13.5749),
    "Fermo": (43.1609, 13.7185),
    "Macerata": (43.2984, 13.4531),
    "Pesaro": (43.9125, 12.9155),
    "Urbino": (43.7263, 12.6367),
    "Campobasso": (41.5603, 14.6627),
    "Isernia": (41.5960, 14.2330),
    "Torino": (45.0703, 7.6869),
    "Alessandria": (44.9073, 8.6116),
    "Asti": (44.9008, 8.2064),
    "Biella": (45.5629, 8.0583),
    "Cuneo": (44.3845, 7.5427),
    "Novara": (45.4469, 8.6222),
    "Verbania": (45.9210, 8.5518),
    "Vercelli": (45.3202, 8.4186),
    "Bari": (41.1171, 16.8719),
    "Barletta": (41.3193, 16.2833),
    "Andria": (41.2316, 16.2917),
    "Trani": (41.2775, 16.4101),
    "Brindisi": (40.6327, 17.9418),
    "Foggia": (41.4622, 15.5446),
    "Lecce": (40.3515, 18.1750),
    "Taranto": (40.4644, 17.2470),
    "Cagliari": (39.2238, 9.1217),
    "Nuoro": (40.3202, 9.3307),
    "Oristano": (39.9038, 8.5912),
    "Sassari": (40.7259, 8.5557),
    "Carbonia": (39.1672, 8.5222),
    "Palermo": (38.1157, 13.3615),
    "Agrigento": (37.3111, 13.5765),
    "Caltanissetta": (37.4901, 14.0629),
    "Catania": (37.5079, 15.0830),
    "Enna": (37.5675, 14.2790),
    "Messina": (38.1938, 15.5540),
    "Ragusa": (36.9269, 14.7255),
    "Siracusa": (37.0755, 15.2866),
    "Trapani": (38.0176, 12.5362),
    "Firenze": (43.7696, 11.2558),
    "Arezzo": (43.4633, 11.8796),
    "Grosseto": (42.7635, 11.1124),
    "Livorno": (43.5485, 10.3106),
    "Lucca": (43.8429, 10.5027),
    "Massa": (44.0354, 10.1393),
    "Pisa": (43.7228, 10.4017),
    "Pistoia": (43.9335, 10.9173),
    "Prato": (43.8777, 11.1022),
    "Siena": (43.3188, 11.3308),
    "Trento": (46.0701, 11.1196),
    "Bolzano": (46.4983, 11.3548),
    "Perugia": (43.1107, 12.3908),
    "Terni": (42.5636, 12.6427),
    "Aosta": (45.7370, 7.3201),
    "Venezia": (45.4408, 12.3155),
    "Belluno": (46.1425, 12.2167),
    "Padova": (45.4064, 11.8768),
    "Rovigo": (45.0698, 11.7902),
    "Treviso": (45.6669, 12.2430),
    "Verona": (45.4384, 10.9916),
    "Vicenza": (45.5455, 11.5354),
}

MAP_MIN_LON = 6.62
MAP_MAX_LON = 18.52
MAP_MIN_LAT = 35.49
MAP_MAX_LAT = 47.10
MAP_WIDTH = 800
MAP_HEIGHT = 960
MARKER_CARD_WIDTH = 178
MARKER_CARD_HEIGHT = 58


CITY_ALIASES = {
    "Ancona": ["Ancona Falconara"],
    "Brescia": ["Brescia Ghedi"],
    "Cagliari": ["Cagliari Elmas"],
    "Roma": ["Roma Urbe", "Roma Fium", "Roma Fiumicino"],
    "Reggio Calabria": ["R Calabria", "R.Calabria"],
    "Forli": ["Forli", "Forli'"],
    "La Spezia": ["Spezia"],
}


NO_DATA = "n.d."

WEATHER_EMOJI = [
    (r"(?i)\btemporale\b", "\u26c8\ufe0f"),
    (r"(?i)\bpioggia\b|\bpioviggine\b|\brovescio\b", "\U0001f327\ufe0f"),
    (r"(?i)\bneve\b", "\u2744\ufe0f"),
    (r"(?i)\bgrandine\b", "\U0001f328\ufe0f"),
    (r"(?i)\bnebbia\b", "\U0001f32b\ufe0f"),
    (r"(?i)\bfoschia\b", "\U0001f301"),
    (r"(?i)\bcoperto\b|\bmolto\s+nuvoloso\b", "\u2601\ufe0f"),
    (r"(?i)\bnuvoloso\b|\bnubi\b|\bparz.*nuv\b", "\u26c5"),
    (r"(?i)\bpoco\s+nuvoloso\b|\bpoche\s+nuvole\b", "\U0001f324\ufe0f"),
    (r"(?i)\bsereno\b|\bsole\b|\bsoleggiato\b", "\u2600\ufe0f"),
]
PRECIPITATION_RE = re.compile(
    r"(?i)\b(pioggia|pioviggine|rovesc|temporale|grandine|neve|rain|drizzle|shower|thunderstorm|snow|sleet)\b"
)


def weather_emoji(condition: str) -> str:
    if not condition:
        return ""
    for pattern, emoji in WEATHER_EMOJI:
        if re.search(pattern, condition):
            return emoji
    return "\U0001f321\ufe0f"


DEFAULT_EMOJI = "\U0001f321\ufe0f"


def normalize_name(value: str) -> str:
    value = unicodedata.normalize("NFKD", value or "")
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = re.sub(r"[^a-zA-Z0-9]+", " ", value).strip().upper()
    return re.sub(r"\s+", " ", value)


def city_search_keys(city: str) -> list[str]:
    keys = [city, *CITY_ALIASES.get(city, [])]
    return [normalize_name(key) for key in keys]


def flatten_weather_data(meteo_data: dict) -> tuple[dict[str, dict], dict[str, dict]]:
    stations = {}
    for zone in meteo_data.get("weather_stations", []):
        for station in zone.get("stations", []):
            name = station.get("name", "")
            key = normalize_name(name)
            if key and key not in stations:
                stations[key] = station

    temperatures = {}
    for block in meteo_data.get("temperatures", []):
        for city in block.get("cities", []):
            name = city.get("city", "")
            key = normalize_name(name)
            if key and key not in temperatures:
                temperatures[key] = city

    return stations, temperatures


def find_by_city(city: str, lookup: dict[str, dict]) -> dict | None:
    keys = city_search_keys(city)
    for key in keys:
        if key in lookup:
            return lookup[key]
    for key in keys:
        for candidate_key, payload in lookup.items():
            if candidate_key.startswith(f"{key} ") or key.startswith(f"{candidate_key} "):
                return payload
    return None


def build_region_capital_weather(meteo_data: dict, openweather_data: dict[str, dict] | None = None, *, openweather_only: bool = False) -> dict[str, list[dict[str, object]]]:
    stations, temperatures = ({}, {}) if openweather_only else flatten_weather_data(meteo_data)
    openweather_data = openweather_data or {}
    payload = {}

    for region_slug, capitals in REGION_CAPITALS.items():
        rows = []
        for capital in capitals:
            station = find_by_city(capital, stations) or {}
            temperature = find_by_city(capital, temperatures) or {}
            openweather = find_by_city(capital, openweather_data) or {}
            row = {
                "name": capital,
                "condition": station.get("condition") or "",
                "temp": station.get("temp") or "",
                "wind": station.get("wind") or "",
                "visibility": station.get("visibility") or "",
                "min": temperature.get("min"),
                "max": temperature.get("max"),
                "sunrise": "",
                "sunset": "",
                "today_forecast": [],
                "forecast_days": [],
            }
            televideo_available = row_has_weather(row)
            used_openweather = merge_openweather(row, openweather)
            row["available"] = row_has_weather(row)
            if televideo_available and used_openweather:
                row["source_label"] = "Rai Televideo + OpenWeatherMap"
            elif televideo_available:
                row["source_label"] = "Rai Televideo"
            elif used_openweather:
                row["source_label"] = openweather.get("source_label") or "OpenWeatherMap"
            else:
                row["source_label"] = ""
            row["source_at"] = openweather.get("source_at") if used_openweather else None
            condition_text = str(row.get("condition") or "")
            row["emoji"] = weather_emoji(condition_text)
            row["temperature_range"] = temperature_range(row)
            row["is_precipitating"] = is_precipitating(row)
            row["precipitation_badge"] = precipitation_badge(row)
            row["summary"] = weather_summary(row)
            rows.append(row)
        payload[region_slug] = rows
    return payload


def row_has_weather(row: dict) -> bool:
    return any(row.get(key) not in (None, "") for key in ("condition", "temp", "wind", "visibility", "min", "max"))


def merge_openweather(row: dict, openweather: dict) -> bool:
    if not openweather:
        return False

    used = False
    for key in ("condition", "temp", "wind", "visibility"):
        if not row.get(key) and openweather.get(key) not in (None, ""):
            row[key] = openweather[key]
            used = True
    for key in ("min", "max"):
        if row.get(key) is None and openweather.get(key) is not None:
            row[key] = openweather[key]
            used = True
    for key in (
        "sunrise", "sunset", "today_forecast", "forecast_days",
        "rain_probability", "rain_mm", "snow_mm", "precipitation_mm",
        "precipitation_period", "precipitation_label",
    ):
        if openweather.get(key):
            row[key] = openweather[key]
            used = True
    return used


def temperature_range(row: dict) -> str:
    if row.get("min") is not None and row.get("max") is not None:
        return f"min {row['min']}\u00b0 / max {row['max']}\u00b0"
    return ""


def _temp_float(value) -> float | None:
    if value in (None, "", NO_DATA):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_wind_float(value: str) -> float:
    if not value:
        return 0.0
    match = re.match(r"([\d.]+)", str(value))
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            return 0.0
    return 0.0


def temp_color(temperature: float | None) -> str:
    """Return a hex color from blue (cold) through green to red (hot)."""
    if temperature is None:
        return "rgba(0,255,0,0.10)"
    if temperature <= 0:
        return "rgba(100,180,255,0.35)"
    if temperature <= 5:
        return "rgba(130,200,255,0.32)"
    if temperature <= 10:
        return "rgba(160,220,240,0.28)"
    if temperature <= 15:
        return "rgba(200,230,180,0.22)"
    if temperature <= 20:
        return "rgba(180,255,140,0.24)"
    if temperature <= 25:
        return "rgba(255,240,80,0.35)"
    if temperature <= 30:
        return "rgba(255,190,40,0.42)"
    if temperature <= 35:
        return "rgba(255,130,30,0.50)"
    return "rgba(255,60,20,0.58)"


def _positive_number(value) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    return number if number > 0 else 0.0


def is_precipitating(row: dict) -> bool:
    if _positive_number(row.get("precipitation_mm")) > 0:
        return True
    return bool(PRECIPITATION_RE.search(str(row.get("condition") or "")))


def precipitation_badge(row: dict) -> str:
    label = str(row.get("precipitation_label") or "")
    if label:
        return label
    probability = row.get("rain_probability")
    if probability not in (None, ""):
        return f"prob. pioggia {probability}%"
    return ""


def weather_summary(row: dict) -> str:
    parts = []
    if row.get("condition"):
        parts.append(str(row["condition"]))
    if row.get("temp"):
        parts.append(f"{row['temp']}\u00b0")
    if row.get("temperature_range"):
        parts.append(str(row["temperature_range"]))
    if row.get("wind"):
        parts.append(f"vento {row['wind']}")
    if row.get("precipitation_badge"):
        parts.append(str(row["precipitation_badge"]))
    return " \u00b7 ".join(parts) if parts else NO_DATA


def project_capital_position(city: str) -> tuple[float, float] | None:
    coordinates = CAPITAL_COORDINATES.get(city)
    if not coordinates:
        return None
    lat, lon = coordinates
    x = (lon - MAP_MIN_LON) / (MAP_MAX_LON - MAP_MIN_LON) * MAP_WIDTH
    y = (MAP_MAX_LAT - lat) / (MAP_MAX_LAT - MAP_MIN_LAT) * MAP_HEIGHT
    return round(x, 1), round(y, 1)


def capital_marker_slug(city: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", normalize_name(city).casefold()).strip("-")


def capital_marker_detail(row: dict) -> tuple[str, str, str]:
    emoji = str(row.get("emoji") or DEFAULT_EMOJI)
    temp = row.get("temp")
    temp_label = f"{temp}\u00b0" if temp not in (None, "") else NO_DATA
    wind = str(row.get("wind") or NO_DATA)
    return emoji, temp_label, f"{emoji} {temp_label} \u00b7 vento {wind}"


def capital_marker_card_candidates(x: float, y: float) -> list[tuple[float, float]]:
    """Return candidate card positions (left,right × centered,top,bottom) ordered by preference."""
    gap = 8
    w = MARKER_CARD_WIDTH
    h = MARKER_CARD_HEIGHT
    candidates = [
        (x + gap,            y - h / 2),   # right-centered (preferred)
        (x - w - gap,        y - h / 2),   # left-centered
        (x + gap,            y - h - gap), # right-top
        (x - w - gap,        y - h - gap), # left-top
        (x + gap,            y + gap),     # right-bottom
        (x - w - gap,        y + gap),     # left-bottom
    ]
    clamped = []
    for cx, cy in candidates:
        cx = min(max(cx, 3), MAP_WIDTH - w - 3)
        cy = min(max(cy, 3), MAP_HEIGHT - h - 3)
        clamped.append((round(cx, 1), round(cy, 1)))
    return clamped


def _card_overlaps(cx: float, cy: float, placed: list[tuple[float, float, float, float]]) -> bool:
    for pcx, pcy, pcw, pch in placed:
        if (cx < pcx + pcw + 4 and cx + MARKER_CARD_WIDTH + 4 > pcx and
            cy < pcy + pch + 4 and cy + MARKER_CARD_HEIGHT + 4 > pcy):
            return True
    return False


def build_capital_weather_markers(region_weather: dict[str, list[dict]]) -> list[dict[str, object]]:
    markers = []
    placed_cards: list[tuple[float, float, float, float]] = []
    for region_slug, rows in region_weather.items():
        for row in rows:
            city = str(row.get("name") or "")
            position = project_capital_position(city)
            if not city or not position:
                continue
            x, y = position
            candidates = capital_marker_card_candidates(x, y)
            best_dist = float("inf")
            card_x = card_y = 0.0
            for cx, cy in candidates:
                if not _card_overlaps(cx, cy, placed_cards):
                    dist = ((cx + MARKER_CARD_WIDTH / 2 - x) ** 2 + (cy + MARKER_CARD_HEIGHT / 2 - y) ** 2) ** 0.5
                    if dist < best_dist:
                        best_dist = dist
                        card_x, card_y = cx, cy
            if best_dist == float("inf"):
                # All candidates overlap — pick the closest to marker
                for cx, cy in candidates:
                    dist = ((cx + MARKER_CARD_WIDTH / 2 - x) ** 2 + (cy + MARKER_CARD_HEIGHT / 2 - y) ** 2) ** 0.5
                    if dist < best_dist:
                        best_dist = dist
                        card_x, card_y = cx, cy
            placed_cards.append((card_x, card_y, MARKER_CARD_WIDTH, MARKER_CARD_HEIGHT))

            emoji, temp_label, detail = capital_marker_detail(row)
            condition = str(row.get("condition") or "")
            temp_val = _temp_float(row.get("temp"))
            min_val = row.get("min")
            max_val = row.get("max")
            temp_range = ""
            if min_val is not None and max_val is not None:
                temp_range = f"{min_val}\u00b0 / {max_val}\u00b0"
            aria_parts = [city]
            if condition:
                aria_parts.append(condition)
            aria_parts.append(detail)
            if row.get("precipitation_badge"):
                aria_parts.append(str(row["precipitation_badge"]))
            markers.append({
                "slug": capital_marker_slug(city),
                "name": city,
                "region_slug": region_slug,
                "x": x,
                "y": y,
                "emoji_y": round(y, 1),
                "card_x": card_x,
                "card_y": card_y,
                "card_width": MARKER_CARD_WIDTH,
                "card_height": MARKER_CARD_HEIGHT,
                "available": bool(row.get("available")),
                "precipitating": bool(row.get("is_precipitating")),
                "precipitation_badge": row.get("precipitation_badge") or "",
                "precipitation_mm": _positive_number(row.get("precipitation_mm")),
                "emoji": emoji,
                "temp_label": temp_label,
                "temp_value": temp_val,
                "temp_color": temp_color(temp_val),
                "temp_range": temp_range,
                "wind": row.get("wind") or NO_DATA,
                "detail": detail,
                "condition": condition,
                "source_label": row.get("source_label") or "",
                "aria_label": ": ".join(aria_parts),
            })
    return sorted(markers, key=lambda marker: (marker["y"], marker["x"], marker["name"]))


def enrich_map_regions(map_regions: list[dict], region_weather: dict[str, list[dict]]) -> list[dict]:
    enriched = []
    for region in map_regions:
        item = deepcopy(region)
        item["weather_capitals"] = region_weather.get(item["slug"], [])
        enriched.append(item)
    return enriched
