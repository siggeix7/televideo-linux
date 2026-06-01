"""Carica i dati delle regioni italiane per la mappa SVG da GeoJSON convertito."""

from __future__ import annotations

import json
from pathlib import Path

from django.urls import reverse

_SHORT = {
    "piemonte": "PIE", "aosta": "VdA", "lombardia": "LOM",
    "altoadige": "AA", "trentino": "TNT", "veneto": "VEN", "friuli": "FVG",
    "liguria": "LIG", "emilia": "EMR", "toscana": "TOS",
    "umbria": "UMB", "marche": "MAR", "lazio": "LAZ",
    "abruzzo": "ABR", "molise": "MOL", "campania": "CAM",
    "puglia": "PUG", "basilicata": "BAS", "calabria": "CAL",
    "sicilia": "SIC", "sardegna": "SAR",
}

_NAMES = {
    "piemonte": "Piemonte", "aosta": "Valle d'Aosta", "lombardia": "Lombardia",
    "altoadige": "Alto Adige", "trentino": "Trentino", "veneto": "Veneto", "friuli": "Friuli V.G.",
    "liguria": "Liguria", "emilia": "Emilia R.", "toscana": "Toscana",
    "umbria": "Umbria", "marche": "Marche", "lazio": "Lazio",
    "abruzzo": "Abruzzo", "molise": "Molise", "campania": "Campania",
    "puglia": "Puglia", "basilicata": "Basilicata", "calabria": "Calabria",
    "sicilia": "Sicilia", "sardegna": "Sardegna",
}

_FONT = {
    "aosta": 9, "altoadige": 9, "trentino": 9, "molise": 9, "basilicata": 9,
    "marche": 10, "umbria": 10, "abruzzo": 10,
    "sicilia": 12, "sardegna": 12,
}

_DATA = json.loads(Path(__file__).with_name("map_data.json").read_text())


def get_map_regions():
    regions = []
    for slug, item in sorted(_DATA.items()):
        regions.append({
            "slug": slug,
            "label": _NAMES.get(slug, slug),
            "label_short": _SHORT.get(slug, ""),
            "font_size": _FONT.get(slug, 9),
            "cx": item["cx"],
            "cy": item["cy"],
            "path": item["d"],
            "url": reverse("news:region", kwargs={"region_slug_value": slug}),
        })
    return regions
