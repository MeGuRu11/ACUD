"""Shared Tkinter theme values."""

from tkinter import ttk

WINDOW_MINSIZE = (1180, 720)

APP_THEME = {
    "app_background": "#eef2f6",
    "topbar": "#10242d",
    "topbar_text": "#ffffff",
    "topbar_muted": "#b9c7d6",
    "surface": "#ffffff",
    "surface_soft": "#f8fafc",
    "sidebar": "#ffffff",
    "line": "#d9e0ea",
    "text": "#18212f",
    "muted_text": "#657084",
    "primary": "#245c63",
    "primary_alt": "#1f7a70",
    "accent": "#b38b24",
    "accent_soft": "#e2c164",
    "danger": "#b3343a",
    "success": "#287a4e",
    "table_background": "#ffffff",
    "table_heading": "#f3f6fa",
    "table_selected": "#e8f4f1",
}

# Compatibility aliases while the legacy widgets are migrated.
APP_THEME["background"] = APP_THEME["app_background"]
APP_THEME["panel"] = APP_THEME["sidebar"]
APP_THEME["accent_active"] = "#9f7a1f"
APP_THEME["table_text"] = APP_THEME["text"]
APP_THEME["secondary"] = APP_THEME["muted_text"]

FONT = {
    "family": "Segoe UI",
    "size": 10,
    "small": 9,
    "caption": 8,
    "heading": 14,
    "title": 18,
}

SPACING = {
    "xs": 4,
    "sm": 8,
    "md": 12,
    "panel": 16,
    "lg": 22,
}

ROLE_LABELS = {
    "admin": "Администратор",
    "editor": "Редактор",
    "viewer": "Наблюдатель",
}


def configure_ttk_style(root, theme_name="clam"):
    style = ttk.Style(root)
    if theme_name in style.theme_names():
        style.theme_use(theme_name)
    style.configure(
        "Treeview",
        background=APP_THEME["table_background"],
        foreground=APP_THEME["text"],
        fieldbackground=APP_THEME["table_background"],
        bordercolor=APP_THEME["line"],
        lightcolor=APP_THEME["line"],
        darkcolor=APP_THEME["line"],
        font=(FONT["family"], FONT["size"]),
        rowheight=32,
    )
    style.map(
        "Treeview",
        background=[("selected", APP_THEME["table_selected"])],
        foreground=[("selected", APP_THEME["text"])],
    )
    style.configure(
        "Treeview.Heading",
        background=APP_THEME["table_heading"],
        foreground=APP_THEME["muted_text"],
        bordercolor=APP_THEME["line"],
        font=(FONT["family"], FONT["size"], "bold"),
        relief="flat",
    )
    style.configure(
        "TCombobox",
        fieldbackground=APP_THEME["surface"],
        background=APP_THEME["surface"],
        foreground=APP_THEME["text"],
        arrowcolor=APP_THEME["primary"],
        font=(FONT["family"], FONT["size"]),
    )
    style.configure(
        "Vertical.TScrollbar",
        background=APP_THEME["surface_soft"],
        troughcolor=APP_THEME["surface"],
        bordercolor=APP_THEME["line"],
        arrowcolor=APP_THEME["muted_text"],
    )
    style.configure(
        "Horizontal.TScrollbar",
        background=APP_THEME["surface_soft"],
        troughcolor=APP_THEME["surface"],
        bordercolor=APP_THEME["line"],
        arrowcolor=APP_THEME["muted_text"],
    )
    return style
