import tkinter as tk

import pytest

from asud.ui import dialogs


class FakeUserManager:
    def create_initial_admin(self, username, password, full_name):
        return True, "Администратор создан"


def test_initial_admin_dialog_uses_polished_sectioned_layout(monkeypatch):
    try:
        root = tk.Tk()
    except tk.TclError as exc:
        pytest.skip(f"Tk is not available: {exc}")
    root.withdraw()

    def no_wait(self, on_close):
        self.dialog.protocol("WM_DELETE_WINDOW", on_close)
        self.center_on_screen()

    monkeypatch.setattr(dialogs.DialogBase, "wait", no_wait)
    setup = dialogs.InitialAdminDialog(root, FakeUserManager())
    setup.dialog.update()

    def collect_texts(widget):
        texts = []
        try:
            text = widget.cget("text")
            if text:
                texts.append(text)
        except tk.TclError:
            pass
        for child in widget.winfo_children():
            texts.extend(collect_texts(child))
        return texts

    try:
        texts = collect_texts(setup.dialog)
        assert "Первый запуск" in texts
        assert "Учётная запись администратора" in texts
        assert "Безопасность" in texts
        assert "Минимум 8 символов" in " ".join(texts)
        assert setup.entries["login"].winfo_width() >= 390
        assert setup.entries["password"].winfo_width() >= 390
        assert setup.entries["confirm"].winfo_height() >= 34
        assert setup.entries["fullname"].winfo_height() >= 34
        assert setup.password_strength_var.get() == "Надёжность пароля: не задан"
        assert setup.password_match_var.get() == ""
        assert 640 <= setup.dialog.winfo_width() <= 720
        assert 620 <= setup.dialog.winfo_height() <= 740
    finally:
        setup.dialog.destroy()
        root.destroy()


def test_initial_admin_dialog_updates_password_feedback(monkeypatch):
    try:
        root = tk.Tk()
    except tk.TclError as exc:
        pytest.skip(f"Tk is not available: {exc}")
    root.withdraw()

    monkeypatch.setattr(dialogs.DialogBase, "wait", lambda self, on_close: None)
    setup = dialogs.InitialAdminDialog(root, FakeUserManager())

    try:
        setup.entries["password"].insert(0, "Adminpass1")
        setup.entries["confirm"].insert(0, "Adminpass1")
        setup.update_password_feedback()

        assert setup.password_strength_var.get() == "Надёжность пароля: высокая"
        assert setup.password_match_var.get() == "Пароли совпадают"
    finally:
        setup.dialog.destroy()
        root.destroy()
