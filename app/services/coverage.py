from app.schemas.responses import CoverageResponse
from app.domain.analytics.meta import get_data_coverage


def build_coverage_response() -> CoverageResponse:
    return get_data_coverage()
