from __future__ import annotations

import time
from typing import Callable

from django.core.cache import cache
from django.http import HttpResponse


class RateLimitMiddleware:
    LIMIT = 60
    WINDOW = 60

    def __init__(self, get_response: Callable):
        self.get_response = get_response

    def __call__(self, request):
        if not request.path.startswith("/api/"):
            return self.get_response(request)

        ip = self._client_ip(request)
        key = f"rl:{ip}"
        now = int(time.time())
        window_start = now - self.WINDOW

        entries = cache.get(key)
        if entries is None:
            entries = []
        entries = [ts for ts in entries if ts > window_start]

        if len(entries) >= self.LIMIT:
            return HttpResponse(
                "Troppe richieste. Riprova tra un minuto.",
                content_type="text/plain; charset=utf-8",
                status=429,
            )

        entries.append(now)
        cache.set(key, entries, timeout=self.WINDOW + 10)
        return self.get_response(request)

    @staticmethod
    def _client_ip(request) -> str:
        x_forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded:
            return x_forwarded.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "127.0.0.1")
