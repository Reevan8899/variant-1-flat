"""Единые проверки пользовательских команд для Flat и Modular."""

import csv
import re

import pytest

from main import main


@pytest.fixture
def cli(tmp_path, capsys):
    path = tmp_path / "test-notes"

    def run(*args, code=0):
        assert main(["--db", str(path), *args]) == code
        return capsys.readouterr()

    return run, path


def create(run, title, body="Содержимое", tags=()):
    flags = [argument for tag in tags for argument in ("--tag", tag)]
    output = run("add", "--title", title, "--body", body, *flags).out
    return re.search(r"ID: ([a-f0-9]{32})", output)[1]


def test_empty_list(cli):
    run, _ = cli
    assert "Заметки не найдены" in run("list").out


def test_add_and_list(cli):
    run, path = cli
    note = create(run, " План ", tags=["Учёба"])
    assert path.is_file()
    assert f"{note} | План | учёба" in run("list").out


def test_list_shows_newest_first(cli):
    run, _ = cli
    old = create(run, "Первая")
    new = create(run, "Вторая")
    output = run("list").out
    assert output.index(new) < output.index(old)


def test_text_search_matches_title_and_body(cli):
    run, _ = cli
    first = create(run, "План встречи")
    second = create(run, "Документ", body="Подготовить план")
    other = create(run, "Книги")
    output = run("search", "--query", "ПЛАН").out
    assert first in output and second in output and other not in output


def test_search_no_matches(cli):
    run, _ = cli
    create(run, "Задача")
    assert "Заметки не найдены" in run("search", "--query", "другое").out


def test_many_to_many_tags_and_deduplication(cli):
    run, _ = cli
    first = create(run, "Первый", tags=["Проект", " ПРоЕКТ ", "СРОЧНО"])
    second = create(run, "Второй", tags=["проект"])
    third = create(run, "Личное", tags=["срочно"])
    output = run("search-tag", "--tag", "ПРОЕКТ").out
    assert first in output and second in output and third not in output
    assert f"{first} | Первый | проект, срочно" in output
    assert "Заметки не найдены" in run("search-tag", "--tag", "про").out
    run("delete", first)
    output = run("search-tag", "--tag", "проект").out
    assert first not in output and second in output


def test_edit_preserves_unspecified_values(cli):
    run, _ = cli
    note = create(run, "Старая", body="Прежний текст", tags=["срок"])
    assert note in run("edit", note, "--title", "Новая").out
    assert f"{note} | Новая | срок" in run("search", "--query", "прежний").out
    run("edit", note, "--body", "Иной текст", "--tag", "Новый")
    assert note in run("search", "--query", "иной").out
    assert note in run("search-tag", "--tag", "новый").out
    assert note not in run("search-tag", "--tag", "срок").out


def test_clear_tags(cli):
    run, _ = cli
    note = create(run, "Тема", tags=["Работа"])
    run("edit", note, "--clear-tags")
    assert note not in run("search-tag", "--tag", "Работа").out
    assert note in run("list").out


@pytest.mark.parametrize("command", ["edit", "delete"])
def test_missing_id(cli, command):
    run, _ = cli
    extra = ["--title", "Новая"] if command == "edit" else []
    assert "не найдена" in run(command, "missing", *extra, code=2).err


@pytest.mark.parametrize(("flags", "field"), [
    (["--title", " ", "--body", "Текст"], "Заголовок"),
    (["--title", "a" * 101, "--body", "Текст"], "Заголовок"),
    (["--title", "Тема", "--body", " "], "Текст"),
    (["--title", "Тема", "--body", "a" * 10_001], "Текст"),
    (["--title", "Тема", "--body", "Текст", "--tag", "a" * 41], "Тег"),
], ids=["empty-title", "long-title", "empty-body", "long-body", "long-tag"])
def test_add_validation(cli, flags, field):
    run, _ = cli
    assert field in run("add", *flags, code=2).err
    assert "Заметки не найдены" in run("list").out


def test_inclusive_limits(cli):
    run, _ = cli
    note = create(run, "я" * 100, body="я" * 10_000, tags=["я" * 40])
    assert note in run("list").out


def test_invalid_edit_leaves_original(cli):
    run, _ = cli
    note = create(run, "Тема", tags=["исходный"])
    assert "Укажите хотя бы" in run("edit", note, code=2).err
    assert "Текст" in run("edit", note, "--title", "Новая", "--body", " ", code=2).err
    assert f"{note} | Тема | исходный" in run("list").out


def test_invalid_queries_and_cli_syntax(cli):
    run, _ = cli
    assert "Запрос" in run("search", "--query", " ", code=2).err
    assert "Тег" in run("search-tag", "--tag", " ", code=2).err
    assert "Неверная команда" in run("search", code=2).err


def test_invalid_storage_is_preserved(cli):
    run, path = cli
    path.write_bytes(b"invalid storage")
    assert "Хранилище" in run("list", code=2).err
    assert path.read_bytes() == b"invalid storage"


def test_export_to_csv(cli, tmp_path):
    run, _ = cli
    note = create(run, "Тема, с запятой", body="Текст\nна второй строке", tags=["работа"])
    path = tmp_path / "export.csv"
    run("export", "--output", str(path))
    with path.open(encoding="utf-8", newline="") as source:
        rows = list(csv.reader(source))
    assert rows == [["id", "title", "body", "tags"], [note, "Тема, с запятой", "Текст\nна второй строке", "работа"]]
    assert "CSV" in run("export", "--output", str(path), code=2).err
