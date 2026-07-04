import re

from pydantic import BaseModel, ConfigDict, Field, field_validator

THREAD_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")


class ChatRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    message: str = Field(..., min_length=1, max_length=1000)
    thread_id: str | None = Field(
        default=None,
        min_length=3,
        max_length=120,
        description="Conversation identifier used to preserve context across turns.",
    )

    @field_validator("message")
    @classmethod
    def validate_message(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Message cannot be empty.")
        return value

    @field_validator("thread_id")
    @classmethod
    def validate_thread_id(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not THREAD_ID_PATTERN.fullmatch(value):
            raise ValueError("thread_id may only contain letters, numbers, hyphens, and underscores.")
        return value
