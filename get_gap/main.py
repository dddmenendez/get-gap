"""API HTTP de get-gap.

Arrancar en local:  uvicorn get_gap.main:app --reload
Documentación interactiva: http://127.0.0.1:8000/docs
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from . import __version__
from .engine import SearchParams, find_slots
from .formatting import whatsapp_text
from .models import BusyInterval, Group, Member, Suggestion
from .plans import PLANS, get_plan
from .storage import InMemoryStore

app = FastAPI(title="get-gap", version=__version__)
store = InMemoryStore()

DEFAULT_RANGE_DAYS = 30
MAX_RANGE_DAYS = 366


# ---------- esquemas de entrada/salida ----------


class GroupIn(BaseModel):
    name: str
    timezone: str = "Europe/Madrid"


class MemberIn(BaseModel):
    name: str


class SuggestIn(BaseModel):
    plan: str = Field(examples=["cena"])
    date_from: date | None = None
    date_to: date | None = None
    min_attendees: int | None = Field(None, ge=1)
    required: list[str] = Field(default_factory=list, description="ids de miembros imprescindibles")
    limit: int = Field(3, ge=1, le=10)
    duration_hours: float | None = Field(None, gt=0, description="sobrescribe la duración del plan")


class SuggestOut(BaseModel):
    plan: str
    suggestions: list[Suggestion]
    whatsapp_text: str


class PlanOut(BaseModel):
    key: str
    label: str
    duration_hours: float


# ---------- helpers ----------


def _group_or_404(group_id: str) -> Group:
    group = store.get(group_id)
    if group is None:
        raise HTTPException(404, "Grupo no encontrado")
    return group


# ---------- endpoints ----------


@app.get("/plans", response_model=list[PlanOut])
def list_plans() -> list[PlanOut]:
    return [
        PlanOut(key=p.key, label=p.label, duration_hours=p.duration.total_seconds() / 3600)
        for p in PLANS.values()
    ]


@app.post("/groups", response_model=Group, status_code=201)
def create_group(body: GroupIn) -> Group:
    try:
        ZoneInfo(body.timezone)
    except Exception:
        raise HTTPException(422, f"Zona horaria no válida: {body.timezone}") from None
    return store.save(Group(name=body.name, timezone=body.timezone))


@app.get("/groups/{group_id}", response_model=Group)
def get_group(group_id: str) -> Group:
    return _group_or_404(group_id)


@app.post("/groups/{group_id}/members", response_model=Member, status_code=201)
def add_member(group_id: str, body: MemberIn) -> Member:
    group = _group_or_404(group_id)
    member = Member(name=body.name)
    group.members.append(member)
    store.save(group)
    return member


@app.put("/groups/{group_id}/members/{member_id}/busy", response_model=Member)
def set_busy(group_id: str, member_id: str, busy: list[BusyInterval]) -> Member:
    """Marcado manual: sustituye los bloques ocupados del miembro."""
    group = _group_or_404(group_id)
    member = group.member(member_id)
    if member is None:
        raise HTTPException(404, "Miembro no encontrado")
    member.busy = busy
    store.save(group)
    return member


@app.post("/groups/{group_id}/suggest", response_model=SuggestOut)
def suggest(group_id: str, body: SuggestIn) -> SuggestOut:
    group = _group_or_404(group_id)
    try:
        plan = get_plan(body.plan)
    except KeyError as e:
        raise HTTPException(422, str(e)) from None
    if body.duration_hours:
        plan = plan.with_duration(timedelta(hours=body.duration_hours))

    unknown = set(body.required) - {m.id for m in group.members}
    if unknown:
        raise HTTPException(422, f"Miembros desconocidos en required: {sorted(unknown)}")

    tz = ZoneInfo(group.timezone)
    now = datetime.now(tz)
    date_from = body.date_from or now.date()
    date_to = body.date_to or date_from + timedelta(days=DEFAULT_RANGE_DAYS)
    if date_to < date_from:
        raise HTTPException(422, "date_to debe ser >= date_from")
    if (date_to - date_from).days > MAX_RANGE_DAYS:
        raise HTTPException(422, f"El rango máximo es de {MAX_RANGE_DAYS} días")

    params = SearchParams(
        date_from=date_from,
        date_to=date_to,
        timezone=group.timezone,
        min_attendees=body.min_attendees,
        required=frozenset(body.required),
        limit=body.limit,
        not_before=now,
    )
    suggestions = find_slots(plan, group.members, params)
    return SuggestOut(
        plan=plan.key,
        suggestions=suggestions,
        whatsapp_text=whatsapp_text(plan, suggestions),
    )
