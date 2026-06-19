from pathlib import Path


def test_installer_batch_is_ascii_launcher_without_bom():
    data = Path("build_installer.bat").read_bytes()

    assert data.startswith(b"@echo off")
    assert not data.startswith(b"\xef\xbb\xbf")
    data.decode("ascii")


def test_installer_powershell_is_utf8_and_russian():
    source = Path("installer/build_installer.ps1").read_text(encoding="utf-8-sig")

    assert "АСУД — сборка фирменного установщика" in source
    assert "Сборка завершена успешно" in source
    assert "РђРЎРЈР”" not in source
