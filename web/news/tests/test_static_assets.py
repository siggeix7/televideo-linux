from pathlib import Path

from django.test import SimpleTestCase


class StaticAssetTests(SimpleTestCase):
    def test_news_search_debounce_timeout_is_declared(self):
        app_js = Path(__file__).resolve().parents[1] / "static" / "news" / "app.js"
        source = app_js.read_text(encoding="utf-8")

        self.assertIn("let searchTimeout", source)
        self.assertIn("clearTimeout(searchTimeout)", source)
