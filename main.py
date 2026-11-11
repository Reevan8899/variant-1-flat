"""CLI менеджера заметок."""

import argparse
import os
import sys
from pathlib import Path

import handlers
from models import Note, NoteError


class NoteParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise NoteError("Неверная команда или параметры. Откройте --help.")


def make_parser() -> NoteParser:
    parser = NoteParser(description="Менеджер заметок и тегов")
    parser.add_argument("--db", type=Path, help="Путь к файлу хранилища")
    commands = parser.add_subparsers(dest="command", required=True)
    add = commands.add_parser("add", help="Создать заметку")
    add.add_argument("--title", required=True)
    add.add_argument("--body", required=True)
    add.add_argument("--tag", dest="tags", action="append", default=[])
    commands.add_parser("list", help="Показать все заметки")
    search = commands.add_parser("search", help="Найти заметки по тексту")
    search.add_argument("--query", required=True)
    search_tag = commands.add_parser("search-tag", help="Найти заметки по тегу")
    search_tag.add_argument("--tag", required=True)
    edit = commands.add_parser("edit", help="Изменить заметку")
    edit.add_argument("id")
    edit.add_argument("--title")
    edit.add_argument("--body")
    tags = edit.add_mutually_exclusive_group()
    tags.add_argument("--tag", dest="tags", action="append")
    tags.add_argument("--clear-tags", dest="tags", action="store_const", const=[])
    commands.add_parser("delete", help="Удалить заметку").add_argument("id")
    return parser


def print_notes(notes: list[Note]) -> None:
    if not notes:
        print("Заметки не найдены.")
        return
    print("ID | Заголовок | Теги")
    for note in notes:
        tags = ", ".join(tag.name for tag in note.tags)
        print(f"{note.id} | {note.title} | {tags}")


def main(argv: list[str] | None = None) -> int:
    try:
        args = make_parser().parse_args(argv)
        path = args.db or Path(os.environ.get("NOTES_FILE", "notes.json"))
        match args.command:
            case "add":
                note = handlers.add_note(path, args.title, args.body, args.tags)
                print(f"Заметка создана. ID: {note.id}")
            case "list":
                print_notes(handlers.list_notes(path))
            case "search":
                print_notes(handlers.search_notes(path, args.query))
            case "search-tag":
                print_notes(handlers.search_tag(path, args.tag))
            case "edit":
                handlers.edit_note(path, args.id, args.title, args.body, args.tags)
                print(f"Заметка обновлена. ID: {args.id}")
            case "delete":
                handlers.delete_note(path, args.id)
                print(f"Заметка удалена. ID: {args.id}")
    except NoteError as error:
        print(f"Ошибка: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
