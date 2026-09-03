from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from apps.api.database import get_db
from apps.api.dependencies import get_current_user
from database.models import User, Customer
from apps.api.routers.mock_utils import simulate_timeout, get_tenant_resource
from slowapi import Limiter
from slowapi.util import get_remote_address

router = APIRouter(prefix="/crm", tags=["crm"], dependencies=[Depends(get_current_user), Depends(simulate_timeout)])
limiter = Limiter(key_func=get_remote_address)

@router.get("/customers/{customer_id}")
@limiter.limit("10/minute")
async def get_customer(request: Request, customer_id: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    customer = await get_tenant_resource(db, Customer, customer_id, current_user)
    return {"id": customer.id, "name": customer.name, "email": customer.email, "phone": customer.phone}
