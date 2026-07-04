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
from app.observability import observation_context, update_current_span

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
        with observation_context("mysql.ping", as_type="retriever", input={"table": self.table}):
            with self.connection() as conn:
                try:
                    with conn.cursor() as cursor:
                        cursor.execute("SELECT 1 AS ok")
                        cursor.fetchone()
                    update_current_span(output={"status": "ok"})
                except Exception as exc:
                    logger.exception("Database ping failed.")
                    update_current_span(output={"status": "error"}, level="ERROR", status_message="ping_failed")
                    raise DatabaseConnectionError() from exc

    def fetch_one(
        self,
        query: str,
        params: tuple[Any, ...] | None = None,
        *,
        query_name: str = "fetch_one",
    ) -> dict[str, Any]:
        logger.info("Executing query", extra={"query_name": query_name})
        with observation_context(
            f"mysql.{query_name}",
            as_type="retriever",
            input={"query_name": query_name, "param_count": len(params or ())},
        ):
            with self.connection() as conn:
                try:
                    with conn.cursor() as cursor:
                        cursor.execute(query, params or ())
                        row = cursor.fetchone()
                        result = row or {}
                        update_current_span(output={"row_count": 1 if result else 0})
                        return result
                except Exception as exc:
                    logger.exception("Database query failed.")
                    update_current_span(
                        output={"query_name": query_name},
                        level="ERROR",
                        status_message="query_failed",
                    )
                    raise DatabaseQueryError() from exc

    def fetch_all(
        self,
        query: str,
        params: tuple[Any, ...] | None = None,
        *,
        query_name: str = "fetch_all",
    ) -> list[dict[str, Any]]:
        logger.info("Executing query", extra={"query_name": query_name})
        with observation_context(
            f"mysql.{query_name}",
            as_type="retriever",
            input={"query_name": query_name, "param_count": len(params or ())},
        ):
            with self.connection() as conn:
                try:
                    with conn.cursor() as cursor:
                        cursor.execute(query, params or ())
                        rows = list(cursor.fetchall())
                        update_current_span(output={"row_count": len(rows)})
                        return rows
                except Exception as exc:
                    logger.exception("Database query failed.")
                    update_current_span(
                        output={"query_name": query_name},
                        level="ERROR",
                        status_message="query_failed",
                    )
                    raise DatabaseQueryError() from exc


@lru_cache
def get_database_client() -> DatabaseClient:
    return DatabaseClient(get_settings())
