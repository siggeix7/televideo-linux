from __future__ import annotations

from datetime import date, timedelta

from django.utils import timezone


SUPERENALOTTO_DRAW_WEEKDAYS = (1, 3, 4, 5)  # martedi, giovedi, venerdi, sabato
SUPERENALOTTO_DRAW_TIME = "20:00"
SUPERENALOTTO_PLAY_DEADLINE = "19:30"
WEEKDAY_LABELS = (
    "lunedi",
    "martedi",
    "mercoledi",
    "giovedi",
    "venerdi",
    "sabato",
    "domenica",
)


def next_draw_date_after(value: date) -> date:
    candidate = value + timedelta(days=1)
    while candidate.weekday() not in SUPERENALOTTO_DRAW_WEEKDAYS:
        candidate += timedelta(days=1)
    return candidate


def next_draw_target(latest_draw) -> tuple[date | None, int | None]:
    if latest_draw is None:
        return None, None
    return next_draw_date_after(latest_draw.draw_date), latest_draw.draw_number + 1


def draw_date_payload(draw_date: date, draw_number: int | None = None) -> dict[str, object]:
    return {
        "date": draw_date.isoformat(),
        "display_date": draw_date.strftime("%d/%m/%Y"),
        "weekday": WEEKDAY_LABELS[draw_date.weekday()],
        "draw_number": draw_number,
        "draw_time": SUPERENALOTTO_DRAW_TIME,
        "play_deadline": SUPERENALOTTO_PLAY_DEADLINE,
    }


def upcoming_draws_after(
    latest_draw_date: date | None,
    latest_draw_number: int | None = None,
    count: int = 4,
) -> list[dict[str, object]]:
    if latest_draw_date is None:
        current = timezone.localdate() - timedelta(days=1)
    else:
        current = latest_draw_date

    next_number = latest_draw_number + 1 if latest_draw_number is not None else None
    draws = []
    for _ in range(count):
        current = next_draw_date_after(current)
        draws.append(draw_date_payload(current, next_number))
        if next_number is not None:
            next_number += 1
    return draws
