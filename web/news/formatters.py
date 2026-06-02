"""
Content formatters: parse raw Televideo text into structured data for display.
"""
from __future__ import annotations

import re
from datetime import date as date_type

from .services.parser import compact_text, display_snapshot_text, prose_paragraphs


DAY_HEADING_RE = re.compile(
    r"^(DOMENICA|LUNEDI'?|MARTEDI|MERCOLEDI|GIOVEDI|VENERDI|SABATO)\s+\d{1,2}\s+[A-ZÀÈÉÌÒÙ']+",
    re.IGNORECASE,
)
TRAILING_PAGE_RE = re.compile(
    r"^(?P<label>.+?)\s+(?:p\.?\s*)?(?P<page>\d{3})(?:\s*(?:>|-|/)\s*(?P<end>\d{3}))?(?:\s+[jJ])?\s*$",
    re.IGNORECASE,
)
LEADING_PAGE_RE = re.compile(
    r"^(?P<page>\d{3})(?:\s*(?:>|-|/)\s*(?P<end>\d{3}))?\s+(?P<label>.+?)\s*$",
    re.IGNORECASE,
)


def parse_televideo_card(raw_text: str, title: str = "", label: str = "", content_kind: str = "") -> dict:
    """Parse generic Televideo pages into displayable blocks."""
    lines = normalized_televideo_lines(raw_text, title=title, label=label)
    index_items, index_used = parse_index_items(lines)
    schedule_groups, schedule_used = parse_program_groups(lines, index_used, content_kind)
    used_indexes = index_used | schedule_used
    paragraphs = paragraphs_from_lines(lines, used_indexes, skip_headings=bool(index_items))

    if not (index_items or schedule_groups or paragraphs):
        paragraphs = prose_paragraphs(raw_text)

    return {
        "index_items": index_items,
        "schedule_groups": schedule_groups,
        "paragraphs": paragraphs,
        "has_content": bool(index_items or schedule_groups or paragraphs),
    }


def normalized_televideo_lines(raw_text: str, *, title: str = "", label: str = "") -> list[dict]:
    title_keys = {line_key(title), line_key(label)} - {""}
    lines = []
    previous_key = ""

    for raw_line in display_snapshot_text(raw_text).splitlines():
        text = clean_display_line(raw_line)
        key = line_key(text)
        if not text or not key:
            continue
        if key in title_keys:
            continue
        if key == previous_key:
            continue
        if is_noise_line(text):
            continue
        lines.append({"raw": raw_line.rstrip(), "text": text})
        previous_key = key
    return lines


def clean_display_line(raw_line: str) -> str:
    text = compact_text(raw_line).strip()
    text = text.strip(' "')
    text = re.sub(r"\s+[jJ]\s*$", "", text)
    return text.strip()


def line_key(value: str) -> str:
    return re.sub(r"\W+", "", compact_text(value).casefold(), flags=re.UNICODE)


def is_noise_line(text: str) -> bool:
    if len(text) <= 2 and not re.search(r"\d{3}", text):
        return True
    return not re.search(r"[A-Za-zÀ-ÿ0-9]", text)


def parse_index_items(lines: list[dict]) -> tuple[list[dict], set[int]]:
    items = []
    used = set()
    seen = set()
    last_item = None

    for index, line in enumerate(lines):
        entry = parse_index_entry(line["text"])
        if entry:
            key = (entry["page"], entry.get("end_page"), line_key(entry["label"]))
            if key not in seen:
                items.append(entry)
                seen.add(key)
                last_item = entry
            used.add(index)
            continue

        if last_item and continuation_for_index(line, last_item):
            last_item["label"] = f"{last_item['label']} {clean_index_label(line['text'])}"
            used.add(index)
            continue

        last_item = None

    return items, used


def parse_index_entry(text: str) -> dict | None:
    trailing = TRAILING_PAGE_RE.match(text)
    if trailing:
        label = clean_index_label(trailing.group("label"))
        if valid_index_label(label):
            return build_index_entry(label, trailing.group("page"), trailing.group("end"))

    leading = LEADING_PAGE_RE.match(text)
    if leading:
        label = clean_index_label(leading.group("label"))
        if valid_index_label(label):
            return build_index_entry(label, leading.group("page"), leading.group("end"))
    return None


def build_index_entry(label: str, page: str, end_page: str | None = None) -> dict:
    return {
        "label": label,
        "page": page,
        "end_page": end_page or "",
        "page_label": f"{page}-{end_page}" if end_page else page,
    }


def clean_index_label(label: str) -> str:
    label = compact_text(label)
    label = re.sub(r"\s+[jJ]\s*$", "", label)
    label = re.sub(r"\s+[.\"`£òùè0]{1,4}$", "", label)
    return label.strip(" -")


def valid_index_label(label: str) -> bool:
    if len(label) < 3:
        return False
    if re.search(r"\bpag\.?$|\bpagina$", label, re.IGNORECASE):
        return False
    return bool(re.search(r"[A-Za-zÀ-ÿ]", label))


def continuation_for_index(line: dict, last_item: dict) -> bool:
    text = line["text"]
    if parse_index_entry(text):
        return False
    if len(last_item.get("label", "")) > 18 or len(text) > 18:
        return False
    return line["raw"].startswith(" ") and text.isupper()


def parse_program_groups(lines: list[dict], index_used: set[int], content_kind: str) -> tuple[list[dict], set[int]]:
    if content_kind != "schedule" and not any(is_day_heading(line["text"]) for line in lines):
        return [], set()

    groups = []
    used = set()
    current_group = None
    current_channel = ""
    current_week = ""
    saw_schedule_marker = False

    for index, line in enumerate(lines):
        if index in index_used:
            continue

        text = line["text"]
        if is_week_heading(text):
            current_week = text
            saw_schedule_marker = True
            used.add(index)
            continue

        if is_channel_heading(text):
            current_channel = text
            saw_schedule_marker = True
            used.add(index)
            continue

        if is_day_heading(text):
            title = f"{current_channel} · {text}" if current_channel else text
            current_group = {"title": title, "kicker": current_week, "items": []}
            groups.append(current_group)
            saw_schedule_marker = True
            used.add(index)
            continue

        if current_group and saw_schedule_marker:
            append_program_item(current_group, line)
            used.add(index)

    groups = [group for group in groups if group["items"]]
    if not groups:
        return [], set()
    return groups, used


def is_week_heading(text: str) -> bool:
    return bool(re.match(r"^SETTIMANA\s+DAL\b", text, re.IGNORECASE))


def is_day_heading(text: str) -> bool:
    return bool(DAY_HEADING_RE.match(text))


def is_channel_heading(text: str) -> bool:
    if parse_index_entry(text):
        return False
    return bool(re.match(r"^RAI\s+(?:\d|SPORT|MOVIE|PREMIUM|YOYO|GULP|STORIA|SCUOLA|RADIO)\b", text, re.IGNORECASE))


def append_program_item(group: dict, line: dict) -> None:
    text = line["text"]
    items = group["items"]
    if items and (line["raw"].startswith(" ") or items[-1].endswith("-")):
        if items[-1].endswith("-"):
            items[-1] = items[-1][:-1] + text
        else:
            items[-1] = f"{items[-1]} {text}"
        return
    items.append(text)


def paragraphs_from_lines(lines: list[dict], used_indexes: set[int], *, skip_headings: bool = False) -> list[str]:
    paragraphs = []
    current = ""

    def flush() -> None:
        nonlocal current
        text = compact_text(current)
        if text:
            paragraphs.append(text)
        current = ""

    for index, line in enumerate(lines):
        if index in used_indexes:
            flush()
            continue
        text = line["text"]
        if skip_headings and looks_like_standalone_heading(text):
            flush()
            continue
        if current.endswith("-"):
            current = current[:-1] + text
        elif current:
            current += " " + text
        else:
            current = text
    flush()
    return paragraphs


def looks_like_standalone_heading(text: str) -> bool:
    if parse_index_entry(text):
        return False
    if len(text) > 44:
        return False
    letters = re.findall(r"[A-Za-zÀ-ÿ]", text)
    if not letters:
        return False
    uppercase = re.findall(r"[A-ZÀÈÉÌÒÙ]", text)
    return len(uppercase) / len(letters) > 0.78


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
    paragraphs = []
    title = snapshots[0].get("title", "")
    normalized_title = compact_text(title).casefold()
    for index, snap in enumerate(snapshots):
        text = snap.get("raw_text", "")
        if index == 0 and normalized_title:
            lines = display_snapshot_text(text).splitlines()
            for line_index, line in enumerate(lines):
                if not line.strip():
                    continue
                if compact_text(line).casefold() == normalized_title:
                    lines.pop(line_index)
                break
            text = "\n".join(lines)
        paragraphs.extend(prose_paragraphs(text))
    full_text = "\n\n".join(paragraphs)
    return {
        "title": title,
        "body": full_text,
        "paragraphs": paragraphs,
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
            if "paragraphs" in merged[page]:
                merged[page]["paragraphs"] = list(merged[page].get("paragraphs") or [])
            merged[page]["all_text"] = snap.get("raw_text", "")
            merged[page]["subpages"] = [snap.get("subpage", "01")]
        else:
            merged[page]["all_text"] += "\n" + snap.get("raw_text", "")
            merged[page].setdefault("paragraphs", [])
            merged[page]["paragraphs"].extend(snap.get("paragraphs") or [])
            merged[page]["subpages"].append(snap.get("subpage", ""))
    return sorted(merged.values(), key=lambda s: s.get("sort_order", 0))


def parse_tv_channel_schedule(raw_text: str) -> list[dict] | None:
    """Parse TV channel schedule with time + program entries."""
    programs = []
    current = None
    for raw_line in raw_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        time_match = re.match(r"^(\d{2}[:.]\d{2})\s+(.+)", line)
        if time_match:
            time_str = time_match.group(1)
            program = time_match.group(2).strip()
            current = {"time": time_str, "program": program}
            programs.append(current)
            continue
        if re.match(r"^\d{1,2}\s+[A-Za-zÀ-ÿ]+(?:\s+\d{4})?$", line) or line.startswith("*"):
            current = None
            continue
        if current and raw_line.startswith("     "):
            if current["program"].endswith("-"):
                current["program"] = current["program"][:-1] + line
            else:
                current["program"] += " " + line
    return programs if len(programs) >= 3 else None
