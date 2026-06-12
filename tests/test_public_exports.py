def test_asud_module_keeps_public_classes_importable():
    from ASUD import DataModel, DissertationReportApp, ReportGenerator, UserManager

    assert UserManager.__name__ == "UserManager"
    assert DataModel.__name__ == "DataModel"
    assert ReportGenerator.__name__ == "ReportGenerator"
    assert DissertationReportApp.__name__ == "DissertationReportApp"
