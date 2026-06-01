from __future__ import annotations

import re
from datetime import date, timedelta
from pathlib import Path

from django.conf import settings
from django.db.models import Q
from django.db import connection
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.template import TemplateDoesNotExist
from django.urls import reverse
from django.utils import timezone

from .formatters import (
    merge_snapshot_pages,
    parse_article_multipage,
    parse_auditel,
    parse_film_schedule,
    parse_lotto_results,
    parse_match_results,
    parse_round_info,
    parse_serie_a_standings,
    parse_temperatures,
    parse_tv_channel_schedule,
    parse_weather_observation,
)
from .models import LottoDraw, NewsItem, SuperEnalottoDraw, TelevideoPageSnapshot
from .map_paths import get_map_regions
from .openweather import openweather_cache_by_city
from .site_urls import public_absolute_url, public_base_url
from .weather_capitals import build_region_capital_weather, enrich_map_regions
from .services.parser import compact_text, display_snapshot_text, fix_mojibake, prose_paragraphs
from .services import (
    REGION_CHOICES,
    SECTION_DEFINITIONS,
    normalize_region,
    refresh_if_stale,
    refresh_section_if_stale,
    region_display_name,
    region_slug,
    section_definition,
)


LANGUAGES = {
    "it": "Italiano",
}

HIDDEN_CATEGORY_CODES = {"p108", "p109", "p401", "p613", "p700", "p711"}
NEWS_LIMIT_OPTIONS = (10, 25, 50, 100)
DEFAULT_NEWS_LIMIT = 25
NEWS_DUPLICATE_TITLE_PREFIX_TOKENS = 3
NEWS_DUPLICATE_TITLE_MIN_TOKENS = 4
NEWS_DUPLICATE_TITLE_MIN_OVERLAP = 0.75
NEWS_DUPLICATE_TITLE_WINDOW = timedelta(hours=48)
NEWS_DUPLICATE_TITLE_WORD_RE = re.compile(r"[^\W_]+", flags=re.UNICODE)
NEWS_DUPLICATE_TITLE_STOPWORDS = {
    "a",
    "ad",
    "agli",
    "ai",
    "al",
    "all",
    "alla",
    "alle",
    "allo",
    "con",
    "da",
    "dal",
    "dall",
    "dalla",
    "dalle",
    "dallo",
    "de",
    "dei",
    "del",
    "dell",
    "della",
    "delle",
    "degli",
    "di",
    "e",
    "ed",
    "fra",
    "gli",
    "i",
    "il",
    "in",
    "l",
    "la",
    "le",
    "lo",
    "nei",
    "nel",
    "nell",
    "nella",
    "nelle",
    "nello",
    "o",
    "od",
    "per",
    "su",
    "sul",
    "sull",
    "sulla",
    "sulle",
    "sullo",
    "tra",
    "un",
    "una",
    "uno",
}

NAVIGATION = (
    ("home", "nav_home", "news:home"),
    ("tv", "nav_tv", "news:tv"),
    ("cultura", "nav_culture", "news:culture"),
    ("ambiente", "nav_environment", "news:environment"),
    ("lavoro", "nav_work", "news:work"),
    ("sport", "nav_sport", "news:sport"),
    ("meteo", "nav_weather", "news:weather"),
    ("viaggi", "nav_travel", "news:travel"),
    ("giochi", "nav_games", "news:games"),
    ("regioni", "nav_regions", "news:regions"),
)

UI_TEXT = {
    "it": {
        "html_lang": "it",
        "site_name": "Televideo News",
        "eyebrow": "Rai Televideo RSS 101 e pagina 104",
        "title": "Televideo News",
        "lede": "Notizie da Rai Televideo, archiviate automaticamente e ordinate per giorno.",
        "nav_home": "Cronaca",
        "nav_tv": "TV",
        "nav_culture": "Cultura",
        "nav_environment": "Ambiente",
        "nav_work": "Lavoro",
        "nav_sport": "Sport",
        "nav_weather": "Meteo",
        "nav_travel": "Viaggi",
        "nav_games": "Giochi",
        "nav_regions": "Regioni",
        "language_nav_label": "Lingua",
        "date_filter_title": "Archivio per giorno",
        "date_filter_label": "Scegli una data",
        "date_filter_all": "Tutti i giorni",
        "news_link": "Cronaca",
        "super_link": "SuperEnalotto",
        "all_categories": "Tutte",
        "search_placeholder": "Cerca in titoli e testi...",
        "clear_search": "Cancella",
        "status_label": "Stato",
        "loading": "Carico notizie...",
        "last_reading": "Ultima lettura",
        "waiting": "in attesa",
        "source_label": "Fonte",
        "data_provider": "Rai Televideo",
        "last_update_label": "Ultimo aggiornamento",
        "empty_title": "Nessuna notizia",
        "empty_message": "Il feed Rai non ha risposto o il database non e' stato popolato.",
        "section_empty_title": "Nessun contenuto",
        "section_empty_message": "La sezione non ha ancora risposto o la cache non e' stata popolata.",
        "load_error_title": "Errore caricamento",
        "unknown_error": "Errore sconosciuto",
        "timeout_error": "Timeout: server non risponde. Riprovo...",
        "no_search_results_title": "Nessun risultato",
        "no_search_results_message": "Nessuna notizia contiene \"{query}\".",
        "no_date_results_title": "Nessuna notizia in questa data",
        "no_date_results_message": "Non ci sono notizie archiviate per il giorno selezionato.",
        "searching_status": "Cerco nell'archivio...",
        "card_ribbon": "NOTIZIA",
        "source_prefix": "Titolo originale:",
        "category_prefix": "Categoria:",
        "source_link": "Fonte Rai",
        "stale_label": "Dati da verificare",
        "stale_message": "Questa sezione non riceve aggiornamenti recenti: mostro l'ultima copia salvata.",
        "noscript_title": "Ultime notizie disponibili",
        "noscript_message": "JavaScript e' disattivato: mostro un estratto statico delle ultime notizie salvate.",
        "open_televideo": "Apri su Televideo",
        "open_archive": "Apri archivio",
        "page_label": "Pagina",
        "subpages_label": "sottopagine",
        "previous_page": "Precedenti",
        "next_page": "Successive",
        "page_status": "Pagina {page} di {pages}",
        "news_limit_label": "Notizie per pagina",
        "super_title": "Archivio SuperEnalotto",
        "super_lede": "Ultima combinazione dalla pagina 696 di Rai Televideo, salvata nello storico.",
        "draw_label": "Concorso",
        "draw_date_label": "Data estrazione",
        "numbers_label": "Combinazione vincente",
        "jolly_label": "Numero Jolly",
        "superstar_label": "Numero SuperStar",
        "jackpot_label": "Jackpot",
        "prize_pool_label": "Montepremi",
        "history_label": "Storico",
        "select_year": "Seleziona anno",
        "draw_number_label": "N.",
        "draw_date_label_short": "Data",
        "numbers_label_short": "Numeri",
        "select_date": "Seleziona concorso",
        "no_draws": "Nessuna estrazione salvata.",
        "super_latest_title": "Ultima estrazione",
        "latest_news": "Ultime notizie",
        "archive_super": "Archivio SuperEnalotto",
        "lotto_title": "Lotto",
        "extraction_date_label": "Estrazione del",
        "film_schedule_title": "Film in programmazione",
        "auditel_title": "Dati Auditel",
        "channel_program_label": "Canale/Programma",
        "share_label": "Share %",
        "viewers_label": "Spettatori",
        "director_prefix": "di",
        "cast_prefix": "con",
        "standings_title": "Classifica Serie A",
        "latest_results_title": "Ultimi risultati",
        "position_label": "#",
        "team_label": "Squadra",
        "points_label": "Pt",
        "wins_label": "V",
        "draws_label": "P",
        "losses_label": "S",
        "goals_for_label": "GF",
        "goals_against_label": "GS",
        "wind_label": "Vento",
        "visibility_label": "Visibilita",
        "region_select_label": "Seleziona regione",
        "footer_prefix": "Televideo News",
        "footer_license": "Licenza MIT",
        "footer_data_prefix": "Dati da",
        "back_home": "Torna alla cronaca",
        "skip_to_content": "Vai al contenuto",
        "nav_label": "Navigazione principale",
        "error_eyebrow": "Errore {code}",
        "error_404_title": "Pagina non trovata",
        "error_404_message": "La pagina che cerchi non esiste o e' stata spostata.",
        "error_500_title": "Errore del server",
        "error_500_message": "Un imprevisto ha interrotto la lettura dei dati. Riprova tra poco.",
        "updated": "Notizie aggiornate",
        "date_unavailable": "data non disponibile",
        "error_prefix": "Errore:",
        "italy_map_title": "Mappa meteo",
        "italy_map_subtitle": "Sorvola una regione per il meteo, clicca per il dettaglio",
        "italy_map_label": "Mappa interattiva dell'Italia",
    },
}


def normalize_language(_value: str | None = None) -> str:
    return "it"


def ui_for(_language: str = "it") -> dict[str, str]:
    return UI_TEXT["it"]


SECTION_TEXT = {
    "it": {
        "tv": ("Guida TV", "Programmi TV, prima serata, film del giorno, RaiPlay, Rai Sport, radio e dati Auditel."),
        "cultura": ("Cultura, Libri, Cinema e Teatro", "Recensioni, libri, film, teatro, concerti, eventi e mostre."),
        "ambiente": ("Ambiente, Scienza e Salute", "Energie rinnovabili, sostenibilita, agenda verde, ricerca, scienza, salute."),
        "lavoro": ("Lavoro e Concorsi", "Concorsi, Gazzetta Ufficiale, sicurezza sul lavoro, formazione ed eventi occupazionali."),
        "sport": ("Sport e Risultati", "Risultati, classifiche, calendari, club di Serie A e B, altri sport e brevi sportive."),
        "meteo": ("Meteo, Mari e Venti", "Previsioni per versanti, temperature, aeroporti, mari, venti e sicurezza in mare."),
        "viaggi": ("Viaggi, Turismo e Sicurezza", "Avvisi per viaggiare sicuri, itinerari, FAI, Touring Club, borghi e info utili."),
        "giochi": ("Giochi e Estrazioni", "SuperEnalotto, Lotto e archivio delle ultime estrazioni salvate nel database."),
        "regioni": ("Televideo Regionale", "Notizie, eventi, cinema, teatri, gusto, viaggi, societa e servizi dalle pagine regionali Rai."),
    },
}


TV_CHANNEL_PAGES = {518, 519, 520, 521, 522, 523, 524, 525, 526, 527}


STRUCTURED_PAGES = {
    "tv": {514, 515, 531, 532, 533, *TV_CHANNEL_PAGES},
    "sport": {202, 203},
    "meteo": {702, 703, 704, 705, 706, 707, 708, 709, 711, 712},
    "giochi": {691, 692, 696},
}


def localize_text(text: str, _language: str = "it", *, multiline: bool = False) -> str:
    return text


def localized_section_definition(section: str, _language: str = "it") -> dict[str, object]:
    definition = section_definition(section).copy()
    title, lede = SECTION_TEXT["it"].get(section, (definition["title"], definition["lede"]))
    definition["title"] = title
    definition["lede"] = lede
    return definition


def nav_items(active: str, _language: str = "it") -> list[dict[str, object]]:
    ui = UI_TEXT["it"]
    return [
        {"key": key, "label": ui[label_key], "url": reverse(route), "active": key == active}
        for key, label_key, route in NAVIGATION
    ]


def snapshot_payload(snapshot: TelevideoPageSnapshot) -> dict[str, object]:
    raw_text = display_snapshot_text(snapshot.raw_text)
    paragraphs = prose_paragraphs(snapshot.raw_text)
    return {
        "page": snapshot.page,
        "subpage": snapshot.subpage,
        "label": fix_mojibake(snapshot.label),
        "title": fix_mojibake(snapshot.title),
        "content_kind": snapshot.content_kind,
        "source_url": snapshot.source_url,
        "raw_text": raw_text,
        "paragraphs": paragraphs,
        "fetched_at": snapshot.fetched_at,
    }


def localize_snapshot_payload(snapshot: dict[str, object], _language: str = "it") -> dict[str, object]:
    return snapshot.copy()


def section_snapshots(section: str, region: str = "") -> list[dict[str, object]]:
    queryset = TelevideoPageSnapshot.objects.filter(section=section, region=region).order_by(
        "sort_order",
        "page",
        "subpage",
    )
    return [snapshot_payload(snapshot) for snapshot in queryset]


def should_display_card(section: str, snap: dict[str, object]) -> bool:
    page = snap.get("page")
    if page in STRUCTURED_PAGES.get(section, set()):
        return False
    if section == "cultura" and snap.get("content_kind") == "article" and len(snap.get("subpages", [])) > 1:
        return False
    return True


def localize_film(film: dict, _language: str = "it") -> dict:
    return film.copy()


def localize_weather_station(station: dict, _language: str = "it") -> dict:
    return station.copy()


def localize_auditel_row(row: dict, _language: str = "it") -> dict:
    return row.copy()


def localize_article(article: dict, _language: str = "it") -> dict:
    return article.copy()


def empty_formatted_section_data() -> dict:
    return {
        "raw": [],
        "merged": [],
        "cards": [],
        "standings": None,
        "results": None,
        "films": [],
        "weather_stations": [],
        "temperatures": [],
        "auditel": [],
        "lotto": None,
        "articles": [],
        "round_info": None,
        "tv_channels": [],
    }


def formatted_section_data(section: str, region: str = "") -> dict:
    """Build structured/formatted data for a section using the formatters."""
    source_snapshots = section_snapshots(section, region)
    source_merged = merge_snapshot_pages(source_snapshots)
    display_snapshots = [localize_snapshot_payload(snapshot) for snapshot in source_snapshots]
    display_merged = merge_snapshot_pages(display_snapshots)
    display_by_page = {snap.get("page"): snap for snap in display_merged}

    data: dict = empty_formatted_section_data()
    data["raw"] = display_snapshots
    data["merged"] = display_merged
    data["cards"] = [snap for snap in display_merged if should_display_card(section, snap)]

    for snap in source_merged:
        raw = snap.get("all_text", snap.get("raw_text", ""))
        page = snap.get("page")
        display_snap = display_by_page.get(page, snap)

        # Serie A standings
        if section == "sport" and page == 203:
            s = parse_serie_a_standings(raw)
            if s:
                data["standings"] = s

        # Match results
        if section == "sport" and page == 202:
            r = parse_match_results(raw)
            if r:
                data["results"] = r
            ri = parse_round_info(raw)
            if ri:
                data["round_info"] = localize_text(ri)

        # Film schedules
        if section == "tv" and page in (514, 515):
            films = parse_film_schedule(raw)
            if films:
                data["films"].extend(localize_film(film) for film in films)

        # TV channel schedules
        if section == "tv" and page in TV_CHANNEL_PAGES:
            programs = parse_tv_channel_schedule(raw)
            if programs:
                data["tv_channels"].append({
                    "page": page,
                    "label": display_snap.get("label", ""),
                    "programs": programs,
                })

        # Weather observations
        if section == "meteo" and page in (702, 703, 704, 705, 706, 707, 708, 709):
            stations = parse_weather_observation(raw)
            if stations:
                data["weather_stations"].append({
                    "page": page,
                    "label": display_snap.get("label", ""),
                    "stations": [localize_weather_station(station) for station in stations],
                })

        # Temperatures
        if section == "meteo" and page in (711, 712):
            temps = parse_temperatures(raw)
            if temps:
                data["temperatures"].append({
                    "page": page,
                    "label": display_snap.get("label", ""),
                    "cities": temps,
                })

        # Auditel
        if section == "tv" and page in (531, 532, 533):
            aud = parse_auditel(raw)
            if aud:
                data["auditel"].append({
                    "page": page,
                    "label": display_snap.get("label", ""),
                    "rows": [localize_auditel_row(row) for row in aud],
                })

        # Lotto
        if section == "giochi" and page in (691, 692):
            lotto = parse_lotto_results(raw)
            if lotto:
                lotto["page"] = page
                lotto["label"] = display_snap.get("label", "")
                data["lotto"] = lotto

        # Multi-page articles (cultura section)
        if snap.get("content_kind") == "article":
            pages_for_article = [s for s in source_snapshots if s["page"] == page]
            if len(pages_for_article) > 1:
                article = parse_article_multipage(pages_for_article)
                if article:
                    article["page"] = page
                    article["label"] = snap.get("label", "")
                    article["title"] = article.get("title") or snap.get("title", "")
                    data["articles"].append(localize_article(article))

    return data


def meteo_map_context() -> dict[str, object]:
    if settings.OPENWEATHER_API_KEY:
        meteo_data = empty_formatted_section_data()
        openweather_data = openweather_cache_by_city()
        region_weather = build_region_capital_weather(meteo_data, openweather_data, openweather_only=True)
        latest = max((item.get("source_at") for item in openweather_data.values() if item.get("source_at")), default=None)
    else:
        refresh_section_if_stale("meteo")
        meteo_data = formatted_section_data("meteo")
        region_weather = build_region_capital_weather(meteo_data)
        latest = max((card["fetched_at"] for card in meteo_data["raw"]), default=None)
    return {
        "meteo_data": meteo_data,
        "meteo_latest": latest,
        "region_weather": region_weather,
        "map_regions": enrich_map_regions(get_map_regions(), region_weather),
    }


def parse_limit(value: str | None, default: int = DEFAULT_NEWS_LIMIT) -> int:
    try:
        parsed = int(value or default)
    except ValueError:
        return default
    return parsed if parsed in NEWS_LIMIT_OPTIONS else default


def parse_page(value: str | None) -> int:
    try:
        return max(int(value or 1), 1)
    except ValueError:
        return 1


def is_stale_timestamp(value, seconds: int) -> bool:
    if not value:
        return False
    threshold = max(seconds * 6, 7200)
    return (timezone.now() - value).total_seconds() > threshold


def base_news_queryset():
    return NewsItem.objects.select_related("category").filter(displayable_filter()).exclude(category__code__in=HIDDEN_CATEGORY_CODES)


def apply_news_filters(queryset, search_query: str):
    if search_query:
        queryset = queryset.filter(
            Q(title_it__icontains=search_query)
            | Q(summary_it__icontains=search_query)
            | Q(category__name_it__icontains=search_query)
            | Q(source_page__icontains=search_query)
        ).distinct()

    return queryset


def ordered_news_queryset(queryset):
    return queryset.order_by("-published_at", "-created_at")


def normalized_news_text(value: str) -> str:
    return compact_text(value or "").casefold()


def normalized_news_title_tokens(value: str) -> tuple[str, ...]:
    tokens = NEWS_DUPLICATE_TITLE_WORD_RE.findall(normalized_news_text(value))
    return tuple(
        token
        for token in tokens
        if token not in NEWS_DUPLICATE_TITLE_STOPWORDS and (len(token) > 1 or token.isdigit())
    )


def dedupe_news_key(item: NewsItem) -> str:
    title = normalized_news_text(item.title_it)
    summary = normalized_news_text(item.summary_it)
    return "\0".join(part for part in (title, summary) if part) or item.source_id


def duplicate_title_prefix(tokens: tuple[str, ...]) -> tuple[str, ...]:
    if len(tokens) < NEWS_DUPLICATE_TITLE_MIN_TOKENS:
        return ()
    return tokens[:NEWS_DUPLICATE_TITLE_PREFIX_TOKENS]


def similar_news_titles(first_tokens: tuple[str, ...], second_tokens: tuple[str, ...]) -> bool:
    first_prefix = duplicate_title_prefix(first_tokens)
    if not first_prefix or first_prefix != duplicate_title_prefix(second_tokens):
        return False
    first_set = set(first_tokens)
    second_set = set(second_tokens)
    common_tokens = len(first_set & second_set)
    return common_tokens / max(len(first_set), len(second_set)) >= NEWS_DUPLICATE_TITLE_MIN_OVERLAP


def news_items_close_in_time(first: NewsItem, second: NewsItem) -> bool:
    if not first.published_at or not second.published_at:
        return True
    return abs(first.published_at - second.published_at) <= NEWS_DUPLICATE_TITLE_WINDOW


def deduplicated_news_items(queryset) -> list[NewsItem]:
    items: list[NewsItem] = []
    seen: set[str] = set()
    seen_similar_titles: dict[tuple[str, ...], list[tuple[NewsItem, tuple[str, ...]]]] = {}
    for item in queryset:
        key = dedupe_news_key(item)
        if key in seen:
            continue
        title_tokens = normalized_news_title_tokens(item.title_it)
        title_prefix = duplicate_title_prefix(title_tokens)
        if title_prefix:
            candidates = seen_similar_titles.get(title_prefix, [])
            if any(
                similar_news_titles(title_tokens, candidate_tokens) and news_items_close_in_time(item, candidate)
                for candidate, candidate_tokens in candidates
            ):
                continue
        seen.add(key)
        items.append(item)
        if title_prefix:
            seen_similar_titles.setdefault(title_prefix, []).append((item, title_tokens))
    return items


def parse_news_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def news_item_local_date(item: NewsItem) -> date | None:
    if not item.published_at:
        return None
    return timezone.localtime(item.published_at).date()


def news_date_label(value: date | None) -> str:
    if value is None:
        return UI_TEXT["it"]["date_unavailable"]
    today = timezone.localdate()
    if value == today:
        return "Oggi"
    if value == today - timedelta(days=1):
        return "Ieri"
    return value.strftime("%d/%m/%Y")


def news_date_options(items: list[NewsItem]) -> list[dict[str, object]]:
    counts: dict[date, int] = {}
    for item in items:
        item_date = news_item_local_date(item)
        if item_date is None:
            continue
        counts[item_date] = counts.get(item_date, 0) + 1
    return [
        {"value": item_date.isoformat(), "label": news_date_label(item_date), "count": count}
        for item_date, count in sorted(counts.items(), reverse=True)
    ]


def serialized_news_item(item: NewsItem) -> dict[str, object]:
    category = item.category
    item_date = news_item_local_date(item)
    return {
        "id": item.source_id,
        "title": item.title_it,
        "summary": item.summary_for("it"),
        "source_title": item.title_it,
        "category_code": category.code if category else "",
        "category_name": category.name_it if category else "",
        "source_page": item.source_page,
        "published": item.pub_date_text,
        "published_display": timezone.localtime(item.published_at).strftime("%d/%m/%Y %H:%M") if item.published_at else item.pub_date_text,
        "published_date": item_date.isoformat() if item_date else "",
        "published_date_label": news_date_label(item_date),
        "published_iso": item.published_at.isoformat() if item.published_at else "",
    }


def grouped_news_items(items: list[dict[str, object]]) -> list[dict[str, object]]:
    groups: list[dict[str, object]] = []
    groups_by_date: dict[str, dict[str, object]] = {}
    for item in items:
        key = str(item.get("published_date") or "unknown")
        if key not in groups_by_date:
            group = {
                "key": key,
                "label": item.get("published_date_label") or UI_TEXT["it"]["date_unavailable"],
                "items": [],
            }
            groups_by_date[key] = group
            groups.append(group)
        groups_by_date[key]["items"].append(item)
    return groups


def news_listing(search_query: str, page: int, limit: int, selected_date: date | None = None) -> dict[str, object]:
    queryset = apply_news_filters(base_news_queryset(), search_query)
    queryset = ordered_news_queryset(queryset)
    all_items = deduplicated_news_items(queryset)
    available_dates = news_date_options(all_items)
    items = [item for item in all_items if news_item_local_date(item) == selected_date] if selected_date else all_items
    total_items = len(items)
    total_pages = max((total_items + limit - 1) // limit, 1)
    page = min(page, total_pages)
    start = (page - 1) * limit
    end = start + limit
    serialized_items = [serialized_news_item(item) for item in items[start:end]]
    date_values = [str(option["value"]) for option in available_dates]
    return {
        "available_dates": available_dates,
        "date_max": date_values[0] if date_values else "",
        "date_min": date_values[-1] if date_values else "",
        "selected_date": selected_date.isoformat() if selected_date else "",
        "search_query": search_query,
        "pagination": {
            "page": page,
            "pages": total_pages,
            "limit": limit,
            "total": total_items,
            "has_previous": page > 1,
            "has_next": page < total_pages,
        },
        "items": serialized_items,
        "groups": grouped_news_items(serialized_items),
    }


def initial_home_listing(request) -> dict[str, object]:
    search_query = (request.GET.get("q") or "").strip()[:120]
    page = parse_page(request.GET.get("page"))
    limit = parse_limit(request.GET.get("limit"))
    selected_date = parse_news_date(request.GET.get("date"))
    return news_listing(search_query, page, limit=limit, selected_date=selected_date)


def home(request):
    if not NewsItem.objects.exists():
        try:
            refresh_if_stale()
        except RuntimeError:
            pass
    listing = initial_home_listing(request)
    return render(
        request,
        "news/home.html",
        {
            "language": "it",
            "languages": LANGUAGES,
            "refresh_seconds": settings.NEWS_REFRESH_SECONDS,
            "default_news_limit": DEFAULT_NEWS_LIMIT,
            "news_limit_options": NEWS_LIMIT_OPTIONS,
            "ui": UI_TEXT["it"],
            "nav_items": nav_items("home"),
            "fallback_groups": listing["groups"],
            "fallback_pagination": listing["pagination"],
            "fallback_page_status": UI_TEXT["it"]["page_status"].replace("{page}", str(listing["pagination"]["page"])).replace("{pages}", str(listing["pagination"]["pages"])),
            "initial_search": listing["search_query"],
            "initial_date": listing["selected_date"],
            "initial_limit": listing["pagination"]["limit"],
            "date_min": listing["date_min"],
            "date_max": listing["date_max"],
        },
    )


def superenalotto(request):
    if not SuperEnalottoDraw.objects.exists():
        try:
            refresh_if_stale()
        except RuntimeError:
            pass
    return render(
        request,
        "news/superenalotto.html",
        {
            "language": "it",
            "languages": LANGUAGES,
            "refresh_seconds": settings.NEWS_REFRESH_SECONDS,
            "ui": UI_TEXT["it"],
            "nav_items": nav_items("giochi"),
        },
    )


def televideo_section(request, section: str, active: str):
    if section not in SECTION_DEFINITIONS:
        raise Http404("Sezione non trovata")
    definition = localized_section_definition(section)
    refresh_section_if_stale(section)
    formatted = formatted_section_data(section)
    latest = max((card["fetched_at"] for card in formatted["raw"]), default=None)
    ctx = {
        "section": {**definition, "key": section},
        "data": formatted,
        "latest": latest,
        "stale": is_stale_timestamp(latest, settings.TELETEXT_SECTION_REFRESH_SECONDS),
        "nav_items": nav_items(active),
        "language": "it",
        "languages": LANGUAGES,
        "refresh_seconds": settings.NEWS_REFRESH_SECONDS,
        "ui": UI_TEXT["it"],
    }
    specific = f"news/section_{section}.html"
    try:
        from django.template.loader import get_template
        get_template(specific)
        return render(request, specific, ctx)
    except TemplateDoesNotExist:
        return render(request, "news/section.html", ctx)


def tv(request):
    return televideo_section(request, "tv", "tv")


def culture(request):
    return televideo_section(request, "cultura", "cultura")


def environment(request):
    return televideo_section(request, "ambiente", "ambiente")


def work(request):
    return televideo_section(request, "lavoro", "lavoro")


def sport(request):
    return televideo_section(request, "sport", "sport")


def weather(request):
    section = "meteo"
    if section not in SECTION_DEFINITIONS:
        raise Http404("Sezione non trovata")
    definition = localized_section_definition(section)
    meteo_context = meteo_map_context()
    formatted = meteo_context["meteo_data"]
    latest = max((card["fetched_at"] for card in formatted["raw"]), default=None)
    ctx = {
        "section": {**definition, "key": section},
        "data": formatted,
        "latest": latest,
        "stale": is_stale_timestamp(latest, settings.METEO_SECTION_REFRESH_SECONDS),
        "nav_items": nav_items("meteo"),
        "language": "it",
        "languages": LANGUAGES,
        "refresh_seconds": settings.NEWS_REFRESH_SECONDS,
        "ui": UI_TEXT["it"],
        "map_regions": meteo_context["map_regions"],
    }
    return render(request, "news/section_meteo.html", ctx)


def travel(request):
    return televideo_section(request, "viaggi", "viaggi")


def games(request):
    refresh_section_if_stale("giochi")
    formatted = formatted_section_data("giochi")
    latest = max((card["fetched_at"] for card in formatted["raw"]), default=None)
    latest_superenalotto = SuperEnalottoDraw.objects.first()
    latest_lotto = LottoDraw.objects.first()
    return render(
        request,
        "news/section_giochi.html",
        {
            "section": {**localized_section_definition("giochi"), "key": "giochi"},
            "data": formatted,
            "latest": latest,
            "stale": is_stale_timestamp(latest, settings.TELETEXT_SECTION_REFRESH_SECONDS),
            "latest_superenalotto": latest_superenalotto,
            "latest_lotto": latest_lotto,
            "nav_items": nav_items("giochi"),
            "language": "it",
            "languages": LANGUAGES,
            "refresh_seconds": settings.NEWS_REFRESH_SECONDS,
            "ui": UI_TEXT["it"],
        },
    )


def regions(request, region_slug_value: str | None = None):
    requested_region = region_slug_value or request.GET.get("regione")
    regions_payload = [
        {
            "name": region_display_name(region),
            "slug": region_slug(region),
            "url": reverse("news:region", kwargs={"region_slug_value": region_slug(region)}),
            "active": False,
        }
        for region in REGION_CHOICES
    ]

    if not requested_region:
        meteo_context = meteo_map_context()
        definition = localized_section_definition("regioni")
        return render(
            request,
            "news/regions.html",
            {
                "section": {**definition, "key": "regioni"},
                "data": {"cards": []},
                "latest": meteo_context["meteo_latest"],
                "stale": is_stale_timestamp(meteo_context["meteo_latest"], settings.METEO_SECTION_REFRESH_SECONDS),
                "regions": regions_payload,
                "selected_region": "",
                "selected_region_display": "",
                "capital_weather": [],
                "is_region_landing": True,
                "map_regions": meteo_context["map_regions"],
                "nav_items": nav_items("regioni"),
                "language": "it",
                "languages": LANGUAGES,
                "refresh_seconds": settings.NEWS_REFRESH_SECONDS,
                "ui": UI_TEXT["it"],
            },
        )

    selected_region = normalize_region(requested_region)
    canonical_slug = region_slug(selected_region)
    # Redirect old Trentino/Alto Adige slugs to the canonical one
    if region_slug_value and region_slug_value != canonical_slug:
        return redirect("news:region", region_slug_value=canonical_slug, permanent=True)
    meteo_context = meteo_map_context()
    refresh_section_if_stale("regioni", selected_region)
    formatted = formatted_section_data("regioni", selected_region)
    latest = max((card["fetched_at"] for card in formatted["raw"]), default=None)
    selected_region_display = region_display_name(selected_region)
    for region in regions_payload:
        region["active"] = region["slug"] == canonical_slug
    return render(
        request,
        "news/regions.html",
        {
            "section": {**localized_section_definition("regioni"), "key": "regioni", "title": f"{localized_section_definition('regioni')['title']} - {selected_region_display}"},
            "data": formatted,
            "latest": latest,
            "stale": is_stale_timestamp(latest, settings.TELETEXT_SECTION_REFRESH_SECONDS),
            "regions": regions_payload,
            "selected_region": selected_region,
            "selected_region_display": selected_region_display,
            "capital_weather": meteo_context["region_weather"].get(canonical_slug, []),
            "is_region_landing": False,
            "map_regions": meteo_context["map_regions"],
            "nav_items": nav_items("regioni"),
            "language": "it",
            "languages": LANGUAGES,
            "refresh_seconds": settings.NEWS_REFRESH_SECONDS,
            "ui": UI_TEXT["it"],
        },
    )


def news_title_for(item: NewsItem, _language: str = "it") -> str:
    return item.title_it


def news_summary_for(item: NewsItem, _language: str = "it") -> str:
    return item.summary_for("it")


def news_api(request):
    limit = parse_limit(request.GET.get("limit"))
    page = parse_page(request.GET.get("page"))
    search_query = (request.GET.get("q") or "").strip()[:120]
    selected_date = parse_news_date(request.GET.get("date"))
    error = ""
    try:
        refresh_if_stale()
    except RuntimeError as exc:
        error = str(exc)
    listing = news_listing(search_query, page, limit, selected_date=selected_date)

    return JsonResponse(
        {
            "language": "it",
            "language_label": "Italiano",
            "generated_at": timezone.localtime().isoformat(),
            "refresh_seconds": settings.NEWS_REFRESH_SECONDS,
            "available_dates": listing["available_dates"],
            "date_max": listing["date_max"],
            "date_min": listing["date_min"],
            "selected_date": listing["selected_date"],
            "search_query": listing["search_query"],
            "ui": UI_TEXT["it"],
            "pagination": listing["pagination"],
            "error": error,
            "items": listing["items"],
        }
    )


def displayable_filter() -> Q:
    return ~Q(title_it__regex=r"^\d+/\d+$") & ~Q(summary_it__regex=r"^S\.?\s*S\.?$", title_it__regex=r"^\d+/\d+$")


def page_not_found(request, exception=None):
    ui = UI_TEXT["it"]
    return render(
        request,
        "news/error.html",
        {
            "code": 404,
            "eyebrow": ui["error_eyebrow"].replace("{code}", "404"),
            "title": ui["error_404_title"],
            "message": ui["error_404_message"],
            "language": "it",
            "languages": LANGUAGES,
            "ui": ui,
            "nav_items": nav_items("home"),
        },
        status=404,
    )


def server_error(request):
    ui = UI_TEXT["it"]
    return render(
        request,
        "news/error.html",
        {
            "code": 500,
            "eyebrow": ui["error_eyebrow"].replace("{code}", "500"),
            "title": ui["error_500_title"],
            "message": ui["error_500_message"],
            "language": "it",
            "languages": LANGUAGES,
            "ui": ui,
            "nav_items": nav_items("home"),
        },
        status=500,
    )


def healthcheck(request):
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
        cursor.fetchone()
    return JsonResponse({"status": "ok", "time": timezone.localtime().isoformat()})


def robots_txt(request):
    sitemap_url = public_absolute_url(request, reverse("news:sitemap"))
    body = f"User-agent: *\nAllow: /\nSitemap: {sitemap_url}\n"
    return HttpResponse(body, content_type="text/plain; charset=utf-8")


def sitemap_xml(request):
    route_names = [
        "home",
        "tv",
        "culture",
        "environment",
        "work",
        "sport",
        "weather",
        "travel",
        "games",
        "regions",
        "superenalotto",
    ]
    urls = [public_absolute_url(request, reverse(f"news:{name}")) for name in route_names]
    urls.append(public_absolute_url(request, reverse("news:atom_feed")))
    urls.extend(
        public_absolute_url(request, reverse("news:region", kwargs={"region_slug_value": region_slug(region)}))
        for region in REGION_CHOICES
    )
    today = timezone.localdate().isoformat()
    entries = "\n".join(
        f"  <url><loc>{url}</loc><lastmod>{today}</lastmod><changefreq>hourly</changefreq></url>"
        for url in urls
    )
    body = "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n<urlset xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\">\n" + entries + "\n</urlset>\n"
    return HttpResponse(body, content_type="application/xml; charset=utf-8")


def decimal_payload(value):
    if value is None:
        return {"text": "", "value": None}
    return {"text": f"EUR {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."), "value": float(value)}


def draw_payload(draw: SuperEnalottoDraw | None) -> dict[str, object] | None:
    if draw is None:
        return None
    return {
        "draw_number": draw.draw_number,
        "draw_date": draw.draw_date.isoformat(),
        "winning_numbers": draw.winning_numbers,
        "jolly_number": draw.jolly_number,
        "superstar_number": draw.superstar_number,
        "jackpot": decimal_payload(draw.jackpot),
        "prize_pool": decimal_payload(draw.prize_pool),
    }


def superenalotto_api(request):
    selected_date = request.GET.get("date") or ""
    selected_year = request.GET.get("year") or ""
    error = ""
    try:
        refresh_if_stale()
    except RuntimeError as exc:
        error = str(exc)

    years_qs = (
        SuperEnalottoDraw.objects
        .dates("draw_date", "year")
        .distinct()
    )
    years = sorted([d.year for d in years_qs])

    selected = None
    if selected_date:
        selected = SuperEnalottoDraw.objects.filter(draw_date=selected_date).first()
    if selected:
        selected_year = str(selected.draw_date.year)
    elif not selected_year:
        selected_year = str(years[-1]) if years else ""

    year_int = int(selected_year) if selected_year else None
    draws_qs = SuperEnalottoDraw.objects.filter(draw_date__year=year_int) if year_int else SuperEnalottoDraw.objects.none()

    return JsonResponse(
        {
            "language": "it",
            "language_label": "Italiano",
            "generated_at": timezone.localtime().isoformat(),
            "refresh_seconds": settings.NEWS_REFRESH_SECONDS,
            "ui": UI_TEXT["it"],
            "error": error,
            "years": years,
            "selected_year": selected_year,
            "selected_date": selected.draw_date.isoformat() if selected else "",
            "draws": [draw_payload(d) for d in draws_qs],
            "selected": draw_payload(selected) if selected else None,
            "draw_count": draws_qs.count(),
        }
    )


def _escape_xml(value: str) -> str:
    return value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;").replace("'", "&apos;")


def page_link_for_item(item) -> str:
    if item.source_page:
        try:
            page_num = int(item.source_page)
            if 100 <= page_num <= 999:
                return f"https://www.televideo.rai.it/televideo/pub/solotesto.jsp?pagina={page_num}"
        except ValueError:
            pass
    return ""


def atom_feed(request):
    items = NewsItem.objects.select_related("category").filter(
        displayable_filter()
    ).exclude(
        category__code__in=HIDDEN_CATEGORY_CODES
    ).order_by("-published_at", "-created_at")[:24]

    base_url = public_base_url(request)
    feed_url = public_absolute_url(request, reverse("news:atom_feed"))
    updated = timezone.now().isoformat()

    entries = []
    for item in items:
        title = item.title_it
        summary = item.summary_for("it")
        link = item.link or page_link_for_item(item)
        if not link:
            link = base_url
        iso_date = (
            item.published_at.strftime("%Y-%m-%dT%H:%M:%S%z")
            if item.published_at
            else updated
        )
        entries.append(
            f"  <entry>\n"
            f"    <title>{_escape_xml(title)}</title>\n"
            f"    <link href=\"{_escape_xml(link)}\" rel=\"alternate\"/>\n"
            f"    <id>urn:televideo:item:{item.source_id}</id>\n"
            f"    <published>{iso_date}</published>\n"
            f"    <updated>{iso_date}</updated>\n"
            f"    <summary type=\"text\">{_escape_xml(summary)}</summary>\n"
            f"  </entry>"
        )

    body = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<feed xmlns="http://www.w3.org/2005/Atom">\n'
        f"  <title>Televideo News - Ultim&apos;Ora Rai Televideo</title>\n"
        f"  <link href=\"{_escape_xml(base_url)}\" rel=\"alternate\"/>\n"
        f"  <link href=\"{_escape_xml(feed_url)}\" rel=\"self\"/>\n"
        f"  <id>{_escape_xml(base_url)}</id>\n"
        f"  <updated>{updated}</updated>\n"
        + "\n".join(entries)
        + "\n</feed>\n"
    )
    return HttpResponse(body, content_type="application/atom+xml; charset=utf-8")


def service_worker_js(request):
    sw_path = Path(__file__).resolve().parent / "static" / "news" / "sw.js"
    content = sw_path.read_text(encoding="utf-8")
    return HttpResponse(content, content_type="application/javascript; charset=utf-8")
