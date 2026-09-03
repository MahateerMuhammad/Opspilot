import pytest
from httpx import AsyncClient, ASGITransport
import uuid
import datetime
from unittest.mock import AsyncMock, patch, MagicMock

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
        role=RoleEnum.admin,
    )

@pytest.fixture
def override_get_db_and_user(app, mock_db_session, mock_user):
    from apps.api.database import get_db
    from apps.api.dependencies import get_current_user
    async def _get_db_override():
        yield mock_db_session
    async def _get_current_user_override():
        return mock_user
        
    app.dependency_overrides[get_db] = _get_db_override
    app.dependency_overrides[get_current_user] = _get_current_user_override
    yield
    app.dependency_overrides = {}

@pytest.mark.asyncio
async def test_simulate_timeout(app, override_get_db_and_user):
    # With X-Mock-Timeout-Rate = 1.0, it should ALWAYS timeout (504)
    with patch("asyncio.sleep", return_value=None):  # Don't actually sleep in tests
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.get("/api/v1/crm/customers/123", headers={"X-Mock-Timeout-Rate": "1.0"})
            
    assert response.status_code == 504
    assert response.json()["detail"] == "Integration timeout"

@pytest.mark.asyncio
async def test_tenant_isolation_not_found(app, mock_db_session, override_get_db_and_user):
    # Mock DB returns None for tenant isolation (e.g. cross-tenant)
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = None
    mock_db_session.execute.return_value = mock_result
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/v1/crm/customers/123")
        
    # Standard 404 for tenant isolation
    assert response.status_code == 404
    assert "not found or permission denied" in response.json()["detail"]
