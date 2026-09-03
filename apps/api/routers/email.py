from fastapi import APIRouter, Depends, Request
from apps.api.dependencies import get_current_user
from apps.api.routers.mock_utils import simulate_timeout
from slowapi import Limiter
from slowapi.util import get_remote_address
from pydantic import BaseModel

router = APIRouter(prefix="/email", tags=["email"], dependencies=[Depends(get_current_user), Depends(simulate_timeout)])
limiter = Limiter(key_func=get_remote_address)

class EmailRequest(BaseModel):
    to: str
    subject: str
    body: str

@router.post("/send")
@limiter.limit("5/minute")
async def send_email(request: Request, payload: EmailRequest):
    return {"status": "sent", "to": payload.to, "subject": payload.subject}
