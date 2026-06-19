from pathlib import Path


def test_installer_pipeline_can_install_missing_inno_setup_and_log_failures():
    source = Path("installer/build_installer.ps1").read_text(encoding="utf-8-sig")
    normalized = source.lower()

    assert "function install-innosetup" in normalized
    assert "get-command winget.exe" in normalized
    assert "jrsoftware.innosetup" in normalized
    assert "--accept-package-agreements" in normalized
    assert "--accept-source-agreements" in normalized
    assert "installer_pipeline.log" in normalized
    assert "find-innocompiler" in normalized
    assert "install-innosetup" in normalized
