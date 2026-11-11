"""JSON-хранилище с прежними функциями модуля database."""

import json
import os
import tempfile
from contextlib import contextmanager
from dataclasses import asdict, replace
from pathlib import Path

from filelock import FileLock, Timeout

from models import Note, NoteError, Tag


def load_all(path: Path) -> list[Note]:
    try:
        with path.open(encoding="utf-8") as source:
            records = json.load(source)
        if not isinstance(records, list):
            raise ValueError("Expected a list of notes")
        notes = []
        for record in records:
            fields = dict(record)
            fields["tags"] = tuple(Tag(**tag) for tag in fields["tags"])
            notes.append(Note(**fields))
        notes.sort(key=lambda note: note.id)
        return sorted(notes, key=lambda note: note.created_at, reverse=True)
    except FileNotFoundError:
        return []
    except (OSError, TypeError, ValueError, KeyError) as error:
        raise NoteError("Хранилище JSON недоступно. Проверьте путь и формат файла.") from error


@contextmanager
def _write_notes(path: Path):
    path = path.resolve()
    lock = FileLock(path.with_name(f"{path.name}.lock"), timeout=2)
    try:
        with lock:
            notes = load_all(path)
            yield notes
            fd, name = tempfile.mkstemp(dir=path.parent, prefix=".notes-", suffix=".tmp")
            temporary = Path(name)
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as target:
                    json.dump([asdict(note) for note in notes], target, ensure_ascii=False)
                    target.flush()
                    os.fsync(target.fileno())
                os.replace(temporary, path)
            finally:
                temporary.unlink(missing_ok=True)
    except (OSError, Timeout) as error:
        raise NoteError("Хранилище JSON недоступно. Проверьте права доступа и повторите операцию.") from error


def _index(notes: list[Note], note_id: str) -> int:
    for index, note in enumerate(notes):
        if note.id == note_id:
            return index
    raise NoteError(f"Заметка {note_id} не найдена.")


def insert(path: Path, note: Note) -> None:
    with _write_notes(path) as notes:
        notes.append(note)


def update(path: Path, note_id: str, title: str | None, body: str | None, tags: tuple[Tag, ...] | None, updated_at: str) -> None:
    with _write_notes(path) as notes:
        index = _index(notes, note_id)
        original = notes[index]
        notes[index] = replace(
            original,
            title=original.title if title is None else title,
            body=original.body if body is None else body,
            tags=original.tags if tags is None else tags,
            updated_at=updated_at,
        )


def delete(path: Path, note_id: str) -> None:
    with _write_notes(path) as notes:
        del notes[_index(notes, note_id)]
