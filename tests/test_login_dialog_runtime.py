import tkinter as tk
from datetime import datetime

import pytest

from asud.ui import dialogs


class FakeUserManager:
    def authenticate(self, username, password):
        return False, None, None


class FixedDateTime(datetime):
    @classmethod
    def now(cls):
        return cls(2026, 6, 13, 9, 10, 31)


def test_login_dialog_centers_real_requested_window_size(monkeypatch):
    try:
        root = tk.Tk()
    except tk.TclError as exc:
        pytest.skip(f"Tk is not available: {exc}")
    root.withdraw()

    def no_wait(self, on_close):
        self.dialog.protocol("WM_DELETE_WINDOW", on_close)
        self.center_on_screen()

    monkeypatch.setattr(dialogs.DialogBase, "wait", no_wait)
    login = dialogs.LoginDialog(root, FakeUserManager())
    root.update_idletasks()

    geometry = login.dialog.geometry()
    width = login.dialog.winfo_width()
    height = login.dialog.winfo_height()
    x = login.dialog.winfo_x()
    y = login.dialog.winfo_y()
    expected_x = (login.dialog.winfo_screenwidth() - width) // 2
    expected_y = (login.dialog.winfo_screenheight() - height) // 2

    try:
        assert width >= 500, geometry
        assert height >= 420, geometry
        assert abs(x - expected_x) <= 2, geometry
        assert abs(y - expected_y) <= 2, geometry
    finally:
        login.dialog.destroy()
        root.destroy()


def test_dialog_fields_bind_clipboard_shortcuts():
    try:
        root = tk.Tk()
    except tk.TclError as exc:
        pytest.skip(f"Tk is not available: {exc}")
    root.withdraw()

    dialog = dialogs.DialogBase(root, "Test", "320x180")
    body = dialog.body_frame()
    form = dialog.form_frame(body)
    entry = dialog.add_field(form, 0, "Логин")

    try:
        for sequence in ["<Control-v>", "<Control-V>", "<Control-c>", "<Control-C>", "<Control-x>", "<Control-X>"]:
            assert entry.bind(sequence), sequence
    finally:
        dialog.dialog.destroy()
        root.destroy()


def test_dialog_fields_execute_clipboard_shortcuts_from_control_keycodes():
    try:
        root = tk.Tk()
    except tk.TclError as exc:
        pytest.skip(f"Tk is not available: {exc}")
    root.geometry("240x80+0+0")

    dialog = dialogs.DialogBase(root, "Test", "320x180")
    body = dialog.body_frame()
    form = dialog.form_frame(body)
    entry = dialog.add_field(form, 0, "Логин")
    dialog.center_on_screen()
    entry.focus_force()
    root.clipboard_clear()
    root.clipboard_append("paste-ok")
    root.update()

    try:
        entry.event_generate("<KeyPress>", state=0x4, keycode=86)
        root.update()
        assert entry.get() == "paste-ok"

        entry.select_range(0, 5)
        entry.event_generate("<KeyPress>", state=0x4, keycode=67)
        root.update()
        assert root.clipboard_get() == "paste"

        entry.event_generate("<KeyPress>", state=0x4, keycode=88)
        root.update()
        assert entry.get() == "-ok"
        assert root.clipboard_get() == "paste"
    finally:
        dialog.dialog.destroy()
        root.destroy()


def test_login_dialog_clock_widget_uses_required_formats(monkeypatch):
    try:
        root = tk.Tk()
    except tk.TclError as exc:
        pytest.skip(f"Tk is not available: {exc}")
    root.withdraw()

    def no_wait(self, on_close):
        self.dialog.protocol("WM_DELETE_WINDOW", on_close)
        self.center_on_screen()

    monkeypatch.setattr(dialogs.DialogBase, "wait", no_wait)
    monkeypatch.setattr(dialogs, "datetime", FixedDateTime)
    login = dialogs.LoginDialog(root, FakeUserManager())

    try:
        assert login.login_clock_date_var.get() == "13.06.2026"
        assert login.login_clock_time_var.get() == "09:10:31"
        assert login.clock_after_id is not None
    finally:
        login.dialog.destroy()
        root.destroy()


def test_login_dialog_clock_widget_is_visible_inside_hero(monkeypatch):
    try:
        root = tk.Tk()
    except tk.TclError as exc:
        pytest.skip(f"Tk is not available: {exc}")
    root.withdraw()

    def no_wait(self, on_close):
        self.dialog.protocol("WM_DELETE_WINDOW", on_close)
        self.center_on_screen()

    monkeypatch.setattr(dialogs.DialogBase, "wait", no_wait)
    login = dialogs.LoginDialog(root, FakeUserManager())
    root.update()

    try:
        assert login.clock_frame.winfo_ismapped()
        assert login.clock_frame.winfo_height() > 1
        assert login.clock_frame.winfo_y() + login.clock_frame.winfo_height() <= login.hero_frame.winfo_height()
    finally:
        login.dialog.destroy()
        root.destroy()


def test_login_dialog_uses_app_icon_image_instead_of_text_badge(monkeypatch):
    try:
        root = tk.Tk()
    except tk.TclError as exc:
        pytest.skip(f"Tk is not available: {exc}")
    root.withdraw()

    def no_wait(self, on_close):
        self.dialog.protocol("WM_DELETE_WINDOW", on_close)
        self.center_on_screen()

    monkeypatch.setattr(dialogs.DialogBase, "wait", no_wait)
    login = dialogs.LoginDialog(root, FakeUserManager())
    root.update()

    try:
        assert hasattr(login, "login_icon_image")
        assert login.login_icon_label.cget("image")
        assert login.login_icon_label.cget("text") == ""
    finally:
        login.dialog.destroy()
        root.destroy()
