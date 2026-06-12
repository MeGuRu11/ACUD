from pathlib import Path

from ASUD import UserManager, check_password


def make_user_manager(tmp_path: Path) -> UserManager:
    return UserManager({"users_file": str(tmp_path / "users.json")})


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

    ok, message = manager.change_password(
        "admin",
        "",
        "Newpass1",
        require_old=True,
    )

    assert not ok
    assert message == "Введите текущий пароль"
    assert check_password("admin", manager.users["admin"]["password_hash"])
