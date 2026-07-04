from functools import lru_cache

from app.config import get_settings
from app.tools.database import DatabaseClient


@lru_cache
def get_database_client() -> DatabaseClient:
    return DatabaseClient(get_settings())
