"""Modelos de dominio de get-gap."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, Field, model_validator


def _new_id() -> str:
    return uuid4().hex[:12]


class CalendarSource(str, Enum):
    """De dónde sacamos la disponibilidad de un miembro."""

    MANUAL = "manual"
    GOOGLE = "google"
    ICLOUD = "icloud"


class BusyInterval(BaseModel):
    """Bloque ocupado. Solo libre/ocupado: nunca guardamos títulos ni detalles."""

    start: datetime
    end: datetime

    @model_validator(mode="after")
    def _check(self) -> "BusyInterval":
        if self.start.tzinfo is None or self.end.tzinfo is None:
            raise ValueError("start y end deben llevar zona horaria")
        if self.end <= self.start:
            raise ValueError("end debe ser posterior a start")
        return self

    def overlaps(self, start: datetime, end: datetime) -> bool:
        return self.start < end and start < self.end


class Member(BaseModel):
    id: str = Field(default_factory=_new_id)
    name: str
    source: CalendarSource = CalendarSource.MANUAL
    busy: list[BusyInterval] = Field(default_factory=list)

    def is_free(self, start: datetime, end: datetime) -> bool:
        return not any(b.overlaps(start, end) for b in self.busy)


class Group(BaseModel):
    id: str = Field(default_factory=_new_id)
    name: str
    timezone: str = "Europe/Madrid"
    members: list[Member] = Field(default_factory=list)

    def member(self, member_id: str) -> Member | None:
        return next((m for m in self.members if m.id == member_id), None)


class Suggestion(BaseModel):
    """Una fecha propuesta para el plan."""

    start: datetime
    end: datetime
    available: list[str]  # nombres de quien puede ir
    unavailable: list[str]
    score: float

    @property
    def all_in(self) -> bool:
        return not self.unavailable
