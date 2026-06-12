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
