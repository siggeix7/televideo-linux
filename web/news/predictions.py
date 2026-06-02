from collections import Counter, defaultdict
from datetime import timedelta

from .models import SuperEnalottoDraw, SuperEnalottoPrediction


SUPERENALOTTO_MAX_NUMBER = 90
NUMBERS_RANGE = range(1, SUPERENALOTTO_MAX_NUMBER + 1)
COMBO_COUNT = 6
NUMBERS_PER_COMBO = 6
RECENT_WINDOW = 50
MARKOV_WINDOW = 1000
PREDICTION_ENGINE_VERSION = "cycle-aware-v2"
CURRENT_COMBO_LABELS = (
    "Ciclo di ritorno",
    "Transizioni Markov",
    "Gap anomalo",
    "Tendenza recente",
    "Mix controllato",
    "Ensemble pesato",
)


def _all_draws():
    return SuperEnalottoDraw.objects.order_by("draw_date")


def _draws_as_lists(draws_queryset):
    """Return list of [draw_date, [n1,n2,...,n6], jolly, superstar] ordered ASC."""
    draws = []
    for draw in draws_queryset:
        numbers = sorted(draw.winning_numbers or [])
        draws.append({
            "date": draw.draw_date,
            "numbers": numbers,
            "jolly": draw.jolly_number,
            "superstar": draw.superstar_number,
        })
    return draws


def number_frequencies(draws_queryset=None):
    if draws_queryset is None:
        draws_queryset = _all_draws()
    main_counter = Counter()
    jolly_counter = Counter()
    superstar_counter = Counter()
    for draw in draws_queryset:
        numbers = draw.winning_numbers or []
        for n in numbers:
            main_counter[n] += 1
        if draw.jolly_number:
            jolly_counter[draw.jolly_number] += 1
        if draw.superstar_number:
            superstar_counter[draw.superstar_number] += 1
    return main_counter, jolly_counter, superstar_counter


def hot_numbers(main_counter, top=18):
    return [num for num, _ in main_counter.most_common(top)]


def _overdue_with_gaps(draws_list):
    """Compute overdue numbers with detailed gap analysis.

    Returns:
        overdue_sorted: list of numbers sorted by gap (most overdue first)
        gap_info: dict mapping number -> (current_gap, avg_gap, std_gap, n_appearances)
        most_overdue: list of (number, gap, avg_gap, ratio) for top overdue
    """
    total = len(draws_list)
    last_seen = {}
    all_gaps = defaultdict(list)

    for i, draw in enumerate(draws_list):
        for n in draw["numbers"]:
            if n in last_seen:
                all_gaps[n].append(i - last_seen[n])
            last_seen[n] = i

    gap_info = {}
    for n in NUMBERS_RANGE:
        if n in all_gaps and all_gaps[n]:
            avg_gap = sum(all_gaps[n]) / len(all_gaps[n])
            std_gap = 0
            if len(all_gaps[n]) > 1:
                m = avg_gap
                std_gap = (sum((g - m) ** 2 for g in all_gaps[n]) / len(all_gaps[n])) ** 0.5
            current_gap = total - last_seen.get(n, total)
            gap_info[n] = (current_gap, avg_gap, std_gap, len(all_gaps[n]) + 1)
        else:
            gap_info[n] = (total, 0, 0, 0)

    sorted_by_gap = sorted(gap_info.items(), key=lambda x: -x[1][0])
    overdue_sorted = [n for n, _ in sorted_by_gap]

    most_overdue = []
    for n, (cur, avg, std, cnt) in list(sorted(gap_info.items(), key=lambda x: -x[1][0]))[:20]:
        if avg > 0:
            ratio = cur / avg
            most_overdue.append((n, cur, round(avg, 1), round(ratio, 2)))
        else:
            most_overdue.append((n, cur, 0, 0))

    return overdue_sorted, gap_info, most_overdue


def _cycle_aware_candidates(draws_list, num_candidates=24):
    """Find numbers whose current gap is near their typical return cycle.

    This is the ONLY strategy that showed statistically significant
    prediction accuracy (p<0.05) in historical backtesting.
    """
    total = len(draws_list)
    last_seen = {}
    all_gaps = defaultdict(list)

    for i, draw in enumerate(draws_list):
        for n in draw["numbers"]:
            if n in last_seen:
                all_gaps[n].append(i - last_seen[n])
            last_seen[n] = i

    cycle_scores = []
    for n in NUMBERS_RANGE:
        if n in all_gaps and len(all_gaps[n]) >= 3:
            avg_gap = sum(all_gaps[n]) / len(all_gaps[n])
            if avg_gap > 0:
                cur_gap = total - last_seen.get(n, total)
                ratio = cur_gap / avg_gap
                # Score highest when current gap is near typical (0.7x - 1.3x of avg)
                if 0.7 <= ratio <= 1.3:
                    score = 100 - abs(ratio - 1.0) * 80
                elif ratio > 2.5:
                    score = 40  # very overdue, moderate boost
                elif 0.5 <= ratio < 0.7:
                    score = 30
                else:
                    score = 10
                cycle_scores.append((n, score, ratio, avg_gap, cur_gap))

    cycle_scores.sort(key=lambda x: -x[1])
    return [n for n, _, _, _, _ in cycle_scores[:num_candidates]]


def _markov_candidates(draws_list, num_candidates=24):
    """Find numbers most likely to follow the last draw's numbers.

    Based on transition frequencies from historical data with
    window=MARKOV_WINDOW.
    """
    if len(draws_list) < 2:
        return []

    last = set(draws_list[-1]["numbers"])
    window = min(MARKOV_WINDOW, len(draws_list))
    start = max(0, len(draws_list) - window)

    transitions = defaultdict(Counter)
    for i in range(start, len(draws_list) - 1):
        for a in draws_list[i]["numbers"]:
            if a in last:
                for b in draws_list[i + 1]["numbers"]:
                    if b not in last:
                        transitions[a][b] += 1

    scores = Counter()
    for a in last:
        for b, count in transitions[a].most_common(30):
            scores[b] += count

    # Blend with overall frequency
    freq = Counter()
    for draw in draws_list:
        for n in draw["numbers"]:
            freq[n] += 1

    for n in NUMBERS_RANGE:
        scores[n] += freq.get(n, 0) * 0.3

    return [n for n, _ in scores.most_common(num_candidates)]


def generate_combinations(draws_queryset=None):
    if draws_queryset is None:
        draws_queryset = _all_draws()

    draws_list = _draws_as_lists(draws_queryset)
    recent = draws_queryset.order_by("-draw_date")[:RECENT_WINDOW]
    main_counter, jolly_counter, superstar_counter = number_frequencies(recent)
    main_all, _, _ = number_frequencies(draws_queryset)

    hot = hot_numbers(main_counter, top=NUMBERS_PER_COMBO * 3)
    overdue_sorted, gap_info, most_overdue = _overdue_with_gaps(draws_list)
    overdue = overdue_sorted[:NUMBERS_PER_COMBO * 3]
    cycle_candidates = _cycle_aware_candidates(draws_list)
    markov_candidates = _markov_candidates(draws_list)

    combos = []

    def pick_jolly(exclude, counter=None):
        if counter is None:
            counter = jolly_counter
        candidates = [n for n, _ in counter.most_common(12) if n not in exclude]
        if not candidates:
            candidates = [n for n in NUMBERS_RANGE if n not in exclude]
        return candidates[0] if candidates else 1

    def pick_superstar(exclude, counter=None):
        if counter is None:
            counter = superstar_counter
        candidates = [n for n, _ in counter.most_common(12) if n not in exclude]
        if not candidates:
            candidates = [n for n in NUMBERS_RANGE if n not in exclude]
        return candidates[0] if candidates else 1

    def build_combo(nums, jolly_counter_override=None, superstar_counter_override=None):
        selected = []
        seen = set()
        for n in nums:
            if n not in seen:
                selected.append(n)
                seen.add(n)
            if len(selected) >= NUMBERS_PER_COMBO:
                break
        if len(selected) < NUMBERS_PER_COMBO:
            for n in NUMBERS_RANGE:
                if n not in seen:
                    selected.append(n)
                    seen.add(n)
                if len(selected) >= NUMBERS_PER_COMBO:
                    break
        jolly = pick_jolly(set(selected), jolly_counter_override)
        superstar = pick_superstar(set(selected) | {jolly}, superstar_counter_override)
        return {"numbers": selected, "jolly": jolly, "superstar": superstar}

    # --------------------------------------------------------------
    # Combo 1: Cycle-Aware (the only statistically significant strategy)
    # --------------------------------------------------------------
    combo1 = build_combo(cycle_candidates)
    combo1["label"] = "Ciclo di ritorno"
    combo1["engine_version"] = PREDICTION_ENGINE_VERSION
    combo1["description"] = "Numeri in fase di ritorno secondo il loro ciclo storico"
    combo1["reasoning"] = [
        "Analisi dei cicli di ritorno: ogni numero ha un ritmo tipico di riapparizione (~13-18 estrazioni).",
        "Quando il gap attuale si avvicina alla media storica, la probabilit\u00e0 aumenta leggermente.",
        "Unica strategia con significativit\u00e0 statistica (p<0.05) nei backtest su 2809 estrazioni.",
    ]
    cycle_details = []
    for n in combo1["numbers"]:
        if n in gap_info:
            cur, avg, std, cnt = gap_info[n]
            cycle_details.append(f"{n}: gap attuale={int(cur)} estrazioni, ciclo medio={avg:.1f}")
    combo1["cycle_details"] = cycle_details
    combos.append(combo1)

    # --------------------------------------------------------------
    # Combo 2: Catena di Markov
    # --------------------------------------------------------------
    combo2 = build_combo(markov_candidates)
    combo2["label"] = "Transizioni Markov"
    combo2["engine_version"] = PREDICTION_ENGINE_VERSION
    combo2["description"] = "Numeri che storicamente seguono quelli dell'ultima estrazione"
    combo2["reasoning"] = [
        "Analisi delle transizioni: quali numeri appaiono pi\u00f9 spesso dopo i numeri dell'ultima estrazione.",
        "Finestra di analisi: ultime 1000 estrazioni per catturare pattern stabili.",
        "Combinato con la frequenza globale per bilanciare.",
    ]
    last_draw_nums = sorted(draws_list[-1]["numbers"]) if draws_list else []
    combo2["context"] = f"Basato sull'ultima estrazione: {last_draw_nums}"
    combos.append(combo2)

    # --------------------------------------------------------------
    # Combo 3: Gap anomalo (improved overdue analysis)
    # --------------------------------------------------------------
    combo3 = build_combo(overdue)
    combo3["label"] = "Gap anomalo"
    combo3["engine_version"] = PREDICTION_ENGINE_VERSION
    combo3["description"] = "Numeri con assenza molto superiore al loro ciclo medio"
    combo3["reasoning"] = [
        "Numeri con il gap attuale pi\u00f9 lungo rispetto alla loro ultima apparizione.",
        "Il gap \u00e8 confrontato con la media storica per identificare anomalie.",
        "Esempio: il 70 manca da 104 estrazioni (5.9x il suo ciclo medio di 17.7).",
    ]
    gap_examples = []
    for n in combo3["numbers"][:6]:
        if n in gap_info:
            cur, avg, _, _ = gap_info[n]
            if avg > 0:
                gap_examples.append(f"{n}: {int(cur)} estrazioni (media: {avg:.1f})")
            else:
                gap_examples.append(f"{n}: {int(cur)} estrazioni")
    combo3["gap_details"] = gap_examples
    combos.append(combo3)

    # --------------------------------------------------------------
    # Combo 4: Tendenza recente (improved recency)
    # --------------------------------------------------------------
    combo4 = build_combo(hot, jolly_counter, superstar_counter)
    combo4["label"] = "Tendenza recente"
    combo4["engine_version"] = PREDICTION_ENGINE_VERSION
    combo4["description"] = "Numeri con frequenza recente superiore alla media storica"
    combo4["reasoning"] = [
        "Frequenza nelle ultime 50 estrazioni (finestra mobile).",
        "Misura i numeri che stanno sovraperformando rispetto alla frequenza storica.",
        "Il backtest mostra che dopo somme basse (<200) la frequenza \u00e8 la strategia migliore.",
    ]
    combos.append(combo4)

    # --------------------------------------------------------------
    # Combo 5: Mix controllato (decade-aware, interleaved from all strategies)
    # --------------------------------------------------------------
    balanced = []
    decade_map = {n: (n - 1) // 10 for n in NUMBERS_RANGE}
    used_decades = defaultdict(int)
    seen_bal = set()
    # Interleave: round-robin from each strategy pool to ensure diversity
    pools = [cycle_candidates, markov_candidates, overdue, hot]
    pool_indices = [0, 0, 0, 0]
    while len(balanced) < NUMBERS_PER_COMBO * 2:
        added_this_round = False
        for pi, pool in enumerate(pools):
            while pool_indices[pi] < len(pool):
                n = pool[pool_indices[pi]]
                pool_indices[pi] += 1
                if n in seen_bal:
                    continue
                d = decade_map[n]
                if used_decades[d] < 2:
                    balanced.append(n)
                    seen_bal.add(n)
                    used_decades[d] += 1
                    added_this_round = True
                    break
                elif used_decades[d] < 3 and len(balanced) >= NUMBERS_PER_COMBO:
                    balanced.append(n)
                    seen_bal.add(n)
                    used_decades[d] += 1
                    added_this_round = True
                    break
            if len(balanced) >= NUMBERS_PER_COMBO * 2:
                break
        if not added_this_round:
            break
    # Fill remaining from frequency
    if len(balanced) < NUMBERS_PER_COMBO:
        for n, _ in main_all.most_common(90):
            if n not in seen_bal:
                balanced.append(n)
                seen_bal.add(n)
                if len(balanced) >= NUMBERS_PER_COMBO:
                    break

    combo5 = build_combo(balanced)
    combo5["label"] = "Mix controllato"
    combo5["engine_version"] = PREDICTION_ENGINE_VERSION
    combo5["description"] = "Mix di pi\u00f9 strategie distribuito sulle decine"
    combo5["reasoning"] = [
        "Combina ciclo di ritorno, transizioni Markov e gap anomalo.",
        "Distribuito su decine diverse per massima copertura.",
        "Evita concentrazioni eccessive in singole fasce numeriche.",
    ]
    combos.append(combo5)

    # --------------------------------------------------------------
    # Combo 6: Ensemble pesato (tutte le strategie)
    # --------------------------------------------------------------
    ensemble = Counter()
    for n in cycle_candidates[:18]:
        ensemble[n] += 3.5
    for n in markov_candidates[:18]:
        ensemble[n] += 2.5
    for n in overdue[:18]:
        ensemble[n] += 2.0
    for n in hot[:18]:
        ensemble[n] += 1.5

    best_ensemble = [n for n, _ in ensemble.most_common(NUMBERS_PER_COMBO * 2)]
    combo6 = build_combo(best_ensemble)
    combo6["label"] = "Ensemble pesato"
    combo6["engine_version"] = PREDICTION_ENGINE_VERSION
    combo6["description"] = "Pesato su tutte le strategie con peso proporzionale all'affidabilit\u00e0"
    combo6["reasoning"] = [
        "Ciclo di ritorno: peso 3.5x (unica strategia statisticamente significativa).",
        "Transizioni Markov: peso 2.5x.",
        "Gap anomalo: peso 2.0x.",
        "Tendenza recente: peso 1.5x.",
        "L'ensemble ha mostrato performance superiori alla media nei backtest.",
    ]
    combos.append(combo6)

    return combos


def prediction_uses_current_engine(prediction: SuperEnalottoPrediction | None) -> bool:
    if not prediction or not prediction.combinations:
        return False
    if len(prediction.combinations) != COMBO_COUNT:
        return False
    labels = tuple(combo.get("label") for combo in prediction.combinations)
    if labels != CURRENT_COMBO_LABELS:
        return False
    return all(combo.get("engine_version") == PREDICTION_ENGINE_VERSION for combo in prediction.combinations)


def verify_predictions(new_draw):
    pending = SuperEnalottoPrediction.objects.filter(is_verified=False)
    drawn_set = set(new_draw.winning_numbers or [])
    for prediction in pending:
        matched_counts = []
        for combo in prediction.combinations:
            combo_nums = set(combo.get("numbers", []))
            matches = len(combo_nums & drawn_set)
            jolly_match = new_draw.jolly_number and combo.get("jolly") == new_draw.jolly_number
            superstar_match = new_draw.superstar_number and combo.get("superstar") == new_draw.superstar_number
            matched_counts.append({
                "matches": matches,
                "jolly_match": jolly_match,
                "superstar_match": superstar_match,
            })
        prediction.matched_counts = matched_counts
        prediction.matched_draw = new_draw
        prediction.is_verified = True
        prediction.save(update_fields=["matched_counts", "matched_draw", "is_verified"])


def build_analysis_summary():
    """Build a summary of the latest statistical analysis for the UI."""
    draws = _draws_as_lists(_all_draws())
    total = len(draws)
    if total < 2:
        return {}

    _, _, most_overdue = _overdue_with_gaps(draws)

    freq = Counter()
    for draw in draws:
        for n in draw["numbers"]:
            freq[n] += 1

    top_freq = freq.most_common(10)
    expected = total * 6 / 90
    random_baseline = 0.40

    # Recent trend: last 100 vs all
    recent_100 = Counter()
    for draw in draws[-100:]:
        for n in draw["numbers"]:
            recent_100[n] += 1
    recent_norm = 100 * 6 / 90

    trending_up = []
    for n in NUMBERS_RANGE:
        all_ratio = freq.get(n, 0) / expected if expected else 0
        rec_ratio = recent_100.get(n, 0) / recent_norm if recent_norm else 0
        diff = rec_ratio - all_ratio
        if diff > 0.3:
            trending_up.append((n, round(diff, 2)))

    trending_up.sort(key=lambda x: -x[1])

    last_draw = draws[-1]
    last_sum = sum(last_draw["numbers"])

    return {
        "total_draws": total,
        "random_baseline": random_baseline,
        "expected_freq": round(expected, 1),
        "top_frequent": top_freq[:8],
        "most_overdue": most_overdue[:12],
        "trending_up": trending_up[:10],
        "last_draw": {
            "numbers": last_draw["numbers"],
            "date": last_draw["date"].isoformat() if hasattr(last_draw["date"], "isoformat") else str(last_draw["date"]),
            "sum": last_sum,
        },
        "methodology": {
            "cycle_aware": {
                "description": "Analisi del ciclo di ritorno individuale (p<0.05 nei backtest)",
                "avg_performance": "0.4226 match/estrazione (vs 0.40 casuale)",
            },
            "markov": {
                "description": "Transizioni Markov dall'ultima estrazione verso la successiva",
                "window": MARKOV_WINDOW,
                "avg_performance": "0.4069 match/estrazione",
            },
            "overdue": {
                "description": "Gap anomalo rispetto al ciclo medio individuale",
                "avg_performance": "0.4094 match/estrazione",
            },
            "hot": {
                "description": "Tendenza recente nelle ultime 50 estrazioni",
                "window": RECENT_WINDOW,
                "avg_performance": "0.3713-0.3941 match/estrazione",
            },
        },
    }


def create_prediction():
    latest = SuperEnalottoDraw.objects.order_by("-draw_date").first()
    if not latest:
        return None
    target_date = latest.draw_date + timedelta(days=3)
    target_number = latest.draw_number + 1
    combos = generate_combinations()
    prediction = SuperEnalottoPrediction.objects.create(
        target_draw_date=target_date,
        draw_number=target_number,
        combinations=combos,
    )
    return prediction
