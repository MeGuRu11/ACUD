"""Main Tkinter application window."""

import json
import logging
import os
import queue
import re
import sys
import threading
import tkinter as tk
from datetime import datetime
from functools import partial
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import pandas as pd

from asud.auth import UserManager
from asud.config import APP_ICON_PNG, CONFIG_FILE, DEFAULT_CONFIG
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
    from matplotlib.ticker import MaxNLocator

    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False


TABLE_COLUMN_WIDTHS = {
    "Год защиты": 96,
    "ФИО": 230,
    "Название диссертации": 360,
    "Диссертационный совет": 210,
    "Дата защиты диссертации": 175,
    "Специальность": 190,
    "Искомая степень": 200,
    "Информация о лишении степени": 280,
    "Примечания": 250,
    "1 Научный руководитель (консультант)": 280,
    "2 Научный руководитель (консультант)": 280,
}


class DissertationReportApp:
    def __init__(self, root):
        self.root = root;
        self.root.title("Автоматизированная система учёта диссертаций | ВМедА им. С.М. Кирова");
        self.center_root_window(1360, 820);
        self.root.minsize(*WINDOW_MINSIZE)
        self.root.configure(bg=APP_THEME["app_background"])
        self.set_app_icon()
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
        self.queue_after_id = None
        self.login_after_id = None
        self.is_closing = False
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.schedule_process_queue()
        self.ui_built = False;
        self.schedule_login()

    def center_root_window(self, width, height):
        self.root.deiconify()
        self.root.update_idletasks()
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = max(0, (screen_width - width) // 2)
        y = max(0, (screen_height - height) // 2)
        self.root.geometry(f"{width}x{height}+{x}+{y}")

    def center_toplevel_window(self, window, width, height):
        window.deiconify()
        window.update_idletasks()
        screen_width = window.winfo_screenwidth()
        screen_height = window.winfo_screenheight()
        x = max(0, (screen_width - width) // 2)
        y = max(0, (screen_height - height) // 2)
        window.geometry(f"{width}x{height}+{x}+{y}")

    def maximize_main_window(self):
        self.root.deiconify()
        self.root.update_idletasks()
        try:
            self.root.state("zoomed")
        except tk.TclError:
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()
            self.root.geometry(f"{screen_width}x{screen_height}+0+0")

    def maximize_toplevel_window(self, window):
        window.deiconify()
        window.update_idletasks()
        try:
            window.state("zoomed")
        except tk.TclError:
            screen_width = window.winfo_screenwidth()
            screen_height = window.winfo_screenheight()
            window.geometry(f"{screen_width}x{screen_height}+0+0")

    def set_app_icon(self):
        self.app_icon_image = None
        icon_path = self.resolve_asset_path(APP_ICON_PNG)
        if not icon_path.exists():
            return
        try:
            self.app_icon_image = tk.PhotoImage(file=str(icon_path))
            self.root.iconphoto(True, self.app_icon_image)
        except tk.TclError as exc:
            print(f"Иконка приложения не загружена: {exc}")

    def resolve_asset_path(self, path):
        asset_path = Path(path)
        if asset_path.exists():
            return asset_path
        if hasattr(sys, "_MEIPASS"):
            bundled_path = Path(sys._MEIPASS) / path
            if bundled_path.exists():
                return bundled_path
        return Path(__file__).resolve().parents[2] / path

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
                df = self.data_model.clean_missing_values(df)
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
                df = self.data_model.clean_missing_values(df)
                df = self.data_model._add_missing_columns(df)
                self.data_model.data = df.copy();
                self.data_model.filtered_data = self.data_model.data.copy()
                self.data_model.apply_filters();
                self.display_data();
                self.log_action("Данные загружены")
            except Exception as e:
                print(f"Ошибка загрузки: {e}")

    def show_login(self):
        self.login_after_id = None
        if self.is_closing:
            return
        if not self.user_manager.has_users():
            setup = InitialAdminDialog(self.root, self.user_manager)
            if not setup.result:
                self.destroy_root_after_cancel()
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
            self.destroy_root_after_cancel()

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
        self.maximize_main_window()
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

        self.load_brand_icon()

        if self.logo_image:
            self.brand_icon_label = tk.Label(brand, image=self.logo_image, bg=APP_THEME["topbar"])
            self.brand_icon_label.pack(side="left", padx=(0, SPACING["sm"]))

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

    def load_brand_icon(self):
        logo_path = self.resolve_asset_path(self.config["logo_path"])
        app_icon_path = self.resolve_asset_path(APP_ICON_PNG)
        if PIL_AVAILABLE and logo_path.exists():
            try:
                pi = Image.open(logo_path);
                pi = pi.resize((38, 38), Image.Resampling.LANCZOS);
                self.logo_image = ImageTk.PhotoImage(pi)
                return
            except Exception as e:
                print(f"Лого: {e}")
        if not app_icon_path.exists():
            return
        try:
            if PIL_AVAILABLE:
                pi = Image.open(app_icon_path)
                pi = pi.resize((40, 40), Image.Resampling.LANCZOS)
                self.logo_image = ImageTk.PhotoImage(pi)
            else:
                source = tk.PhotoImage(file=str(app_icon_path))
                scale = max(1, min(source.width(), source.height()) // 40)
                self.logo_image = source.subsample(scale, scale)
        except tk.TclError as exc:
            print(f"Иконка бренда не загружена: {exc}")

    def build_sidebar(self, parent):
        self.control_frame = tk.Frame(parent, bg=APP_THEME["sidebar"], width=276)
        self.control_frame.pack(side="left", fill="y")
        self.control_frame.pack_propagate(False)

        self.add_nav_group("Данные")
        self.btn_load = self.create_nav_button("Загрузить Excel", self.load_excel_async, active=True)
        self.btn_add = self.create_nav_button("Новая запись", self.add_record)
        self.btn_open_record = self.create_nav_button("Открыть запись", self.open_selected_record_view)
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
            text="Данные сохранены в Базе Данных",
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
        self.tree.bind("<Double-1>", self.open_selected_record_view)
        self.tree.bind("<Return>", self.open_selected_record_view)

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
        self.status_var.set(f"Поиск применён. Найдено записей: {len(self.data_model.filtered_data)}")

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
        self.status_var.set(f"Поиск применён. Найдено записей: {len(self.data_model.filtered_data)}")

    def open_filter_dialog(self):
        if self.data_model.data.empty: return messagebox.showwarning("Нет данных", "Сначала загрузите данные.")
        FilterDialog(self.root, self.data_model.get_columns(), self.add_filter)

    def add_filter(self, field, value):
        self.data_model.add_filter(field, value);
        self.display_data()
        self.status_var.set(f"Отбор применён. Найдено записей: {len(self.data_model.filtered_data)}")

    def clear_filters(self):
        self.data_model.clear_filters();
        self.search_entry.delete(0, tk.END);
        self.year_entry.delete(0, tk.END);
        self._on_year_focus_out()
        self.display_data();
        self.status_var.set("Отбор сброшен")

    def apply_year_filter(self):
        year = self.year_entry.get().strip()
        if year == "2023 или 2020-2024": year = ""
        if not year:
            self.data_model.filters = [(f, v) for f, v in self.data_model.filters if f != "Год защиты"]
            self.data_model.apply_filters();
            self.display_data()
            self.status_var.set("Отбор по году снят");
            return
        if not re.fullmatch(r'\d{4}([\-:\.]\d{4})?', year): return
        start_year, end_year = self.data_model._parse_year_range(year)
        if start_year is not None and end_year is not None:
            self.data_model.filters = [(f, v) for f, v in self.data_model.filters if f != "Год защиты"]
            self.data_model.add_filter("Год защиты", year)
            self.display_data()
            txt = f"Год: {start_year}" if start_year == end_year else f"Годы: {start_year}-{end_year}"
            self.status_var.set(f"{txt}. Найдено записей: {len(self.data_model.filtered_data)}")

    def clear_year_filter(self):
        self.year_entry.delete(0, tk.END);
        self._on_year_focus_out()
        self.data_model.filters = [(f, v) for f, v in self.data_model.filters if f != "Год защиты"]
        self.data_model.apply_filters();
        self.display_data()
        self.status_var.set("Отбор по году снят")

    def load_excel_async(self):
        if self.current_role not in ("admin", "editor"): return messagebox.showerror("Доступ запрещён",
                                                                                     "Недостаточно прав.")
        fp = filedialog.askopenfilename(title="Выберите Excel", filetypes=[("Excel", "*.xlsx *.xls")])
        if not fp: return
        self.current_filepath = fp;
        self.status_var.set("Загрузка Excel...");
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
        self.root.config(cursor="");
        self.btn_load.config(state="normal")
        if success:
            self.display_data();
            self.save_persisted_data();
            self.backup_data()
            self.log_action(f"Загружен: {filepath}");
            self.status_var.set(f"Данные загружены и сохранены. Записей: {len(self.data_model.data)}")
            messagebox.showinfo("Успех", "Данные загружены и сохранены.")
            self.year_entry.delete(0, tk.END);
            self._on_year_focus_out()
        else:
            self.status_var.set("Ошибка загрузки Excel")
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
        self.update_filter_summary()
        self.tree.update_idletasks()

    def update_filter_summary(self):
        if not hasattr(self, "filter_summary_var"):
            return
        if self.data_model.data.empty:
            self.filter_summary_var.set("Данные не загружены")
            return
        found = len(self.data_model.filtered_data)
        total = len(self.data_model.data)
        filters = []
        if self.data_model.smart_search_query:
            filters.append(f"поиск: {self.data_model.smart_search_query}")
        filters.extend(f"{field}: {value}" for field, value in self.data_model.filters)
        suffix = " | " + "; ".join(filters) if filters else ""
        self.filter_summary_var.set(f"Найдено: {found} из {total}{suffix}")

    def get_table_column_widths(self, columns):
        default_width = int(self.config.get("default_columns_width", 140))
        widths = {}
        for column in columns:
            if column in TABLE_COLUMN_WIDTHS:
                widths[column] = TABLE_COLUMN_WIDTHS[column]
            else:
                header_width = max(default_width, len(str(column)) * 9 + 24)
                widths[column] = min(header_width, 280)
        return widths

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
        cw = self.get_table_column_widths(dc)
        for c in dc: self.tree.heading(c, text=c, command=partial(self.set_sort, c)); self.tree.column(c,
                                                                                                       width=cw[c],
                                                                                                       minwidth=min(110, cw[c]),
                                                                                                       stretch=False,
                                                                                                       anchor="w")
        for idx, row in df.iterrows():
            oi = row.get('_original_index', idx);
            self.tree.insert("", "end", iid=str(oi), values=[self.data_model.format_display_value(row[c]) for c in dc])
        self.update_filter_summary()
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

    def open_selected_record_view(self, event=None):
        if event is not None and hasattr(event, "x") and hasattr(event, "y"):
            if self.tree.identify_region(event.x, event.y) == "heading":
                return
        sel = self.tree.selection()
        if not sel:
            return messagebox.showwarning("Запись", "Выберите строку в списке записей.")
        self.show_record_detail_view(int(sel[0]))

    def get_record_detail_sections(self, columns):
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
            fields = [field for field in wanted_fields if field in columns]
            if fields:
                sections.append((title, fields))
                assigned.update(fields)

        extra_fields = [field for field in columns if field not in assigned]
        if extra_fields:
            sections.append(("Дополнительные сведения", extra_fields))

        return sections

    def format_record_detail_value(self, column, value):
        display_value = self.data_model.format_display_value(value)
        if column == "Год защиты" and re.fullmatch(r"\d+\.0", display_value):
            return display_value[:-2]
        return display_value

    def get_record_detail_meta_value(self, record, column):
        value = self.format_record_detail_value(column, record.get(column, ""))
        return value if value else "Не указано"

    def is_long_record_detail_field(self, column):
        column_lower = column.lower()
        return any(marker in column_lower for marker in ("название", "примеч", "информация"))

    def create_record_meta_badge(self, parent, title, value):
        badge = tk.Frame(
            parent,
            bg="#173640",
            highlightbackground=APP_THEME["primary_alt"],
            highlightthickness=1,
        )
        badge.pack(side="left", padx=(0, SPACING["sm"]))
        tk.Label(
            badge,
            text=title,
            bg="#173640",
            fg=APP_THEME["topbar_muted"],
            font=self.ui_font("caption", "bold"),
            anchor="w",
        ).pack(fill="x", padx=SPACING["md"], pady=(SPACING["xs"], 0))
        tk.Label(
            badge,
            text=value,
            bg="#173640",
            fg=APP_THEME["topbar_text"],
            font=self.ui_font("small", "bold"),
            anchor="w",
            wraplength=170,
        ).pack(fill="x", padx=SPACING["md"], pady=(0, SPACING["xs"]))
        return badge

    def create_record_detail_section(self, parent, title):
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
            font=self.ui_font("heading", "bold"),
            anchor="w",
        ).pack(fill="x", padx=SPACING["lg"], pady=(SPACING["md"], SPACING["sm"]))

        content = tk.Frame(section, bg=APP_THEME["surface"])
        content.pack(fill="x", padx=SPACING["lg"], pady=(0, SPACING["md"]))
        content.columnconfigure(0, weight=1, uniform="record_detail_fields")
        content.columnconfigure(1, weight=1, uniform="record_detail_fields")
        return content

    def create_record_detail_field(self, parent, column, value, can_edit, row, column_index=0, columnspan=1):
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
            font=self.ui_font("small", "bold"),
            anchor="w",
        ).grid(row=0, column=0, sticky="ew", pady=(0, SPACING["xs"]))

        if self.is_long_record_detail_field(column):
            height = 4 if "название" in column.lower() else 3
            widget = tk.Text(
                field,
                height=height,
                wrap="word",
                font=self.ui_font("size"),
                bg=APP_THEME["surface_soft"],
                fg=APP_THEME["text"],
                insertbackground=APP_THEME["text"],
                relief="flat",
                bd=0,
                highlightbackground=APP_THEME["line"],
                highlightcolor=APP_THEME["primary_alt"],
                highlightthickness=1,
                padx=SPACING["sm"],
                pady=SPACING["sm"],
            )
            widget.insert("1.0", value)
            widget.grid(row=1, column=0, sticky="ew")
            if not can_edit:
                widget.config(state="disabled")
            return widget

        widget = tk.Entry(
            field,
            font=self.ui_font("size"),
            bg=APP_THEME["surface_soft"],
            fg=APP_THEME["text"],
            insertbackground=APP_THEME["text"],
            relief="flat",
            bd=0,
            highlightbackground=APP_THEME["line"],
            highlightcolor=APP_THEME["primary_alt"],
            highlightthickness=1,
            readonlybackground=APP_THEME["surface_soft"],
        )
        widget.insert(0, value)
        widget.grid(row=1, column=0, sticky="ew", ipady=SPACING["xs"])
        if not can_edit:
            widget.config(state="readonly")
        return widget

    def extract_record_detail_field_value(self, widget):
        if isinstance(widget, tk.Text):
            return widget.get("1.0", "end-1c").strip()
        return widget.get().strip()

    def show_record_detail_view(self, record_index):
        record = self.data_model.get_row_by_original_index(record_index)
        if record is None:
            return messagebox.showerror("Ошибка", "Запись не найдена.")

        can_edit = self.current_role in ("admin", "editor")
        title_value = record.get("ФИО") or "Карточка записи"
        detail = tk.Toplevel(self.root)
        detail.title(f"Карточка записи | {title_value}")
        detail_width = min(1160, max(980, detail.winfo_screenwidth() - 160))
        detail_height = min(800, max(680, detail.winfo_screenheight() - 140))
        self.center_toplevel_window(detail, detail_width, detail_height)
        detail.minsize(960, 660)
        detail.configure(bg=APP_THEME["app_background"])
        configure_ttk_style(detail, self.config["theme"])
        if self.app_icon_image is not None:
            detail.iconphoto(False, self.app_icon_image)

        header = tk.Frame(detail, bg=APP_THEME["topbar"], height=132)
        header.pack(fill="x")
        header.pack_propagate(False)
        header_content = tk.Frame(header, bg=APP_THEME["topbar"])
        header_content.pack(fill="both", expand=True, padx=SPACING["lg"], pady=SPACING["md"])
        header_content.columnconfigure(0, weight=1)
        header_content.columnconfigure(1, weight=0)
        tk.Label(
            header_content,
            text="Карточка записи",
            bg=APP_THEME["topbar"],
            fg=APP_THEME["topbar_text"],
            font=self.ui_font("title", "bold"),
            anchor="w",
        ).grid(row=0, column=0, sticky="ew")
        tk.Label(
            header_content,
            text=title_value,
            bg=APP_THEME["topbar"],
            fg=APP_THEME["topbar_muted"],
            font=self.ui_font("size", "bold"),
            anchor="w",
        ).grid(row=1, column=0, sticky="ew", pady=(SPACING["xs"], 0))

        mode_text = "Редактирование доступно" if can_edit else "Режим просмотра"
        tk.Label(
            header_content,
            text=mode_text,
            bg=APP_THEME["primary_alt"] if can_edit else "#173640",
            fg=APP_THEME["topbar_text"],
            font=self.ui_font("small", "bold"),
            padx=SPACING["md"],
            pady=SPACING["xs"],
        ).grid(row=2, column=0, sticky="w", pady=(SPACING["sm"], 0))

        meta_panel = tk.Frame(header_content, bg=APP_THEME["topbar"])
        meta_panel.grid(row=0, column=1, rowspan=3, sticky="ne", padx=(SPACING["lg"], 0))
        self.create_record_meta_badge(meta_panel, "Год защиты", self.get_record_detail_meta_value(record, "Год защиты"))
        self.create_record_meta_badge(
            meta_panel,
            "Степень",
            self.get_record_detail_meta_value(record, "Искомая степень"),
        )
        self.create_record_meta_badge(
            meta_panel,
            "Совет",
            self.get_record_detail_meta_value(record, "Диссертационный совет"),
        )

        detail_footer = tk.Frame(detail, bg=APP_THEME["surface"], height=78)
        detail_footer.pack(side="bottom", fill="x")
        detail_footer.pack_propagate(False)
        footer_hint = "Внесите изменения и сохраните карточку." if can_edit else "Просмотр записи без правки."
        tk.Label(
            detail_footer,
            text=footer_hint,
            bg=APP_THEME["surface"],
            fg=APP_THEME["muted_text"],
            font=self.ui_font("small"),
            anchor="w",
        ).pack(side="left", fill="x", expand=True, padx=SPACING["lg"], pady=SPACING["md"])

        footer_actions = tk.Frame(detail_footer, bg=APP_THEME["surface"])
        footer_actions.pack(side="right", padx=SPACING["lg"], pady=SPACING["md"])

        content_shell = tk.Frame(detail, bg=APP_THEME["app_background"])
        content_shell.pack(side="top", fill="both", expand=True)
        detail_canvas = tk.Canvas(content_shell, bg=APP_THEME["app_background"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(content_shell, orient="vertical", command=detail_canvas.yview)
        body = tk.Frame(detail_canvas, bg=APP_THEME["app_background"])
        body_id = detail_canvas.create_window((0, 0), window=body, anchor="nw")
        detail_canvas.configure(yscrollcommand=scrollbar.set)
        detail_canvas.pack(side="left", fill="both", expand=True, padx=(SPACING["lg"], 0), pady=SPACING["lg"])
        scrollbar.pack(side="right", fill="y", padx=(0, SPACING["lg"]), pady=SPACING["lg"])
        body.bind("<Configure>", lambda e: detail_canvas.configure(scrollregion=detail_canvas.bbox("all")))
        detail_canvas.bind("<Configure>", lambda e: detail_canvas.itemconfigure(body_id, width=e.width))

        fields = {}
        columns = [column for column in self.data_model.get_columns() if column != "_original_index"]
        for section_title, section_columns in self.get_record_detail_sections(columns):
            section = self.create_record_detail_section(body, section_title)
            grid_row = 0
            grid_column = 0
            for column in section_columns:
                value = self.format_record_detail_value(column, record.get(column, ""))
                if self.is_long_record_detail_field(column):
                    if grid_column != 0:
                        grid_row += 1
                        grid_column = 0
                    widget = self.create_record_detail_field(
                        section,
                        column,
                        value,
                        can_edit,
                        grid_row,
                        column_index=0,
                        columnspan=2,
                    )
                    grid_row += 1
                    grid_column = 0
                else:
                    widget = self.create_record_detail_field(
                        section,
                        column,
                        value,
                        can_edit,
                        grid_row,
                        column_index=grid_column,
                    )
                    if grid_column == 0:
                        grid_column = 1
                    else:
                        grid_row += 1
                        grid_column = 0
                fields[column] = widget

        if can_edit:
            tk.Button(
                footer_actions,
                text="Сохранить изменения",
                command=lambda: self.save_record_detail_changes(record_index, fields, detail),
                bg=APP_THEME["primary_alt"],
                fg=APP_THEME["topbar_text"],
                activebackground=APP_THEME["primary"],
                font=self.ui_font("size", "bold"),
                relief="flat",
                padx=SPACING["lg"],
                pady=SPACING["sm"],
            ).pack(side="left", padx=(0, SPACING["sm"]))
        tk.Button(
            footer_actions,
            text="Закрыть",
            command=detail.destroy,
            bg=APP_THEME["surface_soft"],
            fg=APP_THEME["text"],
            activebackground=APP_THEME["line"],
            font=self.ui_font("size", "bold"),
            relief="flat",
            padx=SPACING["lg"],
            pady=SPACING["sm"],
        ).pack(side="right")
        detail.focus_set()

    def save_record_detail_changes(self, record_index, fields, detail_window):
        if self.current_role not in ("admin", "editor"):
            return messagebox.showerror("Доступ запрещён", "Недостаточно прав для редактирования.")
        new_values = {}
        for column, widget in fields.items():
            new_values[column] = self.extract_record_detail_field_value(widget)
        self.data_model.update_record(record_index, new_values, allow_empty_update=True)
        self.display_data()
        self.save_persisted_data()
        self.log_action(f"Карточка записи обновлена: {record_index}")
        self.status_var.set("Запись обновлена и сохранена в Базе Данных")
        messagebox.showinfo("Успех", "Изменения сохранены.")
        detail_window.focus_set()

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
        self.status_var.set("Экспорт отчёта...");
        self.root.config(cursor="watch")

        def worker():
            try:
                task()
                self.root.after(0, self.export_complete, True, None, success_message, audit_action)
            except Exception as exc:
                self.root.after(0, self.export_complete, False, str(exc), success_message, audit_action)

        threading.Thread(target=worker, daemon=True).start()

    def export_complete(self, success, error, success_message, audit_action):
        self.root.config(cursor="")
        if success:
            self.status_var.set(success_message)
            messagebox.showinfo("Успех", success_message)
            self.log_action(audit_action)
        else:
            self.status_var.set("Ошибка экспорта отчёта")
            messagebox.showerror("Ошибка", f"Ошибка сохранения: {error}")

    def export_excel(self):
        if self.data_model.filtered_data.empty: return messagebox.showwarning("Нет данных")
        ed = self.data_model.filtered_data.drop(columns=['_original_index'], errors='ignore')

        def on_cols(sel):
            fp = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel", "*.xlsx")])
            if fp:
                self.run_export_task(
                    lambda: self.report_gen.export_to_excel(ed, fp, sel),
                    f"Отчёт сохранён: {fp}",
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
                    f"Отчёт сохранён: {fp}",
                    f"Экспорт Word: {fp}",
                )

        ColumnSelectorDialog(self.root, ed.columns.tolist(), on_cols)

    def build_year_statistics(self, df):
        years = pd.to_numeric(df["Год защиты"], errors="coerce").dropna().astype(int)
        counts = years.value_counts().sort_index()
        return self.summarize_year_counts(counts)

    def summarize_year_counts(self, counts):
        counts = counts.sort_index()
        if counts.empty:
            return {
                "counts": counts,
                "total": 0,
                "period": "нет данных",
                "peak_year": None,
                "peak_count": 0,
            }
        peak_year = int(counts.idxmax())
        peak_count = int(counts.loc[peak_year])
        return {
            "counts": counts,
            "total": int(counts.sum()),
            "period": f"{int(counts.index.min())}-{int(counts.index.max())}",
            "peak_year": peak_year,
            "peak_count": peak_count,
        }

    def filter_year_statistics_by_min_count(self, stats, min_count):
        try:
            min_count = max(1, int(min_count))
        except (TypeError, ValueError):
            min_count = 1
        counts = stats["counts"][stats["counts"] >= min_count]
        return self.summarize_year_counts(counts)

    @staticmethod
    def parse_optional_int(value):
        value = str(value or "").strip()
        if not value:
            return None
        try:
            return int(value)
        except ValueError:
            return None

    def filter_statistics_dataframe(self, df, criteria):
        result = df.copy()
        if result.empty:
            return result

        years = pd.to_numeric(result["Год защиты"], errors="coerce")
        year_from = self.parse_optional_int(criteria.get("year_from"))
        year_to = self.parse_optional_int(criteria.get("year_to"))
        if year_from is not None:
            result = result[years >= year_from]
            years = pd.to_numeric(result["Год защиты"], errors="coerce")
        if year_to is not None:
            result = result[years <= year_to]

        degree = str(criteria.get("degree") or "").strip()
        if degree and degree != "Все степени" and "Искомая степень" in result.columns:
            degree_values = result["Искомая степень"].map(DataModel.format_display_value).str.lower()
            result = result[degree_values == degree.lower()]

        query = str(criteria.get("query") or "").strip().lower()
        if query:
            def matches_query(row):
                return any(query in DataModel.format_display_value(value).lower() for value in row)

            result = result[result.apply(matches_query, axis=1)]

        min_count = self.parse_optional_int(criteria.get("min_count"))
        max_count = self.parse_optional_int(criteria.get("max_count"))
        if min_count is not None or max_count is not None:
            year_counts = pd.to_numeric(result["Год защиты"], errors="coerce").dropna().astype(int).value_counts()
            if min_count is not None:
                year_counts = year_counts[year_counts >= min_count]
            if max_count is not None:
                year_counts = year_counts[year_counts <= max_count]
            allowed_years = set(year_counts.index.astype(int).tolist())
            result_years = pd.to_numeric(result["Год защиты"], errors="coerce")
            result = result[result_years.isin(allowed_years)]

        return result

    def calculate_statistics_chart_size(self, bar_count):
        width = max(7.4, min(13.5, 5.8 + int(bar_count) * 0.52))
        return (width, 4.6)

    def format_work_count(self, count):
        count = int(count)
        if count % 10 == 1 and count % 100 != 11:
            return "работа"
        if count % 10 in (2, 3, 4) and count % 100 not in (12, 13, 14):
            return "работы"
        return "работ"

    def create_statistics_card(self, parent, title, value, subtitle):
        card = tk.Frame(
            parent,
            bg=APP_THEME["surface"],
            highlightbackground=APP_THEME["line"],
            highlightthickness=1,
        )
        card.pack(side="left", fill="x", expand=True, padx=(0, SPACING["md"]))
        tk.Label(
            card,
            text=title,
            bg=APP_THEME["surface"],
            fg=APP_THEME["muted_text"],
            font=self.ui_font("small", "bold"),
            anchor="w",
        ).pack(fill="x", padx=SPACING["md"], pady=(SPACING["md"], 2))
        value_label = tk.Label(
            card,
            text=value,
            bg=APP_THEME["surface"],
            fg=APP_THEME["text"],
            font=self.ui_font("title", "bold"),
            anchor="w",
        )
        value_label.pack(fill="x", padx=SPACING["md"])
        subtitle_label = tk.Label(
            card,
            text=subtitle,
            bg=APP_THEME["surface"],
            fg=APP_THEME["muted_text"],
            font=self.ui_font("caption"),
            anchor="w",
        )
        subtitle_label.pack(fill="x", padx=SPACING["md"], pady=(2, SPACING["md"]))
        return {"frame": card, "value": value_label, "subtitle": subtitle_label}

    def create_year_statistics_chart(self, parent, stats):
        counts = stats["counts"]
        years = [str(int(year)) for year in counts.index]
        values = [int(value) for value in counts.values]
        fig, ax = plt.subplots(figsize=self.calculate_statistics_chart_size(len(values)), dpi=100)
        fig.patch.set_facecolor(APP_THEME["surface"])
        ax.set_facecolor(APP_THEME["surface"])

        bars = ax.bar(
            years,
            values,
            color=APP_THEME["primary_alt"],
            edgecolor=APP_THEME["primary"],
            linewidth=0.8,
        )
        ax.set_title("Количество защищённых работ по годам", loc="left", pad=12, fontsize=13, fontweight="bold")
        ax.set_xlabel("Год")
        ax.set_ylabel("Количество работ")
        ax.yaxis.set_major_locator(MaxNLocator(integer=True))
        ax.set_ylim(0, max(values) + max(1, round(max(values) * 0.2)))
        ax.grid(axis="y", color=APP_THEME["line"], linestyle="--", linewidth=0.8, alpha=0.75)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["left"].set_color(APP_THEME["line"])
        ax.spines["bottom"].set_color(APP_THEME["line"])
        ax.tick_params(axis="x", labelrotation=0)

        for bar, value in zip(bars, values):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 0.05,
                str(value),
                ha="center",
                va="bottom",
                fontsize=10,
                color=APP_THEME["text"],
                fontweight="bold",
            )

        annotation = ax.annotate(
            "",
            xy=(0, 0),
            xytext=(12, 12),
            textcoords="offset points",
            bbox={"boxstyle": "round,pad=0.35", "fc": APP_THEME["text"], "ec": APP_THEME["text"], "alpha": 0.92},
            color=APP_THEME["topbar_text"],
            arrowprops={"arrowstyle": "->", "color": APP_THEME["text"]},
        )
        annotation.set_visible(False)
        fig.subplots_adjust(left=0.08, right=0.985, top=0.86, bottom=0.16)

        canvas = FigureCanvasTkAgg(fig, master=parent)

        def on_motion(event):
            visible = annotation.get_visible()
            if event.inaxes != ax:
                if visible:
                    annotation.set_visible(False)
                    canvas.draw_idle()
                return
            for bar, year, count in zip(bars, years, values):
                contains, _ = bar.contains(event)
                if contains:
                    annotation.xy = (bar.get_x() + bar.get_width() / 2, bar.get_height())
                    annotation.set_text(f"{year}: {count} {self.format_work_count(count)}")
                    annotation.set_visible(True)
                    canvas.draw_idle()
                    return
            if visible:
                annotation.set_visible(False)
                canvas.draw_idle()

        canvas.mpl_connect("motion_notify_event", on_motion)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        return canvas

    def fill_statistics_distribution_table(self, table, stats):
        for item in table.get_children():
            table.delete(item)
        if stats["total"] <= 0:
            return
        for year, count in stats["counts"].items():
            share = int(round((int(count) / stats["total"]) * 100))
            table.insert("", "end", values=(int(year), int(count), f"{share}%"))

    def show_statistics(self):
        if not MATPLOTLIB_AVAILABLE: return messagebox.showerror("Ошибка", "Требуется matplotlib")
        if self.data_model.data.empty: return messagebox.showwarning("Нет данных")
        df = self.data_model.data.copy()
        if "Год защиты" not in df.columns: return messagebox.showwarning("Нет данных о годах")
        stats = self.build_year_statistics(df)
        if stats["counts"].empty: return messagebox.showwarning("Нет данных о годах")

        sw = tk.Toplevel(self.root)
        sw.title("Статистика")
        sw.minsize(1080, 680)
        self.maximize_toplevel_window(sw)
        sw.configure(bg=APP_THEME["app_background"])
        configure_ttk_style(sw, self.config["theme"])

        header = tk.Frame(sw, bg=APP_THEME["topbar"], height=90)
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Label(
            header,
            text="Статистика по годам защиты",
            bg=APP_THEME["topbar"],
            fg=APP_THEME["topbar_text"],
            font=self.ui_font("title", "bold"),
            anchor="w",
        ).pack(fill="x", padx=SPACING["lg"], pady=(SPACING["md"], 0))
        tk.Label(
            header,
            text="Сводка по загруженным работам и распределение защит по календарным годам.",
            bg=APP_THEME["topbar"],
            fg=APP_THEME["topbar_muted"],
            font=self.ui_font("small"),
            anchor="w",
            wraplength=980,
            justify="left",
        ).pack(fill="x", padx=SPACING["lg"], pady=(2, SPACING["md"]))

        cards = tk.Frame(sw, bg=APP_THEME["app_background"])
        cards.pack(fill="x", padx=SPACING["lg"], pady=SPACING["md"])
        total_card = self.create_statistics_card(
            cards,
            "Всего работ",
            str(stats["total"]),
            f"учтено в статистике: {stats['total']} {self.format_work_count(stats['total'])}",
        )
        period_card = self.create_statistics_card(cards, "Период", stats["period"], "по полю «Год защиты»")
        peak_card = self.create_statistics_card(
            cards,
            "Пиковый год",
            str(stats["peak_year"]),
            f"{stats['peak_count']} {self.format_work_count(stats['peak_count'])}",
        )

        filter_frame = tk.Frame(
            sw,
            bg=APP_THEME["surface"],
            highlightbackground=APP_THEME["line"],
            highlightthickness=1,
        )
        filter_frame.pack(fill="x", padx=SPACING["lg"], pady=(0, SPACING["md"]))

        degree_values = ["Все степени"]
        if "Искомая степень" in df.columns:
            degree_values.extend(
                sorted(
                    {
                        DataModel.format_display_value(value)
                        for value in df["Искомая степень"]
                        if DataModel.format_display_value(value)
                    }
                )
            )
        max_count = max(1, int(stats["counts"].max()))
        year_min = int(stats["counts"].index.min())
        year_max = int(stats["counts"].index.max())
        year_from_var = tk.StringVar(value=str(year_min))
        year_to_var = tk.StringVar(value=str(year_max))
        degree_var = tk.StringVar(value="Все степени")
        query_var = tk.StringVar()
        min_count_var = tk.StringVar(value="1")
        max_count_var = tk.StringVar()
        filter_status_var = tk.StringVar()

        for column_index in range(12):
            filter_frame.columnconfigure(column_index, weight=1 if column_index in (5, 11) else 0)

        tk.Label(
            filter_frame,
            text="Год с",
            bg=APP_THEME["surface"],
            fg=APP_THEME["text"],
            font=self.ui_font("small", "bold"),
            anchor="w",
        ).grid(row=0, column=0, sticky="w", padx=(SPACING["md"], SPACING["xs"]), pady=(SPACING["sm"], 2))
        year_from_entry = tk.Entry(filter_frame, width=8, textvariable=year_from_var, font=self.ui_font("size"))
        year_from_entry.grid(row=1, column=0, sticky="ew", padx=(SPACING["md"], SPACING["sm"]), pady=(0, SPACING["sm"]))

        tk.Label(
            filter_frame,
            text="Год по",
            bg=APP_THEME["surface"],
            fg=APP_THEME["text"],
            font=self.ui_font("small", "bold"),
            anchor="w",
        ).grid(row=0, column=1, sticky="w", padx=(0, SPACING["xs"]), pady=(SPACING["sm"], 2))
        year_to_entry = tk.Entry(filter_frame, width=8, textvariable=year_to_var, font=self.ui_font("size"))
        year_to_entry.grid(row=1, column=1, sticky="ew", padx=(0, SPACING["sm"]), pady=(0, SPACING["sm"]))

        tk.Label(
            filter_frame,
            text="Искомая степень",
            bg=APP_THEME["surface"],
            fg=APP_THEME["text"],
            font=self.ui_font("small", "bold"),
            anchor="w",
        ).grid(row=0, column=2, sticky="w", padx=(0, SPACING["xs"]), pady=(SPACING["sm"], 2))
        degree_combo = ttk.Combobox(
            filter_frame,
            textvariable=degree_var,
            values=degree_values,
            state="readonly",
            width=26,
            font=self.ui_font("size"),
        )
        degree_combo.grid(row=1, column=2, sticky="ew", padx=(0, SPACING["sm"]), pady=(0, SPACING["sm"]))

        tk.Label(
            filter_frame,
            text="Поиск в статистике",
            bg=APP_THEME["surface"],
            fg=APP_THEME["text"],
            font=self.ui_font("small", "bold"),
            anchor="w",
        ).grid(row=0, column=3, sticky="w", padx=(0, SPACING["xs"]), pady=(SPACING["sm"], 2))
        query_entry = tk.Entry(filter_frame, textvariable=query_var, font=self.ui_font("size"), width=22)
        query_entry.grid(row=1, column=3, columnspan=3, sticky="ew", padx=(0, SPACING["sm"]), pady=(0, SPACING["sm"]))

        tk.Label(
            filter_frame,
            text="Минимум работ за год",
            bg=APP_THEME["surface"],
            fg=APP_THEME["text"],
            font=self.ui_font("small", "bold"),
            anchor="w",
        ).grid(row=0, column=6, sticky="w", padx=(0, SPACING["xs"]), pady=(SPACING["sm"], 2))
        min_count_spinbox = tk.Spinbox(
            filter_frame,
            from_=1,
            to=max_count,
            width=6,
            textvariable=min_count_var,
            font=self.ui_font("size"),
            command=lambda: refresh_statistics_view(),
            relief="solid",
            bd=1,
        )
        min_count_spinbox.grid(row=1, column=6, sticky="ew", padx=(0, SPACING["sm"]), pady=(0, SPACING["sm"]))

        tk.Label(
            filter_frame,
            text="Максимум работ за год",
            bg=APP_THEME["surface"],
            fg=APP_THEME["text"],
            font=self.ui_font("small", "bold"),
            anchor="w",
        ).grid(row=0, column=7, sticky="w", padx=(0, SPACING["xs"]), pady=(SPACING["sm"], 2))
        max_count_spinbox = tk.Spinbox(
            filter_frame,
            from_=1,
            to=max_count,
            width=6,
            textvariable=max_count_var,
            font=self.ui_font("size"),
            command=lambda: refresh_statistics_view(),
            relief="solid",
            bd=1,
        )
        max_count_spinbox.grid(row=1, column=7, sticky="ew", padx=(0, SPACING["sm"]), pady=(0, SPACING["sm"]))

        tk.Button(
            filter_frame,
            text="Применить",
            command=lambda: refresh_statistics_view(),
            bg=APP_THEME["primary_alt"],
            fg=APP_THEME["topbar_text"],
            activebackground=APP_THEME["primary"],
            font=self.ui_font("small", "bold"),
            relief="flat",
            padx=SPACING["md"],
        ).grid(row=1, column=8, sticky="ew", padx=(0, SPACING["sm"]), pady=(0, SPACING["sm"]))

        def reset_statistics_filters():
            year_from_var.set(str(year_min))
            year_to_var.set(str(year_max))
            degree_var.set("Все степени")
            query_var.set("")
            min_count_var.set("1")
            max_count_var.set("")
            refresh_statistics_view()

        tk.Button(
            filter_frame,
            text="Сброс",
            command=reset_statistics_filters,
            bg=APP_THEME["surface_soft"],
            fg=APP_THEME["text"],
            activebackground=APP_THEME["line"],
            font=self.ui_font("small", "bold"),
            relief="flat",
            padx=SPACING["md"],
        ).grid(row=1, column=9, sticky="ew", padx=(0, SPACING["sm"]), pady=(0, SPACING["sm"]))

        tk.Label(
            filter_frame,
            textvariable=filter_status_var,
            bg=APP_THEME["surface"],
            fg=APP_THEME["muted_text"],
            font=self.ui_font("small"),
            anchor="e",
        ).grid(row=1, column=10, columnspan=2, sticky="ew", padx=(0, SPACING["md"]), pady=(0, SPACING["sm"]))

        content = tk.Frame(sw, bg=APP_THEME["app_background"])
        content.pack(fill="both", expand=True, padx=SPACING["lg"], pady=(0, SPACING["lg"]))
        content.columnconfigure(0, weight=4)
        content.columnconfigure(1, weight=1)
        content.rowconfigure(0, weight=1)

        chart_frame = tk.Frame(
            content,
            bg=APP_THEME["surface"],
            highlightbackground=APP_THEME["line"],
            highlightthickness=1,
        )
        chart_frame.grid(row=0, column=0, sticky="nsew", padx=(0, SPACING["md"]))

        side_frame = tk.Frame(
            content,
            bg=APP_THEME["surface"],
            highlightbackground=APP_THEME["line"],
            highlightthickness=1,
        )
        side_frame.grid(row=0, column=1, sticky="nsew")
        tk.Label(
            side_frame,
            text="Распределение",
            bg=APP_THEME["surface"],
            fg=APP_THEME["text"],
            font=self.ui_font("size", "bold"),
            anchor="w",
        ).pack(fill="x", padx=SPACING["md"], pady=(SPACING["md"], SPACING["sm"]))
        table = ttk.Treeview(side_frame, columns=("year", "count", "share"), show="headings", height=12)
        table.heading("year", text="Год")
        table.heading("count", text="Работ")
        table.heading("share", text="Доля")
        table.column("year", width=70, anchor="center")
        table.column("count", width=70, anchor="center")
        table.column("share", width=70, anchor="center")
        table.pack(fill="both", expand=True, padx=SPACING["md"], pady=(0, SPACING["md"]))

        def refresh_statistics_view(*_):
            criteria = {
                "year_from": year_from_var.get(),
                "year_to": year_to_var.get(),
                "degree": degree_var.get(),
                "query": query_var.get(),
                "min_count": min_count_var.get(),
                "max_count": max_count_var.get(),
            }
            filtered_df = self.filter_statistics_dataframe(df, criteria)
            filtered_stats = self.build_year_statistics(filtered_df)
            for child in chart_frame.winfo_children():
                child.destroy()

            if filtered_stats["counts"].empty:
                total_card["value"].config(text="0")
                total_card["subtitle"].config(text="по текущему фильтру нет работ")
                period_card["value"].config(text="нет данных")
                peak_card["value"].config(text="нет данных")
                peak_card["subtitle"].config(text="нет данных")
                tk.Label(
                    chart_frame,
                    text="Нет годов с выбранным количеством работ",
                    bg=APP_THEME["surface"],
                    fg=APP_THEME["muted_text"],
                    font=self.ui_font("size", "bold"),
                ).pack(fill="both", expand=True)
                for item in table.get_children():
                    table.delete(item)
                filter_status_var.set("Нет данных по выбранным условиям.")
                return

            total_card["value"].config(text=str(filtered_stats["total"]))
            total_card["subtitle"].config(
                text=f"в текущей выборке: {filtered_stats['total']} {self.format_work_count(filtered_stats['total'])}"
            )
            period_card["value"].config(text=filtered_stats["period"])
            peak_card["value"].config(text=str(filtered_stats["peak_year"]))
            peak_card["subtitle"].config(
                text=f"{filtered_stats['peak_count']} {self.format_work_count(filtered_stats['peak_count'])}"
            )
            self.create_year_statistics_chart(chart_frame, filtered_stats)
            self.fill_statistics_distribution_table(table, filtered_stats)
            shown_years = len(filtered_stats["counts"])
            filter_status_var.set(
                f"Показано годов: {shown_years}. "
                f"Работ в выборке: {filtered_stats['total']}."
            )

        for widget in (year_from_entry, year_to_entry, query_entry, min_count_spinbox, max_count_spinbox):
            widget.bind("<Return>", refresh_statistics_view)
            widget.bind("<FocusOut>", refresh_statistics_view)
        degree_combo.bind("<<ComboboxSelected>>", refresh_statistics_view)
        refresh_statistics_view()

        tk.Button(
            sw,
            text="Закрыть",
            command=sw.destroy,
            bg=APP_THEME["surface_soft"],
            fg=APP_THEME["text"],
            activebackground=APP_THEME["line"],
            font=self.ui_font("size", "bold"),
            relief="flat",
            padx=SPACING["lg"],
            pady=SPACING["sm"],
        ).pack(anchor="e", padx=SPACING["lg"], pady=(0, SPACING["md"]))

    def manage_users(self):
        if self.current_role != "admin": return messagebox.showerror("Доступ запрещён")
        UserManagementDialog(self.root, self.user_manager, self.current_user, log_callback=self.log_action)

    def switch_user(self):
        self.save_persisted_data()
        if self.ui_built: self.clear_ui(); self.ui_built = False
        self.current_user = None;
        self.current_role = None;
        self.status_var.set("Готово. Данные будут сохранены в локальную базу SQLite.");
        self.schedule_login()

    def on_closing(self):
        if self.is_closing:
            return
        self.is_closing = True
        self.cancel_scheduled_callbacks()
        self.save_persisted_data();
        self.log_action("Завершение");
        if hasattr(self, "storage"):
            self.storage.close()
        logging.shutdown()
        self.root.destroy()

    def schedule_process_queue(self):
        if self.is_closing:
            return
        try:
            if not self.root.winfo_exists():
                return
            self.queue_after_id = self.root.after(100, self.process_queue)
        except tk.TclError:
            self.queue_after_id = None

    def schedule_login(self):
        if self.is_closing:
            return
        try:
            if not self.root.winfo_exists():
                return
            self.login_after_id = self.root.after(100, self.show_login)
        except tk.TclError:
            self.login_after_id = None

    def cancel_scheduled_callbacks(self):
        if self.queue_after_id:
            try:
                self.root.after_cancel(self.queue_after_id)
            except tk.TclError:
                pass
            finally:
                self.queue_after_id = None
        if self.login_after_id:
            try:
                self.root.after_cancel(self.login_after_id)
            except tk.TclError:
                pass
            finally:
                self.login_after_id = None

    def destroy_root_after_cancel(self):
        if self.is_closing:
            return
        self.is_closing = True
        self.cancel_scheduled_callbacks()
        self.root.destroy()

    def process_queue(self):
        if self.is_closing:
            return
        try:
            while True: self.task_queue.get_nowait()()
        except queue.Empty:
            pass
        self.schedule_process_queue()
