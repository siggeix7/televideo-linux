from __future__ import annotations

import urllib.error
import urllib.parse
import urllib.request

from .constants import BASE_URLS, RSS_PATH, TEXT_PATH, USER_AGENT


def request_text(url: str, timeout: float) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="replace")


def fetch_text(urls: list[str], timeout: float, retries: int) -> tuple[str, str]:
    errors = []
    for _ in range(retries + 1):
        for url in urls:
            try:
                return request_text(url, timeout), url
            except (TimeoutError, urllib.error.URLError, urllib.error.HTTPError) as exc:
                errors.append(str(exc))
    last_error = errors[-1] if errors else "nessun URL configurato"
    raise RuntimeError(f"nessuna risposta valida dagli host Rai: {last_error}")


def build_rss_urls() -> list[str]:
    return [base_url + RSS_PATH for base_url in BASE_URLS]


def build_text_urls(page: str, subpage: str | None = None, region: str = "") -> list[str]:
    query = {"pagina": page}
    if subpage:
        query["sottopagina"] = subpage
    if region:
        query["regione"] = region
    path = TEXT_PATH + "?" + urllib.parse.urlencode(query)
    return [base_url + path for base_url in BASE_URLS]


def page_link(page: int | str, subpage: str | None = None, region: str = "") -> str:
    query = {"pagina": str(page).zfill(3)}
    if subpage:
        query["sottopagina"] = subpage
    if region:
        query["regione"] = region
    return BASE_URLS[0] + TEXT_PATH + "?" + urllib.parse.urlencode(query)


def fetch_televideo_content(page: int | str, subpage: str | None = None, region: str = "", timeout: float = 8, retries: int = 1) -> str:
    from .parser import extract_page_content
    source, _ = fetch_text(
        build_text_urls(str(page).zfill(3), subpage=subpage, region=region),
        timeout,
        retries,
    )
    return extract_page_content(source)
