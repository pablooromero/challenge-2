from typing import Literal

from pydantic import BaseModel, Field

from app.agent.graph.state import AssistantIntent
from app.schemas.analytics import MetricName, SortField, VehicleGroupBy


class ClassificationOutput(BaseModel):
    intent: AssistantIntent
    metric: MetricName | None = None
    rank_direction: Literal["max", "min"] | None = None
    low_metric: MetricName | None = None
    high_metric: MetricName | None = None
    group_by: VehicleGroupBy | None = None
    sort_by: SortField | None = None


class FinalAnswerOutput(BaseModel):
    answer: str = Field(min_length=1, max_length=800)
