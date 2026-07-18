"""Smoke / demo-rehearsal script.

Runs the analytical layer directly against the configured MySQL database (no LLM
cost) to confirm the deterministic answers behind the key demo questions, plus a
few flexible-query scenarios. Useful before a live demo.

Usage:
    python scripts/smoke_queries.py
"""

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.domain.analytics.flexible import run_metric_query
from app.domain.analytics.kpis import get_basic_kpis
from app.domain.analytics.ranking import find_best_or_worst_period
from app.domain.analytics.relational import find_relational_pattern
from app.domain.forecast.projection import forecast_next_month


def section(title: str) -> None:
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


def main() -> None:
    section("Basic KPIs acumulados (incluye ratios derivados)")
    kpis = get_basic_kpis()
    print("Ventas totales:", kpis.summary.total_sales)
    print("Leads totales:", kpis.summary.total_leads)
    print("ROAS acumulado:", kpis.summary.roas)
    print("CTR acumulado:", kpis.summary.ctr)
    print("Conversion rate acumulada:", kpis.summary.conversion_rate)
    print("Rango de datos:", kpis.meta.data_range.model_dump(by_alias=True))

    section("Temporal: mejor mes de ventas")
    best = find_best_or_worst_period(metric="total_sales", direction="max")
    print("Mes lider:", best.row.period if best.row else None, "->", best.row.total_sales if best.row else None)

    section("Relacional: pocos leads, muchas ventas (esperado 2025-10)")
    rel = find_relational_pattern(low_metric="total_leads", high_metric="total_sales")
    if rel.row:
        print("Mes:", rel.row.period, "| leads:", rel.row.total_leads, "| ventas:", rel.row.total_sales)
        print("Rank leads (bajo):", rel.low_metric_rank, "| rank ventas (alto):", rel.high_metric_rank)

    section("Forecast proximo mes (esperado target 2026-07)")
    fc = forecast_next_month()
    print("Periodo proyectado:", fc.projected_period)
    print("Leads proyectados:", fc.leads_projection.projected_value)
    print("Ventas proyectadas:", fc.sales_projection.projected_value)
    print("Outliers atenuados (leads):", fc.leads_projection.outlier_periods)

    section("Flexible: ingresos y ROAS por tipo de vehiculo")
    flex = run_metric_query(metrics=["total_revenue_usd", "roas"], dimension="vehicle_type", sort_by="total_revenue_usd")
    for row in flex.rows[:5]:
        print(f"  {row.dimension}: ingresos={row.total_revenue_usd} roas={row.roas}")

    section("Flexible con filtro temporal: ventas y leads en 2025 (por mes)")
    flex2 = run_metric_query(
        metrics=["total_sales", "total_leads"],
        dimension="month",
        sort_by="total_sales",
        start_date="2025",
        end_date="2025",
    )
    print("Meses devueltos:", len(flex2.rows), "| rango:", flex2.meta.data_range.model_dump(by_alias=True))
    for row in flex2.rows[:3]:
        print(f"  {row.dimension}: ventas={row.total_sales} leads={row.total_leads}")

    print("\nOK: smoke completado.")


if __name__ == "__main__":
    main()
