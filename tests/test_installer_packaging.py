from pathlib import Path

from PIL import Image


def test_inno_setup_script_is_russian_per_user_and_clean():
    source = Path("installer/ASUD.iss").read_text(encoding="utf-8-sig")
    normalized = source.lower()

    assert "wizardstyle=modern" in normalized
    assert "privilegesrequired=lowest" in normalized
    assert r"defaultdirname={localappdata}\programs\asud" in normalized
    assert r'messagesfile: "compiler:languages\russian.isl"' in normalized
    assert r'source: "..\dist\asud.exe"' in normalized
    assert "асуд" in normalized
    assert "вмеда им. с.м. кирова" in normalized

    runtime_files = (
        "asud.sqlite3",
        "users.json",
        "config.json",
        "last_data.csv",
        "audit.log",
    )
    files_section = normalized.split("[files]", maxsplit=1)[1].split("[", maxsplit=1)[0]
    assert all(filename not in files_section for filename in runtime_files)


def test_installer_has_brand_assets_shortcuts_and_launch():
    source = Path("installer/ASUD.iss").read_text(encoding="utf-8-sig").lower()

    assert "wizardimagefile=assets\\wizard-large.bmp" in source
    assert "wizardsmallimagefile=assets\\wizard-small.bmp" in source
    assert r'name: "{autoprograms}\асуд"' in source
    assert r'name: "{autodesktop}\асуд"' in source
    assert "postinstall" in source
    assert "nowait" in source


def test_installer_pipeline_builds_exe_assets_and_setup():
    launcher = Path("build_installer.bat").read_text(encoding="ascii").lower()
    script = Path("installer/build_installer.ps1").read_text(encoding="utf-8-sig").lower()

    assert "chcp 65001" in launcher
    assert "installer\\build_installer.ps1" in launcher
    assert "build_exe.bat" in script
    assert "--no-pause" in script
    assert "generate_installer_assets.py" in script
    assert "iscc.exe" in script
    assert "asud.iss" in script
    assert "asud-setup-$appversion.exe" in script
    assert "winget install jrsoftware.innosetup" in script
    assert "nopause" in script


def test_generated_installer_assets_have_inno_dimensions():
    with Image.open("installer/assets/wizard-large.bmp") as image:
        assert image.format == "BMP"
        assert image.mode == "RGB"
        assert image.size == (164, 314)

    with Image.open("installer/assets/wizard-small.bmp") as image:
        assert image.format == "BMP"
        assert image.mode == "RGB"
        assert image.size == (55, 55)


def test_installer_outputs_are_ignored_by_git():
    gitignore = Path(".gitignore").read_text(encoding="utf-8-sig")

    assert "release/" in gitignore
    assert "installer/assets/*.bmp" in gitignore
