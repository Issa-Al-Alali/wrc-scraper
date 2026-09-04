from collections.abc import Iterator
from datetime import date, timedelta

PartitionSize = str  # "weekly" | "monthly" | "quarterly"


def _next_month(d: date) -> date:
    if d.month == 12:
        return date(d.year + 1, 1, 1)
    return date(d.year, d.month + 1, 1)


def _next_quarter(d: date) -> date:
    quarter_start_month = ((d.month - 1) // 3) * 3 + 1
    d = date(d.year, quarter_start_month, 1)
    for _ in range(3):
        d = _next_month(d)
    return d


def generate_partitions(
    start_date: date, end_date: date, size: PartitionSize = "monthly"
) -> Iterator[tuple[date, date, str]]:
    """Yield (partition_start, partition_end, partition_label) tuples covering
    [start_date, end_date). partition_end is exclusive."""
    if start_date >= end_date:
        return

    if size == "weekly":
        cursor = start_date
        while cursor < end_date:
            nxt = min(cursor + timedelta(days=7), end_date)
            label = cursor.isoformat()
            yield cursor, nxt, label
            cursor = nxt

    elif size == "monthly":
        cursor = date(start_date.year, start_date.month, 1)
        while cursor < end_date:
            nxt = _next_month(cursor)
            label = cursor.strftime("%Y-%m")
            yield max(cursor, start_date), min(nxt, end_date), label
            cursor = nxt

    elif size == "quarterly":
        quarter_start_month = ((start_date.month - 1) // 3) * 3 + 1
        cursor = date(start_date.year, quarter_start_month, 1)
        while cursor < end_date:
            nxt = _next_quarter(cursor)
            quarter = (cursor.month - 1) // 3 + 1
            label = f"{cursor.year}-Q{quarter}"
            yield max(cursor, start_date), min(nxt, end_date), label
            cursor = nxt

    else:
        raise ValueError(f"Unknown partition size: {size!r}")