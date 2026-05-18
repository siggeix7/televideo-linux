from __future__ import annotations

from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone

from .models import NewsItem
from .services import refresh_if_stale


LANGUAGES = {
    "la": "Latino",
    "it": "Italiano",
    "en": "English",
}


def normalize_language(value: str | None) -> str:
    return value if value in LANGUAGES else "la"


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
        },
    )


def news_api(request):
    language = normalize_language(request.GET.get("lang"))
    limit = min(max(int(request.GET.get("limit", "18")), 1), 50)
    error = ""
    try:
        refresh_if_stale()
    except RuntimeError as exc:
        error = str(exc)

    items = []
    for item in NewsItem.objects.all()[:limit]:
        items.append(
            {
                "id": item.source_id,
                "title": item.title_for(language),
                "summary": item.summary_for(language),
                "source_title": item.title_it,
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
            "error": error,
            "items": items,
        }
    )
