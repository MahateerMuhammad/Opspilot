import functools
import uuid
from typing import Callable, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database.models.idempotency import IdempotencyKey

def idempotent(tool_name: str):
    """
    Decorator for mutating tools to ensure idempotency.
    The wrapped function must accept `db: AsyncSession`, `tenant_id: UUID`, 
    and an optional `idempotency_key: str` (either in kwargs or inside an input Pydantic model).
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            db: AsyncSession = kwargs.get('db')
            tenant_id = kwargs.get('tenant_id')
            
            if not db or not tenant_id:
                raise ValueError("idempotent decorator requires 'db' and 'tenant_id' in kwargs")
                
            # Try to extract idempotency_key from kwargs, or from an input model in kwargs
            i_key = kwargs.get('idempotency_key')
            if not i_key:
                # Look inside pydantic models passed as kwargs
                for arg in kwargs.values():
                    if hasattr(arg, 'idempotency_key') and arg.idempotency_key:
                        i_key = arg.idempotency_key
                        break
            
            if not i_key:
                # Generate a random one if caller didn't provide it (one-off execution)
                i_key = f"auto_{uuid.uuid4().hex}"
                
            # Check existing key
            result = await db.execute(
                select(IdempotencyKey).where(
                    IdempotencyKey.tenant_id == tenant_id,
                    IdempotencyKey.key == i_key,
                    IdempotencyKey.tool_name == tool_name
                )
            )
            existing_record = result.scalars().first()
            
            if existing_record:
                if existing_record.status == "completed":
                    return existing_record.result_data
                elif existing_record.status == "in_progress":
                    raise Exception(f"Operation {tool_name} with key {i_key} is already in progress.")
            
            # Create in_progress record
            record = IdempotencyKey(
                tenant_id=tenant_id,
                key=i_key,
                tool_name=tool_name,
                status="in_progress"
            )
            db.add(record)
            await db.commit()
            await db.refresh(record)
            
            try:
                # Execute the actual tool
                result_data = await func(*args, **kwargs)
                
                # If result is a pydantic model, convert to dict
                if hasattr(result_data, 'model_dump'):
                    store_data = result_data.model_dump(mode='json')
                else:
                    store_data = result_data

                record.status = "completed"
                record.result_data = store_data
                db.add(record)
                await db.commit()
                return result_data
                
            except Exception as e:
                # On failure, we remove or mark failed so it can be retried
                record.status = "failed"
                record.result_data = {"error": str(e)}
                db.add(record)
                await db.commit()
                raise e
                
        return wrapper
    return decorator
