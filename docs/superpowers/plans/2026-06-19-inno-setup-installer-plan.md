# ASUD Inno Setup Installer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Создать, собрать и проверить полностью русскоязычный фирменный установщик `ASUD-Setup-1.0.0.exe` на Inno Setup 6.

**Architecture:** Готовый PyInstaller-файл `dist/ASUD.exe` упаковывается отдельным Inno Setup-сценарием. Фирменные BMP создаются воспроизводимым Python-скриптом из существующей PNG-иконки, а `build_installer.bat` оркестрирует генерацию ресурсов, сборку EXE и компиляцию установщика. Runtime-данные не являются источниками установщика.

**Tech Stack:** Inno Setup 6, Windows Batch, Python 3.12, Pillow, pytest.

---

### Task 1: Зафиксировать контракт установщика тестами

**Files:**
- Create: `tests/test_installer_packaging.py`

- [ ] **Step 1: Write the failing tests**

```python
from pathlib import Path


def test_inno_setup_script_is_russian_per_user_and_clean():
    source = Path("installer/ASUD.iss").read_text(encoding="utf-8")
    normalized = source.lower()
    assert "wizardstyle=modern" in normalized
    assert "privilegesrequired=lowest" in normalized
    assert r"defaultdirname={localappdata}\programs\asud" in normalized
    assert r'messagesfile: "compiler:languages\russian.isl"' in normalized
    assert r'source: "..\dist\asud.exe"' in normalized
    assert "asud.sqlite3" not in normalized
    assert "users.json" not in normalized
    assert "config.json" not in normalized
    assert "last_data.csv" not in normalized


def test_installer_has_brand_assets_and_shortcuts():
    source = Path("installer/ASUD.iss").read_text(encoding="utf-8").lower()
    assert "wizardimagefile=assets\\wizard-large.bmp" in source
    assert "wizardsmallimagefile=assets\\wizard-small.bmp" in source
    assert r'name: "{autoprograms}\асуд"' in source
    assert r'name: "{autodesktop}\асуд"' in source
    assert "postinstall" in source


def test_installer_batch_builds_exe_assets_and_setup():
    source = Path("build_installer.bat").read_text(encoding="utf-8").lower()
    assert "build_exe.bat --no-pause" in source
    assert "generate_installer_assets.py" in source
    assert "iscc.exe" in source
    assert "installer\\asud.iss" in source
    assert "release\\asud-setup-1.0.0.exe" in source
```

- [ ] **Step 2: Run tests to verify RED**

Run: `python -m pytest -q tests/test_installer_packaging.py`

Expected: FAIL because `installer/ASUD.iss` and `build_installer.bat` do not exist.

### Task 2: Создать воспроизводимые фирменные изображения мастера

**Files:**
- Create: `installer/generate_installer_assets.py`
- Generate: `installer/assets/wizard-large.bmp`
- Generate: `installer/assets/wizard-small.bmp`

- [ ] **Step 1: Implement the asset generator**

The script must:

- open `assets/asud_icon.png`;
- create a 164×314 dark `#102D36` wizard image with the logo, `АСУД`, subtitle and teal accents;
- create a 55×55 white/teal small wizard image;
- save 24-bit BMP files supported by Inno Setup;
- accept project paths relative to its own location.

- [ ] **Step 2: Generate the assets**

Run: `python installer/generate_installer_assets.py`

Expected: both BMP files exist and Pillow reports `BMP`, `RGB`, and the required dimensions.

- [ ] **Step 3: Add asset checks**

Extend `tests/test_installer_packaging.py`:

```python
from PIL import Image


def test_generated_installer_assets_have_inno_dimensions():
    with Image.open("installer/assets/wizard-large.bmp") as image:
        assert image.format == "BMP"
        assert image.mode == "RGB"
        assert image.size == (164, 314)
    with Image.open("installer/assets/wizard-small.bmp") as image:
        assert image.format == "BMP"
        assert image.mode == "RGB"
        assert image.size == (55, 55)
```

Run: `python -m pytest -q tests/test_installer_packaging.py`

Expected: script tests still fail only because the ISS/batch files are not complete.

### Task 3: Реализовать Inno Setup-сценарий

**Files:**
- Create: `installer/ASUD.iss`

- [ ] **Step 1: Configure setup metadata**

Use:

```ini
#define MyAppName "АСУД"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "ВМедА им. С.М. Кирова"
#define MyAppExeName "ASUD.exe"

[Setup]
AppId={{5A23EAE1-DBED-4B16-94B2-56A2A6AD7FD8}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\Programs\ASUD
PrivilegesRequired=lowest
WizardStyle=modern
SetupIconFile=..\assets\asud_icon.ico
WizardImageFile=assets\wizard-large.bmp
WizardSmallImageFile=assets\wizard-small.bmp
OutputDir=..\release
OutputBaseFilename=ASUD-Setup-{#MyAppVersion}
Compression=lzma2/ultra64
SolidCompression=yes
UninstallDisplayIcon={app}\{#MyAppExeName}
```

- [ ] **Step 2: Add Russian language, tasks, files, shortcuts and launch**

The script includes only `..\dist\ASUD.exe`, creates Start/Desktop shortcuts, and offers launch after installation. Add Russian custom messages describing clean installation and administrator creation on first launch.

- [ ] **Step 3: Run packaging tests**

Run: `python -m pytest -q tests/test_installer_packaging.py`

Expected: ISS tests pass; batch test still fails.

### Task 4: Реализовать русскоязычную сборку установщика

**Files:**
- Create: `build_installer.bat`
- Modify: `.gitignore`

- [ ] **Step 1: Create build_installer.bat**

The batch script:

- enables UTF-8 with `chcp 65001`;
- detects `ISCC.exe` in PATH and standard Inno Setup 6 locations;
- prints a Russian six-step banner;
- runs the asset generator;
- runs `build_exe.bat --no-pause`;
- compiles `installer\ASUD.iss`;
- checks `release\ASUD-Setup-1.0.0.exe`;
- prints the result size and path;
- supports `--no-pause` and `--help`;
- suggests `winget install JRSoftware.InnoSetup` if the compiler is missing.

- [ ] **Step 2: Ignore generated outputs**

Add:

```gitignore
release/
installer/assets/*.bmp
```

- [ ] **Step 3: Run tests**

Run: `python -m pytest -q tests/test_installer_packaging.py tests/test_packaging_script.py`

Expected: PASS.

### Task 5: Install Inno Setup and build the release

**Files:**
- Generate: `release/ASUD-Setup-1.0.0.exe`
- Generate: `build/inno_setup_build.log`

- [ ] **Step 1: Install compiler if missing**

Run: `winget install JRSoftware.InnoSetup --accept-package-agreements --accept-source-agreements`

Expected: Inno Setup 6 installed and `ISCC.exe` available in a standard location.

- [ ] **Step 2: Build installer**

Run: `cmd /c build_installer.bat --no-pause`

Expected: exit code 0 and `release/ASUD-Setup-1.0.0.exe`.

- [ ] **Step 3: Verify produced binary**

Run PowerShell checks for file existence, size, version information, and SHA-256. Confirm the ISS source list contains only `ASUD.exe`.

### Task 6: Full verification and documentation

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Document installer build and clean-install behavior**

Add Russian commands:

```powershell
.\build_installer.bat
```

Describe output path, Inno Setup dependency, per-user install location, and persistence of `%LOCALAPPDATA%\ASUD`.

- [ ] **Step 2: Run full verification**

Run:

```powershell
python -m pytest -q
ruff check .
python -m py_compile ASUD.py asud\*.py asud\ui\*.py installer\generate_installer_assets.py
cmd /c build_installer.bat --no-pause
```

Expected: tests and lint pass; installer build exits 0.

- [ ] **Step 3: Review Git diff**

Confirm no runtime databases, user files, logs, backups, generated release files, or temporary Word files are staged.

- [ ] **Step 4: Commit and push**

```powershell
git add .gitignore README.md build_installer.bat installer tests/test_installer_packaging.py docs/superpowers/plans/2026-06-19-inno-setup-installer-plan.md
git commit -m "feat: add branded Russian installer"
git push origin main
```
