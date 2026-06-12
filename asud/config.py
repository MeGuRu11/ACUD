"""Configuration defaults and shared constants for ASUD."""

CONFIG_FILE = "config.json"
DEFAULT_CONFIG = {
    "logo_path": "logo.png",
    "persistence_file": "last_data.csv",
    "audit_log": "audit.log",
    "backup_dir": "backups",
    "users_file": "users.json",
    "report_template": "template.docx",
    "default_columns_width": 120,
    "theme": "clam",
    "db_path": "asud.sqlite3",
}
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
