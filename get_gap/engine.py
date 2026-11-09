"""Motor que cruza agendas y propone fechas para un plan."""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from .models import Member, Suggestion
from .plans import PlanTemplate

PREFERRED_WEEKDAY_BONUS = 10.0
MAX_START_PENALTY = 10.0
DAY_PENALTY = 0.1  # ligera preferencia por fechas más cercanas


@dataclass(frozen=True)
class SearchParams:
    date_from: date
    date_to: date
    timezone: str = "Europe/Madrid"
    min_attendees: int | None = None  # por defecto: todos
    required: frozenset[str] = frozenset()  # ids que tienen que ir sí o sí
    limit: int = 3
    not_before: datetime | None = None  # normalmente "ahora"


def iter_candidates(
    plan: PlanTemplate, date_from: date, date_to: date, tz: ZoneInfo
) -> Iterator[tuple[datetime, datetime]]:
    """Genera todos los (inicio, fin) posibles del plan en el rango."""
    day = date_from
    while day <= date_to:
        if day.weekday() in plan.weekdays:
            window_open = datetime.combine(day, plan.window_start, tzinfo=tz)
            window_close = window_open + plan.window_length
            start = window_open
            while start + plan.duration <= window_close:
                yield start, start + plan.duration
                start += plan.step
        day += timedelta(days=1)


def _score(
    plan: PlanTemplate,
    start: datetime,
    n_available: int,
    total: int,
    date_from: date,
) -> float:
    score = 100.0 * n_available / total
    if start.weekday() in plan.preferred_weekdays:
        score += PREFERRED_WEEKDAY_BONUS
    if plan.preferred_start is not None:
        preferred = start.replace(
            hour=plan.preferred_start.hour, minute=plan.preferred_start.minute
        )
        minutes_off = abs((start - preferred).total_seconds()) / 60
        score -= min(MAX_START_PENALTY, minutes_off / 30)
    score -= DAY_PENALTY * (start.date() - date_from).days
    return round(score, 2)


def find_slots(
    plan: PlanTemplate, members: Sequence[Member], params: SearchParams
) -> list[Suggestion]:
    """Devuelve las mejores fechas para el plan, ordenadas de mejor a peor.

    Criterio: primero las que permiten ir a más gente; a igualdad, la
    puntuación del plan (día preferido, hora preferida, cercanía).
    Nunca propone dos opciones que se solapen ni dos el mismo día.
    """
    if not members:
        return []
    if params.date_to < params.date_from:
        raise ValueError("date_to debe ser >= date_from")

    tz = ZoneInfo(params.timezone)
    total = len(members)
    min_att = total if params.min_attendees is None else params.min_attendees
    min_att = max(1, min(min_att, total))

    scored: list[tuple[int, float, Suggestion]] = []
    for start, end in iter_candidates(plan, params.date_from, params.date_to, tz):
        if params.not_before and start < params.not_before:
            continue
        free = [m for m in members if m.is_free(start, end)]
        if len(free) < min_att:
            continue
        free_ids = {m.id for m in free}
        if not params.required <= free_ids:
            continue
        score = _score(plan, start, len(free), total, params.date_from)
        scored.append(
            (
                len(free),
                score,
                Suggestion(
                    start=start,
                    end=end,
                    available=[m.name for m in free],
                    unavailable=[m.name for m in members if m.id not in free_ids],
                    score=score,
                ),
            )
        )

    scored.sort(key=lambda t: (-t[0], -t[1], t[2].start))

    picked: list[Suggestion] = []
    for _, _, s in scored:
        if any(_clashes(s, p) for p in picked):
            continue
        picked.append(s)
        if len(picked) >= params.limit:
            break
    return picked


def _clashes(a: Suggestion, b: Suggestion) -> bool:
    if a.start < b.end and b.start < a.end:
        return True
    return a.start.date() == b.start.date()
