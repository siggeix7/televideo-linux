from unittest.mock import patch

from django.test import TestCase, override_settings
from django.utils import timezone

from news.models import OpenWeatherCity
from news.openweather import openweather_city_payload, refresh_due_openweather_cities, refresh_due_openweather_city
from news.weather_capitals import build_region_capital_weather


def forecast_payload():
    return {
        "city": {"timezone": 7200, "sunrise": 1717214400, "sunset": 1717279200},
        "list": [
            {
                "dt": 1717232400,
                "weather": [{"description": "cielo sereno"}],
                "main": {"temp": 21.4, "temp_min": 20.7, "temp_max": 22.2},
                "wind": {"speed": 2.4},
                "visibility": 10000,
                "pop": 0.1,
            },
            {
                "dt": 1717243200,
                "weather": [{"description": "poche nuvole"}],
                "main": {"temp": 24.2, "temp_min": 23.1, "temp_max": 25.4},
                "wind": {"speed": 2.0},
                "visibility": 9000,
                "pop": 0.2,
            },
            {
                "dt": 1717318800,
                "weather": [{"description": "pioggia leggera"}],
                "main": {"temp": 18.1, "temp_min": 17.0, "temp_max": 19.5},
                "wind": {"speed": 3.2},
                "visibility": 7000,
                "pop": 0.8,
            },
        ],
    }


class OpenWeatherServiceTests(TestCase):
    @override_settings(
        OPENWEATHER_API_KEY="test-key",
        OPENWEATHER_STALE_SECONDS=43200,
        OPENWEATHER_MAX_CALLS_PER_MINUTE=40,
    )
    def test_refresh_updates_batch_with_rate_limit(self):
        sleeps = []

        with patch("news.openweather.fetch_openweather_payload", return_value=forecast_payload()) as fetch:
            result = refresh_due_openweather_cities(max_calls=2, sleep_func=sleeps.append)

        self.assertEqual(result["status"], "updated")
        self.assertEqual(result["updated"], 2)
        self.assertEqual(fetch.call_count, 2)
        self.assertEqual(sleeps, [1.5])
        city = OpenWeatherCity.objects.get(city=result["results"][0]["city"])
        self.assertEqual(city.condition, "Cielo sereno")
        self.assertEqual(city.temp, 21)
        self.assertEqual(city.temp_min, 21)
        self.assertEqual(city.temp_max, 25)
        self.assertEqual(len(city.today_forecast), 2)
        self.assertEqual(len(city.forecast_days), 2)

    @override_settings(OPENWEATHER_API_KEY="test-key", OPENWEATHER_MAX_CALLS_PER_MINUTE=40)
    def test_refresh_single_city_wrapper_still_works(self):
        with patch("news.openweather.fetch_openweather_payload", return_value=forecast_payload()):
            result = refresh_due_openweather_city()

        self.assertEqual(result["status"], "updated")

    @override_settings(OPENWEATHER_API_KEY="")
    def test_refresh_is_disabled_without_api_key(self):
        result = refresh_due_openweather_city()

        self.assertEqual(result["status"], "disabled")

    def test_weather_capitals_uses_openweather_as_fallback(self):
        data = {"weather_stations": [], "temperatures": []}
        openweather = {
            "ROMA": {
                "condition": "Sereno",
                "temp": 22,
                "min": 20,
                "max": 24,
                "wind": "2.0 m/s",
                "visibility": "10.0 km",
                "sunrise": "05:20",
                "sunset": "20:40",
                "today_forecast": [{"time": "12:00", "temp": 22, "condition": "Sereno"}],
                "forecast_days": [{"label": "Oggi", "min": 20, "max": 24, "condition": "Sereno"}],
                "source_label": "OpenWeatherMap",
                "source_at": timezone.now(),
            }
        }

        regions = build_region_capital_weather(data, openweather)
        roma = next(city for city in regions["lazio"] if city["name"] == "Roma")

        self.assertTrue(roma["available"])
        self.assertEqual(roma["source_label"], "OpenWeatherMap")
        self.assertEqual(roma["sunrise"], "05:20")
        self.assertEqual(roma["forecast_days"][0]["label"], "Oggi")
        self.assertIn("Sereno", roma["summary"])

    def test_weather_capitals_can_ignore_televideo_when_openweather_only(self):
        data = {
            "weather_stations": [{"stations": [{"name": "Roma", "condition": "Nuvoloso", "temp": 12}]}],
            "temperatures": [{"cities": [{"city": "Roma", "min": 10, "max": 14}]}],
        }
        openweather = {
            "ROMA": {
                "condition": "Sereno",
                "temp": 22,
                "min": 20,
                "max": 24,
                "source_label": "OpenWeatherMap",
            }
        }

        regions = build_region_capital_weather(data, openweather, openweather_only=True)
        roma = next(city for city in regions["lazio"] if city["name"] == "Roma")

        self.assertEqual(roma["condition"], "Sereno")
        self.assertEqual(roma["temp"], 22)
        self.assertEqual(roma["source_label"], "OpenWeatherMap")

    def test_openweather_payload_exposes_grouped_forecasts(self):
        city = OpenWeatherCity.objects.create(city="Roma", region_slug="lazio", query="Roma,IT")
        from news.openweather import store_openweather_payload

        store_openweather_payload(city, forecast_payload(), now=timezone.now())
        payload = openweather_city_payload(city)

        self.assertEqual(payload["condition"], "Cielo sereno")
        self.assertEqual(payload["temp"], 21)
        self.assertTrue(payload["sunrise"])
        self.assertTrue(payload["sunset"])
        self.assertEqual(payload["forecast_days"][0]["label"], "Oggi")
        self.assertEqual(payload["forecast_days"][1]["label"], "Domani")
