"""Seed script for OpsPilot phase 1."""
import asyncio
import os
import sys

# Add parent directory to python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

from database.models import Base, Tenant, User, RoleEnum
from apps.api.security import get_password_hash

load_dotenv()
database_url = os.getenv("DATABASE_URL")
if not database_url:
    print("DATABASE_URL not found in environment.")
    sys.exit(1)

engine = create_async_engine(database_url, echo=True)
async_session_maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def seed():
    # Since we are using Alembic, we don't technically need Base.metadata.create_all
    # But for the seed script, we want to ensure tables exist if alembic hasn't run.
    # Actually, the user will probably run `alembic upgrade head` first, or we do it here.
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_maker() as session:
        # Check if tenant exists
        tenant_name = "Acme Corp"
        import sqlalchemy as sa
        result = await session.execute(sa.select(Tenant).where(Tenant.name == tenant_name))
        tenant = result.scalars().first()

        if not tenant:
            tenant = Tenant(name=tenant_name)
            session.add(tenant)
            await session.commit()
            await session.refresh(tenant)
            print(f"Created Tenant: {tenant.name} ({tenant.id})")

        admin_email = "admin@acme.com"
        result = await session.execute(sa.select(User).where(User.email == admin_email))
        admin = result.scalars().first()

        if not admin:
            admin = User(
                tenant_id=tenant.id,
                email=admin_email,
                hashed_password=get_password_hash("password123"),
                role=RoleEnum.admin
            )
            session.add(admin)
            await session.commit()
            print(f"Created Admin User: {admin.email}")
        else:
            print("Admin user already exists.")

if __name__ == "__main__":
    asyncio.run(seed())
