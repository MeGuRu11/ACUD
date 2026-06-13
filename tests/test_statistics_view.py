from pathlib import Path

import pandas as pd

from asud.ui.app import DissertationReportApp


def test_build_year_statistics_counts_sorted_years_and_summary():
    app = DissertationReportApp.__new__(DissertationReportApp)
    df = pd.DataFrame(
        {
            "Год защиты": [2023, 2020, 2023, 2024, 2021, None],
            "ФИО": ["a", "b", "c", "d", "e", "skip"],
        }
    )

    stats = app.build_year_statistics(df)

    assert stats["counts"].to_dict() == {2020: 1, 2021: 1, 2023: 2, 2024: 1}
    assert stats["total"] == 5
    assert stats["period"] == "2020-2024"
    assert stats["peak_year"] == 2023
    assert stats["peak_count"] == 2


def test_statistics_window_source_has_redesigned_informative_chart():
    source = Path("asud/ui/app.py").read_text(encoding="utf-8")

    assert "build_year_statistics" in source
    assert "create_statistics_card" in source
    assert "create_year_statistics_chart" in source
    assert "Количество работ" in source
    assert 'ax.set_xlabel("Год")' in source
    assert 'ax.set_ylabel("Количество работ")' in source
    assert "MaxNLocator(integer=True)" in source
    assert "motion_notify_event" in source
    assert "contains(event)" in source
    assert "работ" in source
    assert "Пиковый год" in source
    assert "Всего работ" in source
