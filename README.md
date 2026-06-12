# ASUD

Локальное desktop-приложение для учета диссертаций, импорта Excel-таблиц, редактирования записей, управления пользователями и экспорта отчетов в Excel/Word.

## Текущий стек

- Python 3.12
- Tkinter
- pandas / openpyxl
- python-docx
- Pillow
- matplotlib
- bcrypt

## Установка

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Запуск

```powershell
python ASUD.py
```

При первом запуске приложение предложит создать администратора. Автоматическая учетная запись `admin/admin` больше не создается.

## Локальные файлы выполнения

Приложение может создавать `config.json`, `asud.sqlite3`, `audit.log` и `backups/`. Старые `users.json` и `last_data.csv`, если они есть, импортируются в SQLite при первом запуске с сохранением копии в `backups/migration_<дата>/`.

## Проверки

```powershell
pytest
python -m py_compile ASUD.py asud\*.py asud\ui\*.py
ruff check .
```
