import enum
from typing import Dict, Any, List
from uuid import UUID
import json
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.tools.registry import ToolRisk
from database.models import AuditLog

class ApprovalLevel(int, enum.Enum):
    auto = 1
    operator = 2
    manager = 3
    admin = 4

def map_risk_to_approval(risk: ToolRisk) -> ApprovalLevel:
    mapping = {
        ToolRisk.low: ApprovalLevel.auto,
        ToolRisk.medium: ApprovalLevel.operator,
        ToolRisk.high: ApprovalLevel.manager,
        ToolRisk.critical: ApprovalLevel.admin,
    }
    return mapping[risk]

# --- Pure Rules ---
# Same input always produces same output. Context is a simple dictionary.
def rule_high_value_refund(action: str, context: Dict[str, Any]) -> ApprovalLevel:
    if action == "execute_refund" and context.get("amount", 0) > 500:
        return ApprovalLevel.manager
    return ApprovalLevel.auto

def rule_old_order(action: str, context: Dict[str, Any]) -> ApprovalLevel:
    if action in ["cancel_order", "execute_refund"] and context.get("order_age_days", 0) > 30:
        return ApprovalLevel.manager
    return ApprovalLevel.auto

def rule_enterprise_customer(action: str, context: Dict[str, Any]) -> ApprovalLevel:
    if context.get("customer_plan") == "enterprise":
        return ApprovalLevel.manager
    return ApprovalLevel.auto

# Available rules
DEFAULT_RULES = [rule_high_value_refund, rule_old_order, rule_enterprise_customer]

class RulesEngine:
    def __init__(self, rules: List = None):
        self.rules = rules or DEFAULT_RULES

    async def evaluate(
        self, 
        action: str, 
        tool_risk: ToolRisk, 
        context: Dict[str, Any], 
        db: AsyncSession, 
        tenant_id: UUID,
        user_id: UUID
    ) -> ApprovalLevel:
        
        highest_level = ApprovalLevel.auto
        evaluations = []

        # Evaluate rules
        for rule in self.rules:
            result = rule(action, context)
            evaluations.append({"rule": rule.__name__, "result": result.name})
            if result > highest_level:
                highest_level = result

        # Apply hard floor
        floor_level = map_risk_to_approval(tool_risk)
        final_level = highest_level
        if floor_level > highest_level:
            final_level = floor_level
            evaluations.append({"rule": "HARD_FLOOR", "result": final_level.name})

        # Log to audit_logs
        audit_entry = AuditLog(
            tenant_id=tenant_id,
            user_id=user_id,
            action="evaluate_rules",
            resource_type="tool_action",
            resource_id=action,
            input_hash=str(hash(json.dumps(context, sort_keys=True))),
            output_summary=json.dumps({"final_level": final_level.name, "evaluations": evaluations})
        )
        db.add(audit_entry)
        await db.commit()
        
        return final_level
