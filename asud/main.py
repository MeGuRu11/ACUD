"""Application entry point."""

import tkinter as tk
from tkinter import ttk

from asud.ui.app import DissertationReportApp


def main() -> None:
    root = tk.Tk()
    style = ttk.Style()
    if "clam" in style.theme_names():
        style.theme_use("clam")
    DissertationReportApp(root)
    root.mainloop()
