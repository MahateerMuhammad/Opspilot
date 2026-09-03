"""Main FastAPI application module."""
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from apps.api.config import settings
from apps.api.routers import auth, crm, orders, payments, inventory, tickets, email
from apps.api.dependencies import get_current_user, require_role
from database.models import User, RoleEnum
from apps.api.schemas import UserResponse

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="OpsPilot API",
    openapi_url=f"{settings.api_v1_str}/openapi.json",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.cors_origins.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix=settings.api_v1_str)
app.include_router(crm.router, prefix=settings.api_v1_str)
app.include_router(orders.router, prefix=settings.api_v1_str)
app.include_router(payments.router, prefix=settings.api_v1_str)
app.include_router(inventory.router, prefix=settings.api_v1_str)
app.include_router(tickets.router, prefix=settings.api_v1_str)
app.include_router(email.router, prefix=settings.api_v1_str)

@app.get(f"{settings.api_v1_str}/users/me", response_model=UserResponse)
async def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user

@app.get(f"{settings.api_v1_str}/admin-only")
async def admin_only_endpoint(current_user: User = Depends(require_role([RoleEnum.admin]))):
    return {"message": "Hello admin"}
