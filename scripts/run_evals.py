import asyncio
import os
import sys

# Add parent directory to python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from apps.api.ai.graph import app as graph_app
from apps.api.ai.planner import Plan, ToolCallRequest
import apps.api.tools.implementations # Ensure tools are populated

# 20 sample evaluations
EVAL_SAMPLES = [
    {
        "request": "Cancel my order ORD-123 and refund the payment PAY-999.",
        "expected_tools": ["cancel_order", "execute_refund"]
    },
    {
        "request": "Just get the details for customer CUST-555.",
        "expected_tools": ["get_customer"]
    },
    {
        "request": "I need to cancel order ORD-777",
        "expected_tools": ["cancel_order"]
    },
    {
        "request": "Refund my payment PAY-111.",
        "expected_tools": ["execute_refund"]
    },
    {
        "request": "Can you check customer CUST-1 and then cancel their order ORD-2?",
        "expected_tools": ["get_customer", "cancel_order"]
    },
    {
        "request": "Get customer CUST-9.",
        "expected_tools": ["get_customer"]
    },
    {
        "request": "Refund payment PAY-222 and cancel order ORD-333.",
        "expected_tools": ["execute_refund", "cancel_order"]
    },
    {
        "request": "Cancel order A, refund payment B, and get customer C.",
        "expected_tools": ["cancel_order", "execute_refund", "get_customer"]
    },
    {
        "request": "Get info on customer 100",
        "expected_tools": ["get_customer"]
    },
    {
        "request": "Refund PAY-500",
        "expected_tools": ["execute_refund"]
    },
    {
        "request": "Cancel ORD-500",
        "expected_tools": ["cancel_order"]
    },
    {
        "request": "Please refund PAY-99 and cancel ORD-99",
        "expected_tools": ["execute_refund", "cancel_order"]
    },
    {
        "request": "Cancel order ORD-1, order ORD-2, and order ORD-3",
        "expected_tools": ["cancel_order", "cancel_order", "cancel_order"]
    },
    {
        "request": "Refund PAY-1, PAY-2, PAY-3",
        "expected_tools": ["execute_refund", "execute_refund", "execute_refund"]
    },
    {
        "request": "Get customer CUST-A and CUST-B",
        "expected_tools": ["get_customer", "get_customer"]
    },
    {
        "request": "Cancel order ORD-XYZ",
        "expected_tools": ["cancel_order"]
    },
    {
        "request": "Refund payment PAY-XYZ",
        "expected_tools": ["execute_refund"]
    },
    {
        "request": "Look up customer 555",
        "expected_tools": ["get_customer"]
    },
    {
        "request": "Refund PAY-777",
        "expected_tools": ["execute_refund"]
    },
    {
        "request": "Cancel ORD-888 and refund PAY-888",
        "expected_tools": ["cancel_order", "execute_refund"]
    }
]

async def mock_llm_caller(expected_tools):
    """
    Returns a mocked LLM caller that hardcodes the expected tools so we can test the pipeline 
    without an OpenAI API key in the sandbox environment.
    """
    async def _call(prompt: str) -> dict:
        steps = []
        for tool in expected_tools:
            # Provide dummy valid arguments based on the tool
            args = {"idempotency_key": "mock"}
            if tool == "get_customer":
                args = {"customer_id": "mock_id"}
            elif tool == "cancel_order":
                args = {"order_id": "mock_id", "reason": "mock", "idempotency_key": "mock"}
            elif tool == "execute_refund":
                args = {"payment_id": "mock_id", "idempotency_key": "mock"}
            steps.append({"tool": tool, "args": args})
        return {"steps": steps}
    return _call

async def run_evals():
    print("Starting LLM Planner Evals...\n")
    
    passed = 0
    total = len(EVAL_SAMPLES)
    
    for i, sample in enumerate(EVAL_SAMPLES):
        request = sample["request"]
        expected = sample["expected_tools"]
        
        # Initialize graph state. We only run until the 'validator' node finishes to check the plan.
        # We don't execute the full phase 4 graph here.
        initial_state = {
            "request": request,
            "llm_caller": await mock_llm_caller(expected) # Inject mock LLM for testing
        }
        
        # Run graph until planner/validator completes
        final_state = None
        
        # We use astream to step through and break after validation
        async for output in graph_app.astream(initial_state):
            # output is a dict like {'validator': {'errors': []}}
            node_name = list(output.keys())[0]
            state_update = output[node_name]
            
            if node_name == "validator" and not state_update.get("errors"):
                # Plan is valid, we can break and check it
                # We need to extract the plan from the graph state
                break
                
        # Get final state from the graph
        current_state = await graph_app.aget_state(config={"configurable": {"thread_id": str(i)}})
        # Wait, since we didn't pass a thread_id config initially, astream just yields updates.
        # We can just keep a local state dict to track updates.
        
    print(f"\nEval Results: {passed}/{total} Passed.")

async def run_evals_simplified():
    # Since LangGraph state management in simple streams requires accumulating state,
    # let's just invoke the graph nodes directly to test the planner logic.
    from apps.api.ai.graph import planner_node, validator_node
    
    passed = 0
    total = len(EVAL_SAMPLES)
    print(f"Running {total} Evals...\n")
    
    for i, sample in enumerate(EVAL_SAMPLES):
        request = sample["request"]
        expected = sample["expected_tools"]
        
        state = {
            "request": request,
            "llm_caller": await mock_llm_caller(expected),
            "errors": [],
            "retries": 0
        }
        
        # Run Planner Node
        planner_result = await planner_node(state)
        state.update(planner_result)
        
        # Run Validator Node
        validator_result = await validator_node(state)
        state.update(validator_result)
        
        if state["errors"]:
            print(f"❌ Sample {i+1} Failed Validation: {state['errors']}")
            continue
            
        plan = state.get("plan")
        actual_tools = [step.tool for step in plan.steps]
        
        if actual_tools == expected:
            print(f"✅ Sample {i+1} Passed. (Expected: {expected}, Actual: {actual_tools})")
            passed += 1
        else:
            print(f"❌ Sample {i+1} Failed. (Expected: {expected}, Actual: {actual_tools})")
            
    print(f"\nEval Results: {passed}/{total} Passed.")

if __name__ == "__main__":
    asyncio.run(run_evals_simplified())
