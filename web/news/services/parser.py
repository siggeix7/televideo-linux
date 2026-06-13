from __future__ import annotations

import hashlib
import html
import re
import xml.etree.ElementTree as ET
from datetime import date
from decimal import Decimal, InvalidOperation
from email.utils import parsedate_to_datetime

from django.utils import timezone

from .constants import COMPOSITE_CATEGORY_PAGES, LOTTO_PAGES, SUMMARY_MAX_CHARS, SUMMARY_SENTENCES


ITALIAN_MONTHS = {
    "gennaio": 1,
    "febbraio": 2,
    "marzo": 3,
    "aprile": 4,
    "maggio": 5,
    "giugno": 6,
    "luglio": 7,
    "agosto": 8,
    "settembre": 9,
    "ottobre": 10,
    "novembre": 11,
    "dicembre": 12,
}


def strip_html(value: str) -> str:
    value = re.sub(r"<br\s*/?>", "\n", value, flags=re.IGNORECASE)
    value = re.sub(r"<[^>]+>", "", value)
    return html.unescape(value)


def compact_text(value: str) -> str:
    return re.sub(r"\s+", " ", strip_html(value)).strip()


MOJIBAKE_MARKERS = ("\u00c3", "\u00c2", "\u00e2\u20ac", "\u00e2\u20ac\u2122", "\u00e2\u20ac\u0153", "\u00e2\u20ac\u009d")
SUBPAGE_MARKER_RE = re.compile(r"^\s*(?:\d{1,2}/\d{1,2}|-\d+-|[<>]{2})\s*$")


def fix_mojibake(value: str) -> str:
    if not value or not any(marker in value for marker in MOJIBAKE_MARKERS):
        return value
    try:
        fixed = value.encode("latin1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return value
    original_score = sum(value.count(marker) for marker in MOJIBAKE_MARKERS)
    fixed_score = sum(fixed.count(marker) for marker in MOJIBAKE_MARKERS)
    return fixed if fixed_score < original_score else value


def is_subpage_marker(line: str) -> bool:
    return bool(SUBPAGE_MARKER_RE.fullmatch(line.strip()))


def is_navigation_line(line: str) -> bool:
    compact = compact_text(line)
    if not compact:
        return False
    if "www.servizitelevideo.rai.it" in compact or "RAI INFORMA" in compact:
        return True
    lowered = compact.casefold()
    if "televideo regionale" in lowered:
        return True
    if "del televideo" in lowered or "sul televideo" in lowered:
        return True
    if lowered.startswith("per le frequenze"):
        return True
    if re.search(r"\b\d{3}\s*(?:>|-|/)\s*\d{3}\b", compact):
        return False
    return len(re.findall(r"\b\d{3}\b", compact)) >= 2


def is_artifact_line(line: str) -> bool:
    compact = re.sub(r"\s+", "", compact_text(line))
    if len(compact) >= 8 and re.fullmatch(r"[ùò£pPqQnNoO0|_\-]+", compact):
        return True
    if len(compact) >= 8:
        repeated = max(compact.count(char) for char in set(compact))
        if repeated / len(compact) >= 0.82 and not re.search(r"\d{3}", compact):
            return True
    return False


def display_snapshot_text(content: str) -> str:
    lines: list[str] = []
    for raw_line in clean_snapshot_text(content).splitlines():
        line = raw_line.strip()
        if is_subpage_marker(line) or is_navigation_line(line) or is_artifact_line(line):
            continue
        lines.append(raw_line.rstrip())
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    return "\n".join(lines)


def prose_paragraphs(content: str) -> list[str]:
    paragraphs: list[str] = []
    current = ""

    def flush() -> None:
        nonlocal current
        text = compact_text(current).strip()
        if text:
            paragraphs.append(text)
        current = ""

    for raw_line in display_snapshot_text(content).splitlines():
        line = raw_line.strip()
        if not line:
            flush()
            continue
        if is_subpage_marker(line) or is_navigation_line(line):
            flush()
            continue
        if current.endswith("-"):
            current = current[:-1] + line
        elif current:
            current += " " + line
        else:
            current = line
    flush()
    return paragraphs


def extract_page_content(html_text: str) -> str:
    html_text = fix_mojibake(html_text)
    pre_match = re.search(r"<pre\b[^>]*>(.*?)</pre>", html_text, flags=re.IGNORECASE | re.DOTALL)
    if not pre_match:
        raise RuntimeError("formato pagina Rai non riconosciuto")
    content = strip_html(pre_match.group(1)).replace("\r\n", "\n").replace("\r", "\n").replace("\t", "")
    lines = [line.rstrip() for line in content.splitlines()]
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    return "\n".join(lines)


def parse_rss(rss_text: str) -> list[dict[str, str]]:
    try:
        root = ET.fromstring(rss_text)
    except ET.ParseError as exc:
        raise RuntimeError("formato RSS Rai non riconosciuto") from exc
    items = []
    for item in root.findall("./channel/item"):
        title = compact_text(item.findtext("title") or "")
        description = compact_text(item.findtext("description") or "")
        pub_date = compact_text(item.findtext("pubDate") or "")
        link = compact_text(item.findtext("link") or "")
        if title:
            items.append({"title": title, "description": description, "pub_date": pub_date, "link": link})
    return items


def parse_published_at(pub_date: str):
    if not pub_date or pub_date.startswith("Televideo pagina"):
        return timezone.now()
    try:
        parsed = parsedate_to_datetime(pub_date)
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        parsed = timezone.make_aware(parsed, timezone.get_current_timezone())
    return parsed


def source_id_for(item: dict[str, str]) -> str:
    if item.get("source_id"):
        return item["source_id"]
    key = item.get("link") or f"{item.get('title', '')}\0{item.get('pub_date', '')}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:24]


def summarize_description(description: str) -> str:
    text = re.sub(r"^\d{1,2}\.\d{2}\s+", "", description).strip()
    sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+|(?<=[.!?])(?=[A-Z])", text) if part.strip()]
    selected = []
    for sentence in sentences[:SUMMARY_SENTENCES]:
        candidate = " ".join(selected + [sentence])
        if len(candidate) <= SUMMARY_MAX_CHARS:
            selected.append(sentence)
            continue
        if not selected:
            selected.append(sentence[:SUMMARY_MAX_CHARS].rsplit(" ", 1)[0].rstrip(" ,.;:") + "...")
        break
    return " ".join(selected) or text


def detail_pages_from_category(content: str, category_pages: set[int]) -> list[int]:
    pages: list[int] = []
    for line in content.splitlines():
        match = re.search(r"\b(\d{3})\s*$", line)
        if not match:
            continue
        page = int(match.group(1))
        if page in category_pages or page in pages:
            continue
        pages.append(page)
    return pages


def unwrap_televideo_lines(lines: list[str]) -> str:
    output: list[str] = []
    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            if output and output[-1] != "\n":
                output.append("\n")
            continue
        if "www.servizitelevideo.rai.it" in line or "RAI INFORMA" in line or "Ultime News Flash" in line:
            continue
        if output and output[-1].endswith("-"):
            output[-1] = output[-1][:-1] + line
        elif output and output[-1] != "\n":
            output[-1] += " " + line
        else:
            output.append(line)
    return re.sub(r"\n{3,}", "\n\n", "".join(output)).strip()


def parse_article_content(content: str, fallback_title: str) -> tuple[str, str] | None:
    if not content.strip() or "Pagina vuota" in content:
        return None
    lines = [line for line in content.splitlines() if line.strip()]
    if not lines:
        return None
    title_line = lines[0].strip()
    body_start = 1
    while title_line.endswith("-") and body_start < len(lines):
        title_line = title_line[:-1] + lines[body_start].strip()
        body_start += 1
    title = compact_text(title_line).strip(" -") or fallback_title
    body = unwrap_televideo_lines(lines[body_start:]) or title
    if is_low_quality_article(title, body):
        return None
    return title, body


def is_low_quality_article(title: str, body: str) -> bool:
    compact_body = compact_text(body)
    if re.fullmatch(r"\d+/\d+", title.strip()):
        return True
    if len(compact_body) < 40:
        return True
    if compact_body in {"S. S.", "S.S.", "np"}:
        return True
    if starts_mid_word(title) and starts_mid_word(compact_body):
        return True
    return False


def starts_mid_word(value: str) -> bool:
    match = re.search(r"[^\W\d_]", compact_text(value), flags=re.UNICODE)
    return bool(match and match.group(0).islower())


def parse_italian_decimal(value: str) -> Decimal | None:
    try:
        return Decimal(value.replace(".", "").replace(",", "."))
    except (InvalidOperation, AttributeError):
        return None


def parse_lotto_content(content: str) -> dict[str, object]:
    compact = compact_text(content)
    date_match = re.search(r"\b(\d{2})/(\d{2})/(\d{4})\b", compact)
    if not date_match:
        raise RuntimeError("formato Lotto non riconosciuto")
    day, month, year = (int(date_match.group(1)), int(date_match.group(2)), int(date_match.group(3)))
    wheels: dict[str, list[int]] = {}
    for line in content.splitlines():
        match = re.match(r"^\s*([A-Z. ]{3,12})\s+((?:\d{1,2}\s+){4}\d{1,2})\b", line)
        if not match:
            continue
        wheel = compact_text(match.group(1)).title()
        wheels[wheel] = [int(value) for value in match.group(2).split()]
    if not wheels:
        raise RuntimeError("ruote Lotto non riconosciute")
    return {"draw_date": date(year, month, day), "wheels": wheels, "raw_text": content}


def parse_superenalotto_content(content: str) -> dict[str, object]:
    compact = compact_text(content)
    draw_match = re.search(r"CONCORSO\s+N\.(\d+)\s+(\d{2})/(\d{2})/(\d{4})", compact, flags=re.IGNORECASE)
    if not draw_match:
        raise RuntimeError("formato SuperEnalotto non riconosciuto")
    draw_number = int(draw_match.group(1))
    day, month, year = (int(draw_match.group(2)), int(draw_match.group(3)), int(draw_match.group(4)))
    draw_date = date(year, month, day)
    numbers_match = re.search(r"^\s*(\d{1,2}(?:\s+\d{1,2}){5})\b", content, flags=re.MULTILINE)
    if not numbers_match:
        raise RuntimeError("combinazione SuperEnalotto non riconosciuta")
    winning_numbers = [int(number) for number in numbers_match.group(1).split()]
    jolly_match = re.search(r"Numero\s+Jolly\s+(\d+)", compact, flags=re.IGNORECASE)
    superstar_match = re.search(r"N\.ro\s+SuperStar\s+(\d+)", compact, flags=re.IGNORECASE)
    jackpot_match = re.search(r"Jackpot.*?euro\s+([\d.]+,\d{2})", compact, flags=re.IGNORECASE)
    prize_pool_match = re.search(r"Montepremi.*?E\.\s+([\d.]+,\d{2})", compact, flags=re.IGNORECASE)
    return {
        "draw_number": draw_number,
        "draw_date": draw_date,
        "winning_numbers": winning_numbers,
        "jolly_number": int(jolly_match.group(1)) if jolly_match else None,
        "superstar_number": int(superstar_match.group(1)) if superstar_match else None,
        "jackpot": parse_italian_decimal(jackpot_match.group(1)) if jackpot_match else None,
        "prize_pool": parse_italian_decimal(prize_pool_match.group(1)) if prize_pool_match else None,
        "raw_text": content,
    }


def parse_superenalotto_official_archive(content: str) -> list[dict[str, object]]:
    text = fix_mojibake(content)
    text = html.unescape(re.sub(r"<[^>]+>", " ", text))
    text = re.sub(r"\s+", " ", text).strip()
    pattern = re.compile(
        r"Concorso\s+N(?:[º°.]|o)?\s*(\d+)\s+del\s+"
        r"(\d{1,2})\s+([A-Za-zÀ-ÿ]+)\s+(\d{4})\s+"
        r"((?:\d{1,2}\s+){7}\d{1,2})\s+Dettagli",
        flags=re.IGNORECASE,
    )
    draws: list[dict[str, object]] = []
    seen: set[tuple[int, date]] = set()
    for match in pattern.finditer(text):
        draw_number = int(match.group(1))
        month = ITALIAN_MONTHS.get(match.group(3).casefold())
        if not month:
            continue
        draw_date = date(int(match.group(4)), month, int(match.group(2)))
        key = (draw_number, draw_date)
        if key in seen:
            continue
        values = [int(value) for value in match.group(5).split()]
        if len(values) != 8:
            continue
        winning_numbers = values[:6]
        if len(set(winning_numbers)) != 6 or any(number < 1 or number > 90 for number in values):
            continue
        seen.add(key)
        draws.append(
            {
                "draw_number": draw_number,
                "draw_date": draw_date,
                "winning_numbers": winning_numbers,
                "jolly_number": values[6],
                "superstar_number": values[7],
                "raw_text": (
                    "Fonte ufficiale SuperEnalotto archivio: "
                    f"Concorso N.{draw_number} del {draw_date.isoformat()} "
                    f"numeri {' '.join(str(number) for number in winning_numbers)} "
                    f"Jolly {values[6]} SuperStar {values[7]}"
                ),
            }
        )
    if not draws:
        raise RuntimeError("archivio ufficiale SuperEnalotto non riconosciuto")
    return draws


def clean_snapshot_text(content: str) -> str:
    content = fix_mojibake(content)
    content = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", content)
    content = re.sub(r"[£òù]{3,}", "", content)
    lines = [line.rstrip() for line in content.splitlines()]
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    return "\n".join(lines)


def empty_snapshot(content: str) -> bool:
    compact = compact_text(content).lower()
    return not compact or "pagina vuota" in compact or "servizio non disponibile" in compact


def snapshot_total_subpages(content: str) -> int:
    totals = [int(match.group(1)) for match in re.finditer(r"\b\d{1,2}/(\d{1,2})\b", content)]
    return min(max(totals or [1]), 20)


def snapshot_title(content: str, fallback: str) -> str:
    for line in content.splitlines()[:10]:
        candidate = compact_text(line).strip(" -")
        if not candidate:
            continue
        if re.fullmatch(r"\d{1,2}/\d{1,2}", candidate):
            continue
        if re.match(r"^\d{1,2}/\d{1,2}/\d{2,4}\b", candidate):
            continue
        if "www." in candidate.lower() or "servizio non disponibile" in candidate.lower():
            continue
        return candidate[:180]
    return fallback[:180]
