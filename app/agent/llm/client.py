import logging
from time import sleep

from openai import APIConnectionError, APIError, APITimeoutError, RateLimitError
from pydantic import ValidationError

from app.agent.llm.prompts import answer_user_prompt, classifier_user_prompt
from app.agent.llm.schemas import ClassificationOutput, FinalAnswerOutput
from app.agent.prompting import compile_prompt
from app.core.config import get_settings
from app.observability import observation_context, update_current_span
from app.observability.langfuse import get_openai_client

logger = logging.getLogger(__name__)
TRANSIENT_LLM_ERRORS = (APIConnectionError, APITimeoutError, RateLimitError, APIError)
LLM_FALLBACK_ERRORS = TRANSIENT_LLM_ERRORS + (ValidationError,)


def is_llm_enabled() -> bool:
    return get_openai_client() is not None


def _safe_thread_identifier(thread_id: str | None) -> str | None:
    if not thread_id:
        return None

    sanitized = "".join(char for char in thread_id if char.isalnum() or char in {"-", "_"})
    return sanitized[:64] or None


def _call_with_retry(operation_name: str, callback):
    settings = get_settings()
    max_attempts = settings.openai_max_retries
    backoff_seconds = settings.openai_retry_backoff_seconds

    for attempt in range(1, max_attempts + 1):
        try:
            return callback()
        except TRANSIENT_LLM_ERRORS as exc:
            if attempt >= max_attempts:
                raise
            logger.warning(
                "Retrying %s after transient OpenAI error (%s), attempt %s/%s.",
                operation_name,
                type(exc).__name__,
                attempt,
                max_attempts,
            )
            sleep(backoff_seconds * attempt)


def classify_question_with_llm(
    *,
    question: str,
    conversation: list[dict[str, str]],
    last_metric: str | None,
    last_intent: str | None,
    thread_id: str | None,
) -> tuple[ClassificationOutput | None, list[str], str | None, dict[str, dict[str, str | int | None]]]:
    client = get_openai_client()
    if client is None:
        return None, [], None, {}

    settings = get_settings()
    prompt = compile_prompt(
        "bi-assistant-intent-classifier",
        input_payload=classifier_user_prompt(
            question=question,
            conversation=conversation,
            last_metric=last_metric,
            last_intent=last_intent,
        ),
    )
    with observation_context(
        "assistant.llm.intent_classification",
        as_type="chain",
        input={"question": question, "thread_id": thread_id, "prompt": prompt.meta()},
        metadata={"llm_task": "classification"},
    ):
        try:
            response = _call_with_retry(
                "assistant.llm.intent_classification",
                lambda: client.responses.parse(
                    model=settings.openai_model,
                    input=prompt.compiled,
                    text_format=ClassificationOutput,
                    text={"verbosity": "medium"},
                    temperature=0.1,
                    max_output_tokens=250,
                    store=False,
                    safety_identifier=_safe_thread_identifier(thread_id),
                    name="assistant.llm.intent_classification",
                    langfuse_prompt=prompt.prompt_client if prompt.source == "langfuse" else None,
                    langfuse_public_key=settings.langfuse_public_key,
                    metadata={
                        "llm_task": "classification",
                        "prompt_name": prompt.name,
                        "prompt_version": prompt.version,
                        "prompt_source": prompt.source,
                    },
                ),
            )
        except LLM_FALLBACK_ERRORS as exc:
            logger.warning("Falling back to rule-based classification: %s", exc)
            update_current_span(output={"fallback": "rules", "reason": type(exc).__name__})
            return (
                None,
                ["La clasificacion LLM no estuvo disponible; se uso el fallback deterministico."],
                None,
                {prompt.name: prompt.meta()},
            )

        parsed = response.output_parsed
        if parsed is None:
            logger.warning("OpenAI structured classifier returned no parsed payload.")
            update_current_span(output={"fallback": "rules", "reason": "invalid_output"})
            return (
                None,
                ["La clasificacion LLM no devolvio una salida valida; se uso el fallback."],
                None,
                {prompt.name: prompt.meta()},
            )

        update_current_span(
            output={"intent": parsed.intent, "metric": parsed.metric, "model": settings.openai_model},
        )
        return parsed, [], settings.openai_model, {prompt.name: prompt.meta()}


def compose_answer_with_llm(
    *,
    question: str,
    intent: str,
    fallback_answer: str,
    tool_result: dict,
    warnings: list[str],
    thread_id: str | None,
) -> tuple[str | None, list[str], str | None, dict[str, dict[str, str | int | None]]]:
    client = get_openai_client()
    if client is None:
        return None, [], None, {}

    settings = get_settings()
    prompt = compile_prompt(
        "bi-assistant-answer-composer",
        input_payload=answer_user_prompt(
            question=question,
            intent=intent,
            fallback_answer=fallback_answer,
            tool_result=tool_result,
            warnings=warnings,
        ),
    )
    with observation_context(
        "assistant.llm.answer_composer",
        as_type="chain",
        input={"intent": intent, "thread_id": thread_id, "prompt": prompt.meta()},
        metadata={"llm_task": "answer_composer"},
    ):
        try:
            response = _call_with_retry(
                "assistant.llm.answer_composer",
                lambda: client.responses.parse(
                    model=settings.openai_model,
                    input=prompt.compiled,
                    text_format=FinalAnswerOutput,
                    text={"verbosity": "medium"},
                    temperature=0.2,
                    max_output_tokens=450,
                    store=False,
                    safety_identifier=_safe_thread_identifier(thread_id),
                    name="assistant.llm.answer_composer",
                    langfuse_prompt=prompt.prompt_client if prompt.source == "langfuse" else None,
                    langfuse_public_key=settings.langfuse_public_key,
                    metadata={
                        "llm_task": "answer_composer",
                        "prompt_name": prompt.name,
                        "prompt_version": prompt.version,
                        "prompt_source": prompt.source,
                    },
                ),
            )
        except LLM_FALLBACK_ERRORS as exc:
            logger.warning("Falling back to deterministic answer composer: %s", exc)
            update_current_span(output={"fallback": "rules", "reason": type(exc).__name__})
            return (
                None,
                ["La redaccion LLM no estuvo disponible; se uso la respuesta deterministica."],
                None,
                {prompt.name: prompt.meta()},
            )

        parsed = response.output_parsed
        if parsed is None or not parsed.answer.strip():
            logger.warning("OpenAI answer composer returned no parsed payload.")
            update_current_span(output={"fallback": "rules", "reason": "invalid_output"})
            return (
                None,
                ["La redaccion LLM no devolvio una salida valida; se uso la respuesta deterministica."],
                None,
                {prompt.name: prompt.meta()},
            )

        update_current_span(output={"answer_length": len(parsed.answer.strip()), "model": settings.openai_model})
        return parsed.answer.strip(), [], settings.openai_model, {prompt.name: prompt.meta()}
