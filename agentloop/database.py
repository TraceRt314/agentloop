"""Database setup and connection management."""

import logging
from contextlib import contextmanager
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from .config import settings

logger = logging.getLogger(__name__)


def _build_engine():
    if settings.database_url.startswith("sqlite"):
        return create_engine(
            settings.database_url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            echo=settings.debug,
        )
    return create_engine(settings.database_url, echo=settings.debug)


engine = _build_engine()


def run_migrations() -> None:
    """Run Alembic migrations to bring the DB up to date."""
    try:
        from alembic import command
        from alembic.config import Config

        alembic_cfg = Config("alembic.ini")
        command.upgrade(alembic_cfg, "head")
        logger.info("Alembic migrations applied successfully")
    except Exception:
        logger.warning("Alembic migration failed, falling back to create_all()")
        create_db_and_tables()


def create_db_and_tables():
    """Fallback: create all tables from SQLModel metadata."""
    SQLModel.metadata.create_all(engine)


def get_session():
    """Dependency for FastAPI endpoints."""
    with Session(engine) as session:
        yield session


@contextmanager
def get_sync_session():
    """Context manager for scripts / WebSocket."""
    with Session(engine) as session:
        yield session