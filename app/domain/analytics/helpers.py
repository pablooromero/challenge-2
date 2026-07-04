from decimal import Decimal


def to_int(value: int | Decimal | None) -> int:
    if value is None:
        return 0
    return int(value)


def to_float(value: float | Decimal | None) -> float:
    if value is None:
        return 0.0
    return float(value)


def safe_divide(numerator: float, denominator: float) -> float:
    if denominator == 0:
        return 0.0
    return numerator / denominator


def calculate_ctr(clicks: int, impressions: int) -> float:
    return round(safe_divide(clicks, impressions), 4)


def calculate_cpl(cost: float, leads: int) -> float:
    return round(safe_divide(cost, leads), 2)


def calculate_cpa(cost: float, sales: int) -> float:
    return round(safe_divide(cost, sales), 2)


def calculate_roas(revenue: float, cost: float) -> float:
    return round(safe_divide(revenue, cost), 2)


def calculate_conversion_rate(sales: int, leads: int) -> float:
    return round(safe_divide(sales, leads), 4)
