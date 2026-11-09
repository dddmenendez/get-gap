"""Fuentes de calendario.

Cada proveedor solo tiene que saber devolver bloques ocupados en un rango.
- ManualProvider: lo que el usuario marca a mano (ya implementado).
- Google (freeBusy API vía OAuth) e iCloud (CalDAV con contraseña de
  aplicación) se añadirán implementando este mismo protocolo.
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from .models import BusyInterval


class CalendarProvider(Protocol):
    def get_busy(self, start: datetime, end: datetime) -> list[BusyInterval]: ...


class ManualProvider:
    def __init__(self, busy: list[BusyInterval] | None = None) -> None:
        self._busy = list(busy or [])

    def get_busy(self, start: datetime, end: datetime) -> list[BusyInterval]:
        return [b for b in self._busy if b.overlaps(start, end)]
