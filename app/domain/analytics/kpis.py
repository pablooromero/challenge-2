import logging

from app.domain.analytics.filters import build_where_clause
from app.domain.analytics.helpers import to_float, to_int
from app.domain.analytics.meta import build_meta
from app.repositories.metrics_repository import fetch_basic_kpis
from app.schemas.analytics import KpiToolResult
from app.schemas.responses import KpiSummary

logger = logging.getLogger(__name__)


def query_basic_kpis_summary(
    start_date: str | None = None,
    end_date: str | None = None,
    vehicle_type: str | None = None,
    vehicle_model: str | None = None,
) -> KpiSummary:
    where_clause, params, _ = build_where_clause(
        start_date=start_date,
        end_date=end_date,
        vehicle_type=vehicle_type,
        vehicle_model=vehicle_model,
    )
    logger.info("Running basic KPI aggregate query.")
    row = fetch_basic_kpis(where_clause, params)
    return KpiSummary(
        total_leads=to_int(row.get("total_leads")),
        total_sales=to_int(row.get("total_sales")),
        total_revenue_usd=to_float(row.get("total_revenue_usd")),
        total_ad_cost_usd=to_float(row.get("total_ad_cost_usd")),
        total_clicks=to_int(row.get("total_clicks")),
        total_impressions=to_int(row.get("total_impressions")),
    )


def get_basic_kpis(
    start_date: str | None = None,
    end_date: str | None = None,
    vehicle_type: str | None = None,
    vehicle_model: str | None = None,
) -> KpiToolResult:
    meta = build_meta(
        start_date=start_date,
        end_date=end_date,
        vehicle_type=vehicle_type,
        vehicle_model=vehicle_model,
        granularity="summary",
        primary_unit="mixed",
    )
    summary = query_basic_kpis_summary(
        start_date=start_date,
        end_date=end_date,
        vehicle_type=vehicle_type,
        vehicle_model=vehicle_model,
    )
    return KpiToolResult(meta=meta, summary=summary)
