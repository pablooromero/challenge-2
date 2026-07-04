import logging
from functools import lru_cache

from openai import APIConnectionError, APIError, APITimeoutError, OpenAI, RateLimitError
from pydantic import ValidationError

from app.agent.llm.prompts import (
    answer_instructions,
    answer_user_prompt,
    classifier_instructions,
    classifier_user_prompt,
)
from app.agent.llm.schemas import ClassificationOutput, FinalAnswerOutput
from app.core.config import get_settings

logger = logging.getLogger(__name__)


@lru_cache
def get_openai_client() -> OpenAI | None:
    settings = get_settings()
    if not settings.openai_api_key:
        return None

    return OpenAI(
        api_key=settings.openai_api_key,
        timeout=settings.openai_timeout_seconds,
    )


def is_llm_enabled() -> bool:
    return get_openai_client() is not None


def _safe_thread_identifier(thread_id: str | None) -> str | None:
    if not thread_id:
        return None

    sanitized = "".join(char for char in thread_id if char.isalnum() or char in {"-", "_"})
    return sanitized[:64] or None


def classify_question_with_llm(
    *,
    question: str,
    conversation: list[dict[str, str]],
    last_metric: str | None,
    last_intent: str | None,
    thread_id: str | None,
) -> tuple[ClassificationOutput | None, list[str], str | None]:
    client = get_openai_client()
    if client is None:
        return None, [], None

    settings = get_settings()
    try:
        response = client.responses.parse(
            model=settings.openai_model,
            input=[
                {"role": "developer", "content": classifier_instructions()},
                {
                    "role": "user",
                    "content": classifier_user_prompt(
                        question=question,
                        conversation=conversation,
                        last_metric=last_metric,
                        last_intent=last_intent,
                    ),
                },
            ],
            text_format=ClassificationOutput,
            text={"verbosity": "medium"},
            temperature=0.1,
            max_output_tokens=250,
            store=False,
            safety_identifier=_safe_thread_identifier(thread_id),
        )
    except (APIConnectionError, APITimeoutError, RateLimitError, APIError, ValidationError) as exc:
        logger.warning("Falling back to rule-based classification: %s", exc)
        return None, ["La clasificacion LLM no estuvo disponible; se uso el fallback deterministico."], None

    parsed = response.output_parsed
    if parsed is None:
        logger.warning("OpenAI structured classifier returned no parsed payload.")
        return None, ["La clasificacion LLM no devolvio una salida valida; se uso el fallback."], None

    return parsed, [], settings.openai_model


def compose_answer_with_llm(
    *,
    question: str,
    intent: str,
    fallback_answer: str,
    tool_result: dict,
    warnings: list[str],
    thread_id: str | None,
) -> tuple[str | None, list[str], str | None]:
    client = get_openai_client()
    if client is None:
        return None, [], None

    settings = get_settings()
    try:
        response = client.responses.parse(
            model=settings.openai_model,
            input=[
                {"role": "developer", "content": answer_instructions()},
                {
                    "role": "user",
                    "content": answer_user_prompt(
                        question=question,
                        intent=intent,
                        fallback_answer=fallback_answer,
                        tool_result=tool_result,
                        warnings=warnings,
                    ),
                },
            ],
            text_format=FinalAnswerOutput,
            text={"verbosity": "medium"},
            temperature=0.2,
            max_output_tokens=220,
            store=False,
            safety_identifier=_safe_thread_identifier(thread_id),
        )
    except (APIConnectionError, APITimeoutError, RateLimitError, APIError, ValidationError) as exc:
        logger.warning("Falling back to deterministic answer composer: %s", exc)
        return None, ["La redaccion LLM no estuvo disponible; se uso la respuesta deterministica."], None

    parsed = response.output_parsed
    if parsed is None or not parsed.answer.strip():
        logger.warning("OpenAI answer composer returned no parsed payload.")
        return None, ["La redaccion LLM no devolvio una salida valida; se uso la respuesta deterministica."], None

    return parsed.answer.strip(), [], settings.openai_model
