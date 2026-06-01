import logging
import time

from django.conf import settings
from django.core.management.base import BaseCommand

from news.openweather import refresh_due_openweather_cities


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Refreshes cached OpenWeatherMap data for province capitals with pacing."

    def add_arguments(self, parser):
        parser.add_argument("--once", action="store_true", help="check once and exit")
        parser.add_argument("--loop", action="store_true", help="check forever")
        parser.add_argument("--force", action="store_true", help="refresh cached cities even if they are not stale")
        parser.add_argument("--max-calls", type=int, default=settings.OPENWEATHER_BATCH_SIZE, help="maximum API calls per check")
        parser.add_argument(
            "--interval",
            type=int,
            default=settings.OPENWEATHER_REFRESH_CHECK_SECONDS,
            help="seconds between checks",
        )

    def handle(self, *args, **options):
        loop = options["loop"]
        interval = max(options["interval"], 60)

        while True:
            sleep_interval = interval
            try:
                result = refresh_due_openweather_cities(force=options["force"], max_calls=options["max_calls"])
            except Exception as exc:
                logger.exception("OpenWeather refresh check failed")
                if options["once"] or not loop:
                    raise
                sleep_interval = min(interval, 60)
                self.stderr.write(self.style.ERROR(f"OpenWeather refresh check failed: {exc}"))
            else:
                detail = result.get("message") or f"updated={result.get('updated', 0)} errors={result.get('errors', 0)} remaining={result.get('remaining', 0)}"
                self.stdout.write(self.style.SUCCESS(f"OpenWeather {result['status']}: {detail}"))

            if options["once"] or not loop:
                return
            time.sleep(sleep_interval)
