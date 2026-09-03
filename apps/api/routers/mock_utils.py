import os
import random
import asyncio
from fastapi import HTTPException, status, Request
from database.models import User
from database.repository import TenantRepository
from typing import Type, TypeVar
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.ext.asyncio import AsyncSession

ModelType = TypeVar("ModelType", bound=DeclarativeBase)

async def simulate_timeout(request: Request):
    """Dependency to simulate random timeouts for mock endpoints."""
    # Toggle via header or environment
    timeout_rate_str = request.headers.get("X-Mock-Timeout-Rate", os.getenv("MOCK_TIMEOUT_RATE", "0"))
    try:
        timeout_rate = float(timeout_rate_str)
    except ValueError:
        timeout_rate = 0.0

    if timeout_rate > 0 and random.random() < timeout_rate:
        await asyncio.sleep(2) # Simulate delay
        raise HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail="Integration timeout")

async def get_tenant_resource(db: AsyncSession, model: Type[ModelType], resource_id: str, current_user: User):
    """Shared utility to fetch a resource and enforce tenant isolation."""
    repo = TenantRepository(model, db, current_user.tenant_id)
    resource = await repo.get(resource_id)
    if not resource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{model.__name__} not found or permission denied"
        )
    return resource
