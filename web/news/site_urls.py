from __future__ import annotations

from urllib.parse import urljoin

from django.conf import settings


def public_base_url(request) -> str:
    configured = getattr(settings, "PUBLIC_SITE_URL", "")
    if configured:
        return configured.rstrip("/")
    return request.build_absolute_uri("/").rstrip("/")


def public_absolute_url(request, path: str) -> str:
    base_url = public_base_url(request)
    return urljoin(base_url + "/", path.lstrip("/"))


def seo_context(request) -> dict[str, str]:
    return {
        "app_version": getattr(settings, "APP_VERSION", "dev"),
        "canonical_url": public_absolute_url(request, request.path),
    }
