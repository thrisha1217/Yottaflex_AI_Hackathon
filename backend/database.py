from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from backend.config import settings

# SQLite needs check_same_thread=False; pool_size is not supported for SQLite
_is_sqlite = settings.DATABASE_URL.startswith("sqlite")

if _is_sqlite:
    engine = create_engine(
        settings.DATABASE_URL,
        connect_args={"check_same_thread": False},
    )
else:
    engine = create_engine(
        settings.DATABASE_URL,
        pool_pre_ping=True,
        pool_size=10,
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI dependency that yields a database session and closes it after use."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
