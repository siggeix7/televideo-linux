"""Carica i dati delle regioni italiane per la mappa SVG da GeoJSON convertito."""

from __future__ import annotations

import json
from pathlib import Path

from django.urls import reverse

_SHORT = {
    "piemonte": "PIE", "aosta": "VdA", "lombardia": "LOM",
    "trentino-alto-adige": "TAA", "veneto": "VEN", "friuli": "FVG",
    "liguria": "LIG", "emilia": "EMR", "toscana": "TOS",
    "umbria": "UMB", "marche": "MAR", "lazio": "LAZ",
    "abruzzo": "ABR", "molise": "MOL", "campania": "CAM",
    "puglia": "PUG", "basilicata": "BAS", "calabria": "CAL",
    "sicilia": "SIC", "sardegna": "SAR",
}

_NAMES = {
    "piemonte": "Piemonte", "aosta": "Valle d'Aosta", "lombardia": "Lombardia",
    "trentino-alto-adige": "Trentino-Alto Adige", "veneto": "Veneto", "friuli": "Friuli V.G.",
    "liguria": "Liguria", "emilia": "Emilia R.", "toscana": "Toscana",
    "umbria": "Umbria", "marche": "Marche", "lazio": "Lazio",
    "abruzzo": "Abruzzo", "molise": "Molise", "campania": "Campania",
    "puglia": "Puglia", "basilicata": "Basilicata", "calabria": "Calabria",
    "sicilia": "Sicilia", "sardegna": "Sardegna",
}

_FONT = {
    "aosta": 9, "molise": 9, "basilicata": 9,
    "marche": 10, "umbria": 10, "abruzzo": 10,
    "sicilia": 12, "sardegna": 12,
    "trentino-alto-adige": 9,
}

# Regions to merge: key = new slug, value = [source slugs]
_MERGE = {
    "trentino-alto-adige": ["trentino", "altoadige"],
}

# Trentino-Alto Adige outline generated from the official Openpolis/ISTAT
# regional GeoJSON and projected into this SVG coordinate system.
_TAA_MERGED_PATH = (
    "M 363.9,45.5 L 350.6,49.7 L 355.5,54.4 L 352.9,55.1 L 351.9,60.8 "
    "L 347.8,61.4 L 351.7,64.2 L 352.1,68.7 L 358.2,70.5 L 356.9,72.5 "
    "L 360.5,75.5 L 355.4,81.2 L 341.8,83.3 L 341.9,93.6 L 335.3,93.6 "
    "L 332.0,90.0 L 320.9,92.4 L 319.2,98.6 L 313.1,97.6 L 308.5,106.5 "
    "L 309.4,109.0 L 307.4,108.7 L 307.8,112.7 L 304.0,116.8 L 296.9,114.3 "
    "L 291.6,118.1 L 285.3,114.3 L 288.2,106.6 L 284.1,104.5 L 275.6,104.2 "
    "L 271.7,107.5 L 264.4,108.6 L 261.5,100.6 L 262.7,97.4 L 259.0,91.9 "
    "L 265.5,81.4 L 264.9,75.5 L 267.9,70.8 L 266.6,64.1 L 263.4,61.7 "
    "L 270.9,57.8 L 268.9,52.3 L 259.3,48.8 L 261.6,40.2 L 255.0,36.9 "
    "L 260.2,20.3 L 265.6,21.6 L 273.4,18.6 L 279.9,23.0 L 277.6,25.9 "
    "L 297.2,27.8 L 301.4,23.0 L 302.2,15.6 L 306.8,11.2 L 317.2,9.0 "
    "L 322.7,11.2 L 328.0,7.4 L 331.9,9.6 L 337.9,7.3 L 346.0,10.9 "
    "L 361.5,4.2 L 377.4,1.2 L 379.1,2.7 L 376.7,6.0 L 371.1,7.8 "
    "L 374.3,13.5 L 372.7,15.4 L 377.5,18.8 L 381.4,17.9 L 383.6,21.5 "
    "L 382.1,26.3 L 387.0,27.0 L 388.8,31.8 L 395.1,34.8 L 388.9,39.5 "
    "L 380.5,39.0 L 375.9,41.9 L 376.0,39.8 L 367.6,35.2 Z"
)
_TAA_LABEL_POINT = (315, 55)

# Render order: smaller/enclosed regions LAST so they render on top and remain clickable.
# Higher index = drawn later = on top.
_RENDER_ORDER = {
    "sicilia": 1, "sardegna": 1,
    "piemonte": 2, "lombardia": 2, "veneto": 2, "emilia": 2, "toscana": 2,
    "lazio": 3, "campania": 3, "puglia": 3, "calabria": 3,
    "abruzzo": 4, "marche": 4, "liguria": 4, "friuli": 4,
    "umbria": 5, "molise": 5, "basilicata": 5, "trentino-alto-adige": 5, "aosta": 5,
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
    candidates = []

    # Build merged regions from _MERGE config
    merged_slugs = set()
    for new_slug, source_slugs in _MERGE.items():
        merged_slugs.update(source_slugs)
        # Use manually merged path if available, otherwise concat cleaned paths
        if new_slug == "trentino-alto-adige":
            combined_d = _TAA_MERGED_PATH
        else:
            cleaned_parts = []
            for s in source_slugs:
                if s in _DATA:
                    cleaned_parts.append(_clean_path(_DATA[s]["d"]))
            combined_d = " ".join(cleaned_parts)
        if new_slug == "trentino-alto-adige":
            cx, cy = _TAA_LABEL_POINT
        else:
            # Average centroids
            cxs, cys = [], []
            for s in source_slugs:
                if s in _DATA:
                    cxs.append(_DATA[s]["cx"])
                    cys.append(_DATA[s]["cy"])
            cx = sum(cxs) / len(cxs) if cxs else 0
            cy = sum(cys) / len(cys) if cys else 0
        entry = {
            "slug": new_slug,
            "label": _NAMES.get(new_slug, new_slug),
            "label_short": _SHORT.get(new_slug, ""),
            "font_size": _FONT.get(new_slug, 9),
            "cx": cx,
            "cy": cy,
            "path": combined_d,
            "url": reverse("news:region", kwargs={"region_slug_value": new_slug}),
        }
        candidates.append(entry)

    for slug, item in _DATA.items():
        if slug in merged_slugs:
            continue
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
    candidates.sort(key=lambda r: (_RENDER_ORDER.get(r["slug"], 3), -_estimate_area(_DATA.get(r["slug"], {"d": r["path"]}))))
    return candidates
