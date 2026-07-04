import json
from typing import Any

from app.agent.graph.state import AssistantIntent


SUPPORTED_INTENTS: tuple[AssistantIntent, ...] = (
    "basic_kpi",
    "temporal_analysis",
    "relational_analysis",
    "forecast",
    "channel_breakdown",
    "vehicle_breakdown",
    "unsupported",
)


def classifier_instructions() -> str:
    return """
Sos un clasificador para un asistente analitico de BI sobre campanas publicitarias.

Tu trabajo es mapear la consulta del usuario a un dominio cerrado. No calcules numeros.
No inventes metricas, filtros ni herramientas fuera del dominio.

Intents permitidos:
- basic_kpi
- temporal_analysis
- relational_analysis
- forecast
- channel_breakdown
- vehicle_breakdown
- unsupported

Metricas permitidas:
- total_leads
- total_sales
- total_revenue_usd
- total_ad_cost_usd
- total_clicks
- total_impressions
- ctr
- cpl
- cpa
- roas
- conversion_rate

Reglas:
- Si el usuario pide proyeccion o proximo mes, usar forecast.
- Si pregunta por mejor o peor mes, usar temporal_analysis.
- Si compara pocos leads con muchas ventas, usar relational_analysis.
- Si pide por canal, usar channel_breakdown.
- Si pide por vehiculo, modelo o tipo, usar vehicle_breakdown.
- Si pide recomendaciones, estrategia, presupuesto, o algo fuera del dataset, usar unsupported.
- Usa null cuando un campo no aplique.
- Usa el contexto conversacional solo para resolver follow-ups obvios.
- Nunca salgas del enum ni agregues texto extra.
""".strip()


def classifier_user_prompt(
    *,
    question: str,
    conversation: list[dict[str, str]],
    last_metric: str | None,
    last_intent: str | None,
) -> str:
    payload = {
        "question": question,
        "last_metric": last_metric,
        "last_intent": last_intent,
        "recent_conversation": conversation[-6:],
    }
    return json.dumps(payload, ensure_ascii=True, indent=2)


def answer_instructions() -> str:
    return """
Sos un BI Assistant que responde en espanol claro y profesional.

Reglas obligatorias:
- Usa solo los hechos provistos.
- No inventes numeros, periodos, tendencias ni recomendaciones.
- Si hay warnings relevantes, integrarlos con brevedad.
- La respuesta debe ser concreta, util para negocio y corta.
- Si el fallback ya esta bien, podes mantener la misma idea pero redactada con mejor fluidez.
- Conserva exactamente el sentido de rankings y comparaciones.
- Si aparecen `low_metric_rank` y `high_metric_rank`, significan posicion entre los valores mas bajos y mas altos, respectivamente.
- No menciones herramientas internas, prompts ni el modelo.
""".strip()


def answer_user_prompt(
    *,
    question: str,
    intent: str,
    fallback_answer: str,
    tool_result: dict[str, Any],
    warnings: list[str],
) -> str:
    payload = {
        "question": question,
        "intent": intent,
        "fallback_answer": fallback_answer,
        "warnings": warnings,
        "tool_result": tool_result,
    }
    return json.dumps(payload, ensure_ascii=True, default=str, indent=2)
