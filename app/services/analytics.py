import logging
from decimal import Decimal

from app.schemas.responses import CoverageResponse, DataRange, KpiSummary
from app.services.database import get_database_client

logger = logging.getLogger(__name__)


def _to_int(value: int | Decimal | None) -> int:
    if value is None:
        return 0
    return int(value)


def _to_float(value: float | Decimal | None) -> float:
    if value is None:
        return 0.0
    return float(value)


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


def get_basic_kpis() -> KpiSummary:
    db = get_database_client()
    table = db.settings.mysql_table
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
    """
    row = db.fetch_one(query)

    return KpiSummary(
        total_leads=_to_int(row.get("total_leads")),
        total_sales=_to_int(row.get("total_sales")),
        total_revenue_usd=_to_float(row.get("total_revenue_usd")),
        total_ad_cost_usd=_to_float(row.get("total_ad_cost_usd")),
        total_clicks=_to_int(row.get("total_clicks")),
        total_impressions=_to_int(row.get("total_impressions")),
    )
