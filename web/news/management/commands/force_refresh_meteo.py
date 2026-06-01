import logging

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import close_old_connections

from news.openweather import refresh_due_openweather_cities
from news.services.updater import _retry_on_db_lock, update_section_snapshots


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Force-refreshes all meteo data (Televideo snapshots + OpenWeatherMap cache)."

    def handle(self, *args, **options):
        close_old_connections()
        results: list[str] = []

        saved = _retry_on_db_lock(update_section_snapshots, "meteo")
        results.append(f"Televideo meteo snapshots: {saved} record(s) saved")

        if settings.OPENWEATHER_API_KEY:
            result = _retry_on_db_lock(
                refresh_due_openweather_cities,
                force=True,
                max_calls=None,
            )
            detail = (
                result.get("message")
                or f"updated={result.get('updated', 0)} errors={result.get('errors', 0)} remaining={result.get('remaining', 0)}"
            )
            results.append(f"OpenWeatherMap: {result['status']} — {detail}")
        else:
            results.append("OpenWeatherMap: API key not configured, skipped")

        for line in results:
            self.stdout.write(self.style.SUCCESS(line))
