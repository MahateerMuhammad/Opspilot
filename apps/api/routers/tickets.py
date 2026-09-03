from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from apps.api.database import get_db
from apps.api.dependencies import get_current_user
from database.models import User, Ticket
from apps.api.routers.mock_utils import simulate_timeout, get_tenant_resource
from slowapi import Limiter
from slowapi.util import get_remote_address

router = APIRouter(prefix="/tickets", tags=["tickets"], dependencies=[Depends(get_current_user), Depends(simulate_timeout)])
limiter = Limiter(key_func=get_remote_address)

@router.get("/{ticket_id}")
@limiter.limit("10/minute")
async def get_ticket(request: Request, ticket_id: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    ticket = await get_tenant_resource(db, Ticket, ticket_id, current_user)
    return {"id": ticket.id, "subject": ticket.subject, "status": ticket.status}
