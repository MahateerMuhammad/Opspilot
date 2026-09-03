from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from apps.api.database import get_db
from apps.api.dependencies import get_current_user
from database.models import User, Order, OrderStatus
from apps.api.routers.mock_utils import simulate_timeout, get_tenant_resource
from slowapi import Limiter
from slowapi.util import get_remote_address
from pydantic import BaseModel

router = APIRouter(prefix="/orders", tags=["orders"], dependencies=[Depends(get_current_user), Depends(simulate_timeout)])
limiter = Limiter(key_func=get_remote_address)

class CancelOrderRequest(BaseModel):
    reason: str

@router.get("/{order_id}")
@limiter.limit("10/minute")
async def get_order(request: Request, order_id: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    order = await get_tenant_resource(db, Order, order_id, current_user)
    return {"id": order.id, "status": order.status, "total_amount": order.total_amount, "customer_id": order.customer_id}

@router.post("/{order_id}/cancel")
@limiter.limit("5/minute")
async def cancel_order(request: Request, order_id: str, payload: CancelOrderRequest, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    order = await get_tenant_resource(db, Order, order_id, current_user)
    if order.status in [OrderStatus.delivered, OrderStatus.cancelled]:
        return {"error": f"Cannot cancel order in status {order.status}"}
    
    order.status = OrderStatus.cancelled
    db.add(order)
    await db.commit()
    return {"id": order.id, "status": order.status, "message": "Order cancelled"}
