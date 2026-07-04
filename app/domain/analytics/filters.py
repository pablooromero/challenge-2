from datetime import date
from typing import Any

from app.core.errors import AnalyticsValidationError


def normalize_date(value: str | None, field_name: str) -> str | None:
    if value is None:
        return None
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError as exc:
        raise AnalyticsValidationError(
            f"Invalid {field_name}. Expected ISO date format YYYY-MM-DD."
        ) from exc


def normalize_limit(limit: int) -> int:
    if limit < 1 or limit > 50:
        raise AnalyticsValidationError("Limit must be between 1 and 50.")
    return limit


def build_where_clause(
    start_date: str | None = None,
    end_date: str | None = None,
    vehicle_type: str | None = None,
    vehicle_model: str | None = None,
) -> tuple[str, tuple[Any, ...], dict[str, str]]:
    normalized_start = normalize_date(start_date, "start_date")
    normalized_end = normalize_date(end_date, "end_date")
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
