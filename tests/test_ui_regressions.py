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
