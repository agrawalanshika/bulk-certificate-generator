import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.services import job_processor


@pytest.fixture()
def session_factory():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


@pytest.fixture()
def generated_dir(tmp_path, monkeypatch):
    """Send generated PDFs to a temp dir instead of the real generated/ folder."""
    monkeypatch.setattr(settings, "generated_dir", str(tmp_path))
    return tmp_path


@pytest.fixture()
def client(session_factory, generated_dir, monkeypatch):
    def override_get_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    # Background task opens its own session: point it at the test database too.
    monkeypatch.setattr(job_processor, "SessionLocal", session_factory)
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def db_session(session_factory):
    db = session_factory()
    yield db
    db.close()