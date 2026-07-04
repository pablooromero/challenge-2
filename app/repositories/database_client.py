import logging
from contextlib import contextmanager
from functools import lru_cache
from typing import Any, Iterator

import pymysql
from pymysql.connections import Connection
from pymysql.cursors import DictCursor

from app.core.config import Settings, get_settings
from app.core.errors import (
    DatabaseConfigurationError,
    DatabaseConnectionError,
    DatabaseQueryError,
)

logger = logging.getLogger(__name__)


class DatabaseClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def _ensure_configured(self) -> None:
        required = {
            "MYSQL_HOST": self.settings.mysql_host,
            "MYSQL_DB": self.settings.mysql_db,
            "MYSQL_USER": self.settings.mysql_user,
            "MYSQL_PASSWORD": self.settings.mysql_password,
        }
        missing = [key for key, value in required.items() if not value]
        if missing:
            raise DatabaseConfigurationError(
                f"Missing required database settings: {', '.join(missing)}."
            )

    def _connection_kwargs(self) -> dict[str, Any]:
        self._ensure_configured()
        return {
            "host": self.settings.mysql_host,
            "port": self.settings.mysql_port,
            "user": self.settings.mysql_user,
            "password": self.settings.mysql_password,
            "database": self.settings.mysql_db,
            "charset": "utf8mb4",
            "cursorclass": DictCursor,
            "connect_timeout": self.settings.mysql_connect_timeout,
            "read_timeout": self.settings.mysql_read_timeout,
            "write_timeout": self.settings.mysql_write_timeout,
            "autocommit": True,
        }

    @property
    def table(self) -> str:
        return self.settings.mysql_table

    @contextmanager
    def connection(self) -> Iterator[Connection]:
        try:
            conn = pymysql.connect(**self._connection_kwargs())
        except DatabaseConfigurationError:
            raise
        except Exception as exc:
            logger.exception("Failed to open MySQL connection.")
            raise DatabaseConnectionError() from exc

        try:
            yield conn
        finally:
            conn.close()

    def ping(self) -> None:
        with self.connection() as conn:
            try:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT 1 AS ok")
                    cursor.fetchone()
            except Exception as exc:
                logger.exception("Database ping failed.")
                raise DatabaseConnectionError() from exc

    def fetch_one(self, query: str, params: tuple[Any, ...] | None = None) -> dict[str, Any]:
        logger.info("Executing query", extra={"query_name": "fetch_one"})
        with self.connection() as conn:
            try:
                with conn.cursor() as cursor:
                    cursor.execute(query, params or ())
                    row = cursor.fetchone()
                    return row or {}
            except Exception as exc:
                logger.exception("Database query failed.")
                raise DatabaseQueryError() from exc

    def fetch_all(
        self, query: str, params: tuple[Any, ...] | None = None
    ) -> list[dict[str, Any]]:
        logger.info("Executing query", extra={"query_name": "fetch_all"})
        with self.connection() as conn:
            try:
                with conn.cursor() as cursor:
                    cursor.execute(query, params or ())
                    return list(cursor.fetchall())
            except Exception as exc:
                logger.exception("Database query failed.")
                raise DatabaseQueryError() from exc


@lru_cache
def get_database_client() -> DatabaseClient:
    return DatabaseClient(get_settings())
