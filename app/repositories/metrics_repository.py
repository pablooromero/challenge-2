from typing import Any

from app.repositories.database_client import get_database_client


def fetch_data_coverage(where_clause: str = "", params: tuple[Any, ...] = ()) -> dict[str, Any]:
    db = get_database_client()
    query = f"""
        SELECT
            MIN(fecha) AS min_fecha,
            MAX(fecha) AS max_fecha,
            COUNT(*) AS record_count
        FROM `{db.table}`
        {where_clause}
    """
    return db.fetch_one(query, params, query_name="data_coverage")


def fetch_basic_kpis(where_clause: str = "", params: tuple[Any, ...] = ()) -> dict[str, Any]:
    db = get_database_client()
    query = f"""
        SELECT
            COALESCE(SUM(total_leads), 0) AS total_leads,
            COALESCE(SUM(cantidad_ventas), 0) AS total_sales,
            COALESCE(SUM(ingresos_ventas_usd), 0) AS total_revenue_usd,
            COALESCE(SUM(google_ads_costo_usd + meta_ads_costo_usd), 0) AS total_ad_cost_usd,
            COALESCE(SUM(google_ads_clics + meta_ads_clics), 0) AS total_clicks,
            COALESCE(SUM(google_ads_impresiones + meta_ads_impresiones), 0) AS total_impressions
        FROM `{db.table}`
        {where_clause}
    """
    return db.fetch_one(query, params, query_name="basic_kpis")


def fetch_monthly_aggregates(where_clause: str = "", params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    db = get_database_client()
    query = f"""
        SELECT
            DATE_FORMAT(fecha, '%%Y-%%m') AS period,
            COALESCE(SUM(total_leads), 0) AS total_leads,
            COALESCE(SUM(cantidad_ventas), 0) AS total_sales,
            COALESCE(SUM(ingresos_ventas_usd), 0) AS total_revenue_usd,
            COALESCE(SUM(google_ads_costo_usd + meta_ads_costo_usd), 0) AS total_ad_cost_usd,
            COALESCE(SUM(google_ads_clics + meta_ads_clics), 0) AS total_clicks,
            COALESCE(SUM(google_ads_impresiones + meta_ads_impresiones), 0) AS total_impressions
        FROM `{db.table}`
        {where_clause}
        GROUP BY DATE_FORMAT(fecha, '%%Y-%%m')
        ORDER BY DATE_FORMAT(fecha, '%%Y-%%m')
    """
    return db.fetch_all(query, params, query_name="monthly_aggregates")


def fetch_channel_breakdown(where_clause: str = "", params: tuple[Any, ...] = ()) -> dict[str, Any]:
    db = get_database_client()
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
        FROM `{db.table}`
        {where_clause}
    """
    return db.fetch_one(query, params, query_name="channel_breakdown")


# Escaped with %% because PyMySQL applies `query % params` when params are provided.
_BASE_METRIC_COLUMNS = """
    COALESCE(SUM(total_leads), 0) AS total_leads,
    COALESCE(SUM(cantidad_ventas), 0) AS total_sales,
    COALESCE(SUM(ingresos_ventas_usd), 0) AS total_revenue_usd,
    COALESCE(SUM(google_ads_costo_usd + meta_ads_costo_usd), 0) AS total_ad_cost_usd,
    COALESCE(SUM(google_ads_clics + meta_ads_clics), 0) AS total_clicks,
    COALESCE(SUM(google_ads_impresiones + meta_ads_impresiones), 0) AS total_impressions
"""


def fetch_metric_aggregates(
    dimension_expr: str | None,
    where_clause: str = "",
    params: tuple[Any, ...] = (),
    *,
    hard_limit: int = 1000,
) -> list[dict[str, Any]]:
    """Aggregate the fixed base-metric columns, optionally grouped by a dimension.

    `dimension_expr` and `hard_limit` are supplied exclusively from server-side
    allowlists/constants (never from user input), so this stays injection-safe
    while the query shape is dynamic.
    """
    db = get_database_client()
    if dimension_expr:
        query = f"""
            SELECT
                {dimension_expr} AS dimension,
                {_BASE_METRIC_COLUMNS}
            FROM `{db.table}`
            {where_clause}
            GROUP BY {dimension_expr}
            ORDER BY {dimension_expr}
            LIMIT {int(hard_limit)}
        """
    else:
        query = f"""
            SELECT
                {_BASE_METRIC_COLUMNS}
            FROM `{db.table}`
            {where_clause}
            LIMIT {int(hard_limit)}
        """
    return db.fetch_all(query, params, query_name="metric_aggregates")


def fetch_vehicle_breakdown(
    select_columns: str,
    group_clause: str,
    where_clause: str = "",
    params: tuple[Any, ...] = (),
) -> list[dict[str, Any]]:
    db = get_database_client()
    query = f"""
        SELECT
            {select_columns},
            COUNT(*) AS day_count,
            COALESCE(SUM(total_leads), 0) AS total_leads,
            COALESCE(SUM(cantidad_ventas), 0) AS total_sales,
            COALESCE(SUM(ingresos_ventas_usd), 0) AS total_revenue_usd
        FROM `{db.table}`
        {where_clause}
        GROUP BY {group_clause}
    """
    return db.fetch_all(query, params, query_name="vehicle_breakdown")
