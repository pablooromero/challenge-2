from app.repositories.metrics_repository import fetch_data_coverage
from app.schemas.analytics import AnalyticsMeta
from app.schemas.responses import CoverageResponse, DataRange

from app.domain.analytics.filters import build_where_clause
from app.domain.analytics.helpers import to_int


def get_data_coverage() -> CoverageResponse:
    row = fetch_data_coverage()
    return CoverageResponse(
        status="ok",
        message="Cobertura real obtenida desde MySQL.",
        data_range=DataRange(
            from_date=row.get("min_fecha").isoformat() if row.get("min_fecha") else None,
            to_date=row.get("max_fecha").isoformat() if row.get("max_fecha") else None,
        ),
        record_count=to_int(row.get("record_count")),
    )


def get_filtered_coverage(
    start_date: str | None = None,
    end_date: str | None = None,
    vehicle_type: str | None = None,
    vehicle_model: str | None = None,
) -> tuple[DataRange, int, dict[str, str], list[str]]:
    where_clause, params, filters_applied = build_where_clause(
        start_date=start_date,
        end_date=end_date,
        vehicle_type=vehicle_type,
        vehicle_model=vehicle_model,
    )
    row = fetch_data_coverage(where_clause, params)

    record_count = to_int(row.get("record_count"))
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


def build_meta(
    start_date: str | None = None,
    end_date: str | None = None,
    vehicle_type: str | None = None,
    vehicle_model: str | None = None,
    *,
    granularity: str | None = None,
    primary_unit: str | None = None,
) -> AnalyticsMeta:
    data_range, record_count, filters_applied, warnings = get_filtered_coverage(
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
