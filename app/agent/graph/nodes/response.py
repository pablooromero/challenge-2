import json
from typing import Any

from langchain_core.messages import AIMessage, ToolMessage

from app.agent.graph.state import AssistantState


def latest_tool_result(state: AssistantState) -> dict[str, Any] | None:
    for message in reversed(state.get("messages", [])):
        if isinstance(message, ToolMessage):
            content = message.content
            if isinstance(content, str):
                try:
                    return json.loads(content)
                except json.JSONDecodeError:
                    return {"raw_content": content}
    return None


def metric_label(metric: str) -> str:
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


def compose_answer(state: AssistantState) -> dict[str, Any]:
    intent = state.get("intent", "basic_kpi")
    metric = state.get("metric") or "total_sales"
    tool_result = latest_tool_result(state)
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
        answer = (
            f"Al ultimo dato disponible ({meta['data_range']['to']}), "
            f"el valor acumulado de {metric_label(metric)} es {metric_value} desde "
            f"{meta['data_range']['from']}."
        )
    elif intent == "temporal_analysis":
        row = tool_result.get("row")
        if row is None:
            answer = "No encontre datos mensuales para responder esa comparacion."
        else:
            qualifier = "mayor" if tool_result["direction"] == "max" else "menor"
            answer = (
                f"El mes con {qualifier} valor de {metric_label(tool_result['metric'])} "
                f"fue {row['period']}, con un valor de {row[tool_result['metric']]}."
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
                f"{metric_label(tool_result['low_metric'])} y #{tool_result['high_metric_rank']} en "
                f"{metric_label(tool_result['high_metric'])}."
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
