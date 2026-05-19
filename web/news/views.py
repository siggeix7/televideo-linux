from __future__ import annotations

from django.conf import settings
from django.db.models import Case, Count, IntegerField, Q, Value, When
from django.db import connection
from django.http import Http404, JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone

from .models import Category, LottoDraw, NewsItem, SuperEnalottoDraw, TelevideoPageSnapshot
from .services import (
    REGION_CHOICES,
    SECTION_DEFINITIONS,
    normalize_region,
    refresh_if_stale,
    refresh_section_if_stale,
    region_slug,
    section_definition,
    update_lotto,
    update_superenalotto,
)


LANGUAGES = {
    "la": "Latino",
    "it": "Italiano",
    "en": "English",
}

HIDDEN_CATEGORY_CODES = {"p401", "p613", "p700", "p711"}

NAVIGATION = (
    ("home", "Cronaca", "news:home"),
    ("tv", "TV", "news:tv"),
    ("cultura", "Cultura", "news:culture"),
    ("ambiente", "Ambiente", "news:environment"),
    ("lavoro", "Lavoro", "news:work"),
    ("sport", "Sport", "news:sport"),
    ("meteo", "Meteo", "news:weather"),
    ("viaggi", "Viaggi", "news:travel"),
    ("giochi", "Giochi", "news:games"),
    ("regioni", "Regioni", "news:regions"),
)

UI_TEXT = {
    "it": {
        "html_lang": "it",
        "eyebrow": "Rai Televideo RSS 101 e pagina 104",
        "title": "Televideo News",
        "lede": "Notizie reali da Rai Televideo, archiviate automaticamente e organizzate per categoria.",
        "language_nav_label": "Lingua dell'interfaccia e delle notizie",
        "categories_title": "Categorie",
        "news_link": "Cronaca",
        "super_link": "SuperEnalotto",
        "all_categories": "Tutte",
        "status_label": "Stato aggiornamento",
        "loading": "Carico le ultime notizie...",
        "last_reading": "Ultima lettura",
        "waiting": "in attesa",
        "empty_title": "Le pergamene sono ancora vuote",
        "empty_message": "Il feed Rai non ha risposto oppure il job di aggiornamento non ha ancora popolato il database.",
        "card_ribbon": "Notizia",
        "source_prefix": "Titolo originale:",
        "category_prefix": "Categoria:",
        "source_link": "Fonte Rai",
        "previous_page": "Precedenti",
        "next_page": "Successive",
        "page_status": "Pagina {page} di {pages}",
        "super_title": "Archivio SuperEnalotto",
        "super_lede": "Ultima combinazione dalla pagina 696 di Rai Televideo, salvata nello storico SQLite.",
        "draw_label": "Concorso",
        "draw_date_label": "Data estrazione",
        "numbers_label": "Combinazione vincente",
        "jolly_label": "Numero Jolly",
        "superstar_label": "Numero SuperStar",
        "jackpot_label": "Jackpot",
        "prize_pool_label": "Montepremi",
        "history_label": "Storico disponibile",
        "trend_label": "Andamento Jackpot e Montepremi",
        "select_date": "Seleziona data",
        "no_draws": "Nessuna estrazione salvata nello storico.",
        "updated": "Notizie aggiornate in {language}",
        "date_unavailable": "data non disponibile",
        "error_prefix": "Errore durante l'aggiornamento:",
    },
    "en": {
        "html_lang": "en",
        "eyebrow": "Rai Televideo RSS 101 and page 104",
        "title": "Televideo News",
        "lede": "Real Rai Televideo news, automatically archived and grouped by category.",
        "language_nav_label": "Interface and news language",
        "categories_title": "Categories",
        "news_link": "Chronicle",
        "super_link": "SuperEnalotto",
        "all_categories": "All",
        "status_label": "Update status",
        "loading": "Loading the latest news...",
        "last_reading": "Last reading",
        "waiting": "waiting",
        "empty_title": "The parchments are still empty",
        "empty_message": "The Rai feed did not answer yet, or the updater has not populated the database.",
        "card_ribbon": "News",
        "source_prefix": "Original title:",
        "category_prefix": "Category:",
        "source_link": "Rai source",
        "previous_page": "Previous",
        "next_page": "Next",
        "page_status": "Page {page} of {pages}",
        "super_title": "SuperEnalotto Archive",
        "super_lede": "Latest draw from Rai Televideo page 696, stored in the SQLite history.",
        "draw_label": "Draw",
        "draw_date_label": "Draw date",
        "numbers_label": "Winning numbers",
        "jolly_label": "Jolly number",
        "superstar_label": "SuperStar number",
        "jackpot_label": "Jackpot",
        "prize_pool_label": "Prize pool",
        "history_label": "Available history",
        "trend_label": "Jackpot and prize pool trend",
        "select_date": "Select date",
        "no_draws": "No draws saved in history yet.",
        "updated": "News updated in {language}",
        "date_unavailable": "date unavailable",
        "error_prefix": "Update error:",
    },
    "la": {
        "html_lang": "la",
        "eyebrow": "Rai Televideo RSS CI et pagina CIV",
        "title": "Nuntia Televidei",
        "lede": "Notitiae verae ex Rai Televideo, in archivio servatae et per categorias dispositae.",
        "language_nav_label": "Lingua interfaciei et nuntiorum",
        "categories_title": "Categoriae",
        "news_link": "Chronica",
        "super_link": "SuperEnalotto",
        "all_categories": "Omnes",
        "status_label": "Status renovationis",
        "loading": "Novissima nuntia colligo...",
        "last_reading": "Ultima lectio",
        "waiting": "exspectatur",
        "empty_title": "Pergamenae adhuc vacuae sunt",
        "empty_message": "Fons Rai nondum respondit aut minister renovandi datorum tabulam nondum implevit.",
        "card_ribbon": "Nuntium",
        "source_prefix": "Titulus primus:",
        "category_prefix": "Categoria:",
        "source_link": "Fons Rai",
        "previous_page": "Priora",
        "next_page": "Sequentia",
        "page_status": "Pagina {page} ex {pages}",
        "super_title": "Archivum SuperEnalotto",
        "super_lede": "Ultima sortitio ex pagina DCXCVI Rai Televideo, in memoria SQLite servata.",
        "draw_label": "Concursus",
        "draw_date_label": "Dies sortitionis",
        "numbers_label": "Numeri victores",
        "jolly_label": "Numerus Jolly",
        "superstar_label": "Numerus SuperStar",
        "jackpot_label": "Praemium maximum",
        "prize_pool_label": "Mons praemiorum",
        "history_label": "Historia servata",
        "trend_label": "Cursus praemii maximi et montis praemiorum",
        "select_date": "Diem elige",
        "no_draws": "Nulla sortitio adhuc servata est.",
        "updated": "Nuntia renovata lingua {language}",
        "date_unavailable": "dies ignotus",
        "error_prefix": "Error renovationis:",
    },
}


def normalize_language(value: str | None) -> str:
    return value if value in LANGUAGES else "la"


def ui_for(language: str) -> dict[str, str]:
    return UI_TEXT[normalize_language(language)]


def nav_items(active: str) -> list[dict[str, object]]:
    return [
        {"key": key, "label": label, "url": reverse(route), "active": key == active}
        for key, label, route in NAVIGATION
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
        "render_pre": snapshot.content_kind in {"index", "schedule", "table", "weather"},
    }


def section_snapshots(section: str, region: str = "") -> list[dict[str, object]]:
    queryset = TelevideoPageSnapshot.objects.filter(section=section, region=region).order_by(
        "sort_order",
        "page",
        "subpage",
    )
    return [snapshot_payload(snapshot) for snapshot in queryset]


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
    language = normalize_language(request.GET.get("lang"))
    if not NewsItem.objects.exists():
        try:
            refresh_if_stale()
        except RuntimeError:
            pass
    return render(
        request,
        "news/home.html",
        {
            "language": language,
            "languages": LANGUAGES,
            "refresh_seconds": settings.NEWS_REFRESH_SECONDS,
            "ui": ui_for(language),
            "nav_items": nav_items("home"),
        },
    )


def superenalotto(request):
    language = normalize_language(request.GET.get("lang"))
    if not SuperEnalottoDraw.objects.exists():
        try:
            refresh_if_stale()
        except RuntimeError:
            pass
    return render(
        request,
        "news/superenalotto.html",
        {
            "language": language,
            "languages": LANGUAGES,
            "refresh_seconds": settings.NEWS_REFRESH_SECONDS,
            "ui": ui_for(language),
            "nav_items": nav_items("giochi"),
        },
    )


def televideo_section(request, section: str, active: str):
    language = normalize_language(request.GET.get("lang"))
    if section not in SECTION_DEFINITIONS:
        raise Http404("Sezione non trovata")
    definition = section_definition(section)
    refresh_section_if_stale(section)
    snapshots = section_snapshots(section)
    latest = max((card["fetched_at"] for card in snapshots), default=None)
    return render(
        request,
        "news/section.html",
        {
            "section": {**definition, "key": section},
            "cards": snapshots,
            "latest": latest,
            "nav_items": nav_items(active),
            "language": language,
            "languages": LANGUAGES,
            "refresh_seconds": settings.NEWS_REFRESH_SECONDS,
            "ui": ui_for(language),
        },
    )


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
    return televideo_section(request, "meteo", "meteo")


def travel(request):
    return televideo_section(request, "viaggi", "viaggi")


def games(request):
    language = normalize_language(request.GET.get("lang"))
    refresh_section_if_stale("giochi")
    try:
        update_superenalotto()
        update_lotto()
    except RuntimeError:
        pass
    latest_superenalotto = SuperEnalottoDraw.objects.first()
    latest_lotto = LottoDraw.objects.first()
    snapshots = section_snapshots("giochi")
    latest = max((card["fetched_at"] for card in snapshots), default=None)
    return render(
        request,
        "news/games.html",
        {
            "section": {**section_definition("giochi"), "key": "giochi"},
            "cards": snapshots,
            "latest": latest,
            "latest_superenalotto": latest_superenalotto,
            "latest_lotto": latest_lotto,
            "nav_items": nav_items("giochi"),
            "language": language,
            "languages": LANGUAGES,
            "refresh_seconds": settings.NEWS_REFRESH_SECONDS,
            "ui": ui_for(language),
        },
    )


def regions(request, region_slug_value: str | None = None):
    language = normalize_language(request.GET.get("lang"))
    selected_region = normalize_region(region_slug_value or request.GET.get("regione"))
    refresh_section_if_stale("regioni", selected_region)
    snapshots = section_snapshots("regioni", selected_region)
    latest = max((card["fetched_at"] for card in snapshots), default=None)
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
            "section": {**section_definition("regioni"), "key": "regioni", "title": f"Televideo {selected_region}"},
            "cards": snapshots,
            "latest": latest,
            "regions": regions_payload,
            "selected_region": selected_region,
            "nav_items": nav_items("regioni"),
            "language": language,
            "languages": LANGUAGES,
            "refresh_seconds": settings.NEWS_REFRESH_SECONDS,
            "ui": ui_for(language),
        },
    )


def serialized_categories(language: str) -> list[dict[str, object]]:
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
                "name": category.name_for(language),
                "page": category.page,
                "count": category.news_count,
            }
        )
    return categories


def news_api(request):
    language = normalize_language(request.GET.get("lang"))
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
                "title": item.title_for(language),
                "summary": item.summary_for(language),
                "source_title": item.title_it,
                "category_code": category.code if category else "",
                "category_name": category.name_for(language) if category else "",
                "source_page": item.source_page,
                "published": item.pub_date_text,
                "published_iso": item.published_at.isoformat() if item.published_at else "",
            }
        )

    return JsonResponse(
        {
            "language": language,
            "language_label": LANGUAGES[language],
            "generated_at": timezone.localtime().isoformat(),
            "refresh_seconds": settings.NEWS_REFRESH_SECONDS,
            "selected_category": category_code,
            "ui": ui_for(language),
            "categories": serialized_categories(language),
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
    language = normalize_language(request.GET.get("lang"))
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
            "language": language,
            "language_label": LANGUAGES[language],
            "generated_at": timezone.localtime().isoformat(),
            "refresh_seconds": settings.NEWS_REFRESH_SECONDS,
            "ui": ui_for(language),
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
