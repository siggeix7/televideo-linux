from unittest.mock import patch

from django.test import TestCase

from news.models import Category
from news.services.updater import update_category_news


class NewsUpdaterTests(TestCase):
    def test_skips_flash_pages_already_covered_by_rss(self):
        category = Category.objects.create(code="p109", page=109, name_it="Ultime News")

        with patch("news.services.updater.fetch_televideo_content") as fetch:
            self.assertEqual(update_category_news([category], per_category_limit=1), 0)

        fetch.assert_not_called()
