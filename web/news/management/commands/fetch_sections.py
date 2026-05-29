import logging
import time

from django.conf import settings
from django.core.management.base import BaseCommand

from news.services.updater import refresh_all_sections


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Periodically refreshes all Televideo section snapshots (TV, sport, etc.)."

    def add_arguments(self, parser):
        parser.add_argument("--once", action="store_true", help="fetch once and exit")
        parser.add_argument("--loop", action="store_true", help="fetch forever")
        parser.add_argument(
            "--interval",
            type=int,
            default=settings.TELETEXT_SECTION_REFRESH_SECONDS,
            help="seconds between full section refreshes",
        )

    def handle(self, *args, **options):
        loop = options["loop"]
        interval = max(options["interval"], 60)
        while True:
            sleep_interval = interval
            try:
                saved = refresh_all_sections()
            except Exception as exc:
                logger.exception("Televideo section refresh failed")
                if options["once"] or not loop:
                    raise
                sleep_interval = min(interval, 60)
                self.stderr.write(self.style.ERROR(f"Televideo section refresh failed: {exc}"))
            else:
                self.stdout.write(self.style.SUCCESS(f"stored {saved} section snapshots"))
            if options["once"] or not loop:
                return
            time.sleep(sleep_interval)
