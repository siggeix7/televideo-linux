from datetime import date

from django.conf import settings
from django.test import TestCase

from news.models import Category, LottoDraw, NewsItem, OpenWeatherCity, SuperEnalottoDraw, SuperEnalottoPrediction, TelevideoPageSnapshot


class CategoryTests(TestCase):
    def test_create_category(self):
        category = Category.objects.create(code="test", page=100, name_it="Test", sort_order=1)
        self.assertEqual(category.code, "test")
        self.assertEqual(category.name_it, "Test")

    def test_name_for_language(self):
        category = Category.objects.create(
            code="multi", name_it="Italiano", name_la="Latine", name_en="English"
        )
        self.assertEqual(category.name_for("it"), "Italiano")
        self.assertEqual(category.name_for("la"), "Latine")
        self.assertEqual(category.name_for("en"), "English")
        self.assertEqual(category.name_for("fr"), "Italiano")


class NewsItemTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(code="test", name_it="Test")

    def test_create_item(self):
        item = NewsItem.objects.create(
            source_id="test-001",
            category=self.category,
            title_it="Titolo",
            title_la="Titulus",
            title_en="Title",
            summary_it="Riassunto",
            summary_la="Summarium",
            summary_en="Summary",
        )
        self.assertEqual(item.title_for("it"), "Titolo")
        self.assertEqual(item.title_for("la"), "Titulus")
        self.assertEqual(item.title_for("en"), "Title")
        self.assertEqual(item.title_for("fr"), "Titolo")

    def test_summary_cleaning(self):
        item = NewsItem.objects.create(
            source_id="test-002",
            category=self.category,
            title_it="Titolo",
            summary_it="Dalle tavole del Televideo: Contenuto reale.",
        )
        self.assertEqual(item.summary_for("it"), "Contenuto reale.")


class SuperEnalottoDrawTests(TestCase):
    def test_create_draw(self):
        draw = SuperEnalottoDraw.objects.create(
            draw_number=1,
            draw_date=date(2025, 1, 1),
            winning_numbers=[1, 2, 3, 4, 5, 6],
            jolly_number=7,
            superstar_number=8,
            jackpot=1000000,
            prize_pool=5000000,
        )
        self.assertEqual(draw.winning_numbers, [1, 2, 3, 4, 5, 6])
        self.assertEqual(str(draw), "Concorso 1 del 2025-01-01")


class LottoDrawTests(TestCase):
    def test_create_draw(self):
        draw = LottoDraw.objects.create(
            draw_date=date(2025, 1, 1),
            wheels={"Bari": [1, 2, 3, 4, 5]},
            raw_text="Bari 1 2 3 4 5",
        )
        self.assertEqual(draw.wheels["Bari"], [1, 2, 3, 4, 5])


class OpenWeatherCityTests(TestCase):
    def test_create_city_cache(self):
        city = OpenWeatherCity.objects.create(
            city="Roma",
            region_slug="lazio",
            query="Roma,IT",
            condition="Sereno",
            temp=22,
        )
        self.assertEqual(str(city), "Roma")


class TelevideoPageSnapshotTests(TestCase):
    def test_create_snapshot(self):
        snapshot = TelevideoPageSnapshot.objects.create(
            section="test",
            page=100,
            subpage="01",
            label="Test page",
            title="Test title",
            content_kind="article",
            raw_text="Test content",
        )
        self.assertEqual(snapshot.section, "test")
        self.assertEqual(snapshot.page, 100)


class SettingsDefaultsTests(TestCase):
    def test_meteo_section_refresh_defaults_to_two_and_half_hours(self):
        self.assertEqual(settings.METEO_SECTION_REFRESH_SECONDS, 9000)

    def test_openweather_stale_defaults_to_two_and_half_hours(self):
        self.assertEqual(settings.OPENWEATHER_STALE_SECONDS, 9000)

    def test_openweather_batch_size_defaults_to_200(self):
        self.assertEqual(settings.OPENWEATHER_BATCH_SIZE, 200)


class SuperEnalottoPredictionTests(TestCase):
    def test_create_prediction(self):
        prediction = SuperEnalottoPrediction.objects.create(
            target_draw_date=date(2026, 6, 4),
            draw_number=100,
            combinations=[
                {"numbers": [1, 2, 3, 4, 5, 6], "jolly": 7, "superstar": 8, "label": "Test"},
                {"numbers": [10, 20, 30, 40, 50, 60], "jolly": 15, "superstar": 25, "label": "Test 2"},
            ],
        )
        self.assertEqual(prediction.draw_number, 100)
        self.assertEqual(len(prediction.combinations), 2)
        self.assertFalse(prediction.is_verified)

    def test_prediction_matched_counts(self):
        draw = SuperEnalottoDraw.objects.create(
            draw_number=1, draw_date=date(2026, 1, 1),
            winning_numbers=[1, 2, 3, 4, 5, 6],
            jolly_number=7, superstar_number=8,
        )
        prediction = SuperEnalottoPrediction.objects.create(
            target_draw_date=date(2026, 1, 1),
            draw_number=1,
            combinations=[
                {"numbers": [1, 2, 3, 10, 11, 12], "jolly": 7, "superstar": 8, "label": "Test"},
            ],
            matched_draw=draw,
            matched_counts=[{"matches": 3, "jolly_match": True, "superstar_match": True}],
            is_verified=True,
        )
        self.assertTrue(prediction.is_verified)
        self.assertEqual(prediction.matched_counts[0]["matches"], 3)
        self.assertEqual(str(prediction), "Pronostico SuperEnalotto per il 2026-01-01")
