"""Almacenamiento en memoria. Se sustituirá por una base de datos."""

from __future__ import annotations

from .models import Group


class InMemoryStore:
    def __init__(self) -> None:
        self._groups: dict[str, Group] = {}

    def save(self, group: Group) -> Group:
        self._groups[group.id] = group
        return group

    def get(self, group_id: str) -> Group | None:
        return self._groups.get(group_id)

    def clear(self) -> None:
        self._groups.clear()
