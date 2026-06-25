"""
Workflow Factory for generating test workflow data.
Task 5b: Test Data Factories - WorkflowFactory
"""

import random
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import factory
from factory import Faker, LazyFunction


class WorkflowFactory(factory.Factory):
    """
    Factory for generating workflow test data with states and transitions.

    Creates workflows for testing the Temporal-based workflow execution
    and state management systems.
    """

    class Meta:
        model = dict

    # Core identifiers
    id = LazyFunction(lambda: f"workflow_{uuid.uuid4().hex[:8]}")
    workflow_id = factory.LazyAttribute(lambda obj: obj.id)  # Temporal workflow ID
    run_id = LazyFunction(lambda: f"run_{uuid.uuid4().hex[:8]}")

    # Workflow classification
    workflow_type = Faker(
        "random_element",
        elements=[
            "activity_analysis",
            "competency_assessment",
            "report_generation",
            "user_onboarding",
            "periodic_sync",
            "data_migration",
            "health_check",
        ],
    )

    workflow_name = factory.LazyAttribute(
        lambda obj: f"{obj.workflow_type.replace('_', ' ').title()} Workflow"
    )

    # Execution context
    initiator_type = Faker(
        "random_element", elements=["user", "system", "scheduler", "external_api", "webhook"]
    )

    initiator_id = factory.LazyAttribute(lambda obj: f"{obj.initiator_type}_{uuid.uuid4().hex[:8]}")

    # Current state
    status = Faker(
        "random_element",
        elements=["pending", "running", "paused", "completed", "failed", "cancelled", "timed_out"],
    )

    current_step = Faker(
        "random_element",
        elements=[
            "initialize",
            "validate_input",
            "process_data",
            "analyze_results",
            "generate_output",
            "notify_completion",
            "cleanup",
            "finalize",
        ],
    )

    step_number = Faker("random_int", min=1, max=10)
    total_steps = Faker("random_int", min=5, max=15)

    # Progress tracking
    progress_percentage = factory.LazyAttribute(
        lambda obj: min(100, (obj.step_number / obj.total_steps) * 100)
    )

    # Input and output data
    input_data = factory.LazyFunction(lambda: _generate_workflow_input())
    output_data = factory.Maybe(
        decider="status",
        yes_declaration=factory.LazyFunction(lambda: _generate_workflow_output()),
        no_declaration=None,
    )

    # Execution metadata
    execution_context = factory.LazyFunction(lambda: _generate_execution_context())

    # Error handling
    error_message = factory.Maybe(
        decider="status", yes_declaration=Faker("sentence", nb_words=10), no_declaration=None
    )

    retry_count = factory.Maybe(
        decider="status", yes_declaration=Faker("random_int", min=1, max=3), no_declaration=0
    )

    max_retries = 3

    # Timing information
    created_at = Faker("date_time_this_month", tzinfo=UTC)
    started_at = factory.LazyAttribute(
        lambda obj: obj.created_at + timedelta(seconds=random.randint(1, 300))
    )

    completed_at = factory.Maybe(
        decider="status",
        yes_declaration=factory.LazyAttribute(
            lambda obj: obj.started_at
            + timedelta(
                seconds=random.randint(60, 3600)  # 1 min to 1 hour
            )
        ),
        no_declaration=None,
    )

    duration_seconds = factory.Maybe(
        decider="completed_at",
        yes_declaration=factory.LazyAttribute(
            lambda obj: (obj.completed_at - obj.started_at).total_seconds()
            if obj.completed_at
            else None
        ),
        no_declaration=None,
    )

    # Scheduling
    scheduled_at = factory.LazyAttribute(lambda obj: obj.created_at)
    priority = Faker("random_element", elements=["low", "normal", "high", "urgent"])

    # Workflow history
    state_history = factory.LazyFunction(lambda: _generate_state_history())
    step_history = factory.LazyFunction(lambda: _generate_step_history())

    # Dependencies
    depends_on = factory.LazyFunction(lambda: _generate_dependencies())
    blocks = factory.LazyFunction(lambda: [])  # Workflows blocked by this one

    # Tags and metadata
    tags = factory.LazyFunction(lambda: _generate_workflow_tags())
    metadata = factory.LazyFunction(lambda: _generate_workflow_metadata())

    @classmethod
    def create_activity_analysis_workflow(
        cls, user_id: str | None = None, **kwargs
    ) -> dict[str, Any]:
        """Create an activity analysis workflow."""
        user_id = user_id or f"user_{uuid.uuid4().hex[:8]}"

        return cls(
            workflow_type="activity_analysis",
            workflow_name="Activity Analysis Workflow",
            input_data={
                "user_id": user_id,
                "analysis_period": "last_30_days",
                "include_classifications": True,
                "include_competencies": True,
            },
            current_step="analyze_results",
            step_number=4,
            total_steps=7,
            tags=["analysis", "competency", "user_activity"],
            **kwargs,
        )

    @classmethod
    def create_competency_assessment_workflow(
        cls, user_id: str | None = None, **kwargs
    ) -> dict[str, Any]:
        """Create a competency assessment workflow."""
        user_id = user_id or f"user_{uuid.uuid4().hex[:8]}"

        return cls(
            workflow_type="competency_assessment",
            workflow_name="Competency Assessment Workflow",
            input_data={
                "user_id": user_id,
                "assessment_type": "comprehensive",
                "include_peer_feedback": True,
                "competency_categories": ["technical_skills", "soft_skills"],
            },
            current_step="process_data",
            step_number=3,
            total_steps=8,
            tags=["assessment", "competency", "evaluation"],
            **kwargs,
        )

    @classmethod
    def create_report_generation_workflow(
        cls, report_type: str = "individual", **kwargs
    ) -> dict[str, Any]:
        """Create a report generation workflow."""
        return cls(
            workflow_type="report_generation",
            workflow_name=f"{report_type.title()} Report Generation",
            input_data={
                "report_type": report_type,
                "format": "pdf",
                "include_charts": True,
                "period": "quarterly",
            },
            current_step="generate_output",
            step_number=6,
            total_steps=8,
            tags=["report", "generation", report_type],
            **kwargs,
        )

    @classmethod
    def create_failed_workflow(cls, error_type: str = "timeout", **kwargs) -> dict[str, Any]:
        """Create a failed workflow for error testing."""
        error_messages = {
            "timeout": "Workflow execution timed out after 30 minutes",
            "invalid_input": "Invalid input data provided to workflow",
            "dependency_failure": "Required dependency workflow failed",
            "resource_unavailable": "Required external resource is unavailable",
            "processing_error": "Error occurred during data processing step",
        }

        return cls(
            status="failed",
            error_message=error_messages.get(error_type, "Unknown error occurred"),
            retry_count=3,
            current_step="process_data",
            completed_at=factory.LazyAttribute(
                lambda obj: obj.started_at + timedelta(minutes=random.randint(5, 30))
            ),
            **kwargs,
        )

    @classmethod
    def create_long_running_workflow(cls, **kwargs) -> dict[str, Any]:
        """Create a long-running workflow for performance testing."""
        return cls(
            status="running",
            current_step="process_data",
            step_number=3,
            total_steps=15,  # More steps for longer execution
            started_at=factory.LazyAttribute(
                lambda obj: obj.created_at - timedelta(hours=random.randint(2, 12))
            ),
            tags=["long_running", "batch_processing"],
            **kwargs,
        )

    @classmethod
    def create_scheduled_workflow(
        cls, schedule_time: datetime | None = None, **kwargs
    ) -> dict[str, Any]:
        """Create a scheduled workflow."""
        if not schedule_time:
            schedule_time = datetime.now(UTC) + timedelta(hours=random.randint(1, 24))

        return cls(
            status="pending",
            scheduled_at=schedule_time,
            initiator_type="scheduler",
            current_step="initialize",
            step_number=0,
            tags=["scheduled", "automated"],
            **kwargs,
        )

    @classmethod
    def create_workflow_chain(cls, count: int = 3) -> list[dict[str, Any]]:
        """
        Create a chain of dependent workflows.

        Args:
            count: Number of workflows in the chain

        Returns:
            List of workflows where each depends on the previous
        """
        workflows = []
        previous_workflow_id = None

        for i in range(count):
            workflow = cls(
                workflow_name=f"Chain Step {i + 1}",
                depends_on=[previous_workflow_id] if previous_workflow_id else [],
                tags=["chained", f"step_{i + 1}"],
            )

            if previous_workflow_id:
                # Mark previous workflow as blocking this one
                for prev_workflow in workflows:
                    if prev_workflow["id"] == previous_workflow_id:
                        prev_workflow["blocks"].append(workflow["id"])

            workflows.append(workflow)
            previous_workflow_id = workflow["id"]

        return workflows

    @classmethod
    def create_parallel_workflows(
        cls, count: int = 3, shared_input: dict | None = None
    ) -> list[dict[str, Any]]:
        """
        Create parallel workflows that can run simultaneously.

        Args:
            count: Number of parallel workflows
            shared_input: Common input data for all workflows

        Returns:
            List of independent workflows
        """
        workflows = []
        base_input = shared_input or {"batch_id": f"batch_{uuid.uuid4().hex[:8]}"}

        for i in range(count):
            workflow = cls(
                workflow_name=f"Parallel Task {i + 1}",
                input_data={**base_input, "task_number": i + 1},
                depends_on=[],  # No dependencies for parallel execution
                tags=["parallel", f"task_{i + 1}"],
            )
            workflows.append(workflow)

        return workflows

    @classmethod
    def create_user_workflow_history(cls, user_id: str, days: int = 90) -> list[dict[str, Any]]:
        """
        Create workflow execution history for a user.

        Args:
            user_id: User ID for all workflows
            days: Number of days of history to generate

        Returns:
            List of workflows ordered chronologically
        """
        workflows = []
        base_date = datetime.now(UTC) - timedelta(days=days)

        # Generate 20-50 workflows over the period
        workflow_count = random.randint(20, 50)

        workflow_types = [
            "activity_analysis",
            "competency_assessment",
            "report_generation",
            "periodic_sync",
            "user_onboarding",
        ]

        for _i in range(workflow_count):
            # Distribute workflows across time period
            day_offset = random.randint(0, days)
            hour_offset = random.randint(8, 18)  # Business hours
            created_time = base_date + timedelta(days=day_offset, hours=hour_offset)

            workflow_type = random.choice(workflow_types)

            if workflow_type == "activity_analysis":
                workflow = cls.create_activity_analysis_workflow(
                    user_id=user_id, created_at=created_time
                )
            elif workflow_type == "competency_assessment":
                workflow = cls.create_competency_assessment_workflow(
                    user_id=user_id, created_at=created_time
                )
            elif workflow_type == "report_generation":
                workflow = cls.create_report_generation_workflow(created_at=created_time)
            else:
                workflow = cls(workflow_type=workflow_type, created_at=created_time)

            # Add user context to input data
            workflow["input_data"]["user_id"] = user_id

            workflows.append(workflow)

        # Sort chronologically
        workflows.sort(key=lambda x: x["created_at"])
        return workflows


def _generate_workflow_input() -> dict[str, Any]:
    """Generate sample workflow input data."""
    inputs = {
        "activity_analysis": {
            "user_id": f"user_{uuid.uuid4().hex[:8]}",
            "analysis_period": "last_30_days",
            "include_classifications": True,
        },
        "competency_assessment": {
            "user_id": f"user_{uuid.uuid4().hex[:8]}",
            "assessment_type": "comprehensive",
        },
        "report_generation": {"report_type": "individual", "format": "pdf", "period": "monthly"},
    }

    return random.choice(list(inputs.values()))


def _generate_workflow_output() -> dict[str, Any]:
    """Generate sample workflow output data."""
    return {
        "status": "success",
        "results_count": random.randint(1, 100),
        "processing_time_ms": random.randint(1000, 30000),
        "output_size_bytes": random.randint(1024, 1048576),
        "artifacts": [f"artifact_{uuid.uuid4().hex[:8]}.json"],
    }


def _generate_execution_context() -> dict[str, Any]:
    """Generate workflow execution context."""
    return {
        "executor_id": f"worker_{random.randint(1, 10)}",
        "execution_environment": random.choice(["development", "staging", "production"]),
        "resource_allocation": {
            "cpu_cores": random.randint(1, 4),
            "memory_mb": random.choice([512, 1024, 2048, 4096]),
        },
        "timeout_minutes": random.randint(5, 60),
    }


def _generate_state_history() -> list[dict[str, Any]]:
    """Generate workflow state transition history."""
    states = ["pending", "running", "completed"]
    history = []

    base_time = datetime.now(UTC) - timedelta(hours=1)

    for i, state in enumerate(states):
        timestamp = base_time + timedelta(minutes=i * 10)
        history.append(
            {
                "state": state,
                "timestamp": timestamp.isoformat(),
                "duration_seconds": 600 if i < len(states) - 1 else None,
            }
        )

    return history


def _generate_step_history() -> list[dict[str, Any]]:
    """Generate workflow step execution history."""
    steps = [
        "initialize",
        "validate_input",
        "process_data",
        "analyze_results",
        "generate_output",
        "finalize",
    ]

    history = []
    base_time = datetime.now(UTC) - timedelta(hours=1)

    for i, step in enumerate(steps):
        start_time = base_time + timedelta(minutes=i * 8)
        end_time = start_time + timedelta(minutes=random.randint(2, 10))

        history.append(
            {
                "step": step,
                "started_at": start_time.isoformat(),
                "completed_at": end_time.isoformat(),
                "status": "completed",
                "output": {"step_result": f"Step {i + 1} completed successfully"},
            }
        )

    return history


def _generate_dependencies() -> list[str]:
    """Generate workflow dependencies."""
    # Most workflows have 0-2 dependencies
    dependency_count = random.choices([0, 1, 2], weights=[60, 30, 10], k=1)[0]
    return [f"workflow_{uuid.uuid4().hex[:8]}" for _ in range(dependency_count)]


def _generate_workflow_tags() -> list[str]:
    """Generate workflow tags."""
    all_tags = [
        "user_facing",
        "background",
        "scheduled",
        "critical",
        "low_priority",
        "data_processing",
        "analysis",
        "reporting",
        "sync",
        "cleanup",
    ]

    return random.sample(all_tags, random.randint(1, 4))


def _generate_workflow_metadata() -> dict[str, Any]:
    """Generate additional workflow metadata."""
    return {
        "version": f"v{random.randint(1, 5)}.{random.randint(0, 9)}.{random.randint(0, 9)}",
        "environment": random.choice(["development", "staging", "production"]),
        "region": random.choice(["us-east-1", "us-west-2", "eu-west-1"]),
        "cost_estimate_usd": round(random.uniform(0.01, 5.0), 3),
        "resource_usage": {
            "cpu_seconds": random.randint(10, 3600),
            "memory_peak_mb": random.randint(64, 2048),
            "network_bytes": random.randint(1024, 104857600),
        },
    }
