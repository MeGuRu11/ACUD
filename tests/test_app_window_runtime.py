import tkinter as tk

import pytest

from asud.ui.app import DissertationReportApp


def test_center_root_window_places_main_window_near_screen_center():
    try:
        root = tk.Tk()
    except tk.TclError as exc:
        pytest.skip(f"Tk is not available: {exc}")
    root.withdraw()
    app = DissertationReportApp.__new__(DissertationReportApp)
    app.root = root

    try:
        app.center_root_window(900, 600)
        root.update_idletasks()
        geometry = root.geometry()
        width = root.winfo_width()
        height = root.winfo_height()
        x = root.winfo_x()
        y = root.winfo_y()
        expected_x = (root.winfo_screenwidth() - width) // 2
        expected_y = (root.winfo_screenheight() - height) // 2

        assert width == 900, geometry
        assert height == 600, geometry
        assert abs(x - expected_x) <= 2, geometry
        assert abs(y - expected_y) <= 2, geometry
    finally:
        root.destroy()
