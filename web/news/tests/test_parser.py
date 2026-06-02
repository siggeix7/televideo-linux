from django.test import SimpleTestCase

from news.formatters import parse_televideo_card
from news.services.parser import parse_article_content


def item_page(item: dict) -> str:
    return f"{item['page']}-{item['end_page']}" if item.get("end_page") else item["page"]


class TelevideoParserTests(SimpleTestCase):
    def test_rejects_left_truncated_article_fragments(self):
        content = "\n".join(
            [
                "re di soccorso.",
                "ovane italiano di 20 anni,residen-",
                "Liguria, e' cosciente ma ha un ar-.",
            ]
        )

        self.assertIsNone(parse_article_content(content, "Ultime News"))

    def test_parses_generic_index_entries(self):
        content = "\n".join(
            [
                "Indice lavoro",
                "INFO GAZZETTA UFFICIALE 466",
                "SICUREZZA SUL LAVORO 467",
                "AGENZIE PER IL LAVORO 468",
                "RAI RADIO TECHETE' 543",
                "TUTTA LA GAZZETTA SU: www.ipzs.it",
                "Scienza e Salute p.475",
            ]
        )

        parsed = parse_televideo_card(content, title="Indice lavoro", label="Indice lavoro", content_kind="index")

        self.assertEqual([item_page(item) for item in parsed["index_items"]], ["466", "467", "468", "543", "475"])
        self.assertEqual(parsed["index_items"][0]["label"], "INFO GAZZETTA UFFICIALE")
        self.assertEqual(parsed["index_items"][3]["label"], "RAI RADIO TECHETE'")
        self.assertIn("TUTTA LA GAZZETTA", parsed["paragraphs"][0])

    def test_parses_programmi_criptati_groups(self):
        content = "\n".join(
            [
                "Programmi criptati",
                "I programmi della RAI",
                "vengono trasmessi in tecnica digitale",
                "SETTIMANA DAL 31/05 AL 06/06",
                "RAI 1",
                "MERCOLEDI 03 GIUGNO",
                "Calcio: Uefa Friendly Match 2026",
                "        Lussemburgo - Italia",
                "RAI 3",
                "SABATO 06 GIUGNO",
                "Film: Mediterranee",
            ]
        )

        parsed = parse_televideo_card(content, title="Programmi criptati", label="Programmi criptati", content_kind="schedule")

        self.assertEqual(len(parsed["schedule_groups"]), 2)
        self.assertEqual(parsed["schedule_groups"][0]["title"], "RAI 1 · MERCOLEDI 03 GIUGNO")
        self.assertEqual(parsed["schedule_groups"][0]["items"][0], "Calcio: Uefa Friendly Match 2026 Lussemburgo - Italia")
        self.assertIn("I programmi della RAI", parsed["paragraphs"][0])

    def test_descriptive_schedule_falls_back_to_paragraphs(self):
        content = "\n".join(
            [
                "FILM CLUB",
                "Ogni venerdi Evie e Noa condividono la",
                "visione di un classico del cinema.",
                "Serie in 6 episodi",
            ]
        )

        parsed = parse_televideo_card(content, title="FILM CLUB", label="RaiPlay", content_kind="schedule")

        self.assertFalse(parsed["index_items"])
        self.assertFalse(parsed["schedule_groups"])
        self.assertEqual(parsed["paragraphs"][0], "Ogni venerdi Evie e Noa condividono la visione di un classico del cinema. Serie in 6 episodi")

    def test_regional_pharmacy_index_removes_televideo_border_artifacts(self):
        content = "\n".join(
            [
                "Farmacie",
                "ùppppppppppppppppppppppppppp0",
                "        ùppppppppppppppppppppppppppp0",
                "       TORINO",
                " 691   di turno",
                " 692   notturne e 24 ore",
                " 693   ALESSANDRIA, ASTI, BIELLA",
                " 694   CUNEO, NOVARA, VERCELLI",
            ]
        )

        parsed = parse_televideo_card(content, title="Farmacie", label="Farmacie", content_kind="table")

        self.assertEqual([item_page(item) for item in parsed["index_items"]], ["691", "692", "693", "694"])
        self.assertEqual(parsed["index_items"][0]["label"], "di turno")
        self.assertFalse(parsed["paragraphs"])
        self.assertNotIn("ùpp", str(parsed))

    def test_travel_index_parses_page_word_links_and_drops_televideo_notes(self):
        content = "\n".join(
            [
                "Indice in viaggio",
                "AVVISI VIAGGIARE SICURI 434>440",
                "    STRADE D'ITALIA - ITINERARI   443",
                "    COS'E' IL FAI                 445  j",
                "    CAPITALE CULTURA:",
                "     A SPASSO PER... a pagina 408 del",
                "         TELEVIDEO REGIONALE RAI3",
            ]
        )

        parsed = parse_televideo_card(content, title="Indice in viaggio", label="Indice in viaggio", content_kind="index")

        self.assertEqual([item_page(item) for item in parsed["index_items"]], ["434-440", "443", "445", "408"])
        self.assertEqual(parsed["index_items"][-1]["label"], "A SPASSO PER...")
        self.assertFalse(parsed["paragraphs"])
        self.assertNotIn("TELEVIDEO REGIONALE", str(parsed))

    def test_games_index_is_deduplicated_and_structured(self):
        content = "\n".join(
            [
                "Indice lotto e lotterie",
                "GUIDA TV 501",
                "                         GUIDA TV   501",
                "                         MAGAZINE   545",
                "                         RADIO RAI  535",
                "       ESTRAZIONI",
                "    DEL 30/05/2026                 691",
                "    DEL 29/05/2026                 692",
                "    NUOVO SUPERENALOTTO SUPERSTAR  696",
            ]
        )

        parsed = parse_televideo_card(content, title="Indice lotto e lotterie", label="Indice lotto e lotterie", content_kind="index")

        self.assertEqual([item_page(item) for item in parsed["index_items"]], ["501", "545", "535", "691", "692", "696"])
        self.assertFalse(parsed["paragraphs"])
        self.assertEqual([item["label"] for item in parsed["index_items"]].count("GUIDA TV"), 1)

    def test_unparsed_table_does_not_fallback_to_raw_paragraphs(self):
        content = "\n".join(
            [
                "NUOVO",
                "CONCORSO N.87 30/05/2026",
                "COMBINAZIONE nessun sei",
                "N.ro SuperStar 56 euro 25.859,69",
            ]
        )

        parsed = parse_televideo_card(content, title="Ultime notizie", label="SuperEnalotto", content_kind="table")

        self.assertFalse(parsed["has_content"])
        self.assertFalse(parsed["paragraphs"])

    def test_split_page_labels_are_parsed_as_index_items(self):
        content = "\n".join(
            [
                "Culturambiente",
                "576 VIAGGIO NEI BENI DEL FAI",
                "TOURING CLUB ITALIANO",
                "pag. 579",
                "AGENDA VERDE",
                "pag. 582",
                "sssssssssssssssssssssssssss",
            ]
        )

        parsed = parse_televideo_card(content, title="Culturambiente", label="Culturambiente", content_kind="article")

        self.assertEqual(
            [item["label"] for item in parsed["index_items"]],
            ["VIAGGIO NEI BENI DEL FAI", "TOURING CLUB ITALIANO", "AGENDA VERDE"],
        )
        self.assertFalse(parsed["paragraphs"])
        self.assertNotIn("pag.", str(parsed))
        self.assertNotIn("ssss", str(parsed))
