"""Database configuration and session management."""
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from config import settings

# Create engine
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {},
    echo=settings.debug,
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for all models
Base = declarative_base()


def get_db():
    """Dependency for getting database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context():
    """Context manager for database sessions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database tables and apply tiny SQLite additions for local upgrades."""
    Base.metadata.create_all(bind=engine)

    if "sqlite" in settings.database_url:
        from sqlalchemy import inspect, text

        inspector = inspect(engine)
        columns = {column["name"] for column in inspector.get_columns("mmf_accounts")}
        if "investment_date" not in columns:
            with engine.begin() as connection:
                connection.execute(text("ALTER TABLE mmf_accounts ADD COLUMN investment_date DATE"))
                connection.execute(text(
                    "UPDATE mmf_accounts SET investment_date = DATE(created_at) "
                    "WHERE investment_date IS NULL"
                ))
