from pathlib import Path


def test_dialogs_use_shared_theme_helpers():
    source = Path("asud/ui/dialogs.py").read_text(encoding="utf-8")

    assert "DialogBase" in source
    assert "create_dialog_button" in source
    assert "APP_THEME" in source
    assert "FONT" in source


def test_dialogs_do_not_use_legacy_palette_or_emoji_labels():
    source = Path("asud/ui/dialogs.py").read_text(encoding="utf-8")

    for legacy in ["#0b2a1b", "#1a3d2a", "#d4af37", "Times New Roman"]:
        assert legacy not in source

    for label in ["🔍", "🔑", "✏️", "🗑️", "➕", "❌", "📝", "🔐"]:
        assert label not in source


def test_login_dialog_has_centered_polished_auth_layout():
    source = Path("asud/ui/dialogs.py").read_text(encoding="utf-8")

    assert "LOGIN_DIALOG_SIZE" in source
    assert "560x540" in source
    assert "center_on_screen" in source
    assert "build_login_card" in source
    assert "Добро пожаловать" in source
    assert "АСУД" in source
    assert "self.dialog.lift()" in source
    assert "self.entry_login.focus_set()" in source
    assert "login_form_card" in source
    assert "credential_hint" in source


def test_login_dialog_centers_brand_and_buttons_and_enables_clipboard_shortcuts():
    source = Path("asud/ui/dialogs.py").read_text(encoding="utf-8")

    assert "APP_ICON_PNG" in source
    assert "login_icon_label" in source
    assert "PhotoImage(file=" in source
    assert "subsample" in source
    assert "text=\"АСУД\"" in source
    assert "anchor=\"center\"" in source
    assert "button_row" in source
    assert "justify=\"center\"" in source
    assert "enable_entry_shortcuts" in source
    assert "ENTRY_SHORTCUT_KEYCODES" in source
    assert "ENTRY_SHORTCUT_KEYSYMS" in source
    assert "paste_entry_clipboard" in source
    assert "copy_entry_selection" in source
    assert "cut_entry_selection" in source
    assert "<Control-KeyPress>" in source


def test_login_dialog_has_no_self_registration_entrypoint():
    source = Path("asud/ui/dialogs.py").read_text(encoding="utf-8")
    login_source = source[source.index("class LoginDialog"):source.index("class InitialAdminDialog")]

    assert "Зарегистрировать нового пользователя" not in login_source
    assert "open_registration" not in login_source
    assert "RegistrationDialog" not in login_source


def test_login_dialog_has_live_date_time_widget():
    source = Path("asud/ui/dialogs.py").read_text(encoding="utf-8")

    assert "build_clock_widget" in source
    assert "update_clock" in source
    assert "login_clock_date_var" in source
    assert "login_clock_time_var" in source
    assert 'strftime("%d.%m.%Y")' in source
    assert 'strftime("%H:%M:%S")' in source
    assert "self.dialog.after(1000, self.update_clock)" in source


def test_login_dialog_uses_dedicated_clock_row_and_larger_fields():
    source = Path("asud/ui/dialogs.py").read_text(encoding="utf-8")
    login_source = source[source.index("class LoginDialog"):source.index("class InitialAdminDialog")]

    assert "login_clock_row" in login_source
    assert ".place(" not in login_source[login_source.index("def build_clock_widget"):login_source.index("def update_clock")]
    assert "ipady=SPACING[\"sm\"]" in login_source
    assert "width=42" in login_source
