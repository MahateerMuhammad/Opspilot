from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from apps.api.database import get_db
from apps.api.dependencies import get_current_user
from database.models import User, Payment, PaymentStatus
from apps.api.routers.mock_utils import simulate_timeout, get_tenant_resource
from slowapi import Limiter
from slowapi.util import get_remote_address

router = APIRouter(prefix="/payments", tags=["payments"], dependencies=[Depends(get_current_user), Depends(simulate_timeout)])
limiter = Limiter(key_func=get_remote_address)

@router.get("/order/{order_id}")
@limiter.limit("10/minute")
async def get_payments_for_order(request: Request, order_id: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = await db.execute(select(Payment).where(Payment.order_id == order_id, Payment.tenant_id == current_user.tenant_id))
    payments = result.scalars().all()
    return [{"id": p.id, "amount": p.amount, "status": p.status, "transaction_id": p.transaction_id} for p in payments]

@router.post("/{payment_id}/refund")
@limiter.limit("5/minute")
async def refund_payment(request: Request, payment_id: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    payment = await get_tenant_resource(db, Payment, payment_id, current_user)
    if payment.status != PaymentStatus.completed:
        return {"error": "Can only refund completed payments."}
        
    payment.status = PaymentStatus.refunded
    db.add(payment)
    await db.commit()
    return {"id": payment.id, "status": payment.status, "message": "Refund processed"}
