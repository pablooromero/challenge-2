from fastapi import APIRouter

from app.schemas.analytics import KpiToolResult
from app.schemas.forecast import ForecastResult
from app.schemas.requests import ChatRequest
from app.schemas.responses import ChatResponse, CoverageResponse, HealthResponse, KpiResponse
from app.domain.analytics.kpis import get_basic_kpis
from app.domain.forecast.projection import forecast_next_month
from app.services.chat import build_chat_response
from app.services.coverage import build_coverage_response
from app.services.health import build_health_response

router = APIRouter(prefix="/api", tags=["api"])


# NOTE: estos handlers son sincronos a proposito. El pipeline hace I/O bloqueante
# (PyMySQL + cliente OpenAI sync), por lo que declararlos `def` hace que FastAPI los
# ejecute en su threadpool y no bloqueen el event loop ni serialicen las requests.
@router.get("/health", response_model=HealthResponse)
def get_health() -> HealthResponse:
    return build_health_response()


@router.get("/coverage", response_model=CoverageResponse)
def get_coverage() -> CoverageResponse:
    return build_coverage_response()


@router.get("/kpis", response_model=KpiResponse)
def get_kpis() -> KpiResponse:
    result: KpiToolResult = get_basic_kpis()
    return KpiResponse(status="ok", summary=result.summary)


@router.get("/forecast", response_model=ForecastResult)
def get_forecast() -> ForecastResult:
    return forecast_next_month()


@router.post("/chat", response_model=ChatResponse)
def post_chat(payload: ChatRequest) -> ChatResponse:
    return build_chat_response(payload.message, payload.thread_id)
