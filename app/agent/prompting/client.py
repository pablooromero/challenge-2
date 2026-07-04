import logging
from functools import lru_cache
from typing import Any

from langfuse import Langfuse

from app.agent.prompting.catalog import PROMPT_SPECS
from app.agent.prompting.types import CompiledPrompt, PromptSpec
from app.core.config import get_settings

logger = logging.getLogger(__name__)


class LocalPromptClient:
    def __init__(self, spec: PromptSpec, label: str | None) -> None:
        self.name = spec.name
        self.version = 0
        self.labels = [label] if label else []
        self.is_fallback = True
        self.prompt = spec.prompt
        self._prompt_type = spec.prompt_type

    def compile(self, **kwargs: Any) -> str | list[dict[str, str]]:
        return _compile_fallback_prompt(self.prompt, kwargs)

    @property
    def prompt_type(self) -> str:
        return self._prompt_type


@lru_cache
def get_langfuse_prompt_client() -> Langfuse | None:
    settings = get_settings()
    if not settings.langfuse_public_key or not settings.langfuse_secret_key:
        return None

    return Langfuse(
        public_key=settings.langfuse_public_key,
        secret_key=settings.langfuse_secret_key,
        host=settings.langfuse_host,
    )


def is_langfuse_enabled() -> bool:
    return get_langfuse_prompt_client() is not None


def _compile_template(template: str, variables: dict[str, Any]) -> str:
    rendered = template
    for key, value in variables.items():
        rendered = rendered.replace(f"{{{{{key}}}}}", str(value))
    return rendered


def _compile_fallback_prompt(
    prompt: str | list[dict[str, str]],
    variables: dict[str, Any],
) -> str | list[dict[str, str]]:
    if isinstance(prompt, str):
        return _compile_template(prompt, variables)

    return [
        {
            **message,
            "content": _compile_template(message.get("content", ""), variables),
        }
        for message in prompt
    ]


def _get_prompt_spec(name: str) -> PromptSpec:
    try:
        return PROMPT_SPECS[name]
    except KeyError as exc:
        raise ValueError(f"Unknown prompt requested: {name}") from exc


def _resolve_prompt_client(name: str):
    settings = get_settings()
    spec = _get_prompt_spec(name)
    label = settings.langfuse_prompt_label
    client = get_langfuse_prompt_client()

    if client is None:
        return LocalPromptClient(spec, label), "local"

    prompt = client.get_prompt(
        name=spec.name,
        label=label,
        type=spec.prompt_type,
        fallback=spec.prompt,
        cache_ttl_seconds=settings.langfuse_prompt_cache_ttl_seconds,
    )
    source = "langfuse" if not getattr(prompt, "is_fallback", False) else "local"
    if source == "local":
        logger.warning("Using local fallback prompt for %s.", name)
    return prompt, source


def compile_prompt(name: str, **variables: Any) -> CompiledPrompt:
    settings = get_settings()
    prompt_client, source = _resolve_prompt_client(name)
    compiled = prompt_client.compile(**variables)

    return CompiledPrompt(
        name=prompt_client.name,
        prompt_type=_get_prompt_spec(name).prompt_type,
        compiled=compiled,
        version=getattr(prompt_client, "version", 0),
        label=settings.langfuse_prompt_label,
        source=source,
        is_fallback=bool(getattr(prompt_client, "is_fallback", False)),
        prompt_client=prompt_client,
    )
