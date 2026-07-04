from app.domain.analytics.breakdowns import get_monthly_aggregates
from app.domain.forecast.outliers import attenuate_series
from app.domain.forecast.series import SeriesPoint, month_after, period_month
from app.schemas.analytics import AnalyticsMeta
from app.schemas.forecast import ForecastHistoryPoint, ForecastProjection, ForecastResult

TREND_WEIGHT = 0.7
SEASONAL_WEIGHT = 0.3
RECENT_WEIGHTS = (0.5, 0.3, 0.2)


def weighted_average(values: list[float]) -> float:
    if not values:
        return 0.0
    if len(values) >= 3:
        recent = values[-3:]
        weights = RECENT_WEIGHTS
    else:
        recent = values
        weights = RECENT_WEIGHTS[: len(recent)]

    weight_total = sum(weights)
    return sum(value * weight for value, weight in zip(recent, weights)) / weight_total


def seasonal_reference(points: list[SeriesPoint], target_period: str) -> tuple[float | None, str | None]:
    target_month = period_month(target_period)
    matching = [point for point in points if period_month(point.period) == target_month]
    if not matching:
        return None, None
    reference = matching[-1]
    return reference.adjusted_value, reference.period


def build_projection(metric: str, points: list[SeriesPoint], target_period: str) -> ForecastProjection:
    adjusted_values = [point.adjusted_value for point in points]
    trend_component = round(weighted_average(adjusted_values), 2)
    seasonal_value, _ = seasonal_reference(points[:-1], target_period)

    if seasonal_value is None:
        blended = trend_component
    else:
        blended = (trend_component * TREND_WEIGHT) + (seasonal_value * SEASONAL_WEIGHT)

    outlier_periods = [point.period for point in points if point.is_outlier]
    history = [
        ForecastHistoryPoint(
            period=point.period,
            raw_value=round(point.raw_value, 2),
            adjusted_value=round(point.adjusted_value, 2),
            is_outlier=point.is_outlier,
        )
        for point in points
    ]
    return ForecastProjection(
        metric=metric,  # type: ignore[arg-type]
        projected_value=max(0, round(blended)),
        trend_component=trend_component,
        seasonal_component=round(seasonal_value, 2) if seasonal_value is not None else None,
        blended_value=round(blended, 2),
        outlier_periods=outlier_periods,
        history=history,
    )


def methodology_text() -> str:
    return (
        "Forecast based on monthly aggregates, with IQR-based outlier attenuation, "
        "a weighted moving average over the three most recent months, and a soft "
        "seasonal adjustment using the same month from the prior year when available."
    )


def forecast_next_month(
    start_date: str | None = None,
    end_date: str | None = None,
    vehicle_type: str | None = None,
    vehicle_model: str | None = None,
) -> ForecastResult:
    monthly = get_monthly_aggregates(
        start_date=start_date,
        end_date=end_date,
        vehicle_type=vehicle_type,
        vehicle_model=vehicle_model,
    )
    if not monthly.rows:
        meta = monthly.meta
        meta.warnings.append("Forecast could not be generated because no monthly data is available.")
        return ForecastResult(
            meta=meta,
            projected_period="unknown",
            methodology=methodology_text(),
            leads_projection=ForecastProjection(
                metric="total_leads",
                projected_value=0,
                trend_component=0.0,
                seasonal_component=None,
                blended_value=0.0,
            ),
            sales_projection=ForecastProjection(
                metric="total_sales",
                projected_value=0,
                trend_component=0.0,
                seasonal_component=None,
                blended_value=0.0,
            ),
        )

    target_period = month_after(monthly.rows[-1].period)
    meta = AnalyticsMeta.model_validate(monthly.meta.model_dump())
    meta.granularity = "forecast_month"
    meta.primary_unit = "count"

    if len(monthly.rows) < 3:
        meta.warnings.append(
            "Forecast is based on fewer than three months of history, so confidence is limited."
        )

    leads_points = attenuate_series(monthly.rows, "total_leads")
    sales_points = attenuate_series(monthly.rows, "total_sales")

    if any(point.is_outlier for point in leads_points + sales_points):
        meta.warnings.append("Outlier attenuation was applied to reduce the impact of atypical months.")

    leads_projection = build_projection("total_leads", leads_points, target_period)
    sales_projection = build_projection("total_sales", sales_points, target_period)

    if leads_projection.seasonal_component is None or sales_projection.seasonal_component is None:
        meta.warnings.append(
            "Seasonal adjustment was unavailable for at least one metric, so the forecast leans more on recent trend."
        )

    return ForecastResult(
        meta=meta,
        projected_period=target_period,
        methodology=methodology_text(),
        leads_projection=leads_projection,
        sales_projection=sales_projection,
    )
