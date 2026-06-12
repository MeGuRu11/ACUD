from pathlib import Path

from ASUD import UserManager, check_password
from asud.storage import SQLiteStorage


def make_user_manager(tmp_path: Path) -> UserManager:
    return UserManager({"users_file": str(tmp_path / "users.json")})


def test_user_manager_does_not_create_default_admin_password(tmp_path):
    manager = make_user_manager(tmp_path)

    assert manager.users == {}


def test_create_initial_admin_validates_password_and_persists(tmp_path):
    manager = make_user_manager(tmp_path)

    ok, message = manager.create_initial_admin("admin", "short", "Administrator")
    assert not ok
    assert message == "Мин. 8 символов"

    ok, message = manager.create_initial_admin("admin", "Adminpass1", "Administrator")

    assert ok, message
    assert manager.users["admin"]["role"] == "admin"
    assert check_password("Adminpass1", manager.users["admin"]["password_hash"])


def test_change_password_requires_current_password_for_regular_user(tmp_path):
    manager = make_user_manager(tmp_path)
    ok, message = manager.add_user(
        "editor1",
        "Oldpass1",
        "editor",
        "Editor User",
    )
    assert ok, message

    ok, message = manager.change_password(
        "editor1",
        "",
        "Newpass1",
        require_old=True,
    )

    assert not ok
    assert message == "Введите текущий пароль"
    assert check_password("Oldpass1", manager.users["editor1"]["password_hash"])


def test_admin_self_password_change_requires_current_password(tmp_path):
    manager = make_user_manager(tmp_path)
    ok, message = manager.create_initial_admin("admin", "Adminpass1", "Administrator")
    assert ok, message

    ok, message = manager.change_password(
        "admin",
        "",
        "Newpass1",
        require_old=True,
    )

    assert not ok
    assert message == "Введите текущий пароль"
    assert check_password("Adminpass1", manager.users["admin"]["password_hash"])


def test_user_manager_can_persist_users_in_sqlite(tmp_path):
    config = {"users_file": str(tmp_path / "users.json")}
    storage = SQLiteStorage(tmp_path / "asud.sqlite3")
    manager = UserManager(config, storage=storage)

    ok, message = manager.add_user("viewer1", "Viewerpass1", "viewer", "Viewer User")
    assert ok, message
    storage.close()

    reloaded_storage = SQLiteStorage(tmp_path / "asud.sqlite3")
    reloaded = UserManager(config, storage=reloaded_storage)

    assert "viewer1" in reloaded.users
    assert reloaded.users["viewer1"]["role"] == "viewer"
    reloaded_storage.close()
