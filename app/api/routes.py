from fastapi import APIRouter

from app.schemas.analytics import KpiToolResult
from app.schemas.requests import ChatRequest
from app.schemas.responses import ChatResponse, CoverageResponse, HealthResponse, KpiResponse
from app.services.analytics import get_basic_kpis
from app.services.chat import build_mock_chat_response
from app.services.coverage import build_coverage_response
from app.services.health import build_health_response

router = APIRouter(prefix="/api", tags=["api"])


@router.get("/health", response_model=HealthResponse)
async def get_health() -> HealthResponse:
    return build_health_response()


@router.get("/coverage", response_model=CoverageResponse)
async def get_coverage() -> CoverageResponse:
    return build_coverage_response()


@router.get("/kpis", response_model=KpiResponse)
async def get_kpis() -> KpiResponse:
    result: KpiToolResult = get_basic_kpis()
    return KpiResponse(status="ok", summary=result.summary)


@router.post("/chat", response_model=ChatResponse)
async def post_chat(payload: ChatRequest) -> ChatResponse:
    return build_mock_chat_response(payload.message, payload.thread_id)
