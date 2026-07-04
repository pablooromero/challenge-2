import json
from typing import Any


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
