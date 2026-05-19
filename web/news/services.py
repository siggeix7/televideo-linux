from __future__ import annotations

import hashlib
import html
import json
import os
import re
import threading
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import date
from decimal import Decimal, InvalidOperation
from email.utils import parsedate_to_datetime
from functools import lru_cache

from django.conf import settings
from django.db import close_old_connections, transaction
from django.utils import timezone

from .models import Category, NewsItem, SuperEnalottoDraw


BASE_URLS = (
    "https://www.televideo.rai.it/televideo/pub/",
    "https://www.servizitelevideo.rai.it/televideo/pub/",
)
RSS_PATH = "rss101.xml"
TEXT_PATH = "solotesto.jsp"
CATEGORY_INDEX_PAGE = "104"
SUPERENALOTTO_PAGE = "696"
USER_AGENT = "televideo-linux-web/1.0"
GOOGLE_TRANSLATE_URL = "https://translate.googleapis.com/translate_a/single"
MYMEMORY_URL = "https://api.mymemory.translated.net/get"
SUMMARY_SENTENCES = 2
SUMMARY_MAX_CHARS = 360
_REFRESH_LOCK = threading.Lock()

CATEGORY_LABELS = {
    101: ("rss101", "Ultim'Ora", "Novissima Hora", "Breaking News"),
    103: ("p103", "Prima", "Prima Pagina", "Front Page"),
    105: ("p105", "Edicola", "Acta Diurna", "Press Review"),
    108: ("p108", "Ultim'Ora Flash", "Novissima Brevia", "News Flash"),
    109: ("p109", "Ultime News", "Novissima", "Latest News"),
    110: ("p110", "Attualita'", "Res Hodiernae", "Current Affairs"),
    120: ("p120", "Politica", "Politica", "Politics"),
    130: ("p130", "Economia", "Oeconomia", "Economy"),
    140: ("p140", "Dall'Italia", "Ex Italia", "Italy"),
    150: ("p150", "Dal Mondo", "Ex Mundo", "World"),
    160: ("p160", "Culture", "Culturae", "Culture"),
    170: ("p170", "Cittadini", "Cives", "Citizens"),
    180: ("p180", "Focus", "Inquisitio", "Focus"),
    190: ("p190", "Motori", "Currus", "Motors"),
    201: ("p201", "Calcio", "Pediludium", "Football"),
    260: ("p260", "Altri Sport", "Alii Ludi", "Other Sports"),
    299: ("p299", "Brevi Sport", "Breves Ludi", "Sports Briefs"),
    401: ("p401", "Almanacco", "Almanach", "Almanac"),
    613: ("p613", "Viabilita'", "Viae", "Traffic"),
    700: ("p700", "Meteo", "Tempestas", "Weather"),
    711: ("p711", "Temperature", "Temperaturae", "Temperatures"),
}
COMPOSITE_CATEGORY_PAGES = {103, 105, 110, 170, 180, 190}
EXTRA_CATEGORY_PAGES = (201, 260, 299, 401, 613, 700, 711)


def strip_html(value: str) -> str:
    value = re.sub(r"<br\s*/?>", "\n", value, flags=re.IGNORECASE)
    value = re.sub(r"<[^>]+>", "", value)
    return html.unescape(value)


def compact_text(value: str) -> str:
    return re.sub(r"\s+", " ", strip_html(value)).strip()


def request_text(url: str, timeout: float) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="replace")


def fetch_text(urls: list[str], timeout: float, retries: int) -> tuple[str, str]:
    errors = []
    for _ in range(retries + 1):
        for url in urls:
            try:
                return request_text(url, timeout), url
            except (TimeoutError, urllib.error.URLError, urllib.error.HTTPError) as exc:
                errors.append(str(exc))
    last_error = errors[-1] if errors else "nessun URL configurato"
    raise RuntimeError(f"nessuna risposta valida dagli host Rai: {last_error}")


def build_rss_urls() -> list[str]:
    return [base_url + RSS_PATH for base_url in BASE_URLS]


def build_text_urls(page: str) -> list[str]:
    path = TEXT_PATH + "?" + urllib.parse.urlencode({"pagina": page})
    return [base_url + path for base_url in BASE_URLS]


def page_link(page: int | str) -> str:
    return BASE_URLS[0] + TEXT_PATH + "?" + urllib.parse.urlencode({"pagina": str(page).zfill(3)})


def extract_page_content(html_text: str) -> str:
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


def fetch_televideo_content(page: int | str) -> str:
    source, _ = fetch_text(build_text_urls(str(page).zfill(3)), settings.TRANSLATION_TIMEOUT, settings.TRANSLATION_RETRIES)
    return extract_page_content(source)


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


def category_from_labels(page: int, sort_order: int) -> Category:
    code, name_it, name_la, name_en = CATEGORY_LABELS[page]
    category, _ = Category.objects.update_or_create(
        code=code,
        defaults={
            "page": page,
            "name_it": name_it,
            "name_la": name_la,
            "name_en": name_en,
            "sort_order": sort_order,
            "active": True,
            "fetched_at": timezone.now(),
        },
    )
    return category


def sync_categories_from_page_104() -> list[Category]:
    rss_category = category_from_labels(101, 0)
    try:
        content = fetch_televideo_content(CATEGORY_INDEX_PAGE)
        discovered_pages = []
        for match in re.finditer(r"\b(\d{3})\b", content):
            page = int(match.group(1))
            if page in CATEGORY_LABELS and page not in {101, 104} and page not in discovered_pages:
                discovered_pages.append(page)
    except RuntimeError:
        discovered_pages = [page for page in CATEGORY_LABELS if page != 101]

    for page in EXTRA_CATEGORY_PAGES:
        if page not in discovered_pages:
            discovered_pages.append(page)

    categories = [rss_category]
    for index, page in enumerate(discovered_pages, start=1):
        categories.append(category_from_labels(page, index))
    return categories


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


def google_translate(text: str, target_language: str, timeout: float) -> str:
    query = {
        "client": "gtx",
        "sl": "it",
        "tl": target_language,
        "dt": "t",
        "q": text,
    }
    url = GOOGLE_TRANSLATE_URL + "?" + urllib.parse.urlencode(query)
    source = request_text(url, timeout)
    payload = json.loads(source)
    if not isinstance(payload, list) or not payload or not isinstance(payload[0], list):
        raise RuntimeError("risposta Google Translate inattesa")
    translated = "".join(segment[0] for segment in payload[0] if isinstance(segment, list) and segment and isinstance(segment[0], str))
    translated = compact_text(translated)
    if not translated:
        raise RuntimeError("Google Translate senza testo tradotto")
    return translated


def mymemory_translate(text: str, target_language: str, timeout: float) -> str:
    query = {"q": text, "langpair": f"it|{target_language}"}
    email = os.environ.get("TELEVIDEO_MYMEMORY_EMAIL")
    if email:
        query["de"] = email
    url = MYMEMORY_URL + "?" + urllib.parse.urlencode(query)
    payload = json.loads(request_text(url, timeout))
    response = payload.get("responseData")
    if not isinstance(response, dict):
        raise RuntimeError("traduttore MyMemory senza responseData")
    translated = compact_text(str(response.get("translatedText") or ""))
    if not translated:
        raise RuntimeError("traduttore MyMemory senza testo tradotto")
    return translated


@lru_cache(maxsize=1024)
def translate_text(text: str, target_language: str) -> str:
    if target_language == "it":
        return text
    timeout = settings.TRANSLATION_TIMEOUT
    providers = (google_translate, mymemory_translate)
    for provider in providers:
        try:
            return provider(text, target_language, timeout)
        except (RuntimeError, TimeoutError, urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError):
            continue
    return text


def medieval_latin_style(text: str) -> str:
    substitutions = (
        (r"\bPapa\b", "dominus Papa"),
        (r"\bPontifex\b", "summus Pontifex"),
        (r"\bminister\b", "dominus minister"),
        (r"\bItalia\b", "regnum Italiae"),
        (r"\bhodie\b", "hoc die"),
    )
    for pattern, replacement in substitutions:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    text = re.sub("ae", "e", text, flags=re.IGNORECASE)
    text = re.sub("oe", "e", text, flags=re.IGNORECASE)
    return compact_text(text)


def ensure_sentence(text: str) -> str:
    text = compact_text(text)
    if not text:
        return text
    if re.search(r"(\.\.\.|[.!?])[\"'»”)]*$", text):
        return text
    return text + "."


def preserve_title_lead(source_title: str, translated_title: str) -> str:
    if ":" not in source_title or ":" not in translated_title:
        return translated_title
    source_lead = source_title.split(":", 1)[0].strip()
    if not re.fullmatch(r"[A-Z][\w'.-]{1,24}", source_lead, flags=re.UNICODE):
        return translated_title
    return source_lead + ":" + translated_title.split(":", 1)[1]


def italian_chronicle(summary: str) -> str:
    return ensure_sentence(summary)


def english_chronicle(summary: str) -> str:
    translated = translate_text(summary, "en")
    return ensure_sentence(translated)


def latin_chronicle(summary: str) -> str:
    translated = medieval_latin_style(translate_text(summary, "la"))
    return ensure_sentence(translated)


def build_translated_item(item: dict[str, str], category: Category | None = None, source_page: str = "") -> dict[str, object]:
    title_it = item["title"]
    summary_it = summarize_description(item["description"])
    title_la = preserve_title_lead(title_it, medieval_latin_style(translate_text(title_it, "la")))
    title_en = preserve_title_lead(title_it, translate_text(title_it, "en"))
    return {
        "source_id": source_id_for(item),
        "category": category,
        "source_page": source_page,
        "link": item["link"],
        "pub_date_text": item["pub_date"],
        "published_at": parse_published_at(item["pub_date"]),
        "title_it": title_it,
        "summary_it": italian_chronicle(summary_it),
        "title_la": title_la,
        "summary_la": latin_chronicle(summary_it),
        "title_en": title_en,
        "summary_en": english_chronicle(summary_it),
    }


def save_item(item: dict[str, str], category: Category | None = None, source_page: str = "") -> int:
    source_id = source_id_for(item)
    existing = NewsItem.objects.filter(source_id=source_id).first()
    if existing:
        existing.category = category or existing.category
        existing.source_page = source_page or existing.source_page
        existing.pub_date_text = item.get("pub_date", existing.pub_date_text)
        existing.link = item.get("link", existing.link)
        existing.fetched_at = timezone.now()
        existing.save(update_fields=["category", "source_page", "pub_date_text", "link", "fetched_at"])
        return 1

    defaults = build_translated_item(item, category=category, source_page=source_page)
    defaults.pop("source_id")
    NewsItem.objects.create(source_id=source_id, **defaults)
    return 1


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
    return False


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


def parse_italian_decimal(value: str) -> Decimal | None:
    try:
        return Decimal(value.replace(".", "").replace(",", "."))
    except (InvalidOperation, AttributeError):
        return None


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


def update_superenalotto() -> int:
    content = fetch_televideo_content(SUPERENALOTTO_PAGE)
    defaults = parse_superenalotto_content(content)
    draw_number = int(defaults.pop("draw_number"))
    draw_date = defaults.pop("draw_date")
    SuperEnalottoDraw.objects.update_or_create(
        draw_number=draw_number,
        draw_date=draw_date,
        defaults=defaults,
    )
    return 1


def update_rss_news(limit: int | None, category: Category) -> int:
    rss_text, _ = fetch_text(build_rss_urls(), settings.TRANSLATION_TIMEOUT, settings.TRANSLATION_RETRIES)
    items = parse_rss(rss_text)
    if limit:
        items = items[:limit]
    return sum(save_item(item, category=category, source_page="101") for item in items)


def update_category_news(categories: list[Category], per_category_limit: int) -> int:
    saved = 0
    category_pages = {category.page for category in categories if category.page}
    for category in categories:
        if not category.page or category.page == 101:
            continue
        try:
            content = fetch_televideo_content(category.page)
        except RuntimeError:
            continue
        if not content.strip() or "Pagina vuota" in content:
            continue

        detail_pages = detail_pages_from_category(content, {int(page) for page in category_pages})[:per_category_limit]
        if not detail_pages and category.page not in COMPOSITE_CATEGORY_PAGES:
            detail_pages = [category.page]

        for page in detail_pages:
            try:
                article_content = fetch_televideo_content(page)
            except RuntimeError:
                continue
            article = parse_article_content(article_content, category.name_it)
            if not article:
                continue
            title, description = article
            source_key = f"{category.code}:{page}:{title}"
            item = {
                "source_id": hashlib.sha256(source_key.encode("utf-8")).hexdigest()[:24],
                "title": title,
                "description": description,
                "pub_date": f"Televideo pagina {page}",
                "link": page_link(page),
            }
            saved += save_item(item, category=category, source_page=str(page))
    return saved


def update_news(limit: int | None = None, category_limit: int | None = None) -> int:
    category_limit = settings.CATEGORY_FETCH_LIMIT if category_limit is None else category_limit
    with transaction.atomic():
        categories = sync_categories_from_page_104()
        saved = update_rss_news(limit, categories[0])
        saved += update_category_news(categories, category_limit)
        try:
            saved += update_superenalotto()
        except RuntimeError:
            pass
    return saved


def refresh_if_stale() -> None:
    latest = NewsItem.objects.order_by("-fetched_at").first()
    if latest and (timezone.now() - latest.fetched_at).total_seconds() < settings.NEWS_REFRESH_SECONDS:
        return
    if not _REFRESH_LOCK.acquire(blocking=False):
        return

    thread = threading.Thread(target=refresh_worker, daemon=True)
    thread.start()


def refresh_worker() -> None:
    try:
        close_old_connections()
        update_news(settings.NEWS_FETCH_LIMIT, settings.CATEGORY_FETCH_LIMIT)
    finally:
        close_old_connections()
        _REFRESH_LOCK.release()
