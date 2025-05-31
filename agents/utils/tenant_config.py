# Temporary tenant config - will be removed for single tenant setup
from agents.orchestrator import WorkflowOrchestrator
from agents.postgres import get_checkpointer

# Single default orchestrator configuration
checkpointer = get_checkpointer()
# Create single orchestrator instance
default_orchestrator = WorkflowOrchestrator(checkpointer)  # Removed tenant_id


def get_default_orchestrator():
    """Get the default workflow orchestrator."""
    return default_orchestrator
