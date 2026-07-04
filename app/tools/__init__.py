"""Tooling package reserved for analytical data access and business logic."""

def get_all_tools() -> list:
    from app.tools.analytics_tools import get_analytics_tools
    from app.tools.forecast_tools import get_forecast_tools

    return [*get_analytics_tools(), *get_forecast_tools()]


def get_analytics_tools() -> list:
    from app.tools.analytics_tools import get_analytics_tools as _get_analytics_tools

    return _get_analytics_tools()


def get_forecast_tools() -> list:
    from app.tools.forecast_tools import get_forecast_tools as _get_forecast_tools

    return _get_forecast_tools()


__all__ = ["get_all_tools", "get_analytics_tools", "get_forecast_tools"]
