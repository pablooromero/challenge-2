from langchain.tools import tool
from pydantic import BaseModel, Field

from app.domain.forecast.projection import forecast_next_month


class ForecastInput(BaseModel):
    start_date: str | None = Field(default=None, description="Inclusive start date in YYYY-MM-DD.")
    end_date: str | None = Field(default=None, description="Inclusive end date in YYYY-MM-DD.")
    vehicle_type: str | None = Field(default=None, description="Optional vehicle type filter.")
    vehicle_model: str | None = Field(default=None, description="Optional vehicle model filter.")


@tool(args_schema=ForecastInput)
def forecast_next_month_tool(
    start_date: str | None = None,
    end_date: str | None = None,
    vehicle_type: str | None = None,
    vehicle_model: str | None = None,
) -> dict:
    """Project next-month leads and sales using deterministic trend and seasonality logic."""
    result = forecast_next_month(
        start_date=start_date,
        end_date=end_date,
        vehicle_type=vehicle_type,
        vehicle_model=vehicle_model,
    )
    return result.model_dump(by_alias=True)


def get_forecast_tools() -> list:
    return [forecast_next_month_tool]
