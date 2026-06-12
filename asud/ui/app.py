"""Main Tkinter application window."""

import json
import logging
import os
import queue
import re
import threading
import tkinter as tk
from datetime import datetime
from functools import partial
from tkinter import filedialog, messagebox, ttk

import pandas as pd

from asud.auth import UserManager
from asud.config import CONFIG_FILE, DEFAULT_CONFIG
from asud.data_model import DataModel
from asud.reports import ReportGenerator
from asud.storage import SQLiteStorage
from asud.ui.theme import APP_THEME, FONT, ROLE_LABELS, SPACING, WINDOW_MINSIZE, configure_ttk_style
from asud.ui.dialogs import (
    ColumnSelectorDialog,
    FilterDialog,
    InitialAdminDialog,
    LoginDialog,
    RecordDialog,
    UserManagementDialog,
)

try:
    from PIL import Image, ImageTk

    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False


class DissertationReportApp:
    def __init__(self, root):
        self.root = root;
        self.root.title("Автоматизированная система учёта диссертаций | ВМедА им. С.М. Кирова");
        self.root.geometry("1360x820");
        self.root.minsize(*WINDOW_MINSIZE)
        self.root.configure(bg=APP_THEME["app_background"])
        self.config = self.load_config();
        self.setup_logging()
        self.storage = SQLiteStorage(self.config["db_path"])
        self.storage.migrate_from_files(
            users_file=self.config["users_file"],
            persistence_file=self.config["persistence_file"],
            backup_dir=self.config["backup_dir"],
        )
        self.user_manager = UserManager(self.config, storage=self.storage);
        self.data_model = DataModel(self.config);
        self.report_gen = ReportGenerator(self.config)
        self.current_user = None;
        self.current_role = None;
        self.current_filepath = None
        self.status_var = tk.StringVar();
        self.status_var.set("Готово. Данные будут сохранены в локальную базу SQLite.")
        self.task_queue = queue.Queue();
        self.root.after(100, self.process_queue);
        self.ui_built = False;
        self.root.after(100, self.show_login)

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            config = DEFAULT_CONFIG.copy()
            config.update(loaded)
            if config != loaded:
                self.save_config(config)
        else:
            config = DEFAULT_CONFIG.copy();
            self.save_config(config)
        os.makedirs(config["backup_dir"], exist_ok=True);
        return config

    def save_config(self, config=None):
        if config is None: config = self.config
        with open(CONFIG_FILE, "w", encoding="utf-8") as f: json.dump(config, f, indent=2, ensure_ascii=False)

    def setup_logging(self):
        import sys
        if sys.version_info >= (3, 9):
            logging.basicConfig(filename=self.config["audit_log"], level=logging.INFO,
                                format='%(asctime)s - %(levelname)s - %(message)s', encoding='utf-8')
        else:
            lh = logging.FileHandler(self.config["audit_log"], mode='a', encoding='utf-8');
            lh.setLevel(logging.INFO)
            lh.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
            rl = logging.getLogger();
            rl.setLevel(logging.INFO);
            rl.addHandler(lh)

    def log_action(self, action):
        logging.info(f"Пользователь {self.current_user} ({self.current_role}): {action}")
        if hasattr(self, "storage"):
            self.storage.append_audit(self.current_user, self.current_role, action)

    def backup_data(self):
        if not self.data_model.data.empty:
            bp = os.path.join(self.config["backup_dir"], f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
            self.data_model.data.to_csv(bp, index=False, encoding='utf-8');
            self.log_action(f"Бэкап: {bp}")

    def save_persisted_data(self):
        if not self.data_model.data.empty:
            if hasattr(self, "storage"):
                self.storage.save_records(self.data_model.data)
            else:
                self.data_model.data.to_csv(self.config["persistence_file"], index=False, encoding='utf-8')

    def load_persisted_data(self):
        if hasattr(self, "storage"):
            df = self.storage.load_records()
            if not df.empty:
                if "Год защиты" in df.columns: df["Год защиты"] = pd.to_numeric(df["Год защиты"],
                                                                                errors="coerce").astype("Int64")
                df = self.data_model._add_missing_columns(df)
                self.data_model.data = df.copy();
                self.data_model.filtered_data = self.data_model.data.copy()
                self.data_model.apply_filters();
                self.display_data();
                self.log_action("Данные загружены")
                return
        if os.path.exists(self.config["persistence_file"]):
            try:
                df = pd.read_csv(self.config["persistence_file"], encoding='utf-8')
                if "Год защиты" in df.columns: df["Год защиты"] = pd.to_numeric(df["Год защиты"],
                                                                                errors="coerce").astype("Int64")
                df = self.data_model._add_missing_columns(df)
                self.data_model.data = df.copy();
                self.data_model.filtered_data = self.data_model.data.copy()
                self.data_model.apply_filters();
                self.display_data();
                self.log_action("Данные загружены")
            except Exception as e:
                print(f"Ошибка загрузки: {e}")

    def show_login(self):
        if not self.user_manager.has_users():
            setup = InitialAdminDialog(self.root, self.user_manager)
            if not setup.result:
                self.root.destroy()
                return
        login = LoginDialog(self.root, self.user_manager)
        if login.result:
            self.current_user, self.current_role = login.result
            self.log_action("Вход")
            self.status_var.set(
                f"Пользователь: {self.current_user} | {ROLE_LABELS.get(self.current_role, self.current_role)}"
            )
            self.build_ui();
            self.load_persisted_data();
            self.update_permissions();
            self.ui_built = True
        else:
            self.root.destroy()

    def update_permissions(self):
        mutation_buttons = [self.btn_load, self.btn_add, self.btn_edit, self.btn_delete]
        if self.current_role == "admin":
            for button in mutation_buttons + [self.btn_users]:
                button.config(state="normal")
        elif self.current_role == "editor":
            for button in mutation_buttons:
                button.config(state="normal")
            self.btn_users.config(state="disabled")
        else:
            for button in mutation_buttons + [self.btn_users]:
                button.config(state="disabled")

    def build_ui(self):
        self.root.configure(bg=APP_THEME["app_background"])
        configure_ttk_style(self.root, self.config["theme"])
        self.logo_image = None
        self.build_topbar()
        self.build_statusbar()
        self.content_frame = tk.Frame(self.root, bg=APP_THEME["app_background"])
        self.content_frame.pack(fill="both", expand=True)
        self.build_sidebar(self.content_frame)
        self.build_workbench(self.content_frame)
        self.bind_shortcuts()

    def ui_font(self, size_key="size", weight=None):
        font = (FONT["family"], FONT[size_key])
        if weight:
            font += (weight,)
        return font

    def build_topbar(self):
        self.topbar_frame = tk.Frame(self.root, bg=APP_THEME["topbar"], height=64)
        self.topbar_frame.pack(fill="x")
        self.topbar_frame.pack_propagate(False)
        self.topbar_frame.columnconfigure(1, weight=1)

        brand = tk.Frame(self.topbar_frame, bg=APP_THEME["topbar"])
        brand.grid(row=0, column=0, padx=(SPACING["lg"], SPACING["md"]), sticky="w")

        if PIL_AVAILABLE and os.path.exists(self.config["logo_path"]):
            try:
                pi = Image.open(self.config["logo_path"]);
                pi = pi.resize((38, 38), Image.Resampling.LANCZOS);
                self.logo_image = ImageTk.PhotoImage(pi)
            except Exception as e:
                print(f"Лого: {e}")

        if self.logo_image:
            tk.Label(brand, image=self.logo_image, bg=APP_THEME["topbar"]).pack(side="left", padx=(0, SPACING["sm"]))
        else:
            tk.Label(
                brand,
                text="АС",
                bg=APP_THEME["primary_alt"],
                fg=APP_THEME["topbar_text"],
                font=self.ui_font("size", "bold"),
                width=4,
                height=2,
            ).pack(side="left", padx=(0, SPACING["sm"]))

        brand_text = tk.Frame(brand, bg=APP_THEME["topbar"])
        brand_text.pack(side="left")
        tk.Label(
            brand_text,
            text="АСУД",
            bg=APP_THEME["topbar"],
            fg=APP_THEME["topbar_text"],
            font=self.ui_font("size", "bold"),
            anchor="w",
        ).pack(anchor="w")
        tk.Label(
            brand_text,
            text="Военно-медицинская академия им. С.М. Кирова",
            bg=APP_THEME["topbar"],
            fg=APP_THEME["topbar_muted"],
            font=self.ui_font("small"),
            anchor="w",
        ).pack(anchor="w")

        context = tk.Frame(self.topbar_frame, bg=APP_THEME["topbar"])
        context.grid(row=0, column=1, sticky="ew")
        tk.Label(
            context,
            text="Реестр диссертаций",
            bg=APP_THEME["topbar"],
            fg=APP_THEME["topbar_text"],
            font=self.ui_font("title", "bold"),
        ).pack(side="left")
        tk.Label(
            context,
            text="База данных активна",
            bg=APP_THEME["topbar"],
            fg=APP_THEME["topbar_muted"],
            font=self.ui_font("small"),
            padx=SPACING["md"],
        ).pack(side="left")

        account = tk.Frame(self.topbar_frame, bg=APP_THEME["topbar"])
        account.grid(row=0, column=2, padx=(SPACING["md"], SPACING["lg"]), sticky="e")
        tk.Label(
            account,
            text=self.current_user or "",
            bg=APP_THEME["topbar"],
            fg=APP_THEME["topbar_text"],
            font=self.ui_font("size", "bold"),
            anchor="e",
        ).pack(anchor="e")
        tk.Label(
            account,
            text=ROLE_LABELS.get(self.current_role, self.current_role or ""),
            bg=APP_THEME["topbar"],
            fg=APP_THEME["topbar_muted"],
            font=self.ui_font("small"),
            anchor="e",
        ).pack(anchor="e")

    def build_sidebar(self, parent):
        self.control_frame = tk.Frame(parent, bg=APP_THEME["sidebar"], width=276)
        self.control_frame.pack(side="left", fill="y")
        self.control_frame.pack_propagate(False)

        self.add_nav_group("Данные")
        self.btn_load = self.create_nav_button("Загрузить Excel", self.load_excel_async, active=True)
        self.btn_add = self.create_nav_button("Новая запись", self.add_record)
        self.btn_edit = self.create_nav_button("Редактировать", self.edit_selected)
        self.btn_delete = self.create_nav_button("Удалить", self.delete_selected, variant="danger")

        self.add_nav_group("Отбор")
        self.create_nav_button("Расширенный фильтр", self.open_filter_dialog)
        self.create_nav_button("Сбросить отбор", self.clear_filters)

        self.add_nav_group("Выгрузка")
        self.btn_export_excel = self.create_nav_button("Excel", self.export_excel)
        self.btn_export_word = self.create_nav_button("Word", self.export_word)
        if MATPLOTLIB_AVAILABLE:
            self.btn_stats = self.create_nav_button("Статистика", self.show_statistics)

        self.add_nav_group("Администрирование")
        self.btn_users = self.create_nav_button("Пользователи", self.manage_users)
        self.create_nav_button("Сменить пользователя", self.switch_user)
        self.create_nav_button("Выход", self.on_closing, variant="neutral")

    def add_nav_group(self, text):
        top_pad = SPACING["panel"] if self.control_frame.winfo_children() else SPACING["md"]
        tk.Label(
            self.control_frame,
            text=text.upper(),
            bg=APP_THEME["sidebar"],
            fg=APP_THEME["muted_text"],
            font=self.ui_font("caption", "bold"),
            anchor="w",
        ).pack(fill="x", padx=SPACING["panel"], pady=(top_pad, SPACING["xs"]))

    def create_nav_button(self, text, command, variant="default", active=False):
        palette = {
            "default": (APP_THEME["surface"], APP_THEME["text"], APP_THEME["line"]),
            "danger": (APP_THEME["danger"], APP_THEME["topbar_text"], APP_THEME["danger"]),
            "neutral": (APP_THEME["surface_soft"], APP_THEME["muted_text"], APP_THEME["line"]),
        }
        bg, fg, border = palette[variant]
        if active:
            bg, fg, border = APP_THEME["primary"], APP_THEME["topbar_text"], APP_THEME["primary"]
        button = tk.Button(
            self.control_frame,
            text=text,
            command=command,
            bg=bg,
            fg=fg,
            activebackground=APP_THEME["primary_alt"],
            activeforeground=APP_THEME["topbar_text"],
            disabledforeground="#a7b0bd",
            font=self.ui_font("size", "bold"),
            anchor="w",
            relief="flat",
            bd=1,
            highlightbackground=border,
            highlightcolor=border,
            padx=SPACING["md"],
            pady=SPACING["sm"],
        )
        button.pack(fill="x", padx=SPACING["panel"], pady=3)
        return button

    def build_workbench(self, parent):
        self.main_frame = tk.Frame(parent, bg=APP_THEME["app_background"])
        self.main_frame.pack(side="left", fill="both", expand=True, padx=SPACING["lg"], pady=SPACING["panel"])
        self.main_frame.rowconfigure(2, weight=1)
        self.main_frame.columnconfigure(0, weight=1)

        self.toolbar_frame = tk.Frame(self.main_frame, bg=APP_THEME["app_background"])
        self.toolbar_frame.grid(row=0, column=0, sticky="ew")
        self.toolbar_frame.columnconfigure(0, weight=1)

        search_box = tk.Frame(
            self.toolbar_frame,
            bg=APP_THEME["surface"],
            highlightbackground=APP_THEME["line"],
            highlightthickness=1,
        )
        search_box.grid(row=0, column=0, sticky="ew", padx=(0, SPACING["md"]))
        search_box.columnconfigure(0, weight=1)
        self.search_entry = tk.Entry(
            search_box,
            borderwidth=0,
            relief="flat",
            bg=APP_THEME["surface"],
            fg=APP_THEME["text"],
            insertbackground=APP_THEME["text"],
            font=(FONT["family"], FONT["size"]),
        )
        self.search_entry.grid(row=0, column=0, sticky="ew", padx=SPACING["md"], pady=SPACING["sm"])
        self.search_entry.bind("<KeyRelease>", lambda e: self.smart_search())
        tk.Button(
            search_box,
            text="Найти",
            command=self.simple_search,
            bg=APP_THEME["primary_alt"],
            fg=APP_THEME["topbar_text"],
            activebackground=APP_THEME["primary"],
            activeforeground=APP_THEME["topbar_text"],
            font=self.ui_font("size", "bold"),
            relief="flat",
            padx=SPACING["md"],
            pady=SPACING["sm"],
        ).grid(row=0, column=1, sticky="e")

        year_box = tk.Frame(
            self.toolbar_frame,
            bg=APP_THEME["surface"],
            highlightbackground=APP_THEME["line"],
            highlightthickness=1,
        )
        year_box.grid(row=0, column=1, sticky="e")
        tk.Label(
            year_box,
            text="Год",
            bg=APP_THEME["surface"],
            fg=APP_THEME["muted_text"],
            font=self.ui_font("small", "bold"),
        ).pack(side="left", padx=(SPACING["md"], SPACING["xs"]))
        self.year_entry = tk.Entry(
            year_box,
            width=18,
            borderwidth=0,
            relief="flat",
            bg=APP_THEME["surface"],
            fg=APP_THEME["muted_text"],
            insertbackground=APP_THEME["text"],
            font=(FONT["family"], FONT["small"]),
        )
        self.year_entry.pack(side="left", padx=SPACING["xs"], pady=SPACING["sm"])
        self.year_entry.bind("<KeyRelease>", lambda e: self.apply_year_filter())
        self.year_entry.insert(0, "2023 или 2020-2024")
        self.year_entry.bind("<FocusIn>", lambda e: self._on_year_focus_in())
        self.year_entry.bind("<FocusOut>", lambda e: self._on_year_focus_out())
        tk.Button(
            year_box,
            text="Сброс",
            command=self.clear_year_filter,
            bg=APP_THEME["surface_soft"],
            fg=APP_THEME["muted_text"],
            activebackground=APP_THEME["line"],
            font=self.ui_font("small", "bold"),
            relief="flat",
            padx=SPACING["sm"],
        ).pack(side="left", padx=(SPACING["xs"], SPACING["sm"]))

        self.filter_summary_var = tk.StringVar(value="Найдено: 0")
        tk.Label(
            self.main_frame,
            textvariable=self.filter_summary_var,
            bg=APP_THEME["app_background"],
            fg=APP_THEME["muted_text"],
            font=self.ui_font("small"),
            anchor="w",
        ).grid(row=1, column=0, sticky="ew", pady=(SPACING["sm"], SPACING["sm"]))

        self.table_frame = tk.Frame(
            self.main_frame,
            bg=APP_THEME["surface"],
            highlightbackground=APP_THEME["line"],
            highlightthickness=1,
        )
        self.table_frame.grid(row=2, column=0, sticky="nsew")
        self.table_frame.rowconfigure(1, weight=1)
        self.table_frame.columnconfigure(0, weight=1)

        table_header = tk.Frame(self.table_frame, bg=APP_THEME["surface_soft"])
        table_header.grid(row=0, column=0, columnspan=2, sticky="ew")
        table_header.columnconfigure(0, weight=1)
        tk.Label(
            table_header,
            text="Список записей",
            bg=APP_THEME["surface_soft"],
            fg=APP_THEME["text"],
            font=self.ui_font("size", "bold"),
            anchor="w",
        ).grid(row=0, column=0, sticky="w", padx=SPACING["md"], pady=SPACING["sm"])
        tk.Label(
            table_header,
            text="Данные сохранены в SQLite",
            bg=APP_THEME["surface_soft"],
            fg=APP_THEME["muted_text"],
            font=self.ui_font("small"),
            anchor="e",
        ).grid(row=0, column=1, sticky="e", padx=SPACING["md"], pady=SPACING["sm"])

        tc = tk.Frame(self.table_frame, bg=APP_THEME["table_background"])
        tc.grid(row=1, column=0, sticky="nsew")
        self.tree = ttk.Treeview(tc, show="headings")
        vsb = ttk.Scrollbar(tc, orient="vertical", command=self.tree.yview);
        self.tree.configure(yscrollcommand=vsb.set)
        hsb = ttk.Scrollbar(tc, orient="horizontal", command=self.tree.xview);
        self.tree.configure(xscrollcommand=hsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew");
        vsb.grid(row=0, column=1, sticky="ns");
        hsb.grid(row=1, column=0, sticky="ew")
        tc.rowconfigure(0, weight=1);
        tc.columnconfigure(0, weight=1)
        self.tree.bind("<Button-1>", self.on_tree_click)

    def build_statusbar(self):
        self.status_frame = tk.Frame(self.root, bg=APP_THEME["surface"], height=28)
        self.status_frame.pack(side=tk.BOTTOM, fill=tk.X)
        self.status_frame.pack_propagate(False)
        tk.Label(
            self.status_frame,
            textvariable=self.status_var,
            anchor=tk.W,
            bg=APP_THEME["surface"],
            fg=APP_THEME["muted_text"],
            font=self.ui_font("small"),
            padx=SPACING["panel"],
        ).pack(fill=tk.BOTH, expand=True)

    def bind_shortcuts(self):
        self.root.bind("<Control-o>", lambda e: self.load_excel_async());
        self.root.bind("<Control-f>", lambda e: self.search_entry.focus_set())
        self.root.bind("<Control-s>", lambda e: self.export_excel());
        self.root.bind("<Delete>", lambda e: self.delete_selected());
        self.root.bind("<Control-e>", lambda e: self.edit_selected())

    def _on_year_focus_in(self):
        if self.year_entry.get() == "2023 или 2020-2024": self.year_entry.delete(0, tk.END); self.year_entry.config(
            fg=APP_THEME["text"])

    def _on_year_focus_out(self):
        if not self.year_entry.get().strip(): self.year_entry.insert(0, "2023 или 2020-2024"); self.year_entry.config(
            fg=APP_THEME["muted_text"])

    def clear_ui(self):
        frame_names = [
            "topbar_frame",
            "content_frame",
            "control_frame",
            "main_frame",
            "toolbar_frame",
            "table_frame",
            "status_frame",
        ]
        for a in frame_names:
            if hasattr(self, a):
                w = getattr(self, a)
                if w and hasattr(w, 'winfo_exists') and w.winfo_exists(): w.destroy()
                setattr(self, a, None)
        self.tree = None

    def on_tree_click(self, event):
        r = self.tree.identify_region(event.x, event.y)
        if r == "heading":
            c = self.tree.identify_column(event.x);
            ci = int(c.replace("#", "")) - 1;
            cn = self.tree["columns"][ci]
            if self.data_model.sort_column == cn:
                self.data_model.sort_reverse = not self.data_model.sort_reverse
            else:
                self.data_model.sort_column = cn;
                self.data_model.sort_reverse = False
            self.data_model.sort_data();
            self.display_data()

    def smart_search(self):
        q = self.search_entry.get().strip();
        self.data_model.set_smart_search(q);
        self.display_data()
        self.status_var.set(f"Найдено: {len(self.data_model.filtered_data)}")

    def simple_search(self):
        q = self.search_entry.get().strip()
        if not q:
            self.data_model.clear_filters()
        else:
            self.data_model.clear_filters()
            m = self.data_model.data.apply(lambda r: any(q.lower() in str(c).lower() for c in r), axis=1)
            self.data_model.filtered_data = self.data_model.data[m].copy()
            self.data_model.filtered_data['_original_index'] = self.data_model.filtered_data.index
            self.data_model.sort_data()
        self.display_data();
        self.status_var.set(f"Найдено: {len(self.data_model.filtered_data)}")

    def open_filter_dialog(self):
        if self.data_model.data.empty: return messagebox.showwarning("Нет данных", "Сначала загрузите данные.")
        FilterDialog(self.root, self.data_model.get_columns(), self.add_filter)

    def add_filter(self, field, value):
        self.data_model.add_filter(field, value);
        self.display_data()
        self.status_var.set(f"Фильтр: {len(self.data_model.filtered_data)} записей")

    def clear_filters(self):
        self.data_model.clear_filters();
        self.search_entry.delete(0, tk.END);
        self.year_entry.delete(0, tk.END);
        self._on_year_focus_out()
        self.display_data();
        self.status_var.set("Фильтры сброшены")

    def apply_year_filter(self):
        year = self.year_entry.get().strip()
        if year == "2023 или 2020-2024": year = ""
        if not year:
            self.data_model.filters = [(f, v) for f, v in self.data_model.filters if f != "Год защиты"]
            self.data_model.apply_filters();
            self.display_data()
            self.status_var.set("Фильтр по году снят");
            return
        if not re.fullmatch(r'\d{4}([\-:\.]\d{4})?', year): return
        start_year, end_year = self.data_model._parse_year_range(year)
        if start_year is not None and end_year is not None:
            self.data_model.filters = [(f, v) for f, v in self.data_model.filters if f != "Год защиты"]
            self.data_model.add_filter("Год защиты", year)
            self.display_data()
            txt = f"Год: {start_year}" if start_year == end_year else f"Годы: {start_year}-{end_year}"
            self.status_var.set(f"{txt}, записей: {len(self.data_model.filtered_data)}")

    def clear_year_filter(self):
        self.year_entry.delete(0, tk.END);
        self._on_year_focus_out()
        self.data_model.filters = [(f, v) for f, v in self.data_model.filters if f != "Год защиты"]
        self.data_model.apply_filters();
        self.display_data()
        self.status_var.set("Фильтр по году снят")

    def load_excel_async(self):
        if self.current_role not in ("admin", "editor"): return messagebox.showerror("Доступ запрещён",
                                                                                     "Недостаточно прав.")
        fp = filedialog.askopenfilename(title="Выберите Excel", filetypes=[("Excel", "*.xlsx *.xls")])
        if not fp: return
        self.current_filepath = fp;
        self.status_var.set("Загрузка...");
        self.root.config(cursor="watch");
        self.btn_load.config(state="disabled")

        def worker():
            try:
                self.data_model.load_excel(fp);
                self.root.after(0, self.load_complete, True, None, fp)
            except Exception as e:
                self.root.after(0, self.load_complete, False, str(e), fp)

        threading.Thread(target=worker, daemon=True).start()

    def load_complete(self, success, error, filepath):
        self.status_var.set("Готов");
        self.root.config(cursor="");
        self.btn_load.config(state="normal")
        if success:
            self.display_data();
            self.save_persisted_data();
            self.backup_data()
            self.log_action(f"Загружен: {filepath}");
            messagebox.showinfo("Успех", "Данные загружены!")
            self.year_entry.delete(0, tk.END);
            self._on_year_focus_out()
        else:
            messagebox.showerror("Ошибка", f"Не удалось загрузить:\n{error}");
            self.log_action(f"Ошибка: {error}")

    def display_empty_state(self, message):
        if not hasattr(self, 'tree') or self.tree is None:
            return
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.tree["columns"] = ("message",)
        self.tree.heading("message", text="")
        self.tree.column("message", width=600, minwidth=300, stretch=True, anchor="center")
        self.tree.insert("", "end", values=(message,))
        self.tree.update_idletasks()

    def display_data(self):
        if not hasattr(self, 'tree') or self.tree is None: return
        for i in self.tree.get_children(): self.tree.delete(i)
        df = self.data_model.get_filtered_data()
        if df.empty:
            message = "Данные не загружены" if self.data_model.data.empty else "По фильтру ничего не найдено"
            self.display_empty_state(message)
            return
        dc = [c for c in df.columns if c != '_original_index'];
        self.tree["columns"] = dc
        dw = self.config.get("default_columns_width", 120)
        cw = {"ФИО": 180, "Название диссертации": 250, "Диссертационный совет": 200, "Примечания": 200,
              "Информация о лишении степени": 220}
        for c in dc: self.tree.heading(c, text=c, command=partial(self.set_sort, c)); self.tree.column(c,
                                                                                                       width=cw.get(c,
                                                                                                                    dw),
                                                                                                       minwidth=80,
                                                                                                       stretch=False,
                                                                                                       anchor="w")
        for idx, row in df.iterrows():
            oi = row.get('_original_index', idx);
            self.tree.insert("", "end", iid=str(oi), values=[row[c] for c in dc])
        self.tree.update_idletasks()

    def set_sort(self, col):
        if self.data_model.sort_column == col:
            self.data_model.sort_reverse = not self.data_model.sort_reverse
        else:
            self.data_model.sort_column = col;
            self.data_model.sort_reverse = False
        self.data_model.sort_data();
        self.display_data()

    def add_record(self):
        if self.current_role not in ("admin", "editor"): return messagebox.showerror("Доступ запрещён")
        if self.data_model.data.empty: return messagebox.showwarning("Нет данных", "Загрузите файл.")

        def on_save(nr):
            self.data_model.add_record(nr);
            self.display_data();
            self.save_persisted_data();
            self.log_action(
                f"Добавлено: {nr}");
            messagebox.showinfo("Успех", "Запись добавлена")

        RecordDialog(self.root, "Добавить", self.data_model.get_columns(), on_save=on_save)

    def edit_selected(self):
        if self.current_role not in ("admin", "editor"): return messagebox.showerror("Доступ запрещён")
        sel = self.tree.selection()
        if not sel: return messagebox.showwarning("Редактирование", "Выберите запись.")
        oi = int(sel[0]);
        rd = self.data_model.get_row_by_original_index(oi)
        if rd is None: return messagebox.showerror("Ошибка", "Запись не найдена.")

        def on_save(nr):
            self.data_model.update_record(oi, nr);
            self.display_data();
            self.save_persisted_data();
            self.log_action(
                f"Отредактировано: {oi}");
            messagebox.showinfo("Успех", "Запись обновлена")

        RecordDialog(self.root, "Редактировать", self.data_model.get_columns(), initial_values=rd, on_save=on_save)

    def delete_selected(self):
        if self.current_role not in ("admin", "editor"): return messagebox.showerror("Доступ запрещён")
        sel = self.tree.selection()
        if not sel: return messagebox.showwarning("Удаление", "Выберите запись.")
        oi = int(sel[0])
        if messagebox.askyesno("Подтверждение", "Удалить запись?"):
            try:
                self.data_model.delete_record(oi);
                self.display_data();
                self.save_persisted_data();
                self.log_action(
                    f"Удалено: {oi}");
                messagebox.showinfo("Успех", "Запись удалена")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Ошибка удаления: {e}")

    def run_export_task(self, task, success_message, audit_action):
        self.status_var.set("Экспорт...");
        self.root.config(cursor="watch")

        def worker():
            try:
                task()
                self.root.after(0, self.export_complete, True, None, success_message, audit_action)
            except Exception as exc:
                self.root.after(0, self.export_complete, False, str(exc), success_message, audit_action)

        threading.Thread(target=worker, daemon=True).start()

    def export_complete(self, success, error, success_message, audit_action):
        self.status_var.set("Готов")
        self.root.config(cursor="")
        if success:
            messagebox.showinfo("Успех", success_message)
            self.log_action(audit_action)
        else:
            messagebox.showerror("Ошибка", f"Ошибка сохранения: {error}")

    def export_excel(self):
        if self.data_model.filtered_data.empty: return messagebox.showwarning("Нет данных")
        ed = self.data_model.filtered_data.drop(columns=['_original_index'], errors='ignore')

        def on_cols(sel):
            fp = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel", "*.xlsx")])
            if fp:
                self.run_export_task(
                    lambda: self.report_gen.export_to_excel(ed, fp, sel),
                    f"Сохранено: {fp}",
                    f"Экспорт Excel: {fp}",
                )

        ColumnSelectorDialog(self.root, ed.columns.tolist(), on_cols)

    def export_word(self):
        if self.data_model.filtered_data.empty: return messagebox.showwarning("Нет данных")
        ed = self.data_model.filtered_data.drop(columns=['_original_index'], errors='ignore')

        def on_cols(sel):
            fp = filedialog.asksaveasfilename(defaultextension=".docx", filetypes=[("Word", "*.docx")])
            if fp:
                qt = "поиск по полям: " + " ; ".join(
                    f"{f}='{v}'" for f, v in self.data_model.filters) if self.data_model.filters else (
                    f"поиск: «{self.data_model.smart_search_query}»" if self.data_model.smart_search_query else "все записи")
                self.run_export_task(
                    lambda: self.report_gen.export_to_word(ed, fp, qt, sel),
                    f"Сохранено: {fp}",
                    f"Экспорт Word: {fp}",
                )

        ColumnSelectorDialog(self.root, ed.columns.tolist(), on_cols)

    def show_statistics(self):
        if not MATPLOTLIB_AVAILABLE: return messagebox.showerror("Ошибка", "Требуется matplotlib")
        if self.data_model.data.empty: return messagebox.showwarning("Нет данных")
        df = self.data_model.data.copy()
        if "Год защиты" not in df.columns or df["Год защиты"].isnull().all(): return messagebox.showwarning(
            "Нет данных о годах")
        yc = df["Год защиты"].value_counts().sort_index()
        fig, ax = plt.subplots(figsize=(8, 5));
        ax.bar(yc.index.astype(str), yc.values)
        ax.set_xlabel("Год");
        ax.set_ylabel("Количество");
        ax.set_title("Распределение защит по годам");
        ax.tick_params(axis='x', rotation=45)

        sw = tk.Toplevel(self.root);
        sw.title("Статистика");
        sw.geometry("800x600")

        # 🔧 ИСПРАВЛЕНО: Разделили создание канваса и его упаковку
        canvas = FigureCanvasTkAgg(fig, master=sw)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def manage_users(self):
        if self.current_role != "admin": return messagebox.showerror("Доступ запрещён")
        UserManagementDialog(self.root, self.user_manager, self.current_user, log_callback=self.log_action)

    def switch_user(self):
        self.save_persisted_data()
        if self.ui_built: self.clear_ui(); self.ui_built = False
        self.current_user = None;
        self.current_role = None;
        self.status_var.set("Готов");
        self.root.after(100, self.show_login)

    def on_closing(self):
        self.save_persisted_data();
        self.log_action("Завершение");
        if hasattr(self, "storage"):
            self.storage.close()
        logging.shutdown()
        self.root.destroy()

    def process_queue(self):
        try:
            while True: self.task_queue.get_nowait()()
        except queue.Empty:
            pass
        self.root.after(100, self.process_queue)
