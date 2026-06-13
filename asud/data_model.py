"""In-memory dissertation data model and filtering logic."""

import re
from datetime import datetime

import pandas as pd

from .config import REQUIRED_COLUMNS


MISSING_TEXT_VALUES = {"", "none", "nan", "<na>", "nat", "null"}


class DataModel:
    def __init__(self, config):
        self.config = config
        self.data = pd.DataFrame()
        self.filtered_data = pd.DataFrame()
        self.filters = []
        self.sort_column = None
        self.sort_reverse = False
        self.smart_search_query = ""

    @staticmethod
    def is_missing_value(value):
        if value is None:
            return True
        try:
            if pd.isna(value):
                return True
        except (TypeError, ValueError):
            pass
        return isinstance(value, str) and value.strip().lower() in MISSING_TEXT_VALUES

    @classmethod
    def format_display_value(cls, value):
        if cls.is_missing_value(value):
            return ""
        return str(value).strip() if isinstance(value, str) else str(value)

    @classmethod
    def clean_missing_values(cls, df):
        clean = df.copy()
        for column in clean.columns:
            clean[column] = clean[column].map(lambda value: "" if cls.is_missing_value(value) else value)
        return clean

    def _safe_convert_value(self, col, val):
        if self.is_missing_value(val): return pd.NA
        if col in self.data.columns:
            d = str(self.data[col].dtype)
            if 'Int64' in d:
                try:
                    return int(val)
                except (TypeError, ValueError):
                    return pd.NA
            elif 'Float64' in d:
                try:
                    return float(val)
                except (TypeError, ValueError):
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
        df = self.clean_missing_values(df)
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
        df = self.clean_missing_values(df)
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
            except (TypeError, ValueError):
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

    def update_record(self, index, new_values, allow_empty_update=False):
        for col, val in new_values.items():
            if col not in self.data.columns or col == '_original_index': continue
            cur = self.data.at[index, col] if index in self.data.index else None
            is_empty = self.is_missing_value(val)
            if is_empty and not allow_empty_update and pd.notna(cur) and str(cur).strip() != '': continue
            sv = self._safe_convert_value(col, val)
            if allow_empty_update and self.is_missing_value(sv):
                sv = ""
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
            return {k: self.format_display_value(v) for k, v in row.to_dict().items()}
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
