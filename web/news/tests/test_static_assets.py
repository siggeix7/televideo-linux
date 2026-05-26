from pathlib import Path

from django.test import SimpleTestCase


class StaticAssetTests(SimpleTestCase):
    def test_news_search_debounce_timeout_is_declared(self):
        app_js = Path(__file__).resolve().parents[1] / "static" / "news" / "app.js"
        source = app_js.read_text(encoding="utf-8")

        self.assertIn("let searchTimeout", source)
        self.assertIn("clearTimeout(searchTimeout)", source)

    def test_news_update_toast_skips_first_render(self):
        app_js = Path(__file__).resolve().parents[1] / "static" / "news" / "app.js"
        source = app_js.read_text(encoding="utf-8")

        self.assertIn("var wasFirstRender = firstRender", source)
        self.assertIn("!wasFirstRender", source)

    def test_superenalotto_requests_abort_stale_fetches(self):
        super_js = Path(__file__).resolve().parents[1] / "static" / "news" / "superenalotto.js"
        source = super_js.read_text(encoding="utf-8")

        self.assertIn("let activeController", source)
        self.assertIn("let requestSeq", source)
        self.assertIn("if (activeController) activeController.abort()", source)
