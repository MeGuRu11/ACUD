"""Configuration defaults and shared constants for ASUD."""

CONFIG_FILE = "config.json"
DEFAULT_CONFIG = {
    "logo_path": "logo.png",
    "app_icon_svg": "assets/asud_icon.svg",
    "app_icon_png": "assets/asud_icon.png",
    "persistence_file": "last_data.csv",
    "audit_log": "audit.log",
    "backup_dir": "backups",
    "users_file": "users.json",
    "report_template": "template.docx",
    "default_columns_width": 120,
    "theme": "clam",
    "db_path": "asud.sqlite3",
}
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
