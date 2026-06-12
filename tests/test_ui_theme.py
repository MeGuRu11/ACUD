from asud.ui.theme import APP_THEME, WINDOW_MINSIZE


def test_theme_defines_main_palette_and_window_size():
    assert WINDOW_MINSIZE == (1100, 650)
    assert APP_THEME["background"]
    assert APP_THEME["panel"]
    assert APP_THEME["accent"]
    assert APP_THEME["table_background"]
