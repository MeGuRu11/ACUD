from pathlib import Path


def test_build_exe_batch_uses_pyinstaller_with_project_assets():
    script = Path("build_exe.bat").read_text(encoding="utf-8")
    normalized = script.lower()

    assert "chcp 65001" in normalized
    assert "pyinstaller" in normalized
    assert "--onefile" in normalized
    assert "--windowed" in normalized
    assert "--name asud" in normalized
    assert "--log-level warn" in normalized
    assert "asud.py" in normalized
    assert "build\\pyinstaller_build.log" in normalized
    assert "> \"%build_log%\" 2>&1" in normalized
    assert "--add-data" in normalized
    assert "project_dir=%~dp0" in normalized
    assert "icon_ico_file=%project_dir%assets\\asud_icon.ico" in normalized
    assert "pyinstaller_assets=%project_dir%assets;assets" in normalized
    assert "assets;assets" in normalized
    assert "asud_icon.ico" in normalized
    assert "--icon \"%icon_ico_file%\"" in normalized
    assert "--icon=%icon_ico_file%" not in normalized
    assert "dist\\asud.exe" in normalized
    assert "--no-pause" in normalized
    assert "set \"esc=" not in normalized
    assert "%esc%" not in normalized
    assert "[ok]" in normalized
    assert "[info]" in normalized
    assert "[error]" in normalized


def test_build_exe_batch_does_not_bundle_runtime_state():
    script = Path("build_exe.bat").read_text(encoding="utf-8").lower()

    assert "asud.sqlite3" not in script
    assert "users.json" not in script
    assert "config.json" not in script
    assert "last_data.csv" not in script
    assert "audit.log" not in script


def test_pyinstaller_build_artifacts_are_ignored_by_git():
    gitignore = Path(".gitignore").read_text(encoding="utf-8")

    assert "build/" in gitignore
    assert "dist/" in gitignore
    assert "*.spec" in gitignore
    assert "assets/asud_icon.ico" in gitignore
