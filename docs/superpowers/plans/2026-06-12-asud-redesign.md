# ASUD Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the ASUD desktop interface so it matches the approved redesign, keeps the existing Tkinter stack, and verifies the core workflow from authorization through records, filters, and reports.

**Architecture:** Keep business logic in `asud/auth.py`, `asud/data_model.py`, `asud/storage.py`, and `asud/reports.py`; concentrate UI composition in `asud/ui/app.py` and dialog composition in `asud/ui/dialogs.py`. Create a stronger design-system layer in `asud/ui/theme.py` with shared colors, fonts, spacing, text labels, and widget helper functions so the main window and dialogs stop hardcoding colors.

**Tech Stack:** Python 3.12, Tkinter/ttk, pandas, SQLite, python-docx/openpyxl, pytest, ruff.

---

## File Structure

- Modify: `asud/config.py`
  - Restore Russian column constants and degree options.
  - Keep config defaults stable and backward-compatible.
- Modify: `asud/ui/theme.py`
  - Define the approved palette, font tokens, spacing tokens, role labels, status labels, and reusable style helpers.
  - Configure ttk styles for tree tables, buttons, labels, entries, comboboxes, notebooks, and dialogs.
- Modify: `asud/ui/app.py`
  - Rebuild the main window as top bar, left navigation, filter/search toolbar, workbench table, status bar, and role-aware action groups.
  - Keep existing commands and permissions but improve labels, statuses, and empty states.
- Modify: `asud/ui/dialogs.py`
  - Rebuild login, initial admin setup, registration, password change, user management, filters, column selector, and record editor with the shared design system.
  - Remove hardcoded dark-green/gold fragments and emoji-heavy labels.
- Modify: `tests/test_config.py`
  - Verify Russian constants are not corrupted.
- Modify: `tests/test_ui_theme.py`
  - Verify the approved palette/style tokens and label dictionaries exist.
- Modify: `tests/test_ui_regressions.py`
  - Verify the main UI references the new layout helpers/texts and keeps permission-sensitive buttons.
- Create: `tests/test_ui_dialogs_static.py`
  - Static regression coverage that dialogs use the shared theme helpers instead of hardcoded legacy palette strings.
- Keep: `design/asud_redesign_mockup.html`
  - Approved visual reference, not production runtime.
- Keep: `.vscode/launch.json`
  - Stable launcher for VS Code.

---

### Task 1: Lock Data and Theme Contracts

**Files:**
- Modify: `tests/test_config.py`
- Modify: `tests/test_ui_theme.py`
- Modify: `asud/config.py`
- Modify: `asud/ui/theme.py`

- [ ] **Step 1: Write failing tests for Russian constants and theme tokens**

Add to `tests/test_config.py`:

```python
from asud.config import DEGREE_OPTIONS, REQUIRED_COLUMNS


def test_required_columns_are_readable_russian_labels():
    assert REQUIRED_COLUMNS == [
        "ФИО",
        "Название диссертации",
        "Диссертационный совет",
        "Дата защиты диссертации",
        "Специальность",
        "Искомая степень",
        "Информация о лишении степени",
        "Примечания",
    ]
    assert all("?" not in column for column in REQUIRED_COLUMNS)


def test_degree_options_are_readable_russian_labels():
    assert DEGREE_OPTIONS == [
        "кандидат медицинских наук",
        "доктор медицинских наук",
    ]
```

Replace `tests/test_ui_theme.py` assertions with:

```python
from asud.ui.theme import APP_THEME, FONT, ROLE_LABELS, SPACING, WINDOW_MINSIZE


def test_theme_defines_approved_palette_and_window_size():
    assert WINDOW_MINSIZE == (1180, 720)
    assert APP_THEME["app_background"] == "#eef2f6"
    assert APP_THEME["topbar"] == "#10242d"
    assert APP_THEME["primary"] == "#245c63"
    assert APP_THEME["primary_alt"] == "#1f7a70"
    assert APP_THEME["accent"] == "#b38b24"
    assert APP_THEME["surface"] == "#ffffff"


def test_theme_defines_typography_spacing_and_role_labels():
    assert FONT["family"] == "Segoe UI"
    assert SPACING["panel"] == 16
    assert ROLE_LABELS == {
        "admin": "Администратор",
        "editor": "Редактор",
        "viewer": "Наблюдатель",
    }
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```powershell
pytest tests/test_config.py tests/test_ui_theme.py -q
```

Expected: failures for corrupted `REQUIRED_COLUMNS`, old `WINDOW_MINSIZE`, and missing `FONT`, `SPACING`, `ROLE_LABELS`.

- [ ] **Step 3: Implement constants and theme tokens**

Update `asud/config.py` to use readable Russian constants shown in Step 1.

Update `asud/ui/theme.py` with approved palette names:

```python
WINDOW_MINSIZE = (1180, 720)

APP_THEME = {
    "app_background": "#eef2f6",
    "topbar": "#10242d",
    "topbar_text": "#ffffff",
    "topbar_muted": "#b9c7d6",
    "surface": "#ffffff",
    "surface_soft": "#f8fafc",
    "sidebar": "#ffffff",
    "line": "#d9e0ea",
    "text": "#18212f",
    "muted_text": "#657084",
    "primary": "#245c63",
    "primary_alt": "#1f7a70",
    "accent": "#b38b24",
    "accent_soft": "#e2c164",
    "danger": "#b3343a",
    "success": "#287a4e",
    "table_background": "#ffffff",
    "table_heading": "#f3f6fa",
    "table_selected": "#e8f4f1",
}
```

Also keep compatibility aliases for any old code still being migrated:

```python
APP_THEME["background"] = APP_THEME["app_background"]
APP_THEME["panel"] = APP_THEME["sidebar"]
APP_THEME["accent_active"] = "#9f7a1f"
APP_THEME["table_text"] = APP_THEME["text"]
```

- [ ] **Step 4: Run targeted tests**

Run:

```powershell
pytest tests/test_config.py tests/test_ui_theme.py -q
```

Expected: all selected tests pass.

- [ ] **Step 5: Commit**

Run:

```powershell
git add asud/config.py asud/ui/theme.py tests/test_config.py tests/test_ui_theme.py
git commit -m "feat: define approved asud design tokens"
```

---

### Task 2: Main Window Redesign

**Files:**
- Modify: `tests/test_ui_regressions.py`
- Modify: `asud/ui/app.py`
- Modify: `asud/ui/theme.py`

- [ ] **Step 1: Write failing static tests for the redesigned shell**

Add to `tests/test_ui_regressions.py`:

```python
def test_main_window_uses_redesigned_shell_sections():
    app_source = Path("asud/ui/app.py").read_text(encoding="utf-8")

    assert "build_topbar" in app_source
    assert "build_sidebar" in app_source
    assert "build_workbench" in app_source
    assert "Реестр диссертаций" in app_source
    assert "База данных активна" in app_source
    assert "Загрузить Excel" in app_source
    assert "Новая запись" in app_source


def test_main_window_uses_shared_theme_not_legacy_fonts():
    app_source = Path("asud/ui/app.py").read_text(encoding="utf-8")

    assert "APP_THEME[\"topbar\"]" in app_source
    assert "FONT[\"family\"]" in app_source
    assert "Times New Roman" not in app_source
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
pytest tests/test_ui_regressions.py::test_main_window_uses_redesigned_shell_sections tests/test_ui_regressions.py::test_main_window_uses_shared_theme_not_legacy_fonts -q
```

Expected: fails because helper methods and new theme usage are not present yet.

- [ ] **Step 3: Implement redesigned shell**

Refactor `asud/ui/app.py`:

- `build_ui()` configures root background, style, and calls:
  - `build_topbar()`
  - `build_sidebar()`
  - `build_workbench()`
  - `build_statusbar()`
  - `bind_shortcuts()`
- `build_topbar()` shows compact brand, page title `Реестр диссертаций`, DB state, current user, and role label.
- `build_sidebar()` uses grouped action buttons:
  - `Данные`: `Загрузить Excel`, `Новая запись`, `Редактировать`, `Удалить`
  - `Отбор`: `Расширенный фильтр`, `Сбросить отбор`
  - `Выгрузка`: `Excel`, `Word`, `Статистика`
  - `Администрирование`: `Пользователи`, `Сменить пользователя`, `Выход`
- `build_workbench()` creates search, year filter, active filter summary, table title, and `ttk.Treeview`.
- Preserve button attributes used by permissions:
  - `self.btn_load`
  - `self.btn_add`
  - `self.btn_edit`
  - `self.btn_delete`
  - `self.btn_users`

- [ ] **Step 4: Run targeted tests**

Run:

```powershell
pytest tests/test_ui_regressions.py tests/test_ui_theme.py -q
```

Expected: all selected tests pass.

- [ ] **Step 5: Commit**

Run:

```powershell
git add asud/ui/app.py asud/ui/theme.py tests/test_ui_regressions.py
git commit -m "feat: redesign main asud workspace"
```

---

### Task 3: Dialog Redesign

**Files:**
- Create: `tests/test_ui_dialogs_static.py`
- Modify: `asud/ui/dialogs.py`
- Modify: `asud/ui/theme.py`

- [ ] **Step 1: Write failing static tests for dialog design**

Create `tests/test_ui_dialogs_static.py`:

```python
from pathlib import Path


def test_dialogs_use_shared_theme_helpers():
    source = Path("asud/ui/dialogs.py").read_text(encoding="utf-8")

    assert "DialogBase" in source
    assert "create_dialog_button" in source
    assert "APP_THEME" in source
    assert "FONT" in source


def test_dialogs_do_not_use_legacy_palette_or_emoji_labels():
    source = Path("asud/ui/dialogs.py").read_text(encoding="utf-8")

    for legacy in ["#0b2a1b", "#1a3d2a", "#d4af37", "Times New Roman"]:
        assert legacy not in source

    for label in ["🔍", "🔑", "✏️", "🗑️", "➕", "❌", "📝", "🔐"]:
        assert label not in source
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
pytest tests/test_ui_dialogs_static.py -q
```

Expected: fails because dialogs still use legacy palette and fonts.

- [ ] **Step 3: Implement shared dialog helpers and restyle dialogs**

Update `asud/ui/dialogs.py`:

- Import shared tokens/helpers from `asud.ui.theme`.
- Add `DialogBase` for:
  - creating centered `Toplevel`
  - applying surface background
  - consistent header
  - consistent footer buttons
  - consistent form rows
- Update these classes to use the shared helpers:
  - `LoginDialog`
  - `InitialAdminDialog`
  - `ChangePasswordDialog`
  - `RegistrationDialog`
  - `AddUserDialog`
  - `EditUserDialog`
  - `UserManagementDialog`
  - `FilterDialog`
  - `ColumnSelectorDialog`
  - `RecordDialog`
- Replace emoji labels with clear desktop labels:
  - `Пароль`
  - `Изменить`
  - `Удалить`
  - `Добавить`
  - `Закрыть`
  - `Поиск`
- Keep all existing public class names and constructor signatures.

- [ ] **Step 4: Run targeted tests**

Run:

```powershell
pytest tests/test_ui_dialogs_static.py tests/test_ui_regressions.py -q
```

Expected: all selected tests pass.

- [ ] **Step 5: Commit**

Run:

```powershell
git add asud/ui/dialogs.py asud/ui/theme.py tests/test_ui_dialogs_static.py
git commit -m "feat: redesign asud dialogs"
```

---

### Task 4: Workflow Texts, Statuses, and Role States

**Files:**
- Modify: `tests/test_ui_regressions.py`
- Modify: `asud/ui/app.py`
- Modify: `asud/ui/dialogs.py`

- [ ] **Step 1: Write failing tests for improved workflow text**

Add to `tests/test_ui_regressions.py`:

```python
def test_ui_uses_clear_workflow_status_texts():
    app_source = Path("asud/ui/app.py").read_text(encoding="utf-8")

    assert "Данные сохранены" in app_source
    assert "Загрузка Excel" in app_source
    assert "Экспорт отчёта" in app_source
    assert "По фильтру ничего не найдено" in app_source
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
pytest tests/test_ui_regressions.py::test_ui_uses_clear_workflow_status_texts -q
```

Expected: fails until statuses are rewritten.

- [ ] **Step 3: Improve text and states**

Update UI texts:

- Initial status: `Готово. Данные будут сохранены в локальную базу SQLite.`
- After login: `Пользователь: <login> | <role label>`
- Loading: `Загрузка Excel...`
- Load success: `Данные загружены и сохранены.`
- Export: `Экспорт отчёта...`
- Export success: `Отчёт сохранён: <path>`
- Filters reset: `Отбор сброшен`
- No records: `Данные не загружены`
- No filter result: `По фильтру ничего не найдено`

Keep permissions:

- Admin: all actions.
- Editor: data load, add, edit, delete, filter/export; no user management.
- Viewer: search/filter/export only if data exists, no mutation actions.

- [ ] **Step 4: Run targeted tests**

Run:

```powershell
pytest tests/test_ui_regressions.py -q
```

Expected: all UI regression tests pass.

- [ ] **Step 5: Commit**

Run:

```powershell
git add asud/ui/app.py asud/ui/dialogs.py tests/test_ui_regressions.py
git commit -m "feat: polish workflow labels and role states"
```

---

### Task 5: Full Verification

**Files:**
- Modify only if verification finds issues.

- [ ] **Step 1: Run unit and regression tests**

Run:

```powershell
pytest -q
```

Expected: all tests pass.

- [ ] **Step 2: Run lint**

Run:

```powershell
ruff check .
```

Expected: no lint errors.

- [ ] **Step 3: Run import/compile check**

Run:

```powershell
python -m py_compile ASUD.py asud/main.py asud/ui/app.py asud/ui/dialogs.py asud/ui/theme.py
```

Expected: no output and exit code 0.

- [ ] **Step 4: Run Tk smoke check**

Run:

```powershell
python -c "import tkinter as tk; from asud.ui.app import DissertationReportApp; root=tk.Tk(); app=DissertationReportApp.__new__(DissertationReportApp); root.destroy(); print('tk-smoke-ok')"
```

Expected: `tk-smoke-ok`.

- [ ] **Step 5: Commit verification fixes or final metadata**

Run if files changed after verification:

```powershell
git add .
git commit -m "chore: verify redesigned asud app"
```

---

## Self-Review

- Spec coverage:
  - Approved visual direction: Task 1, Task 2, Task 3.
  - Full design and palette rework: Task 1, Task 2, Task 3.
  - Text cleanup: Task 4.
  - Authorization through system workflow verification: Task 3, Task 4, Task 5 plus existing auth/storage/report tests.
  - Keep the app working: every task has targeted verification and Task 5 has full verification.
- Placeholder scan:
  - No `TBD`, `TODO`, or undefined future placeholders are used in executable steps.
- Type consistency:
  - `APP_THEME`, `FONT`, `SPACING`, `ROLE_LABELS`, `WINDOW_MINSIZE`, and existing public dialog/app class names are consistent across tasks.
