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

## Локальные файлы выполнения

Приложение может создавать `config.json`, `users.json`, `last_data.csv`, `audit.log`, `backups/` и позднее `asud.sqlite3`. Эти файлы содержат локальное состояние и не входят в исходный код проекта.
