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


def test_main_window_uses_redesigned_shell_sections():
    app_source = Path("asud/ui/app.py").read_text(encoding="utf-8")

    assert "build_topbar" in app_source
    assert "build_sidebar" in app_source
    assert "build_workbench" in app_source
    assert "Реестр диссертаций" in app_source
    assert "База данных активна" in app_source
    assert "Загрузить Excel" in app_source
    assert "Новая запись" in app_source


def test_main_window_uses_shared_theme_not_legacy_fonts():
    app_source = Path("asud/ui/app.py").read_text(encoding="utf-8")

    assert 'APP_THEME["topbar"]' in app_source
    assert 'FONT["family"]' in app_source
    assert "Times New Roman" not in app_source


def test_ui_uses_clear_workflow_status_texts():
    app_source = Path("asud/ui/app.py").read_text(encoding="utf-8")

    assert "Данные сохранены" in app_source
    assert "Данные сохранены в Базе Данных" in app_source
    assert "Данные сохранены в SQLite" not in app_source
    assert "Загрузка Excel" in app_source
    assert "Экспорт отчёта" in app_source
    assert "По фильтру ничего не найдено" in app_source


def test_main_window_uses_centering_and_app_icon():
    app_source = Path("asud/ui/app.py").read_text(encoding="utf-8")

    assert "APP_ICON_PNG" in app_source
    assert "set_app_icon" in app_source
    assert "center_root_window" in app_source
    assert "self.center_root_window" in app_source


def test_topbar_uses_app_icon_instead_of_text_badge():
    app_source = Path("asud/ui/app.py").read_text(encoding="utf-8")

    assert "load_brand_icon" in app_source
    assert "brand_icon_label" in app_source
    assert "APP_ICON_PNG" in app_source
    assert "PhotoImage(file=" in app_source
    assert 'text="АС",' not in app_source
