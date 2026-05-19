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
