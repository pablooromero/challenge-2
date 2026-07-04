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
    return db.fetch_one(query, params)


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
    return db.fetch_one(query, params)


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
    return db.fetch_all(query, params)


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
    return db.fetch_one(query, params)


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
    return db.fetch_all(query, params)
