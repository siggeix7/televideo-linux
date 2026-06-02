from __future__ import annotations

import logging
import time

from django.conf import settings
from django.core.management.base import BaseCommand

from news.services import update_news


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Fetches live Rai Televideo news and stores translations in the database."

    def add_arguments(self, parser):
        parser.add_argument("--once", action="store_true", help="fetch once and exit")
        parser.add_argument("--loop", action="store_true", help="fetch forever")
        parser.add_argument("--interval", type=int, default=settings.NEWS_REFRESH_SECONDS, help="seconds between fetches")
        parser.add_argument("--limit", type=int, default=settings.NEWS_FETCH_LIMIT, help="maximum feed items to store")
        parser.add_argument("--category-limit", type=int, default=settings.CATEGORY_FETCH_LIMIT, help="maximum items to store for each Televideo category")

    def handle(self, *args, **options):
        loop = options["loop"]
        interval = max(options["interval"], 10)
        limit = options["limit"]
        category_limit = options["category_limit"]

        while True:
            sleep_interval = interval
            try:
                saved = update_news(limit, category_limit)
            except Exception as exc:
                logger.exception("Televideo news refresh failed")
                if options["once"] or not loop:
                    raise
                sleep_interval = min(interval, 60)
                self.stderr.write(self.style.ERROR(f"Televideo refresh failed: {exc}"))
            else:
                self.stdout.write(self.style.SUCCESS(f"stored {saved} Televideo records"))
            if options["once"] or not loop:
                return
            time.sleep(sleep_interval)
