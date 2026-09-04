import pytest
import uuid
from unittest.mock import AsyncMock, patch, MagicMock

from database.models import WorkflowRun, WorkflowStep, WorkflowRunStatus
from apps.api.engine.workflow import resume_workflow, _execute_with_retry
from apps.api.tools.registry import registry, ToolRisk
import apps.api.tools.implementations  # Ensure tools are registered

@pytest.fixture
def mock_db():
    return AsyncMock()

@pytest.mark.asyncio
async def test_workflow_resume_skips_completed(mock_db):
    tenant_id = uuid.uuid4()
    workflow_id = uuid.uuid4()
    run_id = uuid.uuid4()
    
    step1_id = uuid.uuid4()
    step2_id = uuid.uuid4()
    
    # Workflow run with step1 completed
    mock_run = WorkflowRun(
        id=run_id, 
        tenant_id=tenant_id, 
        workflow_id=workflow_id,
        status=WorkflowRunStatus.pending,
        completed_steps=[{"step_id": str(step1_id), "action": "get_customer"}]
    )
    
    mock_step1 = WorkflowStep(id=step1_id, sequence_number=1, action_type="get_customer")
    mock_step2 = WorkflowStep(id=step2_id, sequence_number=2, action_type="get_customer")
    
    # Mocking db calls
    # 1. select WorkflowRun
    mock_res_run = MagicMock()
    mock_res_run.scalars.return_value.first.return_value = mock_run
    
    # 2. select WorkflowStep
    mock_res_steps = MagicMock()
    mock_res_steps.scalars.return_value.all.return_value = [mock_step1, mock_step2]
    
    mock_db.execute.side_effect = [mock_res_run, mock_res_steps]
    
    # Execute workflow
    with patch("apps.api.engine.workflow._execute_with_retry", new_callable=AsyncMock) as mock_exec:
        with patch("apps.api.engine.workflow.verify_step_state", return_value=True):
            result_run = await resume_workflow(run_id, mock_db, tenant_id)
            
            # Step 1 should be skipped, so execute is called exactly once (for step 2)
            assert mock_exec.call_count == 1
            args, kwargs = mock_exec.call_args
            assert args[0] == "get_customer" # tool_name
            
            assert result_run.status == WorkflowRunStatus.completed
            assert len(result_run.completed_steps) == 2
            assert result_run.completed_steps[1]["step_id"] == str(step2_id)

@pytest.mark.asyncio
async def test_execute_retry_readonly(mock_db):
    # Dummy tool def
    mock_tool = MagicMock()
    
    # Fails twice, succeeds on third
    mock_tool.handler = AsyncMock(side_effect=[Exception("fail1"), Exception("fail2"), {"success": True}])
    
    with patch("apps.api.engine.workflow.registry.get_tool", return_value=mock_tool):
        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            result = await _execute_with_retry("dummy_tool", {}, mock_db, uuid.uuid4(), is_mutating=False)
            
            assert result == {"success": True}
            assert mock_tool.handler.call_count == 3
            assert mock_sleep.call_count == 2

@pytest.mark.asyncio
async def test_execute_no_retry_mutating(mock_db):
    mock_tool = MagicMock()
    
    # Fails immediately
    mock_tool.handler = AsyncMock(side_effect=Exception("mutating fail"))
    
    with patch("apps.api.engine.workflow.registry.get_tool", return_value=mock_tool):
        with pytest.raises(Exception, match="mutating fail"):
            await _execute_with_retry("dummy_mutating", {}, mock_db, uuid.uuid4(), is_mutating=True)
            
        # Ensure it was called exactly once, no retries
        assert mock_tool.handler.call_count == 1
