from typing import Any, Literal

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages
from typing_extensions import Annotated, TypedDict


AssistantIntent = Literal[
    "basic_kpi",
    "temporal_analysis",
    "relational_analysis",
    "forecast",
    "channel_breakdown",
    "vehicle_breakdown",
    "unsupported",
]


class AssistantState(TypedDict, total=False):
    messages: Annotated[list[AnyMessage], add_messages]
    normalized_question: str
    intent: AssistantIntent
    metric: str | None
    rank_direction: Literal["max", "min"] | None
    low_metric: str | None
    high_metric: str | None
    group_by: str | None
    sort_by: str | None
    tool_name: str | None
    tool_args: dict[str, Any]
    tool_result: dict[str, Any] | None
    answer: str | None
    chart_payload: dict[str, Any] | None
    warnings: list[str]
    error: str | None
    last_metric: str | None
    last_intent: AssistantIntent | None
