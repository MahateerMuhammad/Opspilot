from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from apps.api.database import get_db
from apps.api.dependencies import get_current_user
from database.models import User, Product, Inventory
from apps.api.routers.mock_utils import simulate_timeout, get_tenant_resource
from slowapi import Limiter
from slowapi.util import get_remote_address

router = APIRouter(prefix="/inventory", tags=["inventory"], dependencies=[Depends(get_current_user), Depends(simulate_timeout)])
limiter = Limiter(key_func=get_remote_address)

@router.get("/{sku}")
@limiter.limit("10/minute")
async def check_inventory(request: Request, sku: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = await db.execute(select(Product).where(Product.sku == sku, Product.tenant_id == current_user.tenant_id))
    product = result.scalars().first()
    if not product:
        return {"error": "Product not found"}
        
    result_inv = await db.execute(select(Inventory).where(Inventory.product_id == product.id))
    inv = result_inv.scalars().first()
    return {"sku": sku, "quantity_on_hand": inv.quantity_on_hand if inv else 0}
