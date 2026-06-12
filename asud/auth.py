"""User management and password hashing."""

import hashlib
import json
import os
import re
import secrets
from datetime import datetime

try:
    import bcrypt

    BCRYPT_AVAILABLE = True
except ImportError:
    BCRYPT_AVAILABLE = False


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


class UserManager:
    def __init__(self, config, storage=None):
        self.config = config
        self.users_file = config["users_file"]
        self.storage = storage
        self.current_user = None
        self.load_users()

    def load_users(self):
        if self.storage is not None:
            self.users = self.storage.load_users()
            if self.users:
                self._ensure_user_defaults()
                self.save_users()
            else:
                self._create_default_admin()
            return

        if os.path.exists(self.users_file):
            try:
                with open(self.users_file, "r", encoding="utf-8") as f:
                    self.users = json.load(f)
                self._ensure_user_defaults()
                self.save_users()
            except (json.JSONDecodeError, IOError):
                self._create_default_admin()
        else:
            self._create_default_admin()

    def _ensure_user_defaults(self):
        for username, data in self.users.items():
            for k, v in {"full_name": username, "created_at": datetime.now().isoformat(), "last_login": None,
                         "force_password_change": False}.items():
                data.setdefault(k, v)

    def _create_default_admin(self):
        self.users = {"admin": {"password_hash": hash_password("admin"), "role": "admin", "full_name": "Администратор",
                                "created_at": datetime.now().isoformat(), "last_login": None,
                                "force_password_change": True}}
        self.save_users()

    def save_users(self):
        if self.storage is not None:
            self.storage.save_users(self.users)
            return
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
