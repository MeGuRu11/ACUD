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


def test_filter_year_statistics_by_min_count_rebuilds_summary():
    app = DissertationReportApp.__new__(DissertationReportApp)
    stats = app.build_year_statistics(
        pd.DataFrame(
            {
                "Год защиты": [2020, 2021, 2021, 2022, 2023, 2023, 2023],
                "ФИО": list("abcdefg"),
            }
        )
    )

    filtered = app.filter_year_statistics_by_min_count(stats, 2)

    assert filtered["counts"].to_dict() == {2021: 2, 2023: 3}
    assert filtered["total"] == 5
    assert filtered["period"] == "2021-2023"
    assert filtered["peak_year"] == 2023
    assert filtered["peak_count"] == 3


def test_statistics_chart_size_changes_with_bar_count():
    app = DissertationReportApp.__new__(DissertationReportApp)

    compact = app.calculate_statistics_chart_size(2)
    wide = app.calculate_statistics_chart_size(9)

    assert compact[0] < wide[0]
    assert compact[1] == wide[1]


def test_filter_statistics_dataframe_combines_year_degree_and_text_query():
    app = DissertationReportApp.__new__(DissertationReportApp)
    df = pd.DataFrame(
        {
            "Год защиты": [2020, 2021, 2022, 2023, 2024],
            "Искомая степень": [
                "кандидат медицинских наук",
                "доктор медицинских наук",
                "кандидат медицинских наук",
                "кандидат медицинских наук",
                "кандидат медицинских наук",
            ],
            "Название диссертации": [
                "кардиология",
                "хирургия",
                "военная хирургия",
                "терапия",
                "хирургия",
            ],
            "ФИО": ["a", "b", "c", "d", "e"],
        }
    )

    filtered = app.filter_statistics_dataframe(
        df,
        {
            "year_from": "2021",
            "year_to": "2024",
            "degree": "кандидат медицинских наук",
            "query": "хирург",
            "min_count": "1",
            "max_count": "1",
        },
    )

    assert filtered["ФИО"].tolist() == ["c", "e"]


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
    assert "Минимум работ за год" in source
    assert "Максимум работ за год" in source
    assert "Искомая степень" in source
    assert "Поиск в статистике" in source
    assert "refresh_statistics_view" in source
