from pathlib import Path


def test_build_exe_batch_uses_pyinstaller_with_project_assets():
    script = Path("build_exe.bat").read_text(encoding="utf-8")
    normalized = script.lower()

    assert "chcp 65001" in normalized
    assert "pyinstaller" in normalized
    assert "--onefile" in normalized
    assert "--windowed" in normalized
    assert "--name asud" in normalized
    assert "asud.py" in normalized
    assert "--add-data" in normalized
    assert "assets;assets" in normalized
    assert "asud_icon.ico" in normalized
    assert "dist\\asud.exe" in normalized
    assert "esc" in normalized


def test_pyinstaller_build_artifacts_are_ignored_by_git():
    gitignore = Path(".gitignore").read_text(encoding="utf-8")

    assert "build/" in gitignore
    assert "dist/" in gitignore
    assert "*.spec" in gitignore
    assert "assets/asud_icon.ico" in gitignore
