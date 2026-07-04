from app.core.errors import AnalyticsValidationError
from app.domain.analytics.breakdowns import get_monthly_aggregates
from app.schemas.analytics import MetricName, MonthlyAggregateRow, RankDirection, RankedPeriodResult

METRIC_LABELS: dict[MetricName, str] = {
    "total_leads": "leads",
    "total_sales": "sales",
    "total_revenue_usd": "revenue",
    "total_ad_cost_usd": "ad cost",
    "total_clicks": "clicks",
    "total_impressions": "impressions",
    "ctr": "CTR",
    "cpl": "CPL",
    "cpa": "CPA",
    "roas": "ROAS",
    "conversion_rate": "conversion rate",
}


def metric_value(row: MonthlyAggregateRow, metric: MetricName) -> float:
    return float(getattr(row, metric))


def find_best_or_worst_period(
    metric: MetricName,
    direction: RankDirection = "max",
    start_date: str | None = None,
    end_date: str | None = None,
    vehicle_type: str | None = None,
    vehicle_model: str | None = None,
) -> RankedPeriodResult:
    monthly = get_monthly_aggregates(
        start_date=start_date,
        end_date=end_date,
        vehicle_type=vehicle_type,
        vehicle_model=vehicle_model,
    )
    if direction not in {"max", "min"}:
        raise AnalyticsValidationError("direction must be either 'max' or 'min'.")

    if not monthly.rows:
        return RankedPeriodResult(
            meta=monthly.meta,
            metric=metric,
            direction=direction,
            row=None,
            explanation="No monthly data is available for the applied filters.",
        )

    ranked_row = sorted(
        monthly.rows,
        key=lambda row: metric_value(row, metric),
        reverse=direction == "max",
    )[0]
    return RankedPeriodResult(
        meta=monthly.meta,
        metric=metric,
        direction=direction,
        row=ranked_row,
        explanation=(
            f"Selected the month with the {direction}imum {METRIC_LABELS[metric]} "
            f"using monthly aggregates."
        ),
    )
