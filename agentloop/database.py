"""Database setup and connection management."""

from contextlib import contextmanager
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from .config import settings


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


def create_db_and_tables():
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