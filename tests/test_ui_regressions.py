import ast
from pathlib import Path


def test_users_button_is_stored_for_permission_updates():
    tree = ast.parse(Path("asud/ui/app.py").read_text(encoding="utf-8"))

    assigned_self_attrs = {
        node.targets[0].attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Assign)
        and node.targets
        and isinstance(node.targets[0], ast.Attribute)
        and isinstance(node.targets[0].value, ast.Name)
        and node.targets[0].value.id == "self"
    }

    assert "btn_users" in assigned_self_attrs


def test_login_flow_runs_initial_admin_setup_when_user_store_is_empty():
    app_source = Path("asud/ui/app.py").read_text(encoding="utf-8")

    assert "InitialAdminDialog" in app_source
    assert "has_users()" in app_source


def test_table_has_explicit_empty_states():
    app_source = Path("asud/ui/app.py").read_text(encoding="utf-8")

    assert "display_empty_state" in app_source
    assert "Данные не загружены" in app_source
    assert "По фильтру ничего не найдено" in app_source


def test_exports_run_in_background_task():
    app_source = Path("asud/ui/app.py").read_text(encoding="utf-8")

    assert "run_export_task" in app_source
    assert "threading.Thread(target=worker, daemon=True).start()" in app_source
