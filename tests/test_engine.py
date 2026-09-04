import pytest
import uuid
from unittest.mock import AsyncMock
import json

from apps.api.engine.rules import RulesEngine, ApprovalLevel, rule_enterprise_customer, rule_high_value_refund
from apps.api.tools.registry import ToolRisk

@pytest.mark.asyncio
async def test_rules_engine_agree():
    engine = RulesEngine()
    db = AsyncMock()
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    
    # Both old order (>30 days) and high value refund (>500). Should output manager.
    context = {"amount": 600, "order_age_days": 40}
    # risk low is auto, but rules output manager
    result = await engine.evaluate("execute_refund", ToolRisk.low, context, db, tenant_id, user_id)
    
    assert result == ApprovalLevel.manager
    
    # Check audit log was created
    assert db.add.called
    assert db.commit.called
    audit_log = db.add.call_args[0][0]
    assert audit_log.action == "evaluate_rules"
    evals = json.loads(audit_log.output_summary)
    assert evals["final_level"] == "manager"

@pytest.mark.asyncio
async def test_rules_engine_conflict():
    # One rule says manager, other says auto. Highest wins.
    # refund < 500 (auto), but enterprise customer (manager). Result: manager
    engine = RulesEngine([rule_high_value_refund, rule_enterprise_customer])
    db = AsyncMock()
    
    context = {"amount": 100, "customer_plan": "enterprise"}
    result = await engine.evaluate("execute_refund", ToolRisk.low, context, db, uuid.uuid4(), uuid.uuid4())
    assert result == ApprovalLevel.manager

@pytest.mark.asyncio
async def test_rules_engine_hard_floor_override():
    engine = RulesEngine()
    db = AsyncMock()
    
    # Rule engine says auto (amount=10, age=1, plan=basic)
    context = {"amount": 10, "order_age_days": 1, "customer_plan": "basic"}
    
    # But tool risk is critical -> admin
    result = await engine.evaluate("execute_refund", ToolRisk.critical, context, db, uuid.uuid4(), uuid.uuid4())
    
    # The hard floor MUST override the rules engine
    assert result == ApprovalLevel.admin
    
    # Check audit log shows hard floor
    audit_log = db.add.call_args[0][0]
    evals = json.loads(audit_log.output_summary)
    assert evals["final_level"] == "admin"
    assert any(e["rule"] == "HARD_FLOOR" for e in evals["evaluations"])
