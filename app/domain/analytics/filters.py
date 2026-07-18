import calendar
import re
from datetime import date
from typing import Any, Literal

from app.core.errors import AnalyticsValidationError

_YEAR_RE = re.compile(r"^\d{4}$")
_MONTH_RE = re.compile(r"^\d{4}-\d{2}$")


def normalize_date(
    value: str | None,
    field_name: str,
    boundary: Literal["start", "end"] = "start",
) -> str | None:
    """Normalize a date filter into an ISO YYYY-MM-DD string.

    Accepts full dates (YYYY-MM-DD), months (YYYY-MM) and years (YYYY). For the
    coarser granularities the value is expanded to the first/last day of the
    period depending on `boundary`, so the LLM can emit a period without having
    to compute exact day boundaries.
    """
    if value is None:
        return None

    value = value.strip()
    try:
        if _YEAR_RE.match(value):
            year = int(value)
            return date(year, 1, 1).isoformat() if boundary == "start" else date(year, 12, 31).isoformat()
        if _MONTH_RE.match(value):
            year, month = (int(part) for part in value.split("-"))
            if boundary == "start":
                return date(year, month, 1).isoformat()
            last_day = calendar.monthrange(year, month)[1]
            return date(year, month, last_day).isoformat()
        return date.fromisoformat(value).isoformat()
    except (ValueError, IndexError) as exc:
        raise AnalyticsValidationError(
            f"Invalid {field_name}. Expected YYYY, YYYY-MM or YYYY-MM-DD."
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
    normalized_start = normalize_date(start_date, "start_date", "start")
    normalized_end = normalize_date(end_date, "end_date", "end")
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
