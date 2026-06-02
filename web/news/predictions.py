from collections import Counter
from datetime import timedelta

from django.db.models import Count, Q
from django.utils import timezone

from .models import SuperEnalottoDraw, SuperEnalottoPrediction


SUPERENALOTTO_MAX_NUMBER = 90
NUMBERS_RANGE = range(1, SUPERENALOTTO_MAX_NUMBER + 1)
COMBO_COUNT = 6
NUMBERS_PER_COMBO = 6
RECENT_WINDOW = 50


def _all_draws():
    return SuperEnalottoDraw.objects.order_by("draw_date")


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


def cold_numbers(main_counter, bottom=18):
    all_present = set(main_counter.keys())
    never_drawn = [n for n in NUMBERS_RANGE if n not in all_present]
    sorted_asc = [num for num, _ in main_counter.most_common()[::-1]]
    result = never_drawn + sorted_asc
    return result[:bottom]


def overdue_numbers(draws_queryset):
    last_seen = {}
    for draw in draws_queryset:
        numbers = draw.winning_numbers or []
        date = draw.draw_date
        for n in numbers:
            if n not in last_seen:
                last_seen[n] = date
    today = timezone.localdate()
    absence = {}
    for n in NUMBERS_RANGE:
        if n in last_seen:
            absence[n] = (today - last_seen[n]).days
        else:
            absence[n] = 9999
    return sorted(absence, key=absence.get, reverse=True)


def generate_combinations(draws_queryset=None):
    if draws_queryset is None:
        draws_queryset = _all_draws()

    recent = draws_queryset.order_by("-draw_date")[:RECENT_WINDOW]
    main_counter, jolly_counter, superstar_counter = number_frequencies(recent)
    main_all, _, _ = number_frequencies(draws_queryset)

    hot = hot_numbers(main_counter, top=NUMBERS_PER_COMBO * 3)
    cold = cold_numbers(main_all, bottom=NUMBERS_PER_COMBO * 3)
    overdue = overdue_numbers(draws_queryset)[:NUMBERS_PER_COMBO * 3]

    combos = []

    def pick_jolly(exclude):
        candidates = [n for n, _ in jolly_counter.most_common(12) if n not in exclude]
        if not candidates:
            candidates = [n for n in NUMBERS_RANGE if n not in exclude]
        return candidates[0] if candidates else 1

    def pick_superstar(exclude):
        candidates = [n for n, _ in superstar_counter.most_common(12) if n not in exclude]
        if not candidates:
            candidates = [n for n in NUMBERS_RANGE if n not in exclude]
        return candidates[0] if candidates else 1

    def build_combo(nums):
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
        jolly = pick_jolly(set(selected))
        superstar = pick_superstar(set(selected) | {jolly})
        return {"numbers": selected, "jolly": jolly, "superstar": superstar}

    combo1 = build_combo(hot)
    combos.append({"label": "Numeri caldi", "description": "I numeri piu frequenti nelle ultime estrazioni", **combo1})

    combo2 = build_combo(cold)
    combos.append({"label": "Numeri freddi", "description": "I numeri meno frequenti nello storico", **combo2})

    balanced = []
    hot_set = set(hot)
    cold_set = set(cold)
    decade_map = {n: (n - 1) // 10 for n in NUMBERS_RANGE}
    for _ in range(NUMBERS_PER_COMBO // 2):
        for pool in (hot, cold):
            for n in pool:
                if n not in balanced:
                    decade = decade_map[n]
                    if len([x for x in balanced if decade_map[x] == decade]) < 1:
                        balanced.append(n)
                        break
    remaining = [n for n in (hot + cold) if n not in balanced]
    balanced.extend(remaining[:NUMBERS_PER_COMBO - len(balanced)])
    combo3 = build_combo(balanced)
    combos.append({"label": "Bilanciato", "description": "Mix di numeri caldi e freddi su decine diverse", **combo3})

    combo4 = build_combo([n for n in hot if n not in balanced][:NUMBERS_PER_COMBO * 2] + [n for n in hot if n % 2 == 0][:NUMBERS_PER_COMBO])
    combos.append({"label": "Pattern", "description": "Basato su sequenze e pattern statistici", **combo4})

    combo5 = build_combo(overdue)
    combos.append({"label": "Ritardatari", "description": "I numeri che mancano da piu estrazioni", **combo5})

    weighted = []
    max_freq = max(main_all.values()) if main_all else 1
    weights = {}
    for n in NUMBERS_RANGE:
        freq = main_all.get(n, 0)
        weights[n] = max_freq - freq + 1
    total_weight = sum(weights.values())
    combo6_nums = []
    while len(combo6_nums) < NUMBERS_PER_COMBO * 3 and total_weight > 0:
        import random
        r = random.randint(1, total_weight)
        cumulative = 0
        for n, w in weights.items():
            if n in combo6_nums:
                continue
            cumulative += w
            if cumulative >= r:
                combo6_nums.append(n)
                weights[n] = 0
                total_weight = sum(weights.values())
                break
        if len(combo6_nums) >= NUMBERS_PER_COMBO * 3:
            break
    combo6 = build_combo(combo6_nums)
    combos.append({"label": "Probabilistico", "description": "Pesato sulla frequenza inversa dei numeri", **combo6})

    return combos


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
