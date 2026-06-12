"""Shared Tkinter theme values."""

from tkinter import ttk

WINDOW_MINSIZE = (1100, 650)

APP_THEME = {
    "background": "#10291f",
    "panel": "#1f3b2d",
    "text": "#ffffff",
    "muted_text": "#d8ded8",
    "accent": "#c9a227",
    "accent_active": "#ad8d20",
    "table_background": "#fbfaf7",
    "table_text": "#111111",
    "danger": "#b8322a",
    "secondary": "#666666",
}


def configure_ttk_style(root, theme_name="clam"):
    style = ttk.Style(root)
    if theme_name in style.theme_names():
        style.theme_use(theme_name)
    style.configure(
        "Treeview",
        background=APP_THEME["table_background"],
        foreground=APP_THEME["table_text"],
        fieldbackground=APP_THEME["table_background"],
        font=("Times New Roman", 10),
        rowheight=25,
    )
    style.configure(
        "Treeview.Heading",
        background=APP_THEME["panel"],
        foreground=APP_THEME["accent"],
        font=("Times New Roman", 10, "bold"),
    )
    return style
