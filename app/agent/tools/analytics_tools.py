from typing import Literal

from langchain.tools import tool
from pydantic import BaseModel, Field

from app.domain.analytics.breakdowns import (
    get_channel_breakdown,
    get_monthly_aggregates,
    get_vehicle_breakdown,
)
from app.domain.analytics.kpis import get_basic_kpis
from app.domain.analytics.ranking import find_best_or_worst_period
from app.domain.analytics.relational import find_relational_pattern
from app.observability import observation_context, update_current_span
from app.schemas.analytics import MetricName, SortField, VehicleGroupBy


class AnalyticsFilterInput(BaseModel):
    start_date: str | None = Field(default=None, description="Inclusive start date in YYYY-MM-DD.")
    end_date: str | None = Field(default=None, description="Inclusive end date in YYYY-MM-DD.")
    vehicle_type: str | None = Field(default=None, description="Optional vehicle type filter.")
    vehicle_model: str | None = Field(default=None, description="Optional vehicle model filter.")


class VehicleBreakdownInput(AnalyticsFilterInput):
    group_by: VehicleGroupBy = Field(
        default="type_model",
        description="Grouping level for the vehicle breakdown.",
    )
    sort_by: SortField = Field(
        default="total_sales",
        description="Metric used to sort the vehicle breakdown rows.",
    )
    limit: int = Field(default=10, ge=1, le=50, description="Maximum number of rows to return.")


class PeriodRankingInput(AnalyticsFilterInput):
    metric: MetricName = Field(description="Metric used to rank monthly periods.")
    direction: Literal["max", "min"] = Field(
        default="max",
        description="Whether to find the period with the highest or lowest value.",
    )


class RelationalPatternInput(AnalyticsFilterInput):
    low_metric: MetricName = Field(
        description="Metric that should rank low, for example total_leads."
    )
    high_metric: MetricName = Field(
        description="Metric that should rank high, for example total_sales."
    )


@tool(args_schema=AnalyticsFilterInput)
def get_basic_kpis_tool(
    start_date: str | None = None,
    end_date: str | None = None,
    vehicle_type: str | None = None,
    vehicle_model: str | None = None,
) -> dict:
    """Return aggregated campaign KPIs for the selected filters."""
    with observation_context(
        "assistant.tool.get_basic_kpis",
        as_type="tool",
        input={"start_date": start_date, "end_date": end_date},
    ):
        result = get_basic_kpis(
            start_date=start_date,
            end_date=end_date,
            vehicle_type=vehicle_type,
            vehicle_model=vehicle_model,
        )
        update_current_span(output={"record_count": result.meta.record_count})
        return result.model_dump(by_alias=True)


@tool(args_schema=AnalyticsFilterInput)
def get_monthly_aggregates_tool(
    start_date: str | None = None,
    end_date: str | None = None,
    vehicle_type: str | None = None,
    vehicle_model: str | None = None,
) -> dict:
    """Return monthly campaign aggregates and derived metrics like ROAS and conversion rate."""
    with observation_context(
        "assistant.tool.get_monthly_aggregates",
        as_type="tool",
        input={"start_date": start_date, "end_date": end_date},
    ):
        result = get_monthly_aggregates(
            start_date=start_date,
            end_date=end_date,
            vehicle_type=vehicle_type,
            vehicle_model=vehicle_model,
        )
        update_current_span(output={"row_count": len(result.rows)})
        return result.model_dump(by_alias=True)


@tool(args_schema=AnalyticsFilterInput)
def get_channel_breakdown_tool(
    start_date: str | None = None,
    end_date: str | None = None,
    vehicle_type: str | None = None,
    vehicle_model: str | None = None,
) -> dict:
    """Return channel-level breakdown for Google Ads and Meta Ads."""
    with observation_context(
        "assistant.tool.get_channel_breakdown",
        as_type="tool",
        input={"start_date": start_date, "end_date": end_date},
    ):
        result = get_channel_breakdown(
            start_date=start_date,
            end_date=end_date,
            vehicle_type=vehicle_type,
            vehicle_model=vehicle_model,
        )
        update_current_span(output={"row_count": len(result.rows)})
        return result.model_dump(by_alias=True)


@tool(args_schema=VehicleBreakdownInput)
def get_vehicle_breakdown_tool(
    start_date: str | None = None,
    end_date: str | None = None,
    vehicle_type: str | None = None,
    vehicle_model: str | None = None,
    group_by: VehicleGroupBy = "type_model",
    sort_by: SortField = "total_sales",
    limit: int = 10,
) -> dict:
    """Return the best-performing vehicle groups by type, model, or both."""
    with observation_context(
        "assistant.tool.get_vehicle_breakdown",
        as_type="tool",
        input={"group_by": group_by, "sort_by": sort_by, "limit": limit},
    ):
        result = get_vehicle_breakdown(
            start_date=start_date,
            end_date=end_date,
            vehicle_type=vehicle_type,
            vehicle_model=vehicle_model,
            group_by=group_by,
            sort_by=sort_by,
            limit=limit,
        )
        update_current_span(output={"row_count": len(result.rows), "group_by": result.group_by})
        return result.model_dump(by_alias=True)


@tool(args_schema=PeriodRankingInput)
def find_best_or_worst_period_tool(
    metric: MetricName,
    direction: Literal["max", "min"] = "max",
    start_date: str | None = None,
    end_date: str | None = None,
    vehicle_type: str | None = None,
    vehicle_model: str | None = None,
) -> dict:
    """Find the best or worst monthly period for a given metric."""
    with observation_context(
        "assistant.tool.find_best_or_worst_period",
        as_type="tool",
        input={"metric": metric, "direction": direction},
    ):
        result = find_best_or_worst_period(
            metric=metric,
            direction=direction,
            start_date=start_date,
            end_date=end_date,
            vehicle_type=vehicle_type,
            vehicle_model=vehicle_model,
        )
        update_current_span(output={"period": result.row.period if result.row else None})
        return result.model_dump(by_alias=True)


@tool(args_schema=RelationalPatternInput)
def find_relational_pattern_tool(
    low_metric: MetricName,
    high_metric: MetricName,
    start_date: str | None = None,
    end_date: str | None = None,
    vehicle_type: str | None = None,
    vehicle_model: str | None = None,
) -> dict:
    """Find the month that best matches a low-metric and high-metric combination."""
    with observation_context(
        "assistant.tool.find_relational_pattern",
        as_type="tool",
        input={"low_metric": low_metric, "high_metric": high_metric},
    ):
        result = find_relational_pattern(
            low_metric=low_metric,
            high_metric=high_metric,
            start_date=start_date,
            end_date=end_date,
            vehicle_type=vehicle_type,
            vehicle_model=vehicle_model,
        )
        update_current_span(output={"period": result.row.period if result.row else None})
        return result.model_dump(by_alias=True)


def get_analytics_tools() -> list:
    return [
        get_basic_kpis_tool,
        get_monthly_aggregates_tool,
        get_channel_breakdown_tool,
        get_vehicle_breakdown_tool,
        find_best_or_worst_period_tool,
        find_relational_pattern_tool,
    ]
