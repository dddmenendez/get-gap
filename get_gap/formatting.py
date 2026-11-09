"""Texto listo para pegar en WhatsApp."""

from __future__ import annotations

from collections.abc import Sequence

from .models import Suggestion
from .plans import PlanTemplate

DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
MESES = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]


def _fecha(s: Suggestion) -> str:
    d = s.start
    return f"{DIAS[d.weekday()]} {d.day} de {MESES[d.month - 1]}"


def describe(plan: PlanTemplate, s: Suggestion) -> str:
    if plan.multi_day:
        fin = s.end
        when = (
            f"del {_fecha(s)} ({s.start:%H:%M}) "
            f"al {DIAS[fin.weekday()]} {fin.day} ({fin:%H:%M})"
        )
    else:
        when = f"{_fecha(s)}, {s.start:%H:%M}-{s.end:%H:%M}"
    who = "vamos todos ✅" if s.all_in else f"falta: {', '.join(s.unavailable)}"
    return f"{when} · {who}"


def whatsapp_text(plan: PlanTemplate, suggestions: Sequence[Suggestion]) -> str:
    if not suggestions:
        return f"📅 {plan.label}: no hay ningún hueco que encaje en esas fechas 😕"
    lines = [f"📅 {plan.label}: opciones"]
    lines += [f"{i}. {describe(plan, s)}" for i, s in enumerate(suggestions, 1)]
    return "\n".join(lines)
