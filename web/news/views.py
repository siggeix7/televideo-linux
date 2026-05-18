from __future__ import annotations

from django.conf import settings
from django.db.models import Count
from django.db import connection
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone

from .models import Category, NewsItem, SuperEnalottoDraw
from .services import refresh_if_stale


LANGUAGES = {
    "la": "Latino",
    "it": "Italiano",
    "en": "English",
}

UI_TEXT = {
    "it": {
        "html_lang": "it",
        "eyebrow": "Rai Televideo RSS 101 e pagina 104",
        "title": "Chronica Televidei",
        "lede": "Notizie reali, raccolte in tempo quasi reale e ordinate nelle categorie del Televideo come una cronaca da monastero digitale.",
        "language_nav_label": "Lingua dell'interfaccia e delle notizie",
        "categories_title": "Categorie",
        "news_link": "Cronaca",
        "super_link": "SuperEnalotto",
        "all_categories": "Tutte",
        "status_label": "Stato della cronaca",
        "loading": "Carico le ultime notizie...",
        "last_reading": "Ultima lettura",
        "waiting": "in attesa",
        "empty_title": "Le pergamene sono ancora vuote",
        "empty_message": "Il feed Rai non ha risposto oppure il job di aggiornamento non ha ancora popolato il database.",
        "card_ribbon": "Novella",
        "source_prefix": "Fonte originale:",
        "category_prefix": "Categoria:",
        "source_link": "Leggi fonte Rai",
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
        "updated": "Cronaca aggiornata in {language}",
        "date_unavailable": "data non disponibile",
        "error_prefix": "Errore durante l'aggiornamento:",
    },
    "en": {
        "html_lang": "en",
        "eyebrow": "Rai Televideo RSS 101 and page 104",
        "title": "Chronica Televidei",
        "lede": "Real news, gathered almost live and arranged by Televideo categories as a digital monastic chronicle.",
        "language_nav_label": "Interface and news language",
        "categories_title": "Categories",
        "news_link": "Chronicle",
        "super_link": "SuperEnalotto",
        "all_categories": "All",
        "status_label": "Chronicle status",
        "loading": "Loading the latest news...",
        "last_reading": "Last reading",
        "waiting": "waiting",
        "empty_title": "The parchments are still empty",
        "empty_message": "The Rai feed did not answer yet, or the updater has not populated the database.",
        "card_ribbon": "Dispatch",
        "source_prefix": "Original source:",
        "category_prefix": "Category:",
        "source_link": "Read Rai source",
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
        "updated": "Chronicle updated in {language}",
        "date_unavailable": "date unavailable",
        "error_prefix": "Update error:",
    },
    "la": {
        "html_lang": "la",
        "eyebrow": "Rai Televideo RSS CI et pagina CIV",
        "title": "Chronica Televidei",
        "lede": "Notitiae verae fere in ipso tempore collectae et per categorias Televidei dispositae, more chronicae monasticae digitalis.",
        "language_nav_label": "Lingua interfaciei et nuntiorum",
        "categories_title": "Categoriae",
        "news_link": "Chronica",
        "super_link": "SuperEnalotto",
        "all_categories": "Omnes",
        "status_label": "Status chronicae",
        "loading": "Novissima nuntia colligo...",
        "last_reading": "Ultima lectio",
        "waiting": "exspectatur",
        "empty_title": "Pergamenae adhuc vacuae sunt",
        "empty_message": "Fons Rai nondum respondit aut minister renovandi datorum tabulam nondum implevit.",
        "card_ribbon": "Novella",
        "source_prefix": "Fons primus:",
        "category_prefix": "Categoria:",
        "source_link": "Fontem Rai lege",
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
        "updated": "Chronica renovata lingua {language}",
        "date_unavailable": "dies ignotus",
        "error_prefix": "Error renovationis:",
    },
}


def normalize_language(value: str | None) -> str:
    return value if value in LANGUAGES else "la"


def ui_for(language: str) -> dict[str, str]:
    return UI_TEXT[normalize_language(language)]


def parse_limit(value: str | None, default: int = 18) -> int:
    try:
        return min(max(int(value or default), 1), 80)
    except ValueError:
        return default


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
        },
    )


def serialized_categories(language: str) -> list[dict[str, object]]:
    categories = []
    queryset = Category.objects.filter(active=True).annotate(news_count=Count("items")).filter(news_count__gt=0)
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
    limit = parse_limit(request.GET.get("limit"))
    category_code = request.GET.get("category") or "all"
    error = ""
    try:
        refresh_if_stale()
    except RuntimeError as exc:
        error = str(exc)

    queryset = NewsItem.objects.select_related("category").all()
    if category_code != "all":
        filtered = queryset.filter(category__code=category_code)
        if filtered.exists():
            queryset = filtered
        else:
            category_code = "all"

    items = []
    for item in queryset[:limit]:
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
                "link": item.link,
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
            "error": error,
            "items": items,
        }
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
