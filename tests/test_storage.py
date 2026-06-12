import json

import pandas as pd

from asud.storage import SQLiteStorage


def test_sqlite_storage_round_trips_users_records_and_audit(tmp_path):
    storage = SQLiteStorage(tmp_path / "asud.sqlite3")
    users = {
        "admin": {
            "password_hash": "hash",
            "role": "admin",
            "full_name": "Administrator",
            "created_at": "2026-06-12T10:00:00",
            "last_login": None,
            "force_password_change": True,
        }
    }
    records = pd.DataFrame(
        [
            {"ФИО": "Иванов И.И.", "Год защиты": 2024, "Примечания": "test"},
            {"ФИО": "Петров П.П.", "Год защиты": None, "Примечания": ""},
        ]
    )

    storage.save_users(users)
    storage.save_records(records)
    storage.append_audit("admin", "admin", "import", "2 rows")

    assert storage.load_users() == users
    loaded_records = storage.load_records()
    assert loaded_records.to_dict(orient="records")[0]["ФИО"] == "Иванов И.И."
    assert list(loaded_records.columns) == ["ФИО", "Год защиты", "Примечания"]
    assert storage.list_audit()[0]["action"] == "import"


def test_sqlite_storage_migrates_legacy_json_and_csv_with_backup(tmp_path):
    users_file = tmp_path / "users.json"
    csv_file = tmp_path / "last_data.csv"
    backup_dir = tmp_path / "backups"
    users_file.write_text(
        json.dumps(
            {
                "editor1": {
                    "password_hash": "hash",
                    "role": "editor",
                    "full_name": "Editor User",
                    "created_at": "2026-06-12T10:00:00",
                    "last_login": None,
                    "force_password_change": False,
                }
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    pd.DataFrame([{"ФИО": "Сидоров С.С.", "Год защиты": 2022}]).to_csv(
        csv_file,
        index=False,
        encoding="utf-8",
    )

    storage = SQLiteStorage(tmp_path / "asud.sqlite3")
    migrated = storage.migrate_from_files(
        users_file=users_file,
        persistence_file=csv_file,
        backup_dir=backup_dir,
    )

    assert migrated is True
    assert "editor1" in storage.load_users()
    assert storage.load_records().iloc[0]["ФИО"] == "Сидоров С.С."
    migration_dirs = list(backup_dir.glob("migration_*"))
    assert len(migration_dirs) == 1
    assert (migration_dirs[0] / "users.json").exists()
    assert (migration_dirs[0] / "last_data.csv").exists()
