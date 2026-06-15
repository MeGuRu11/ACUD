from asud.ui.theme import (
    APP_THEME,
    FONT,
    ROLE_LABELS,
    ROLE_VALUES,
    SPACING,
    WINDOW_MINSIZE,
    role_label_to_value,
    role_value_to_label,
)


def test_theme_defines_approved_palette_and_window_size():
    assert WINDOW_MINSIZE == (1180, 720)
    assert APP_THEME["app_background"] == "#eef2f6"
    assert APP_THEME["topbar"] == "#10242d"
    assert APP_THEME["primary"] == "#245c63"
    assert APP_THEME["primary_alt"] == "#1f7a70"
    assert APP_THEME["accent"] == "#b38b24"
    assert APP_THEME["surface"] == "#ffffff"


def test_theme_defines_typography_spacing_and_role_labels():
    assert FONT["family"] == "Segoe UI"
    assert SPACING["panel"] == 16
    assert ROLE_LABELS == {
        "admin": "Администратор",
        "editor": "Редактор",
        "viewer": "Наблюдатель",
    }
    assert ROLE_VALUES == ["Наблюдатель", "Редактор", "Администратор"]
    assert role_value_to_label("editor") == "Редактор"
    assert role_label_to_value("Редактор") == "editor"
    assert role_label_to_value("editor") == "editor"
