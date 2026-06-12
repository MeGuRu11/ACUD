"""Main Tkinter application window."""

import json
import logging
import os
import queue
import shutil
import threading
import time
import tkinter as tk
from functools import partial
from tkinter import filedialog, messagebox, ttk

import pandas as pd

from asud.auth import UserManager
from asud.config import CONFIG_FILE, DEFAULT_CONFIG
from asud.data_model import DataModel
from asud.reports import ReportGenerator
from asud.storage import SQLiteStorage
from asud.ui.theme import APP_THEME, WINDOW_MINSIZE, configure_ttk_style
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
        self.root.geometry("1300x700");
        self.root.minsize(*WINDOW_MINSIZE)
        self.root.configure(bg=APP_THEME["background"])
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
        self.status_var.set("Готов")
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
            rn = {"admin": "Администратор", "editor": "Редактор", "viewer": "Наблюдатель"}
            self.status_var.set(f"Пользователь: {self.current_user} | {rn.get(self.current_role, self.current_role)}")
            self.build_ui();
            self.load_persisted_data();
            self.update_permissions();
            self.ui_built = True
        else:
            self.root.destroy()

    def update_permissions(self):
        aa = [self.btn_load, self.btn_add, self.btn_edit, self.btn_delete, self.btn_users];
        ea = [self.btn_add, self.btn_edit, self.btn_delete]
        if self.current_role == "admin":
            for b in aa: b.config(state="normal")
        elif self.current_role == "editor":
            for b in ea: b.config(state="normal")
            for b in aa:
                if b not in ea: b.config(state="disabled")
        else:
            for b in aa + ea: b.config(state="disabled")

    def build_ui(self):
        self.bg_main = APP_THEME["background"];
        self.bg_panel = APP_THEME["panel"];
        self.fg_text = APP_THEME["text"];
        self.accent = APP_THEME["accent"];
        self.table_bg = APP_THEME["table_background"];
        self.table_fg = APP_THEME["table_text"]
        hf = tk.Frame(self.root, bg=self.bg_main);
        hf.pack(fill="x", padx=10, pady=5)
        self.logo_image = None
        if PIL_AVAILABLE and os.path.exists(self.config["logo_path"]):
            try:
                pi = Image.open(self.config["logo_path"]);
                pi = pi.resize((80, 80), Image.Resampling.LANCZOS);
                self.logo_image = ImageTk.PhotoImage(pi)
            except Exception as e:
                print(f"Лого: {e}")
        hf.columnconfigure(0, weight=0);
        hf.columnconfigure(1, weight=1)
        if self.logo_image: tk.Label(hf, image=self.logo_image, bg=self.bg_main).grid(row=0, column=0, padx=(0, 10),
                                                                                      pady=5, sticky="w")
        tk.Label(hf,
                 text="Военно-медицинская академия имени С.М. Кирова\nАвтоматизированная система учёта диссертаций",
                 font=("Times New Roman", 16, "bold"), fg=self.accent, bg=self.bg_main, justify="center").grid(row=0,
                                                                                                               column=1,
                                                                                                               sticky="ew",
                                                                                                               pady=5)

        self.control_frame = tk.Frame(self.root, bg=self.bg_panel, width=320);
        self.control_frame.pack(side="left", fill="y", padx=10, pady=10)
        bs = {"bg": self.accent, "fg": "black", "font": ("Times New Roman", 10, "bold"), "activebackground": APP_THEME["accent_active"],
              "bd": 2, "relief": "raised"}
        tk.Label(self.control_frame, text="1. Загрузка данных", bg=self.bg_panel, fg=self.fg_text,
                 font=("Times New Roman", 11, "bold")).pack(anchor="w", pady=(0, 5))
        self.btn_load = tk.Button(self.control_frame, text="Загрузить Excel", command=self.load_excel_async, width=28,
                                  **bs);
        self.btn_load.pack(pady=2)
        tk.Label(self.control_frame, text="2. Управление", bg=self.bg_panel, fg=self.fg_text,
                 font=("Times New Roman", 11, "bold")).pack(anchor="w", pady=(15, 5))
        self.btn_add = tk.Button(self.control_frame, text="Добавить запись", command=self.add_record, width=28, **bs);
        self.btn_add.pack(pady=2)
        self.btn_edit = tk.Button(self.control_frame, text="Редактировать", command=self.edit_selected, width=28, **bs);
        self.btn_edit.pack(pady=2)
        self.btn_delete = tk.Button(self.control_frame, text="Удалить", command=self.delete_selected, width=28, **bs);
        self.btn_delete.pack(pady=2)

        tk.Label(self.control_frame, text="3. Поиск и фильтры", bg=self.bg_panel, fg=self.fg_text,
                 font=("Times New Roman", 11, "bold")).pack(anchor="w", pady=(15, 5))
        self.search_frame = tk.Frame(self.control_frame, bg=self.bg_panel);
        self.search_frame.pack(fill="x", pady=2)
        self.search_entry = tk.Entry(self.search_frame, width=20, font=("Times New Roman", 10));
        self.search_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self.search_entry.bind("<KeyRelease>", lambda e: self.smart_search())
        tk.Button(self.search_frame, text="🔍", command=self.simple_search, bg=self.accent, fg="black", width=3,
                  font=("Times New Roman", 8)).pack(side="right")

        # 🔧 ИСПРАВЛЕНО: Поле года с безопасным вводом
        self.year_filter_frame = tk.Frame(self.control_frame, bg=self.bg_panel);
        self.year_filter_frame.pack(fill="x", pady=2)
        tk.Label(self.year_filter_frame, text="📅 Год:", bg=self.bg_panel, fg=self.fg_text,
                 font=("Times New Roman", 9)).pack(side="left")
        self.year_entry = tk.Entry(self.year_filter_frame, width=12, font=("Times New Roman", 9));
        self.year_entry.pack(side="left", padx=2)
        self.year_entry.bind("<KeyRelease>", lambda e: self.apply_year_filter())
        self.year_entry.insert(0, "2023 или 2020-2024")
        self.year_entry.bind("<FocusIn>", lambda e: self._on_year_focus_in())
        self.year_entry.bind("<FocusOut>", lambda e: self._on_year_focus_out())
        tk.Button(self.year_filter_frame, text="✕", command=self.clear_year_filter, bg=self.accent, fg="black", width=2,
                  font=("Times New Roman", 8)).pack(side="left", padx=2)

        tk.Button(self.control_frame, text="Расширенный фильтр", command=self.open_filter_dialog, width=28, **bs).pack(
            pady=2)
        tk.Button(self.control_frame, text="Сбросить фильтры", command=self.clear_filters, width=28, **bs).pack(pady=2)

        tk.Label(self.control_frame, text="4. Отчёты", bg=self.bg_panel, fg=self.fg_text,
                 font=("Times New Roman", 11, "bold")).pack(anchor="w", pady=(15, 5))
        self.btn_export_excel = tk.Button(self.control_frame, text="Экспорт Excel", command=self.export_excel, width=28,
                                          **bs);
        self.btn_export_excel.pack(pady=2)
        self.btn_export_word = tk.Button(self.control_frame, text="Экспорт Word", command=self.export_word, width=28,
                                         **bs);
        self.btn_export_word.pack(pady=2)
        if MATPLOTLIB_AVAILABLE: self.btn_stats = tk.Button(self.control_frame, text="Статистика",
                                                            command=self.show_statistics, width=28,
                                                            **bs); self.btn_stats.pack(pady=2)
        self.btn_users = tk.Button(self.control_frame, text="👥 Пользователи", command=self.manage_users, width=28,
                                   **bs)
        self.btn_users.pack(pady=2)
        tk.Button(self.control_frame, text="🔄 Сменить пользователя", command=self.switch_user, width=28, **bs).pack(
            pady=2)
        tk.Button(self.control_frame, text="🚪 Выход", command=self.on_closing, width=28, **bs).pack(pady=2)

        tk.Label(self.root, textvariable=self.status_var, bd=1, relief=tk.SUNKEN, anchor=tk.W, bg=self.bg_panel,
                 fg=self.fg_text, font=("Times New Roman", 9)).pack(side=tk.BOTTOM, fill=tk.X)

        self.table_frame = tk.Frame(self.root, bg=self.table_bg);
        self.table_frame.pack(side="right", expand=True, fill="both", padx=10, pady=10)
        self.table_frame.rowconfigure(0, weight=1);
        self.table_frame.columnconfigure(0, weight=1)
        configure_ttk_style(self.root, self.config["theme"])
        tc = tk.Frame(self.table_frame, bg=self.table_bg);
        tc.grid(row=0, column=0, sticky="nsew")
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

        self.root.bind("<Control-o>", lambda e: self.load_excel_async());
        self.root.bind("<Control-f>", lambda e: self.search_entry.focus_set())
        self.root.bind("<Control-s>", lambda e: self.export_excel());
        self.root.bind("<Delete>", lambda e: self.delete_selected());
        self.root.bind("<Control-e>", lambda e: self.edit_selected())
        self.tree.bind("<Button-1>", self.on_tree_click)

    def _on_year_focus_in(self):
        if self.year_entry.get() == "2023 или 2020-2024": self.year_entry.delete(0, tk.END); self.year_entry.config(
            fg="black")

    def _on_year_focus_out(self):
        if not self.year_entry.get().strip(): self.year_entry.insert(0, "2023 или 2020-2024"); self.year_entry.config(
            fg="gray")

    def clear_ui(self):
        for a in ['control_frame', 'table_frame']:
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

    def display_data(self):
        if not hasattr(self, 'tree') or self.tree is None: return
        for i in self.tree.get_children(): self.tree.delete(i)
        df = self.data_model.get_filtered_data()
        if df.empty: self.tree["columns"] = []; return
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

    def export_excel(self):
        if self.data_model.filtered_data.empty: return messagebox.showwarning("Нет данных")
        ed = self.data_model.filtered_data.drop(columns=['_original_index'], errors='ignore')

        def on_cols(sel):
            fp = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel", "*.xlsx")])
            if fp:
                try:
                    self.report_gen.export_to_excel(ed, fp, sel);
                    messagebox.showinfo("Успех",
                                        f"Сохранено: {fp}");
                    self.log_action(
                        f"Экспорт Excel: {fp}")
                except Exception as e:
                    messagebox.showerror("Ошибка", f"Ошибка сохранения: {e}")

        ColumnSelectorDialog(self.root, ed.columns.tolist(), on_cols)

    def export_word(self):
        if self.data_model.filtered_data.empty: return messagebox.showwarning("Нет данных")
        ed = self.data_model.filtered_data.drop(columns=['_original_index'], errors='ignore')

        def on_cols(sel):
            fp = filedialog.asksaveasfilename(defaultextension=".docx", filetypes=[("Word", "*.docx")])
            if fp:
                try:
                    qt = "поиск по полям: " + " ; ".join(
                        f"{f}='{v}'" for f, v in self.data_model.filters) if self.data_model.filters else (
                        f"поиск: «{self.data_model.smart_search_query}»" if self.data_model.smart_search_query else "все записи")
                    self.report_gen.export_to_word(ed, fp, qt, sel);
                    messagebox.showinfo("Успех", f"Сохранено: {fp}");
                    self.log_action(f"Экспорт Word: {fp}")
                except Exception as e:
                    messagebox.showerror("Ошибка", f"Ошибка сохранения: {e}")

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
        self.root.destroy()

    def process_queue(self):
        try:
            while True: self.task_queue.get_nowait()()
        except queue.Empty:
            pass
        self.root.after(100, self.process_queue)
