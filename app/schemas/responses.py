from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: dict[str, str] = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    error: ErrorDetail


class DataRange(BaseModel):
    from_date: str | None = Field(default=None, alias="from")
    to_date: str | None = Field(default=None, alias="to")

    model_config = {"populate_by_name": True}


class ChartDataset(BaseModel):
    label: str
    data: list[float] = Field(default_factory=list)


class ChartPayload(BaseModel):
    type: str
    labels: list[str] = Field(default_factory=list)
    datasets: list[ChartDataset] = Field(default_factory=list)


class ChatMeta(BaseModel):
    thread_id: str
    warnings: list[str] = Field(default_factory=list)
    last_data_date: str | None = None
    source: str = "mock"


class ChatResponse(BaseModel):
    answer: str
    intent: str
    data_range: DataRange | None = None
    chart: ChartPayload | None = None
    meta: ChatMeta


class HealthResponse(BaseModel):
    status: str
    app_name: str
    environment: str
    version: str
    database_status: str
    database_message: str | None = None


class CoverageResponse(BaseModel):
    status: str
    message: str
    data_range: DataRange | None = None
    record_count: int | None = None


class KpiSummary(BaseModel):
    total_leads: int
    total_sales: int
    total_revenue_usd: float
    total_ad_cost_usd: float
    total_clicks: int
    total_impressions: int


class AnalyticsSnapshot(BaseModel):
    coverage: CoverageResponse
    summary: KpiSummary


class KpiResponse(BaseModel):
    status: str
    summary: KpiSummary
