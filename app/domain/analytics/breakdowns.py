import logging
from typing import Any

from app.core.errors import AnalyticsValidationError
from app.domain.analytics.filters import build_where_clause, normalize_limit
from app.domain.analytics.helpers import (
    calculate_conversion_rate,
    calculate_cpa,
    calculate_cpl,
    calculate_ctr,
    calculate_roas,
    safe_divide,
    to_float,
    to_int,
)
from app.domain.analytics.meta import build_meta
from app.repositories.metrics_repository import (
    fetch_channel_breakdown,
    fetch_monthly_aggregates,
    fetch_vehicle_breakdown,
)
from app.schemas.analytics import (
    AnalyticsMeta,
    ChannelBreakdownResult,
    ChannelBreakdownRow,
    MonthlyAggregateRow,
    MonthlyAggregatesResult,
    SortField,
    VehicleBreakdownResult,
    VehicleBreakdownRow,
    VehicleGroupBy,
)

logger = logging.getLogger(__name__)

METRIC_UNITS = {
    "total_sales": "count",
}


def monthly_row_from_db(row: dict[str, Any]) -> MonthlyAggregateRow:
    total_leads = to_int(row.get("total_leads"))
    total_sales = to_int(row.get("total_sales"))
    total_revenue = to_float(row.get("total_revenue_usd"))
    total_ad_cost = to_float(row.get("total_ad_cost_usd"))
    total_clicks = to_int(row.get("total_clicks"))
    total_impressions = to_int(row.get("total_impressions"))

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


def append_monthly_warnings(meta: AnalyticsMeta, rows: list[MonthlyAggregateRow]) -> None:
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


def get_monthly_aggregates(
    start_date: str | None = None,
    end_date: str | None = None,
    vehicle_type: str | None = None,
    vehicle_model: str | None = None,
) -> MonthlyAggregatesResult:
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
        granularity="month",
        primary_unit="mixed",
    )
    logger.info("Running monthly aggregates query.")
    rows = [monthly_row_from_db(row) for row in fetch_monthly_aggregates(where_clause, params)]
    append_monthly_warnings(meta, rows)
    return MonthlyAggregatesResult(meta=meta, rows=rows)


def get_channel_breakdown(
    start_date: str | None = None,
    end_date: str | None = None,
    vehicle_type: str | None = None,
    vehicle_model: str | None = None,
) -> ChannelBreakdownResult:
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
        granularity="summary",
        primary_unit="mixed",
    )
    row = fetch_channel_breakdown(where_clause, params)

    google_leads = to_int(row.get("google_leads"))
    meta_leads = to_int(row.get("meta_leads"))
    total_leads = google_leads + meta_leads

    rows = [
        ChannelBreakdownRow(
            channel="google_ads",
            total_impressions=to_int(row.get("google_impressions")),
            total_clicks=to_int(row.get("google_clicks")),
            total_leads=google_leads,
            total_ad_cost_usd=to_float(row.get("google_cost")),
            ctr=calculate_ctr(to_int(row.get("google_clicks")), to_int(row.get("google_impressions"))),
            cpl=calculate_cpl(to_float(row.get("google_cost")), google_leads),
            share_of_total_leads=round(safe_divide(google_leads, total_leads), 4),
        ),
        ChannelBreakdownRow(
            channel="meta_ads",
            total_impressions=to_int(row.get("meta_impressions")),
            total_clicks=to_int(row.get("meta_clicks")),
            total_leads=meta_leads,
            total_ad_cost_usd=to_float(row.get("meta_cost")),
            ctr=calculate_ctr(to_int(row.get("meta_clicks")), to_int(row.get("meta_impressions"))),
            cpl=calculate_cpl(to_float(row.get("meta_cost")), meta_leads),
            share_of_total_leads=round(safe_divide(meta_leads, total_leads), 4),
        ),
    ]
    if any(item.total_impressions == 0 for item in rows):
        meta.warnings.append("A channel had zero impressions, so its CTR defaulted to 0.")
    if any(item.total_leads == 0 for item in rows):
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
    allowed_groupings = {
        "type": ["vehiculo_tipo_principal"],
        "model": ["vehiculo_modelo_principal"],
        "type_model": ["vehiculo_tipo_principal", "vehiculo_modelo_principal"],
    }
    if group_by not in allowed_groupings:
        raise AnalyticsValidationError("Unsupported group_by value.")
    if sort_by not in {"day_count", "total_leads", "total_sales", "total_revenue_usd", "conversion_rate"}:
        raise AnalyticsValidationError("Unsupported sort_by value.")

    limit = normalize_limit(limit)
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
        granularity=group_by,
        primary_unit=METRIC_UNITS["total_sales"],
    )
    group_columns = allowed_groupings[group_by]
    select_columns = ", ".join(group_columns)
    group_clause = ", ".join(group_columns)

    raw_rows = fetch_vehicle_breakdown(select_columns, group_clause, where_clause, params)
    rows = [
        VehicleBreakdownRow(
            vehicle_type=row.get("vehiculo_tipo_principal"),
            vehicle_model=row.get("vehiculo_modelo_principal"),
            day_count=to_int(row.get("day_count")),
            total_leads=to_int(row.get("total_leads")),
            total_sales=to_int(row.get("total_sales")),
            total_revenue_usd=to_float(row.get("total_revenue_usd")),
            conversion_rate=calculate_conversion_rate(
                to_int(row.get("total_sales")),
                to_int(row.get("total_leads")),
            ),
        )
        for row in raw_rows
    ]
    sorted_rows = sorted(rows, key=lambda item: getattr(item, sort_by), reverse=True)[:limit]
    if any(item.total_leads == 0 for item in sorted_rows):
        meta.warnings.append(
            "Some vehicle groups had zero leads, so their conversion_rate defaulted to 0."
        )

    return VehicleBreakdownResult(
        meta=meta,
        group_by=group_by,
        sort_by=sort_by,
        rows=sorted_rows,
    )
