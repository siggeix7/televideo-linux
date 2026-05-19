from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.parse
from functools import lru_cache

from django.conf import settings

from .constants import GOOGLE_TRANSLATE_URL, MYMEMORY_URL
from .fetcher import request_text
from .parser import compact_text


MAX_TRANSLATE_CHARS = 1300


def google_translate(text: str, target_language: str, timeout: float) -> str:
    query = {"client": "gtx", "sl": "it", "tl": target_language, "dt": "t", "q": text}
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


def split_translation_units(text: str, limit: int = MAX_TRANSLATE_CHARS) -> list[str]:
    """Split long text into safe chunks for free translation endpoints."""
    text = compact_text(text)
    if not text:
        return []
    if len(text) <= limit:
        return [text]

    units = re.split(r"(?<=[.!?;:])\s+", text)
    chunks: list[str] = []
    current = ""
    for unit in units:
        if not unit:
            continue
        if len(unit) > limit:
            if current:
                chunks.append(current)
                current = ""
            for index in range(0, len(unit), limit):
                chunks.append(unit[index:index + limit].strip())
            continue
        candidate = f"{current} {unit}".strip()
        if len(candidate) > limit and current:
            chunks.append(current)
            current = unit
        else:
            current = candidate
    if current:
        chunks.append(current)
    return chunks


def translate_compact_once(text: str, target_language: str) -> str:
    timeout = settings.TRANSLATION_TIMEOUT
    providers = (google_translate, mymemory_translate)
    retries = max(int(getattr(settings, "TRANSLATION_RETRIES", 1)), 0)
    for _ in range(retries + 1):
        for provider in providers:
            try:
                return provider(text, target_language, timeout)
            except (RuntimeError, TimeoutError, urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError):
                continue
    return text


@lru_cache(maxsize=4096)
def translate_text(text: str, target_language: str) -> str:
    text = compact_text(text)
    if target_language == "it":
        return text
    if not text:
        return text
    chunks = split_translation_units(text)
    translated = [translate_compact_once(chunk, target_language) for chunk in chunks]
    return compact_text(" ".join(translated))


@lru_cache(maxsize=2048)
def translate_lines(text: str, target_language: str) -> str:
    if target_language == "it" or not text.strip():
        return text
    translated_lines = []
    for line in strip_lines_for_translation(text):
        if not line.strip():
            translated_lines.append("")
        else:
            translated_lines.append(translate_text(line.strip(), target_language))
    return "\n".join(translated_lines).strip()


def strip_lines_for_translation(text: str) -> list[str]:
    text = re.sub(r"\r\n?|\t", lambda match: "\n" if match.group(0).startswith("\r") else " ", text)
    return [line.rstrip() for line in text.splitlines()]


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
    return ensure_sentence(translate_text(summary, "en"))


def latin_chronicle(summary: str) -> str:
    return ensure_sentence(medieval_latin_style(translate_text(summary, "la")))


def build_translated_item(item: dict[str, str], category=None, source_page: str = "") -> dict[str, object]:
    from .parser import source_id_for, summarize_description, parse_published_at
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
