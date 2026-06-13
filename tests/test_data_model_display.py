import math

import pandas as pd

from asud.data_model import DataModel


def test_format_display_value_hides_empty_placeholders():
    model = DataModel({})

    for value in [None, pd.NA, float("nan"), "nan", "NaN", "None", "<NA>", "NaT", "  "]:
        assert model.format_display_value(value) == ""

    assert model.format_display_value("-") == "-"
    assert model.format_display_value("Иванов И.И.") == "Иванов И.И."
    assert model.format_display_value(2024) == "2024"


def test_clean_missing_values_removes_string_placeholders_from_dataframe():
    model = DataModel({})
    df = pd.DataFrame(
        [
            {
                "ФИО": "Иванов И.И.",
                "Примечания": "nan",
                "Информация о лишении степени": "None",
                "Искомая степень": math.nan,
            }
        ]
    )

    clean = model.clean_missing_values(df)

    assert clean.loc[0, "Примечания"] == ""
    assert clean.loc[0, "Информация о лишении степени"] == ""
    assert clean.loc[0, "Искомая степень"] == ""


def test_update_record_can_clear_values_when_explicitly_allowed():
    model = DataModel({})
    model.data = pd.DataFrame([{"ФИО": "Иванов И.И.", "Примечания": "старое"}])
    model.apply_filters()

    model.update_record(0, {"Примечания": ""}, allow_empty_update=True)

    assert model.data.loc[0, "Примечания"] == ""
