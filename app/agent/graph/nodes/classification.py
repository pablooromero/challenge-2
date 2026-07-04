from typing import Any, Literal

from langchain_core.messages import AIMessage, HumanMessage

from app.agent.graph.state import AssistantIntent, AssistantState
from app.agent.llm import classify_question_with_llm


def extract_metric(question: str) -> str | None:
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


def recent_conversation(state: AssistantState) -> list[dict[str, str]]:
    conversation: list[dict[str, str]] = []
    for message in state.get("messages", []):
        if isinstance(message, HumanMessage):
            conversation.append({"role": "user", "content": message.content})
        elif isinstance(message, AIMessage) and message.content:
            conversation.append({"role": "assistant", "content": str(message.content)})
    return conversation


def classify_intent_and_entities(state: AssistantState) -> dict[str, Any]:
    question = state.get("normalized_question", "")
    warnings = list(state.get("warnings", []))

    llm_result, llm_warnings, llm_model = classify_question_with_llm(
        question=question,
        conversation=recent_conversation(state),
        last_metric=state.get("last_metric"),
        last_intent=state.get("last_intent"),
        thread_id=state.get("thread_id"),
    )
    warnings.extend(llm_warnings)

    if llm_result is not None:
        return {
            "intent": llm_result.intent,
            "metric": llm_result.metric,
            "rank_direction": llm_result.rank_direction,
            "low_metric": llm_result.low_metric,
            "high_metric": llm_result.high_metric,
            "group_by": llm_result.group_by,
            "sort_by": llm_result.sort_by,
            "classification_source": "openai",
            "llm_model": llm_model,
            "warnings": warnings,
        }

    metric = extract_metric(question)
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
        "classification_source": "rules",
        "warnings": warnings,
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
