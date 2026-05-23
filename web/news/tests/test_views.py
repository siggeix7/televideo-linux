from datetime import date, timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from news.models import Category, NewsItem, SuperEnalottoDraw, TelevideoPageSnapshot


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

    def test_news_api_searches_archive(self):
        category = Category.objects.create(code="test", name_it="Test", sort_order=1, active=True)
        NewsItem.objects.create(
            source_id="search-1",
            category=category,
            title_it="Titolo speciale",
            summary_it="Dalle tavole del Televideo: Contenuto con parola unica",
            link="http://www.televideo.rai.it/televideo/pub/view.jsp?id=1&p=101",
            published_at=timezone.now(),
        )
        NewsItem.objects.create(
            source_id="search-2",
            category=category,
            title_it="Altro titolo",
            summary_it="Contenuto generico",
            published_at=timezone.now(),
        )

        response = self.client.get(reverse("news:news_api") + "?q=unica")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["pagination"]["total"], 1)
        self.assertEqual(data["items"][0]["title"], "Titolo speciale")
        self.assertEqual(data["items"][0]["summary"], "Contenuto con parola unica")
        self.assertNotIn("link", data["items"][0])
        self.assertEqual(data["search_query"], "unica")

    def test_news_api_deduplicates_items(self):
        category = Category.objects.create(code="test", name_it="Test", sort_order=1, active=True)
        published_at = timezone.now()
        for index in range(2):
            NewsItem.objects.create(
                source_id=f"duplicate-{index}",
                category=category,
                title_it="Titolo duplicato",
                summary_it="Testo identico della notizia.",
                published_at=published_at - timedelta(minutes=index),
            )

        response = self.client.get(reverse("news:news_api"))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["pagination"]["total"], 1)
        self.assertEqual(len(data["items"]), 1)

    def test_news_api_deduplicates_similar_titles(self):
        category = Category.objects.create(code="test", name_it="Test", sort_order=1, active=True)
        published_at = timezone.now()
        NewsItem.objects.create(
            source_id="similar-1",
            category=category,
            title_it="Droni Kiev su dormitorio,morti e feriti",
            summary_it="Attacco nella notte con vittime e persone ferite.",
            published_at=published_at,
        )
        NewsItem.objects.create(
            source_id="similar-2",
            category=category,
            title_it="Droni Kiev su dormitorio studenti,morti",
            summary_it="Colpito un dormitorio studentesco, si registrano vittime.",
            published_at=published_at - timedelta(minutes=5),
        )

        response = self.client.get(reverse("news:news_api"))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["pagination"]["total"], 1)
        self.assertEqual(data["items"][0]["title"], "Droni Kiev su dormitorio,morti e feriti")

    def test_news_api_keeps_titles_with_different_subjects(self):
        category = Category.objects.create(code="test", name_it="Test", sort_order=1, active=True)
        published_at = timezone.now()
        NewsItem.objects.create(
            source_id="distinct-1",
            category=category,
            title_it="Droni Kiev su dormitorio,morti e feriti",
            summary_it="Attacco contro un dormitorio.",
            published_at=published_at,
        )
        NewsItem.objects.create(
            source_id="distinct-2",
            category=category,
            title_it="Droni Kiev su deposito,morti e feriti",
            summary_it="Attacco contro un deposito.",
            published_at=published_at - timedelta(minutes=5),
        )

        response = self.client.get(reverse("news:news_api"))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["pagination"]["total"], 2)

    def test_home_renders_initial_news_and_filters(self):
        category = Category.objects.create(code="test", name_it="Test", sort_order=1, active=True)
        NewsItem.objects.create(
            source_id="home-1",
            category=category,
            title_it="Titolo iniziale",
            summary_it="Testo renderizzato dal server",
            published_at=timezone.now(),
        )

        response = self.client.get(reverse("news:home") + "?q=server&category=test")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "data-server-rendered")
        self.assertContains(response, "value=\"server\"")
        self.assertContains(response, "Cancella")
        self.assertContains(response, "Vai al contenuto")
        self.assertContains(response, "aria-current=\"page\"")
        self.assertNotContains(response, "news-group__header")
        self.assertNotContains(response, "news-card--lead")

    def test_home_does_not_render_televideo_links(self):
        category = Category.objects.create(code="test", name_it="Test", sort_order=1, active=True)
        NewsItem.objects.create(
            source_id="home-link",
            category=category,
            title_it="Titolo senza link",
            summary_it="Testo renderizzato dal server",
            link="http://www.televideo.rai.it/televideo/pub/view.jsp?id=1&p=101",
            published_at=timezone.now(),
        )

        response = self.client.get(reverse("news:home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Titolo senza link")
        self.assertNotContains(response, "www.televideo.rai.it/televideo/pub/view.jsp")
        self.assertNotContains(response, "news-card__title-link")

    def test_culture_section_formats_article_text(self):
        TelevideoPageSnapshot.objects.create(
            section="cultura",
            page=540,
            subpage="01",
            label="Cultura",
            title="Titolo articolo",
            content_kind="article",
            raw_text="1/2\nTitolo articolo\nPrima parte\ncontinua.\n101 Sommario 102 Esteri",
            sort_order=1,
        )
        TelevideoPageSnapshot.objects.create(
            section="cultura",
            page=540,
            subpage="02",
            label="Cultura",
            title="Titolo articolo",
            content_kind="article",
            raw_text="2/2\nSeconda parte.\nRAI INFORMA",
            sort_order=2,
        )

        response = self.client.get(reverse("news:culture"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Prima parte continua.")
        self.assertContains(response, "Seconda parte.")
        self.assertNotContains(response, "1/2")
        self.assertNotContains(response, "2/2")
        self.assertNotContains(response, "101 Sommario 102 Esteri")

    def test_robots_and_sitemap(self):
        robots = self.client.get(reverse("news:robots"))
        sitemap = self.client.get(reverse("news:sitemap"))
        self.assertEqual(robots.status_code, 200)
        self.assertContains(robots, "Sitemap:")
        self.assertEqual(sitemap.status_code, 200)
        self.assertContains(sitemap, "<urlset")

    def test_superenalotto_page(self):
        response = self.client.get(reverse("news:superenalotto"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Vai al contenuto")
        self.assertContains(response, "id=\"main\"")

    def test_superenalotto_api(self):
        response = self.client.get(reverse("news:superenalotto_api"))
        self.assertEqual(response.status_code, 200)

    def test_superenalotto_api_falls_back_from_invalid_date(self):
        SuperEnalottoDraw.objects.create(
            draw_number=1,
            draw_date=date(2026, 1, 1),
            winning_numbers=[1, 2, 3, 4, 5, 6],
        )

        response = self.client.get(reverse("news:superenalotto_api") + "?date=1999-01-01")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["selected_date"], "2026-01-01")
        self.assertEqual(data["selected"]["draw_number"], 1)

    def test_healthcheck(self):
        response = self.client.get(reverse("news:healthcheck"))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "ok")

    def test_section_pages(self):
        sections = ["tv", "culture", "environment", "work", "sport", "weather", "travel", "games"]
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
