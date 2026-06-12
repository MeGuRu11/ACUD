#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
АСУД | ВМедА им. С.М. Кирова
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import pandas as pd
import numpy as np
from docx import Document
from docx.shared import Pt, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
import os
import re
import json
import shutil
import threading
import queue
import time
import hashlib
import secrets
from datetime import datetime
from openpyxl.styles import Border, Side
import logging
from functools import partial

# Опциональные библиотеки
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

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import cm

    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

try:
    import bcrypt

    BCRYPT_AVAILABLE = True
except ImportError:
    BCRYPT_AVAILABLE = False


# =============================================================================
# ХЕШИРОВАНИЕ ПАРОЛЕЙ
# =============================================================================
def hash_password(password):
    if BCRYPT_AVAILABLE:
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    else:
        salt = secrets.token_hex(16)
        pwd_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'),
                                       salt.encode('utf-8'), 100000).hex()
        return f"{salt}${pwd_hash}"


def check_password(password, stored_hash):
    if BCRYPT_AVAILABLE:
        return bcrypt.checkpw(password.encode('utf-8'), stored_hash.encode('utf-8'))
    else:
        if '$' not in stored_hash: return False
        salt, pwd_hash = stored_hash.split('$', 1)
        return hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000).hex() == pwd_hash


# =============================================================================
# КОНФИГУРАЦИЯ
# =============================================================================
CONFIG_FILE = "config.json"
DEFAULT_CONFIG = {
    "logo_path": "logo.png", "persistence_file": "last_data.csv",
    "audit_log": "audit.log", "backup_dir": "backups",
    "users_file": "users.json", "report_template": "template.docx",
    "default_columns_width": 120, "theme": "clam"
}
REQUIRED_COLUMNS = ["Искомая степень", "Информация о лишении степени", "Примечания"]
DEGREE_OPTIONS = ["кандидат медицинских наук", "доктор медицинских наук"]


# =============================================================================
# УПРАВЛЕНИЕ ПОЛЬЗОВАТЕЛЯМИ
# =============================================================================
class UserManager:
    def __init__(self, config):
        self.config = config
        self.users_file = config["users_file"]
        self.current_user = None
        self.load_users()

    def load_users(self):
        if os.path.exists(self.users_file):
            try:
                with open(self.users_file, "r", encoding="utf-8") as f:
                    self.users = json.load(f)
                for username, data in self.users.items():
                    for k, v in {"full_name": username, "created_at": datetime.now().isoformat(), "last_login": None,
                                 "force_password_change": False}.items():
                        data.setdefault(k, v)
                self.save_users()
            except (json.JSONDecodeError, IOError):
                self._create_default_admin()
        else:
            self._create_default_admin()

    def _create_default_admin(self):
        self.users = {"admin": {"password_hash": hash_password("admin"), "role": "admin", "full_name": "Администратор",
                                "created_at": datetime.now().isoformat(), "last_login": None,
                                "force_password_change": True}}
        self.save_users()

    def save_users(self):
        os.makedirs(os.path.dirname(self.users_file) if os.path.dirname(self.users_file) else ".", exist_ok=True)
        with open(self.users_file, "w", encoding="utf-8") as f:
            json.dump(self.users, f, indent=2, ensure_ascii=False)

    def authenticate(self, username, password):
        if username in self.users and check_password(password, self.users[username]["password_hash"]):
            self.current_user = username
            self.users[username]["last_login"] = datetime.now().isoformat()
            self.save_users()
            return True, self.users[username]["role"], self.users[username].get("force_password_change", False)
        return False, None, None

    def validate_password(self, password):
        if len(password) < 8: return False, "Мин. 8 символов"
        if not re.search(r'[A-ZА-ЯЁ]', password): return False, "Нужна заглавная буква"
        if not re.search(r'[a-zа-яё]', password): return False, "Нужна строчная буква"
        if not re.search(r'\d', password): return False, "Нужна цифра"
        return True, ""

    def validate_username(self, username):
        """Валидация логина."""
        if not username or len(username) < 3: return False, "Мин. 3 символа"
        if not re.match(r'^[a-zA-Z0-9_-]+$', username): return False, "Только латиница, цифры, _ и -"
        return True, ""

    def add_user(self, username, password, role, full_name, created_by=None):
        if username in self.users: return False, "Логин занят"
        valid, err = self.validate_username(username)
        if not valid: return False, err
        valid, err = self.validate_password(password)
        if not valid: return False, err
        if role not in ("admin", "editor", "viewer"): return False, "Недопустимая роль"
        self.users[username] = {"password_hash": hash_password(password), "role": role, "full_name": full_name,
                                "created_at": datetime.now().isoformat(), "created_by": created_by or "system",
                                "last_login": None, "force_password_change": False}
        self.save_users()
        return True, "Успешно"

    def register_user(self, username, password, full_name):
        if username in self.users: return False, "Логин занят"
        valid, err = self.validate_username(username)
        if not valid: return False, err
        if len(full_name.strip()) < 2: return False, "Мин. 2 символа для ФИО"
        valid, err = self.validate_password(password)
        if not valid: return False, err
        self.users[username] = {"password_hash": hash_password(password), "role": "viewer",
                                "full_name": full_name.strip(), "created_at": datetime.now().isoformat(),
                                "created_by": "self", "last_login": None, "force_password_change": True}
        self.save_users()
        return True, "Успешно"

    def change_password(self, username, old_password, new_password, require_old=True):
        if username not in self.users: return False, "Не найден"
        if require_old:
            if not old_password:
                return False, "Введите текущий пароль"
            if not check_password(old_password, self.users[username]["password_hash"]):
                return False, "Неверный текущий пароль"
        valid, err = self.validate_password(new_password)
        if not valid: return False, err
        if check_password(new_password, self.users[username]["password_hash"]):
            return False, "Пароли совпадают"
        self.users[username]["password_hash"] = hash_password(new_password)
        self.users[username]["force_password_change"] = False
        self.save_users()
        return True, "Изменён"

    # ✅ НОВОЕ: изменение логина пользователя
    def change_username(self, old_username, new_username, changed_by=None):
        if old_username not in self.users: return False, "Пользователь не найден"
        if old_username == "admin": return False, "Нельзя изменить логин главного администратора"
        if new_username in self.users: return False, "Логин уже занят"
        valid, err = self.validate_username(new_username)
        if not valid: return False, err

        # Копируем данные и создаём новую запись
        user_data = self.users[old_username].copy()
        if changed_by: user_data["modified_by"] = changed_by
        user_data["modified_at"] = datetime.now().isoformat()

        self.users[new_username] = user_data
        del self.users[old_username]

        # Если меняли свой логин — обновляем текущую сессию
        if self.current_user == old_username:
            self.current_user = new_username

        self.save_users()
        return True, f"Логин изменён: {old_username} → {new_username}"

    def update_user(self, username, new_role=None, new_full_name=None, force_password_change=None):
        if username not in self.users: return False, "Не найден"
        if username == "admin" and new_role and new_role != "admin": return False, "Нельзя сменить роль админа"
        if new_role: self.users[username]["role"] = new_role
        if new_full_name: self.users[username]["full_name"] = new_full_name
        if force_password_change is not None: self.users[username]["force_password_change"] = force_password_change
        self.save_users()
        return True, "Обновлено"

    def delete_user(self, username):
        if username not in self.users: return False, "Не найден"
        if username == "admin": return False, "Нельзя удалить админа"
        if username == self.current_user: return False, "Нельзя удалить себя"
        if sum(1 for u, d in self.users.items() if d["role"] == "admin") <= 1 and self.users[username][
            "role"] == "admin":
            return False, "Нужен хотя бы 1 админ"
        del self.users[username]
        self.save_users()
        return True, "Удалён"

    def get_user_info(self, username):
        return {k: v for k, v in self.users[username].items() if
                k != "password_hash"} if username in self.users else None

    def get_users_list(self):
        return [{"username": u, "role": d["role"], "full_name": d["full_name"], "created_at": d.get("created_at", ""),
                 "last_login": d.get("last_login", "Никогда"),
                 "force_password_change": d.get("force_password_change", False)} for u, d in self.users.items()]


# =============================================================================
# МОДЕЛЬ ДАННЫХ
# =============================================================================
class DataModel:
    def __init__(self, config):
        self.config = config
        self.data = pd.DataFrame()
        self.filtered_data = pd.DataFrame()
        self.filters = []
        self.sort_column = None
        self.sort_reverse = False
        self.smart_search_query = ""

    def _safe_convert_value(self, col, val):
        if val is None or (isinstance(val, str) and val.strip() == ''): return pd.NA
        if col in self.data.columns:
            d = str(self.data[col].dtype)
            if 'Int64' in d:
                try:
                    return int(val)
                except:
                    return pd.NA
            elif 'Float64' in d:
                try:
                    return float(val)
                except:
                    return pd.NA
        return val

    def load_excel(self, filepath, progress_callback=None):
        df_raw = pd.read_excel(filepath, header=None, dtype=str)
        if df_raw.empty: raise ValueError("Файл пуст.")
        key_cols = ["ФИО", "Название диссертации", "Диссертационный совет"]
        header_row = next(
            (i for i, r in df_raw.iterrows() if any(k in str(r).lower() for k in [x.lower() for x in key_cols])), None)
        if header_row is None: header_row = next((i for i, r in df_raw.iterrows() if r.notna().sum() >= 5), 0)
        df = pd.read_excel(filepath, header=header_row, dtype=str).dropna(how='all').dropna(axis=1, how='all')
        df.columns = df.columns.str.strip()
        for col in REQUIRED_COLUMNS:
            if col not in df.columns: df[col] = None
        df = df[df["ФИО"].notna() & (df["ФИО"] != "")] if "ФИО" in df.columns else df
        df.reset_index(drop=True, inplace=True)
        date_col = "Дата защиты диссертации"
        if date_col in df.columns:
            df[date_col] = df[date_col].apply(self._normalize_date)
            df["Год защиты"] = pd.to_datetime(df[date_col], format="%d.%m.%Y", errors="coerce").dt.year.astype("Int64")
        self.data = df.copy()
        self.filtered_data = self.data.copy()
        self.apply_filters()
        return True

    def _add_missing_columns(self, df):
        for col in REQUIRED_COLUMNS:
            if col not in df.columns: df[col] = None
        return df[[c for c in df.columns if c not in REQUIRED_COLUMNS] + REQUIRED_COLUMNS]

    def _normalize_date(self, date_str):
        if pd.isna(date_str) or not date_str.strip(): return ""
        date_str = str(date_str).strip()
        if re.match(r"\d{1,2}\.\d{1,2}\.\d{4}", date_str): return date_str
        months = {"января": "01", "февраля": "02", "марта": "03", "апреля": "04", "мая": "05", "июня": "06",
                  "июля": "07", "августа": "08", "сентября": "09", "октября": "10", "ноября": "11", "декабря": "12"}
        parts = date_str.replace("г.", "").replace(".", "").strip().split()
        if len(parts) >= 3 and parts[1].lower() in months:
            try:
                return datetime(int(parts[2]), int(months[parts[1].lower()]), int(parts[0])).strftime("%d.%m.%Y")
            except:
                pass
        return date_str

    def add_record(self, record):
        for col in REQUIRED_COLUMNS: record.setdefault(col, None)
        safe = {col: self._safe_convert_value(col, val) for col, val in record.items()}
        self.data = pd.concat([self.data, pd.Series(safe).to_frame().T], ignore_index=True)
        date_col = "Дата защиты диссертации"
        if date_col in self.data.columns:
            self.data[date_col] = self.data[date_col].apply(self._normalize_date)
            self.data["Год защиты"] = pd.to_datetime(self.data[date_col], format="%d.%m.%Y",
                                                     errors="coerce").dt.year.astype("Int64")
        self.apply_filters()

    def delete_record(self, index):
        self.data = self.data.drop(index).reset_index(drop=True)
        self.apply_filters()

    def update_record(self, index, new_values):
        for col, val in new_values.items():
            if col not in self.data.columns or col == '_original_index': continue
            cur = self.data.at[index, col] if index in self.data.index else None
            is_empty = val is None or (isinstance(val, str) and val.strip() == '')
            if is_empty and pd.notna(cur) and str(cur).strip() != '': continue
            sv = self._safe_convert_value(col, val)
            self.data.at[index, col] = sv
            if index in self.filtered_data.index and col in self.filtered_data.columns: self.filtered_data.at[
                index, col] = sv
        date_col = "Дата защиты диссертации"
        if date_col in self.data.columns:
            self.data[date_col] = self.data[date_col].apply(self._normalize_date)
            self.data["Год защиты"] = pd.to_datetime(self.data[date_col], format="%d.%m.%Y",
                                                     errors="coerce").dt.year.astype("Int64")
            if date_col in self.filtered_data.columns:
                self.filtered_data[date_col] = self.filtered_data[date_col].apply(self._normalize_date)
                self.filtered_data["Год защиты"] = pd.to_datetime(self.filtered_data[date_col], format="%d.%m.%Y",
                                                                  errors="coerce").dt.year.astype("Int64")
        self.apply_filters()

    def get_row_by_original_index(self, index):
        if index in self.data.index:
            row = self.data.loc[index].copy()
            return {k: ('' if pd.isna(v) else str(v)) for k, v in row.to_dict().items()}
        return None

    def add_filter(self, field, value):
        self.filters.append((field, value))
        self.apply_filters()

    def clear_filters(self):
        self.filters = []
        self.smart_search_query = ""
        self.apply_filters()

    def set_smart_search(self, query):
        self.smart_search_query = query.strip().lower()
        self.apply_filters()

    def _parse_year_range(self, value: str) -> tuple:
        value = value.strip()
        for sep in ['-', ':', '..']:
            if sep in value:
                parts = value.split(sep)
                if len(parts) == 2:
                    try:
                        return (min(int(parts[0]), int(parts[1])), max(int(parts[0]), int(parts[1])))
                    except ValueError:
                        pass
        try:
            return (int(value), int(value))
        except ValueError:
            return (None, None)

    def apply_filters(self):
        if self.data.empty:
            self.filtered_data = self.data.copy()
            return
        result = self.data.copy()
        for field, value in self.filters:
            if field not in result.columns: continue
            if field == "Год защиты":
                s, e = self._parse_year_range(value)
                mask = result[field].between(s, e, inclusive='both') if s is not None else result[field].astype(
                    str).str.contains(value, case=False, na=False)
            else:
                mask = result[field].astype(str).str.contains(value, case=False, na=False)
            result = result[mask]
        if self.smart_search_query:
            def smart(row): return any(
                self.smart_search_query in str(c).lower() for c in row if pd.notna(c) and c != '_original_index')

            result = result[result.apply(smart, axis=1)]
        result = result.copy()
        result['_original_index'] = result.index
        self.filtered_data = result
        self.sort_data()

    def sort_data(self):
        if self.sort_column and self.sort_column in self.filtered_data.columns:
            self.filtered_data = self.filtered_data.sort_values(by=self.sort_column,
                                                                ascending=not self.sort_reverse).reset_index(drop=True)

    def set_sort(self, column, reverse=False):
        self.sort_column = column
        self.sort_reverse = reverse
        self.sort_data()

    def get_columns(self):
        return self.data.columns.tolist() if not self.data.empty else []

    def get_filtered_data(self):
        return self.filtered_data


# =============================================================================
# ГЕНЕРАТОР ОТЧЁТОВ
# =============================================================================
class ReportGenerator:
    def __init__(self, config):
        self.config = config

    def export_to_excel(self, df, filepath, selected_columns=None):
        if selected_columns: df = df[selected_columns]
        with pd.ExcelWriter(filepath, engine='openpyxl') as w:
            df.to_excel(w, sheet_name='Отчёт', index=False)
            ws = w.sheets['Отчёт']
            b = Border(left=Side('thin'), right=Side('thin'), top=Side('thin'), bottom=Side('thin'))
            for r in ws.iter_rows():
                for c in r:
                    if c.value is not None: c.border = b
            for col in ws.columns:
                ml = max((len(str(c.value)) for c in col if c.value), default=0)
                ws.column_dimensions[col[0].column_letter].width = min(ml + 2, 50)

    def _remove_cell_borders(self, cell):
        try:
            tc = cell._element
            tcPr = tc.tcPr or OxmlElement('w:tcPr') or tc.append(OxmlElement('w:tcPr'))
            borders = tcPr.find(qn('w:tcBorders')) or tcPr.append(OxmlElement('w:tcBorders'))
            for n in ['top', 'left', 'bottom', 'right', 'insideH', 'insideV']:
                b = borders.find(qn(f'w:{n}'))
                if b is not None: borders.remove(b)
        except:
            pass

    def export_to_word(self, df, filepath, query_text="", selected_columns=None, template_path=None):
        from docx.enum.section import WD_SECTION, WD_ORIENT
        if selected_columns: df = df[selected_columns]
        doc = Document()
        s = doc.sections[0];
        s.page_height = Cm(29.7);
        s.page_width = Cm(21);
        s.top_margin = Cm(2);
        s.bottom_margin = Cm(2);
        s.left_margin = Cm(3);
        s.right_margin = Cm(1.5)
        ht = doc.add_table(1, 2);
        ht.autofit = False;
        ht.columns[0].width = Cm(4);
        ht.columns[1].width = Cm(13)
        ch = ht.cell(0, 0);
        ch.vertical_alignment = WD_ALIGN_PARAGRAPH.CENTER
        for p in ch.paragraphs: p.clear()
        p1 = ch.paragraphs[0];
        p1.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r1 = p1.add_run(
            "МИНИСТЕРСТВО ОБОРОНЫ\nРОССИЙСКОЙ ФЕДЕРАЦИИ\n(МИНОБОРОНЫ РОССИИ)\nВОЕННО-МЕДИЦИНСКАЯ АКАДЕМИЯ\nг. Санкт-Петербург, ул. Академика Лебедева, д.6, 194044")
        r1.font.name = 'Times New Roman';
        r1.font.size = Pt(12);
        r1.bold = True
        for row in ht.rows:
            for cell in row.cells: self._remove_cell_borders(cell)
        doc.add_paragraph().paragraph_format.space_after = Pt(18)
        h = doc.add_paragraph();
        h.alignment = WD_ALIGN_PARAGRAPH.CENTER;
        rh = h.add_run("Справка.");
        rh.font.name = 'Times New Roman';
        rh.font.size = Pt(14);
        rh.bold = True;
        h.paragraph_format.space_after = Pt(12)
        i = doc.add_paragraph();
        i.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY;
        i.paragraph_format.line_spacing = 1.15
        ri = i.add_run(
            f"В ответ на Ваш запрос представляем информацию о диссертационных работах, соответствующих следующим критериям: {query_text}." if query_text else "В ответ на Ваш запрос представляем информацию о диссертационных работах.")
        ri.font.name = 'Times New Roman';
        ri.font.size = Pt(12);
        i.paragraph_format.space_after = Pt(12)
        ar = doc.add_paragraph();
        ar.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY;
        ar.paragraph_format.line_spacing = 1.15;
        ar.paragraph_format.space_after = Pt(18)
        ra = ar.add_run(
            "Сведения о диссертационных работах приведены в Приложении на ____ листе(ах) в алфавитном порядке.")
        ra.font.name = 'Times New Roman';
        ra.font.size = Pt(12)
        doc.add_paragraph().paragraph_format.space_after = Pt(36)
        st = doc.add_table(2, 2);
        st.autofit = False;
        st.columns[0].width = Cm(12);
        st.columns[1].width = Cm(5)
        st.cell(0, 0).text = "Начальник отдела по работе с диссертационными советами"
        st.cell(1, 0).text = "врач-методист"
        sn = st.cell(1, 1);
        sn.text = "Стеганцев И.В."
        for p in sn.paragraphs: p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        for row in st.rows:
            for cell in row.cells: self._remove_cell_borders(cell)
        doc.add_paragraph().paragraph_format.space_after = Pt(12)
        dp = doc.add_paragraph();
        dp.alignment = WD_ALIGN_PARAGRAPH.LEFT;
        dr = dp.add_run(datetime.now().strftime("%d.%m.%Y"));
        dr.font.name = 'Times New Roman';
        dr.font.size = Pt(11)
        if not df.empty:
            doc.add_page_break()
            ns = doc.add_section(WD_SECTION.NEW_PAGE);
            ns.orientation = WD_ORIENT.LANDSCAPE;
            ns.page_width = Cm(29.7);
            ns.page_height = Cm(21);
            ns.top_margin = Cm(1.5);
            ns.bottom_margin = Cm(1.5);
            ns.left_margin = Cm(1.5);
            ns.right_margin = Cm(1.5)
            ah = doc.add_paragraph();
            ah.alignment = WD_ALIGN_PARAGRAPH.CENTER;
            rht = ah.add_run("ПРИЛОЖЕНИЕ");
            rht.font.name = 'Times New Roman';
            rht.font.size = Pt(14);
            rht.bold = True;
            ah.paragraph_format.space_after = Pt(6)
            ash = doc.add_paragraph();
            ash.alignment = WD_ALIGN_PARAGRAPH.CENTER;
            rs = ash.add_run("Сведения о диссертационных работах");
            rs.font.name = 'Times New Roman';
            rs.font.size = Pt(12);
            ash.paragraph_format.space_after = Pt(18)
            dc = [c for c in df.columns if c != '_original_index']
            tbl = doc.add_table(1, len(dc));
            tbl.style = 'Table Grid';
            tbl.autofit = False
            cw = {'ФИО': Cm(4), 'Диссертационный совет': Cm(3.5), 'Название диссертации': Cm(7),
                  'Дата защиты диссертации': Cm(2.5), 'Специальность': Cm(3),
                  '1 Научный руководитель (консультант)': Cm(4), '2 Научный руководитель (консультант)': Cm(4),
                  'Год защиты': Cm(1.5), 'Искомая степень': Cm(3.5), 'Информация о лишении степени': Cm(4),
                  'Примечания': Cm(4)}
            for i, c in enumerate(dc):
                tbl.rows[0].cells[i].text = c
                for p in tbl.rows[0].cells[
                    i].paragraphs: p.alignment = WD_ALIGN_PARAGRAPH.CENTER; p.paragraph_format.space_after = Pt(2)
                for r in p.runs: r.font.name = 'Times New Roman'; r.font.size = Pt(9); r.bold = True
                tbl.rows[0].cells[i].width = cw.get(c, Cm(3))
            for _, row in df.iterrows():
                rc = tbl.add_row().cells
                for i, c in enumerate(dc):
                    v = row[c];
                    t = str(v) if pd.notna(v) and str(v).strip() != '' else '–'
                    rc[i].text = t
                    for p in rc[
                        i].paragraphs: p.alignment = WD_ALIGN_PARAGRAPH.LEFT; p.paragraph_format.space_after = Pt(2)
                    for r in p.runs: r.font.name = 'Times New Roman'; r.font.size = Pt(9)
                    if c in ['Название диссертации', 'Примечания', 'Информация о лишении степени']: rc[i].paragraphs[
                        0].paragraph_format.word_wrap = True
            fn = doc.add_paragraph();
            fn.alignment = WD_ALIGN_PARAGRAPH.LEFT;
            fn.paragraph_format.space_after = Pt(6);
            rf = fn.add_run(f"Всего записей: {len(df)}");
            rf.font.name = 'Times New Roman';
            rf.font.size = Pt(10);
            rf.italic = True
        doc.save(filepath)


# =============================================================================
# ДИАЛОГИ
# =============================================================================
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


# =============================================================================
# ГЛАВНОЕ ОКНО
# =============================================================================
class DissertationReportApp:
    def __init__(self, root):
        self.root = root;
        self.root.title("Автоматизированная система учёта диссертаций | ВМедА им. С.М. Кирова");
        self.root.geometry("1300x700");
        self.root.configure(bg="#0b2a1b")
        self.config = self.load_config();
        self.setup_logging()
        self.user_manager = UserManager(self.config);
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
                config = json.load(f)
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

    def backup_data(self):
        if not self.data_model.data.empty:
            bp = os.path.join(self.config["backup_dir"], f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
            self.data_model.data.to_csv(bp, index=False, encoding='utf-8');
            self.log_action(f"Бэкап: {bp}")

    def save_persisted_data(self):
        if not self.data_model.data.empty: self.data_model.data.to_csv(self.config["persistence_file"], index=False,
                                                                       encoding='utf-8')

    def load_persisted_data(self):
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
        self.bg_main = "#0b2a1b";
        self.bg_panel = "#1a3d2a";
        self.fg_text = "#ffffff";
        self.accent = "#d4af37";
        self.table_bg = "#f8f4e9";
        self.table_fg = "#000000"
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
        bs = {"bg": self.accent, "fg": "black", "font": ("Times New Roman", 10, "bold"), "activebackground": "#b89b2e",
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
        style = ttk.Style();
        style.theme_use(self.config["theme"])
        style.configure("Treeview", background=self.table_bg, foreground=self.table_fg, fieldbackground=self.table_bg,
                        font=("Times New Roman", 10), rowheight=25)
        style.configure("Treeview.Heading", background=self.bg_panel, foreground=self.accent,
                        font=("Times New Roman", 10, "bold"))
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
        self.root.destroy()

    def process_queue(self):
        try:
            while True: self.task_queue.get_nowait()()
        except queue.Empty:
            pass
        self.root.after(100, self.process_queue)


if __name__ == "__main__":
    root = tk.Tk()
    style = ttk.Style()
    if "clam" in style.theme_names(): style.theme_use("clam")
    app = DissertationReportApp(root)
    root.mainloop()
