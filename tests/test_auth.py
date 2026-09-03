import pytest
from httpx import AsyncClient
from fastapi import FastAPI
from unittest.mock import AsyncMock, patch
import uuid
import datetime

# Mock the database dependencies before importing the app
from apps.api.database import get_db

@pytest.fixture
def app():
    from apps.api.main import app as main_app
    return main_app

@pytest.fixture
def mock_db_session():
    return AsyncMock()

@pytest.fixture
def mock_user():
    from database.models import User, RoleEnum
    return User(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        email="test@example.com",
        hashed_password="mocked_hash", # Will be mocked in verify_password
        role=RoleEnum.admin,
        created_at=datetime.datetime.utcnow()
    )

@pytest.fixture
def override_get_db(app, mock_db_session):
    async def _get_db_override():
        yield mock_db_session
    
    app.dependency_overrides[get_db] = _get_db_override
    yield
    app.dependency_overrides = {}

@pytest.mark.asyncio
async def test_login_success(app, mock_user, mock_db_session, override_get_db):
    from apps.api.schemas import LoginRequest
    
    # Mock the database result
    from unittest.mock import MagicMock
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = mock_user
    mock_db_session.execute.return_value = mock_result
    
    from httpx import ASGITransport
    # Mock verify_password to return True
    with patch("apps.api.routers.auth.verify_password", return_value=True):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.post("/api/v1/auth/login", json={"email": "test@example.com", "password": "password"})
            
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"

@pytest.mark.asyncio
async def test_login_failure_wrong_password(app, mock_user, mock_db_session, override_get_db):
    from unittest.mock import MagicMock
    from httpx import ASGITransport
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = mock_user
    mock_db_session.execute.return_value = mock_result
    
    # Mock verify_password to return False
    with patch("apps.api.routers.auth.verify_password", return_value=False):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.post("/api/v1/auth/login", json={"email": "test@example.com", "password": "wrongpassword"})
            
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_rate_limiting(app, mock_db_session, override_get_db):
    from unittest.mock import MagicMock
    from httpx import ASGITransport
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = None
    mock_db_session.execute.return_value = mock_result
    
    # Endpoint /login has a 5/minute limit. We will hit it 6 times.
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        for i in range(5):
            response = await ac.post("/api/v1/auth/login", json={"email": "test@example.com", "password": "wrong"})
            assert response.status_code == 401
            
        # The 6th should be 429 Too Many Requests
        response = await ac.post("/api/v1/auth/login", json={"email": "test@example.com", "password": "wrong"})
        assert response.status_code == 429
