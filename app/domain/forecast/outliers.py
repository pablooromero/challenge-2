from statistics import quantiles

from app.domain.forecast.series import SeriesPoint


def compute_iqr_bounds(values: list[float]) -> tuple[float | None, float | None]:
    if len(values) < 4:
        return None, None
    q1, _, q3 = quantiles(values, n=4, method="inclusive")
    iqr = q3 - q1
    return q1 - (1.5 * iqr), q3 + (1.5 * iqr)


def attenuate_series(rows: list, metric: str) -> list[SeriesPoint]:
    values = [float(getattr(row, metric)) for row in rows]
    lower, upper = compute_iqr_bounds(values)

    points: list[SeriesPoint] = []
    for row in rows:
        raw_value = float(getattr(row, metric))
        is_outlier = False
        adjusted_value = raw_value

        if lower is not None and upper is not None:
            if raw_value < lower:
                adjusted_value = lower
                is_outlier = True
            elif raw_value > upper:
                adjusted_value = upper
                is_outlier = True

        points.append(
            SeriesPoint(
                period=row.period,
                raw_value=raw_value,
                adjusted_value=adjusted_value,
                is_outlier=is_outlier,
            )
        )
    return points
