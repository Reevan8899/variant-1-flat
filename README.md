# Практическая работа № 7. Вариант № 1

Менеджер заметок с тегами. Модели, SQLite, обработчики и CLI размещены в корне репозитория. [Вторая реализация](https://github.com/Reevan8899/variant-1-modular)

## Модель данных

- `Note` хранит ID, заголовок, текст, даты создания и изменения, связанные теги.
- `Tag` хранит ID и нормализованное имя. Связь заметок и тегов многие-ко-многим задаёт таблица `note_tags`.

## Запуск

Нужен Python 3.10+. Хранилище по умолчанию `notes.sqlite3`. Чтобы указать другой путь, передайте `--db PATH` до команды или задайте `NOTES_FILE`.

```sh
python -m main add --title "План" --body "Подготовить материалы" --tag Учёба --tag Срочно
python -m main list
python -m main search --query "МАТЕРИАЛЫ"
python -m main search-tag --tag учёба
python -m main edit ID --title "Обновлённый план"
python -m main delete ID
```

Укажите фактический ID из списка. При редактировании `--tag` заменяет набор тегов, `--clear-tags` очищает его. Удаление по указанному ID выполняется сразу.

## Проверка

```sh
python -m pip install -r requirements.txt
python -m pytest --cov=models --cov=database --cov=handlers --cov=main --cov-report=term-missing --cov-fail-under=80
```
