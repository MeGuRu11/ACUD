"""Tkinter dialogs used by the ASUD application."""

import re
import tkinter as tk
from tkinter import messagebox, ttk

import pandas as pd

from asud.config import DEGREE_OPTIONS
from asud.ui.theme import APP_THEME, FONT, ROLE_LABELS, SPACING, configure_ttk_style

LOGIN_DIALOG_SIZE = "520x440"


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
        self.result = None
        super().__init__(parent, "Вход в систему", LOGIN_DIALOG_SIZE)
        self.build_login_card()
        self.dialog.bind("<Return>", lambda e: self.login())
        self.entry_login.focus_set()
        self.wait(self.cancel)

    def build_login_card(self):
        hero = tk.Frame(self.dialog, bg=APP_THEME["topbar"], height=140)
        hero.pack(fill="x")
        hero.pack_propagate(False)

        badge = tk.Frame(hero, bg=APP_THEME["primary_alt"], width=52, height=52)
        badge.pack(side="left", padx=(SPACING["lg"], SPACING["panel"]), pady=SPACING["lg"])
        badge.pack_propagate(False)
        tk.Label(
            badge,
            text="АС",
            bg=APP_THEME["primary_alt"],
            fg=APP_THEME["topbar_text"],
            font=ui_font("heading", "bold"),
        ).pack(expand=True)

        hero_text = tk.Frame(hero, bg=APP_THEME["topbar"])
        hero_text.pack(side="left", fill="both", expand=True, pady=SPACING["lg"], padx=(0, SPACING["lg"]))
        tk.Label(
            hero_text,
            text="АСУД",
            bg=APP_THEME["topbar"],
            fg=APP_THEME["topbar_muted"],
            font=ui_font("small", "bold"),
            anchor="w",
        ).pack(fill="x", pady=(0, 2))
        tk.Label(
            hero_text,
            text="Добро пожаловать",
            bg=APP_THEME["topbar"],
            fg=APP_THEME["topbar_text"],
            font=(FONT["family"], 22, "bold"),
            anchor="w",
        ).pack(fill="x")
        tk.Label(
            hero_text,
            text="Войдите, чтобы работать с реестром диссертаций.",
            bg=APP_THEME["topbar"],
            fg=APP_THEME["topbar_muted"],
            font=ui_font("size"),
            anchor="w",
        ).pack(fill="x", pady=(4, 0))

        body = self.body_frame(padx=SPACING["lg"], pady=SPACING["lg"])
        card = tk.Frame(
            body,
            bg=APP_THEME["surface"],
            highlightbackground=APP_THEME["line"],
            highlightthickness=1,
        )
        card.pack(fill="both", expand=True)
        card.columnconfigure(0, weight=1)

        form = self.form_frame(card)
        form.pack(fill="x", padx=SPACING["panel"], pady=(SPACING["panel"], SPACING["sm"]))
        self.entry_login = self.add_field(form, 0, "Логин")
        self.entry_password = self.add_field(form, 1, "Пароль", show="*")

        footer = self.add_footer()
        create_dialog_button(footer, "Войти", self.login, width=16).pack(
            side="left", padx=SPACING["lg"], pady=SPACING["md"]
        )
        create_dialog_button(footer, "Отмена", self.cancel, variant="secondary").pack(
            side="left", padx=(0, SPACING["sm"]), pady=SPACING["md"]
        )
        tk.Button(
            card,
            text="Зарегистрировать нового пользователя",
            command=self.open_registration,
            bg=APP_THEME["surface"],
            fg=APP_THEME["primary"],
            activebackground=APP_THEME["surface_soft"],
            activeforeground=APP_THEME["primary"],
            font=ui_font("small", "bold"),
            relief="flat",
            cursor="hand2",
        ).pack(anchor="w", padx=SPACING["panel"], pady=(0, SPACING["panel"]))

    def open_registration(self):
        registration = RegistrationDialog(self.dialog, self.user_manager)
        if registration.result:
            self.entry_login.focus_set()

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
            self.dialog.destroy()
        else:
            messagebox.showerror("Ошибка", "Неверный логин или пароль")

    def cancel(self):
        self.result = None
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
        super().__init__(parent, "Добавить пользователя", "500x400")
        self.add_header("Добавить пользователя", "Администратор создаёт учётную запись и назначает роль.")
        body = self.body_frame()
        form = self.form_frame(body)
        self.entries = {
            "login": self.add_field(form, 0, "Логин"),
            "password": self.add_field(form, 1, "Пароль", show="*"),
            "fullname": self.add_field(form, 2, "ФИО"),
            "role": self.add_combobox(form, 3, "Роль", ["viewer", "editor", "admin"], initial="viewer"),
        }
        footer = self.add_footer()
        create_dialog_button(footer, "Создать", self.create).pack(
            side="left", padx=SPACING["panel"], pady=SPACING["md"]
        )
        create_dialog_button(footer, "Отмена", self.cancel, variant="secondary").pack(
            side="left", padx=(0, SPACING["sm"]), pady=SPACING["md"]
        )
        self.entries["login"].focus_set()
        self.wait(self.cancel)

    def create(self):
        login = self.entries["login"].get().strip()
        password = self.entries["password"].get()
        full_name = self.entries["fullname"].get().strip()
        role = self.entries["role"].get()
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
            ["viewer", "editor", "admin"],
            initial=user_info.get("role", "viewer"),
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
        new_role = self.combo_role.get()
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
            if query and not any(query in str(user[key]).lower() for key in ["username", "full_name", "role"]):
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
                    ROLE_LABELS.get(user["role"], user["role"]),
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
    def __init__(self, parent, columns, on_confirm):
        self.columns = columns
        self.on_confirm = on_confirm
        self.vars = {}
        super().__init__(parent, "Колонки отчёта", "430x470")
        self.add_header("Колонки отчёта", "Выберите поля, которые должны попасть в выгрузку.")
        body = self.body_frame()
        canvas = tk.Canvas(body, bg=APP_THEME["surface"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(body, orient="vertical", command=canvas.yview)
        scroll_frame = tk.Frame(canvas, bg=APP_THEME["surface"])
        scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        for column in columns:
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
            ).pack(fill="x", pady=2)
        footer = self.add_footer()
        create_dialog_button(footer, "Выбрать", self.confirm).pack(
            side="left", padx=SPACING["panel"], pady=SPACING["md"]
        )
        create_dialog_button(footer, "Отмена", self.close, variant="secondary").pack(
            side="left", padx=(0, SPACING["sm"]), pady=SPACING["md"]
        )
        self.wait(self.close)

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
        super().__init__(parent, title, "680x560", resizable=True)
        self.add_header(title, "Заполните карточку записи. Пустые поля не будут затирать существующие значения.")
        body = self.body_frame()
        canvas = tk.Canvas(body, bg=APP_THEME["surface"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(body, orient="vertical", command=canvas.yview)
        scroll_frame = tk.Frame(canvas, bg=APP_THEME["surface"])
        scroll_frame.columnconfigure(1, weight=1)
        scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        row = 0
        for column in columns:
            if column == "_original_index":
                continue
            if column == "Искомая степень":
                combo = self.add_combobox(
                    scroll_frame,
                    row,
                    column,
                    DEGREE_OPTIONS,
                    initial=self.initial_values.get(column, ""),
                    width=44,
                )
                self.comboboxes[column] = combo
            else:
                entry = self.add_field(scroll_frame, row, column, width=46, initial=self.initial_values.get(column, ""))
                self.entries[column] = entry
            row += 1

        footer = self.add_footer()
        create_dialog_button(footer, "Сохранить", self.save).pack(
            side="left", padx=SPACING["panel"], pady=SPACING["md"]
        )
        create_dialog_button(footer, "Отмена", self.close, variant="secondary").pack(
            side="left", padx=(0, SPACING["sm"]), pady=SPACING["md"]
        )
        self.wait(self.close)

    def save(self):
        new_record = {}
        for column in self.columns:
            if column == "_original_index":
                continue
            if column == "Искомая степень" and column in self.comboboxes:
                value = self.comboboxes[column].get().strip()
            elif column in self.entries:
                value = self.entries[column].get().strip()
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
