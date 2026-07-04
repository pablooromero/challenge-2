import json
from typing import Any

from langchain_core.messages import AIMessage, ToolMessage

from app.agent.graph.state import AssistantState
from app.agent.llm import compose_answer_with_llm
from app.agent.prompting import compile_prompt
from app.observability import observation_context, update_current_span


def latest_tool_result(state: AssistantState) -> dict[str, Any] | None:
    for message in reversed(state.get("messages", [])):
        if isinstance(message, ToolMessage):
            content = message.content
            if isinstance(content, str):
                if content.startswith("Error:"):
                    return {"tool_error": content.splitlines()[0]}
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


def question_mentions_freshness(question: str) -> bool:
    freshness_tokens = (
        "al dia de hoy",
        "a hoy",
        "hoy",
        "actual",
        "actuales",
        "hasta la fecha",
    )
    return any(token in question for token in freshness_tokens)


def append_freshness_notice(answer: str, question: str, meta: dict[str, Any]) -> str:
    data_range = meta.get("data_range") or {}
    last_data_date = data_range.get("to")
    if not last_data_date:
        return answer
    if not question_mentions_freshness(question):
        return answer
    if last_data_date in answer or "ultimo dato disponible" in answer.lower():
        return answer
    return f"{answer} El ultimo dato disponible en la base es {last_data_date}."


def build_deterministic_answer(state: AssistantState) -> dict[str, Any]:
    intent = state.get("intent", "basic_kpi")
    metric = state.get("metric") or "total_sales"
    question = state.get("normalized_question", "")
    tool_result = latest_tool_result(state)
    prompt_versions = dict(state.get("prompt_versions", {}))
    if tool_result is None:
        return {
            "error": "No se pudo recuperar el resultado de la herramienta analitica.",
            "error_reason": "tool_result_missing_after_execution",
            "error_details": {"intent": intent},
        }
    if "tool_error" in tool_result:
        return {
            "error": "No pude consultar la capa de datos en este momento.",
            "error_reason": "tool_execution_failed",
            "error_details": {"tool_error": str(tool_result["tool_error"])[:160]},
        }
    if "meta" not in tool_result:
        return {
            "error": "La herramienta analitica devolvio un formato inesperado.",
            "error_reason": "tool_result_invalid_format",
            "error_details": {"intent": intent},
        }

    meta = tool_result.get("meta", {})
    warnings = list(meta.get("warnings", []))
    if meta.get("record_count") == 0:
        return {
            "tool_result": tool_result,
            "warnings": warnings,
            "answer": "No encontre datos para los filtros o el periodo solicitado.",
            "last_metric": metric,
            "last_intent": intent,
            "prompt_versions": prompt_versions,
        }

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
                f"{row['total_sales']} ventas. Fue el #{tool_result['low_metric_rank']} mas bajo en "
                f"{metric_label(tool_result['low_metric'])} y el #{tool_result['high_metric_rank']} mas alto en "
                f"{metric_label(tool_result['high_metric'])}."
            )
            last_metric = tool_result["high_metric"]
    elif intent == "forecast":
        forecast_prompt = compile_prompt(
            "bi-assistant-forecast-explainer",
            projected_period=tool_result["projected_period"],
            projected_leads=tool_result["leads_projection"]["projected_value"],
            projected_sales=tool_result["sales_projection"]["projected_value"],
        )
        prompt_versions[forecast_prompt.name] = forecast_prompt.meta()
        answer = str(forecast_prompt.compiled)
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

    answer = append_freshness_notice(answer, question, meta)

    return {
        "tool_result": tool_result,
        "warnings": warnings,
        "answer": answer,
        "last_metric": last_metric,
        "last_intent": last_intent,
        "prompt_versions": prompt_versions,
    }


def compose_answer(state: AssistantState) -> dict[str, Any]:
    with observation_context(
        "assistant.node.compose_answer",
        as_type="agent",
        input={"intent": state.get("intent"), "thread_id": state.get("thread_id")},
    ):
        deterministic_payload = build_deterministic_answer(state)
        if deterministic_payload.get("error"):
            return deterministic_payload

        warnings = list(deterministic_payload["warnings"])
        answer = deterministic_payload["answer"]
        prompt_versions = dict(deterministic_payload.get("prompt_versions", {}))
        llm_answer, llm_warnings, llm_model, llm_prompts = compose_answer_with_llm(
            question=state.get("normalized_question", ""),
            intent=state.get("intent", "basic_kpi"),
            fallback_answer=answer,
            tool_result=deterministic_payload["tool_result"],
            warnings=warnings,
            thread_id=state.get("thread_id"),
        )
        warnings.extend(llm_warnings)
        prompt_versions.update(llm_prompts)

        if llm_answer is not None:
            answer = llm_answer

        response_source = "openai" if llm_answer is not None else "rules"
        update_current_span(
            output={"response_source": response_source, "warnings_count": len(warnings)},
            metadata={
                "response_source": response_source,
                "classification_reason": state.get("classification_reason") or "unknown",
                "planning_reason": state.get("planning_reason") or "unknown",
            },
        )
        return {
            **deterministic_payload,
            "warnings": warnings,
            "answer": answer,
            "response_source": response_source,
            "llm_model": llm_model or state.get("llm_model"),
            "prompt_versions": prompt_versions,
            "messages": [AIMessage(content=answer)],
        }


def build_chart_payload(state: AssistantState) -> dict[str, Any]:
    with observation_context(
        "assistant.node.build_chart_payload",
        as_type="agent",
        input={"intent": state.get("intent"), "thread_id": state.get("thread_id")},
    ):
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

        update_current_span(output={"chart_type": chart_payload.get("type") if chart_payload else None})
        return {"chart_payload": chart_payload}
