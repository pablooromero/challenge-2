from typing import Literal

from pydantic import BaseModel, Field

from app.agent.graph.state import AssistantIntent
from app.schemas.analytics import FlexibleDimension, MetricName, SortField, VehicleGroupBy


class ClassificationOutput(BaseModel):
    intent: AssistantIntent
    metric: MetricName | None = None
    rank_direction: Literal["max", "min"] | None = None
    low_metric: MetricName | None = None
    high_metric: MetricName | None = None
    group_by: VehicleGroupBy | None = None
    sort_by: SortField | None = None
    # Filtros extraidos del lenguaje natural (parametrizados aguas abajo, nunca SQL libre).
    start_date: str | None = Field(
        default=None, description="Inicio del periodo en YYYY, YYYY-MM o YYYY-MM-DD."
    )
    end_date: str | None = Field(
        default=None, description="Fin del periodo en YYYY, YYYY-MM o YYYY-MM-DD."
    )
    vehicle_type: str | None = Field(default=None, description="Filtro por tipo de vehiculo.")
    vehicle_model: str | None = Field(default=None, description="Filtro por modelo de vehiculo.")
    # Campos para el intent flexible_metrics.
    metrics: list[MetricName] = Field(
        default_factory=list, description="Metricas pedidas para consultas flexibles."
    )
    dimension: FlexibleDimension | None = Field(
        default=None, description="Dimension de agrupamiento para consultas flexibles."
    )


class FinalAnswerOutput(BaseModel):
    answer: str = Field(min_length=1, max_length=800)
