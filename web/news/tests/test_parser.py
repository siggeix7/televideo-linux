from django.test import SimpleTestCase

from news.services.parser import parse_article_content


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
