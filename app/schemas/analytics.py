from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.responses import DataRange, KpiSummary

MetricName = Literal[
    "total_leads",
    "total_sales",
    "total_revenue_usd",
    "total_ad_cost_usd",
    "total_clicks",
    "total_impressions",
    "ctr",
    "cpl",
    "cpa",
    "roas",
    "conversion_rate",
]

SortField = Literal[
    "day_count",
    "total_leads",
    "total_sales",
    "total_revenue_usd",
    "conversion_rate",
]

VehicleGroupBy = Literal["type", "model", "type_model"]
RankDirection = Literal["max", "min"]


class AnalyticsMeta(BaseModel):
    data_range: DataRange
    record_count: int
    granularity: str | None = None
    filters_applied: dict[str, str] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    primary_unit: str | None = None


class KpiToolResult(BaseModel):
    meta: AnalyticsMeta
    summary: KpiSummary


class MonthlyAggregateRow(BaseModel):
    period: str
    total_leads: int
    total_sales: int
    total_revenue_usd: float
    total_ad_cost_usd: float
    total_clicks: int
    total_impressions: int
    ctr: float
    cpl: float
    cpa: float
    roas: float
    conversion_rate: float


class MonthlyAggregatesResult(BaseModel):
    meta: AnalyticsMeta
    rows: list[MonthlyAggregateRow] = Field(default_factory=list)


class ChannelBreakdownRow(BaseModel):
    channel: str
    total_impressions: int
    total_clicks: int
    total_leads: int
    total_ad_cost_usd: float
    ctr: float
    cpl: float
    share_of_total_leads: float


class ChannelBreakdownResult(BaseModel):
    meta: AnalyticsMeta
    rows: list[ChannelBreakdownRow] = Field(default_factory=list)


class VehicleBreakdownRow(BaseModel):
    vehicle_type: str | None = None
    vehicle_model: str | None = None
    day_count: int
    total_leads: int
    total_sales: int
    total_revenue_usd: float
    conversion_rate: float


class VehicleBreakdownResult(BaseModel):
    meta: AnalyticsMeta
    group_by: VehicleGroupBy
    sort_by: SortField
    rows: list[VehicleBreakdownRow] = Field(default_factory=list)


class RankedPeriodResult(BaseModel):
    meta: AnalyticsMeta
    metric: MetricName
    direction: RankDirection
    row: MonthlyAggregateRow | None = None
    explanation: str


class RelationalPatternResult(BaseModel):
    meta: AnalyticsMeta
    low_metric: MetricName
    high_metric: MetricName
    row: MonthlyAggregateRow | None = None
    low_metric_rank: int | None = None
    high_metric_rank: int | None = None
    combined_rank_score: int | None = None
    explanation: str
