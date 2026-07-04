from fastapi import APIRouter

from app.config import get_settings
from app.schemas.requests import ChatRequest
from app.schemas.responses import ChatResponse, CoverageResponse, HealthResponse
from app.services.chat import build_mock_chat_response
from app.services.coverage import build_coverage_placeholder

router = APIRouter(prefix="/api", tags=["api"])


@router.get("/health", response_model=HealthResponse)
async def get_health() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(
        status="ok",
        app_name=settings.app_name,
        environment=settings.app_env,
        version="0.1.0",
    )


@router.get("/coverage", response_model=CoverageResponse)
async def get_coverage() -> CoverageResponse:
    return build_coverage_placeholder()


@router.post("/chat", response_model=ChatResponse)
async def post_chat(payload: ChatRequest) -> ChatResponse:
    return build_mock_chat_response(payload.message, payload.thread_id)
