from pathlib import Path

import pandas as pd

from asud.config import REQUIRED_COLUMNS
from asud.data_model import DataModel


def test_app_svg_icon_exists_and_contains_brand_shapes():
    icon = Path("assets/asud_icon.svg")

    assert icon.exists()
    source = icon.read_text(encoding="utf-8")
    assert "<svg" in source
    assert "АСУД" in source
    assert "linearGradient" in source
    assert "shield" in source


def test_sample_excel_can_be_loaded_by_data_model():
    sample = Path("examples/Тестовые_данные_АСУД.xlsx")

    assert sample.exists()
    df = pd.read_excel(sample, dtype=str)
    assert list(df.columns) == REQUIRED_COLUMNS
    assert len(df) >= 5

    model = DataModel({"default_columns_width": 120})
    assert model.load_excel(sample) is True
    assert not model.data.empty
    assert "Год защиты" in model.data.columns
