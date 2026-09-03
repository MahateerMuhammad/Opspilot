import pytest
import uuid
from typing import Dict, Any
from unittest.mock import AsyncMock, patch, MagicMock

from apps.api.tools.registry import registry, ToolRisk
from apps.api.tools.implementations import ExecuteRefundInput, execute_refund_tool
from database.models import Payment, PaymentStatus
from database.models.idempotency import IdempotencyKey

def test_registry_security_constraints():
    # Execute refund is critical, must require approval
    refund_tool = registry.get_tool("execute_refund")
    assert refund_tool.risk_level == ToolRisk.critical
    assert refund_tool.requires_approval is True
    
    # Cancel order is high, must require approval
    cancel_tool = registry.get_tool("cancel_order")
    assert cancel_tool.risk_level == ToolRisk.high
    assert cancel_tool.requires_approval is True
    
    # Get customer is low, does not require approval
    get_customer_tool = registry.get_tool("get_customer")
    assert get_customer_tool.risk_level == ToolRisk.low
    assert get_customer_tool.requires_approval is False

@pytest.mark.asyncio
async def test_idempotency_decorator():
    mock_db = AsyncMock()
    tenant_id = uuid.uuid4()
    payment_id = str(uuid.uuid4())
    idem_key = "test-key-123"
    
    input_data = ExecuteRefundInput(payment_id=payment_id, idempotency_key=idem_key)
    
    # First call: no existing record, so idempotency returns None for first query
    mock_result_empty = MagicMock()
    mock_result_empty.scalars.return_value.first.return_value = None
    
    # After it creates in_progress, it calls the tool logic
    # The tool logic will query for the payment
    mock_payment = Payment(id=uuid.UUID(payment_id), tenant_id=tenant_id, status=PaymentStatus.completed)
    mock_result_payment = MagicMock()
    mock_result_payment.scalars.return_value.first.return_value = mock_payment
    
    # Setting up side_effects for db.execute calls in order:
    # 1. Idempotency check -> empty
    # 2. Tool logic -> payment found
    mock_db.execute.side_effect = [mock_result_empty, mock_result_payment]
    
    result = await execute_refund_tool(input_data, db=mock_db, tenant_id=tenant_id)
    assert result["status"] == "refunded"
    
    # Second call: Idempotency check returns a completed record
    mock_completed_record = IdempotencyKey(status="completed", result_data={"id": payment_id, "status": "refunded", "message": "Refund executed"})
    mock_result_completed = MagicMock()
    mock_result_completed.scalars.return_value.first.return_value = mock_completed_record
    
    # Reset side_effect
    mock_db.execute.side_effect = [mock_result_completed]
    
    result_second = await execute_refund_tool(input_data, db=mock_db, tenant_id=tenant_id)
    
    assert result_second == {"id": payment_id, "status": "refunded", "message": "Refund executed"}
    
    # The tool logic (which sets payment to refunded and adds to DB) should only have been called ONCE
    # DB commit is called when: 
    # Call 1: creating in_progress (1), tool logic commit (2), updating to completed (3). Total: 3
    # Call 2: just returns, no commits! Total remains 3.
    assert mock_db.commit.call_count == 3
