from __future__ import annotations

BASE_URLS = (
    "https://www.televideo.rai.it/televideo/pub/",
    "https://www.servizitelevideo.rai.it/televideo/pub/",
)
RSS_PATH = "rss101.xml"
TEXT_PATH = "solotesto.jsp"
CATEGORY_INDEX_PAGE = "104"
SUPERENALOTTO_PAGE = "696"
LOTTO_PAGES = (691, 692)
USER_AGENT = "televideo-linux-web/1.0"
GOOGLE_TRANSLATE_URL = "https://translate.googleapis.com/translate_a/single"
MYMEMORY_URL = "https://api.mymemory.translated.net/get"
SUMMARY_SENTENCES = 2
SUMMARY_MAX_CHARS = 360

CATEGORY_LABELS = {
    101: ("rss101", "Ultim'Ora", "Novissima Hora", "Breaking News"),
    103: ("p103", "Prima", "Prima Pagina", "Front Page"),
    105: ("p105", "Edicola", "Acta Diurna", "Press Review"),
    108: ("p108", "Ultim'Ora Flash", "Novissima Brevia", "News Flash"),
    109: ("p109", "Ultime News", "Novissima", "Latest News"),
    110: ("p110", "Attualita'", "Res Hodiernae", "Current Affairs"),
    120: ("p120", "Politica", "Politica", "Politics"),
    130: ("p130", "Economia", "Oeconomia", "Economy"),
    140: ("p140", "Dall'Italia", "Ex Italia", "Italy"),
    150: ("p150", "Dal Mondo", "Ex Mundo", "World"),
    160: ("p160", "Culture", "Culturae", "Culture"),
    170: ("p170", "Cittadini", "Cives", "Citizens"),
    180: ("p180", "Focus", "Inquisitio", "Focus"),
    190: ("p190", "Motori", "Currus", "Motors"),
    201: ("p201", "Calcio", "Pediludium", "Football"),
    260: ("p260", "Altri Sport", "Alii Ludi", "Other Sports"),
    299: ("p299", "Brevi Sport", "Breves Ludi", "Sports Briefs"),
}
COMPOSITE_CATEGORY_PAGES = {103, 105, 110, 170, 180, 190}
FLASH_NEWS_PAGES = {108, 109}
EXTRA_CATEGORY_PAGES = (201, 260, 299)

REGIONS = {
    "abruzzo": "Abruzzo", "altoadige": "Altoadige", "alto-adige": "Altoadige",
    "basilicata": "Basilicata", "calabria": "Calabria", "campania": "Campania",
    "emilia": "Emilia", "emilia-romagna": "Emilia",
    "friuli": "Friuli", "friuli-venezia-giulia": "Friuli",
    "lazio": "Lazio", "liguria": "Liguria", "lombardia": "Lombardia",
    "marche": "Marche", "molise": "Molise", "piemonte": "Piemonte",
    "puglia": "Puglia", "sardegna": "Sardegna", "sicilia": "Sicilia",
    "toscana": "Toscana", "trentino": "Trentino", "umbria": "Umbria",
    "aosta": "Aosta", "valle-aosta": "Aosta", "veneto": "Veneto",
}

REGION_CHOICES = (
    "Abruzzo", "Altoadige", "Basilicata", "Calabria", "Campania",
    "Emilia", "Friuli", "Lazio", "Liguria", "Lombardia",
    "Marche", "Molise", "Piemonte", "Puglia", "Sardegna",
    "Sicilia", "Toscana", "Trentino", "Umbria", "Aosta", "Veneto",
)

SECTION_DEFINITIONS = {
    "tv": {
        "title": "Guida TV",
        "eyebrow": "Rai Televideo 501-535",
        "lede": "Programmi TV, prima serata, film del giorno, RaiPlay, Rai Sport, radio e dati Auditel.",
        "seal": "TV",
        "pages": (
            (501, "Indice guida TV", "index"), (514, "Film oggi", "schedule"),
            (515, "Prima serata", "schedule"), (517, "Programmi criptati", "schedule"),
            (518, "Rai Sport HD", "schedule"), (519, "Rai Sport", "schedule"),
            (520, "Rai Movie", "schedule"), (521, "Rai Premium", "schedule"),
            (522, "Rai Yoyo", "schedule"), (523, "Rai 4", "schedule"),
            (524, "Rai Gulp", "schedule"), (525, "Rai 5", "schedule"),
            (526, "Rai Storia", "schedule"), (527, "Rai Scuola", "schedule"),
            (528, "RaiPlay", "schedule"), (530, "Auditel", "index"),
            (531, "Auditel percentuali", "table"), (532, "Auditel ascoltatori", "table"),
            (533, "Programmi piu visti", "table"), (535, "Radio", "index"),
            (546, "Magazine TV", "article"),
        ),
    },
    "cultura": {
        "title": "Cultura, Libri, Cinema e Teatro",
        "eyebrow": "Rai Televideo 561-600",
        "lede": "Recensioni, libri, film, teatro, concerti, eventi e mostre recuperati dalle rubriche culturali.",
        "seal": "CU",
        "pages": (
            (561, "Indice libri e cultura", "index"), (562, "Le pagine da leggere", "article"),
            (564, "Lo scaffale", "article"), (565, "All'ordine del giorno", "article"),
            (566, "Centro libro e lettura", "article"), (567, "Cinema", "index"),
            (568, "Film in produzione", "article"), (569, "Film piu visti", "table"),
            (570, "Film in sala - commedia", "article"), (571, "Film in sala - drammatico", "article"),
            (572, "Film in sala - documentario", "article"), (573, "Film in sala - azione", "article"),
            (574, "Film in sala - thriller", "article"), (575, "Film in arrivo", "article"),
            (576, "Teatri", "index"), (577, "Teatri stabili", "schedule"),
            (580, "Teatri lirici", "schedule"), (583, "Concerti", "article"),
            (595, "Eventi e mostre", "index"), (596, "Capitale cultura eventi", "article"),
            (597, "Capitale cultura luoghi", "article"), (598, "Mostre d'arte", "article"),
            (600, "Giulio Regeni", "article"), (427, "A teatro questa settimana", "article"),
            (428, "Film della settimana", "article"),
        ),
    },
    "ambiente": {
        "title": "Ambiente, Scienza e Salute",
        "eyebrow": "Rai Televideo 450-483",
        "lede": "Energie rinnovabili, sostenibilita, agenda verde, ricerca, scienza, salute e istituti scientifici.",
        "seal": "EA",
        "pages": (
            (450, "Indice ambiente", "index"), (451, "Energie rinnovabili", "article"),
            (452, "Riduci, riusa, ricicla", "article"), (453, "Sostenibilita ambientale", "article"),
            (454, "Agenda verde", "article"), (456, "Lo sapevate che", "article"),
            (457, "ENEA", "article"), (458, "INGV", "article"),
            (459, "Stazione Zoologica", "article"), (477, "Scienza e salute", "article"),
            (481, "CNR", "article"), (483, "INAF", "article"),
            (635, "ASviS", "article"),
        ),
    },
    "lavoro": {
        "title": "Lavoro e Concorsi",
        "eyebrow": "Rai Televideo 465-470",
        "lede": "Concorsi, Gazzetta Ufficiale, sicurezza sul lavoro, formazione, agenzie ed eventi occupazionali.",
        "seal": "LA",
        "pages": (
            (465, "Indice lavoro", "index"), (466, "Gazzetta e concorsi", "article"),
            (467, "Sicurezza sul lavoro", "article"), (468, "Agenzie per il lavoro", "article"),
            (469, "Formazione", "article"), (470, "Eventi per il lavoro", "article"),
        ),
    },
    "sport": {
        "title": "Sport e Risultati",
        "eyebrow": "Rai Televideo 200-299",
        "lede": "Risultati, classifiche, calendari, club di Serie A e B, altri sport e brevi sportive.",
        "seal": "SP",
        "pages": (
            (200, "Indice sport", "index"), (202, "Serie A risultati", "table"),
            (203, "Serie A classifica", "table"), (204, "Serie A calendario", "schedule"),
            (209, "Serie B playoff", "schedule"), (229, "Brevi calcio", "article"),
            (230, "Club Serie A", "article"), (250, "Club Serie B", "article"),
            (260, "Altri sport", "index"), (261, "Tennis", "article"),
            (263, "Ciclismo", "article"), (266, "Basket", "article"),
            (268, "Motori", "article"), (299, "Brevi sport", "article"),
        ),
    },
    "meteo": {
        "title": "Meteo, Mari e Venti",
        "eyebrow": "Rai Televideo 700-719",
        "lede": "Previsioni per versanti, temperature, aeroporti, mari, venti e sicurezza in mare.",
        "seal": "MT",
        "pages": (
            (700, "Indice meteo", "index"), (702, "Alpi e Valpadana oggi", "weather"),
            (703, "Alpi e Valpadana domani", "weather"), (704, "Ligure e Tirrenico oggi", "weather"),
            (705, "Ligure e Tirrenico domani", "weather"), (706, "Adriatico e Ionico oggi", "weather"),
            (707, "Adriatico e Ionico domani", "weather"), (708, "Tirreno meridionale e isole oggi", "weather"),
            (709, "Tirreno meridionale e isole domani", "weather"), (710, "Prossimi giorni", "weather"),
            (711, "Temperature Italia", "table"), (712, "Temperature estero", "table"),
            (713, "Aeroporti nord-centro", "weather"), (714, "Aeroporti sud-isole", "weather"),
            (715, "Mari situazione", "weather"), (716, "Mari previsione", "weather"),
            (717, "Venti", "weather"), (719, "Guardia Costiera", "article"),
        ),
    },
    "viaggi": {
        "title": "Viaggi, Turismo e Sicurezza",
        "eyebrow": "Rai Televideo 433-448",
        "lede": "Avvisi per viaggiare sicuri, itinerari, FAI, Touring Club, borghi e informazioni utili.",
        "seal": "VI",
        "pages": (
            (433, "Indice in viaggio", "index"), (434, "Viaggiare sicuri", "article"),
            (435, "Avvisi viaggio", "article"), (436, "Avvisi viaggio", "article"),
            (437, "Avvisi viaggio", "article"), (438, "Avvisi viaggio", "article"),
            (439, "Regole di viaggio", "article"), (443, "Strade d'Italia", "article"),
            (444, "Belpaese", "article"), (445, "FAI", "article"),
            (446, "Beni FAI", "article"), (447, "Touring Club", "article"),
            (448, "Borghi Bandiera Arancione", "article"), (596, "Capitale cultura eventi", "article"),
            (597, "Capitale cultura luoghi", "article"), (719, "Sicurezza in mare", "article"),
        ),
    },
    "giochi": {
        "title": "Giochi e Estrazioni",
        "eyebrow": "Rai Televideo 690-696",
        "lede": "SuperEnalotto, Lotto e archivio delle ultime estrazioni salvate nel database.",
        "seal": "90",
        "pages": (
            (690, "Indice lotto e lotterie", "index"), (691, "Lotto ultima estrazione", "table"),
            (692, "Lotto estrazione precedente", "table"), (696, "SuperEnalotto", "table"),
        ),
    },
}

REGIONAL_SECTION = {
    "title": "Televideo Regionale",
    "eyebrow": "Rai Televideo regionale 300",
    "lede": "Notizie, eventi, cinema, teatri, gusto, viaggi, societa e servizi dalle pagine regionali Rai.",
    "seal": "R3",
    "pages": (
        (300, "Indice regionale", "index"), (101, "Ultim'ora regionale", "article"),
        (103, "Prima regionale", "article"), (301, "Sport regione", "index"),
        (407, "Carnet", "article"), (408, "A spasso per", "article"),
        (409, "Festival", "article"), (411, "Musei", "article"),
        (413, "A tavola", "article"), (418, "Ricettario", "article"),
        (420, "In viaggio", "index"), (421, "Viabilita regionale", "table"),
        (430, "Cinema", "index"), (431, "Cinema locali", "schedule"),
        (450, "Teatri", "index"), (451, "Teatri locali", "schedule"),
        (498, "Istituzioni", "article"), (520, "Societa", "article"),
        (575, "Culturambiente", "article"), (690, "Farmacie", "table"),
    ),
}
