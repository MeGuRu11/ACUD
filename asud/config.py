"""Configuration defaults and shared constants for ASUD."""

from __future__ import annotations

import os
import sys
from pathlib import Path

APP_DATA_DIR_NAME = "ASUD"
RUNTIME_CONFIG_KEYS = {
    "persistence_file",
    "audit_log",
    "backup_dir",
    "users_file",
    "db_path",
}


def get_project_dir() -> Path:
    return Path(__file__).resolve().parents[1]


def get_runtime_dir() -> Path:
    if getattr(sys, "frozen", False):
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            return Path(local_app_data) / APP_DATA_DIR_NAME
        return Path.home() / f".{APP_DATA_DIR_NAME.lower()}"
    return get_project_dir()


def runtime_path(name: str) -> str:
    return str(get_runtime_dir() / name)


def build_default_config() -> dict[str, str | int]:
    return {
        "logo_path": "logo.png",
        "app_icon_svg": "assets/asud_icon.svg",
        "app_icon_png": "assets/asud_icon.png",
        "persistence_file": runtime_path("last_data.csv"),
        "audit_log": runtime_path("audit.log"),
        "backup_dir": runtime_path("backups"),
        "users_file": runtime_path("users.json"),
        "report_template": "template.docx",
        "default_columns_width": 120,
        "theme": "clam",
        "db_path": runtime_path("asud.sqlite3"),
    }


def normalize_runtime_config(config: dict) -> dict:
    runtime_dir = get_runtime_dir()
    normalized = config.copy()
    for key in RUNTIME_CONFIG_KEYS:
        value = normalized.get(key)
        if not value:
            continue
        path = Path(str(value))
        if not path.is_absolute():
            normalized[key] = str(runtime_dir / path)
    return normalized


CONFIG_FILE = str(get_runtime_dir() / "config.json")
DEFAULT_CONFIG = build_default_config()
APP_ICON_SVG = DEFAULT_CONFIG["app_icon_svg"]
APP_ICON_PNG = DEFAULT_CONFIG["app_icon_png"]
REQUIRED_COLUMNS = [
    "ФИО",
    "Название диссертации",
    "Диссертационный совет",
    "Дата защиты диссертации",
    "Специальность",
    "Искомая степень",
    "Информация о лишении степени",
    "Примечания",
]
DEGREE_OPTIONS = [
    "кандидат медицинских наук",
    "доктор медицинских наук",
]
