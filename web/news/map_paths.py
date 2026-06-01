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
    """Merge chained M...Z sub-paths into a single closed polygon,
    discarding internal holes/islands that create empty areas.
    
    The raw data uses M...Z M...Z where consecutive segments share endpoints.
    We merge the main chain into one polygon and drop standalone sub-paths
    that are likely to be lakes/holes inside the region.
    """
    parts_raw = [p.strip() for p in d.split("Z")]
    parts_raw = [p for p in parts_raw if p.strip()]

    if len(parts_raw) <= 1:
        return d

    # First pass: extract all sub-paths
    subpaths = []
    for part in parts_raw:
        part = part.strip()
        tokens = part.strip().split()
        coord_tokens = []
        for tok in tokens:
            if tok in ("M", "L"):
                continue
            tok = tok.rstrip("Z").rstrip(",")
            if "," in tok:
                coord_tokens.append(tok)
        if coord_tokens:
            subpaths.append({
                "text": part,
                "start": coord_tokens[0],
                "end": coord_tokens[-1],
            })

    # Build connected chains
    used = set()
    chains = []
    for i, sp in enumerate(subpaths):
        if i in used:
            continue
        chain = [i]
        used.add(i)
        current_end = sp["end"]
        while True:
            found = False
            for j, sp2 in enumerate(subpaths):
                if j in used:
                    continue
                try:
                    x1, y1 = map(float, current_end.split(","))
                    x2, y2 = map(float, sp2["start"].split(","))
                    if abs(x1 - x2) < 1.0 and abs(y1 - y2) < 1.0:
                        chain.append(j)
                        used.add(j)
                        current_end = sp2["end"]
                        found = True
                        break
                except (ValueError, IndexError):
                    pass
            if not found:
                break
        chains.append(chain)

    # For each chain, merge into one path
    merged_paths = []
    for chain in chains:
        tokens_list = []
        for idx in chain:
            sp = subpaths[idx]
            toks = sp["text"].strip().split()
            if idx == chain[0]:
                tokens_list.extend(toks)
            else:
                # Remove M and the first coordinate (duplicate of previous end)
                if toks[0] == "M":
                    toks = toks[2:]  # skip "M x,y"
                tokens_list.extend(toks)
        # Close with Z
        path = " ".join(tokens_list) + " Z"
        # Compute bounding box area
        xs, ys = [], []
        for tok in tokens_list:
            if tok in ("M", "L", "Z"):
                continue
            try:
                x, y = tok.split(",")
                xs.append(float(x))
                ys.append(float(y))
            except ValueError:
                pass
        if xs and ys:
            bbox_area = (max(xs) - min(xs)) * (max(ys) - min(ys))
        else:
            bbox_area = 0
        merged_paths.append((path, bbox_area))

    # Sort by area (largest first) and keep only the main polygon
    merged_paths.sort(key=lambda x: -x[1])

    return merged_paths[0][0]


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
