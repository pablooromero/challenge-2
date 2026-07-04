from dataclasses import dataclass


@dataclass
class SeriesPoint:
    period: str
    raw_value: float
    adjusted_value: float
    is_outlier: bool


def month_after(period: str) -> str:
    year, month = map(int, period.split("-"))
    if month == 12:
        return f"{year + 1}-01"
    return f"{year:04d}-{month + 1:02d}"


def period_month(period: str) -> int:
    return int(period.split("-")[1])
