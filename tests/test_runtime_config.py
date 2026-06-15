import sys

from asud import config


def test_frozen_runtime_dir_uses_device_local_app_data(monkeypatch, tmp_path):
    fake_exe = tmp_path / "dist" / "ASUD.exe"
    local_app_data = tmp_path / "LocalAppData"
    fake_exe.parent.mkdir()
    fake_exe.write_text("", encoding="utf-8")
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(fake_exe))
    monkeypatch.setenv("LOCALAPPDATA", str(local_app_data))

    assert config.get_runtime_dir() == local_app_data / "ASUD"


def test_default_runtime_config_uses_runtime_dir_for_local_state(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "get_runtime_dir", lambda: tmp_path)

    runtime_config = config.build_default_config()

    assert runtime_config["db_path"] == str(tmp_path / "asud.sqlite3")
    assert runtime_config["users_file"] == str(tmp_path / "users.json")
    assert runtime_config["persistence_file"] == str(tmp_path / "last_data.csv")
    assert runtime_config["audit_log"] == str(tmp_path / "audit.log")
    assert runtime_config["backup_dir"] == str(tmp_path / "backups")
