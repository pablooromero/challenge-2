import logging
from contextlib import nullcontext
from functools import lru_cache
from typing import Any

from langfuse import Langfuse, propagate_attributes
from langfuse.openai import OpenAI

from app.core.config import get_settings

logger = logging.getLogger(__name__)

APP_VERSION = "0.1.0"


def _sanitize_propagated_metadata(metadata: dict[str, Any] | None) -> dict[str, str] | None:
    if not metadata:
        return None

    sanitized: dict[str, str] = {}
    for key, value in metadata.items():
        normalized_key = "".join(char for char in str(key) if char.isalnum())
        if not normalized_key or value is None:
            continue

        normalized_value = " ".join(str(value).split())[:200]
        if normalized_value:
            sanitized[normalized_key] = normalized_value

    return sanitized or None


def _sanitize_tags(tags: list[str] | None) -> list[str] | None:
    if not tags:
        return None

    sanitized = [" ".join(tag.split())[:200] for tag in tags if tag and " ".join(tag.split())]
    return sanitized or None


@lru_cache
def get_langfuse_client() -> Langfuse | None:
    settings = get_settings()
    if not settings.langfuse_public_key or not settings.langfuse_secret_key:
        return None

    try:
        return Langfuse(
            public_key=settings.langfuse_public_key,
            secret_key=settings.langfuse_secret_key,
            host=settings.langfuse_host,
            environment=settings.app_env,
            release=APP_VERSION,
        )
    except Exception as exc:
        logger.warning("Langfuse client initialization failed: %s", exc)
        return None


@lru_cache
def get_openai_client() -> OpenAI | None:
    settings = get_settings()
    if not settings.openai_api_key:
        return None

    return OpenAI(
        api_key=settings.openai_api_key,
        timeout=settings.openai_timeout_seconds,
    )


def observation_context(name: str, as_type: str = "span", **kwargs: Any):
    client = get_langfuse_client()
    if client is None:
        return nullcontext()

    try:
        return client.start_as_current_observation(name=name, as_type=as_type, **kwargs)
    except Exception as exc:
        logger.warning("Langfuse observation setup failed for %s: %s", name, exc)
        return nullcontext()


def propagation_context(
    *,
    user_id: str | None = None,
    session_id: str | None = None,
    metadata: dict[str, Any] | None = None,
    version: str | None = None,
    tags: list[str] | None = None,
    trace_name: str | None = None,
    environment: str | None = None,
):
    if get_langfuse_client() is None:
        return nullcontext()

    try:
        return propagate_attributes(
            user_id=user_id,
            session_id=session_id,
            metadata=_sanitize_propagated_metadata(metadata),
            version=version,
            tags=_sanitize_tags(tags),
            trace_name=trace_name,
            environment=environment,
        )
    except Exception as exc:
        logger.warning("Langfuse attribute propagation failed: %s", exc)
        return nullcontext()


def update_current_span(**kwargs: Any) -> None:
    client = get_langfuse_client()
    if client is None:
        return

    try:
        client.update_current_span(**kwargs)
    except Exception as exc:
        logger.warning("Langfuse span update failed: %s", exc)


def update_current_generation(**kwargs: Any) -> None:
    client = get_langfuse_client()
    if client is None:
        return

    try:
        client.update_current_generation(**kwargs)
    except Exception as exc:
        logger.warning("Langfuse generation update failed: %s", exc)


def set_trace_io(*, input: Any | None = None, output: Any | None = None) -> None:
    client = get_langfuse_client()
    if client is None:
        return

    try:
        client.set_current_trace_io(input=input, output=output)
    except Exception as exc:
        logger.warning("Langfuse trace IO update failed: %s", exc)


def get_current_trace_details() -> tuple[str | None, str | None]:
    client = get_langfuse_client()
    if client is None:
        return None, None

    try:
        trace_id = client.get_current_trace_id()
        trace_url = client.get_trace_url(trace_id=trace_id) if trace_id else None
        return trace_id, trace_url
    except Exception as exc:
        logger.warning("Langfuse trace lookup failed: %s", exc)
        return None, None


def flush_observability() -> None:
    client = get_langfuse_client()
    if client is None:
        return

    try:
        client.flush()
    except Exception as exc:
        logger.warning("Langfuse flush failed: %s", exc)
