from typing import Any, Literal

from langchain_core.messages import AIMessage, HumanMessage

from app.agent.guardrails import detect_ambiguous_question, detect_restricted_request
from app.agent.graph.state import AssistantIntent, AssistantState
from app.agent.llm import classify_question_with_llm
from app.observability import observation_context, update_current_span


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


def matched_keywords(question: str, keywords: tuple[str, ...]) -> list[str]:
    return [keyword for keyword in keywords if keyword in question]


def classify_intent_and_entities(state: AssistantState) -> dict[str, Any]:
    with observation_context(
        "assistant.node.classify_intent_and_entities",
        as_type="agent",
        input={"thread_id": state.get("thread_id")},
    ):
        question = state.get("normalized_question", "")
        warnings = list(state.get("warnings", []))
        prompt_versions = dict(state.get("prompt_versions", {}))
        restricted_match = detect_restricted_request(question)
        ambiguity_match = detect_ambiguous_question(question)
        last_metric = state.get("last_metric")
        last_intent = state.get("last_intent")

        if restricted_match is not None:
            warnings.append(
                "La consulta fue rechazada porque intenta salir del dominio analitico permitido."
            )
            update_current_span(
                output={
                    "intent": "unsupported",
                    "source": "guardrail",
                    "restricted_request": True,
                    "guardrail_category": restricted_match.category,
                },
                metadata={
                    "decision_source": "guardrail",
                    "classification_reason": restricted_match.reason,
                    **restricted_match.as_metadata(),
                },
                level="WARNING",
                status_message="guardrail_blocked",
            )
            return {
                "intent": "unsupported",
                "classification_source": "guardrail",
                "classification_reason": restricted_match.reason,
                "classification_details": restricted_match.as_metadata(),
                "warnings": warnings,
                "prompt_versions": prompt_versions,
            }

        if last_metric is None and last_intent is None and ambiguity_match is not None:
            update_current_span(
                output={"intent": "unsupported", "source": "guardrail", "ambiguous_question": True},
                metadata={
                    "decision_source": "guardrail",
                    "classification_reason": ambiguity_match.reason,
                    **ambiguity_match.as_metadata(),
                },
                level="WARNING",
                status_message="guardrail_needs_clarification",
            )
            return {
                "intent": "unsupported",
                "classification_source": "guardrail",
                "classification_reason": ambiguity_match.reason,
                "classification_details": ambiguity_match.as_metadata(),
                "error": (
                    "No me quedo claro que metrica o analisis necesitas. "
                    "Reformulá la consulta indicando, por ejemplo, ventas, leads, mes, canal o proyeccion."
                ),
                "error_reason": ambiguity_match.reason,
                "error_details": ambiguity_match.as_metadata(),
                "warnings": warnings,
                "prompt_versions": prompt_versions,
            }

        llm_result, llm_warnings, llm_model, llm_prompts = classify_question_with_llm(
            question=question,
            conversation=recent_conversation(state),
            last_metric=last_metric,
            last_intent=last_intent,
            thread_id=state.get("thread_id"),
        )
        warnings.extend(llm_warnings)
        prompt_versions.update(llm_prompts)

        if llm_result is not None:
            classification_reason = (
                "llm_out_of_scope_classification" if llm_result.intent == "unsupported" else "llm_structured_classification"
            )
            classification_details = {
                "decision_source": "openai",
                "intent": llm_result.intent,
                "metric": llm_result.metric or "null",
                "model": llm_model or "unknown",
                "prompt_name": next(iter(llm_prompts), "bi-assistant-intent-classifier"),
            }
            update_current_span(
                output={
                    "intent": llm_result.intent,
                    "metric": llm_result.metric,
                    "source": "openai",
                },
                metadata={
                    "decision_source": "openai",
                    "classification_reason": classification_reason,
                    **classification_details,
                },
            )
            return {
                "intent": llm_result.intent,
                "metric": llm_result.metric,
                "rank_direction": llm_result.rank_direction,
                "low_metric": llm_result.low_metric,
                "high_metric": llm_result.high_metric,
                "group_by": llm_result.group_by,
                "sort_by": llm_result.sort_by,
                "sort_dir": None,
                "metrics": llm_result.metrics or None,
                "dimension": llm_result.dimension,
                "start_date": llm_result.start_date,
                "end_date": llm_result.end_date,
                "vehicle_type": llm_result.vehicle_type,
                "vehicle_model": llm_result.vehicle_model,
                "classification_source": "openai",
                "classification_reason": classification_reason,
                "classification_details": classification_details,
                "llm_model": llm_model,
                "warnings": warnings,
                "prompt_versions": prompt_versions,
            }

        metric = extract_metric(question)
        intent: AssistantIntent = "basic_kpi"
        rank_direction: Literal["max", "min"] | None = None
        low_metric: str | None = None
        high_metric: str | None = None
        group_by: str | None = None
        sort_by: str | None = None
        classification_reason = "rule_default_basic_kpi"
        classification_details: dict[str, Any] = {"decision_source": "rules", "matched_keywords": []}

        forecast_keywords = ("proyect", "proximo mes", "forecast", "estim")
        channel_keywords = ("por canal", "google ads", "meta ads")
        vehicle_keywords = ("por modelo", "vehiculo", "modelo", "tipo")
        relational_keywords = ("pocos leads", "muchas ventas", "pocas", "muchas")
        temporal_keywords = ("mes", "evolucion", "mejor", "peor")
        unsupported_keywords = ("presupuesto", "recomenda", "estrategia")

        if any(token in question for token in forecast_keywords):
            intent = "forecast"
            classification_reason = "rule_forecast_keywords"
            classification_details["matched_keywords"] = matched_keywords(question, forecast_keywords)
        elif any(token in question for token in channel_keywords):
            intent = "channel_breakdown"
            classification_reason = "rule_channel_breakdown_keywords"
            classification_details["matched_keywords"] = matched_keywords(question, channel_keywords)
        elif any(token in question for token in vehicle_keywords):
            intent = "vehicle_breakdown"
            if "por modelo" in question:
                group_by = "model"
            elif "tipo" in question and "modelo" not in question:
                group_by = "type"
            else:
                group_by = "type_model"
            sort_by = "total_sales"
            classification_reason = "rule_vehicle_breakdown_keywords"
            classification_details["matched_keywords"] = matched_keywords(question, vehicle_keywords)
        elif ("pocos leads" in question and "muchas ventas" in question) or (
            "pocas" in question and "muchas" in question
        ):
            intent = "relational_analysis"
            low_metric = "total_leads"
            high_metric = "total_sales"
            classification_reason = "rule_relational_pattern_keywords"
            classification_details["matched_keywords"] = matched_keywords(question, relational_keywords)
        elif any(token in question for token in temporal_keywords):
            intent = "temporal_analysis"
            if metric is None:
                metric = "total_sales"
            rank_direction = "min" if any(word in question for word in ["menor", "menos", "peor"]) else "max"
            classification_reason = "rule_temporal_analysis_keywords"
            classification_details["matched_keywords"] = matched_keywords(question, temporal_keywords)
        elif any(word in question for word in unsupported_keywords):
            intent = "unsupported"
            classification_reason = "rule_out_of_scope_business_advice"
            classification_details["matched_keywords"] = matched_keywords(question, unsupported_keywords)

        update_current_span(
            output={"intent": intent, "metric": metric, "source": "rules"},
            metadata={
                "decision_source": "rules",
                "classification_reason": classification_reason,
                "matched_keywords": ",".join(classification_details["matched_keywords"]),
            },
        )
        return {
            "intent": intent,
            "metric": metric,
            "rank_direction": rank_direction,
            "low_metric": low_metric,
            "high_metric": high_metric,
            "group_by": group_by,
            "sort_by": sort_by,
            "classification_source": "rules",
            "classification_reason": classification_reason,
            "classification_details": classification_details,
            "warnings": warnings,
            "prompt_versions": prompt_versions,
        }


def resolve_context(state: AssistantState) -> dict[str, Any]:
    with observation_context(
        "assistant.node.resolve_context",
        as_type="agent",
        input={"thread_id": state.get("thread_id")},
    ):
        question = state.get("normalized_question", "")
        intent = state.get("intent", "basic_kpi")
        metric = state.get("metric")
        group_by = state.get("group_by")
        last_metric = state.get("last_metric")
        last_intent = state.get("last_intent")
        ambiguity_match = detect_ambiguous_question(question)

        if intent == "unsupported":
            update_current_span(
                output={"intent": intent, "metric": metric, "group_by": group_by},
                metadata={"context_resolution": "skipped_for_unsupported_intent"},
            )
            return {
                "intent": intent,
                "metric": metric,
                "group_by": group_by,
            }

        if last_metric is None and last_intent is None and ambiguity_match is not None:
            update_current_span(
                output={"ambiguous_question": True, "source": "guardrail"},
                metadata={
                    "decision_source": "guardrail",
                    "error_reason": ambiguity_match.reason,
                    **ambiguity_match.as_metadata(),
                },
                level="WARNING",
                status_message="guardrail_needs_clarification",
            )
            return {
                "error": (
                    "No me quedo claro que metrica o analisis necesitas. "
                    "Reformulá la consulta indicando, por ejemplo, ventas, leads, mes, canal o proyeccion."
                ),
                "error_reason": ambiguity_match.reason,
                "error_details": ambiguity_match.as_metadata(),
            }

        if metric is None and any(token in question for token in ["y ", "tambien", "ademas", "comparalo"]):
            metric = last_metric or "total_sales"

        if intent == "basic_kpi" and "por canal" in question:
            intent = "channel_breakdown"
        if intent == "basic_kpi" and ("por modelo" in question or "por vehiculo" in question):
            intent = "vehicle_breakdown"
            group_by = "model" if "modelo" in question else "type_model"

        if intent == "basic_kpi" and metric is None and last_intent in {"basic_kpi", "temporal_analysis"}:
            metric = last_metric or "total_sales"

        update_current_span(
            output={"intent": intent, "metric": metric, "group_by": group_by},
            metadata={
                "context_resolution": "applied" if metric != state.get("metric") or group_by != state.get("group_by") else "noop",
                "last_metric_used": (last_metric or "none"),
                "last_intent_used": (last_intent or "none"),
            },
        )
        return {
            "intent": intent,
            "metric": metric,
            "group_by": group_by,
        }
