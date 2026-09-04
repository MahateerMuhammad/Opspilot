import json
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from apps.api.tools.registry import registry
from apps.api.ai.prompts import SYSTEM_PROMPT

class ToolCallRequest(BaseModel):
    tool: str
    args: Dict[str, Any]

class Plan(BaseModel):
    steps: List[ToolCallRequest] = Field(max_length=15)

def format_tool_catalog() -> str:
    catalog = registry.list_tools()
    lines = []
    for name, tool in catalog.items():
        schema_dict = tool.input_schema.model_json_schema()
        lines.append(f"Tool: {name}")
        lines.append(f"Description: {tool.description}")
        lines.append(f"Args: {json.dumps(schema_dict.get('properties', {}))}")
        lines.append("")
    return "\n".join(lines)

def validate_plan(plan: Plan) -> List[str]:
    """
    Validates the plan against the registry.
    Returns a list of error strings. Empty list means success.
    """
    errors = []
    if len(plan.steps) > 15:
        errors.append("Plan exceeds maximum length of 15 steps.")
        
    for i, step in enumerate(plan.steps):
        tool_def = registry.get_tool(step.tool)
        if not tool_def:
            errors.append(f"Step {i+1}: Tool '{step.tool}' is not registered.")
            continue
            
        try:
            # Validate arguments against the Pydantic schema
            tool_def.input_schema(**step.args)
        except Exception as e:
            errors.append(f"Step {i+1}: Invalid arguments for tool '{step.tool}'. Error: {str(e)}")
            
    return errors
