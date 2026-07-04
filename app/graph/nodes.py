from __future__ import annotations

import json
from typing import Any, Literal
from uuid import uuid4

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from app.graph.state import AssistantIntent, AssistantState


def _latest_human_message(state: AssistantState) -> str:
    for message in reversed(state.get("messages", [])):
        if isinstance(message, HumanMessage):
            return message.content
    return ""


def _normalize_text(text: str) -> str:
    return " ".join(text.strip().lower().split())


def _extract_metric(question: str) -> str | None:
    metric_map = [
        ("roas", "roas"),
        ("ctr", "ctr"),
        ("conversion", "conversion_rate"),
        ("cpa", "cpa"),
        ("cpl", "cpl"),
        ("ingres", "total_revenue_usd"),
        ("revenue", "total_revenue_usd"),
        ("factur", "total_revenue_usd"),
        ("costo", "total_ad_cost_usd"),
        ("gasto", "total_ad_cost_usd"),
        ("inversion", "total_ad_cost_usd"),
        ("lead", "total_leads"),
        ("venta", "total_sales"),
        ("clic", "total_clicks"),
        ("click", "total_clicks"),
        ("impres", "total_impressions"),
    ]
    for token, metric in metric_map:
        if token in question:
            return metric
    return None


def normalize_input(state: AssistantState) -> dict[str, Any]:
    question = _latest_human_message(state)
    normalized = _normalize_text(question)
    return {
        "normalized_question": normalized,
        "warnings": [],
        "error": None,
    }


def classify_intent_and_entities(state: AssistantState) -> dict[str, Any]:
    question = state.get("normalized_question", "")
    metric = _extract_metric(question)
    intent: AssistantIntent = "basic_kpi"
    rank_direction: Literal["max", "min"] | None = None
    low_metric: str | None = None
    high_metric: str | None = None
    group_by: str | None = None
    sort_by: str | None = None

    if any(token in question for token in ["proyect", "proximo mes", "forecast", "estim"]):
        intent = "forecast"
    elif "por canal" in question or "google ads" in question or "meta ads" in question:
        intent = "channel_breakdown"
    elif "por modelo" in question or "vehiculo" in question or "modelo" in question or "tipo" in question:
        intent = "vehicle_breakdown"
        if "por modelo" in question:
            group_by = "model"
        elif "tipo" in question and "modelo" not in question:
            group_by = "type"
        else:
            group_by = "type_model"
        sort_by = "total_sales"
    elif ("pocos leads" in question and "muchas ventas" in question) or (
        "pocas" in question and "muchas" in question
    ):
        intent = "relational_analysis"
        low_metric = "total_leads"
        high_metric = "total_sales"
    elif "mes" in question or "evolucion" in question or "mejor" in question or "peor" in question:
        intent = "temporal_analysis"
        if metric is None:
            metric = "total_sales"
        rank_direction = "min" if any(word in question for word in ["menor", "menos", "peor"]) else "max"
    elif any(word in question for word in ["presupuesto", "recomenda", "estrategia"]):
        intent = "unsupported"

    return {
        "intent": intent,
        "metric": metric,
        "rank_direction": rank_direction,
        "low_metric": low_metric,
        "high_metric": high_metric,
        "group_by": group_by,
        "sort_by": sort_by,
    }


def resolve_context(state: AssistantState) -> dict[str, Any]:
    question = state.get("normalized_question", "")
    intent = state.get("intent", "basic_kpi")
    metric = state.get("metric")
    group_by = state.get("group_by")
    last_metric = state.get("last_metric")
    last_intent = state.get("last_intent")

    if metric is None and any(token in question for token in ["y ", "tambien", "ademas", "comparalo"]):
        metric = last_metric or "total_sales"

    if intent == "basic_kpi" and "por canal" in question:
        intent = "channel_breakdown"
    if intent == "basic_kpi" and ("por modelo" in question or "por vehiculo" in question):
        intent = "vehicle_breakdown"
        group_by = "model" if "modelo" in question else "type_model"

    if intent == "basic_kpi" and metric is None and last_intent in {"basic_kpi", "temporal_analysis"}:
        metric = last_metric or "total_sales"

    return {
        "intent": intent,
        "metric": metric,
        "group_by": group_by,
    }


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


def compose_answer(state: AssistantState) -> dict[str, Any]:
    intent = state.get("intent", "basic_kpi")
    metric = state.get("metric") or "total_sales"
    tool_result = _latest_tool_result(state)
    if tool_result is None:
        return {"error": "No se pudo recuperar el resultado de la herramienta analitica."}

    meta = tool_result.get("meta", {})
    warnings = list(meta.get("warnings", []))
    answer = "No se pudo componer una respuesta."
    last_metric = metric
    last_intent = intent

    if intent == "basic_kpi":
        summary = tool_result["summary"]
        metric_value = summary.get(metric, summary.get("total_sales"))
        metric_label = _metric_label(metric)
        answer = (
            f"Al ultimo dato disponible ({meta['data_range']['to']}), "
            f"el valor acumulado de {metric_label} es {metric_value} desde {meta['data_range']['from']}."
        )
    elif intent == "temporal_analysis":
        row = tool_result.get("row")
        metric_label = _metric_label(tool_result.get("metric", metric))
        if row is None:
            answer = "No encontre datos mensuales para responder esa comparacion."
        else:
            qualifier = "mayor" if tool_result["direction"] == "max" else "menor"
            answer = (
                f"El mes con {qualifier} valor de {metric_label} fue {row['period']}, "
                f"con un valor de {row[tool_result['metric']]}."
            )
            last_metric = tool_result["metric"]
    elif intent == "relational_analysis":
        row = tool_result.get("row")
        if row is None:
            answer = "No encontre un periodo mensual valido para ese patron."
        else:
            answer = (
                f"El mejor candidato es {row['period']}: tuvo {row['total_leads']} leads y "
                f"{row['total_sales']} ventas. Quedo rankeado #{tool_result['low_metric_rank']} en "
                f"{_metric_label(tool_result['low_metric'])} y #{tool_result['high_metric_rank']} en "
                f"{_metric_label(tool_result['high_metric'])}."
            )
            last_metric = tool_result["high_metric"]
    elif intent == "forecast":
        answer = (
            f"Para {tool_result['projected_period']} la proyeccion es de "
            f"{tool_result['leads_projection']['projected_value']} leads y "
            f"{tool_result['sales_projection']['projected_value']} ventas. "
            "Es un forecast deterministico basado en tendencia reciente y ajuste estacional suave."
        )
        last_metric = "total_sales"
    elif intent == "channel_breakdown":
        rows = tool_result.get("rows", [])
        if len(rows) >= 2:
            top = max(rows, key=lambda row: row["total_leads"])
            answer = (
                f"El canal con mas leads fue {top['channel']}, con {top['total_leads']} leads, "
                f"CTR de {top['ctr']} y CPL de USD {top['cpl']}."
            )
        else:
            answer = "No encontre suficiente informacion por canal para responder."
        last_metric = "total_leads"
    elif intent == "vehicle_breakdown":
        rows = tool_result.get("rows", [])
        if rows:
            top = rows[0]
            label = " / ".join(
                [segment for segment in [top.get("vehicle_type"), top.get("vehicle_model")] if segment]
            )
            answer = (
                f"El grupo de vehiculo con mejor resultado fue {label}, con "
                f"{top['total_sales']} ventas y tasa de conversion de {top['conversion_rate']}."
            )
        else:
            answer = "No encontre suficiente informacion por vehiculo para responder."
        last_metric = "total_sales"
    else:
        answer = "Todavia no puedo resolver esa consulta con el flujo actual."

    return {
        "tool_result": tool_result,
        "warnings": warnings,
        "answer": answer,
        "last_metric": last_metric,
        "last_intent": last_intent,
        "messages": [AIMessage(content=answer)],
    }


def build_chart_payload(state: AssistantState) -> dict[str, Any]:
    intent = state.get("intent", "basic_kpi")
    tool_result = state.get("tool_result")
    if not tool_result:
        return {"chart_payload": None}

    chart_payload: dict[str, Any] | None = None

    if intent == "channel_breakdown":
        rows = tool_result.get("rows", [])
        chart_payload = {
            "type": "bar",
            "labels": [row["channel"] for row in rows],
            "datasets": [
                {"label": "Leads", "data": [row["total_leads"] for row in rows]},
                {"label": "Costo USD", "data": [row["total_ad_cost_usd"] for row in rows]},
            ],
        }
    elif intent == "vehicle_breakdown":
        rows = tool_result.get("rows", [])
        labels = [
            " / ".join([segment for segment in [row.get("vehicle_type"), row.get("vehicle_model")] if segment])
            for row in rows
        ]
        chart_payload = {
            "type": "bar",
            "labels": labels,
            "datasets": [{"label": "Ventas", "data": [row["total_sales"] for row in rows]}],
        }
    elif intent == "forecast":
        leads_history = tool_result["leads_projection"]["history"]
        sales_history = tool_result["sales_projection"]["history"]
        projected_period = tool_result["projected_period"]
        chart_payload = {
            "type": "line",
            "labels": [point["period"] for point in leads_history] + [projected_period],
            "datasets": [
                {
                    "label": "Leads proyectados",
                    "data": [point["adjusted_value"] for point in leads_history]
                    + [tool_result["leads_projection"]["projected_value"]],
                },
                {
                    "label": "Ventas proyectadas",
                    "data": [point["adjusted_value"] for point in sales_history]
                    + [tool_result["sales_projection"]["projected_value"]],
                },
            ],
        }

    return {"chart_payload": chart_payload}


def error_handler(state: AssistantState) -> dict[str, Any]:
    message = state.get("error") or "Ocurrio un error inesperado en el flujo del asistente."
    return {
        "answer": message,
        "warnings": [message],
        "messages": [AIMessage(content=message)],
        "chart_payload": None,
    }


def route_on_error(state: AssistantState) -> Literal["error_handler", "next"]:
    return "error_handler" if state.get("error") else "next"


def route_after_planning(state: AssistantState) -> Literal["error_handler", "execute_tools"]:
    return "error_handler" if state.get("error") else "execute_tools"


def _latest_tool_result(state: AssistantState) -> dict[str, Any] | None:
    for message in reversed(state.get("messages", [])):
        if isinstance(message, ToolMessage):
            content = message.content
            if isinstance(content, str):
                try:
                    return json.loads(content)
                except json.JSONDecodeError:
                    return {"raw_content": content}
    return None


def _metric_label(metric: str) -> str:
    labels = {
        "total_leads": "leads",
        "total_sales": "ventas",
        "total_revenue_usd": "ingresos",
        "total_ad_cost_usd": "costo publicitario",
        "total_clicks": "clics",
        "total_impressions": "impresiones",
        "ctr": "CTR",
        "cpl": "CPL",
        "cpa": "CPA",
        "roas": "ROAS",
        "conversion_rate": "tasa de conversion",
    }
    return labels.get(metric, metric)
