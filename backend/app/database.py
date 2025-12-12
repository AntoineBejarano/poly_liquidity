"""
Database connection and session management.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.settings import settings
from app.models.base import Base

# Create engine
# SQLite doesn't support pool_size and max_overflow
if settings.database_url.startswith("sqlite"):
    engine = create_engine(
        settings.database_url,
        pool_pre_ping=True,
        connect_args={"check_same_thread": False},
    )
else:
    engine = create_engine(
        settings.database_url,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
    )

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """
    Dependency for FastAPI to get database session.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

