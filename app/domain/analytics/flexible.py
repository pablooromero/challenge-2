"""Flexible, allowlist-driven metric queries.

This module is the "semantic layer" of the assistant: the LLM never writes SQL.
It emits a validated contract (metrics + dimension + filters + sort) and this
module compiles it into a parameterized query using server-side allowlists only.
Derived ratios (CTR, CPL, CPA, ROAS, conversion rate) are computed in Python
from the aggregated base sums, so there is never an unsafe division in SQL.
"""

from app.core.errors import AnalyticsValidationError
from app.domain.analytics.filters import build_where_clause
from app.domain.analytics.helpers import (
    calculate_conversion_rate,
    calculate_cpa,
    calculate_cpl,
    calculate_ctr,
    calculate_roas,
    to_float,
    to_int,
)
from app.domain.analytics.meta import build_meta
from app.repositories.metrics_repository import fetch_metric_aggregates
from app.schemas.analytics import (
    FlexibleDimension,
    FlexibleQueryResult,
    FlexibleQueryRow,
    MetricName,
    SortDirection,
)

# Fixed base metrics returned by the repository query (the aggregated columns).
BASE_METRICS: tuple[MetricName, ...] = (
    "total_leads",
    "total_sales",
    "total_revenue_usd",
    "total_ad_cost_usd",
    "total_clicks",
    "total_impressions",
)

# Ratios derived in Python from the base metrics above.
DERIVED_METRICS: tuple[MetricName, ...] = ("ctr", "cpl", "cpa", "roas", "conversion_rate")

ALLOWED_METRICS: frozenset[str] = frozenset(BASE_METRICS + DERIVED_METRICS)

# Allowlist of dimension expressions. Keys are the only accepted values; the SQL
# fragments are trusted constants. `month` is escaped with %% for PyMySQL.
DIMENSION_SQL: dict[FlexibleDimension, str | None] = {
    "none": None,
    "month": "DATE_FORMAT(fecha, '%%Y-%%m')",
    "vehicle_type": "vehiculo_tipo_principal",
    "vehicle_model": "vehiculo_modelo_principal",
}

DIMENSION_LABELS: dict[FlexibleDimension, str] = {
    "none": "total",
    "month": "mes",
    "vehicle_type": "tipo de vehiculo",
    "vehicle_model": "modelo de vehiculo",
}

_MAX_LIMIT = 100


def _row_from_db(row: dict) -> FlexibleQueryRow:
    total_leads = to_int(row.get("total_leads"))
    total_sales = to_int(row.get("total_sales"))
    total_revenue = to_float(row.get("total_revenue_usd"))
    total_cost = to_float(row.get("total_ad_cost_usd"))
    total_clicks = to_int(row.get("total_clicks"))
    total_impressions = to_int(row.get("total_impressions"))
    dimension_value = row.get("dimension")
    return FlexibleQueryRow(
        dimension=str(dimension_value) if dimension_value is not None else None,
        total_leads=total_leads,
        total_sales=total_sales,
        total_revenue_usd=total_revenue,
        total_ad_cost_usd=total_cost,
        total_clicks=total_clicks,
        total_impressions=total_impressions,
        ctr=calculate_ctr(total_clicks, total_impressions),
        cpl=calculate_cpl(total_cost, total_leads),
        cpa=calculate_cpa(total_cost, total_sales),
        roas=calculate_roas(total_revenue, total_cost),
        conversion_rate=calculate_conversion_rate(total_sales, total_leads),
    )


def _validate_spec(
    metrics: list[MetricName],
    dimension: FlexibleDimension,
    sort_by: MetricName | None,
) -> list[MetricName]:
    if dimension not in DIMENSION_SQL:
        raise AnalyticsValidationError("Unsupported dimension for flexible query.")

    # Dedupe while preserving order; fall back to total_sales if empty.
    seen: set[str] = set()
    clean_metrics: list[MetricName] = []
    for metric in metrics:
        if metric not in ALLOWED_METRICS:
            raise AnalyticsValidationError(f"Unsupported metric: {metric}.")
        if metric not in seen:
            seen.add(metric)
            clean_metrics.append(metric)
    if not clean_metrics:
        clean_metrics = ["total_sales"]

    if sort_by is not None and sort_by not in ALLOWED_METRICS:
        raise AnalyticsValidationError(f"Unsupported sort_by metric: {sort_by}.")
    return clean_metrics


def run_metric_query(
    metrics: list[MetricName],
    dimension: FlexibleDimension = "none",
    sort_by: MetricName | None = None,
    sort_dir: SortDirection = "desc",
    limit: int = 12,
    start_date: str | None = None,
    end_date: str | None = None,
    vehicle_type: str | None = None,
    vehicle_model: str | None = None,
) -> FlexibleQueryResult:
    clean_metrics = _validate_spec(metrics, dimension, sort_by)
    limit = max(1, min(int(limit), _MAX_LIMIT))
    resolved_sort = sort_by if sort_by in clean_metrics else clean_metrics[0]

    where_clause, params, _ = build_where_clause(
        start_date=start_date,
        end_date=end_date,
        vehicle_type=vehicle_type,
        vehicle_model=vehicle_model,
    )
    meta = build_meta(
        start_date=start_date,
        end_date=end_date,
        vehicle_type=vehicle_type,
        vehicle_model=vehicle_model,
        granularity=dimension,
        primary_unit="mixed",
    )

    dimension_expr = DIMENSION_SQL[dimension]
    raw_rows = fetch_metric_aggregates(dimension_expr, where_clause, params)
    rows = [_row_from_db(row) for row in raw_rows]

    # Sorting and limiting happen in Python so we can rank on derived ratios too.
    if dimension != "none":
        rows.sort(key=lambda item: getattr(item, resolved_sort), reverse=(sort_dir == "desc"))
        rows = rows[:limit]

    return FlexibleQueryResult(
        meta=meta,
        dimension=dimension,
        metrics=clean_metrics,
        sort_by=resolved_sort,
        sort_dir=sort_dir,
        rows=rows,
    )
