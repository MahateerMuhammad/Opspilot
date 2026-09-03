import pytest
import uuid
from unittest.mock import AsyncMock, patch
from database.repository import TenantRepository
from database.models import Customer, Tenant
import sqlalchemy as sa

@pytest.mark.asyncio
async def test_tenant_repository_isolation():
    tenant_id = uuid.uuid4()
    mock_session = AsyncMock()
    
    # We want to check that the query generated automatically adds `where tenant_id = ...`
    repo = TenantRepository(Customer, mock_session, tenant_id)
    
    query = repo._get_base_query()
    
    # The query is a SQLAlchemy Select object
    # We can compile it to string to check for the tenant_id condition
    compiled = str(query.compile(compile_kwargs={"literal_binds": True}))
    
    assert "customers.tenant_id = '" + tenant_id.hex + "'" in compiled

