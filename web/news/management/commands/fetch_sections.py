import time

from django.conf import settings
from django.core.management.base import BaseCommand

from news.services.updater import refresh_all_sections


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
            saved = refresh_all_sections()
            self.stdout.write(self.style.SUCCESS(f"stored {saved} section snapshots"))
            if options["once"] or not loop:
                return
            time.sleep(interval)
