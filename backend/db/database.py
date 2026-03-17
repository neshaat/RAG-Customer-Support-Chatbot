from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.db.models import Base
from backend.config import DATABASE_URL
import os

# Ensure the DB directory exists for SQLite
db_path = DATABASE_URL.replace("sqlite:///", "")
os.makedirs(os.path.dirname(db_path), exist_ok=True)

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Create all tables."""
    Base.metadata.create_all(bind=engine)


def get_db():
    """Yield a DB session (use as context manager or dependency)."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
