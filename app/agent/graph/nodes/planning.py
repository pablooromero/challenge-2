from typing import Any
from uuid import uuid4

from langchain_core.messages import AIMessage

from app.agent.graph.state import AssistantState


def plan_tools(state: AssistantState) -> dict[str, Any]:
    intent = state.get("intent", "basic_kpi")
    metric = state.get("metric") or "total_sales"
    rank_direction = state.get("rank_direction") or "max"
    low_metric = state.get("low_metric") or "total_leads"
    high_metric = state.get("high_metric") or "total_sales"
    group_by = state.get("group_by") or "type_model"
    sort_by = state.get("sort_by") or "total_sales"

    tool_name = "get_basic_kpis_tool"
    tool_args: dict[str, Any] = {}

    if intent == "temporal_analysis":
        tool_name = "find_best_or_worst_period_tool"
        tool_args = {"metric": metric, "direction": rank_direction}
    elif intent == "relational_analysis":
        tool_name = "find_relational_pattern_tool"
        tool_args = {"low_metric": low_metric, "high_metric": high_metric}
    elif intent == "forecast":
        tool_name = "forecast_next_month_tool"
    elif intent == "channel_breakdown":
        tool_name = "get_channel_breakdown_tool"
    elif intent == "vehicle_breakdown":
        tool_name = "get_vehicle_breakdown_tool"
        tool_args = {"group_by": group_by, "sort_by": sort_by, "limit": 5}
    elif intent == "unsupported":
        return {
            "error": "La consulta esta fuera del alcance actual del asistente analitico.",
            "tool_name": None,
            "tool_args": {},
        }

    tool_call = {
        "name": tool_name,
        "args": tool_args,
        "id": f"tool-call-{uuid4().hex[:8]}",
        "type": "tool_call",
    }

    return {
        "tool_name": tool_name,
        "tool_args": tool_args,
        "messages": [AIMessage(content="", tool_calls=[tool_call])],
    }
