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


def test_delete_records_removes_multiple_original_indexes_at_once():
    model = DataModel({})
    model.data = pd.DataFrame(
        [
            {"name": "first", "year": 2020},
            {"name": "second", "year": 2021},
            {"name": "third", "year": 2022},
            {"name": "fourth", "year": 2023},
        ]
    )
    model.apply_filters()

    deleted = model.delete_records([1, 3])

    assert deleted == 2
    assert model.data["name"].tolist() == ["first", "third"]
    assert model.data.index.tolist() == [0, 1]
    assert "_original_index" in model.filtered_data.columns
