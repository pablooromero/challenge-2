from app.schemas.responses import CoverageResponse, DataRange


def build_coverage_placeholder() -> CoverageResponse:
    return CoverageResponse(
        status="pending",
        message="La cobertura real de datos se habilitara cuando integremos MySQL en la fase 2.",
        data_range=DataRange(from_date=None, to_date=None),
    )
