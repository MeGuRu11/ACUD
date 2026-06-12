"""SQLite persistence and legacy file migration."""

from __future__ import annotations

import json
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd


class SQLiteStorage:
    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        if self.db_path.parent != Path("."):
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.initialize()

    def initialize(self):
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL,
                full_name TEXT NOT NULL,
                created_at TEXT NOT NULL,
                last_login TEXT,
                force_password_change INTEGER NOT NULL DEFAULT 0,
                extra_json TEXT NOT NULL DEFAULT '{}'
            );

            CREATE TABLE IF NOT EXISTS records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                position INTEGER NOT NULL,
                data_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT,
                role TEXT,
                action TEXT NOT NULL,
                details TEXT,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            """
        )
        self.conn.commit()

    def load_users(self) -> dict[str, dict[str, Any]]:
        rows = self.conn.execute("SELECT * FROM users ORDER BY username").fetchall()
        users = {}
        for row in rows:
            data = {
                "password_hash": row["password_hash"],
                "role": row["role"],
                "full_name": row["full_name"],
                "created_at": row["created_at"],
                "last_login": row["last_login"],
                "force_password_change": bool(row["force_password_change"]),
            }
            data.update(json.loads(row["extra_json"] or "{}"))
            users[row["username"]] = data
        return users

    def save_users(self, users: dict[str, dict[str, Any]]):
        with self.conn:
            self.conn.execute("DELETE FROM users")
            for username, data in users.items():
                known = {
                    "password_hash",
                    "role",
                    "full_name",
                    "created_at",
                    "last_login",
                    "force_password_change",
                }
                extra = {k: v for k, v in data.items() if k not in known}
                self.conn.execute(
                    """
                    INSERT INTO users (
                        username, password_hash, role, full_name, created_at,
                        last_login, force_password_change, extra_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        username,
                        data["password_hash"],
                        data.get("role", "viewer"),
                        data.get("full_name", username),
                        data.get("created_at", datetime.now().isoformat()),
                        data.get("last_login"),
                        1 if data.get("force_password_change", False) else 0,
                        json.dumps(extra, ensure_ascii=False),
                    ),
                )

    def load_records(self) -> pd.DataFrame:
        rows = self.conn.execute("SELECT data_json FROM records ORDER BY position, id").fetchall()
        if not rows:
            return pd.DataFrame()
        records = [json.loads(row["data_json"]) for row in rows]
        columns_row = self.conn.execute("SELECT value FROM settings WHERE key = 'record_columns'").fetchone()
        columns = json.loads(columns_row["value"]) if columns_row else None
        return pd.DataFrame(records, columns=columns)

    def save_records(self, df: pd.DataFrame):
        clean_df = df.astype(object).where(pd.notna(df), None)
        now = datetime.now().isoformat()
        with self.conn:
            self.conn.execute("DELETE FROM records")
            self.conn.execute(
                """
                INSERT OR REPLACE INTO settings (key, value)
                VALUES ('record_columns', ?)
                """,
                (json.dumps(clean_df.columns.tolist(), ensure_ascii=False),),
            )
            for position, record in enumerate(clean_df.to_dict(orient="records")):
                self.conn.execute(
                    """
                    INSERT INTO records (position, data_json, created_at, updated_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (position, json.dumps(record, ensure_ascii=False), now, now),
                )

    def append_audit(self, username: str | None, role: str | None, action: str, details: str = ""):
        with self.conn:
            self.conn.execute(
                """
                INSERT INTO audit_log (username, role, action, details, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (username, role, action, details, datetime.now().isoformat()),
            )

    def list_audit(self) -> list[dict[str, Any]]:
        rows = self.conn.execute("SELECT * FROM audit_log ORDER BY id").fetchall()
        return [dict(row) for row in rows]

    def has_users(self) -> bool:
        row = self.conn.execute("SELECT 1 FROM users LIMIT 1").fetchone()
        return row is not None

    def has_records(self) -> bool:
        row = self.conn.execute("SELECT 1 FROM records LIMIT 1").fetchone()
        return row is not None

    def migrate_from_files(
        self,
        users_file: str | Path,
        persistence_file: str | Path,
        backup_dir: str | Path,
    ) -> bool:
        users_path = Path(users_file)
        records_path = Path(persistence_file)
        imported_users = False
        imported_records = False

        if users_path.exists() and not self.has_users():
            users = json.loads(users_path.read_text(encoding="utf-8"))
            self.save_users(users)
            imported_users = True

        if records_path.exists() and not self.has_records():
            self.save_records(pd.read_csv(records_path, encoding="utf-8"))
            imported_records = True

        if not (imported_users or imported_records):
            return False

        target_dir = Path(backup_dir) / f"migration_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        target_dir.mkdir(parents=True, exist_ok=True)
        if users_path.exists():
            shutil.copy2(users_path, target_dir / users_path.name)
        if records_path.exists():
            shutil.copy2(records_path, target_dir / records_path.name)
        return True

    def close(self):
        self.conn.close()
