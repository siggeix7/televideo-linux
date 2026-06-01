from __future__ import annotations

import hashlib
import re
import threading

from django.conf import settings
from django.db import close_old_connections
from django.utils import timezone

from .constants import (
    CATEGORY_INDEX_PAGE,
    CATEGORY_LABELS,
    EXTRA_CATEGORY_PAGES,
    FLASH_NEWS_PAGES,
    LOTTO_PAGES,
    REGION_CHOICES,
    REGIONS,
    SECTION_DEFINITIONS,
    SUPERENALOTTO_PAGE,
)
from .fetcher import fetch_televideo_content, fetch_text, build_rss_urls, page_link
from .parser import (
    clean_snapshot_text,
    detail_pages_from_category,
    empty_snapshot,
    parse_article_content,
    parse_lotto_content,
    parse_rss,
    parse_superenalotto_content,
    snapshot_title,
    snapshot_total_subpages,
    source_id_for,
)
from .translator import build_translated_item

from news.models import Category, LottoDraw, NewsItem, SuperEnalottoDraw, TelevideoPageSnapshot


_REFRESH_LOCK = threading.Lock()
_SECTION_REFRESH_LOCK = threading.Lock()


def normalize_region(value: str | None) -> str:
    if not value:
        return "Lombardia"
    key = value.strip().lower().replace("_", "-").replace(" ", "-")
    if key in REGIONS:
        return REGIONS[key]
    for region in REGION_CHOICES:
        if region.lower() == value.strip().lower():
            return region
    return "Lombardia"


def region_slug(region: str) -> str:
    if region == "Trentino":
        return "trentino-alto-adige"
    return region.lower().replace(" ", "-")


def section_definition(section: str) -> dict[str, object]:
    if section == "regioni":
        from .constants import REGIONAL_SECTION
        return REGIONAL_SECTION
    if section not in SECTION_DEFINITIONS:
        raise RuntimeError("sezione Televideo non configurata")
    return SECTION_DEFINITIONS[section]


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


def update_rss_news(limit: int | None, category: Category) -> int:
    rss_text, _ = fetch_text(build_rss_urls(), settings.TRANSLATION_TIMEOUT, settings.TRANSLATION_RETRIES)
    items = parse_rss(rss_text)
    if limit:
        items = items[:limit]
    return sum(save_item(item, category=category, source_page="101") for item in items)


def update_category_news(categories: list[Category], per_category_limit: int) -> int:
    from .constants import COMPOSITE_CATEGORY_PAGES

    saved = 0
    category_pages = {category.page for category in categories if category.page}
    for category in categories:
        if not category.page or category.page == 101:
            continue
        if category.page in FLASH_NEWS_PAGES:
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


def update_superenalotto() -> int:
    content = fetch_televideo_content(SUPERENALOTTO_PAGE)
    defaults = parse_superenalotto_content(content)
    draw_number = int(defaults.pop("draw_number"))
    draw_date = defaults.pop("draw_date")
    SuperEnalottoDraw.objects.update_or_create(
        draw_number=draw_number, draw_date=draw_date, defaults=defaults,
    )
    return 1


def update_lotto() -> int:
    saved = 0
    for page in LOTTO_PAGES:
        try:
            defaults = parse_lotto_content(fetch_televideo_content(page))
        except RuntimeError:
            continue
        draw_date = defaults.pop("draw_date")
        LottoDraw.objects.update_or_create(draw_date=draw_date, defaults=defaults)
        saved += 1
    return saved


def update_section_snapshots(section: str, region: str = "") -> int:
    definition = section_definition(section)
    saved = 0
    normalized_region = normalize_region(region) if section == "regioni" else ""
    pages = definition["pages"]
    for index, spec in enumerate(pages):
        page, label, content_kind = spec
        try:
            first_content = clean_snapshot_text(fetch_televideo_content(page, region=normalized_region))
        except RuntimeError:
            continue
        if empty_snapshot(first_content):
            continue
        total_subpages = snapshot_total_subpages(first_content)
        subpages: list[tuple[str, str]] = [("01", first_content)]
        for subpage_number in range(2, total_subpages + 1):
            subpage = str(subpage_number).zfill(2)
            try:
                subpage_content = clean_snapshot_text(fetch_televideo_content(page, subpage=subpage, region=normalized_region))
            except RuntimeError:
                continue
            if not empty_snapshot(subpage_content):
                subpages.append((subpage, subpage_content))
        for subpage_index, (subpage, content) in enumerate(subpages):
            TelevideoPageSnapshot.objects.update_or_create(
                section=section, page=page, subpage=subpage, region=normalized_region,
                defaults={
                    "label": label,
                    "title": snapshot_title(content, label),
                    "content_kind": content_kind,
                    "sort_order": index * 100 + subpage_index,
                    "source_url": page_link(page, subpage=subpage, region=normalized_region),
                    "raw_text": content,
                },
            )
            saved += 1
    return saved


def update_news(limit: int | None = None, category_limit: int | None = None) -> int:
    category_limit = settings.CATEGORY_FETCH_LIMIT if category_limit is None else category_limit
    categories = sync_categories_from_page_104()
    saved = update_rss_news(limit, categories[0])
    saved += update_category_news(categories, category_limit)
    try:
        saved += update_superenalotto()
    except RuntimeError:
        pass
    saved += update_lotto()
    return saved


def refresh_if_stale() -> None:
    if getattr(settings, "RUNNING_TESTS", False):
        return
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


def refresh_section_if_stale(section: str, region: str = "") -> None:
    if getattr(settings, "RUNNING_TESTS", False):
        return
    normalized_region = normalize_region(region) if section == "regioni" else ""
    latest = (
        TelevideoPageSnapshot.objects.filter(section=section, region=normalized_region)
        .order_by("-fetched_at")
        .first()
    )
    if latest and (timezone.now() - latest.fetched_at).total_seconds() < settings.TELETEXT_SECTION_REFRESH_SECONDS:
        return
    if not _SECTION_REFRESH_LOCK.acquire(blocking=False):
        return
    thread = threading.Thread(
        target=section_refresh_worker,
        args=(section, normalized_region),
        daemon=True,
    )
    thread.start()


def section_refresh_worker(section: str, region: str) -> None:
    try:
        close_old_connections()
        update_section_snapshots(section, region)
    finally:
        close_old_connections()
        _SECTION_REFRESH_LOCK.release()


def refresh_all_sections() -> int:
    saved = 0
    sections = list(SECTION_DEFINITIONS.keys()) + ["regioni"]
    for section in sections:
        try:
            saved += update_section_snapshots(section)
        except RuntimeError:
            pass
    for region in REGION_CHOICES:
        try:
            saved += update_section_snapshots("regioni", region)
        except RuntimeError:
            pass
    return saved
