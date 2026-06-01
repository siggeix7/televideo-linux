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


def build_region_capital_weather(meteo_data: dict) -> dict[str, list[dict[str, object]]]:
    stations, temperatures = flatten_weather_data(meteo_data)
    payload = {}

    for region_slug, capitals in REGION_CAPITALS.items():
        rows = []
        for capital in capitals:
            station = find_by_city(capital, stations) or {}
            temperature = find_by_city(capital, temperatures) or {}
            row = {
                "name": capital,
                "condition": station.get("condition") or "",
                "temp": station.get("temp") or "",
                "wind": station.get("wind") or "",
                "visibility": station.get("visibility") or "",
                "min": temperature.get("min"),
                "max": temperature.get("max"),
            }
            row["available"] = any(row.get(key) not in (None, "") for key in ("condition", "temp", "wind", "visibility", "min", "max"))
            row["temperature_range"] = temperature_range(row)
            row["summary"] = weather_summary(row)
            rows.append(row)
        payload[region_slug] = rows
    return payload


def temperature_range(row: dict) -> str:
    if row.get("min") is not None and row.get("max") is not None:
        return f"min {row['min']}\u00b0 / max {row['max']}\u00b0"
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
    return " \u00b7 ".join(parts) if parts else NO_DATA


def enrich_map_regions(map_regions: list[dict], region_weather: dict[str, list[dict]]) -> list[dict]:
    enriched = []
    for region in map_regions:
        item = deepcopy(region)
        item["weather_capitals"] = region_weather.get(item["slug"], [])
        enriched.append(item)
    return enriched
