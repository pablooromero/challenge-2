from pydantic import BaseModel, ConfigDict, Field


class ChatRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    message: str = Field(..., min_length=1, max_length=2000)
    thread_id: str | None = Field(
        default=None,
        min_length=3,
        max_length=120,
        description="Conversation identifier used to preserve context across turns.",
    )
