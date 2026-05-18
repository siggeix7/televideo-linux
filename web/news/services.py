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
from email.utils import parsedate_to_datetime
from functools import lru_cache

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .models import NewsItem


BASE_URLS = (
    "https://www.televideo.rai.it/televideo/pub/",
    "https://www.servizitelevideo.rai.it/televideo/pub/",
)
RSS_PATH = "rss101.xml"
USER_AGENT = "televideo-linux-web/1.0"
GOOGLE_TRANSLATE_URL = "https://translate.googleapis.com/translate_a/single"
MYMEMORY_URL = "https://api.mymemory.translated.net/get"
SUMMARY_SENTENCES = 2
SUMMARY_MAX_CHARS = 360
_REFRESH_LOCK = threading.Lock()


def compact_text(value: str) -> str:
    value = re.sub(r"<br\s*/?>", "\n", value, flags=re.IGNORECASE)
    value = re.sub(r"<[^>]+>", "", value)
    return re.sub(r"\s+", " ", html.unescape(value)).strip()


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
    if not pub_date:
        return None
    try:
        parsed = parsedate_to_datetime(pub_date)
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        parsed = timezone.make_aware(parsed, timezone.get_current_timezone())
    return parsed


def source_id_for(item: dict[str, str]) -> str:
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


@lru_cache(maxsize=512)
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
    return "Dalle tavole del Televideo: " + ensure_sentence(summary)


def english_chronicle(summary: str) -> str:
    translated = translate_text(summary, "en")
    return "From the Televideo chronicle: " + ensure_sentence(translated)


def latin_chronicle(summary: str) -> str:
    translated = medieval_latin_style(translate_text(summary, "la"))
    return "In chronicis scriptum est: " + ensure_sentence(translated) + " Haec rettulerunt cursores Televidei."


def build_translated_item(item: dict[str, str]) -> dict[str, object]:
    title_it = item["title"]
    summary_it = summarize_description(item["description"])
    title_la = preserve_title_lead(title_it, medieval_latin_style(translate_text(title_it, "la")))
    title_en = preserve_title_lead(title_it, translate_text(title_it, "en"))
    return {
        "source_id": source_id_for(item),
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


def update_news(limit: int | None = None) -> int:
    rss_text, _ = fetch_text(build_rss_urls(), settings.TRANSLATION_TIMEOUT, settings.TRANSLATION_RETRIES)
    items = parse_rss(rss_text)
    if limit:
        items = items[:limit]

    saved = 0
    with transaction.atomic():
        for item in items:
            source_id = source_id_for(item)
            existing = NewsItem.objects.filter(source_id=source_id).first()
            if existing:
                existing.fetched_at = timezone.now()
                existing.save(update_fields=["fetched_at"])
                saved += 1
                continue
            defaults = build_translated_item(item)
            defaults.pop("source_id")
            NewsItem.objects.create(source_id=source_id, **defaults)
            saved += 1
    return saved


def refresh_if_stale() -> None:
    latest = NewsItem.objects.order_by("-fetched_at").first()
    if latest and (timezone.now() - latest.fetched_at).total_seconds() < settings.NEWS_REFRESH_SECONDS:
        return
    if not _REFRESH_LOCK.acquire(blocking=False):
        return
    try:
        update_news(settings.NEWS_FETCH_LIMIT)
    finally:
        _REFRESH_LOCK.release()
