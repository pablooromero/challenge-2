from typing import Any, Literal

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages
from typing_extensions import Annotated, TypedDict

SUPPORTED_INTENTS = (
    "basic_kpi",
    "temporal_analysis",
    "relational_analysis",
    "forecast",
    "channel_breakdown",
    "vehicle_breakdown",
    "flexible_metrics",
    "unsupported",
)

AssistantIntent = Literal[
    "basic_kpi",
    "temporal_analysis",
    "relational_analysis",
    "forecast",
    "channel_breakdown",
    "vehicle_breakdown",
    "flexible_metrics",
    "unsupported",
]


class AssistantState(TypedDict, total=False):
    thread_id: str | None
    messages: Annotated[list[AnyMessage], add_messages]
    normalized_question: str
    intent: AssistantIntent
    metric: str | None
    rank_direction: Literal["max", "min"] | None
    low_metric: str | None
    high_metric: str | None
    group_by: str | None
    sort_by: str | None
    sort_dir: Literal["asc", "desc"] | None
    metrics: list[str] | None
    dimension: str | None
    start_date: str | None
    end_date: str | None
    vehicle_type: str | None
    vehicle_model: str | None
    tool_name: str | None
    tool_args: dict[str, Any]
    tool_result: dict[str, Any] | None
    answer: str | None
    chart_payload: dict[str, Any] | None
    warnings: list[str]
    error: str | None
    last_metric: str | None
    last_intent: AssistantIntent | None
    classification_source: str | None
    classification_reason: str | None
    classification_details: dict[str, Any]
    planning_reason: str | None
    planning_details: dict[str, Any]
    response_source: str | None
    error_reason: str | None
    error_details: dict[str, Any]
    llm_model: str | None
    prompt_versions: dict[str, dict[str, Any]]
