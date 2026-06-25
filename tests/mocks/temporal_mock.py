#!/usr/bin/env python3
"""
Temporal Workflow Mock Infrastructure for ReflectAI Testing

Provides comprehensive Temporal workflow mocking including:
- Workflow state machine simulation
- Activity execution simulation
- Error and retry simulation
- Signal and query handling
- Workflow execution tracking
"""

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any
from unittest.mock import Mock


class WorkflowState(str, Enum):
    """Temporal workflow execution states."""

    RUNNING = "Running"
    COMPLETED = "Completed"
    FAILED = "Failed"
    CANCELLED = "Cancelled"
    TERMINATED = "Terminated"
    TIMED_OUT = "TimedOut"


class ActivityState(str, Enum):
    """Activity execution states."""

    PENDING = "Pending"
    SCHEDULED = "Scheduled"
    STARTED = "Started"
    COMPLETED = "Completed"
    FAILED = "Failed"
    CANCELLED = "Cancelled"
    TIMED_OUT = "TimedOut"


@dataclass
class MockActivityResult:
    """Mock activity execution result."""

    result: Any
    execution_time: float = 0.1  # seconds
    attempts: int = 1
    error: Exception | None = None


@dataclass
class MockWorkflowExecution:
    """Mock workflow execution configuration."""

    workflow_id: str
    run_id: str
    workflow_type: str
    state: WorkflowState = WorkflowState.RUNNING
    start_time: datetime = field(default_factory=datetime.now)
    activities: dict[str, ActivityState] = field(default_factory=dict)
    results: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    signal_history: list[dict] = field(default_factory=list)
    query_history: list[dict] = field(default_factory=list)


class TemporalActivitySimulator:
    """Simulates Temporal activity execution."""

    def __init__(self):
        self.activity_results = self._initialize_activity_results()
        self.execution_times = self._initialize_execution_times()

    def _initialize_activity_results(self) -> dict[str, MockActivityResult]:
        """Initialize predefined activity results."""
        return {
            "classify_activity": MockActivityResult(
                result={
                    "activity_type": "professional_development",
                    "confidence": 0.95,
                    "category": "learning",
                }
            ),
            "assess_competency": MockActivityResult(
                result={
                    "competency_level": "intermediate",
                    "score": 7.5,
                    "evidence": "Demonstrated strong analytical skills",
                }
            ),
            "process_batch": MockActivityResult(
                result={
                    "processed_count": 10,
                    "success_count": 9,
                    "failed_count": 1,
                    "processing_time": 2.5,
                }
            ),
            "generate_report": MockActivityResult(
                result={
                    "report_id": "rpt_12345",
                    "summary": "Weekly progress report generated successfully",
                    "details": "Report contains 15 activities and 3 competencies",
                }
            ),
            "send_notification": MockActivityResult(
                result={
                    "notification_id": "notif_12345",
                    "sent": True,
                    "recipients": ["user@example.com"],
                    "channel": "email",
                }
            ),
            "update_user_context": MockActivityResult(
                result={
                    "context_updated": True,
                    "new_topics": ["machine_learning", "data_science"],
                    "confidence": 0.92,
                }
            ),
            # Error scenarios
            "failing_activity": MockActivityResult(
                result=None, error=Exception("Simulated activity failure"), attempts=3
            ),
            "slow_activity": MockActivityResult(
                result="Slow activity completed",
                execution_time=5.0,  # 5 seconds
            ),
            "timeout_activity": MockActivityResult(
                result=None, error=Exception("Activity timed out"), execution_time=30.0
            ),
        }

    def _initialize_execution_times(self) -> dict[str, float]:
        """Initialize default execution times for activities."""
        return {
            "classify_activity": 0.5,
            "assess_competency": 0.8,
            "process_batch": 2.0,
            "generate_report": 1.5,
            "send_notification": 0.3,
            "update_user_context": 0.6,
        }

    async def execute_activity(self, activity_name: str, **kwargs) -> Any:
        """Execute a mock activity with realistic timing."""
        if activity_name not in self.activity_results:
            raise Exception(f"Unknown activity: {activity_name}")

        result_config = self.activity_results[activity_name]

        # Simulate execution time
        await asyncio.sleep(result_config.execution_time)

        # Raise error if configured
        if result_config.error:
            raise result_config.error

        return result_config.result

    def get_activity_result(self, activity_name: str) -> MockActivityResult:
        """Get activity result configuration."""
        return self.activity_results.get(activity_name, MockActivityResult(result=None))


class TemporalWorkflowSimulator:
    """Simulates Temporal workflow execution."""

    def __init__(self):
        self.activity_simulator = TemporalActivitySimulator()
        self.active_workflows: dict[str, MockWorkflowExecution] = {}
        self.workflow_counter = 0

    def start_workflow(
        self, workflow_type: str, workflow_id: str | None = None
    ) -> MockWorkflowExecution:
        """Start a new workflow execution."""
        if workflow_id is None:
            workflow_id = f"workflow-{self.workflow_counter}"
            self.workflow_counter += 1

        run_id = str(uuid.uuid4())

        execution = MockWorkflowExecution(
            workflow_id=workflow_id,
            run_id=run_id,
            workflow_type=workflow_type,
            state=WorkflowState.RUNNING,
        )

        self.active_workflows[workflow_id] = execution
        return execution

    async def execute_workflow(self, workflow_id: str, **workflow_args) -> Any:
        """Execute a workflow and return the result."""
        if workflow_id not in self.active_workflows:
            raise Exception(f"Workflow not found: {workflow_id}")

        execution = self.active_workflows[workflow_id]

        try:
            # Simulate workflow execution based on type
            if "ActivityProcessing" in execution.workflow_type:
                result = await self._execute_activity_processing_workflow(
                    execution, **workflow_args
                )
            elif "BatchProcessing" in execution.workflow_type:
                result = await self._execute_batch_processing_workflow(execution, **workflow_args)
            elif "ReportGeneration" in execution.workflow_type:
                result = await self._execute_report_generation_workflow(execution, **workflow_args)
            else:
                result = {"status": "completed", "workflow_id": workflow_id}

            execution.state = WorkflowState.COMPLETED
            execution.results["final"] = result
            return result

        except Exception as e:
            execution.state = WorkflowState.FAILED
            execution.error = str(e)
            raise

    async def _execute_activity_processing_workflow(
        self, execution: MockWorkflowExecution, **kwargs
    ) -> dict:
        """Execute activity processing workflow simulation."""
        activities = ["classify_activity", "assess_competency", "update_user_context"]

        for activity_name in activities:
            execution.activities[activity_name] = ActivityState.COMPLETED
            result = await self.activity_simulator.execute_activity(activity_name, **kwargs)
            execution.results[activity_name] = result

        return {
            "status": "completed",
            "activities_executed": len(activities),
            "results": execution.results,
        }

    async def _execute_batch_processing_workflow(
        self, execution: MockWorkflowExecution, **kwargs
    ) -> dict:
        """Execute batch processing workflow simulation."""
        batch_size = kwargs.get("batch_size", 10)
        execution.activities["process_batch"] = ActivityState.COMPLETED

        result = await self.activity_simulator.execute_activity("process_batch", **kwargs)
        execution.results["batch"] = result

        return {"status": "completed", "batch_size": batch_size, "result": result}

    async def _execute_report_generation_workflow(
        self, execution: MockWorkflowExecution, **kwargs
    ) -> dict:
        """Execute report generation workflow simulation."""
        execution.activities["generate_report"] = ActivityState.COMPLETED
        execution.activities["send_notification"] = ActivityState.COMPLETED

        report_result = await self.activity_simulator.execute_activity("generate_report", **kwargs)
        notification_result = await self.activity_simulator.execute_activity(
            "send_notification", **kwargs
        )

        execution.results["report"] = report_result
        execution.results["notification"] = notification_result

        return {
            "status": "completed",
            "report_generated": True,
            "notification_sent": True,
            "results": {"report": report_result, "notification": notification_result},
        }

    def get_workflow_status(self, workflow_id: str) -> MockWorkflowExecution | None:
        """Get workflow execution status."""
        return self.active_workflows.get(workflow_id)

    def list_workflows(self) -> list[MockWorkflowExecution]:
        """List all active workflow executions."""
        return list(self.active_workflows.values())

    def cancel_workflow(self, workflow_id: str):
        """Cancel a workflow execution."""
        if workflow_id in self.active_workflows:
            self.active_workflows[workflow_id].state = WorkflowState.CANCELLED

    def terminate_workflow(self, workflow_id: str):
        """Terminate a workflow execution."""
        if workflow_id in self.active_workflows:
            self.active_workflows[workflow_id].state = WorkflowState.TERMINATED


class TemporalClientMock:
    """Mock Temporal client for testing."""

    def __init__(self):
        self.workflow_simulator = TemporalWorkflowSimulator()

    def start_workflow(self, workflow_class, workflow_id: str = None, **kwargs):
        """Start a workflow execution."""
        workflow_type = getattr(workflow_class, "__name__", "UnknownWorkflow")
        return self.workflow_simulator.start_workflow(workflow_type, workflow_id)

    async def execute_workflow(self, workflow_id: str, **kwargs):
        """Execute a workflow."""
        return await self.workflow_simulator.execute_workflow(workflow_id, **kwargs)

    def get_workflow_status(self, workflow_id: str):
        """Get workflow execution status."""
        return self.workflow_simulator.get_workflow_status(workflow_id)

    def list_workflows(self):
        """List workflow executions."""
        return self.workflow_simulator.list_workflows()

    def cancel_workflow(self, workflow_id: str):
        """Cancel a workflow execution."""
        self.workflow_simulator.cancel_workflow(workflow_id)

    def terminate_workflow(self, workflow_id: str):
        """Terminate a workflow execution."""
        self.workflow_simulator.terminate_workflow(workflow_id)


class ExternalServiceMock:
    """Mock external services (OAuth, email, webhooks)."""

    def __init__(self):
        self.oauth_tokens: dict[str, dict] = {}
        self.email_history: list[dict] = []
        self.webhook_calls: list[dict] = []

    def create_oauth_mock(self, provider: str = "generic") -> Mock:
        """Create a mock OAuth service."""
        mock_oauth = Mock()

        async def mock_get_token(client_id: str, client_secret: str, **kwargs):
            token = f"mock_token_{provider}_{len(self.oauth_tokens)}"
            self.oauth_tokens[token] = {
                "provider": provider,
                "client_id": client_id,
                "expires_at": datetime.now() + timedelta(hours=1),
            }
            return {"access_token": token, "token_type": "Bearer", "expires_in": 3600}

        async def mock_refresh_token(refresh_token: str):
            return {
                "access_token": f"refreshed_token_{len(self.oauth_tokens)}",
                "token_type": "Bearer",
                "expires_in": 3600,
            }

        mock_oauth.get_token = mock_get_token
        mock_oauth.refresh_token = mock_refresh_token
        return mock_oauth

    def create_email_mock(self) -> Mock:
        """Create a mock email service."""
        mock_email = Mock()

        async def mock_send_email(to: str, subject: str, body: str, **kwargs):
            email_data = {
                "to": to,
                "subject": subject,
                "body": body,
                "timestamp": datetime.now().isoformat(),
                "provider": kwargs.get("provider", "mock"),
            }
            self.email_history.append(email_data)
            return {"message_id": f"msg_{len(self.email_history)}", "status": "sent"}

        mock_email.send = mock_send_email
        return mock_email

    def create_webhook_mock(self, service: str = "generic") -> Mock:
        """Create a mock webhook service."""
        mock_webhook = Mock()

        async def mock_send_webhook(url: str, payload: dict, headers: dict = None, **kwargs):
            webhook_data = {
                "url": url,
                "payload": payload,
                "headers": headers or {},
                "service": service,
                "timestamp": datetime.now().isoformat(),
                "status": "delivered",
            }
            self.webhook_calls.append(webhook_data)
            return {"status_code": 200, "response": "OK"}

        mock_webhook.send = mock_send_webhook
        return mock_webhook

    def get_oauth_history(self) -> list[dict]:
        """Get OAuth token history."""
        return list(self.oauth_tokens.values())

    def get_email_history(self) -> list[dict]:
        """Get email sending history."""
        return self.email_history.copy()

    def get_webhook_history(self) -> list[dict]:
        """Get webhook call history."""
        return self.webhook_calls.copy()

    def clear_history(self):
        """Clear all service call history."""
        self.oauth_tokens.clear()
        self.email_history.clear()
        self.webhook_calls.clear()


# Global instances for easy access
temporal_simulator = TemporalWorkflowSimulator()
temporal_client_mock = TemporalClientMock()
external_service_mock = ExternalServiceMock()


def get_temporal_client_mock() -> TemporalClientMock:
    """Get a pre-configured Temporal client mock."""
    return temporal_client_mock


def get_external_service_mock() -> ExternalServiceMock:
    """Get a pre-configured external service mock."""
    return external_service_mock


def create_workflow_execution(workflow_type: str, workflow_id: str = None) -> MockWorkflowExecution:
    """Create a new workflow execution for testing."""
    return temporal_simulator.start_workflow(workflow_type, workflow_id)
