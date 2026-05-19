"""
Content formatters: parse raw Televideo text into structured data for display.
"""
from __future__ import annotations

import re
from datetime import date as date_type


def parse_serie_a_standings(raw_text: str) -> list[dict] | None:
    """Parse Serie A standings table from raw Televideo text."""
    rows = []
    for line in raw_text.splitlines():
        line = line.strip()
        match = re.match(
            r"^([A-ZÀÈÉÌÒÙ. ]{2,20})\s+(\d{1,3})\s+(\d{1,2})\s+(\d{1,2})\s+(\d{1,2})\s+(\d{1,3})\s+(\d{1,3})",
            line,
        )
        if match:
            rows.append({
                "team": match.group(1).strip().title(),
                "pts": int(match.group(2)),
                "w": int(match.group(3)),
                "d": int(match.group(4)),
                "l": int(match.group(5)),
                "gf": int(match.group(6)),
                "gs": int(match.group(7)),
            })
    return rows if len(rows) >= 3 else None


def parse_match_results(raw_text: str) -> list[dict] | None:
    """Parse Serie A match results."""
    results = []
    for line in raw_text.splitlines():
        line = line.strip()
        match = re.match(
            r"^([A-ZÀÈÉÌÒÙ\-. ]{3,30})\-([A-ZÀÈÉÌÒÙ\-. ]{3,30})\s+(\d+\-\d+)",
            line,
        )
        if match:
            results.append({
                "home": match.group(1).strip().title(),
                "away": match.group(2).strip().title(),
                "score": match.group(3),
            })
    return results if results else None


def parse_round_info(raw_text: str) -> str | None:
    """Extract round/giornata info."""
    match = re.search(
        r"(\d+[a-z]*\.[ma]+\s+(?:e\s+ultima\s+)?giornata\s+\d{4}\-\d{2})",
        raw_text,
        re.IGNORECASE,
    )
    if match:
        return match.group(1).strip()
    return None


def parse_film_schedule(raw_text: str) -> list[dict] | None:
    """Parse film schedule listings from TV guide pages."""
    films = []
    current = None
    for line in raw_text.splitlines():
        line = line.strip()
        if not line:
            continue
        date_match = re.match(r"^(\d{6})\s*$", line)
        if date_match:
            if current and current.get("channel") and current.get("title"):
                films.append(current)
            current = {"date": date_match.group(1)}
            continue
        if current is None:
            continue
        channel_match = re.match(r"^([A-ZÀÈÉÌÒÙ0-9\s]{3,20})\s+(\d{2}\.\d{2})\-(\d{2}\.\d{2})", line)
        if channel_match:
            current["channel"] = channel_match.group(1).strip()
            current["start"] = channel_match.group(2)
            current["end"] = channel_match.group(3)
            continue
        title_match = re.match(r"^([A-ZÀÈÉÌÒÙ0-9\s\-\'\",\.\(\)\:\!\?\/]{4,80})$", line)
        if title_match and not line.startswith(("con ", "di ", "West", "Dramm", "Azion", "Comme", "Thril", "Horro", "Docum", "Anima")):
            current["title"] = line.strip()
            continue
        if line.startswith("con ") and len(line) > 5:
            current["cast"] = line[4:].strip()
            continue
        genre_match = re.match(r"^(West\.|Dramm\.|Azion[e]?|Thrill\.|Horror|Docum\.|Anima[z]?\.|Comm[\.e]?d[ia]?[a]?\.?|Fant[a]?\.?|Storico|Avvent\.|Music[a]?\.?|Guerra|Biografico|Comico|Sentim\.)", line, re.IGNORECASE)
        if genre_match:
            current["genre"] = line.strip()
            continue
        director_match = re.match(r"^di ([A-ZÀÈÉÌÒÙ\.\s]{3,40})$", line)
        if director_match:
            current["director"] = director_match.group(1).strip()
            continue
    if current and current.get("channel") and current.get("title"):
        films.append(current)
    return films if films else None


def parse_weather_observation(raw_text: str) -> list[dict] | None:
    """Parse weather observation data."""
    stations = []
    current = None
    for line in raw_text.splitlines():
        line = line.strip()
        if not line:
            continue
        if re.match(r"(OSSERVAZIONI|VERSANTE|ALPI|PREVISIONI|A\.M\.|SERVIZIO)", line, re.IGNORECASE):
            continue
        if re.match(r"^\d+/\d+$", line):
            continue

        station_match = re.match(r"^([A-ZÀÈÉÌÒÙ][A-ZÀÈÉÌÒÙ\s\.\-]{2,28}?)(?:\s*\(([A-Z]{2,4})\))?(?:\s{2,}(.+))?$", line)
        if station_match and not line.startswith(("Temp:", "Vento:", "Visib:", "n.p.", "Osservazione")):
            name = station_match.group(1).strip()
            if name and len(name) >= 3 and not name.startswith(("Temp", "Vent", "Visi")):
                if current and current.get("name"):
                    stations.append(current)
                current = {"name": name}
                code = station_match.group(2)
                if code:
                    current["code"] = code
                extra = station_match.group(3)
                if extra and re.match(r"(Sereno|Poco nuvoloso|Nuvoloso|Coperto|Pioggia|Temporale|Nebbia|Foschia|Parz)", extra, re.IGNORECASE):
                    current["condition"] = extra.strip()
                continue

        if current is None:
            continue

        if line.startswith("Temp:"):
            temp_part = line.replace("Temp:", "").strip()
            vento_match = re.search(r"\s{2,}Vento:(.+)", temp_part)
            if vento_match:
                current["temp"] = temp_part[:vento_match.start()].strip()
                current["wind"] = vento_match.group(1).strip()
            else:
                current["temp"] = temp_part
        elif line.startswith("Vento:"):
            current["wind"] = line.replace("Vento:", "").strip()
        elif line.startswith("Visib:"):
            current["visibility"] = line.replace("Visib:", "").strip()
        elif re.match(r"^(Sereno|Poco nuvoloso|Nuvoloso|Coperto|Pioggia|Temporale|Nebbia|Foschia|Parz\.?\s*nuv)", line, re.IGNORECASE):
            current["condition"] = line.strip()
        elif line.startswith("Osservazione non disponibile"):
            current["condition"] = "n.d."
    if current and current.get("name"):
        stations.append(current)
    return stations if len(stations) >= 2 else None


def parse_temperatures(raw_text: str) -> list[dict] | None:
    """Parse temperature table (min/max for cities)."""
    cities = []
    for line in raw_text.splitlines():
        line = line.strip()
        match = re.match(
            r"^([A-ZÀÈÉÌÒÙ\s]{3,25})\s+(-?\d{1,2})\s+(-?\d{1,2})",
            line,
        )
        if match:
            tmin = int(match.group(2))
            tmax = int(match.group(3))
            # Normalize to 0-60 range for display (min temp -10, max temp +45)
            norm_min = max(0, (tmin + 10) * 100 / 55)
            norm_width = max(3, (tmax - tmin) * 100 / 55)
            cities.append({
                "city": match.group(1).strip().title(),
                "min": tmin,
                "max": tmax,
                "bar_left": round(norm_min, 1),
                "bar_width": round(norm_width, 1),
            })
    return cities if len(cities) >= 3 else None


def parse_lotto_results(raw_text: str) -> dict | None:
    """Parse Lotto extraction results."""
    date_match = re.search(r"ESTRAZIONE DEL\s+(\d{2}/\d{2}/\d{4})", raw_text, re.IGNORECASE)
    wheels = {}
    for line in raw_text.splitlines():
        line = line.strip()
        match = re.match(r"^([A-ZÀÈÉÌÒÙ]{3,12})\s+(\d{1,2}\s+\d{1,2}\s+\d{1,2}\s+\d{1,2}\s+\d{1,2})", line)
        if match:
            wheel = match.group(1).strip().title()
            numbers = [int(n) for n in match.group(2).split()]
            wheels[wheel] = numbers
    if wheels:
        result = {"wheels": wheels}
        if date_match:
            result["date"] = date_match.group(1)
        return result
    return None


def parse_auditel(raw_text: str) -> list[dict] | None:
    """Parse Auditel ratings table."""
    rows = []
    for line in raw_text.splitlines():
        line = line.strip()
        match = re.match(
            r"^([A-ZÀÈÉÌÒÙ0-9][A-ZÀÈÉÌÒÙ0-9\s\-]{2,28}?)\s{2,}([\d\.]+)\s{2,}([\d\.]+)",
            line,
        )
        if match:
            rows.append({
                "channel": match.group(1).strip(),
                "share": match.group(2),
                "viewers": match.group(3),
            })
    return rows if len(rows) >= 3 else None


def parse_article_multipage(snapshots: list) -> dict | None:
    """Merge multi-page articles into a single structured article."""
    if not snapshots:
        return None
    raw_parts = []
    title = snapshots[0].get("title", "")
    for snap in snapshots:
        text = snap.get("raw_text", "")
        # Remove page numbering like "1/5", "2/5"
        text = re.sub(r"^\s*\d+/\d+\s*$", "", text, flags=re.MULTILINE)
        text = re.sub(r"^\d+/\d+\s*", "", text, flags=re.MULTILINE)
        # Remove cross-reference footers
        text = re.sub(r"Almanacco \d+.*?(?=\n|$)", "", text)
        text = re.sub(r"In viaggio \d+.*?(?=\n|$)", "", text)
        text = re.sub(r"\d{3}\s+\w+.*?(?=\n|$)", "", text)
        raw_parts.append(text.strip())
    full_text = "\n\n".join(p for p in raw_parts if p)
    return {
        "title": title,
        "body": full_text,
        "pages": len(snapshots),
    }


def format_date_televideo(date_str: str) -> str:
    """Format Televideo date (DDMMYY or DD/MM/YYYY) to readable format."""
    date_str = date_str.strip()
    if re.match(r"^\d{6}$", date_str):
        day, month, year = int(date_str[:2]), int(date_str[2:4]), int(date_str[4:6])
        year += 2000
        return f"{day:02d}/{month:02d}/{year}"
    return date_str


def group_snapshots(snapshots: list) -> dict[str, list]:
    """Group snapshots by logical content type."""
    groups = {"index": [], "tables": [], "articles": [], "schedules": []}
    for snap in snapshots:
        kind = snap.get("content_kind", "article")
        if kind in groups:
            groups[kind].append(snap)
        else:
            groups["articles"].append(snap)
    return groups


def merge_snapshot_pages(snapshots: list) -> list:
    """Merge multi-page snapshots with the same page number into single entries."""
    merged = {}
    for snap in snapshots:
        page = snap.get("page", 0)
        if page not in merged:
            merged[page] = snap.copy()
            merged[page]["all_text"] = snap.get("raw_text", "")
            merged[page]["subpages"] = [snap.get("subpage", "01")]
        else:
            merged[page]["all_text"] += "\n" + snap.get("raw_text", "")
            merged[page]["subpages"].append(snap.get("subpage", ""))
    return sorted(merged.values(), key=lambda s: s.get("sort_order", 0))
