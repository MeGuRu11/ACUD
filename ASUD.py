#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Compatibility launcher for the ASUD desktop application."""

from asud.auth import UserManager, check_password, hash_password
from asud.config import CONFIG_FILE, DEFAULT_CONFIG, DEGREE_OPTIONS, REQUIRED_COLUMNS
from asud.data_model import DataModel
from asud.main import main
from asud.reports import ReportGenerator
from asud.ui.app import DissertationReportApp
from asud.ui.dialogs import (
    AddUserDialog,
    ChangePasswordDialog,
    ColumnSelectorDialog,
    EditUserDialog,
    FilterDialog,
    InitialAdminDialog,
    LoginDialog,
    RecordDialog,
    RegistrationDialog,
    UserManagementDialog,
)

__all__ = [
    "AddUserDialog",
    "CONFIG_FILE",
    "ChangePasswordDialog",
    "ColumnSelectorDialog",
    "DEFAULT_CONFIG",
    "DEGREE_OPTIONS",
    "DataModel",
    "DissertationReportApp",
    "EditUserDialog",
    "FilterDialog",
    "InitialAdminDialog",
    "LoginDialog",
    "REQUIRED_COLUMNS",
    "RecordDialog",
    "RegistrationDialog",
    "ReportGenerator",
    "UserManagementDialog",
    "UserManager",
    "check_password",
    "hash_password",
    "main",
]


if __name__ == "__main__":
    main()
