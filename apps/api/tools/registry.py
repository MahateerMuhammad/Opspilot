import enum
from typing import Any, Callable, Dict, Optional, Type
from pydantic import BaseModel, Field, create_model

class ToolRisk(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"

class ToolDefinition(BaseModel):
    name: str
    description: str
    input_schema: Type[BaseModel]
    output_schema: Type[BaseModel]
    risk_level: ToolRisk
    requires_approval: bool
    handler: Callable

    def __init__(self, **data):
        # Enforce requires_approval for high/critical tools
        if data.get('risk_level') in [ToolRisk.high, ToolRisk.critical]:
            data['requires_approval'] = True
        super().__init__(**data)

class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, ToolDefinition] = {}

    def register(
        self,
        name: str,
        description: str,
        input_schema: Type[BaseModel],
        output_schema: Type[BaseModel],
        risk_level: ToolRisk,
        requires_approval: bool = False
    ):
        """Decorator to register a tool."""
        def decorator(func: Callable):
            tool_def = ToolDefinition(
                name=name,
                description=description,
                input_schema=input_schema,
                output_schema=output_schema,
                risk_level=risk_level,
                requires_approval=requires_approval,
                handler=func
            )
            self._tools[name] = tool_def
            return func
        return decorator
        
    def get_tool(self, name: str) -> Optional[ToolDefinition]:
        return self._tools.get(name)
        
    def list_tools(self) -> Dict[str, ToolDefinition]:
        return self._tools

# Global registry instance
registry = ToolRegistry()
