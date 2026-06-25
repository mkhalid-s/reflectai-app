"""
Event Factory for generating test event data.
Task 5b: Test Data Factories - EventFactory
"""

import json
import random
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import factory
from factory import Faker, LazyFunction


class EventFactory(factory.Factory):
    """
    Factory for generating event test data for event streams.

    Creates events for testing the Redis pub/sub event system and
    event-driven workflows in the ReflectAI system.
    """

    class Meta:
        model = dict

    # Core identifiers
    id = LazyFunction(lambda: f"event_{uuid.uuid4().hex[:8]}")
    correlation_id = LazyFunction(lambda: f"corr_{uuid.uuid4().hex[:12]}")
    trace_id = LazyFunction(lambda: f"trace_{uuid.uuid4().hex[:16]}")

    # Event classification
    event_type = Faker(
        "random_element",
        elements=[
            "user.activity.created",
            "user.activity.classified",
            "user.activity.completed",
            "user.competency.updated",
            "user.competency.assessed",
            "user.report.requested",
            "user.report.generated",
            "user.report.delivered",
            "workflow.started",
            "workflow.completed",
            "workflow.failed",
            "system.health.check",
            "system.cache.invalidated",
            "system.maintenance.started",
            "integration.slack.message",
            "integration.slack.event",
            "integration.api.called",
        ],
    )

    event_category = factory.LazyAttribute(lambda obj: obj.event_type.split(".")[0])
    event_action = factory.LazyAttribute(lambda obj: obj.event_type.split(".")[-1])

    # Event metadata
    source = Faker(
        "random_element",
        elements=[
            "activity-analyzer",
            "competency-assessor",
            "report-generator",
            "slack-integration",
            "workflow-engine",
            "api-gateway",
            "scheduler",
            "health-monitor",
            "cache-manager",
        ],
    )

    source_version = LazyFunction(
        lambda: f"v{random.randint(1, 3)}.{random.randint(0, 9)}.{random.randint(0, 9)}"
    )

    # Payload data
    payload = factory.LazyFunction(lambda: _generate_event_payload())
    payload_schema_version = "v1.0"

    # Context and routing
    user_id = factory.Maybe(
        decider="event_category",
        yes_declaration=LazyFunction(lambda: f"user_{uuid.uuid4().hex[:8]}"),
        no_declaration=None,
    )

    organization_id = factory.Maybe(
        decider="user_id",
        yes_declaration=LazyFunction(lambda: f"org_{uuid.uuid4().hex[:8]}"),
        no_declaration=None,
    )

    # Temporal information
    timestamp = Faker("date_time_this_month", tzinfo=UTC)
    created_at = factory.LazyAttribute(lambda obj: obj.timestamp)

    # Processing information
    processed = Faker("boolean", chance_of_getting_true=85)
    processed_at = factory.Maybe(
        decider="processed",
        yes_declaration=factory.LazyAttribute(
            lambda obj: obj.timestamp + timedelta(seconds=random.randint(1, 300))
        ),
        no_declaration=None,
    )

    processing_duration_ms = factory.Maybe(
        decider="processed_at",
        yes_declaration=Faker("random_int", min=10, max=5000),
        no_declaration=None,
    )

    # Retry and error handling
    retry_count = 0
    max_retries = 3
    error_message = factory.Maybe(
        decider="processed", yes_declaration=None, no_declaration=Faker("sentence", nb_words=8)
    )

    # Event routing and delivery
    topic = factory.LazyAttribute(lambda obj: obj.event_type.replace(".", "_"))
    partition_key = factory.LazyAttribute(
        lambda obj: obj.user_id or obj.organization_id or "default"
    )

    # Headers and metadata
    headers = factory.LazyFunction(lambda: _generate_event_headers())
    metadata = factory.LazyFunction(lambda: _generate_event_metadata())

    # Priority and delivery
    priority = Faker("random_element", elements=["low", "normal", "high", "urgent"])
    ttl_seconds = Faker("random_int", min=300, max=86400)  # 5 minutes to 1 day

    # Event size and format
    payload_size_bytes = factory.LazyAttribute(
        lambda obj: len(json.dumps(obj.payload, default=str))
    )

    content_encoding = "json"
    content_type = "application/json"

    @classmethod
    def create_user_activity_created(cls, user_id: str | None = None, **kwargs) -> dict[str, Any]:
        """Create a user activity created event."""
        user_id = user_id or f"user_{uuid.uuid4().hex[:8]}"

        return cls(
            event_type="user.activity.created",
            user_id=user_id,
            payload={
                "activity_id": f"activity_{uuid.uuid4().hex[:8]}",
                "user_id": user_id,
                "content": "Completed code review for authentication system",
                "source": "slack",
                "timestamp": datetime.now(UTC).isoformat(),
                "channel_id": f"C{uuid.uuid4().hex[:8].upper()}",
            },
            priority="high",
            **kwargs,
        )

    @classmethod
    def create_user_competency_updated(cls, user_id: str | None = None, **kwargs) -> dict[str, Any]:
        """Create a user competency updated event."""
        user_id = user_id or f"user_{uuid.uuid4().hex[:8]}"

        return cls(
            event_type="user.competency.updated",
            user_id=user_id,
            payload={
                "user_id": user_id,
                "competency_id": f"comp_{uuid.uuid4().hex[:8]}",
                "competency_name": "Python Programming",
                "previous_score": 3.2,
                "new_score": 3.5,
                "evidence_count": 12,
                "updated_by": "system",
            },
            priority="normal",
            **kwargs,
        )

    @classmethod
    def create_workflow_started(cls, workflow_id: str | None = None, **kwargs) -> dict[str, Any]:
        """Create a workflow started event."""
        workflow_id = workflow_id or f"workflow_{uuid.uuid4().hex[:8]}"

        return cls(
            event_type="workflow.started",
            payload={
                "workflow_id": workflow_id,
                "workflow_type": "activity_analysis",
                "initiator": "scheduler",
                "input_params": {
                    "user_id": f"user_{uuid.uuid4().hex[:8]}",
                    "analysis_period": "last_30_days",
                },
                "estimated_duration_minutes": 15,
            },
            priority="normal",
            **kwargs,
        )

    @classmethod
    def create_slack_message_event(cls, user_id: str | None = None, **kwargs) -> dict[str, Any]:
        """Create a Slack message event."""
        user_id = user_id or f"user_{uuid.uuid4().hex[:8]}"

        return cls(
            event_type="integration.slack.message",
            user_id=user_id,
            source="slack-integration",
            payload={
                "user_id": user_id,
                "channel_id": f"C{uuid.uuid4().hex[:8].upper()}",
                "message_ts": f"{int(datetime.now().timestamp())}.123456",
                "text": "Just finished reviewing the API documentation updates",
                "thread_ts": None,
                "message_type": "message",
            },
            priority="high",
            **kwargs,
        )

    @classmethod
    def create_system_health_check(cls, component: str = "database", **kwargs) -> dict[str, Any]:
        """Create a system health check event."""
        return cls(
            event_type="system.health.check",
            source="health-monitor",
            payload={
                "component": component,
                "status": random.choice(["healthy", "degraded", "unhealthy"]),
                "response_time_ms": random.randint(10, 1000),
                "details": {
                    "connections_active": random.randint(5, 50),
                    "memory_usage_percent": random.randint(20, 90),
                },
                "check_type": "automated",
            },
            priority="low" if component != "database" else "high",
            **kwargs,
        )

    @classmethod
    def create_failed_event(cls, error_type: str = "processing_error", **kwargs) -> dict[str, Any]:
        """Create a failed event for error testing."""
        error_messages = {
            "processing_error": "Failed to process event data",
            "validation_error": "Event payload validation failed",
            "timeout_error": "Event processing timed out",
            "dependency_error": "Required service dependency unavailable",
        }

        return cls(
            processed=False,
            error_message=error_messages.get(error_type, "Unknown error occurred"),
            retry_count=random.randint(1, 3),
            **kwargs,
        )

    @classmethod
    def create_high_volume_events(
        cls, count: int = 1000, time_span_hours: int = 1
    ) -> list[dict[str, Any]]:
        """
        Create high volume events for performance testing.

        Args:
            count: Number of events to generate
            time_span_hours: Time span to distribute events across

        Returns:
            List of events for load testing
        """
        events = []
        base_time = datetime.now(UTC) - timedelta(hours=time_span_hours)

        # Event type distribution for realistic load
        event_distributions = {
            "user.activity.created": 0.4,
            "integration.slack.message": 0.3,
            "user.competency.updated": 0.1,
            "workflow.started": 0.05,
            "system.health.check": 0.15,
        }

        for _i in range(count):
            # Distribute events across time span
            offset_seconds = random.randint(0, time_span_hours * 3600)
            event_time = base_time + timedelta(seconds=offset_seconds)

            # Select event type based on distribution
            event_type = random.choices(
                list(event_distributions.keys()), weights=list(event_distributions.values()), k=1
            )[0]

            if event_type == "user.activity.created":
                event = cls.create_user_activity_created(timestamp=event_time)
            elif event_type == "integration.slack.message":
                event = cls.create_slack_message_event(timestamp=event_time)
            elif event_type == "user.competency.updated":
                event = cls.create_user_competency_updated(timestamp=event_time)
            elif event_type == "workflow.started":
                event = cls.create_workflow_started(timestamp=event_time)
            else:
                event = cls.create_system_health_check(timestamp=event_time)

            events.append(event)

        # Sort by timestamp
        events.sort(key=lambda x: x["timestamp"])
        return events

    @classmethod
    def create_event_stream(
        cls, user_id: str, session_duration_minutes: int = 60
    ) -> list[dict[str, Any]]:
        """
        Create a realistic event stream for a user session.

        Args:
            user_id: User ID for all events
            session_duration_minutes: Duration of the session

        Returns:
            List of events representing a user session
        """
        events = []
        session_start = datetime.now(UTC)
        session_end = session_start + timedelta(minutes=session_duration_minutes)

        # Simulate user activity patterns
        activities = [
            ("integration.slack.message", 5),  # Every 5 minutes on average
            ("user.activity.created", 8),  # Every 8 minutes on average
            ("user.competency.updated", 20),  # Every 20 minutes on average
        ]

        current_time = session_start

        while current_time < session_end:
            for event_type, avg_interval in activities:
                # Add some randomness to intervals
                interval_minutes = max(1, random.normalvariate(avg_interval, avg_interval * 0.3))

                if current_time + timedelta(minutes=interval_minutes) <= session_end:
                    event_time = current_time + timedelta(minutes=interval_minutes)

                    if event_type == "integration.slack.message":
                        event = cls.create_slack_message_event(
                            user_id=user_id, timestamp=event_time
                        )
                    elif event_type == "user.activity.created":
                        event = cls.create_user_activity_created(
                            user_id=user_id, timestamp=event_time
                        )
                    else:  # user.competency.updated
                        event = cls.create_user_competency_updated(
                            user_id=user_id, timestamp=event_time
                        )

                    events.append(event)

            current_time += timedelta(minutes=1)  # Advance time

        # Sort by timestamp
        events.sort(key=lambda x: x["timestamp"])
        return events

    @classmethod
    def create_event_chain(cls, count: int = 5) -> list[dict[str, Any]]:
        """
        Create a chain of causally related events.

        Args:
            count: Number of events in the chain

        Returns:
            List of events where each triggers the next
        """
        events = []
        correlation_id = f"corr_{uuid.uuid4().hex[:12]}"
        user_id = f"user_{uuid.uuid4().hex[:8]}"
        base_time = datetime.now(UTC)

        # Define event chain sequence
        chain_sequence = [
            "integration.slack.message",
            "user.activity.created",
            "user.activity.classified",
            "user.competency.updated",
            "user.report.requested",
        ]

        for i in range(min(count, len(chain_sequence))):
            event_time = base_time + timedelta(seconds=i * 30)  # 30 seconds apart
            event_type = chain_sequence[i]

            event = cls(
                event_type=event_type,
                correlation_id=correlation_id,
                user_id=user_id,
                timestamp=event_time,
                headers={
                    **_generate_event_headers(),
                    "causation_id": events[-1]["id"] if events else None,
                },
            )

            events.append(event)

        return events

    @classmethod
    def create_golden_event_dataset(cls, size: int = 5000) -> list[dict[str, Any]]:
        """
        Create golden dataset for event processing testing.

        Args:
            size: Number of events to generate

        Returns:
            List of pre-validated events with expected processing outcomes
        """
        events = []

        # Event type distribution
        distributions = {
            "user.activity.created": int(size * 0.3),
            "user.competency.updated": int(size * 0.2),
            "integration.slack.message": int(size * 0.25),
            "workflow.started": int(size * 0.1),
            "system.health.check": int(size * 0.15),
        }

        for event_type, count in distributions.items():
            for _ in range(count):
                if event_type == "user.activity.created":
                    event = cls.create_user_activity_created()
                elif event_type == "user.competency.updated":
                    event = cls.create_user_competency_updated()
                elif event_type == "integration.slack.message":
                    event = cls.create_slack_message_event()
                elif event_type == "workflow.started":
                    event = cls.create_workflow_started()
                else:
                    event = cls.create_system_health_check()

                # Mark as golden dataset
                event["is_golden"] = True
                event["expected_outcome"] = _generate_expected_outcome(event_type)
                event["processed"] = True

                events.append(event)

        return events


def _generate_event_payload() -> dict[str, Any]:
    """Generate sample event payload data."""
    payloads = {
        "user_activity": {
            "activity_id": f"activity_{uuid.uuid4().hex[:8]}",
            "content": "Updated user profile information",
            "confidence": 0.85,
        },
        "competency_update": {
            "competency_id": f"comp_{uuid.uuid4().hex[:8]}",
            "score_change": 0.3,
            "evidence_added": 2,
        },
        "workflow_event": {
            "workflow_id": f"workflow_{uuid.uuid4().hex[:8]}",
            "step": "processing",
            "progress": 60,
        },
        "system_event": {
            "component": "database",
            "metric": "response_time",
            "value": random.randint(10, 100),
        },
    }

    return random.choice(list(payloads.values()))


def _generate_event_headers() -> dict[str, str]:
    """Generate event headers."""
    return {
        "content-type": "application/json",
        "schema-version": "v1.0",
        "producer": random.choice(["api-service", "scheduler", "slack-bot"]),
        "environment": random.choice(["development", "staging", "production"]),
        "region": random.choice(["us-east-1", "us-west-2", "eu-west-1"]),
    }


def _generate_event_metadata() -> dict[str, Any]:
    """Generate event metadata."""
    return {
        "producer_version": f"v{random.randint(1, 3)}.{random.randint(0, 9)}.{random.randint(0, 9)}",
        "environment": random.choice(["development", "staging", "production"]),
        "datacenter": random.choice(["us-east", "us-west", "eu-central"]),
        "cost_cents": round(random.uniform(0.1, 2.0), 2),
        "sampling_rate": random.choice([1.0, 0.1, 0.01]),
    }


def _generate_expected_outcome(event_type: str) -> dict[str, Any]:
    """Generate expected processing outcome for golden dataset."""
    outcomes = {
        "user.activity.created": {
            "should_trigger_classification": True,
            "expected_downstream_events": ["user.activity.classified"],
            "processing_time_max_ms": 5000,
        },
        "user.competency.updated": {
            "should_update_cache": True,
            "should_trigger_notification": True,
            "processing_time_max_ms": 1000,
        },
        "integration.slack.message": {
            "should_parse_content": True,
            "should_extract_entities": True,
            "processing_time_max_ms": 2000,
        },
        "workflow.started": {
            "should_validate_input": True,
            "should_allocate_resources": True,
            "processing_time_max_ms": 3000,
        },
    }

    return outcomes.get(event_type, {"processing_time_max_ms": 1000})
