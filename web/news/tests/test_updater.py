from unittest.mock import patch

from django.test import TestCase, override_settings

from news.models import Category
from news.services.updater import refresh_all_sections, update_category_news


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
