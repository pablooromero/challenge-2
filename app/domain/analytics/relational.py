from app.core.errors import AnalyticsValidationError
from app.domain.analytics.breakdowns import get_monthly_aggregates
from app.domain.analytics.ranking import METRIC_LABELS, metric_value
from app.schemas.analytics import MetricName, RelationalPatternResult


def find_relational_pattern(
    low_metric: MetricName,
    high_metric: MetricName,
    start_date: str | None = None,
    end_date: str | None = None,
    vehicle_type: str | None = None,
    vehicle_model: str | None = None,
) -> RelationalPatternResult:
    if low_metric == high_metric:
        raise AnalyticsValidationError("low_metric and high_metric must be different.")

    monthly = get_monthly_aggregates(
        start_date=start_date,
        end_date=end_date,
        vehicle_type=vehicle_type,
        vehicle_model=vehicle_model,
    )
    if not monthly.rows:
        return RelationalPatternResult(
            meta=monthly.meta,
            low_metric=low_metric,
            high_metric=high_metric,
            row=None,
            explanation="No monthly data is available for the applied filters.",
        )

    low_rank_map = {
        row.period: rank
        for rank, row in enumerate(
            sorted(monthly.rows, key=lambda item: metric_value(item, low_metric)),
            start=1,
        )
    }
    high_rank_map = {
        row.period: rank
        for rank, row in enumerate(
            sorted(monthly.rows, key=lambda item: metric_value(item, high_metric), reverse=True),
            start=1,
        )
    }

    best_row = min(
        monthly.rows,
        key=lambda row: (
            low_rank_map[row.period] + high_rank_map[row.period],
            -metric_value(row, high_metric),
            metric_value(row, low_metric),
        ),
    )
    combined_rank = low_rank_map[best_row.period] + high_rank_map[best_row.period]

    return RelationalPatternResult(
        meta=monthly.meta,
        low_metric=low_metric,
        high_metric=high_metric,
        row=best_row,
        low_metric_rank=low_rank_map[best_row.period],
        high_metric_rank=high_rank_map[best_row.period],
        combined_rank_score=combined_rank,
        explanation=(
            f"Selected the month that jointly ranks low in {METRIC_LABELS[low_metric]} "
            f"and high in {METRIC_LABELS[high_metric]} across monthly aggregates."
        ),
    )
