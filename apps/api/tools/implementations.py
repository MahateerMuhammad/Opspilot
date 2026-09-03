import httpx
from pydantic import BaseModel, Field
from uuid import UUID
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from apps.api.tools.registry import registry, ToolRisk
from apps.api.tools.idempotency import idempotent
from database.models import Customer, Order, Payment, OrderStatus, PaymentStatus
from apps.api.config import settings

class GetCustomerInput(BaseModel):
    customer_id: str

class GetCustomerOutput(BaseModel):
    id: str
    name: str
    email: str
    phone: Optional[str]

@registry.register(
    name="get_customer",
    description="Retrieve customer details by ID from CRM",
    input_schema=GetCustomerInput,
    output_schema=GetCustomerOutput,
    risk_level=ToolRisk.low
)
async def get_customer_tool(input_data: GetCustomerInput, db: AsyncSession, tenant_id: UUID) -> Dict[str, Any]:
    # Tools can directly query the DB via repository, but to demonstrate they are separate,
    # we could just query the DB directly here for simplicity, simulating the API call.
    result = await db.execute(select(Customer).where(Customer.id == input_data.customer_id, Customer.tenant_id == tenant_id))
    customer = result.scalars().first()
    if not customer:
        raise Exception("Customer not found")
    return {"id": str(customer.id), "name": customer.name, "email": customer.email, "phone": customer.phone}


class ExecuteRefundInput(BaseModel):
    payment_id: str
    idempotency_key: str

class ExecuteRefundOutput(BaseModel):
    id: str
    status: str
    message: str

@registry.register(
    name="execute_refund",
    description="Execute a full refund for a payment.",
    input_schema=ExecuteRefundInput,
    output_schema=ExecuteRefundOutput,
    risk_level=ToolRisk.critical # Will automatically enforce requires_approval
)
@idempotent("execute_refund")
async def execute_refund_tool(input_data: ExecuteRefundInput, db: AsyncSession, tenant_id: UUID) -> Dict[str, Any]:
    result = await db.execute(select(Payment).where(Payment.id == input_data.payment_id, Payment.tenant_id == tenant_id))
    payment = result.scalars().first()
    
    if not payment:
        raise Exception("Payment not found")
        
    if payment.status != PaymentStatus.completed:
        raise Exception("Can only refund completed payments")
        
    payment.status = PaymentStatus.refunded
    db.add(payment)
    await db.commit()
    
    return {"id": str(payment.id), "status": payment.status.value, "message": "Refund executed"}


class CancelOrderInput(BaseModel):
    order_id: str
    reason: str
    idempotency_key: str

class CancelOrderOutput(BaseModel):
    id: str
    status: str
    message: str

@registry.register(
    name="cancel_order",
    description="Cancel an order before it is shipped.",
    input_schema=CancelOrderInput,
    output_schema=CancelOrderOutput,
    risk_level=ToolRisk.high
)
@idempotent("cancel_order")
async def cancel_order_tool(input_data: CancelOrderInput, db: AsyncSession, tenant_id: UUID) -> Dict[str, Any]:
    result = await db.execute(select(Order).where(Order.id == input_data.order_id, Order.tenant_id == tenant_id))
    order = result.scalars().first()
    
    if not order:
        raise Exception("Order not found")
        
    if order.status in [OrderStatus.delivered, OrderStatus.cancelled]:
        raise Exception(f"Cannot cancel order in status {order.status}")
        
    order.status = OrderStatus.cancelled
    db.add(order)
    await db.commit()
    
    return {"id": str(order.id), "status": order.status.value, "message": "Order cancelled"}

