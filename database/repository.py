"""Base repository enforcing tenant isolation."""
from typing import Type, TypeVar, Generic, Optional, List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import DeclarativeBase

ModelType = TypeVar("ModelType", bound=DeclarativeBase)

class TenantRepository(Generic[ModelType]):
    """Base repository that automatically scopes all queries to a specific tenant."""

    def __init__(self, model: Type[ModelType], session: AsyncSession, tenant_id: UUID):
        self.model = model
        self.session = session
        self.tenant_id = tenant_id

    def _get_base_query(self):
        """Returns a query scoped to the current tenant."""
        # Check if the model actually has a tenant_id to avoid errors on models like Tenant itself,
        # but in this foundation phase, we ensure all business entities do.
        if hasattr(self.model, "tenant_id"):
            return select(self.model).where(self.model.tenant_id == self.tenant_id)
        return select(self.model)

    async def get(self, id: UUID) -> Optional[ModelType]:
        query = self._get_base_query().where(self.model.id == id)
        result = await self.session.execute(query)
        return result.scalars().first()

    async def get_all(self) -> List[ModelType]:
        query = self._get_base_query()
        result = await self.session.execute(query)
        return result.scalars().all()

    async def add(self, obj: ModelType) -> ModelType:
        if hasattr(obj, "tenant_id") and not obj.tenant_id:
            obj.tenant_id = self.tenant_id
        self.session.add(obj)
        await self.session.commit()
        await self.session.refresh(obj)
        return obj
