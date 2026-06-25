"""
Workflow Orchestration Service for ReflectAI

Provides workflow management and orchestration capabilities.
In development: Uses async task simulation
In production: Will integrate with Temporal.io
"""

from .engine import WorkflowEngine, get_workflow_engine
from .models import WorkflowContext, WorkflowRequest, WorkflowResponse, WorkflowStatus, WorkflowType
from .temporal_client import get_temporal_client
from .workflows import (
    BatchProcessingWorkflow,
    ConversationWorkflow,
    ParallelAnalysisWorkflow,
    SequentialAnalysisWorkflow,
)

__all__ = [
    # Core engine
    "WorkflowEngine",
    "get_workflow_engine",
    # Temporal client
    "get_temporal_client",
    # Workflows
    "SequentialAnalysisWorkflow",
    "ParallelAnalysisWorkflow",
    "BatchProcessingWorkflow",
    "ConversationWorkflow",
    # Models
    "WorkflowRequest",
    "WorkflowResponse",
    "WorkflowStatus",
    "WorkflowType",
    "WorkflowContext",
]
