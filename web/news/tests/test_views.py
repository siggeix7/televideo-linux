from django.test import TestCase
from django.urls import reverse


class ViewTests(TestCase):
    def test_home_returns_200(self):
        response = self.client.get(reverse("news:home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Televideo")

    def test_home_with_language(self):
        response = self.client.get(reverse("news:home") + "?lang=en")
        self.assertEqual(response.status_code, 200)

    def test_news_api_returns_json(self):
        response = self.client.get(reverse("news:news_api"))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("items", data)
        self.assertIn("categories", data)
        self.assertIn("pagination", data)

    def test_news_api_with_params(self):
        response = self.client.get(reverse("news:news_api") + "?lang=en&category=test&page=1&limit=5")
        self.assertEqual(response.status_code, 200)

    def test_superenalotto_page(self):
        response = self.client.get(reverse("news:superenalotto"))
        self.assertEqual(response.status_code, 200)

    def test_superenalotto_api(self):
        response = self.client.get(reverse("news:superenalotto_api"))
        self.assertEqual(response.status_code, 200)

    def test_healthcheck(self):
        response = self.client.get(reverse("news:healthcheck"))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "ok")

    def test_section_pages(self):
        sections = ["tv", "cultura", "ambiente", "lavoro", "sport", "meteo", "viaggi", "giochi"]
        for section in sections:
            response = self.client.get(reverse(f"news:{section}"))
            self.assertEqual(response.status_code, 200, f"Section {section} failed")

    def test_regions_page(self):
        response = self.client.get(reverse("news:regions"))
        self.assertEqual(response.status_code, 200)

    def test_region_detail(self):
        response = self.client.get(reverse("news:region", kwargs={"region_slug_value": "lazio"}))
        self.assertEqual(response.status_code, 200)

    def test_invalid_section_returns_404(self):
        response = self.client.get("/nonexistent/")
        self.assertEqual(response.status_code, 404)

    def test_page_not_found_handler(self):
        response = self.client.get("/this-does-not-exist/")
        self.assertEqual(response.status_code, 404)
