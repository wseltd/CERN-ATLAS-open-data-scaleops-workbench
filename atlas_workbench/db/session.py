"""SQLite session factory and synchronous DB bootstrap."""

import os
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from atlas_workbench.db.models import Base

DATABASE_URL: str = os.environ.get(
    "DATABASE_URL",
    "sqlite:///./atlas_workbench.db",
)

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_session() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def bootstrap_db() -> None:
    """Create all tables if they do not already exist."""
    Base.metadata.create_all(bind=engine)
