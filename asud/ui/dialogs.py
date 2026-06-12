"""Tkinter dialogs used by the ASUD application."""

import re
import tkinter as tk
from tkinter import messagebox, ttk

import pandas as pd

from asud.config import DEGREE_OPTIONS


class LoginDialog:
    def __init__(self, parent, user_manager):
        self.parent, self.user_manager, self.result = parent, user_manager, None
        self.dialog = tk.Toplevel(parent);
        self.dialog.title("Вход");
        self.dialog.geometry("380x280");
        self.dialog.configure(bg="#0b2a1b");
        self.dialog.transient(parent);
        self.dialog.grab_set();
        self.dialog.resizable(False, False)
        tk.Label(self.dialog, text="Военно-медицинская академия", font=("Times New Roman", 12, "bold"), fg="#d4af37",
                 bg="#0b2a1b").pack(pady=(10, 5))
        tk.Label(self.dialog, text="Введите учётные данные", font=("Times New Roman", 10), fg="#ffffff",
                 bg="#0b2a1b").pack(pady=(0, 10))
        f = tk.Frame(self.dialog, bg="#0b2a1b");
        f.pack(pady=5)
        tk.Label(f, text="Логин:", bg="#0b2a1b", fg="#ffffff").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        self.entry_login = tk.Entry(f, width=25);
        self.entry_login.grid(row=0, column=1, padx=5, pady=5)
        tk.Label(f, text="Пароль:", bg="#0b2a1b", fg="#ffffff").grid(row=1, column=0, padx=5, pady=5, sticky="e")
        self.entry_password = tk.Entry(f, show="*", width=25);
        self.entry_password.grid(row=1, column=1, padx=5, pady=5)
        bf = tk.Frame(self.dialog, bg="#0b2a1b");
        bf.pack(pady=10)
        tk.Button(bf, text="Войти", command=self.login, bg="#d4af37", fg="black", width=12).pack(side="left", padx=5)
        tk.Button(bf, text="Отмена", command=self.cancel, bg="#666666", fg="white", width=12).pack(side="left", padx=5)
        rf = tk.Frame(self.dialog, bg="#0b2a1b");
        rf.pack(pady=(5, 10))
        tk.Button(rf, text="🔹 Нет аккаунта? Зарегистрироваться", command=self.open_registration, bg="#1a3d2a",
                  fg="#d4af37", font=("Times New Roman", 9), relief="flat", cursor="hand2").pack()
        self.dialog.bind("<Return>", lambda e: self.login())
        self.dialog.update_idletasks();
        self.dialog.geometry(
            f'+{(self.dialog.winfo_screenwidth() // 2) - 190}+{(self.dialog.winfo_screenheight() // 2) - 140}')
        self.dialog.protocol("WM_DELETE_WINDOW", self.cancel)
        self.parent.wait_window(self.dialog)

    def open_registration(self):
        r = RegistrationDialog(self.dialog, self.user_manager)
        if r.result: self.entry_login.focus_set()

    def login(self):
        u, p = self.entry_login.get().strip(), self.entry_password.get()
        if not u or not p: return messagebox.showerror("Ошибка", "Введите логин и пароль")
        ok, role, fc = self.user_manager.authenticate(u, p)
        if ok:
            if fc and u != "admin":
                if not messagebox.askyesno("Смена пароля", "Сменить пароль?"): return
                pd = ChangePasswordDialog(self.dialog, self.user_manager, u, False)
                if not pd.result: return
            self.result = (u, role);
            self.dialog.destroy()
        else:
            messagebox.showerror("Ошибка", "Неверный логин или пароль")

    def cancel(self):
        self.result = None;
        self.dialog.destroy()


class ChangePasswordDialog:
    def __init__(self, parent, user_manager, username, is_admin_reset=False):
        self.parent, self.user_manager, self.username, self.is_admin_reset, self.result = parent, user_manager, username, is_admin_reset, None
        self.dialog = tk.Toplevel(parent);
        self.dialog.title("Смена пароля" if not is_admin_reset else f"Сброс: {username}");
        self.dialog.geometry("420x380");
        self.dialog.configure(bg="#0b2a1b");
        self.dialog.transient(parent);
        self.dialog.grab_set();
        self.dialog.resizable(False, False)
        tk.Label(self.dialog, text="🔐 Безопасность", font=("Times New Roman", 12, "bold"), fg="#d4af37",
                 bg="#0b2a1b").pack(pady=(15, 5))
        tk.Label(self.dialog, text="Мин. 8 символов • Заглавная/строчная • Цифра", font=("Times New Roman", 9),
                 fg="#cccccc", bg="#0b2a1b").pack(pady=(0, 15))
        ff = tk.Frame(self.dialog, bg="#0b2a1b");
        ff.pack(pady=5)
        r = 0
        if not is_admin_reset: tk.Label(ff, text="Текущий:", bg="#0b2a1b", fg="#ffffff").grid(row=r, column=0, padx=10,
                                                                                              pady=5,
                                                                                              sticky="e"); self.entry_old = tk.Entry(
            ff, show="*", width=28); self.entry_old.grid(row=r, column=1, padx=10, pady=5); r += 1
        tk.Label(ff, text="Новый:", bg="#0b2a1b", fg="#ffffff").grid(row=r, column=0, padx=10, pady=5, sticky="e");
        self.entry_new = tk.Entry(ff, show="*", width=28);
        self.entry_new.grid(row=r, column=1, padx=10, pady=5);
        r += 1
        tk.Label(ff, text="Повтор:", bg="#0b2a1b", fg="#ffffff").grid(row=r, column=0, padx=10, pady=5, sticky="e");
        self.entry_confirm = tk.Entry(ff, show="*", width=28);
        self.entry_confirm.grid(row=r, column=1, padx=10, pady=5)
        self.strength_var = tk.StringVar();
        tk.Label(ff, textvariable=self.strength_var, bg="#0b2a1b", fg="#d4af37", font=("Times New Roman", 9)).grid(
            row=r + 1, column=1, padx=10, pady=2, sticky="w")
        self.entry_new.bind("<KeyRelease>", self.check_strength)
        bf = tk.Frame(self.dialog, bg="#0b2a1b");
        bf.pack(pady=20)
        tk.Button(bf, text="Сохранить", command=self.save, bg="#d4af37", fg="black", width=12).pack(side="left",
                                                                                                    padx=10)
        tk.Button(bf, text="Отмена", command=self.dialog.destroy, bg="#666666", fg="white", width=12).pack(side="left",
                                                                                                           padx=10)
        self.dialog.bind("<Return>", lambda e: self.save());
        self.entry_new.focus_set()
        self.dialog.update_idletasks();
        self.dialog.geometry(
            f'+{(self.dialog.winfo_screenwidth() // 2) - 210}+{(self.dialog.winfo_screenheight() // 2) - 190}')
        self.dialog.protocol("WM_DELETE_WINDOW", self.cancel);
        self.parent.wait_window(self.dialog)

    def check_strength(self, event=None):
        p = self.entry_new.get();
        s = sum(
            [len(p) >= 8, bool(re.search(r'[A-ZА-ЯЁ]', p)), bool(re.search(r'[a-zа-яё]', p)), bool(re.search(r'\d', p)),
             bool(re.search(r'[!@#$%^&*(),.?":{}|<>]', p))])
        lv = ["", "Слабый", "Средний", "Хороший", "Отличный", "Максимум"];
        cl = ["", "#ff6b6b", "#feca57", "#48dbfb", "#1dd1a1", "#00d2d3"]
        self.strength_var.set(f"Сложность: {lv[s]}")

    def save(self):
        o = self.entry_old.get() if hasattr(self, 'entry_old') else None;
        n = self.entry_new.get();
        c = self.entry_confirm.get()
        if n != c: return messagebox.showerror("Ошибка", "Пароли не совпадают")
        if not n: return messagebox.showerror("Ошибка", "Введите пароль")
        ok, msg = self.user_manager.change_password(self.username, o, n, not self.is_admin_reset)
        if ok:
            self.result = True;
            messagebox.showinfo("Успех", msg);
            self.dialog.destroy()
        else:
            messagebox.showerror("Ошибка", msg)

    def cancel(self):
        self.result = False;
        self.dialog.destroy()


class RegistrationDialog:
    def __init__(self, parent, user_manager):
        self.parent, self.user_manager, self.result = parent, user_manager, None
        self.dialog = tk.Toplevel(parent);
        self.dialog.title("Регистрация");
        self.dialog.geometry("450x440");
        self.dialog.configure(bg="#0b2a1b");
        self.dialog.transient(parent);
        self.dialog.grab_set();
        self.dialog.resizable(False, False)
        tk.Label(self.dialog, text="📝 Регистрация", font=("Times New Roman", 14, "bold"), fg="#d4af37",
                 bg="#0b2a1b").pack(pady=(15, 5))
        tk.Label(self.dialog, text="Права: «Наблюдатель»", font=("Times New Roman", 9), fg="#cccccc",
                 bg="#0b2a1b").pack(pady=(0, 10))
        ff = tk.Frame(self.dialog, bg="#0b2a1b");
        ff.pack(pady=5)

        # 🔧 ИСПРАВЛЕНО: Правильная сетка — индикатор сложности не перекрывает ФИО
        # Строки: 0=Логин, 1=Пароль, 2=Повтор+индикатор, 3=ФИО
        tk.Label(ff, text="Логин:", bg="#0b2a1b", fg="#ffffff").grid(row=0, column=0, padx=10, pady=5, sticky="e")
        self.entry_login = tk.Entry(ff, width=30);
        self.entry_login.grid(row=0, column=1, padx=10, pady=5);
        self.entries = {"login": self.entry_login}

        tk.Label(ff, text="Пароль:", bg="#0b2a1b", fg="#ffffff").grid(row=1, column=0, padx=10, pady=5, sticky="e")
        self.entry_password = tk.Entry(ff, show="*", width=30);
        self.entry_password.grid(row=1, column=1, padx=10, pady=5);
        self.entries["password"] = self.entry_password
        self.entry_password.bind("<KeyRelease>", self.check_strength)

        tk.Label(ff, text="Повтор:", bg="#0b2a1b", fg="#ffffff").grid(row=2, column=0, padx=10, pady=5, sticky="e")
        self.entry_confirm = tk.Entry(ff, show="*", width=30);
        self.entry_confirm.grid(row=2, column=1, padx=10, pady=5);
        self.entries["confirm"] = self.entry_confirm

        # 🔧 Индикатор сложности — на отдельной строке, растянут на обе колонки
        self.strength_var = tk.StringVar()
        tk.Label(ff, textvariable=self.strength_var, bg="#0b2a1b", fg="#d4af37", font=("Times New Roman", 9)).grid(
            row=3, column=0, columnspan=2, padx=10, pady=2, sticky="w")

        tk.Label(ff, text="ФИО:", bg="#0b2a1b", fg="#ffffff").grid(row=4, column=0, padx=10, pady=5, sticky="e")
        self.entry_fullname = tk.Entry(ff, width=30);
        self.entry_fullname.grid(row=4, column=1, padx=10, pady=5);
        self.entries["fullname"] = self.entry_fullname

        bf = tk.Frame(self.dialog, bg="#0b2a1b");
        bf.pack(pady=15)
        tk.Button(bf, text="Зарегистрироваться", command=self.register, bg="#d4af37", fg="black", width=20,
                  font=("Times New Roman", 10, "bold")).pack(side="left", padx=10)
        tk.Button(bf, text="Отмена", command=self.dialog.destroy, bg="#666666", fg="white", width=12).pack(side="left",
                                                                                                           padx=10)
        self.entry_login.focus_set();
        self.dialog.bind("<Return>", lambda e: self.register())
        self.dialog.update_idletasks();
        self.dialog.geometry(
            f'+{(self.dialog.winfo_screenwidth() // 2) - 225}+{(self.dialog.winfo_screenheight() // 2) - 220}')
        self.dialog.protocol("WM_DELETE_WINDOW", self.cancel);
        self.parent.wait_window(self.dialog)

    def check_strength(self, event=None):
        p = self.entries["password"].get();
        s = sum(
            [len(p) >= 8, bool(re.search(r'[A-ZА-ЯЁ]', p)), bool(re.search(r'[a-zа-яё]', p)), bool(re.search(r'\d', p)),
             bool(re.search(r'[!@#$%^&*(),.?":{}|<>]', p))])
        lv = ["", "Слабый", "Средний", "Хороший", "Отличный", "Максимум"];
        cl = ["", "#ff6b6b", "#feca57", "#48dbfb", "#1dd1a1", "#00d2d3"]
        self.strength_var.set(f"Сложность: {lv[s]}")

    def register(self):
        l = self.entries["login"].get().strip();
        p = self.entries["password"].get();
        c = self.entries["confirm"].get();
        f = self.entries["fullname"].get().strip()
        if not l or not p or not f: return messagebox.showerror("Ошибка", "Заполните все поля")
        if p != c: return messagebox.showerror("Ошибка", "Пароли не совпадают")
        ok, msg = self.user_manager.register_user(l, p, f)
        if ok:
            self.result = l;
            messagebox.showinfo("Успех", msg);
            self.dialog.destroy()
        else:
            messagebox.showerror("Ошибка", msg)

    def cancel(self):
        self.result = False;
        self.dialog.destroy()


class AddUserDialog:
    def __init__(self, parent, user_manager):
        self.parent, self.user_manager, self.result = parent, user_manager, None
        self.dialog = tk.Toplevel(parent);
        self.dialog.title("Добавить");
        self.dialog.geometry("420x340");
        self.dialog.configure(bg="#0b2a1b");
        self.dialog.transient(parent);
        self.dialog.grab_set()
        ff = tk.Frame(self.dialog, bg="#0b2a1b");
        ff.pack(pady=15)
        fields = [("Логин", "login"), ("Пароль", "password"), ("ФИО", "fullname"), ("Роль", "role")]
        self.entries = {}
        for i, (l, k) in enumerate(fields):
            tk.Label(ff, text=l, bg="#0b2a1b", fg="#ffffff").grid(row=i, column=0, padx=10, pady=5, sticky="e")
            if k == "role":
                e = ttk.Combobox(ff, values=["viewer", "editor", "admin"], state="readonly", width=28);
                e.set("viewer")
            elif k == "password":
                e = tk.Entry(ff, show="*", width=28)
            else:
                e = tk.Entry(ff, width=28)
            e.grid(row=i, column=1, padx=10, pady=5);
            self.entries[k] = e
        bf = tk.Frame(self.dialog, bg="#0b2a1b");
        bf.pack(pady=15)
        tk.Button(bf, text="Создать", command=self.create, bg="#d4af37", width=12).pack(side="left", padx=10)
        tk.Button(bf, text="Отмена", command=self.dialog.destroy, bg="#666666", fg="white", width=12).pack(side="left",
                                                                                                           padx=10)
        self.entries["login"].focus_set();
        self.parent.wait_window(self.dialog)

    def create(self):
        l = self.entries["login"].get().strip();
        p = self.entries["password"].get();
        f = self.entries["fullname"].get().strip();
        r = self.entries["role"].get()
        ok, msg = self.user_manager.add_user(l, p, r, f, self.user_manager.current_user)
        if ok:
            self.result = l;
            messagebox.showinfo("Успех", msg);
            self.dialog.destroy()
        else:
            messagebox.showerror("Ошибка", msg)


class EditUserDialog:
    def __init__(self, parent, user_manager, username):
        self.parent, self.user_manager, self.username, self.result = parent, user_manager, username, None
        ui = user_manager.get_user_info(username)
        self.dialog = tk.Toplevel(parent);
        self.dialog.title(f"Редактировать: {username}");
        self.dialog.geometry("450x320");
        self.dialog.configure(bg="#0b2a1b");
        self.dialog.transient(parent);
        self.dialog.grab_set()
        ff = tk.Frame(self.dialog, bg="#0b2a1b");
        ff.pack(pady=15)

        # 🔧 НОВОЕ: Поле для изменения логина (недоступно для admin)
        tk.Label(ff, text="Логин:", bg="#0b2a1b", fg="#ffffff").grid(row=0, column=0, padx=10, pady=5, sticky="e")
        self.entry_username = tk.Entry(ff, width=28)
        self.entry_username.grid(row=0, column=1, padx=10, pady=5)
        self.entry_username.insert(0, username)
        if username == "admin":
            self.entry_username.config(state="disabled", fg="gray")

        tk.Label(ff, text="ФИО:", bg="#0b2a1b", fg="#ffffff").grid(row=1, column=0, padx=10, pady=5, sticky="e")
        self.entry_name = tk.Entry(ff, width=28);
        self.entry_name.grid(row=1, column=1, padx=10, pady=5);
        self.entry_name.insert(0, ui.get("full_name", ""))

        tk.Label(ff, text="Роль:", bg="#0b2a1b", fg="#ffffff").grid(row=2, column=0, padx=10, pady=5, sticky="e")
        self.combo_role = ttk.Combobox(ff, values=["viewer", "editor", "admin"],
                                       state="readonly" if username != "admin" else "disabled", width=28)
        self.combo_role.grid(row=2, column=1, padx=10, pady=5);
        self.combo_role.set(ui.get("role", "viewer"))

        self.var_force = tk.BooleanVar(value=ui.get("force_password_change", False))
        tk.Checkbutton(ff, text="Требовать смену пароля", variable=self.var_force, bg="#0b2a1b", fg="#d4af37",
                       selectcolor="#0b2a1b").grid(row=3, column=0, columnspan=2, padx=10, pady=10, sticky="w")

        bf = tk.Frame(self.dialog, bg="#0b2a1b");
        bf.pack(pady=15)
        tk.Button(bf, text="Сохранить", command=self.save, bg="#d4af37", width=12).pack(side="left", padx=10)
        tk.Button(bf, text="Отмена", command=self.dialog.destroy, bg="#666666", fg="white", width=12).pack(side="left",
                                                                                                           padx=10)
        self.parent.wait_window(self.dialog)

    def save(self):
        new_username = self.entry_username.get().strip()
        new_name = self.entry_name.get().strip()
        new_role = self.combo_role.get()
        force_change = self.var_force.get()

        # Если логин изменился — меняем его
        if new_username and new_username != self.username and new_username != "admin":
            ok, msg = self.user_manager.change_username(self.username, new_username,
                                                        changed_by=self.user_manager.current_user)
            if not ok: return messagebox.showerror("Ошибка", msg)
            # После смены логина обновляем self.username для дальнейших операций
            self.username = new_username

        # Обновляем остальные поля
        ok, msg = self.user_manager.update_user(self.username, new_role=new_role, new_full_name=new_name,
                                                force_password_change=force_change)
        if ok:
            self.result = True;
            messagebox.showinfo("Успех", msg);
            self.dialog.destroy()
        else:
            messagebox.showerror("Ошибка", msg)


class UserManagementDialog:
    def __init__(self, parent, user_manager, current_user, log_callback=None):
        self.parent, self.user_manager, self.current_user, self.log = parent, user_manager, current_user, log_callback or (
            lambda x: None)
        self.dialog = tk.Toplevel(parent);
        self.dialog.title("Пользователи");
        self.dialog.geometry("750x520");
        self.dialog.configure(bg="#0b2a1b");
        self.dialog.transient(parent);
        self.dialog.grab_set()
        sf = tk.Frame(self.dialog, bg="#0b2a1b");
        sf.pack(fill="x", padx=10, pady=10)
        tk.Label(sf, text="🔍 Поиск:", bg="#0b2a1b", fg="#d4af37").pack(side="left")
        self.search_var = tk.StringVar();
        se = tk.Entry(sf, textvariable=self.search_var, width=30);
        se.pack(side="left", padx=5);
        se.bind("<KeyRelease>", self.filter_users)
        tk.Button(sf, text="Очистить", command=self.clear_search, bg="#666666", fg="white", width=8).pack(side="left",
                                                                                                          padx=5)
        tf = tk.Frame(self.dialog, bg="#0b2a1b");
        tf.pack(fill="both", expand=True, padx=10, pady=5)
        cols = ("username", "full_name", "role", "created_at", "last_login")
        self.tree = ttk.Treeview(tf, columns=cols, show="headings", selectmode="browse")
        heads = {"username": "Логин", "full_name": "ФИО", "role": "Роль", "created_at": "Создан", "last_login": "Вход"};
        widths = {"username": 130, "full_name": 200, "role": 110, "created_at": 140, "last_login": 140}
        for c in cols: self.tree.heading(c, text=heads[c]); self.tree.column(c, width=widths.get(c, 100), minwidth=80)
        vsb = ttk.Scrollbar(tf, orient="vertical", command=self.tree.yview);
        self.tree.configure(yscrollcommand=vsb.set);
        self.tree.pack(side="left", fill="both", expand=True);
        vsb.pack(side="right", fill="y")
        self.tree.bind("<<TreeviewSelect>>", self.on_select);
        self.tree.bind("<Double-1>", lambda e: self.edit_user())
        bf = tk.Frame(self.dialog, bg="#0b2a1b");
        bf.pack(fill="x", padx=10, pady=10)
        bc = {"bg": "#d4af37", "fg": "black", "width": 18, "font": ("Times New Roman", 9, "bold")}
        self.btn_pwd = tk.Button(bf, text="🔑 Пароль", command=self.change_password, **bc);
        self.btn_pwd.pack(side="left", padx=3)
        self.btn_edit = tk.Button(bf, text="✏️ Изменить", command=self.edit_user, **bc);
        self.btn_edit.pack(side="left", padx=3)
        self.btn_del = tk.Button(bf, text="🗑️ Удалить", command=self.delete_user, bg="#c0392b", fg="white",
                                 **{k: v for k, v in bc.items() if k != 'bg'});
        self.btn_del.pack(side="left", padx=3)
        tk.Button(bf, text="➕ Добавить", command=self.add_user, **bc).pack(side="left", padx=3)
        tk.Button(bf, text="❌ Закрыть", command=self.dialog.destroy, bg="#666666", fg="white", width=12).pack(
            side="right", padx=3)
        self.status_var = tk.StringVar();
        tk.Label(self.dialog, textvariable=self.status_var, bg="#0b2a1b", fg="#cccccc",
                 font=("Times New Roman", 9)).pack(pady=(0, 5))
        self.refresh_list();
        self.on_select();
        self.dialog.protocol("WM_DELETE_WINDOW", self.dialog.destroy);
        self.parent.wait_window(self.dialog)

    def refresh_list(self):
        for i in self.tree.get_children(): self.tree.delete(i)
        users = self.user_manager.get_users_list();
        q = self.search_var.get().lower()
        for u in users:
            if q and not any(q in str(u[k]).lower() for k in ["username", "full_name", "role"]): continue
            ll = u["last_login"];
            ll = ll[:16].replace("T", " ") if ll and ll != "None" and "T" in ll else "Никогда"
            ri = {"admin": "👑 Админ", "editor": "✏️ Редактор", "viewer": "👁️ Наблюдатель"}
            self.tree.insert("", "end", values=(u["username"], u["full_name"], ri.get(u["role"], u["role"]),
                                                u["created_at"][:10] if u["created_at"] else "", ll))
        self.status_var.set(f"Пользователей: {len(self.tree.get_children())}")

    def filter_users(self, event=None):
        self.refresh_list()

    def clear_search(self):
        self.search_var.set("");
        self.refresh_list()

    def on_select(self, event=None):
        sel = self.tree.selection();
        hs = bool(sel)
        if hs:
            v = self.tree.item(sel[0])["values"];
            u, r = v[0], v[2];
            is_self = u == self.current_user;
            is_admin = "Админ" in r
            # 🔧 ИСПРАВЛЕНО: разрешаем менять пароль себе (включая админа)
            self.btn_pwd.config(state="normal" if hs else "disabled")
            self.btn_edit.config(state="normal" if hs and not is_self else "disabled")
            self.btn_del.config(state="normal" if hs and not is_self and not is_admin else "disabled")
        else:
            for b in [self.btn_pwd, self.btn_edit, self.btn_del]: b.config(state="disabled")

    def add_user(self):
        d = AddUserDialog(self.dialog, self.user_manager)
        if d.result: self.refresh_list(); self.log(f"Добавлен: {d.result}")

    def edit_user(self):
        sel = self.tree.selection()
        if not sel: return
        u = self.tree.item(sel[0])["values"][0]
        d = EditUserDialog(self.dialog, self.user_manager, u)
        if d.result: self.refresh_list(); self.log(f"Изменён: {u}")

    def change_password(self):
        sel = self.tree.selection()
        if not sel: return
        u = self.tree.item(sel[0])["values"][0]
        # 🔧 ИСПРАВЛЕНО: разрешаем менять пароль себе
        d = ChangePasswordDialog(self.dialog, self.user_manager, u, is_admin_reset=(u != self.current_user))
        if d.result: self.log(f"Пароль изменён: {u}")

    def delete_user(self):
        sel = self.tree.selection()
        if not sel: return
        u = self.tree.item(sel[0])["values"][0]
        if messagebox.askyesno("Удалить", f"Удалить '{u}'?"):
            ok, msg = self.user_manager.delete_user(u)
            if ok:
                self.refresh_list();
                messagebox.showinfo("Успех", msg);
                self.log(f"Удалён: {u}")
            else:
                messagebox.showerror("Ошибка", msg)


class FilterDialog:
    def __init__(self, parent, columns, on_apply):
        self.parent, self.columns, self.on_apply = parent, columns, on_apply
        self.dialog = tk.Toplevel(parent);
        self.dialog.title("Фильтр");
        self.dialog.geometry("400x200");
        self.dialog.configure(bg="#0b2a1b");
        self.dialog.transient(parent);
        self.dialog.grab_set()
        tk.Label(self.dialog, text="Поле:", bg="#0b2a1b", fg="#d4af37").grid(row=0, column=0, padx=10, pady=5,
                                                                             sticky="e")
        self.field_var = tk.StringVar();
        self.field_combo = ttk.Combobox(self.dialog, textvariable=self.field_var, values=columns, state="readonly",
                                        width=20)
        self.field_combo.grid(row=0, column=1, padx=10, pady=5);
        self.field_combo.current(0)
        tk.Label(self.dialog, text="Значение:", bg="#0b2a1b", fg="#d4af37").grid(row=1, column=0, padx=10, pady=5,
                                                                                 sticky="e")
        self.value_entry = tk.Entry(self.dialog, width=20);
        self.value_entry.grid(row=1, column=1, padx=10, pady=5)
        bf = tk.Frame(self.dialog, bg="#0b2a1b");
        bf.grid(row=2, column=0, columnspan=2, pady=15)
        tk.Button(bf, text="Применить", command=self.apply, bg="#d4af37", width=10).pack(side="left", padx=5)
        tk.Button(bf, text="Отмена", command=self.dialog.destroy, bg="#d4af37", width=10).pack(side="left", padx=5)

    def apply(self):
        f, v = self.field_var.get(), self.value_entry.get().strip()
        if not f or not v: return messagebox.showwarning("Внимание", "Заполните поле и значение")
        self.on_apply(f, v);
        self.dialog.destroy()


class ColumnSelectorDialog:
    def __init__(self, parent, columns, on_confirm):
        self.parent, self.columns, self.on_confirm = parent, columns, on_confirm
        self.dialog = tk.Toplevel(parent);
        self.dialog.title("Колонки");
        self.dialog.geometry("300x400");
        self.dialog.configure(bg="#0b2a1b");
        self.dialog.transient(parent);
        self.dialog.grab_set()
        self.vars = {};
        f = tk.Frame(self.dialog, bg="#0b2a1b");
        f.pack(fill="both", expand=True, padx=10, pady=10)
        for c in columns: v = tk.BooleanVar(value=True); self.vars[c] = v; tk.Checkbutton(f, text=c, variable=v,
                                                                                          bg="#0b2a1b", fg="#ffffff",
                                                                                          selectcolor="#0b2a1b",
                                                                                          anchor="w").pack(fill="x")
        bf = tk.Frame(self.dialog, bg="#0b2a1b");
        bf.pack(pady=10)
        tk.Button(bf, text="OK", command=self.confirm, bg="#d4af37", width=10).pack(side="left", padx=5)
        tk.Button(bf, text="Отмена", command=self.dialog.destroy, bg="#d4af37", width=10).pack(side="left", padx=5)

    def confirm(self): self.on_confirm([c for c, v in self.vars.items() if v.get()]); self.dialog.destroy()


class RecordDialog:
    def __init__(self, parent, title, columns, initial_values=None, on_save=None):
        self.parent, self.columns, self.on_save = parent, columns, on_save
        self.initial_values = {}
        if initial_values:
            for k, v in initial_values.items():
                if k != '_original_index': self.initial_values[k] = '' if pd.isna(v) else str(v)
        self.entries, self.comboboxes = {}, {}
        self.dialog = tk.Toplevel(parent);
        self.dialog.title(title);
        self.dialog.geometry("550x450");
        self.dialog.configure(bg="#0b2a1b");
        self.dialog.transient(parent);
        self.dialog.grab_set()
        canvas = tk.Canvas(self.dialog, bg="#1a3d2a", highlightthickness=0);
        sb = tk.Scrollbar(self.dialog, orient="vertical", command=canvas.yview)
        sf = tk.Frame(canvas, bg="#1a3d2a");
        sf.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=sf, anchor="nw");
        canvas.configure(yscrollcommand=sb.set)
        canvas.pack(side="left", fill="both", expand=True, padx=10, pady=10);
        sb.pack(side="right", fill="y")
        for col in columns:
            if col == '_original_index': continue
            f = tk.Frame(sf, bg="#1a3d2a");
            f.pack(fill="x", pady=2)
            tk.Label(f, text=col, bg="#1a3d2a", fg="#d4af37", font=("Times New Roman", 10, "bold"), width=25,
                     anchor="w").pack(side="left")
            if col == "Искомая степень":
                dv = tk.StringVar();
                cb = ttk.Combobox(f, textvariable=dv, values=DEGREE_OPTIONS, state="readonly", width=37,
                                  font=("Times New Roman", 10))
                cb.pack(side="left", padx=5, fill="x", expand=True);
                self.comboboxes[col] = cb
                if col in self.initial_values and self.initial_values[col]: cb.set(self.initial_values[col])
            else:
                e = tk.Entry(f, width=37, font=("Times New Roman", 10));
                e.pack(side="left", padx=5, fill="x", expand=True);
                self.entries[col] = e
                if col in self.initial_values and self.initial_values[col]: e.insert(0, self.initial_values[col])
        bf = tk.Frame(self.dialog, bg="#0b2a1b");
        bf.pack(fill="x", pady=10)
        tk.Button(bf, text="Сохранить", command=self.save, bg="#d4af37", fg="black",
                  font=("Times New Roman", 10, "bold"), width=15).pack(side="left", padx=10)
        tk.Button(bf, text="Отмена", command=self.dialog.destroy, bg="#d4af37", fg="black",
                  font=("Times New Roman", 10, "bold"), width=15).pack(side="right", padx=10)
        self.dialog.update_idletasks();
        w, h = self.dialog.winfo_width(), self.dialog.winfo_height()
        self.dialog.geometry(
            f'{w}x{h}+{(self.dialog.winfo_screenwidth() // 2) - (w // 2)}+{(self.dialog.winfo_screenheight() // 2) - (h // 2)}')

    def save(self):
        nr = {}
        for col in self.columns:
            if col == '_original_index': continue
            if col == "Искомая степень" and col in self.comboboxes:
                v = self.comboboxes[col].get().strip()
            elif col in self.entries:
                v = self.entries[col].get().strip()
            else:
                v = ""
            if col == "Дата защиты диссертации" and v and not re.match(r"\d{2}\.\d{2}\.\d{4}",
                                                                       v): return messagebox.showerror("Ошибка",
                                                                                                       "Дата: ДД.ММ.ГГГГ")
            nr[col] = v if v != "" else None
        if self.on_save: self.on_save(nr)
        self.dialog.destroy()
