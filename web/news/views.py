from __future__ import annotations

from django.conf import settings
from django.db.models import Case, Count, IntegerField, Q, Value, When
from django.db import connection
from django.http import Http404, JsonResponse
from django.shortcuts import render
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
    parse_weather_observation,
)
from .models import Category, LottoDraw, NewsItem, SuperEnalottoDraw, TelevideoPageSnapshot
from .services import (
    REGION_CHOICES,
    SECTION_DEFINITIONS,
    normalize_region,
    refresh_if_stale,
    refresh_section_if_stale,
    region_slug,
    section_definition,
)


LANGUAGES = {
    "it": "Italiano",
}

_MAP_DATA = {
    "aosta": ("Valle d'Aosta", "VdA", "6.5", 108, 35, "95,25 120,22 124,40 108,43 95,38"),
    "piemonte": ("Piemonte", "PIE", "7", 132, 72, "95,38 109,45 125,50 140,55 155,62 172,82 176,102 160,115 135,112 112,98 95,85 87,62 94,48"),
    "lombardia": ("Lombardia", "LOM", "7.5", 194, 56, "140,55 165,48 185,42 207,35 228,38 240,50 235,60 228,75 215,84 195,87 178,84 160,77 145,65"),
    "altoadige": ("Alto Adige", "AA", "6.5", 260, 24, "236,12 268,8 282,18 280,35 264,42 242,38 235,24"),
    "trentino": ("Trentino", "TNT", "6.5", 256, 48, "236,38 243,38 264,42 280,38 277,55 258,62 238,55 236,46"),
    "veneto": ("Veneto", "VEN", "7.5", 270, 84, "236,60 260,58 280,65 296,82 306,96 300,105 280,108 258,102 244,92 236,78 236,68"),
    "friuli": ("Friuli V.G.", "FVG", "6.5", 325, 60, "296,38 320,30 345,34 348,56 342,80 330,96 318,94 305,78 298,62"),
    "liguria": ("Liguria", "LIG", "7", 138, 132, "105,108 120,98 140,105 155,112 165,125 168,138 155,142 138,142 120,138 110,122 105,115"),
    "emilia": ("Emilia R.", "EMR", "7.5", 215, 102, "162,75 185,68 210,72 235,78 258,82 272,98 275,115 262,122 240,128 215,125 190,118 170,105 160,92"),
    "toscana": ("Toscana", "TOS", "7.5", 185, 152, "152,118 170,112 185,118 200,125 215,132 220,148 218,168 210,180 198,182 182,175 168,168 158,148 152,130"),
    "marche": ("Marche", "MAR", "7", 268, 145, "248,118 268,112 282,118 288,130 288,148 282,162 270,168 258,165 250,152 245,138 248,125"),
    "umbria": ("Umbria", "UMB", "7", 218, 195, "200,168 220,165 232,170 238,185 236,200 228,208 218,210 208,205 200,192 198,178"),
    "lazio": ("Lazio", "LAZ", "8", 232, 230, "205,200 222,198 238,205 248,215 255,225 259,242 252,255 238,258 222,255 212,245 205,232 202,218"),
    "abruzzo": ("Abruzzo", "ABR", "7", 278, 192, "260,158 278,152 292,162 298,178 298,198 292,215 282,225 272,228 262,218 258,198 260,178"),
    "molise": ("Molise", "MOL", "6.5", 282, 242, "272,218 288,215 298,225 300,240 295,250 285,255 275,248 270,235"),
    "campania": ("Campania", "CAM", "7", 255, 278, "232,248 248,252 262,255 275,262 278,278 275,295 262,305 248,302 238,295 230,278 228,262 231,252"),
    "puglia": ("Puglia", "PUG", "7.5", 318, 262, "282,222 302,218 318,225 332,235 342,248 350,258 348,275 338,288 322,298 308,300 295,295 288,282 282,262 282,240"),
    "basilicata": ("Basilicata", "BAS", "6.5", 290, 310, "275,290 290,286 298,295 305,310 300,320 288,322 278,312 275,300"),
    "calabria": ("Calabria", "CAL", "7", 270, 342, "252,300 272,298 282,310 288,325 288,345 285,362 278,372 268,378 260,368 255,350 252,332 250,312"),
    "sicilia": ("Sicilia", "SIC", "9", 222, 412, "175,362 200,358 225,360 248,368 265,378 272,398 268,418 255,435 238,448 218,450 198,442 185,430 178,412 175,395"),
    "sardegna": ("Sardegna", "SAR", "9", 100, 358, "65,318 82,312 102,315 118,322 132,332 140,348 142,365 138,382 128,392 112,398 95,395 78,388 68,372 62,352 63,332"),
}


def get_map_regions():
    regions = []
    for slug, data in _MAP_DATA.items():
        label, label_short, font_size, cx, cy, points = data
        regions.append({
            "slug": slug,
            "label": label,
            "label_short": label_short,
            "font_size": font_size,
            "cx": cx,
            "cy": cy,
            "points": points,
            "url": reverse("news:region", kwargs={"region_slug_value": slug}),
        })
    return regions

HIDDEN_CATEGORY_CODES = {"p401", "p613", "p700", "p711"}

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
        "lede": "Notizie da Rai Televideo, archiviate automaticamente e organizzate per categoria.",
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
        "categories_title": "Categorie",
        "news_link": "Cronaca",
        "super_link": "SuperEnalotto",
        "all_categories": "Tutte",
        "search_placeholder": "Cerca in titoli, testi e categorie...",
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
        "card_ribbon": "NOTIZIA",
        "source_prefix": "Titolo originale:",
        "category_prefix": "Categoria:",
        "source_link": "Fonte Rai",
        "open_televideo": "Apri su Televideo",
        "open_archive": "Apri archivio",
        "page_label": "Pagina",
        "subpages_label": "sottopagine",
        "previous_page": "Precedenti",
        "next_page": "Successive",
        "page_status": "Pagina {page} di {pages}",
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
        "trend_label": "Andamento Jackpot e Montepremi",
        "select_date": "Seleziona data",
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
        "error_eyebrow": "Errore {code}",
        "error_404_title": "Pagina non trovata",
        "error_404_message": "La pagina che cerchi non esiste o e' stata spostata.",
        "error_500_title": "Errore del server",
        "error_500_message": "Un imprevisto ha interrotto la lettura dei dati. Riprova tra poco.",
        "updated": "Notizie aggiornate",
        "date_unavailable": "data non disponibile",
        "error_prefix": "Errore:",
        "italy_map_title": "Mappa meteo",
        "italy_map_subtitle": "Clicca una regione per il dettaglio",
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


STRUCTURED_PAGES = {
    "tv": {514, 515, 531, 532, 533},
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
    lines = snapshot.raw_text.splitlines()
    paragraphs = [line.strip() for line in lines if line.strip()]
    return {
        "page": snapshot.page,
        "subpage": snapshot.subpage,
        "label": snapshot.label,
        "title": snapshot.title,
        "content_kind": snapshot.content_kind,
        "source_url": snapshot.source_url,
        "raw_text": snapshot.raw_text,
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


def formatted_section_data(section: str, region: str = "") -> dict:
    """Build structured/formatted data for a section using the formatters."""
    source_snapshots = section_snapshots(section, region)
    source_merged = merge_snapshot_pages(source_snapshots)
    display_snapshots = [localize_snapshot_payload(snapshot) for snapshot in source_snapshots]
    display_merged = merge_snapshot_pages(display_snapshots)
    display_by_page = {snap.get("page"): snap for snap in display_merged}

    data: dict = {
        "raw": display_snapshots,
        "merged": display_merged,
        "cards": [snap for snap in display_merged if should_display_card(section, snap)],
        "standings": None,
        "results": None,
        "films": [],
        "weather_stations": [],
        "temperatures": [],
        "auditel": [],
        "lotto": None,
        "articles": [],
        "round_info": None,
    }

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


def parse_limit(value: str | None, default: int = 18) -> int:
    try:
        return min(max(int(value or default), 1), 80)
    except ValueError:
        return default


def parse_page(value: str | None) -> int:
    try:
        return max(int(value or 1), 1)
    except ValueError:
        return 1


def home(request):
    if not NewsItem.objects.exists():
        try:
            refresh_if_stale()
        except RuntimeError:
            pass
    return render(
        request,
        "news/home.html",
        {
            "language": "it",
            "languages": LANGUAGES,
            "refresh_seconds": settings.NEWS_REFRESH_SECONDS,
            "ui": UI_TEXT["it"],
            "nav_items": nav_items("home"),
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
    refresh_section_if_stale(section)
    formatted = formatted_section_data(section)
    latest = max((card["fetched_at"] for card in formatted["raw"]), default=None)
    ctx = {
        "section": {**definition, "key": section},
        "data": formatted,
        "latest": latest,
        "nav_items": nav_items("meteo"),
        "language": "it",
        "languages": LANGUAGES,
        "refresh_seconds": settings.NEWS_REFRESH_SECONDS,
        "ui": UI_TEXT["it"],
        "map_regions": get_map_regions(),
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
    selected_region = normalize_region(region_slug_value or request.GET.get("regione"))
    refresh_section_if_stale("regioni", selected_region)
    formatted = formatted_section_data("regioni", selected_region)
    latest = max((card["fetched_at"] for card in formatted["raw"]), default=None)
    regions_payload = [
        {
            "name": region,
            "slug": region_slug(region),
            "url": reverse("news:region", kwargs={"region_slug_value": region_slug(region)}),
            "active": region == selected_region,
        }
        for region in REGION_CHOICES
    ]
    return render(
        request,
        "news/regions.html",
        {
            "section": {**localized_section_definition("regioni"), "key": "regioni", "title": f"{localized_section_definition('regioni')['title']} - {selected_region}"},
            "data": formatted,
            "latest": latest,
            "regions": regions_payload,
            "selected_region": selected_region,
            "nav_items": nav_items("regioni"),
            "language": "it",
            "languages": LANGUAGES,
            "refresh_seconds": settings.NEWS_REFRESH_SECONDS,
            "ui": UI_TEXT["it"],
        },
    )


def serialized_categories(language: str = "it") -> list[dict[str, object]]:
    categories = []
    queryset = (
        Category.objects.filter(active=True)
        .exclude(code__in=HIDDEN_CATEGORY_CODES)
        .annotate(news_count=Count("items", filter=displayable_category_filter()))
        .filter(news_count__gt=0)
    )
    for category in queryset.order_by("sort_order", "name_it"):
        categories.append(
            {
                "code": category.code,
                "name": category.name_it,
                "page": category.page,
                "count": category.news_count,
            }
        )
    return categories


def news_title_for(item: NewsItem, _language: str = "it") -> str:
    return item.title_it


def news_summary_for(item: NewsItem, _language: str = "it") -> str:
    return item.summary_it


def news_api(request):
    limit = parse_limit(request.GET.get("limit"), default=12)
    page = parse_page(request.GET.get("page"))
    category_code = request.GET.get("category") or "all"
    error = ""
    try:
        refresh_if_stale()
    except RuntimeError as exc:
        error = str(exc)

    queryset = (
        NewsItem.objects.select_related("category")
        .filter(displayable_filter())
        .exclude(category__code__in=HIDDEN_CATEGORY_CODES)
    )
    if category_code != "all":
        filtered = queryset.filter(category__code=category_code)
        if filtered.exists():
            queryset = filtered
        else:
            category_code = "all"

    queryset = queryset.annotate(
        source_rank=Case(
            When(category__code="rss101", then=Value(0)),
            default=Value(1),
            output_field=IntegerField(),
        )
    ).order_by("source_rank", "-published_at", "-created_at")
    total_items = queryset.count()
    total_pages = max((total_items + limit - 1) // limit, 1)
    page = min(page, total_pages)
    start = (page - 1) * limit
    end = start + limit

    items = []
    for item in queryset[start:end]:
        category = item.category
        items.append(
            {
                "id": item.source_id,
                "title": item.title_it,
                "summary": item.summary_it,
                "source_title": item.title_it,
                "category_code": category.code if category else "",
                "category_name": category.name_it if category else "",
                "source_page": item.source_page,
                "published": item.pub_date_text,
                "published_iso": item.published_at.isoformat() if item.published_at else "",
            }
        )

    return JsonResponse(
        {
            "language": "it",
            "language_label": "Italiano",
            "generated_at": timezone.localtime().isoformat(),
            "refresh_seconds": settings.NEWS_REFRESH_SECONDS,
            "selected_category": category_code,
            "ui": UI_TEXT["it"],
            "categories": serialized_categories(),
            "pagination": {
                "page": page,
                "pages": total_pages,
                "limit": limit,
                "total": total_items,
                "has_previous": page > 1,
                "has_next": page < total_pages,
            },
            "error": error,
            "items": items,
        }
    )


def displayable_filter() -> Q:
    return ~Q(title_it__regex=r"^\d+/\d+$") & ~Q(summary_it__regex=r"^S\.?\s*S\.?$", title_it__regex=r"^\d+/\d+$")


def displayable_category_filter() -> Q:
    return (
        ~Q(items__category__code__in=HIDDEN_CATEGORY_CODES)
        & ~Q(items__title_it__regex=r"^\d+/\d+$")
        & ~Q(items__summary_it__regex=r"^S\.?\s*S\.?$", items__title_it__regex=r"^\d+/\d+$")
    )


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
    error = ""
    try:
        refresh_if_stale()
    except RuntimeError as exc:
        error = str(exc)

    draws = SuperEnalottoDraw.objects.all()
    selected = draws.filter(draw_date=selected_date).first() if selected_date else draws.first()
    dates = [{"value": draw.draw_date.isoformat(), "label": f"{draw.draw_date.isoformat()} - N.{draw.draw_number}"} for draw in draws]
    trend_draws = list(reversed(list(SuperEnalottoDraw.objects.all()[:30])))

    return JsonResponse(
        {
            "language": "it",
            "language_label": "Italiano",
            "generated_at": timezone.localtime().isoformat(),
            "refresh_seconds": settings.NEWS_REFRESH_SECONDS,
            "ui": UI_TEXT["it"],
            "error": error,
            "dates": dates,
            "selected": draw_payload(selected),
            "trend": [
                {
                    "label": f"{draw.draw_date.isoformat()} N.{draw.draw_number}",
                    "jackpot": float(draw.jackpot) if draw.jackpot is not None else None,
                    "prize_pool": float(draw.prize_pool) if draw.prize_pool is not None else None,
                }
                for draw in trend_draws
            ],
        }
    )
