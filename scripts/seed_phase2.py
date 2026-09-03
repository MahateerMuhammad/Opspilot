"""Seed script for Phase 2: Business Entities and Workflows."""
import asyncio
import os
import sys
import random
from datetime import datetime, timedelta

# Add parent directory to python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from dotenv import load_dotenv

from database.models import (
    Base, Tenant, User, RoleEnum,
    Customer, Order, Payment, OrderStatus, PaymentStatus,
    Product, Inventory, Ticket, TicketStatus,
    Workflow, WorkflowStep, WorkflowRun, WorkflowRunStatus
)
from apps.api.security import get_password_hash

load_dotenv()
database_url = os.getenv("DATABASE_URL")
if not database_url:
    print("DATABASE_URL not found in environment.")
    sys.exit(1)

engine = create_async_engine(database_url, echo=False)
async_session_maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

def random_date(start, end):
    """Generate a random datetime between `start` and `end`"""
    return start + timedelta(
        seconds=random.randint(0, int((end - start).total_seconds())),
    )

async def seed_phase2():
    async with engine.begin() as conn:
        # We assume alembic upgraded the schema, but fallback to create_all for testing locally if no alembic ran
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_maker() as session:
        # Check Tenant
        tenant_name = "Acme Corp"
        result = await session.execute(select(Tenant).where(Tenant.name == tenant_name))
        tenant = result.scalars().first()

        if not tenant:
            tenant = Tenant(name=tenant_name)
            session.add(tenant)
            await session.commit()
            await session.refresh(tenant)
            print(f"Created Tenant: {tenant.name}")

        # Ensure admin user
        admin_email = "admin@acme.com"
        result = await session.execute(select(User).where(User.email == admin_email))
        admin = result.scalars().first()
        if not admin:
            admin = User(tenant_id=tenant.id, email=admin_email, hashed_password=get_password_hash("password123"), role=RoleEnum.admin)
            session.add(admin)
            await session.commit()

        # Seed Customers (approx 30)
        customer_names = [
            "Globex Corporation", "Soylent Corp", "Initech", "Umbrella Corporation",
            "Stark Industries", "Wayne Enterprises", "Cyberdyne Systems", "Oscorp",
            "Massive Dynamic", "Hooli", "Pied Piper", "Aviato", "Goliath National Bank",
            "Dunder Mifflin", "Wernham Hogg", "Vandelay Industries", "Sterling Cooper",
            "Oceanic Airlines", "Virtucon", "MomCorp", "Planet Express", "Monsters Inc",
            "Nakatomi Trading Corp", "Los Pollos Hermanos", "Spacely Space Sprockets",
            "Cogswell Cogs", "Slurm Factory", "Bates Motel", "Tyrell Corporation", "Wonka Industries"
        ]
        
        customers = []
        for name in customer_names:
            email = f"contact@{name.lower().replace(' ', '')}.com"
            customer = Customer(
                tenant_id=tenant.id,
                name=name,
                email=email,
                phone=f"555-{random.randint(100, 999)}-{random.randint(1000, 9999)}"
            )
            session.add(customer)
            customers.append(customer)
        await session.commit()
        for c in customers: await session.refresh(c)
        print(f"Seeded {len(customers)} customers.")

        # Seed Products (some with low inventory for procurement demo)
        product_data = [
            ("Quantum Widget v1", "QW-001", 149.99, 100),
            ("Quantum Widget v2", "QW-002", 299.99, 2), # Low inventory
            ("Flux Capacitor", "FC-99", 999.00, 0), # Out of stock
            ("Plasma Conduit", "PC-01", 45.50, 500),
            ("Neutrino Modulator", "NM-22", 120.00, 5), # Low inventory
            ("Warp Core Ring", "WC-RING", 5500.00, 1) # Low inventory
        ]
        products = []
        for name, sku, price, qty in product_data:
            product = Product(tenant_id=tenant.id, name=name, sku=sku, price=price)
            session.add(product)
            await session.commit()
            await session.refresh(product)
            
            inventory = Inventory(tenant_id=tenant.id, product_id=product.id, quantity_on_hand=qty)
            session.add(inventory)
            products.append(product)
        await session.commit()
        print(f"Seeded {len(products)} products and inventory.")

        # Seed Orders & Payments (50 orders)
        now = datetime.utcnow()
        thirty_days_ago = now - timedelta(days=30)
        
        orders = []
        for i in range(50):
            customer = random.choice(customers)
            status = random.choice([OrderStatus.delivered, OrderStatus.shipped, OrderStatus.processing, OrderStatus.pending, OrderStatus.cancelled])
            order_date = random_date(thirty_days_ago, now)
            
            amount = round(random.uniform(50.0, 5000.0), 2)
            order = Order(
                tenant_id=tenant.id,
                customer_id=customer.id,
                status=status,
                total_amount=amount,
                created_at=order_date
            )
            session.add(order)
            orders.append(order)
            
        await session.commit()
        for o in orders: await session.refresh(o)

        # Seed Payments (Including duplicates for refund demo)
        payments = []
        duplicate_orders = random.sample(orders, 3) # Pick 3 orders for duplicate payment scenarios
        
        for order in orders:
            if order.status != OrderStatus.cancelled:
                # Normal successful payment
                payment = Payment(
                    tenant_id=tenant.id,
                    order_id=order.id,
                    amount=order.total_amount,
                    status=PaymentStatus.completed,
                    transaction_id=f"txn_{uuid.uuid4().hex[:8]}",
                    created_at=order.created_at + timedelta(minutes=5)
                )
                session.add(payment)
                
                # Duplicate payment logic
                if order in duplicate_orders:
                    duplicate_payment = Payment(
                        tenant_id=tenant.id,
                        order_id=order.id,
                        amount=order.total_amount,
                        status=PaymentStatus.completed,
                        transaction_id=f"txn_{uuid.uuid4().hex[:8]}",
                        created_at=order.created_at + timedelta(minutes=6)
                    )
                    session.add(duplicate_payment)
            else:
                # Cancelled order might have a refunded or failed payment
                p_status = random.choice([PaymentStatus.failed, PaymentStatus.refunded])
                payment = Payment(
                    tenant_id=tenant.id,
                    order_id=order.id,
                    amount=order.total_amount,
                    status=p_status,
                    transaction_id=f"txn_{uuid.uuid4().hex[:8]}",
                    created_at=order.created_at + timedelta(minutes=1)
                )
                session.add(payment)
                
        await session.commit()
        print(f"Seeded 50 orders with payments (including 3 duplicate payment scenarios).")

        # Seed a basic Workflow
        workflow = Workflow(
            tenant_id=tenant.id,
            name="Order Fulfillment Process",
            description="Standard steps for fulfilling an order."
        )
        session.add(workflow)
        await session.commit()
        await session.refresh(workflow)
        
        step1 = WorkflowStep(tenant_id=tenant.id, workflow_id=workflow.id, name="Verify Payment", action_type="check_payment", sequence_number=1)
        step2 = WorkflowStep(tenant_id=tenant.id, workflow_id=workflow.id, name="Allocate Inventory", action_type="allocate_inventory", sequence_number=2)
        step3 = WorkflowStep(tenant_id=tenant.id, workflow_id=workflow.id, name="Ship to Customer", action_type="ship_order", sequence_number=3)
        
        session.add_all([step1, step2, step3])
        await session.commit()
        
        print("Seeded sample Workflow and Steps.")
        
        print("Phase 2 Seeding Complete.")

if __name__ == "__main__":
    asyncio.run(seed_phase2())
