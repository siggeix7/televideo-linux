from datetime import date, timedelta

from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from news.models import Category, NewsItem, OpenWeatherCity, SuperEnalottoDraw, TelevideoPageSnapshot


class ViewTests(TestCase):
    def test_home_returns_200(self):
        response = self.client.get(reverse("news:home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Televideo")

    def test_home_with_language(self):
        response = self.client.get(reverse("news:home") + "?lang=en")
        self.assertEqual(response.status_code, 200)

    @override_settings(APP_VERSION="vtest")
    def test_footer_shows_app_version(self):
        response = self.client.get(reverse("news:home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Versione vtest")

    def test_news_api_returns_json(self):
        response = self.client.get(reverse("news:news_api"))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("items", data)
        self.assertIn("available_dates", data)
        self.assertIn("selected_date", data)
        self.assertIn("pagination", data)

    def test_news_api_with_params(self):
        response = self.client.get(reverse("news:news_api") + "?lang=en&date=2026-05-29&page=1&limit=5")
        self.assertEqual(response.status_code, 200)

    def test_news_api_applies_limit_options(self):
        category = Category.objects.create(code="test", name_it="Test", sort_order=1, active=True)
        published_at = timezone.now()
        for index in range(30):
            NewsItem.objects.create(
                source_id=f"limit-{index}",
                category=category,
                title_it=f"Titolo limite {index}",
                summary_it=f"Contenuto limite {index}",
                published_at=published_at - timedelta(minutes=index),
            )

        response = self.client.get(reverse("news:news_api") + "?limit=25")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["pagination"]["limit"], 25)
        self.assertEqual(data["pagination"]["pages"], 2)
        self.assertEqual(len(data["items"]), 25)

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

    def test_news_api_filters_by_date(self):
        category = Category.objects.create(code="test", name_it="Test", sort_order=1, active=True)
        today = timezone.localtime().replace(hour=12, minute=0, second=0, microsecond=0)
        yesterday = today - timedelta(days=1)
        NewsItem.objects.create(
            source_id="date-1",
            category=category,
            title_it="Notizia di oggi",
            summary_it="Contenuto odierno",
            published_at=today,
        )
        NewsItem.objects.create(
            source_id="date-2",
            category=category,
            title_it="Notizia di ieri",
            summary_it="Contenuto precedente",
            published_at=yesterday,
        )

        selected = yesterday.date().isoformat()
        response = self.client.get(reverse("news:news_api") + f"?date={selected}")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["selected_date"], selected)
        self.assertEqual(data["pagination"]["total"], 1)
        self.assertEqual(data["items"][0]["title"], "Notizia di ieri")

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
        published_at = timezone.localtime().replace(hour=12, minute=0, second=0, microsecond=0)
        selected = published_at.date().isoformat()
        NewsItem.objects.create(
            source_id="home-1",
            category=category,
            title_it="Titolo iniziale",
            summary_it="Testo renderizzato dal server",
            published_at=published_at,
        )

        response = self.client.get(reverse("news:home") + f"?q=server&date={selected}")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "data-server-rendered")
        self.assertContains(response, "value=\"server\"")
        self.assertContains(response, f"value=\"{selected}\"")
        self.assertContains(response, "Cancella")
        self.assertContains(response, "Vai al contenuto")
        self.assertContains(response, "aria-current=\"page\"")
        self.assertContains(response, "news-group__header")
        self.assertNotContains(response, "category-panel")
        self.assertNotContains(response, "news-card--lead")

    def test_home_renders_news_limit_controls(self):
        response = self.client.get(reverse("news:home") + "?limit=50")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Notizie per pagina")
        self.assertContains(response, 'data-initial-limit="50"')
        self.assertContains(response, 'data-limit="10"')
        self.assertContains(response, 'data-limit="25"')
        self.assertContains(response, 'data-limit="50" aria-pressed="true"')
        self.assertContains(response, 'data-limit="100"')

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

    def test_home_hides_flash_page_scraped_fragments(self):
        category = Category.objects.create(code="p109", name_it="Ultime News", sort_order=1, active=True)
        NewsItem.objects.create(
            source_id="flash-fragment",
            category=category,
            source_page="109",
            title_it="re di soccorso.",
            summary_it="ovane italiano di 20 anni,residenLiguria, e' cosciente ma ha un ar-.",
            published_at=timezone.now(),
        )

        response = self.client.get(reverse("news:home"))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "re di soccorso")
        self.assertNotContains(response, "residenLiguria")

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

    def test_tv_section_renders_channel_schedules_and_non_channel_cards(self):
        TelevideoPageSnapshot.objects.create(
            section="tv",
            page=517,
            subpage="01",
            label="Programmi criptati",
            title="Programmi criptati",
            content_kind="schedule",
            raw_text="SETTIMANA DAL 17/05 AL 23/05\n\nNESSUN PROGRAMMA CODIFICATO",
            sort_order=1,
        )
        TelevideoPageSnapshot.objects.create(
            section="tv",
            page=518,
            subpage="01",
            label="Rai Sport HD",
            title="23 Maggio",
            content_kind="schedule",
            raw_text=(
                "23 Maggio\n"
                " 06:00 Ciclismo - Giro d'Italia 2026:\n"
                "       RiGiro\n"
                " 07:00 TG Sport Mattina\n"
                " 18:00 Atletica. Coppa Europa La Spe-\n"
                "       zia: 10.000\n"
            ),
            sort_order=2,
        )
        TelevideoPageSnapshot.objects.create(
            section="tv",
            page=518,
            subpage="02",
            label="Rai Sport HD",
            title="23 Maggio",
            content_kind="schedule",
            raw_text=(
                "23 Maggio\n"
                " 20:00 TGiro\n"
                " 20:45 Pallavolo. Torneo Internazionale\n"
                "       femminile\n"
            ),
            sort_order=3,
        )
        TelevideoPageSnapshot.objects.create(
            section="tv",
            page=528,
            subpage="01",
            label="RaiPlay",
            title="FILM CLUB",
            content_kind="schedule",
            raw_text="FILM CLUB\nSerie in 6 episodi",
            sort_order=4,
        )

        response = self.client.get(reverse("news:tv"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "tv-channel")
        self.assertContains(response, "Rai Sport HD")
        self.assertContains(response, "Ciclismo - Giro d&#x27;Italia 2026: RiGiro")
        self.assertContains(response, "Atletica. Coppa Europa La Spezia: 10.000")
        self.assertContains(response, "Pallavolo. Torneo Internazionale femminile")
        self.assertNotContains(response, "TG Sport Mattina 23 Maggio")
        self.assertContains(response, "NESSUN PROGRAMMA CODIFICATO")
        self.assertContains(response, "FILM CLUB")
        self.assertNotContains(response, "raw-block")

    def test_travel_index_does_not_render_televideo_navigation_raw(self):
        TelevideoPageSnapshot.objects.create(
            section="viaggi",
            page=433,
            subpage="01",
            label="Indice in viaggio",
            title="Indice in viaggio",
            content_kind="index",
            raw_text=(
                "Indice in viaggio\n"
                "AVVISI VIAGGIARE SICURI 434>440\n"
                "    STRADE D'ITALIA - ITINERARI   443\n"
                "    COS'E' IL FAI                 445  j\n"
                "    CAPITALE CULTURA:\n"
                "     A SPASSO PER... a pagina 408 del\n"
                "         TELEVIDEO REGIONALE RAI3\n"
            ),
            sort_order=1,
        )

        response = self.client.get(reverse("news:travel"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "televideo-index-item")
        self.assertContains(response, "A SPASSO PER...")
        self.assertNotContains(response, "pag. 408")
        self.assertNotContains(response, "a pagina 408 del")
        self.assertNotContains(response, "TELEVIDEO REGIONALE")
        self.assertNotContains(response, "Pagina 433")
        self.assertNotContains(response, "raw-block")

    def test_games_hides_unparsed_superenalotto_snapshot(self):
        TelevideoPageSnapshot.objects.create(
            section="giochi",
            page=696,
            subpage="01",
            label="SuperEnalotto",
            title="Ultime notizie",
            content_kind="table",
            raw_text=(
                "NUOVO\n"
                "CONCORSO N.87 30/05/2026\n"
                "COMBINAZIONE     nessun        \"sei\"\n"
                "N.ro SuperStar 56   euro      25.859,69\n"
            ),
            sort_order=1,
        )

        response = self.client.get(reverse("news:games"))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "COMBINAZIONE")
        self.assertNotContains(response, "N.ro SuperStar")
        self.assertNotContains(response, "raw-block")

    def test_games_index_is_structured_not_raw(self):
        TelevideoPageSnapshot.objects.create(
            section="giochi",
            page=690,
            subpage="01",
            label="Indice lotto e lotterie",
            title="Indice lotto e lotterie",
            content_kind="index",
            raw_text=(
                "GUIDA TV 501\n"
                "                         GUIDA TV   501\n"
                "                         MAGAZINE   545\n"
                "       ESTRAZIONI\n"
                "    DEL 30/05/2026                 691\n"
                "    NUOVO SUPERENALOTTO SUPERSTAR  696\n"
            ),
            sort_order=1,
        )

        response = self.client.get(reverse("news:games"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "televideo-index-item")
        self.assertContains(response, "NUOVO SUPERENALOTTO SUPERSTAR")
        self.assertNotContains(response, "ESTRAZIONI")
        self.assertNotContains(response, "pag.")
        self.assertNotContains(response, "Pagina 690")
        self.assertNotContains(response, "raw-block")

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
        self.assertEqual(data["selected_date"], "")
        self.assertIsNone(data["selected"])

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
        self.assertContains(response, "italy-map")
        self.assertContains(response, "data-meteo-map")
        self.assertNotContains(response, "data-capitals-map")
        self.assertNotContains(response, "capital-marker")
        self.assertNotContains(response, "Televideo Regionale - Lombardia")

    @override_settings(OPENWEATHER_API_KEY="test-key")
    def test_region_detail(self):
        OpenWeatherCity.objects.create(
            city="Roma",
            region_slug="lazio",
            query="Roma,IT",
            condition="Sereno",
            temp=22,
            fetched_at=timezone.now(),
        )
        response = self.client.get(reverse("news:region", kwargs={"region_slug_value": "lazio"}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Meteo capoluoghi - Lazio")
        self.assertContains(response, "Roma")
        self.assertContains(response, "OpenWeatherMap")

    def test_region_pharmacy_page_removes_televideo_border_artifacts(self):
        TelevideoPageSnapshot.objects.create(
            section="regioni",
            region="Piemonte",
            page=690,
            subpage="01",
            label="Farmacie",
            title="Farmacie",
            content_kind="table",
            raw_text=(
                "Farmacie\n"
                "ùppppppppppppppppppppppppppp0\n"
                "        ùppppppppppppppppppppppppppp0\n"
                "       TORINO\n"
                " 691   di turno\n"
                " 692   notturne e 24 ore\n"
                " 693   ALESSANDRIA, ASTI, BIELLA\n"
                " 694   CUNEO, NOVARA, VERCELLI\n"
            ),
            sort_order=1,
        )

        response = self.client.get(reverse("news:region", kwargs={"region_slug_value": "piemonte"}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "televideo-index-item")
        self.assertContains(response, "di turno")
        self.assertContains(response, "notturne e 24 ore")
        self.assertNotContains(response, "ùpp")
        self.assertNotContains(response, "pag.")
        self.assertNotContains(response, "Pagina 690")
        self.assertNotContains(response, "raw-block")

    def test_region_pharmacy_page_handles_split_page_labels_without_page_refs(self):
        TelevideoPageSnapshot.objects.create(
            section="regioni",
            region="Lombardia",
            page=690,
            subpage="01",
            label="Farmacie",
            title="Farmacie",
            content_kind="table",
            raw_text=(
                "Farmacie\n"
                "ùpppppppppppppppppppppppppp0\n"
                "di turno\n"
                "pag. 691\n"
                "notturne e 24 ore\n"
                "pag. 692\n"
                "BERGAMO, BRESCIA, COMO,\n"
                "pag. 693\n"
                "MANTOVA, MONZA, PAVIA,\n"
                "pag. 694\n"
            ),
            sort_order=1,
        )

        response = self.client.get(reverse("news:region", kwargs={"region_slug_value": "lombardia"}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "di turno")
        self.assertContains(response, "BERGAMO, BRESCIA, COMO,")
        self.assertNotContains(response, "pag.")
        self.assertNotContains(response, "Pagina 690")
        self.assertNotContains(response, "ùpp")

    def test_region_culturambiente_index_removes_split_pages_and_artifacts(self):
        TelevideoPageSnapshot.objects.create(
            section="regioni",
            region="Lombardia",
            page=575,
            subpage="01",
            label="Culturambiente",
            title="Culturambiente",
            content_kind="article",
            raw_text=(
                "Culturambiente\n"
                "576 VIAGGIO NEI BENI DEL FAI\n"
                "TOURING CLUB ITALIANO\n"
                "pag. 579\n"
                "AGENDA VERDE\n"
                "pag. 582\n"
                "I PARCHI DELLA REGIONE\n"
                "pag. 585\n"
                "sssssssssssssssssssssssssss\n"
            ),
            sort_order=1,
        )

        response = self.client.get(reverse("news:region", kwargs={"region_slug_value": "lombardia"}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "VIAGGIO NEI BENI DEL FAI")
        self.assertContains(response, "TOURING CLUB ITALIANO")
        self.assertContains(response, "AGENDA VERDE")
        self.assertNotContains(response, "pag.")
        self.assertNotContains(response, "Pagina 575")
        self.assertNotContains(response, "ssss")

    @override_settings(OPENWEATHER_API_KEY="test-key")
    def test_weather_page_uses_openweather_only_when_key_configured(self):
        OpenWeatherCity.objects.create(
            city="Roma",
            region_slug="lazio",
            query="Roma,IT",
            condition="Sereno",
            temp=22,
            fetched_at=timezone.now(),
        )
        TelevideoPageSnapshot.objects.create(
            section="meteo",
            page=700,
            subpage="01",
            label="Meteo Televideo",
            title="Meteo Televideo",
            content_kind="article",
            raw_text="SENTINEL_METEO_TELEVIDEO",
            sort_order=1,
        )

        response = self.client.get(reverse("news:weather"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "data-capitals-map")
        self.assertContains(response, "italy-map--capitals")
        self.assertContains(response, "capital-marker")
        self.assertContains(response, "Roma")
        self.assertContains(response, "22")
        self.assertContains(response, "OpenWeatherMap")
        self.assertNotContains(response, "data-meteo-map")
        self.assertNotContains(response, "SENTINEL_METEO_TELEVIDEO")
        self.assertNotContains(response, "weather-zone-grid")
        self.assertNotContains(response, "temperature-grid")

    def test_atom_feed_returns_valid_xml(self):
        response = self.client.get(reverse("news:atom_feed"))
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'<?xml version="1.0" encoding="UTF-8"?>', response.content)
        self.assertContains(response, "<feed xmlns=")

    def test_invalid_section_returns_404(self):
        response = self.client.get("/nonexistent/")
        self.assertEqual(response.status_code, 404)

    def test_page_not_found_handler(self):
        response = self.client.get("/this-does-not-exist/")
        self.assertEqual(response.status_code, 404)
