from dataclasses import dataclass
from typing import Any, Literal

ChatMessage = dict[str, str]
PromptType = Literal["text", "chat"]


@dataclass(frozen=True)
class PromptSpec:
    name: str
    prompt_type: PromptType
    prompt: str | list[ChatMessage]
    labels: tuple[str, ...]
    commit_message: str


@dataclass(frozen=True)
class CompiledPrompt:
    name: str
    prompt_type: PromptType
    compiled: str | list[ChatMessage]
    version: int
    label: str | None
    source: str
    is_fallback: bool
    prompt_client: Any | None = None

    def meta(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "label": self.label,
            "source": self.source,
        }
