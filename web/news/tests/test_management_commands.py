from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.test import SimpleTestCase, override_settings


class FetchTelevideoCommandTests(SimpleTestCase):
    @override_settings(NEWS_REFRESH_SECONDS=1800, NEWS_FETCH_LIMIT=30, CATEGORY_FETCH_LIMIT=2)
    def test_loop_continues_after_refresh_error(self):
        stderr = StringIO()
        calls = []

        def fake_update(limit, category_limit):
            calls.append((limit, category_limit))
            if len(calls) == 1:
                raise RuntimeError("temporary Rai error")
            raise KeyboardInterrupt

        with (
            patch("news.management.commands.fetch_televideo.update_news", side_effect=fake_update),
            patch("news.management.commands.fetch_televideo.time.sleep", return_value=None) as sleep_mock,
            patch("news.management.commands.fetch_televideo.logger.exception"),
        ):
            with self.assertRaises(KeyboardInterrupt):
                call_command("fetch_televideo", "--loop", stdout=StringIO(), stderr=stderr)

        self.assertEqual(calls, [(30, 2), (30, 2)])
        sleep_mock.assert_called_once_with(60)
        self.assertIn("Televideo refresh failed: temporary Rai error", stderr.getvalue())


class FetchSectionsCommandTests(SimpleTestCase):
    @override_settings(TELETEXT_SECTION_REFRESH_SECONDS=1800)
    def test_loop_continues_after_refresh_error(self):
        stderr = StringIO()
        calls = []

        def fake_refresh():
            calls.append(1)
            if len(calls) == 1:
                raise RuntimeError("temporary Rai error")
            raise KeyboardInterrupt

        with (
            patch("news.management.commands.fetch_sections.refresh_all_sections", side_effect=fake_refresh),
            patch("news.management.commands.fetch_sections.time.sleep", return_value=None) as sleep_mock,
            patch("news.management.commands.fetch_sections.logger.exception"),
        ):
            with self.assertRaises(KeyboardInterrupt):
                call_command("fetch_sections", "--loop", stdout=StringIO(), stderr=stderr)

        self.assertEqual(calls, [1, 1])
        sleep_mock.assert_called_once_with(60)
        self.assertIn("Televideo section refresh failed: temporary Rai error", stderr.getvalue())
