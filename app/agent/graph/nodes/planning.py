from typing import Any
from uuid import uuid4

from langchain_core.messages import AIMessage

from app.agent.graph.state import AssistantState
from app.observability import observation_context, update_current_span


def plan_tools(state: AssistantState) -> dict[str, Any]:
    with observation_context(
        "assistant.node.plan_tools",
        as_type="agent",
        input={"intent": state.get("intent"), "thread_id": state.get("thread_id")},
    ):
        intent = state.get("intent", "basic_kpi")
        metric = state.get("metric") or "total_sales"
        rank_direction = state.get("rank_direction") or "max"
        low_metric = state.get("low_metric") or "total_leads"
        high_metric = state.get("high_metric") or "total_sales"
        group_by = state.get("group_by") or "type_model"
        sort_by = state.get("sort_by") or "total_sales"

        # Filtros extraidos por el clasificador; se propagan a las tools que los aceptan.
        filter_args = {
            key: state.get(key)
            for key in ("start_date", "end_date", "vehicle_type", "vehicle_model")
            if state.get(key)
        }

        tool_name = "get_basic_kpis_tool"
        tool_args: dict[str, Any] = {}
        planning_reason = "intent_basic_kpi_maps_to_get_basic_kpis_tool"
        planning_details: dict[str, Any] = {"intent": intent, "metric": metric}

        if intent == "flexible_metrics":
            metrics = state.get("metrics") or [metric]
            dimension = state.get("dimension") or "none"
            sort_dir = state.get("sort_dir") or "desc"
            tool_name = "query_metrics_tool"
            tool_args = {
                "metrics": metrics,
                "dimension": dimension,
                "sort_by": state.get("sort_by"),
                "sort_dir": sort_dir,
                "limit": 12,
            }
            planning_reason = "intent_flexible_metrics_maps_to_query_metrics_tool"
            planning_details = {"intent": intent, "metrics": metrics, "dimension": dimension}
        elif intent == "temporal_analysis":
            tool_name = "find_best_or_worst_period_tool"
            tool_args = {"metric": metric, "direction": rank_direction}
            planning_reason = "intent_temporal_analysis_maps_to_find_best_or_worst_period_tool"
            planning_details = {"intent": intent, "metric": metric, "direction": rank_direction}
        elif intent == "relational_analysis":
            tool_name = "find_relational_pattern_tool"
            tool_args = {"low_metric": low_metric, "high_metric": high_metric}
            planning_reason = "intent_relational_analysis_maps_to_find_relational_pattern_tool"
            planning_details = {"intent": intent, "low_metric": low_metric, "high_metric": high_metric}
        elif intent == "forecast":
            tool_name = "forecast_next_month_tool"
            planning_reason = "intent_forecast_maps_to_forecast_next_month_tool"
            planning_details = {"intent": intent}
        elif intent == "channel_breakdown":
            tool_name = "get_channel_breakdown_tool"
            planning_reason = "intent_channel_breakdown_maps_to_get_channel_breakdown_tool"
            planning_details = {"intent": intent}
        elif intent == "vehicle_breakdown":
            tool_name = "get_vehicle_breakdown_tool"
            tool_args = {"group_by": group_by, "sort_by": sort_by, "limit": 5}
            planning_reason = "intent_vehicle_breakdown_maps_to_get_vehicle_breakdown_tool"
            planning_details = {"intent": intent, "group_by": group_by, "sort_by": sort_by, "limit": 5}
        elif intent == "unsupported":
            planning_reason = "unsupported_intent_has_no_tool"
            planning_details = {"intent": intent}
            update_current_span(
                output={"intent": intent, "tool_name": None},
                metadata={"planning_reason": planning_reason, **planning_details},
                level="WARNING",
                status_message="planning_out_of_scope",
            )
            return {
                "error": (
                    "La consulta esta fuera del alcance actual del asistente analitico. "
                    "Puedo ayudar con leads, ventas, ingresos, inversion publicitaria, "
                    "analisis mensuales, comparaciones entre periodos, canales, vehiculos "
                    "y proyecciones del proximo mes."
                ),
                "tool_name": None,
                "tool_args": {},
                "planning_reason": planning_reason,
                "planning_details": planning_details,
                "error_reason": "unsupported_intent_cannot_be_executed",
                "error_details": {"intent": intent},
            }

        # Merge extracted filters into whatever args the intent already produced.
        if filter_args:
            tool_args = {**tool_args, **filter_args}
            planning_details["filters"] = filter_args

        tool_call = {
            "name": tool_name,
            "args": tool_args,
            "id": f"tool-call-{uuid4().hex[:8]}",
            "type": "tool_call",
        }
        update_current_span(
            output={"tool_name": tool_name, "tool_args": tool_args},
            metadata={"planning_reason": planning_reason, **planning_details},
        )
        return {
            "tool_name": tool_name,
            "tool_args": tool_args,
            "planning_reason": planning_reason,
            "planning_details": planning_details,
            "messages": [AIMessage(content="", tool_calls=[tool_call])],
        }
