"""Tkinter dialogs used by the ASUD application."""

import re
import sys
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import messagebox, ttk

import pandas as pd

from asud.config import APP_ICON_PNG, APP_ICON_SVG, DEGREE_OPTIONS
from asud.ui.theme import (
    APP_THEME,
    FONT,
    ROLE_LABELS,
    ROLE_VALUES,
    SPACING,
    configure_ttk_style,
    role_label_to_value,
    role_value_to_label,
)

LOGIN_DIALOG_SIZE = "560x540"


def ui_font(size_key="size", weight=None):
    font = (FONT["family"], FONT[size_key])
    if weight:
        font += (weight,)
    return font


def create_dialog_button(parent, text, command, variant="primary", width=14):
    palettes = {
        "primary": (APP_THEME["primary_alt"], APP_THEME["topbar_text"], APP_THEME["primary"]),
        "secondary": (APP_THEME["surface_soft"], APP_THEME["text"], APP_THEME["line"]),
        "danger": (APP_THEME["danger"], APP_THEME["topbar_text"], APP_THEME["danger"]),
    }
    bg, fg, active_bg = palettes[variant]
    button = tk.Button(
        parent,
        text=text,
        command=command,
        width=width,
        bg=bg,
        fg=fg,
        activebackground=active_bg,
        activeforeground=APP_THEME["topbar_text"] if variant != "secondary" else APP_THEME["text"],
        disabledforeground="#a7b0bd",
        font=ui_font("size", "bold"),
        relief="flat",
        padx=SPACING["sm"],
        pady=SPACING["sm"],
    )
    return button


ENTRY_SHORTCUT_KEYCODES = {
    67: "copy",
    86: "paste",
    88: "cut",
}
ENTRY_SHORTCUT_KEYSYMS = {
    "c": "copy",
    "с": "copy",
    "v": "paste",
    "м": "paste",
    "x": "cut",
    "ч": "cut",
}


def entry_selection_range(entry):
    try:
        return entry.index(tk.SEL_FIRST), entry.index(tk.SEL_LAST)
    except tk.TclError:
        return None


def copy_entry_selection(entry):
    selected_range = entry_selection_range(entry)
    if not selected_range:
        return
    start, end = selected_range
    selected_text = entry.get()[start:end]
    entry.clipboard_clear()
    entry.clipboard_append(selected_text)


def paste_entry_clipboard(entry):
    if entry.cget("state") == "disabled":
        return
    try:
        clipboard_text = entry.clipboard_get()
    except tk.TclError:
        return
    selected_range = entry_selection_range(entry)
    if selected_range:
        entry.delete(*selected_range)
    entry.insert(tk.INSERT, clipboard_text)


def cut_entry_selection(entry):
    if entry.cget("state") == "disabled":
        return
    selected_range = entry_selection_range(entry)
    if not selected_range:
        return
    copy_entry_selection(entry)
    entry.delete(*selected_range)


def run_entry_shortcut(entry, action):
    if action == "copy":
        copy_entry_selection(entry)
    elif action == "paste":
        paste_entry_clipboard(entry)
    elif action == "cut":
        cut_entry_selection(entry)


def enable_entry_shortcuts(entry):
    direct_shortcuts = {
        "<Control-v>": "paste",
        "<Control-V>": "paste",
        "<Control-c>": "copy",
        "<Control-C>": "copy",
        "<Control-x>": "cut",
        "<Control-X>": "cut",
    }

    def handle_action(event, action):
        run_entry_shortcut(event.widget, action)
        return "break"

    def handle_control_keypress(event):
        keysym = (event.keysym or "").lower()
        action = ENTRY_SHORTCUT_KEYCODES.get(event.keycode) or ENTRY_SHORTCUT_KEYSYMS.get(keysym)
        if not action:
            return None
        run_entry_shortcut(event.widget, action)
        return "break"

    entry.bind("<Control-KeyPress>", handle_control_keypress)
    for sequence, action in direct_shortcuts.items():
        entry.bind(sequence, lambda event, shortcut_action=action: handle_action(event, shortcut_action))
    return entry


class DialogBase:
    def __init__(self, parent, title, size, resizable=False):
        self.parent = parent
        self.initial_size = size
        self.dialog = tk.Toplevel(parent)
        self.dialog.withdraw()
        self.dialog.title(title)
        self.dialog.geometry(size)
        self.dialog.configure(bg=APP_THEME["surface"])
        self.dialog.transient(parent)
        self.dialog.grab_set()
        self.dialog.resizable(resizable, resizable)
        configure_ttk_style(self.dialog)

    def requested_size(self):
        try:
            width_text, height_text = self.initial_size.split("x", 1)
            width = int(width_text)
            height = int(height_text)
        except (AttributeError, ValueError):
            width = self.dialog.winfo_reqwidth()
            height = self.dialog.winfo_reqheight()
        return width, height

    def add_header(self, title, subtitle=None):
        header = tk.Frame(self.dialog, bg=APP_THEME["topbar"])
        header.pack(fill="x")
        tk.Label(
            header,
            text=title,
            bg=APP_THEME["topbar"],
            fg=APP_THEME["topbar_text"],
            font=ui_font("heading", "bold"),
            anchor="w",
        ).pack(fill="x", padx=SPACING["panel"], pady=(SPACING["panel"], 2))
        if subtitle:
            tk.Label(
                header,
                text=subtitle,
                bg=APP_THEME["topbar"],
                fg=APP_THEME["topbar_muted"],
                font=ui_font("small"),
                anchor="w",
                wraplength=560,
                justify="left",
            ).pack(fill="x", padx=SPACING["panel"], pady=(0, SPACING["panel"]))

    def body_frame(self, padx=None, pady=None):
        frame = tk.Frame(self.dialog, bg=APP_THEME["surface"])
        frame.pack(fill="both", expand=True, padx=padx or SPACING["panel"], pady=pady or SPACING["panel"])
        return frame

    def form_frame(self, parent):
        frame = tk.Frame(parent, bg=APP_THEME["surface"])
        frame.pack(fill="x")
        frame.columnconfigure(1, weight=1)
        return frame

    def add_field(self, form, row, label, show=None, width=30, initial=""):
        tk.Label(
            form,
            text=label,
            bg=APP_THEME["surface"],
            fg=APP_THEME["muted_text"],
            font=ui_font("small", "bold"),
            anchor="e",
        ).grid(row=row, column=0, padx=(0, SPACING["md"]), pady=SPACING["sm"], sticky="e")
        entry = tk.Entry(
            form,
            show=show or "",
            width=width,
            bg=APP_THEME["surface_soft"],
            fg=APP_THEME["text"],
            insertbackground=APP_THEME["text"],
            relief="flat",
            highlightthickness=1,
            highlightbackground=APP_THEME["line"],
            highlightcolor=APP_THEME["primary_alt"],
            font=(FONT["family"], FONT["size"]),
        )
        entry.grid(row=row, column=1, padx=0, pady=SPACING["sm"], sticky="ew")
        if initial:
            entry.insert(0, initial)
        enable_entry_shortcuts(entry)
        return entry

    def add_combobox(self, form, row, label, values, initial="", state="readonly", width=28):
        tk.Label(
            form,
            text=label,
            bg=APP_THEME["surface"],
            fg=APP_THEME["muted_text"],
            font=ui_font("small", "bold"),
            anchor="e",
        ).grid(row=row, column=0, padx=(0, SPACING["md"]), pady=SPACING["sm"], sticky="e")
        combo = ttk.Combobox(form, values=values, state=state, width=width, font=(FONT["family"], FONT["size"]))
        combo.grid(row=row, column=1, padx=0, pady=SPACING["sm"], sticky="ew")
        if initial:
            combo.set(initial)
        elif values:
            combo.set(values[0])
        return combo

    def add_footer(self):
        footer = tk.Frame(self.dialog, bg=APP_THEME["surface_soft"])
        footer.pack(fill="x", side="bottom", padx=0, pady=0)
        return footer

    def center_on_screen(self):
        try:
            if not self.parent.winfo_viewable():
                self.dialog.transient("")
        except tk.TclError:
            pass
        self.dialog.update_idletasks()
        requested_width, requested_height = self.requested_size()
        width = max(self.dialog.winfo_width(), self.dialog.winfo_reqwidth(), requested_width)
        height = max(self.dialog.winfo_height(), self.dialog.winfo_reqheight(), requested_height)
        screen_width = self.dialog.winfo_screenwidth()
        screen_height = self.dialog.winfo_screenheight()
        x = max(0, (screen_width - width) // 2)
        y = max(0, (screen_height - height) // 2)
        self.dialog.geometry(f"{width}x{height}+{x}+{y}")
        self.dialog.deiconify()
        self.dialog.update_idletasks()
        self.dialog.lift()
        self.dialog.focus_force()

    def center(self):
        self.center_on_screen()

    def wait(self, on_close):
        self.dialog.protocol("WM_DELETE_WINDOW", on_close)
        self.center_on_screen()
        self.parent.wait_window(self.dialog)


class LoginDialog(DialogBase):
    def __init__(self, parent, user_manager):
        self.user_manager = user_manager
        self.icon_asset_path = APP_ICON_PNG
        self.icon_source_path = APP_ICON_SVG
        self.login_icon_source_image = None
        self.login_icon_image = None
        self.clock_after_id = None
        self.result = None
        super().__init__(parent, "Вход в систему", LOGIN_DIALOG_SIZE)
        self.build_login_card()
        self.dialog.bind("<Return>", lambda e: self.login())
        self.entry_login.focus_set()
        self.wait(self.cancel)

    def build_login_card(self):
        self.hero_frame = tk.Frame(self.dialog, bg=APP_THEME["topbar"], height=232)
        self.hero_frame.pack(fill="x")
        self.hero_frame.pack_propagate(False)

        self.login_clock_row = tk.Frame(self.hero_frame, bg=APP_THEME["topbar"], height=36)
        self.login_clock_row.pack(fill="x", padx=SPACING["panel"], pady=(SPACING["sm"], 0))
        self.login_clock_row.pack_propagate(False)
        self.build_clock_widget(self.login_clock_row)

        brand_stack = tk.Frame(self.hero_frame, bg=APP_THEME["topbar"])
        brand_stack.pack(fill="x", pady=(SPACING["xs"], 0))
        self.login_icon_label = tk.Label(
            brand_stack,
            image=self.load_login_icon(),
            bg=APP_THEME["topbar"],
            bd=0,
            highlightthickness=0,
        )
        self.login_icon_label.pack(anchor="center", pady=(0, SPACING["xs"]))

        tk.Label(
            brand_stack,
            text="АСУД",
            bg=APP_THEME["topbar"],
            fg=APP_THEME["topbar_text"],
            font=(FONT["family"], 24, "bold"),
            anchor="center",
        ).pack(fill="x", padx=SPACING["lg"])
        tk.Label(
            self.hero_frame,
            text="Добро пожаловать",
            bg=APP_THEME["topbar"],
            fg=APP_THEME["topbar_text"],
            font=ui_font("small", "bold"),
            anchor="center",
            justify="center",
        ).pack(fill="x", padx=SPACING["lg"], pady=(2, 0))
        tk.Label(
            self.hero_frame,
            text="Вход в реестр диссертаций",
            bg=APP_THEME["topbar"],
            fg=APP_THEME["topbar_muted"],
            font=ui_font("size"),
            anchor="center",
            justify="center",
        ).pack(fill="x", padx=SPACING["lg"], pady=(4, 0))

        body = tk.Frame(self.dialog, bg=APP_THEME["surface"])
        body.pack(fill="x", padx=SPACING["lg"], pady=SPACING["lg"])
        self.login_form_card = tk.Frame(
            body,
            bg=APP_THEME["surface"],
            highlightbackground=APP_THEME["line"],
            highlightthickness=1,
        )
        self.login_form_card.pack(fill="x")
        self.login_form_card.columnconfigure(0, weight=1)

        form = self.form_frame(self.login_form_card)
        form.pack(fill="x", padx=SPACING["lg"], pady=(SPACING["lg"], SPACING["sm"]))
        self.entry_login = self.add_field(form, 0, "Логин", width=42)
        self.entry_login.grid_configure(ipady=SPACING["sm"])
        self.entry_password = self.add_field(form, 1, "Пароль", show="*", width=42)
        self.entry_password.grid_configure(ipady=SPACING["sm"])
        self.credential_hint = tk.Label(
            self.login_form_card,
            text="Учётные записи создаются администратором в разделе «Пользователи».",
            bg=APP_THEME["surface"],
            fg=APP_THEME["muted_text"],
            font=ui_font("small"),
            anchor="w",
            justify="left",
            wraplength=460,
        )
        self.credential_hint.pack(fill="x", padx=SPACING["lg"], pady=(0, SPACING["lg"]))

        footer = self.add_footer()
        button_row = tk.Frame(footer, bg=APP_THEME["surface_soft"])
        button_row.pack(anchor="center", pady=SPACING["panel"])
        create_dialog_button(button_row, "Войти", self.login, width=18).pack(
            side="left", padx=(0, SPACING["sm"])
        )
        create_dialog_button(button_row, "Отмена", self.cancel, variant="secondary", width=18).pack(
            side="left", padx=(SPACING["sm"], 0)
        )

    def resolve_asset_path(self, path):
        asset_path = Path(path)
        if asset_path.exists():
            return asset_path
        if hasattr(sys, "_MEIPASS"):
            bundled_path = Path(sys._MEIPASS) / path
            if bundled_path.exists():
                return bundled_path
        return Path(__file__).resolve().parents[2] / path

    def load_login_icon(self):
        icon_path = self.resolve_asset_path(self.icon_asset_path)
        if not icon_path.exists():
            return ""
        try:
            self.login_icon_source_image = tk.PhotoImage(file=str(icon_path))
            scale = max(1, min(self.login_icon_source_image.width(), self.login_icon_source_image.height()) // 64)
            self.login_icon_image = self.login_icon_source_image.subsample(scale, scale)
            return self.login_icon_image
        except tk.TclError:
            self.login_icon_source_image = None
            self.login_icon_image = None
            return ""

    def build_clock_widget(self, parent):
        self.login_clock_date_var = tk.StringVar()
        self.login_clock_time_var = tk.StringVar()
        self.clock_frame = tk.Frame(parent, bg=APP_THEME["topbar"])
        self.clock_frame.pack(anchor="e")

        clock_shell = tk.Frame(
            self.clock_frame,
            bg="#16323c",
            highlightbackground=APP_THEME["primary_alt"],
            highlightthickness=1,
        )
        clock_shell.pack(anchor="center")
        tk.Label(
            clock_shell,
            textvariable=self.login_clock_date_var,
            bg="#16323c",
            fg=APP_THEME["topbar_text"],
            font=ui_font("small", "bold"),
        ).pack(side="left", padx=(SPACING["md"], SPACING["xs"]), pady=SPACING["xs"])
        tk.Label(
            clock_shell,
            text="|",
            bg="#16323c",
            fg=APP_THEME["topbar_muted"],
            font=ui_font("small"),
        ).pack(side="left", pady=SPACING["xs"])
        tk.Label(
            clock_shell,
            textvariable=self.login_clock_time_var,
            bg="#16323c",
            fg=APP_THEME["accent_soft"],
            font=ui_font("small", "bold"),
        ).pack(side="left", padx=(SPACING["xs"], SPACING["md"]), pady=SPACING["xs"])
        self.update_clock()

    def update_clock(self):
        now = datetime.now()
        self.login_clock_date_var.set(now.strftime("%d.%m.%Y"))
        self.login_clock_time_var.set(now.strftime("%H:%M:%S"))
        self.clock_after_id = self.dialog.after(1000, self.update_clock)

    def stop_clock(self):
        if not self.clock_after_id:
            return
        try:
            self.dialog.after_cancel(self.clock_after_id)
        except tk.TclError:
            pass
        self.clock_after_id = None

    def login(self):
        username = self.entry_login.get().strip()
        password = self.entry_password.get()
        if not username or not password:
            return messagebox.showerror("Ошибка", "Введите логин и пароль")
        ok, role, force_change = self.user_manager.authenticate(username, password)
        if ok:
            if force_change and username != "admin":
                if not messagebox.askyesno("Смена пароля", "Для продолжения необходимо сменить пароль. Открыть форму?"):
                    return
                password_dialog = ChangePasswordDialog(self.dialog, self.user_manager, username, False)
                if not password_dialog.result:
                    return
            self.result = (username, role)
            self.stop_clock()
            self.dialog.destroy()
        else:
            messagebox.showerror("Ошибка", "Неверный логин или пароль")

    def cancel(self):
        self.result = None
        self.stop_clock()
        self.dialog.destroy()


class InitialAdminDialog(DialogBase):
    def __init__(self, parent, user_manager):
        self.user_manager = user_manager
        self.result = None
        super().__init__(parent, "Первичная настройка", "520x410")
        self.add_header(
            "Создание администратора",
            "Задайте первую учётную запись администратора. Стандартный admin/admin не используется.",
        )
        body = self.body_frame()
        form = self.form_frame(body)
        self.entries = {
            "login": self.add_field(form, 0, "Логин", initial="admin"),
            "password": self.add_field(form, 1, "Пароль", show="*"),
            "confirm": self.add_field(form, 2, "Повтор пароля", show="*"),
            "fullname": self.add_field(form, 3, "ФИО"),
        }
        footer = self.add_footer()
        create_dialog_button(footer, "Создать", self.create).pack(
            side="left", padx=SPACING["panel"], pady=SPACING["md"]
        )
        create_dialog_button(footer, "Отмена", self.cancel, variant="secondary").pack(
            side="left", padx=(0, SPACING["sm"]), pady=SPACING["md"]
        )
        self.entries["password"].focus_set()
        self.wait(self.cancel)

    def create(self):
        username = self.entries["login"].get().strip()
        password = self.entries["password"].get()
        confirm = self.entries["confirm"].get()
        full_name = self.entries["fullname"].get().strip()
        if password != confirm:
            return messagebox.showerror("Ошибка", "Пароли не совпадают")
        ok, message = self.user_manager.create_initial_admin(username, password, full_name)
        if ok:
            self.result = username
            messagebox.showinfo("Успех", message)
            self.dialog.destroy()
        else:
            messagebox.showerror("Ошибка", message)

    def cancel(self):
        self.result = None
        self.dialog.destroy()


class ChangePasswordDialog(DialogBase):
    def __init__(self, parent, user_manager, username, is_admin_reset=False):
        self.user_manager = user_manager
        self.username = username
        self.is_admin_reset = is_admin_reset
        self.result = None
        title = "Смена пароля" if not is_admin_reset else f"Сброс пароля: {username}"
        super().__init__(parent, title, "500x410")
        self.add_header(title, "Минимум 8 символов, заглавная и строчная буква, цифра.")
        body = self.body_frame()
        form = self.form_frame(body)
        row = 0
        if not is_admin_reset:
            self.entry_old = self.add_field(form, row, "Текущий пароль", show="*")
            row += 1
        self.entry_new = self.add_field(form, row, "Новый пароль", show="*")
        row += 1
        self.entry_confirm = self.add_field(form, row, "Повтор пароля", show="*")
        row += 1
        self.strength_var = tk.StringVar(value="Сложность: ")
        tk.Label(
            form,
            textvariable=self.strength_var,
            bg=APP_THEME["surface"],
            fg=APP_THEME["primary"],
            font=ui_font("small", "bold"),
            anchor="w",
        ).grid(row=row, column=1, sticky="w", pady=(0, SPACING["sm"]))
        self.entry_new.bind("<KeyRelease>", self.check_strength)

        footer = self.add_footer()
        create_dialog_button(footer, "Сохранить", self.save).pack(
            side="left", padx=SPACING["panel"], pady=SPACING["md"]
        )
        create_dialog_button(footer, "Отмена", self.cancel, variant="secondary").pack(
            side="left", padx=(0, SPACING["sm"]), pady=SPACING["md"]
        )
        self.dialog.bind("<Return>", lambda e: self.save())
        self.entry_new.focus_set()
        self.wait(self.cancel)

    def check_strength(self, event=None):
        password = self.entry_new.get()
        score = sum(
            [
                len(password) >= 8,
                bool(re.search(r"[A-ZА-ЯЁ]", password)),
                bool(re.search(r"[a-zа-яё]", password)),
                bool(re.search(r"\d", password)),
                bool(re.search(r'[!@#$%^&*(),.?":{}|<>]', password)),
            ]
        )
        levels = ["", "Слабый", "Средний", "Хороший", "Отличный", "Максимальный"]
        self.strength_var.set(f"Сложность: {levels[score]}")

    def save(self):
        old_password = self.entry_old.get() if hasattr(self, "entry_old") else None
        new_password = self.entry_new.get()
        confirm = self.entry_confirm.get()
        if new_password != confirm:
            return messagebox.showerror("Ошибка", "Пароли не совпадают")
        if not new_password:
            return messagebox.showerror("Ошибка", "Введите пароль")
        ok, message = self.user_manager.change_password(
            self.username,
            old_password,
            new_password,
            require_old=not self.is_admin_reset,
        )
        if ok:
            self.result = True
            messagebox.showinfo("Успех", message)
            self.dialog.destroy()
        else:
            messagebox.showerror("Ошибка", message)

    def cancel(self):
        self.result = False
        self.dialog.destroy()


class RegistrationDialog(DialogBase):
    def __init__(self, parent, user_manager):
        self.user_manager = user_manager
        self.result = None
        super().__init__(parent, "Регистрация", "520x470")
        self.add_header("Регистрация", "Новая учётная запись получает роль «Наблюдатель».")
        body = self.body_frame()
        form = self.form_frame(body)
        self.entry_login = self.add_field(form, 0, "Логин")
        self.entry_password = self.add_field(form, 1, "Пароль", show="*")
        self.entry_confirm = self.add_field(form, 2, "Повтор пароля", show="*")
        self.strength_var = tk.StringVar(value="Сложность: ")
        tk.Label(
            form,
            textvariable=self.strength_var,
            bg=APP_THEME["surface"],
            fg=APP_THEME["primary"],
            font=ui_font("small", "bold"),
            anchor="w",
        ).grid(row=3, column=1, sticky="w", pady=(0, SPACING["sm"]))
        self.entry_fullname = self.add_field(form, 4, "ФИО")
        self.entries = {
            "login": self.entry_login,
            "password": self.entry_password,
            "confirm": self.entry_confirm,
            "fullname": self.entry_fullname,
        }
        self.entry_password.bind("<KeyRelease>", self.check_strength)

        footer = self.add_footer()
        create_dialog_button(footer, "Зарегистрировать", self.register, width=18).pack(
            side="left", padx=SPACING["panel"], pady=SPACING["md"]
        )
        create_dialog_button(footer, "Отмена", self.cancel, variant="secondary").pack(
            side="left", padx=(0, SPACING["sm"]), pady=SPACING["md"]
        )
        self.dialog.bind("<Return>", lambda e: self.register())
        self.entry_login.focus_set()
        self.wait(self.cancel)

    def check_strength(self, event=None):
        password = self.entry_password.get()
        score = sum(
            [
                len(password) >= 8,
                bool(re.search(r"[A-ZА-ЯЁ]", password)),
                bool(re.search(r"[a-zа-яё]", password)),
                bool(re.search(r"\d", password)),
                bool(re.search(r'[!@#$%^&*(),.?":{}|<>]', password)),
            ]
        )
        levels = ["", "Слабый", "Средний", "Хороший", "Отличный", "Максимальный"]
        self.strength_var.set(f"Сложность: {levels[score]}")

    def register(self):
        login = self.entry_login.get().strip()
        password = self.entry_password.get()
        confirm = self.entry_confirm.get()
        full_name = self.entry_fullname.get().strip()
        if not login or not password or not full_name:
            return messagebox.showerror("Ошибка", "Заполните все поля")
        if password != confirm:
            return messagebox.showerror("Ошибка", "Пароли не совпадают")
        ok, message = self.user_manager.register_user(login, password, full_name)
        if ok:
            self.result = login
            messagebox.showinfo("Успех", message)
            self.dialog.destroy()
        else:
            messagebox.showerror("Ошибка", message)

    def cancel(self):
        self.result = None
        self.dialog.destroy()


class AddUserDialog(DialogBase):
    def __init__(self, parent, user_manager):
        self.user_manager = user_manager
        self.result = None
        super().__init__(parent, "Добавить пользователя", "620x520")
        self.build_user_creation_card()
        self.entries["login"].focus_set()
        self.wait(self.cancel)

    def build_user_creation_card(self):
        self.dialog.configure(bg=APP_THEME["app_background"])
        self.add_header("Добавить пользователя", "Администратор создаёт учётную запись и назначает роль.")
        body = self.body_frame(padx=SPACING["lg"], pady=SPACING["lg"])

        card = tk.Frame(
            body,
            bg=APP_THEME["surface"],
            highlightbackground=APP_THEME["line"],
            highlightthickness=1,
        )
        card.pack(fill="x")
        tk.Label(
            card,
            text="Учётные данные",
            bg=APP_THEME["surface"],
            fg=APP_THEME["text"],
            font=ui_font("heading", "bold"),
            anchor="w",
        ).pack(fill="x", padx=SPACING["lg"], pady=(SPACING["md"], SPACING["xs"]))
        tk.Label(
            card,
            text="Заполните логин, временный пароль, ФИО и роль пользователя.",
            bg=APP_THEME["surface"],
            fg=APP_THEME["muted_text"],
            font=ui_font("small"),
            anchor="w",
        ).pack(fill="x", padx=SPACING["lg"], pady=(0, SPACING["md"]))

        form = self.form_frame(card)
        form.pack(fill="x", padx=SPACING["lg"], pady=(0, SPACING["lg"]))
        self.entries = {
            "login": self.add_field(form, 0, "Логин"),
            "password": self.add_field(form, 1, "Пароль", show="*"),
            "fullname": self.add_field(form, 2, "ФИО"),
            "role": self.add_combobox(
                form,
                3,
                "Роль",
                ROLE_VALUES,
                initial=role_value_to_label("viewer"),
            ),
        }
        role_hint = tk.Frame(body, bg=APP_THEME["surface_soft"], highlightbackground=APP_THEME["line"], highlightthickness=1)
        role_hint.pack(fill="x", pady=(SPACING["md"], 0))
        tk.Label(
            role_hint,
            text="Роли: Наблюдатель — просмотр; Редактор — работа с записями; Администратор — пользователи и полный доступ.",
            bg=APP_THEME["surface_soft"],
            fg=APP_THEME["muted_text"],
            font=ui_font("small"),
            anchor="w",
            justify="left",
            wraplength=520,
        ).pack(fill="x", padx=SPACING["md"], pady=SPACING["md"])

        footer = self.add_footer()
        create_dialog_button(footer, "Создать", self.create).pack(
            side="left", padx=SPACING["panel"], pady=SPACING["md"]
        )
        create_dialog_button(footer, "Отмена", self.cancel, variant="secondary").pack(
            side="left", padx=(0, SPACING["sm"]), pady=SPACING["md"]
        )

    def create(self):
        login = self.entries["login"].get().strip()
        password = self.entries["password"].get()
        full_name = self.entries["fullname"].get().strip()
        role = role_label_to_value(self.entries["role"].get())
        ok, message = self.user_manager.add_user(login, password, role, full_name, self.user_manager.current_user)
        if ok:
            self.result = login
            messagebox.showinfo("Успех", message)
            self.dialog.destroy()
        else:
            messagebox.showerror("Ошибка", message)

    def cancel(self):
        self.result = None
        self.dialog.destroy()


class EditUserDialog(DialogBase):
    def __init__(self, parent, user_manager, username):
        self.user_manager = user_manager
        self.username = username
        self.result = None
        user_info = user_manager.get_user_info(username)
        super().__init__(parent, f"Редактировать: {username}", "520x390")
        self.add_header("Редактирование пользователя", "Изменение ФИО, роли, логина и требования смены пароля.")
        body = self.body_frame()
        form = self.form_frame(body)
        self.entry_username = self.add_field(form, 0, "Логин", initial=username)
        if username == "admin":
            self.entry_username.config(state="disabled", disabledforeground=APP_THEME["muted_text"])
        self.entry_name = self.add_field(form, 1, "ФИО", initial=user_info.get("full_name", ""))
        self.combo_role = self.add_combobox(
            form,
            2,
            "Роль",
            ROLE_VALUES,
            initial=role_value_to_label(user_info.get("role", "viewer")),
            state="readonly" if username != "admin" else "disabled",
        )
        self.var_force = tk.BooleanVar(value=user_info.get("force_password_change", False))
        tk.Checkbutton(
            form,
            text="Требовать смену пароля",
            variable=self.var_force,
            bg=APP_THEME["surface"],
            fg=APP_THEME["text"],
            activebackground=APP_THEME["surface"],
            activeforeground=APP_THEME["text"],
            selectcolor=APP_THEME["surface_soft"],
            font=ui_font("size"),
        ).grid(row=3, column=0, columnspan=2, padx=0, pady=SPACING["md"], sticky="w")

        footer = self.add_footer()
        create_dialog_button(footer, "Сохранить", self.save).pack(
            side="left", padx=SPACING["panel"], pady=SPACING["md"]
        )
        create_dialog_button(footer, "Отмена", self.cancel, variant="secondary").pack(
            side="left", padx=(0, SPACING["sm"]), pady=SPACING["md"]
        )
        self.wait(self.cancel)

    def save(self):
        new_username = self.entry_username.get().strip()
        new_name = self.entry_name.get().strip()
        new_role = role_label_to_value(self.combo_role.get())
        force_change = self.var_force.get()
        if new_username and new_username != self.username and new_username != "admin":
            ok, message = self.user_manager.change_username(
                self.username,
                new_username,
                changed_by=self.user_manager.current_user,
            )
            if not ok:
                return messagebox.showerror("Ошибка", message)
            self.username = new_username
        ok, message = self.user_manager.update_user(
            self.username,
            new_role=new_role,
            new_full_name=new_name,
            force_password_change=force_change,
        )
        if ok:
            self.result = True
            messagebox.showinfo("Успех", message)
            self.dialog.destroy()
        else:
            messagebox.showerror("Ошибка", message)

    def cancel(self):
        self.result = None
        self.dialog.destroy()


class UserManagementDialog(DialogBase):
    def __init__(self, parent, user_manager, current_user, log_callback=None):
        self.user_manager = user_manager
        self.current_user = current_user
        self.log = log_callback or (lambda x: None)
        super().__init__(parent, "Пользователи", "900x600", resizable=True)
        self.add_header("Пользователи", "Управление ролями, паролями и доступом к системе.")
        body = self.body_frame()

        search_frame = tk.Frame(body, bg=APP_THEME["surface"])
        search_frame.pack(fill="x", pady=(0, SPACING["md"]))
        tk.Label(
            search_frame,
            text="Поиск",
            bg=APP_THEME["surface"],
            fg=APP_THEME["muted_text"],
            font=ui_font("small", "bold"),
        ).pack(side="left")
        self.search_var = tk.StringVar()
        search_entry = tk.Entry(
            search_frame,
            textvariable=self.search_var,
            bg=APP_THEME["surface_soft"],
            fg=APP_THEME["text"],
            relief="flat",
            highlightthickness=1,
            highlightbackground=APP_THEME["line"],
            highlightcolor=APP_THEME["primary_alt"],
            font=(FONT["family"], FONT["size"]),
        )
        search_entry.pack(side="left", fill="x", expand=True, padx=SPACING["sm"])
        search_entry.bind("<KeyRelease>", self.filter_users)
        create_dialog_button(search_frame, "Очистить", self.clear_search, variant="secondary", width=10).pack(
            side="left"
        )

        table_frame = tk.Frame(body, bg=APP_THEME["surface"])
        table_frame.pack(fill="both", expand=True)
        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)
        cols = ("username", "full_name", "role", "created_at", "last_login")
        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings", selectmode="browse")
        heads = {
            "username": "Логин",
            "full_name": "ФИО",
            "role": "Роль",
            "created_at": "Создан",
            "last_login": "Вход",
        }
        widths = {"username": 130, "full_name": 250, "role": 130, "created_at": 130, "last_login": 150}
        for col in cols:
            self.tree.heading(col, text=heads[col])
            self.tree.column(col, width=widths[col], minwidth=90, anchor="w")
        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        self.tree.bind("<<TreeviewSelect>>", self.on_select)
        self.tree.bind("<Double-1>", lambda e: self.edit_user())

        footer = self.add_footer()
        self.btn_pwd = create_dialog_button(footer, "Пароль", self.change_password, variant="secondary", width=12)
        self.btn_pwd.pack(side="left", padx=(SPACING["panel"], SPACING["xs"]), pady=SPACING["md"])
        self.btn_edit = create_dialog_button(footer, "Изменить", self.edit_user, variant="secondary", width=12)
        self.btn_edit.pack(side="left", padx=SPACING["xs"], pady=SPACING["md"])
        self.btn_del = create_dialog_button(footer, "Удалить", self.delete_user, variant="danger", width=12)
        self.btn_del.pack(side="left", padx=SPACING["xs"], pady=SPACING["md"])
        create_dialog_button(footer, "Добавить", self.add_user, width=12).pack(
            side="left", padx=SPACING["xs"], pady=SPACING["md"]
        )
        create_dialog_button(footer, "Закрыть", self.close, variant="secondary", width=12).pack(
            side="right", padx=SPACING["panel"], pady=SPACING["md"]
        )
        self.status_var = tk.StringVar()
        tk.Label(
            body,
            textvariable=self.status_var,
            bg=APP_THEME["surface"],
            fg=APP_THEME["muted_text"],
            font=ui_font("small"),
            anchor="w",
        ).pack(fill="x", pady=(SPACING["sm"], 0))
        self.refresh_list()
        self.on_select()
        self.wait(self.close)

    def close(self):
        self.dialog.destroy()

    def refresh_list(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        query = self.search_var.get().lower()
        for user in self.user_manager.get_users_list():
            role_label = ROLE_LABELS.get(user["role"], user["role"])
            searchable_values = [user["username"], user["full_name"], user["role"], role_label]
            if query and not any(query in str(value).lower() for value in searchable_values):
                continue
            last_login = user["last_login"]
            if last_login and last_login != "None" and "T" in last_login:
                last_login = last_login[:16].replace("T", " ")
            else:
                last_login = "Никогда"
            self.tree.insert(
                "",
                "end",
                values=(
                    user["username"],
                    user["full_name"],
                    role_label,
                    user["created_at"][:10] if user["created_at"] else "",
                    last_login,
                ),
            )
        self.status_var.set(f"Пользователей: {len(self.tree.get_children())}")

    def filter_users(self, event=None):
        self.refresh_list()

    def clear_search(self):
        self.search_var.set("")
        self.refresh_list()

    def on_select(self, event=None):
        selection = self.tree.selection()
        if not selection:
            for button in [self.btn_pwd, self.btn_edit, self.btn_del]:
                button.config(state="disabled")
            return
        values = self.tree.item(selection[0])["values"]
        username, role_label = values[0], values[2]
        is_self = username == self.current_user
        is_admin = role_label == ROLE_LABELS["admin"]
        self.btn_pwd.config(state="normal")
        self.btn_edit.config(state="normal" if not is_self else "disabled")
        self.btn_del.config(state="normal" if not is_self and not is_admin else "disabled")

    def add_user(self):
        dialog = AddUserDialog(self.dialog, self.user_manager)
        if dialog.result:
            self.refresh_list()
            self.log(f"Добавлен: {dialog.result}")

    def edit_user(self):
        selection = self.tree.selection()
        if not selection:
            return
        username = self.tree.item(selection[0])["values"][0]
        dialog = EditUserDialog(self.dialog, self.user_manager, username)
        if dialog.result:
            self.refresh_list()
            self.log(f"Изменён: {username}")

    def change_password(self):
        selection = self.tree.selection()
        if not selection:
            return
        username = self.tree.item(selection[0])["values"][0]
        dialog = ChangePasswordDialog(self.dialog, self.user_manager, username, is_admin_reset=(username != self.current_user))
        if dialog.result:
            self.log(f"Пароль изменён: {username}")

    def delete_user(self):
        selection = self.tree.selection()
        if not selection:
            return
        username = self.tree.item(selection[0])["values"][0]
        if messagebox.askyesno("Удалить", f"Удалить пользователя «{username}»?"):
            ok, message = self.user_manager.delete_user(username)
            if ok:
                self.refresh_list()
                messagebox.showinfo("Успех", message)
                self.log(f"Удалён: {username}")
            else:
                messagebox.showerror("Ошибка", message)


class FilterDialog(DialogBase):
    def __init__(self, parent, columns, on_apply):
        self.columns = columns
        self.on_apply = on_apply
        super().__init__(parent, "Расширенный фильтр", "460x250")
        self.add_header("Расширенный фильтр", "Выберите поле и значение для отбора записей.")
        body = self.body_frame()
        form = self.form_frame(body)
        self.field_var = tk.StringVar()
        self.field_combo = self.add_combobox(form, 0, "Поле", columns, width=30)
        self.value_entry = self.add_field(form, 1, "Значение", width=32)
        footer = self.add_footer()
        create_dialog_button(footer, "Применить", self.apply).pack(
            side="left", padx=SPACING["panel"], pady=SPACING["md"]
        )
        create_dialog_button(footer, "Отмена", self.close, variant="secondary").pack(
            side="left", padx=(0, SPACING["sm"]), pady=SPACING["md"]
        )
        self.value_entry.focus_set()
        self.wait(self.close)

    def apply(self):
        field = self.field_combo.get()
        value = self.value_entry.get().strip()
        if not field or not value:
            return messagebox.showwarning("Внимание", "Заполните поле и значение")
        self.on_apply(field, value)
        self.dialog.destroy()

    def close(self):
        self.dialog.destroy()


class ColumnSelectorDialog(DialogBase):
    def __init__(self, parent, columns, on_confirm, report_name="отчёта"):
        self.columns = columns
        self.on_confirm = on_confirm
        self.report_name = report_name
        self.vars = {}
        super().__init__(parent, "Колонки отчёта", "620x640", resizable=True)
        self.build_report_column_card()
        self.wait(self.close)

    def build_report_column_card(self):
        self.dialog.configure(bg=APP_THEME["app_background"])
        self.add_header(
            "Параметры отчёта",
            f"Выберите поля, которые попадут в выгрузку {self.report_name}.",
        )
        body = self.body_frame(padx=SPACING["lg"], pady=SPACING["lg"])

        summary = tk.Frame(
            body,
            bg=APP_THEME["surface"],
            highlightbackground=APP_THEME["line"],
            highlightthickness=1,
        )
        summary.pack(fill="x", pady=(0, SPACING["md"]))
        tk.Label(
            summary,
            text="Доступные поля",
            bg=APP_THEME["surface"],
            fg=APP_THEME["text"],
            font=ui_font("heading", "bold"),
            anchor="w",
        ).pack(fill="x", padx=SPACING["lg"], pady=(SPACING["md"], 2))
        tk.Label(
            summary,
            text=f"Всего колонок: {len(self.columns)}. По умолчанию выбраны все поля.",
            bg=APP_THEME["surface"],
            fg=APP_THEME["muted_text"],
            font=ui_font("small"),
            anchor="w",
        ).pack(fill="x", padx=SPACING["lg"], pady=(0, SPACING["md"]))

        toolbar = tk.Frame(summary, bg=APP_THEME["surface"])
        toolbar.pack(fill="x", padx=SPACING["lg"], pady=(0, SPACING["md"]))
        create_dialog_button(toolbar, "Выбрать все", self.select_all_columns, variant="secondary", width=14).pack(
            side="left", padx=(0, SPACING["sm"])
        )
        create_dialog_button(toolbar, "Снять выбор", self.clear_column_selection, variant="secondary", width=14).pack(
            side="left"
        )

        list_card = tk.Frame(
            body,
            bg=APP_THEME["surface"],
            highlightbackground=APP_THEME["line"],
            highlightthickness=1,
        )
        list_card.pack(fill="both", expand=True)

        canvas = tk.Canvas(list_card, bg=APP_THEME["surface"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(list_card, orient="vertical", command=canvas.yview)
        scroll_frame = tk.Frame(canvas, bg=APP_THEME["surface"])
        scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        scroll_id = canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True, padx=(SPACING["md"], 0), pady=SPACING["md"])
        scrollbar.pack(side="right", fill="y", padx=(0, SPACING["md"]), pady=SPACING["md"])
        canvas.bind("<Configure>", lambda e: canvas.itemconfigure(scroll_id, width=e.width))

        for column in self.columns:
            var = tk.BooleanVar(value=True)
            self.vars[column] = var
            tk.Checkbutton(
                scroll_frame,
                text=column,
                variable=var,
                bg=APP_THEME["surface"],
                fg=APP_THEME["text"],
                activebackground=APP_THEME["surface"],
                activeforeground=APP_THEME["text"],
                selectcolor=APP_THEME["surface_soft"],
                anchor="w",
                font=ui_font("size"),
                padx=SPACING["sm"],
                pady=SPACING["xs"],
            ).pack(fill="x", pady=1)

        footer = self.add_footer()
        create_dialog_button(footer, "Выбрать", self.confirm).pack(
            side="left", padx=SPACING["panel"], pady=SPACING["md"]
        )
        create_dialog_button(footer, "Отмена", self.close, variant="secondary").pack(
            side="left", padx=(0, SPACING["sm"]), pady=SPACING["md"]
        )

    def select_all_columns(self):
        for var in self.vars.values():
            var.set(True)

    def clear_column_selection(self):
        for var in self.vars.values():
            var.set(False)

    def confirm(self):
        selected = [column for column, var in self.vars.items() if var.get()]
        self.on_confirm(selected)
        self.dialog.destroy()

    def close(self):
        self.dialog.destroy()


class RecordDialog(DialogBase):
    def __init__(self, parent, title, columns, initial_values=None, on_save=None):
        self.columns = columns
        self.on_save = on_save
        self.initial_values = {}
        if initial_values:
            for key, value in initial_values.items():
                if key != "_original_index":
                    self.initial_values[key] = "" if pd.isna(value) else str(value)
        self.entries = {}
        self.comboboxes = {}
        super().__init__(parent, title, "980x720", resizable=True)
        self.build_record_card(title)
        self.wait(self.close)

    def get_record_sections(self):
        visible_columns = [column for column in self.columns if column != "_original_index"]
        primary_fields = [
            "ФИО",
            "Название диссертации",
            "Год защиты",
            "Дата защиты диссертации",
            "Искомая степень",
            "Специальность",
            "Диссертационный совет",
        ]
        supervisor_fields = [
            "1 Научный руководитель (консультант)",
            "2 Научный руководитель (консультант)",
        ]
        service_fields = [
            "Примечания",
            "Информация о лишении степени",
        ]
        sections = []
        assigned = set()
        for title, wanted_fields in (
            ("Основные сведения", primary_fields),
            ("Научное сопровождение", supervisor_fields),
            ("Служебная информация", service_fields),
        ):
            fields = [field for field in wanted_fields if field in visible_columns]
            if fields:
                sections.append((title, fields))
                assigned.update(fields)
        extra_fields = [field for field in visible_columns if field not in assigned]
        if extra_fields:
            sections.append(("Дополнительные сведения", extra_fields))
        return sections

    def is_long_record_field(self, column):
        column_lower = column.lower()
        return any(marker in column_lower for marker in ("название", "примеч", "информация"))

    def build_record_card(self, title):
        self.dialog.configure(bg=APP_THEME["app_background"])
        header_title = "Новая запись" if title == "Добавить" else title
        header = tk.Frame(self.dialog, bg=APP_THEME["topbar"], height=112)
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Label(
            header,
            text=header_title,
            bg=APP_THEME["topbar"],
            fg=APP_THEME["topbar_text"],
            font=ui_font("title", "bold"),
            anchor="w",
        ).pack(fill="x", padx=SPACING["lg"], pady=(SPACING["lg"], 2))
        tk.Label(
            header,
            text="Заполните карточку записи. Поля сгруппированы так же, как в просмотре записи.",
            bg=APP_THEME["topbar"],
            fg=APP_THEME["topbar_muted"],
            font=ui_font("small"),
            anchor="w",
            justify="left",
            wraplength=760,
        ).pack(fill="x", padx=SPACING["lg"], pady=(0, SPACING["md"]))

        record_footer = tk.Frame(self.dialog, bg=APP_THEME["surface"], height=76)
        record_footer.pack(side="bottom", fill="x")
        record_footer.pack_propagate(False)
        tk.Label(
            record_footer,
            text="Проверьте данные перед сохранением записи.",
            bg=APP_THEME["surface"],
            fg=APP_THEME["muted_text"],
            font=ui_font("small"),
            anchor="w",
        ).pack(side="left", fill="x", expand=True, padx=SPACING["lg"], pady=SPACING["md"])
        actions = tk.Frame(record_footer, bg=APP_THEME["surface"])
        actions.pack(side="right", padx=SPACING["lg"], pady=SPACING["md"])
        create_dialog_button(actions, "Сохранить", self.save, width=18).pack(side="left", padx=(0, SPACING["sm"]))
        create_dialog_button(actions, "Отмена", self.close, variant="secondary", width=14).pack(side="left")

        content_shell = tk.Frame(self.dialog, bg=APP_THEME["app_background"])
        content_shell.pack(fill="both", expand=True)
        self.record_canvas = tk.Canvas(content_shell, bg=APP_THEME["app_background"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(content_shell, orient="vertical", command=self.record_canvas.yview)
        scroll_frame = tk.Frame(self.record_canvas, bg=APP_THEME["app_background"])
        scroll_frame.bind(
            "<Configure>",
            lambda e: self.record_canvas.configure(scrollregion=self.record_canvas.bbox("all")),
        )
        scroll_id = self.record_canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        self.record_canvas.configure(yscrollcommand=scrollbar.set)
        self.record_canvas.pack(side="left", fill="both", expand=True, padx=(SPACING["lg"], 0), pady=SPACING["lg"])
        scrollbar.pack(side="right", fill="y", padx=(0, SPACING["lg"]), pady=SPACING["lg"])
        self.record_canvas.bind("<Configure>", lambda e: self.record_canvas.itemconfigure(scroll_id, width=e.width))

        for section_title, section_columns in self.get_record_sections():
            section = self.create_record_section(scroll_frame, section_title)
            grid_row = 0
            grid_column = 0
            for column in section_columns:
                if self.is_long_record_field(column):
                    if grid_column != 0:
                        grid_row += 1
                        grid_column = 0
                    self.create_record_field(section, column, grid_row, column_index=0, columnspan=2)
                    grid_row += 1
                    grid_column = 0
                else:
                    self.create_record_field(section, column, grid_row, column_index=grid_column)
                    if grid_column == 0:
                        grid_column = 1
                    else:
                        grid_row += 1
                        grid_column = 0

    def create_record_section(self, parent, title):
        section = tk.Frame(
            parent,
            bg=APP_THEME["surface"],
            highlightbackground=APP_THEME["line"],
            highlightthickness=1,
        )
        section.pack(fill="x", padx=SPACING["lg"], pady=(0, SPACING["md"]))
        tk.Label(
            section,
            text=title,
            bg=APP_THEME["surface"],
            fg=APP_THEME["text"],
            font=ui_font("heading", "bold"),
            anchor="w",
        ).pack(fill="x", padx=SPACING["lg"], pady=(SPACING["md"], SPACING["sm"]))
        content = tk.Frame(section, bg=APP_THEME["surface"])
        content.pack(fill="x", padx=SPACING["lg"], pady=(0, SPACING["md"]))
        content.columnconfigure(0, weight=1, uniform="record_dialog_fields")
        content.columnconfigure(1, weight=1, uniform="record_dialog_fields")
        return content

    def create_record_field(self, parent, column, row, column_index=0, columnspan=1):
        padx = (0, SPACING["md"]) if column_index == 0 and columnspan == 1 else (0, 0)
        field = tk.Frame(parent, bg=APP_THEME["surface"])
        field.grid(
            row=row,
            column=column_index,
            columnspan=columnspan,
            sticky="ew",
            padx=padx,
            pady=(0, SPACING["md"]),
        )
        field.columnconfigure(0, weight=1)
        tk.Label(
            field,
            text=column,
            bg=APP_THEME["surface"],
            fg=APP_THEME["muted_text"],
            font=ui_font("small", "bold"),
            anchor="w",
        ).grid(row=0, column=0, sticky="ew", pady=(0, SPACING["xs"]))

        initial = self.initial_values.get(column, "")
        if column == "Искомая степень":
            combo = ttk.Combobox(
                field,
                values=DEGREE_OPTIONS,
                state="readonly",
                font=ui_font("size"),
            )
            combo.set(initial if initial else DEGREE_OPTIONS[0])
            combo.grid(row=1, column=0, sticky="ew", ipady=SPACING["xs"])
            self.comboboxes[column] = combo
            return combo

        if self.is_long_record_field(column):
            height = 4 if "название" in column.lower() else 3
            widget = tk.Text(
                field,
                height=height,
                wrap="word",
                bg=APP_THEME["surface_soft"],
                fg=APP_THEME["text"],
                insertbackground=APP_THEME["text"],
                relief="flat",
                bd=0,
                highlightthickness=1,
                highlightbackground=APP_THEME["line"],
                highlightcolor=APP_THEME["primary_alt"],
                font=ui_font("size"),
                padx=SPACING["sm"],
                pady=SPACING["sm"],
            )
            widget.insert("1.0", initial)
            widget.grid(row=1, column=0, sticky="ew")
            self.entries[column] = widget
            return widget

        widget = tk.Entry(
            field,
            width=36,
            bg=APP_THEME["surface_soft"],
            fg=APP_THEME["text"],
            insertbackground=APP_THEME["text"],
            relief="flat",
            bd=0,
            highlightthickness=1,
            highlightbackground=APP_THEME["line"],
            highlightcolor=APP_THEME["primary_alt"],
            font=ui_font("size"),
        )
        widget.insert(0, initial)
        widget.grid(row=1, column=0, sticky="ew", ipady=SPACING["xs"])
        enable_entry_shortcuts(widget)
        self.entries[column] = widget
        return widget

    def read_record_widget_value(self, widget):
        if isinstance(widget, tk.Text):
            return widget.get("1.0", "end-1c").strip()
        return widget.get().strip()

    def save(self):
        new_record = {}
        for column in self.columns:
            if column == "_original_index":
                continue
            if column == "Искомая степень" and column in self.comboboxes:
                value = self.comboboxes[column].get().strip()
            elif column in self.entries:
                value = self.read_record_widget_value(self.entries[column])
            else:
                value = ""
            if column == "Дата защиты диссертации" and value and not re.match(r"\d{2}\.\d{2}\.\d{4}", value):
                return messagebox.showerror("Ошибка", "Дата должна быть в формате ДД.ММ.ГГГГ")
            new_record[column] = value if value else None
        if self.on_save:
            self.on_save(new_record)
        self.dialog.destroy()

    def close(self):
        self.dialog.destroy()
