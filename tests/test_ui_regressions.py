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


def test_process_queue_after_callback_is_cancelled_on_close():
    app_source = Path("asud/ui/app.py").read_text(encoding="utf-8")

    assert "self.is_closing" in app_source
    assert "self.queue_after_id" in app_source
    assert "self.login_after_id" in app_source
    assert 'self.root.protocol("WM_DELETE_WINDOW", self.on_closing)' in app_source
    assert "after_cancel(self.queue_after_id)" in app_source
    assert "after_cancel(self.login_after_id)" in app_source
    assert "self.schedule_process_queue()" in app_source
    assert "self.schedule_login()" in app_source


def test_main_window_is_maximized_after_successful_login():
    app_source = Path("asud/ui/app.py").read_text(encoding="utf-8")

    assert "maximize_main_window" in app_source
    assert "self.maximize_main_window()" in app_source
    assert 'state("zoomed")' in app_source


def test_table_column_widths_are_readable_for_domain_columns():
    from asud.ui.app import DissertationReportApp

    app = DissertationReportApp.__new__(DissertationReportApp)
    app.config = {"default_columns_width": 120}

    widths = app.get_table_column_widths(
        [
            "Год защиты",
            "ФИО",
            "Название диссертации",
            "Диссертационный совет",
            "Дата защиты диссертации",
            "Специальность",
            "Искомая степень",
            "Информация о лишении степени",
            "Примечания",
        ]
    )

    assert widths["Год защиты"] >= 96
    assert widths["ФИО"] >= 220
    assert widths["Название диссертации"] >= 340
    assert widths["Информация о лишении степени"] >= 260
    assert widths["Примечания"] >= 240


def test_table_and_detail_view_use_clean_display_values():
    app_source = Path("asud/ui/app.py").read_text(encoding="utf-8")

    assert "format_display_value" in app_source
    assert "show_record_detail_view" in app_source
    assert "save_record_detail_changes" in app_source
    assert 'self.tree.bind("<Double-1>", self.open_selected_record_view)' in app_source
    assert 'self.tree.bind("<Return>", self.open_selected_record_view)' in app_source


def test_sidebar_uses_record_card_for_editing_without_separate_edit_button():
    app_source = Path("asud/ui/app.py").read_text(encoding="utf-8")
    sidebar_source = app_source[app_source.index("def build_sidebar"):app_source.index("def add_nav_group")]

    assert '"Открыть запись"' in sidebar_source
    assert '"Редактировать"' not in sidebar_source
    assert "self.btn_edit" not in app_source
    assert "edit_selected" not in app_source
    assert "<Control-e>" not in app_source


def test_record_detail_view_uses_sectioned_polished_layout():
    app_source = Path("asud/ui/app.py").read_text(encoding="utf-8")

    assert "get_record_detail_sections" in app_source
    assert "create_record_detail_section" in app_source
    assert "create_record_detail_field" in app_source
    assert "create_record_meta_badge" in app_source
    assert "Основные сведения" in app_source
    assert "Научное сопровождение" in app_source
    assert "Служебная информация" in app_source
    assert "detail_footer" in app_source
    assert "detail_canvas" in app_source


def test_detail_and_statistics_windows_have_explicit_window_placement():
    app_source = Path("asud/ui/app.py").read_text(encoding="utf-8")

    assert "center_toplevel_window" in app_source
    assert "self.center_toplevel_window(detail" in app_source
    assert "maximize_toplevel_window" in app_source
    assert "self.maximize_toplevel_window(sw)" in app_source


def test_pyinstaller_bundle_asset_resolution_is_supported():
    app_source = Path("asud/ui/app.py").read_text(encoding="utf-8")
    dialogs_source = Path("asud/ui/dialogs.py").read_text(encoding="utf-8")

    assert "sys._MEIPASS" in app_source
    assert "sys._MEIPASS" in dialogs_source
