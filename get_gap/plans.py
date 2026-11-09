"""Plantillas de plan: cada tipo de quedada define cuándo y cuánto dura.

Todos los planes se describen igual:
- `weekdays`: días de la semana en que puede EMPEZAR (0=lunes ... 6=domingo).
- `window_start` + `window_length`: franja en la que cabe el plan ese día.
- `duration`: lo que dura. Si `duration == window_length` hay un único
  candidato por día (p. ej. un viaje de viernes tarde a domingo noche).
- `preferred_start`: hora ideal; los huecos más cercanos puntúan mejor.
- `preferred_weekdays`: días que suman puntos (p. ej. cenas en viernes/sábado).
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import time, timedelta

ALL_DAYS = frozenset(range(7))


@dataclass(frozen=True)
class PlanTemplate:
    key: str
    label: str
    duration: timedelta
    window_start: time
    window_length: timedelta
    weekdays: frozenset[int] = ALL_DAYS
    preferred_start: time | None = None
    preferred_weekdays: frozenset[int] = field(default_factory=frozenset)
    step: timedelta = timedelta(minutes=30)

    def __post_init__(self) -> None:
        if self.duration > self.window_length:
            raise ValueError(f"{self.key}: duration no cabe en la franja")

    @property
    def multi_day(self) -> bool:
        return self.duration >= timedelta(hours=24)

    def with_duration(self, duration: timedelta) -> "PlanTemplate":
        """Copia con otra duración, ampliando la franja si hace falta."""
        return replace(
            self, duration=duration, window_length=max(self.window_length, duration)
        )


PLANS: dict[str, PlanTemplate] = {
    p.key: p
    for p in [
        PlanTemplate(
            key="cafe",
            label="Café",
            duration=timedelta(hours=1),
            window_start=time(9, 0),
            window_length=timedelta(hours=12),
            preferred_start=time(18, 0),
        ),
        PlanTemplate(
            key="comida",
            label="Comida",
            duration=timedelta(hours=2),
            window_start=time(13, 30),
            window_length=timedelta(hours=3, minutes=30),
            preferred_start=time(14, 0),
            preferred_weekdays=frozenset({5, 6}),
        ),
        PlanTemplate(
            key="cena",
            label="Cena",
            duration=timedelta(hours=2, minutes=30),
            window_start=time(20, 30),
            window_length=timedelta(hours=3, minutes=30),  # hasta las 00:00
            preferred_start=time(21, 0),
            preferred_weekdays=frozenset({3, 4, 5}),  # jueves, viernes, sábado
        ),
        PlanTemplate(
            key="deporte",
            label="Deporte",
            duration=timedelta(hours=1, minutes=30),
            window_start=time(8, 0),
            window_length=timedelta(hours=14),
            preferred_start=time(10, 0),
            preferred_weekdays=frozenset({5, 6}),
        ),
        PlanTemplate(
            key="finde",
            label="Plan de día completo",
            duration=timedelta(hours=10),
            window_start=time(10, 0),
            window_length=timedelta(hours=10),
            weekdays=frozenset({5, 6}),
        ),
        PlanTemplate(
            key="escapada",
            label="Escapada (sábado-domingo)",
            duration=timedelta(days=1, hours=10),  # sáb 10:00 -> dom 20:00
            window_start=time(10, 0),
            window_length=timedelta(days=1, hours=10),
            weekdays=frozenset({5}),
        ),
        PlanTemplate(
            key="viaje",
            label="Viaje (viernes tarde-domingo)",
            duration=timedelta(days=2, hours=7),  # vie 15:00 -> dom 22:00
            window_start=time(15, 0),
            window_length=timedelta(days=2, hours=7),
            weekdays=frozenset({4}),
        ),
    ]
}


def get_plan(key: str) -> PlanTemplate:
    try:
        return PLANS[key]
    except KeyError:
        raise KeyError(f"Plan desconocido: {key}. Opciones: {', '.join(PLANS)}") from None
