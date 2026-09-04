from datetime import date

from common.partitioning import generate_partitions


def test_monthly_partitions_span_full_range():
    parts = list(generate_partitions(date(2024, 1, 15), date(2024, 4, 1), "monthly"))
    labels = [label for _, _, label in parts]
    assert labels == ["2024-01", "2024-02", "2024-03"]
    assert parts[0][0] == date(2024, 1, 15)  # clamped to start_date
    assert parts[0][1] == date(2024, 2, 1)
    assert parts[-1][1] == date(2024, 4, 1)


def test_monthly_partitions_single_full_month():
    parts = list(generate_partitions(date(2024, 3, 1), date(2024, 4, 1), "monthly"))
    assert parts == [(date(2024, 3, 1), date(2024, 4, 1), "2024-03")]


def test_weekly_partitions():
    parts = list(generate_partitions(date(2024, 1, 1), date(2024, 1, 15), "weekly"))
    assert len(parts) == 2
    assert parts[0] == (date(2024, 1, 1), date(2024, 1, 8), "2024-01-01")
    assert parts[1][1] == date(2024, 1, 15)


def test_quarterly_partitions():
    parts = list(generate_partitions(date(2024, 1, 1), date(2024, 7, 1), "quarterly"))
    labels = [label for _, _, label in parts]
    assert labels == ["2024-Q1", "2024-Q2"]


def test_empty_range_yields_nothing():
    assert list(generate_partitions(date(2024, 1, 1), date(2024, 1, 1), "monthly")) == []


def test_unknown_size_raises():
    import pytest

    with pytest.raises(ValueError):
        list(generate_partitions(date(2024, 1, 1), date(2024, 2, 1), "daily"))