"""Операции SQLite для заметок и тегов."""

import sqlite3
from collections import defaultdict
from contextlib import closing, contextmanager
from pathlib import Path

from models import Note, NoteError, Tag

SCHEMA = """
CREATE TABLE IF NOT EXISTS notes (
    id TEXT PRIMARY KEY, title TEXT NOT NULL, body TEXT NOT NULL,
    created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS tags (id TEXT PRIMARY KEY, name TEXT NOT NULL UNIQUE);
CREATE TABLE IF NOT EXISTS note_tags (
    note_id TEXT REFERENCES notes(id) ON DELETE CASCADE,
    tag_id TEXT REFERENCES tags(id), PRIMARY KEY (note_id, tag_id)
);
"""


@contextmanager
def _connect(path: Path):
    try:
        with closing(sqlite3.connect(path)) as connection:
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys = ON")
            connection.executescript(SCHEMA)
            with connection:
                yield connection
    except sqlite3.Error as error:
        raise NoteError("Хранилище SQLite недоступно. Проверьте путь и формат файла.") from error


def _set_tags(connection, note_id: str, tags: tuple[Tag, ...]) -> None:
    connection.execute("DELETE FROM note_tags WHERE note_id = ?", (note_id,))
    connection.executemany("INSERT OR IGNORE INTO tags VALUES (?, ?)", ((tag.id, tag.name) for tag in tags))
    connection.executemany("INSERT INTO note_tags VALUES (?, ?)", ((note_id, tag.id) for tag in tags))


def _prune_tags(connection) -> None:
    connection.execute("DELETE FROM tags WHERE NOT EXISTS (SELECT 1 FROM note_tags WHERE tag_id = tags.id)")


def insert(path: Path, note: Note) -> None:
    with _connect(path) as connection:
        connection.execute("INSERT INTO notes VALUES (?, ?, ?, ?, ?)", (note.id, note.title, note.body, note.created_at, note.updated_at))
        _set_tags(connection, note.id, note.tags)


def load_all(path: Path) -> list[Note]:
    with _connect(path) as connection:
        connection.execute("BEGIN")
        tags_by_note = defaultdict(list)
        for row in connection.execute("SELECT note_id, tags.id, name FROM note_tags JOIN tags ON tags.id = tag_id ORDER BY name"):
            tags_by_note[row["note_id"]].append(Tag(row["id"], row["name"]))
        rows = connection.execute("SELECT * FROM notes ORDER BY created_at DESC, id")
        return [Note(**dict(row), tags=tuple(tags_by_note[row["id"]])) for row in rows]


def update(path: Path, note_id: str, title: str | None, body: str | None, tags: tuple[Tag, ...] | None, updated_at: str) -> None:
    with _connect(path) as connection:
        result = connection.execute(
            "UPDATE notes SET title = COALESCE(?, title), body = COALESCE(?, body), updated_at = ? WHERE id = ?",
            (title, body, updated_at, note_id),
        )
        if result.rowcount == 0:
            raise NoteError(f"Заметка {note_id} не найдена.")
        if tags is not None:
            _set_tags(connection, note_id, tags)
            _prune_tags(connection)


def delete(path: Path, note_id: str) -> None:
    with _connect(path) as connection:
        if connection.execute("DELETE FROM notes WHERE id = ?", (note_id,)).rowcount == 0:
            raise NoteError(f"Заметка {note_id} не найдена.")
        _prune_tags(connection)
