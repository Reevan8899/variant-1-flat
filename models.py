"""Данные менеджера заметок в плоской структуре."""

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import NAMESPACE_URL, uuid5


class NoteError(Exception):
    """Ошибка, которую может обработать интерфейс."""


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class Tag:
    id: str
    name: str

    @classmethod
    def create(cls, name: str) -> "Tag":
        return cls(uuid5(NAMESPACE_URL, f"note-tag:{name}").hex, name)


@dataclass(frozen=True)
class Note:
    id: str
    title: str
    body: str
    created_at: str
    updated_at: str
    tags: tuple[Tag, ...]
