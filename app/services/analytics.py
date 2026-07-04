import logging
from datetime import date
from decimal import Decimal
from typing import Any

from app.errors import AnalyticsValidationError
from app.schemas.analytics import (
    AnalyticsMeta,
    ChannelBreakdownResult,
    ChannelBreakdownRow,
    KpiToolResult,
    MetricName,
    MonthlyAggregateRow,
    MonthlyAggregatesResult,
    RankDirection,
    RankedPeriodResult,
    RelationalPatternResult,
    SortField,
    VehicleBreakdownResult,
    VehicleBreakdownRow,
    VehicleGroupBy,
)
from app.schemas.responses import CoverageResponse, DataRange, KpiSummary
from app.services.database import get_database_client

logger = logging.getLogger(__name__)

METRIC_UNITS: dict[MetricName, str] = {
    "total_leads": "count",
    "total_sales": "count",
    "total_revenue_usd": "usd",
    "total_ad_cost_usd": "usd",
    "total_clicks": "count",
    "total_impressions": "count",
    "ctr": "ratio",
    "cpl": "usd",
    "cpa": "usd",
    "roas": "ratio",
    "conversion_rate": "ratio",
}

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


def _to_int(value: int | Decimal | None) -> int:
    if value is None:
        return 0
    return int(value)


def _to_float(value: float | Decimal | None) -> float:
    if value is None:
        return 0.0
    return float(value)


def _safe_divide(numerator: float, denominator: float) -> float:
    if denominator == 0:
        return 0.0
    return numerator / denominator


def calculate_ctr(clicks: int, impressions: int) -> float:
    return round(_safe_divide(clicks, impressions), 4)


def calculate_cpl(cost: float, leads: int) -> float:
    return round(_safe_divide(cost, leads), 2)


def calculate_cpa(cost: float, sales: int) -> float:
    return round(_safe_divide(cost, sales), 2)


def calculate_roas(revenue: float, cost: float) -> float:
    return round(_safe_divide(revenue, cost), 2)


def calculate_conversion_rate(sales: int, leads: int) -> float:
    return round(_safe_divide(sales, leads), 4)


def _normalize_date(value: str | None, field_name: str) -> str | None:
    if value is None:
        return None
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError as exc:
        raise AnalyticsValidationError(
            f"Invalid {field_name}. Expected ISO date format YYYY-MM-DD."
        ) from exc


def _normalize_limit(limit: int) -> int:
    if limit < 1 or limit > 50:
        raise AnalyticsValidationError("Limit must be between 1 and 50.")
    return limit


def _build_where_clause(
    start_date: str | None = None,
    end_date: str | None = None,
    vehicle_type: str | None = None,
    vehicle_model: str | None = None,
) -> tuple[str, tuple[Any, ...], dict[str, str]]:
    normalized_start = _normalize_date(start_date, "start_date")
    normalized_end = _normalize_date(end_date, "end_date")
    if normalized_start and normalized_end and normalized_start > normalized_end:
        raise AnalyticsValidationError("start_date must be earlier than or equal to end_date.")

    conditions: list[str] = []
    params: list[Any] = []
    filters_applied: dict[str, str] = {}

    if normalized_start:
        conditions.append("fecha >= %s")
        params.append(normalized_start)
        filters_applied["start_date"] = normalized_start
    if normalized_end:
        conditions.append("fecha <= %s")
        params.append(normalized_end)
        filters_applied["end_date"] = normalized_end
    if vehicle_type:
        conditions.append("vehiculo_tipo_principal = %s")
        params.append(vehicle_type)
        filters_applied["vehicle_type"] = vehicle_type
    if vehicle_model:
        conditions.append("vehiculo_modelo_principal = %s")
        params.append(vehicle_model)
        filters_applied["vehicle_model"] = vehicle_model

    if not conditions:
        return "", tuple(), filters_applied

    return f"WHERE {' AND '.join(conditions)}", tuple(params), filters_applied


def _build_coverage_query(where_clause: str) -> str:
    return f"""
        SELECT
            MIN(fecha) AS min_fecha,
            MAX(fecha) AS max_fecha,
            COUNT(*) AS record_count
        FROM `{{table}}`
        {where_clause}
    """


def _get_filtered_coverage(
    start_date: str | None = None,
    end_date: str | None = None,
    vehicle_type: str | None = None,
    vehicle_model: str | None = None,
) -> tuple[DataRange, int, dict[str, str], list[str]]:
    db = get_database_client()
    table = db.settings.mysql_table
    where_clause, params, filters_applied = _build_where_clause(
        start_date=start_date,
        end_date=end_date,
        vehicle_type=vehicle_type,
        vehicle_model=vehicle_model,
    )
    query = _build_coverage_query(where_clause).format(table=table)
    row = db.fetch_one(query, params)

    record_count = _to_int(row.get("record_count"))
    warnings: list[str] = []
    if record_count == 0:
        warnings.append("No records found for the applied filters.")

    return (
        DataRange(
            from_date=row.get("min_fecha").isoformat() if row.get("min_fecha") else None,
            to_date=row.get("max_fecha").isoformat() if row.get("max_fecha") else None,
        ),
        record_count,
        filters_applied,
        warnings,
    )


def _build_meta(
    start_date: str | None = None,
    end_date: str | None = None,
    vehicle_type: str | None = None,
    vehicle_model: str | None = None,
    *,
    granularity: str | None = None,
    primary_unit: str | None = None,
) -> AnalyticsMeta:
    data_range, record_count, filters_applied, warnings = _get_filtered_coverage(
        start_date=start_date,
        end_date=end_date,
        vehicle_type=vehicle_type,
        vehicle_model=vehicle_model,
    )
    return AnalyticsMeta(
        data_range=data_range,
        record_count=record_count,
        granularity=granularity,
        filters_applied=filters_applied,
        warnings=warnings,
        primary_unit=primary_unit,
    )


def _monthly_row_from_db(row: dict[str, Any]) -> MonthlyAggregateRow:
    total_leads = _to_int(row.get("total_leads"))
    total_sales = _to_int(row.get("total_sales"))
    total_revenue = _to_float(row.get("total_revenue_usd"))
    total_ad_cost = _to_float(row.get("total_ad_cost_usd"))
    total_clicks = _to_int(row.get("total_clicks"))
    total_impressions = _to_int(row.get("total_impressions"))

    return MonthlyAggregateRow(
        period=str(row.get("period")),
        total_leads=total_leads,
        total_sales=total_sales,
        total_revenue_usd=total_revenue,
        total_ad_cost_usd=total_ad_cost,
        total_clicks=total_clicks,
        total_impressions=total_impressions,
        ctr=calculate_ctr(total_clicks, total_impressions),
        cpl=calculate_cpl(total_ad_cost, total_leads),
        cpa=calculate_cpa(total_ad_cost, total_sales),
        roas=calculate_roas(total_revenue, total_ad_cost),
        conversion_rate=calculate_conversion_rate(total_sales, total_leads),
    )


def _metric_value(row: MonthlyAggregateRow, metric: MetricName) -> float:
    return float(getattr(row, metric))


def _append_monthly_warnings(meta: AnalyticsMeta, rows: list[MonthlyAggregateRow]) -> None:
    if any(row.total_impressions == 0 for row in rows):
        meta.warnings.append(
            "Some CTR values defaulted to 0 because one or more periods had zero impressions."
        )
    if any(row.total_leads == 0 for row in rows):
        meta.warnings.append(
            "Some CPL or conversion-rate values defaulted to 0 because one or more periods had zero leads."
        )
    if any(row.total_sales == 0 for row in rows):
        meta.warnings.append(
            "Some CPA values defaulted to 0 because one or more periods had zero sales."
        )
    if any(row.total_ad_cost_usd == 0 for row in rows):
        meta.warnings.append(
            "Some ROAS values defaulted to 0 because one or more periods had zero ad cost."
        )


def get_data_coverage() -> CoverageResponse:
    db = get_database_client()
    table = db.settings.mysql_table
    logger.info("Running data coverage query.")
    query = f"""
        SELECT
            MIN(fecha) AS min_fecha,
            MAX(fecha) AS max_fecha,
            COUNT(*) AS record_count
        FROM `{table}`
    """
    row = db.fetch_one(query)

    return CoverageResponse(
        status="ok",
        message="Cobertura real obtenida desde MySQL.",
        data_range=DataRange(
            from_date=row.get("min_fecha").isoformat() if row.get("min_fecha") else None,
            to_date=row.get("max_fecha").isoformat() if row.get("max_fecha") else None,
        ),
        record_count=_to_int(row.get("record_count")),
    )


def _query_basic_kpis_summary(
    start_date: str | None = None,
    end_date: str | None = None,
    vehicle_type: str | None = None,
    vehicle_model: str | None = None,
) -> KpiSummary:
    db = get_database_client()
    table = db.settings.mysql_table
    where_clause, params, _ = _build_where_clause(
        start_date=start_date,
        end_date=end_date,
        vehicle_type=vehicle_type,
        vehicle_model=vehicle_model,
    )
    logger.info("Running basic KPI aggregate query.")
    query = f"""
        SELECT
            COALESCE(SUM(total_leads), 0) AS total_leads,
            COALESCE(SUM(cantidad_ventas), 0) AS total_sales,
            COALESCE(SUM(ingresos_ventas_usd), 0) AS total_revenue_usd,
            COALESCE(SUM(google_ads_costo_usd + meta_ads_costo_usd), 0) AS total_ad_cost_usd,
            COALESCE(SUM(google_ads_clics + meta_ads_clics), 0) AS total_clicks,
            COALESCE(SUM(google_ads_impresiones + meta_ads_impresiones), 0) AS total_impressions
        FROM `{table}`
        {where_clause}
    """
    row = db.fetch_one(query, params)

    return KpiSummary(
        total_leads=_to_int(row.get("total_leads")),
        total_sales=_to_int(row.get("total_sales")),
        total_revenue_usd=_to_float(row.get("total_revenue_usd")),
        total_ad_cost_usd=_to_float(row.get("total_ad_cost_usd")),
        total_clicks=_to_int(row.get("total_clicks")),
        total_impressions=_to_int(row.get("total_impressions")),
    )


def get_basic_kpis(
    start_date: str | None = None,
    end_date: str | None = None,
    vehicle_type: str | None = None,
    vehicle_model: str | None = None,
) -> KpiToolResult:
    meta = _build_meta(
        start_date=start_date,
        end_date=end_date,
        vehicle_type=vehicle_type,
        vehicle_model=vehicle_model,
        granularity="summary",
        primary_unit="mixed",
    )
    summary = _query_basic_kpis_summary(
        start_date=start_date,
        end_date=end_date,
        vehicle_type=vehicle_type,
        vehicle_model=vehicle_model,
    )
    return KpiToolResult(meta=meta, summary=summary)


def get_monthly_aggregates(
    start_date: str | None = None,
    end_date: str | None = None,
    vehicle_type: str | None = None,
    vehicle_model: str | None = None,
) -> MonthlyAggregatesResult:
    db = get_database_client()
    table = db.settings.mysql_table
    where_clause, params, _ = _build_where_clause(
        start_date=start_date,
        end_date=end_date,
        vehicle_type=vehicle_type,
        vehicle_model=vehicle_model,
    )
    meta = _build_meta(
        start_date=start_date,
        end_date=end_date,
        vehicle_type=vehicle_type,
        vehicle_model=vehicle_model,
        granularity="month",
        primary_unit="mixed",
    )
    query = f"""
        SELECT
            DATE_FORMAT(fecha, '%%Y-%%m') AS period,
            COALESCE(SUM(total_leads), 0) AS total_leads,
            COALESCE(SUM(cantidad_ventas), 0) AS total_sales,
            COALESCE(SUM(ingresos_ventas_usd), 0) AS total_revenue_usd,
            COALESCE(SUM(google_ads_costo_usd + meta_ads_costo_usd), 0) AS total_ad_cost_usd,
            COALESCE(SUM(google_ads_clics + meta_ads_clics), 0) AS total_clicks,
            COALESCE(SUM(google_ads_impresiones + meta_ads_impresiones), 0) AS total_impressions
        FROM `{table}`
        {where_clause}
        GROUP BY DATE_FORMAT(fecha, '%%Y-%%m')
        ORDER BY DATE_FORMAT(fecha, '%%Y-%%m')
    """
    rows = [_monthly_row_from_db(row) for row in db.fetch_all(query, params)]
    _append_monthly_warnings(meta, rows)
    return MonthlyAggregatesResult(meta=meta, rows=rows)


def get_channel_breakdown(
    start_date: str | None = None,
    end_date: str | None = None,
    vehicle_type: str | None = None,
    vehicle_model: str | None = None,
) -> ChannelBreakdownResult:
    db = get_database_client()
    table = db.settings.mysql_table
    where_clause, params, _ = _build_where_clause(
        start_date=start_date,
        end_date=end_date,
        vehicle_type=vehicle_type,
        vehicle_model=vehicle_model,
    )
    meta = _build_meta(
        start_date=start_date,
        end_date=end_date,
        vehicle_type=vehicle_type,
        vehicle_model=vehicle_model,
        granularity="summary",
        primary_unit="mixed",
    )
    query = f"""
        SELECT
            COALESCE(SUM(google_ads_impresiones), 0) AS google_impressions,
            COALESCE(SUM(google_ads_clics), 0) AS google_clicks,
            COALESCE(SUM(google_ads_leads), 0) AS google_leads,
            COALESCE(SUM(google_ads_costo_usd), 0) AS google_cost,
            COALESCE(SUM(meta_ads_impresiones), 0) AS meta_impressions,
            COALESCE(SUM(meta_ads_clics), 0) AS meta_clicks,
            COALESCE(SUM(meta_ads_leads), 0) AS meta_leads,
            COALESCE(SUM(meta_ads_costo_usd), 0) AS meta_cost
        FROM `{table}`
        {where_clause}
    """
    row = db.fetch_one(query, params)

    google_leads = _to_int(row.get("google_leads"))
    meta_leads = _to_int(row.get("meta_leads"))
    total_leads = google_leads + meta_leads

    rows = [
        ChannelBreakdownRow(
            channel="google_ads",
            total_impressions=_to_int(row.get("google_impressions")),
            total_clicks=_to_int(row.get("google_clicks")),
            total_leads=google_leads,
            total_ad_cost_usd=_to_float(row.get("google_cost")),
            ctr=calculate_ctr(_to_int(row.get("google_clicks")), _to_int(row.get("google_impressions"))),
            cpl=calculate_cpl(_to_float(row.get("google_cost")), google_leads),
            share_of_total_leads=round(_safe_divide(google_leads, total_leads), 4),
        ),
        ChannelBreakdownRow(
            channel="meta_ads",
            total_impressions=_to_int(row.get("meta_impressions")),
            total_clicks=_to_int(row.get("meta_clicks")),
            total_leads=meta_leads,
            total_ad_cost_usd=_to_float(row.get("meta_cost")),
            ctr=calculate_ctr(_to_int(row.get("meta_clicks")), _to_int(row.get("meta_impressions"))),
            cpl=calculate_cpl(_to_float(row.get("meta_cost")), meta_leads),
            share_of_total_leads=round(_safe_divide(meta_leads, total_leads), 4),
        ),
    ]
    if any(row.total_impressions == 0 for row in rows):
        meta.warnings.append("A channel had zero impressions, so its CTR defaulted to 0.")
    if any(row.total_leads == 0 for row in rows):
        meta.warnings.append("A channel had zero leads, so its CPL defaulted to 0.")
    return ChannelBreakdownResult(meta=meta, rows=rows)


def get_vehicle_breakdown(
    start_date: str | None = None,
    end_date: str | None = None,
    vehicle_type: str | None = None,
    vehicle_model: str | None = None,
    group_by: VehicleGroupBy = "type_model",
    sort_by: SortField = "total_sales",
    limit: int = 10,
) -> VehicleBreakdownResult:
    db = get_database_client()
    table = db.settings.mysql_table
    allowed_groupings = {
        "type": ["vehiculo_tipo_principal"],
        "model": ["vehiculo_modelo_principal"],
        "type_model": ["vehiculo_tipo_principal", "vehiculo_modelo_principal"],
    }
    if group_by not in allowed_groupings:
        raise AnalyticsValidationError("Unsupported group_by value.")
    if sort_by not in {"day_count", "total_leads", "total_sales", "total_revenue_usd", "conversion_rate"}:
        raise AnalyticsValidationError("Unsupported sort_by value.")

    limit = _normalize_limit(limit)
    where_clause, params, _ = _build_where_clause(
        start_date=start_date,
        end_date=end_date,
        vehicle_type=vehicle_type,
        vehicle_model=vehicle_model,
    )
    meta = _build_meta(
        start_date=start_date,
        end_date=end_date,
        vehicle_type=vehicle_type,
        vehicle_model=vehicle_model,
        granularity=group_by,
        primary_unit=METRIC_UNITS["total_sales"],
    )
    group_columns = allowed_groupings[group_by]
    select_columns = ", ".join(group_columns)
    group_clause = ", ".join(group_columns)

    query = f"""
        SELECT
            {select_columns},
            COUNT(*) AS day_count,
            COALESCE(SUM(total_leads), 0) AS total_leads,
            COALESCE(SUM(cantidad_ventas), 0) AS total_sales,
            COALESCE(SUM(ingresos_ventas_usd), 0) AS total_revenue_usd
        FROM `{table}`
        {where_clause}
        GROUP BY {group_clause}
    """
    rows = []
    for row in db.fetch_all(query, params):
        rows.append(
            VehicleBreakdownRow(
                vehicle_type=row.get("vehiculo_tipo_principal"),
                vehicle_model=row.get("vehiculo_modelo_principal"),
                day_count=_to_int(row.get("day_count")),
                total_leads=_to_int(row.get("total_leads")),
                total_sales=_to_int(row.get("total_sales")),
                total_revenue_usd=_to_float(row.get("total_revenue_usd")),
                conversion_rate=calculate_conversion_rate(
                    _to_int(row.get("total_sales")),
                    _to_int(row.get("total_leads")),
                ),
            )
        )

    sorted_rows = sorted(
        rows,
        key=lambda item: getattr(item, sort_by),
        reverse=True,
    )[:limit]
    if any(row.total_leads == 0 for row in sorted_rows):
        meta.warnings.append(
            "Some vehicle groups had zero leads, so their conversion_rate defaulted to 0."
        )

    return VehicleBreakdownResult(
        meta=meta,
        group_by=group_by,
        sort_by=sort_by,
        rows=sorted_rows,
    )


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
        key=lambda row: _metric_value(row, metric),
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
            sorted(monthly.rows, key=lambda item: _metric_value(item, low_metric)),
            start=1,
        )
    }
    high_rank_map = {
        row.period: rank
        for rank, row in enumerate(
            sorted(monthly.rows, key=lambda item: _metric_value(item, high_metric), reverse=True),
            start=1,
        )
    }

    best_row = min(
        monthly.rows,
        key=lambda row: (
            low_rank_map[row.period] + high_rank_map[row.period],
            -_metric_value(row, high_metric),
            _metric_value(row, low_metric),
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
