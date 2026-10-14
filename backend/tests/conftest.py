import os
import uuid
import pytest
from unittest.mock import AsyncMock
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Strict offline test environment configuration
os.environ["DATABASE_URL"] = "sqlite:///./test_luxe.db"
os.environ["SECRET_KEY"] = "test_secret_key_luxe_tech_super_secure_32bytes_or_more"
os.environ["ENVIRONMENT"] = "testing"
os.environ["SUPABASE_URL"] = ""
os.environ["SUPABASE_ANON_KEY"] = ""
os.environ["SUPABASE_SERVICE_ROLE_KEY"] = ""
os.environ["GEMINI_API_KEY"] = ""
os.environ["CORS_ORIGINS"] = "http://localhost:5173,http://localhost:3000"

from app.config import get_settings
get_settings.cache_clear()

from app.database import Base, get_db, init_db
from app.database_seed import seed_database
from app.main import app
from app.services.gemini_service import gemini_service
from app.utils.rate_limit import limiter

test_engine = create_engine("sqlite:///./test_luxe.db", connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=test_engine)
    db = TestingSessionLocal()
    seed_database(db)
    db.close()
    yield
    Base.metadata.drop_all(bind=test_engine)
    try:
        if os.path.exists("./test_luxe.db"):
            os.remove("./test_luxe.db")
    except Exception:
        pass


@pytest.fixture
def client():
    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def mock_gemini_api_calls(monkeypatch):
    monkeypatch.setattr(gemini_service, "_call_gemini", AsyncMock(return_value=None))


@pytest.fixture(autouse=True)
def reset_rate_limits():
    limiter.reset()
    yield
    limiter.reset()


@pytest.fixture
def ordinary_user_headers(client):
    unique_email = f"ordinary_{uuid.uuid4().hex[:8]}@luxe.tech"
    reg_resp = client.post("/api/auth/register", json={
        "email": unique_email,
        "password": "Password123!",
        "name": "Ordinary User"
    })
    token = reg_resp.json()["data"]["token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_headers(ordinary_user_headers):
    return ordinary_user_headers


@pytest.fixture
def privileged_user_headers():
    from app.utils.security import create_access_token
    token = create_access_token({
        "sub": f"lead-analyst-{uuid.uuid4().hex[:8]}",
        "email": "analyst@luxe.tech",
        "role": "lead_analyst"
    })
    return {"Authorization": f"Bearer {token}"}
