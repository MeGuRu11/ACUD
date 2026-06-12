import json

from asud.config import DEGREE_OPTIONS, REQUIRED_COLUMNS
from asud.ui.app import DissertationReportApp


def test_load_config_merges_new_default_keys(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps({"theme": "clam", "backup_dir": "backups"}, ensure_ascii=False),
        encoding="utf-8",
    )
    app = DissertationReportApp.__new__(DissertationReportApp)

    config = app.load_config()

    assert config["db_path"] == "asud.sqlite3"
    assert config["theme"] == "clam"
    saved_config = json.loads(config_path.read_text(encoding="utf-8"))
    assert saved_config["db_path"] == "asud.sqlite3"


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
