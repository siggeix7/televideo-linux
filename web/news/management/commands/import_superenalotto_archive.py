from __future__ import annotations

import logging
import re
import urllib.request
from datetime import date
from http.client import HTTPResponse

from django.core.management.base import BaseCommand

from news.models import SuperEnalottoDraw


logger = logging.getLogger(__name__)

ARCHIVE_URL = "https://www.estrazionilotto.it/superenalotto/archivio-storico/{}"

ITALIAN_MONTHS = {
    "gennaio": 1, "febbraio": 2, "marzo": 3, "aprile": 4,
    "maggio": 5, "giugno": 6, "luglio": 7, "agosto": 8,
    "settembre": 9, "ottobre": 10, "novembre": 11, "dicembre": 12,
}

# Map Italian weekday names for date parsing (we just need the date)
DAY_MAP = {
    "lunedì": 1, "martedì": 2, "mercoledì": 3, "giovedì": 4,
    "venerdì": 5, "sabato": 6, "domenica": 7,
}

USER_AGENT = "Mozilla/5.0 (compatible; televideo-linux/1.0; +https://sabaudotoday.simguient.it)"


def fetch_url(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return resp.read().decode("utf-8", errors="replace")


def parse_draws_from_html(html: str) -> list[dict]:
    draws: list[dict] = []
    seen: set[int] = set()

    # Split by draw blocks — each starts with <h2>Estrazione Superenalotto n. X</h2>
    blocks = re.split(r'(?=<div class="tabella bg-orange-500">)', html)

    for block in blocks:
        draw_match = re.search(
            r"Estrazione Superenalotto n\.\s*(\d+)\s*</h2>.*?<h3>\s*"
            r"(?:lunedì|martedì|mercoledì|giovedì|venerdì|sabato|domenica)?\s*"
            r"(\d{1,2})\s+(\w+)\s+(\d{4})\s*</h3>",
            block, re.DOTALL,
        )
        if not draw_match:
            continue

        draw_number = int(draw_match.group(1))
        day = int(draw_match.group(2))
        month_name = draw_match.group(3).casefold()
        year = int(draw_match.group(4))
        month = ITALIAN_MONTHS.get(month_name)
        if not month:
            continue

        try:
            draw_date = date(year, month, day)
        except ValueError:
            continue

        if draw_number in seen:
            continue
        seen.add(draw_number)

        # Extract numbers: bg-orange-500 = winning, bg-red-500 = jolly, bg-red-700 = superstar
        winning = [
            int(m.group(1))
            for m in re.finditer(
                r'<p class="numero bg-orange-500">(\d+)</p>', block
            )
        ]
        jolly_match = re.search(
            r'<p class="numero bg-red-500">(\d+)</p>', block
        )
        superstar_match = re.search(
            r'<p class="numero bg-red-700">(\d+)</p>', block
        )

        if len(winning) != 6 or any(n < 1 or n > 90 for n in winning):
            continue

        draws.append({
            "draw_number": draw_number,
            "draw_date": draw_date,
            "winning_numbers": winning,
            "jolly_number": int(jolly_match.group(1)) if jolly_match else None,
            "superstar_number": int(superstar_match.group(1)) if superstar_match else None,
        })

    return draws


class Command(BaseCommand):
    help = "Import pre-2009 SuperEnalotto draws from estrazionilotto.it archive."

    def add_arguments(self, parser):
        parser.add_argument("--start-year", type=int, default=1997)
        parser.add_argument("--end-year", type=int, default=2008)

    def handle(self, *args, **options):
        start_year = options["start_year"]
        end_year = options["end_year"]

        for year in range(start_year, end_year + 1):
            url = ARCHIVE_URL.format(year)
            self.stdout.write(f"Fetching {url}...")
            try:
                html = fetch_url(url)
            except Exception as exc:
                self.stderr.write(self.style.ERROR(f"Failed to fetch {year}: {exc}"))
                continue

            draws = parse_draws_from_html(html)
            imported = 0
            skipped = 0

            for d in draws:
                raw = (
                    f"Fonte estrazionilotto.it: "
                    f"Concorso N.{d['draw_number']} del {d['draw_date'].isoformat()} "
                    f"numeri {' '.join(str(n) for n in d['winning_numbers'])} "
                    f"Jolly {d['jolly_number'] or '—'} SuperStar {d['superstar_number'] or '—'}"
                )
                defaults = {
                    "winning_numbers": d["winning_numbers"],
                    "jolly_number": d["jolly_number"],
                    "superstar_number": d["superstar_number"],
                    "raw_text": raw,
                }
                obj, created = SuperEnalottoDraw.objects.update_or_create(
                    draw_number=d["draw_number"],
                    draw_date=d["draw_date"],
                    defaults=defaults,
                )
                if created:
                    imported += 1
                else:
                    skipped += 1

            self.stdout.write(
                self.style.SUCCESS(
                    f"Year {year}: {len(draws)} draws parsed, "
                    f"{imported} imported, {skipped} skipped (already in DB)"
                )
            )

        total = SuperEnalottoDraw.objects.count()
        self.stdout.write(self.style.SUCCESS(f"Done. Total draws in DB: {total}"))
