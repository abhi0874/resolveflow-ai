from collections.abc import Iterator

from fastapi import Request
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

from resolveflow.core.config import Settings


class DatabaseUnavailableError(Exception):
    """Safe public signal for an absent or unreachable database."""


class Database:
    def __init__(self, settings: Settings) -> None:
        if settings.database_url is None:
            raise DatabaseUnavailableError
        self.engine = create_engine(
            make_url(settings.database_url.get_secret_value()),
            pool_size=settings.db_pool_size,
            max_overflow=settings.db_max_overflow,
            pool_timeout=settings.db_pool_timeout,
            pool_pre_ping=True,
            pool_recycle=1800,
            hide_parameters=True,
            connect_args={
                "connect_timeout": settings.db_connect_timeout,
                "options": f"-c statement_timeout={settings.db_statement_timeout_ms}",
            },
        )
        self.sessions = sessionmaker(self.engine, expire_on_commit=False, autoflush=False)

    def dispose(self) -> None:
        self.engine.dispose()


def get_session(request: Request) -> Iterator[Session]:
    database: Database | None = request.app.state.database
    if database is None:
        raise DatabaseUnavailableError
    # Callers explicitly commit their unit of work. Closing rolls back uncommitted
    # work; errors are rolled back before being forwarded to central handlers.
    with database.sessions() as session:
        try:
            yield session
        except Exception:
            session.rollback()
            raise
