from unittest.mock import patch

from django.test import TestCase, override_settings

from news.models import Category, SuperEnalottoDraw
from news.services.updater import refresh_all_sections, update_category_news, update_superenalotto


class NewsUpdaterTests(TestCase):
    def test_skips_flash_pages_already_covered_by_rss(self):
        category = Category.objects.create(code="p109", page=109, name_it="Ultime News")

        with patch("news.services.updater.fetch_televideo_content") as fetch:
            self.assertEqual(update_category_news([category], per_category_limit=1), 0)

        fetch.assert_not_called()

    @override_settings(OPENWEATHER_API_KEY="test-key")
    def test_refresh_all_sections_skips_meteo_with_openweather(self):
        calls = []

        def fake_update(section, region=""):
            calls.append((section, region))
            return 1

        with patch("news.services.updater.update_section_snapshots", side_effect=fake_update):
            refresh_all_sections()

        self.assertNotIn(("meteo", ""), calls)

    def test_update_superenalotto_uses_official_archive(self):
        official_archive = """
        Concorso Nº 95 del 13 Giugno 2026
        13 23 34 68 87 90 80 54 Dettagli
        """

        with (
            patch("news.services.updater.fetch_text", return_value=(official_archive, "https://www.superenalotto.it/archivio-estrazioni")),
            patch("news.services.updater.fetch_televideo_content", side_effect=RuntimeError("Rai non aggiornata")),
        ):
            saved = update_superenalotto()

        draw = SuperEnalottoDraw.objects.get(draw_number=95)
        self.assertEqual(saved, 1)
        self.assertEqual(draw.draw_date.isoformat(), "2026-06-13")
        self.assertEqual(draw.winning_numbers, [13, 23, 34, 68, 87, 90])
        self.assertEqual(draw.jolly_number, 80)
        self.assertEqual(draw.superstar_number, 54)
