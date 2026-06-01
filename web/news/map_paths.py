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

# Render order: smaller/enclosed regions LAST so they render on top and remain clickable.
# Higher index = drawn later = on top.
_RENDER_ORDER = {
    "sicilia": 1, "sardegna": 1,
    "piemonte": 2, "lombardia": 2, "veneto": 2, "emilia": 2, "toscana": 2,
    "lazio": 3, "campania": 3, "puglia": 3, "calabria": 3,
    "abruzzo": 4, "marche": 4, "liguria": 4, "friuli": 4,
    "umbria": 5, "molise": 5, "basilicata": 5, "trentino": 5, "altoadige": 5, "aosta": 5,
}

_DATA = json.loads(Path(__file__).with_name("map_data.json").read_text())


def _clean_path(d: str) -> str:
    """Remove Z from sub-paths that are chained together.
    
    The raw data uses M...Z M...Z where consecutive segments share endpoints.
    Each Z closes the segment back to its own start, creating slivers.
    We merge chained segments by removing Z on connecting segments,
    keeping Z only on closed standalone segments (islands/holes).
    """
    parts = [p.strip() for p in d.split("Z")]
    parts = [p for p in parts if p.strip()]

    if len(parts) <= 1:
        return d

    cleaned = []
    for i, part in enumerate(parts):
        cleaned.append(part.strip())

        if i == len(parts) - 1:
            # Last part: always close with Z
            cleaned.append("Z")
            break

        # Check if this part connects to the next part
        # Get the last coordinate of this part
        this_tokens = part.replace("M", "").replace("L", "").strip().split()
        next_part = parts[i + 1].strip()
        # Get first coordinate of next part (after the initial M)
        next_tokens = next_part.replace("M", "").replace("L", "").strip().split()

        if not this_tokens or not next_tokens:
            cleaned.append("Z")
            continue

        this_last = this_tokens[-1]
        next_first = next_tokens[0]

        # Parse coordinates
        try:
            x1, y1 = this_last.split(",")
            x2, y2 = next_first.split(",")
            if abs(float(x1) - float(x2)) < 1.0 and abs(float(y1) - float(y2)) < 1.0:
                # Connected: don't close this segment with Z
                continue
        except (ValueError, IndexError):
            pass
        cleaned.append("Z")

    return " ".join(cleaned)


def _estimate_area(item: dict) -> float:
    """Approximate the area from the SVG path bounding box."""
    d = item["d"]
    xs, ys = [], []
    for part in d.split("M"):
        if not part.strip():
            continue
        coords = part.strip().split()
        for c in coords:
            c = c.rstrip("Z")
            if "," in c:
                try:
                    x_s, y_s = c.split(",")
                    xs.append(float(x_s))
                    ys.append(float(y_s))
                except ValueError:
                    pass
    if not xs:
        return 0
    return (max(xs) - min(xs)) * (max(ys) - min(ys))


def get_map_regions():
    regions = []
    candidates = []
    for slug, item in _DATA.items():
        entry = {
            "slug": slug,
            "label": _NAMES.get(slug, slug),
            "label_short": _SHORT.get(slug, ""),
            "font_size": _FONT.get(slug, 9),
            "cx": item["cx"],
            "cy": item["cy"],
            "path": _clean_path(item["d"]),
            "url": reverse("news:region", kwargs={"region_slug_value": slug}),
        }
        candidates.append(entry)

    # Sort by render order (small on top), then by estimated area (small on top)
    candidates.sort(key=lambda r: (_RENDER_ORDER.get(r["slug"], 3), -_estimate_area(_DATA[r["slug"]])))
    return candidates
