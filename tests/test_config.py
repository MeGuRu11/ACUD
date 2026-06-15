import json

from asud.config import DEGREE_OPTIONS, REQUIRED_COLUMNS
from asud import config as config_module
from asud.ui import app as app_module


def test_load_config_merges_new_default_keys(tmp_path, monkeypatch):
    monkeypatch.setattr(config_module, "get_runtime_dir", lambda: tmp_path)
    monkeypatch.setattr(app_module, "CONFIG_FILE", str(tmp_path / "config.json"))
    monkeypatch.setattr(app_module, "DEFAULT_CONFIG", config_module.build_default_config())
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps({"theme": "clam", "backup_dir": "backups"}, ensure_ascii=False),
        encoding="utf-8",
    )
    app = app_module.DissertationReportApp.__new__(app_module.DissertationReportApp)

    config = app.load_config()

    assert config["db_path"] == str(tmp_path / "asud.sqlite3")
    assert config["users_file"] == str(tmp_path / "users.json")
    assert config["backup_dir"] == str(tmp_path / "backups")
    assert config["theme"] == "clam"
    saved_config = json.loads(config_path.read_text(encoding="utf-8"))
    assert saved_config["db_path"] == str(tmp_path / "asud.sqlite3")
    assert saved_config["users_file"] == str(tmp_path / "users.json")
    assert saved_config["backup_dir"] == str(tmp_path / "backups")


def test_save_config_creates_missing_runtime_parent(tmp_path, monkeypatch):
    config_path = tmp_path / "device-runtime" / "config.json"
    monkeypatch.setattr(app_module, "CONFIG_FILE", str(config_path))
    app = app_module.DissertationReportApp.__new__(app_module.DissertationReportApp)

    app.save_config({"theme": "clam"})

    assert config_path.exists()
    assert json.loads(config_path.read_text(encoding="utf-8")) == {"theme": "clam"}


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
