"""Проверка данных и обработка команд менеджера заметок."""

from pathlib import Path
from uuid import uuid4

import database
from models import Note, NoteError, Tag, now


def _required(value: str, field: str, maximum: int) -> str:
    cleaned = value.strip()
    if not cleaned or len(cleaned) > maximum:
        raise NoteError(f"{field} должен содержать от 1 до {maximum} символов.")
    return cleaned


def _tag_name(value: str) -> str:
    return _required(" ".join(value.split()).casefold(), "Тег", 40)


def _tags(values: list[str]) -> tuple[Tag, ...]:
    return tuple(Tag.create(name) for name in sorted({_tag_name(value) for value in values}))


def add_note(path: Path, title: str, body: str, tags: list[str]) -> Note:
    timestamp = now()
    note = Note(uuid4().hex, _required(title, "Заголовок", 100), _required(body, "Текст", 10_000), timestamp, timestamp, _tags(tags))
    database.insert(path, note)
    return note


def list_notes(path: Path) -> list[Note]:
    return database.load_all(path)


def search_notes(path: Path, query: str) -> list[Note]:
    needle = _required(query, "Запрос", 10_000).casefold()
    return [note for note in list_notes(path) if needle in note.title.casefold() or needle in note.body.casefold()]


def search_tag(path: Path, tag: str) -> list[Note]:
    target = _tag_name(tag)
    return [note for note in list_notes(path) if any(item.name == target for item in note.tags)]


def edit_note(path: Path, note_id: str, title: str | None, body: str | None, tags: list[str] | None) -> None:
    if title is None and body is None and tags is None:
        raise NoteError("Укажите хотя бы одно изменение.")
    cleaned_title = None if title is None else _required(title, "Заголовок", 100)
    cleaned_body = None if body is None else _required(body, "Текст", 10_000)
    cleaned_tags = None if tags is None else _tags(tags)
    database.update(path, note_id, cleaned_title, cleaned_body, cleaned_tags, now())


def delete_note(path: Path, note_id: str) -> None:
    database.delete(path, note_id)
