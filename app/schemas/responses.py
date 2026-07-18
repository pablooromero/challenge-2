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


class PromptMeta(BaseModel):
    name: str
    version: int
    label: str | None = None
    source: str


class DecisionMeta(BaseModel):
    classification_source: str | None = None
    classification_reason: str | None = None
    planning_reason: str | None = None
    error_reason: str | None = None


class ChatMeta(BaseModel):
    thread_id: str
    warnings: list[str] = Field(default_factory=list)
    last_data_date: str | None = None
    source: str = "mock"
    model: str | None = None
    trace_id: str | None = None
    trace_url: str | None = None
    prompts: list[PromptMeta] = Field(default_factory=list)
    decisions: DecisionMeta | None = None


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
    # Ratios derivados calculados sobre los agregados (0.0 si el denominador es 0).
    ctr: float = 0.0
    cpl: float = 0.0
    cpa: float = 0.0
    roas: float = 0.0
    conversion_rate: float = 0.0


class AnalyticsSnapshot(BaseModel):
    coverage: CoverageResponse
    summary: KpiSummary


class KpiResponse(BaseModel):
    status: str
    summary: KpiSummary
