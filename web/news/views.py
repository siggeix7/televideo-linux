from __future__ import annotations

from django.conf import settings
from django.db.models import Case, Count, IntegerField, Q, Value, When
from django.db import connection
from django.http import Http404, JsonResponse
from django.shortcuts import render
from django.template import TemplateDoesNotExist
from django.urls import reverse
from django.utils import timezone

from .formatters import (
    merge_snapshot_pages,
    parse_article_multipage,
    parse_auditel,
    parse_film_schedule,
    parse_lotto_results,
    parse_match_results,
    parse_round_info,
    parse_serie_a_standings,
    parse_temperatures,
    parse_weather_observation,
)
from .models import Category, LottoDraw, NewsItem, SuperEnalottoDraw, TelevideoPageSnapshot
from .services import (
    REGION_CHOICES,
    SECTION_DEFINITIONS,
    normalize_region,
    refresh_if_stale,
    refresh_section_if_stale,
    region_slug,
    section_definition,
    translate_lines,
    translate_text,
    medieval_latin_style,
)


LANGUAGES = {
    "la": "Latino",
    "it": "Italiano",
    "en": "English",
}

HIDDEN_CATEGORY_CODES = {"p401", "p613", "p700", "p711"}

NAVIGATION = (
    ("home", "nav_home", "news:home"),
    ("tv", "nav_tv", "news:tv"),
    ("cultura", "nav_culture", "news:culture"),
    ("ambiente", "nav_environment", "news:environment"),
    ("lavoro", "nav_work", "news:work"),
    ("sport", "nav_sport", "news:sport"),
    ("meteo", "nav_weather", "news:weather"),
    ("viaggi", "nav_travel", "news:travel"),
    ("giochi", "nav_games", "news:games"),
    ("regioni", "nav_regions", "news:regions"),
)

UI_TEXT = {
    "it": {
        "html_lang": "it",
        "site_name": "Televideo News",
        "eyebrow": "Rai Televideo RSS 101 e pagina 104",
        "title": "Televideo News",
        "lede": "Notizie reali da Rai Televideo, archiviate automaticamente e organizzate per categoria.",
        "nav_home": "Cronaca",
        "nav_tv": "TV",
        "nav_culture": "Cultura",
        "nav_environment": "Ambiente",
        "nav_work": "Lavoro",
        "nav_sport": "Sport",
        "nav_weather": "Meteo",
        "nav_travel": "Viaggi",
        "nav_games": "Giochi",
        "nav_regions": "Regioni",
        "language_nav_label": "Lingua dell'interfaccia e delle notizie",
        "categories_title": "Categorie",
        "news_link": "Cronaca",
        "super_link": "SuperEnalotto",
        "all_categories": "Tutte",
        "search_placeholder": "Cerca in titoli, testi e categorie...",
        "status_label": "Stato aggiornamento",
        "loading": "Carico le ultime notizie...",
        "last_reading": "Ultima lettura",
        "waiting": "in attesa",
        "source_label": "Fonte",
        "data_provider": "Rai Televideo",
        "last_update_label": "Ultimo aggiornamento",
        "empty_title": "Le pergamene sono ancora vuote",
        "empty_message": "Il feed Rai non ha risposto oppure il job di aggiornamento non ha ancora popolato il database.",
        "section_empty_title": "Nessun contenuto disponibile",
        "section_empty_message": "La sezione non ha ancora risposto oppure la cache non e' stata popolata.",
        "load_error_title": "Errore di caricamento",
        "unknown_error": "Errore sconosciuto",
        "timeout_error": "Timeout: il server non risponde. Nuovo tentativo in corso...",
        "no_search_results_title": "Nessun risultato",
        "no_search_results_message": "Nessuna notizia contiene \"{query}\".",
        "card_ribbon": "Notizia",
        "source_prefix": "Titolo originale:",
        "category_prefix": "Categoria:",
        "source_link": "Fonte Rai",
        "open_televideo": "Apri su Televideo",
        "open_archive": "Apri archivio",
        "page_label": "Pagina",
        "subpages_label": "sottopagine",
        "previous_page": "Precedenti",
        "next_page": "Successive",
        "page_status": "Pagina {page} di {pages}",
        "super_title": "Archivio SuperEnalotto",
        "super_lede": "Ultima combinazione dalla pagina 696 di Rai Televideo, salvata nello storico SQLite.",
        "draw_label": "Concorso",
        "draw_date_label": "Data estrazione",
        "numbers_label": "Combinazione vincente",
        "jolly_label": "Numero Jolly",
        "superstar_label": "Numero SuperStar",
        "jackpot_label": "Jackpot",
        "prize_pool_label": "Montepremi",
        "history_label": "Storico disponibile",
        "trend_label": "Andamento Jackpot e Montepremi",
        "select_date": "Seleziona data",
        "no_draws": "Nessuna estrazione salvata nello storico.",
        "super_latest_title": "Ultima estrazione SuperEnalotto",
        "latest_news": "Ultime notizie",
        "archive_super": "Archivio SuperEnalotto",
        "lotto_title": "Lotto",
        "extraction_date_label": "Estrazione del",
        "film_schedule_title": "Film in programmazione",
        "auditel_title": "Dati Auditel",
        "channel_program_label": "Canale/Programma",
        "share_label": "Share %",
        "viewers_label": "Spettatori",
        "director_prefix": "di",
        "cast_prefix": "con",
        "standings_title": "Classifica Serie A",
        "latest_results_title": "Ultimi risultati",
        "position_label": "#",
        "team_label": "Squadra",
        "points_label": "Pt",
        "wins_label": "V",
        "draws_label": "P",
        "losses_label": "S",
        "goals_for_label": "GF",
        "goals_against_label": "GS",
        "wind_label": "Vento",
        "visibility_label": "Visibilita",
        "region_select_label": "Seleziona regione",
        "footer_prefix": "Televideo News",
        "footer_license": "MIT License",
        "footer_data_prefix": "Dati forniti da",
        "back_home": "Torna alla cronaca",
        "error_eyebrow": "Errore {code}",
        "error_404_title": "Pagina non trovata",
        "error_404_message": "La pagina che cerchi non esiste o e' stata spostata.",
        "error_500_title": "Errore del server",
        "error_500_message": "Un imprevisto ha interrotto la lettura dei dati. Riprova tra poco.",
        "updated": "Notizie aggiornate in {language}",
        "date_unavailable": "data non disponibile",
        "error_prefix": "Errore durante l'aggiornamento:",
    },
    "en": {
        "html_lang": "en",
        "site_name": "Televideo News",
        "eyebrow": "Rai Televideo RSS 101 and page 104",
        "title": "Televideo News",
        "lede": "Real Rai Televideo news, automatically archived and grouped by category.",
        "nav_home": "Chronicle",
        "nav_tv": "TV",
        "nav_culture": "Culture",
        "nav_environment": "Environment",
        "nav_work": "Work",
        "nav_sport": "Sport",
        "nav_weather": "Weather",
        "nav_travel": "Travel",
        "nav_games": "Games",
        "nav_regions": "Regions",
        "language_nav_label": "Interface and news language",
        "categories_title": "Categories",
        "news_link": "Chronicle",
        "super_link": "SuperEnalotto",
        "all_categories": "All",
        "search_placeholder": "Search titles, text and categories...",
        "status_label": "Update status",
        "loading": "Loading the latest news...",
        "last_reading": "Last reading",
        "waiting": "waiting",
        "source_label": "Source",
        "data_provider": "Rai Televideo",
        "last_update_label": "Last update",
        "empty_title": "The parchments are still empty",
        "empty_message": "The Rai feed did not answer yet, or the updater has not populated the database.",
        "section_empty_title": "No content available",
        "section_empty_message": "This section has not answered yet, or the cache has not been populated.",
        "load_error_title": "Loading error",
        "unknown_error": "Unknown error",
        "timeout_error": "Timeout: the server is not responding. Retrying...",
        "no_search_results_title": "No results",
        "no_search_results_message": "No news item contains \"{query}\".",
        "card_ribbon": "News",
        "source_prefix": "Original title:",
        "category_prefix": "Category:",
        "source_link": "Rai source",
        "open_televideo": "Open on Televideo",
        "open_archive": "Open archive",
        "page_label": "Page",
        "subpages_label": "subpages",
        "previous_page": "Previous",
        "next_page": "Next",
        "page_status": "Page {page} of {pages}",
        "super_title": "SuperEnalotto Archive",
        "super_lede": "Latest draw from Rai Televideo page 696, stored in the SQLite history.",
        "draw_label": "Draw",
        "draw_date_label": "Draw date",
        "numbers_label": "Winning numbers",
        "jolly_label": "Jolly number",
        "superstar_label": "SuperStar number",
        "jackpot_label": "Jackpot",
        "prize_pool_label": "Prize pool",
        "history_label": "Available history",
        "trend_label": "Jackpot and prize pool trend",
        "select_date": "Select date",
        "no_draws": "No draws saved in history yet.",
        "super_latest_title": "Latest SuperEnalotto draw",
        "latest_news": "Latest news",
        "archive_super": "SuperEnalotto archive",
        "lotto_title": "Lotto",
        "extraction_date_label": "Draw of",
        "film_schedule_title": "Scheduled films",
        "auditel_title": "Auditel data",
        "channel_program_label": "Channel/Program",
        "share_label": "Share %",
        "viewers_label": "Viewers",
        "director_prefix": "by",
        "cast_prefix": "with",
        "standings_title": "Serie A standings",
        "latest_results_title": "Latest results",
        "position_label": "#",
        "team_label": "Team",
        "points_label": "Pts",
        "wins_label": "W",
        "draws_label": "D",
        "losses_label": "L",
        "goals_for_label": "GF",
        "goals_against_label": "GA",
        "wind_label": "Wind",
        "visibility_label": "Visibility",
        "region_select_label": "Select region",
        "footer_prefix": "Televideo News",
        "footer_license": "MIT License",
        "footer_data_prefix": "Data provided by",
        "back_home": "Back to the chronicle",
        "error_eyebrow": "Error {code}",
        "error_404_title": "Page not found",
        "error_404_message": "The page you are looking for does not exist or has been moved.",
        "error_500_title": "Server error",
        "error_500_message": "An unexpected problem interrupted the data reading. Try again shortly.",
        "updated": "News updated in {language}",
        "date_unavailable": "date unavailable",
        "error_prefix": "Update error:",
    },
    "la": {
        "html_lang": "la",
        "site_name": "Nuntia Televidei",
        "eyebrow": "Rai Televideo RSS CI et pagina CIV",
        "title": "Nuntia Televidei",
        "lede": "Notitiae verae ex Rai Televideo, in archivio servatae et per categorias dispositae.",
        "nav_home": "Chronica",
        "nav_tv": "TV",
        "nav_culture": "Cultura",
        "nav_environment": "Ambitus",
        "nav_work": "Labor",
        "nav_sport": "Ludi",
        "nav_weather": "Tempestas",
        "nav_travel": "Itinera",
        "nav_games": "Sortes",
        "nav_regions": "Regiones",
        "language_nav_label": "Lingua interfaciei et nuntiorum",
        "categories_title": "Categoriae",
        "news_link": "Chronica",
        "super_link": "SuperEnalotto",
        "all_categories": "Omnes",
        "search_placeholder": "Quaere in titulis, textibus et categoriis...",
        "status_label": "Status renovationis",
        "loading": "Novissima nuntia colligo...",
        "last_reading": "Ultima lectio",
        "waiting": "exspectatur",
        "source_label": "Fons",
        "data_provider": "Rai Televideo",
        "last_update_label": "Ultima renovatio",
        "empty_title": "Pergamenae adhuc vacuae sunt",
        "empty_message": "Fons Rai nondum respondit aut minister renovandi datorum tabulam nondum implevit.",
        "section_empty_title": "Nullum contentum praesto est",
        "section_empty_message": "Haec sectio nondum respondit aut memoria temporaria nondum impleta est.",
        "load_error_title": "Error onerandi",
        "unknown_error": "Error ignotus",
        "timeout_error": "Tempus exactum est: minister non respondet. Iterum temptatur...",
        "no_search_results_title": "Nullus exitus",
        "no_search_results_message": "Nullum nuntium continet \"{query}\".",
        "card_ribbon": "Nuntium",
        "source_prefix": "Titulus primus:",
        "category_prefix": "Categoria:",
        "source_link": "Fons Rai",
        "open_televideo": "Aperi in Televideo",
        "open_archive": "Aperi archivum",
        "page_label": "Pagina",
        "subpages_label": "subpaginae",
        "previous_page": "Priora",
        "next_page": "Sequentia",
        "page_status": "Pagina {page} ex {pages}",
        "super_title": "Archivum SuperEnalotto",
        "super_lede": "Ultima sortitio ex pagina DCXCVI Rai Televideo, in memoria SQLite servata.",
        "draw_label": "Concursus",
        "draw_date_label": "Dies sortitionis",
        "numbers_label": "Numeri victores",
        "jolly_label": "Numerus Jolly",
        "superstar_label": "Numerus SuperStar",
        "jackpot_label": "Praemium maximum",
        "prize_pool_label": "Mons praemiorum",
        "history_label": "Historia servata",
        "trend_label": "Cursus praemii maximi et montis praemiorum",
        "select_date": "Diem elige",
        "no_draws": "Nulla sortitio adhuc servata est.",
        "super_latest_title": "Ultima sortitio SuperEnalotto",
        "latest_news": "Novissima",
        "archive_super": "Archivum SuperEnalotto",
        "lotto_title": "Lotto",
        "extraction_date_label": "Sortitio diei",
        "film_schedule_title": "Pelliculae in ordine",
        "auditel_title": "Data Auditel",
        "channel_program_label": "Canalis/programma",
        "share_label": "Pars %",
        "viewers_label": "Spectatores",
        "director_prefix": "a",
        "cast_prefix": "cum",
        "standings_title": "Tabula Serie A",
        "latest_results_title": "Exitus novissimi",
        "position_label": "#",
        "team_label": "Grex",
        "points_label": "Pt",
        "wins_label": "V",
        "draws_label": "P",
        "losses_label": "S",
        "goals_for_label": "GF",
        "goals_against_label": "GS",
        "wind_label": "Ventus",
        "visibility_label": "Visibilitas",
        "region_select_label": "Regionem elige",
        "footer_prefix": "Nuntia Televidei",
        "footer_license": "Licentia MIT",
        "footer_data_prefix": "Data praebet",
        "back_home": "Redi ad chronicam",
        "error_eyebrow": "Error {code}",
        "error_404_title": "Pagina non inventa",
        "error_404_message": "Pagina quam quaeris non exstat aut mota est.",
        "error_500_title": "Error ministri",
        "error_500_message": "Casus improvisus lectionem datorum interrupit. Mox iterum tenta.",
        "updated": "Nuntia renovata lingua {language}",
        "date_unavailable": "dies ignotus",
        "error_prefix": "Error renovationis:",
    },
}


def normalize_language(value: str | None) -> str:
    return value if value in LANGUAGES else "la"


def ui_for(language: str) -> dict[str, str]:
    return UI_TEXT[normalize_language(language)]


SECTION_TEXT = {
    "it": {
        "tv": ("Guida TV", "Programmi TV, prima serata, film del giorno, RaiPlay, Rai Sport, radio e dati Auditel."),
        "cultura": ("Cultura, Libri, Cinema e Teatro", "Recensioni, libri, film, teatro, concerti, eventi e mostre recuperati dalle rubriche culturali."),
        "ambiente": ("Ambiente, Scienza e Salute", "Energie rinnovabili, sostenibilita, agenda verde, ricerca, scienza, salute e istituti scientifici."),
        "lavoro": ("Lavoro e Concorsi", "Concorsi, Gazzetta Ufficiale, sicurezza sul lavoro, formazione, agenzie ed eventi occupazionali."),
        "sport": ("Sport e Risultati", "Risultati, classifiche, calendari, club di Serie A e B, altri sport e brevi sportive."),
        "meteo": ("Meteo, Mari e Venti", "Previsioni per versanti, temperature, aeroporti, mari, venti e sicurezza in mare."),
        "viaggi": ("Viaggi, Turismo e Sicurezza", "Avvisi per viaggiare sicuri, itinerari, FAI, Touring Club, borghi e informazioni utili."),
        "giochi": ("Giochi e Estrazioni", "SuperEnalotto, Lotto e archivio delle ultime estrazioni salvate nel database."),
        "regioni": ("Televideo Regionale", "Notizie, eventi, cinema, teatri, gusto, viaggi, societa e servizi dalle pagine regionali Rai."),
    },
    "en": {
        "tv": ("TV Guide", "TV programs, prime time, films of the day, RaiPlay, Rai Sport, radio and Auditel data."),
        "cultura": ("Culture, Books, Cinema and Theatre", "Reviews, books, films, theatre, concerts, events and exhibitions from the cultural columns."),
        "ambiente": ("Environment, Science and Health", "Renewable energy, sustainability, green agenda, research, science, health and scientific institutes."),
        "lavoro": ("Work and Public Competitions", "Public competitions, official notices, workplace safety, training, agencies and employment events."),
        "sport": ("Sport and Results", "Results, standings, calendars, Serie A and B clubs, other sports and sports briefs."),
        "meteo": ("Weather, Seas and Winds", "Forecasts by area, temperatures, airports, seas, winds and sea safety."),
        "viaggi": ("Travel, Tourism and Safety", "Safe travel alerts, itineraries, FAI, Touring Club, villages and useful information."),
        "giochi": ("Games and Draws", "SuperEnalotto, Lotto and the archive of the latest draws saved in the database."),
        "regioni": ("Regional Televideo", "News, events, cinema, theatres, food, travel, society and services from Rai regional pages."),
    },
    "la": {
        "tv": ("Index Televisificus", "Programmata televisifica, prima vespera, pelliculae diei, RaiPlay, Rai Sport, radio et data Auditel."),
        "cultura": ("Cultura, Libri, Cinema et Theatrum", "Recensiones, libri, pelliculae, theatrum, concentus, eventus et exhibitiones e rubricis culturalibus."),
        "ambiente": ("Ambitus, Scientia et Salus", "Energia renovabilis, sustinabilitas, agenda viridis, investigatio, scientia, salus et instituta scientifica."),
        "lavoro": ("Labor et Certamina", "Certamina publica, acta publica, securitas laboris, institutio, agentiae et eventus occupationis."),
        "sport": ("Ludi et Exitus", "Exitus, tabulae, calendaria, greges Serie A et B, alii ludi et brevia ludorum."),
        "meteo": ("Tempestas, Maria et Venti", "Praedictiones per regiones, temperaturae, aeroportus, maria, venti et securitas marina."),
        "viaggi": ("Itinera, Peregrinatio et Securitas", "Nuntii itinerum tutorum, itinera, FAI, Touring Club, oppida et indicia utilia."),
        "giochi": ("Sortes et Extractiones", "SuperEnalotto, Lotto et archivum ultimarum sortitionum in datorum tabula servatarum."),
        "regioni": ("Televideo Regionale", "Nuntia, eventus, cinema, theatra, cibus, itinera, societas et officia e paginis regionalibus Rai."),
    },
}


STRUCTURED_PAGES = {
    "tv": {514, 515, 531, 532, 533},
    "sport": {202, 203},
    "meteo": {702, 703, 704, 705, 706, 707, 708, 709, 711, 712},
    "giochi": {691, 692, 696},
}


def localize_text(text: str, language: str, *, multiline: bool = False) -> str:
    language = normalize_language(language)
    if language == "it" or not text:
        return text
    translated = translate_lines(text, language) if multiline else translate_text(text, language)
    if language == "la":
        if multiline:
            return "\n".join(medieval_latin_style(line) if line.strip() else "" for line in translated.splitlines())
        translated = medieval_latin_style(translated)
    return translated


def localized_section_definition(section: str, language: str) -> dict[str, object]:
    language = normalize_language(language)
    definition = section_definition(section).copy()
    title, lede = SECTION_TEXT[language].get(section, (definition["title"], definition["lede"]))
    definition["title"] = title
    definition["lede"] = lede
    return definition


def nav_items(active: str, language: str) -> list[dict[str, object]]:
    ui = ui_for(language)
    return [
        {"key": key, "label": ui[label_key], "url": reverse(route), "active": key == active}
        for key, label_key, route in NAVIGATION
    ]


def snapshot_payload(snapshot: TelevideoPageSnapshot) -> dict[str, object]:
    lines = snapshot.raw_text.splitlines()
    paragraphs = [line.strip() for line in lines if line.strip()]
    return {
        "page": snapshot.page,
        "subpage": snapshot.subpage,
        "label": snapshot.label,
        "title": snapshot.title,
        "content_kind": snapshot.content_kind,
        "source_url": snapshot.source_url,
        "raw_text": snapshot.raw_text,
        "paragraphs": paragraphs,
        "fetched_at": snapshot.fetched_at,
    }


def localize_snapshot_payload(snapshot: dict[str, object], language: str) -> dict[str, object]:
    if normalize_language(language) == "it":
        return snapshot.copy()
    localized = snapshot.copy()
    localized["source_label"] = snapshot.get("label", "")
    localized["source_title"] = snapshot.get("title", "")
    localized["label"] = localize_text(str(snapshot.get("label", "")), language)
    localized["title"] = localize_text(str(snapshot.get("title", "")), language)
    localized["raw_text"] = localize_text(str(snapshot.get("raw_text", "")), language, multiline=True)
    localized["paragraphs"] = [line.strip() for line in str(localized["raw_text"]).splitlines() if line.strip()]
    return localized


def section_snapshots(section: str, region: str = "") -> list[dict[str, object]]:
    queryset = TelevideoPageSnapshot.objects.filter(section=section, region=region).order_by(
        "sort_order",
        "page",
        "subpage",
    )
    return [snapshot_payload(snapshot) for snapshot in queryset]


def should_display_card(section: str, snap: dict[str, object]) -> bool:
    page = snap.get("page")
    if page in STRUCTURED_PAGES.get(section, set()):
        return False
    if section == "cultura" and snap.get("content_kind") == "article" and len(snap.get("subpages", [])) > 1:
        return False
    return True


def localize_film(film: dict, language: str) -> dict:
    localized = film.copy()
    for key in ("title", "genre"):
        if localized.get(key):
            localized[key] = localize_text(str(localized[key]), language)
    return localized


def localize_weather_station(station: dict, language: str) -> dict:
    localized = station.copy()
    for key in ("condition", "wind", "visibility"):
        if localized.get(key):
            localized[key] = localize_text(str(localized[key]), language)
    return localized


def localize_auditel_row(row: dict, language: str) -> dict:
    localized = row.copy()
    if localized.get("channel"):
        localized["channel"] = localize_text(str(localized["channel"]), language)
    return localized


def localize_article(article: dict, language: str) -> dict:
    localized = article.copy()
    for key in ("title", "label"):
        if localized.get(key):
            localized[key] = localize_text(str(localized[key]), language)
    if localized.get("body"):
        localized["body"] = localize_text(str(localized["body"]), language, multiline=True)
    return localized


def formatted_section_data(section: str, language: str, region: str = "") -> dict:
    """Build structured/formatted data for a section using the formatters."""
    source_snapshots = section_snapshots(section, region)
    source_merged = merge_snapshot_pages(source_snapshots)
    display_snapshots = [localize_snapshot_payload(snapshot, language) for snapshot in source_snapshots]
    display_merged = merge_snapshot_pages(display_snapshots)
    display_by_page = {snap.get("page"): snap for snap in display_merged}

    data: dict = {
        "raw": display_snapshots,
        "merged": display_merged,
        "cards": [snap for snap in display_merged if should_display_card(section, snap)],
        "standings": None,
        "results": None,
        "films": [],
        "weather_stations": [],
        "temperatures": [],
        "auditel": [],
        "lotto": None,
        "articles": [],
        "round_info": None,
    }

    for snap in source_merged:
        raw = snap.get("all_text", snap.get("raw_text", ""))
        page = snap.get("page")
        display_snap = display_by_page.get(page, snap)

        # Serie A standings
        if section == "sport" and page == 203:
            s = parse_serie_a_standings(raw)
            if s:
                data["standings"] = s

        # Match results
        if section == "sport" and page == 202:
            r = parse_match_results(raw)
            if r:
                data["results"] = r
            ri = parse_round_info(raw)
            if ri:
                data["round_info"] = localize_text(ri, language)

        # Film schedules
        if section == "tv" and page in (514, 515):
            films = parse_film_schedule(raw)
            if films:
                data["films"].extend(localize_film(film, language) for film in films)

        # Weather observations
        if section == "meteo" and page in (702, 703, 704, 705, 706, 707, 708, 709):
            stations = parse_weather_observation(raw)
            if stations:
                data["weather_stations"].append({
                    "page": page,
                    "label": display_snap.get("label", ""),
                    "stations": [localize_weather_station(station, language) for station in stations],
                })

        # Temperatures
        if section == "meteo" and page in (711, 712):
            temps = parse_temperatures(raw)
            if temps:
                data["temperatures"].append({
                    "page": page,
                    "label": display_snap.get("label", ""),
                    "cities": temps,
                })

        # Auditel
        if section == "tv" and page in (531, 532, 533):
            aud = parse_auditel(raw)
            if aud:
                data["auditel"].append({
                    "page": page,
                    "label": display_snap.get("label", ""),
                    "rows": [localize_auditel_row(row, language) for row in aud],
                })

        # Lotto
        if section == "giochi" and page in (691, 692):
            lotto = parse_lotto_results(raw)
            if lotto:
                lotto["page"] = page
                lotto["label"] = display_snap.get("label", "")
                data["lotto"] = lotto

        # Multi-page articles (cultura section)
        if snap.get("content_kind") == "article":
            pages_for_article = [s for s in source_snapshots if s["page"] == page]
            if len(pages_for_article) > 1:
                article = parse_article_multipage(pages_for_article)
                if article:
                    article["page"] = page
                    article["label"] = snap.get("label", "")
                    article["title"] = article.get("title") or snap.get("title", "")
                    data["articles"].append(localize_article(article, language))

    return data


def parse_limit(value: str | None, default: int = 18) -> int:
    try:
        return min(max(int(value or default), 1), 80)
    except ValueError:
        return default


def parse_page(value: str | None) -> int:
    try:
        return max(int(value or 1), 1)
    except ValueError:
        return 1


def home(request):
    language = normalize_language(request.GET.get("lang"))
    if not NewsItem.objects.exists():
        try:
            refresh_if_stale()
        except RuntimeError:
            pass
    return render(
        request,
        "news/home.html",
        {
            "language": language,
            "languages": LANGUAGES,
            "refresh_seconds": settings.NEWS_REFRESH_SECONDS,
            "ui": ui_for(language),
            "nav_items": nav_items("home", language),
        },
    )


def superenalotto(request):
    language = normalize_language(request.GET.get("lang"))
    if not SuperEnalottoDraw.objects.exists():
        try:
            refresh_if_stale()
        except RuntimeError:
            pass
    return render(
        request,
        "news/superenalotto.html",
        {
            "language": language,
            "languages": LANGUAGES,
            "refresh_seconds": settings.NEWS_REFRESH_SECONDS,
            "ui": ui_for(language),
            "nav_items": nav_items("giochi", language),
        },
    )


def televideo_section(request, section: str, active: str):
    language = normalize_language(request.GET.get("lang"))
    if section not in SECTION_DEFINITIONS:
        raise Http404("Sezione non trovata")
    definition = localized_section_definition(section, language)
    refresh_section_if_stale(section)
    formatted = formatted_section_data(section, language)
    latest = max((card["fetched_at"] for card in formatted["raw"]), default=None)
    ctx = {
        "section": {**definition, "key": section},
        "data": formatted,
        "latest": latest,
        "nav_items": nav_items(active, language),
        "language": language,
        "languages": LANGUAGES,
        "refresh_seconds": settings.NEWS_REFRESH_SECONDS,
        "ui": ui_for(language),
    }
    specific = f"news/section_{section}.html"
    try:
        from django.template.loader import get_template
        get_template(specific)
        return render(request, specific, ctx)
    except TemplateDoesNotExist:
        return render(request, "news/section.html", ctx)


def tv(request):
    return televideo_section(request, "tv", "tv")


def culture(request):
    return televideo_section(request, "cultura", "cultura")


def environment(request):
    return televideo_section(request, "ambiente", "ambiente")


def work(request):
    return televideo_section(request, "lavoro", "lavoro")


def sport(request):
    return televideo_section(request, "sport", "sport")


def weather(request):
    return televideo_section(request, "meteo", "meteo")


def travel(request):
    return televideo_section(request, "viaggi", "viaggi")


def games(request):
    language = normalize_language(request.GET.get("lang"))
    refresh_section_if_stale("giochi")
    formatted = formatted_section_data("giochi", language)
    latest = max((card["fetched_at"] for card in formatted["raw"]), default=None)
    latest_superenalotto = SuperEnalottoDraw.objects.first()
    latest_lotto = LottoDraw.objects.first()
    return render(
        request,
        "news/section_giochi.html",
        {
            "section": {**localized_section_definition("giochi", language), "key": "giochi"},
            "data": formatted,
            "latest": latest,
            "latest_superenalotto": latest_superenalotto,
            "latest_lotto": latest_lotto,
            "nav_items": nav_items("giochi", language),
            "language": language,
            "languages": LANGUAGES,
            "refresh_seconds": settings.NEWS_REFRESH_SECONDS,
            "ui": ui_for(language),
        },
    )


def regions(request, region_slug_value: str | None = None):
    language = normalize_language(request.GET.get("lang"))
    selected_region = normalize_region(region_slug_value or request.GET.get("regione"))
    refresh_section_if_stale("regioni", selected_region)
    formatted = formatted_section_data("regioni", language, selected_region)
    latest = max((card["fetched_at"] for card in formatted["raw"]), default=None)
    regions_payload = [
        {
            "name": region,
            "slug": region_slug(region),
            "url": reverse("news:region", kwargs={"region_slug_value": region_slug(region)}),
            "active": region == selected_region,
        }
        for region in REGION_CHOICES
    ]
    return render(
        request,
        "news/regions.html",
        {
            "section": {**localized_section_definition("regioni", language), "key": "regioni", "title": f"{localized_section_definition('regioni', language)['title']} - {selected_region}"},
            "data": formatted,
            "latest": latest,
            "regions": regions_payload,
            "selected_region": selected_region,
            "nav_items": nav_items("regioni", language),
            "language": language,
            "languages": LANGUAGES,
            "refresh_seconds": settings.NEWS_REFRESH_SECONDS,
            "ui": ui_for(language),
        },
    )


def serialized_categories(language: str) -> list[dict[str, object]]:
    categories = []
    queryset = (
        Category.objects.filter(active=True)
        .exclude(code__in=HIDDEN_CATEGORY_CODES)
        .annotate(news_count=Count("items", filter=displayable_category_filter()))
        .filter(news_count__gt=0)
    )
    for category in queryset.order_by("sort_order", "name_it"):
        categories.append(
            {
                "code": category.code,
                "name": category.name_for(language),
                "page": category.page,
                "count": category.news_count,
            }
        )
    return categories


def news_title_for(item: NewsItem, language: str) -> str:
    language = normalize_language(language)
    if language == "la" and item.title_la:
        return item.title_la
    if language == "en" and item.title_en:
        return item.title_en
    if language == "it":
        return item.title_it
    return localize_text(item.title_it, language)


def news_summary_for(item: NewsItem, language: str) -> str:
    language = normalize_language(language)
    if language == "la" and item.summary_la:
        return item.summary_for("la")
    if language == "en" and item.summary_en:
        return item.summary_for("en")
    if language == "it":
        return item.summary_for("it")
    return localize_text(item.summary_it, language)


def news_api(request):
    language = normalize_language(request.GET.get("lang"))
    limit = parse_limit(request.GET.get("limit"), default=12)
    page = parse_page(request.GET.get("page"))
    category_code = request.GET.get("category") or "all"
    error = ""
    try:
        refresh_if_stale()
    except RuntimeError as exc:
        error = str(exc)

    queryset = (
        NewsItem.objects.select_related("category")
        .filter(displayable_filter())
        .exclude(category__code__in=HIDDEN_CATEGORY_CODES)
    )
    if category_code != "all":
        filtered = queryset.filter(category__code=category_code)
        if filtered.exists():
            queryset = filtered
        else:
            category_code = "all"

    queryset = queryset.annotate(
        source_rank=Case(
            When(category__code="rss101", then=Value(0)),
            default=Value(1),
            output_field=IntegerField(),
        )
    ).order_by("source_rank", "-published_at", "-created_at")
    total_items = queryset.count()
    total_pages = max((total_items + limit - 1) // limit, 1)
    page = min(page, total_pages)
    start = (page - 1) * limit
    end = start + limit

    items = []
    for item in queryset[start:end]:
        category = item.category
        items.append(
            {
                "id": item.source_id,
                "title": news_title_for(item, language),
                "summary": news_summary_for(item, language),
                "source_title": item.title_it,
                "category_code": category.code if category else "",
                "category_name": category.name_for(language) if category else "",
                "source_page": item.source_page,
                "published": item.pub_date_text,
                "published_iso": item.published_at.isoformat() if item.published_at else "",
            }
        )

    return JsonResponse(
        {
            "language": language,
            "language_label": LANGUAGES[language],
            "generated_at": timezone.localtime().isoformat(),
            "refresh_seconds": settings.NEWS_REFRESH_SECONDS,
            "selected_category": category_code,
            "ui": ui_for(language),
            "categories": serialized_categories(language),
            "pagination": {
                "page": page,
                "pages": total_pages,
                "limit": limit,
                "total": total_items,
                "has_previous": page > 1,
                "has_next": page < total_pages,
            },
            "error": error,
            "items": items,
        }
    )


def displayable_filter() -> Q:
    return ~Q(title_it__regex=r"^\d+/\d+$") & ~Q(summary_it__regex=r"^S\.?\s*S\.?$", title_it__regex=r"^\d+/\d+$")


def displayable_category_filter() -> Q:
    return (
        ~Q(items__category__code__in=HIDDEN_CATEGORY_CODES)
        & ~Q(items__title_it__regex=r"^\d+/\d+$")
        & ~Q(items__summary_it__regex=r"^S\.?\s*S\.?$", items__title_it__regex=r"^\d+/\d+$")
    )


def page_not_found(request, exception=None):
    language = normalize_language(request.GET.get("lang"))
    ui = ui_for(language)
    return render(
        request,
        "news/error.html",
        {
            "code": 404,
            "eyebrow": ui["error_eyebrow"].replace("{code}", "404"),
            "title": ui["error_404_title"],
            "message": ui["error_404_message"],
            "language": language,
            "languages": LANGUAGES,
            "ui": ui,
            "nav_items": nav_items("home", language),
        },
        status=404,
    )


def server_error(request):
    language = normalize_language(request.GET.get("lang"))
    ui = ui_for(language)
    return render(
        request,
        "news/error.html",
        {
            "code": 500,
            "eyebrow": ui["error_eyebrow"].replace("{code}", "500"),
            "title": ui["error_500_title"],
            "message": ui["error_500_message"],
            "language": language,
            "languages": LANGUAGES,
            "ui": ui,
            "nav_items": nav_items("home", language),
        },
        status=500,
    )


def healthcheck(request):
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
        cursor.fetchone()
    return JsonResponse({"status": "ok", "time": timezone.localtime().isoformat()})


def decimal_payload(value):
    if value is None:
        return {"text": "", "value": None}
    return {"text": f"EUR {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."), "value": float(value)}


def draw_payload(draw: SuperEnalottoDraw | None) -> dict[str, object] | None:
    if draw is None:
        return None
    return {
        "draw_number": draw.draw_number,
        "draw_date": draw.draw_date.isoformat(),
        "winning_numbers": draw.winning_numbers,
        "jolly_number": draw.jolly_number,
        "superstar_number": draw.superstar_number,
        "jackpot": decimal_payload(draw.jackpot),
        "prize_pool": decimal_payload(draw.prize_pool),
    }


def superenalotto_api(request):
    language = normalize_language(request.GET.get("lang"))
    selected_date = request.GET.get("date") or ""
    error = ""
    try:
        refresh_if_stale()
    except RuntimeError as exc:
        error = str(exc)

    draws = SuperEnalottoDraw.objects.all()
    selected = draws.filter(draw_date=selected_date).first() if selected_date else draws.first()
    dates = [{"value": draw.draw_date.isoformat(), "label": f"{draw.draw_date.isoformat()} - N.{draw.draw_number}"} for draw in draws]
    trend_draws = list(reversed(list(SuperEnalottoDraw.objects.all()[:30])))

    return JsonResponse(
        {
            "language": language,
            "language_label": LANGUAGES[language],
            "generated_at": timezone.localtime().isoformat(),
            "refresh_seconds": settings.NEWS_REFRESH_SECONDS,
            "ui": ui_for(language),
            "error": error,
            "dates": dates,
            "selected": draw_payload(selected),
            "trend": [
                {
                    "label": f"{draw.draw_date.isoformat()} N.{draw.draw_number}",
                    "jackpot": float(draw.jackpot) if draw.jackpot is not None else None,
                    "prize_pool": float(draw.prize_pool) if draw.prize_pool is not None else None,
                }
                for draw in trend_draws
            ],
        }
    )
