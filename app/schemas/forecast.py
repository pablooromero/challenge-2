from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.analytics import AnalyticsMeta


class ForecastHistoryPoint(BaseModel):
    period: str
    raw_value: float
    adjusted_value: float
    is_outlier: bool


class ForecastProjection(BaseModel):
    metric: Literal["total_leads", "total_sales"]
    projected_value: int
    trend_component: float
    seasonal_component: float | None = None
    blended_value: float
    outlier_periods: list[str] = Field(default_factory=list)
    history: list[ForecastHistoryPoint] = Field(default_factory=list)


class ForecastResult(BaseModel):
    meta: AnalyticsMeta
    projected_period: str
    methodology: str
    leads_projection: ForecastProjection
    sales_projection: ForecastProjection
