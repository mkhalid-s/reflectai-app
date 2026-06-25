"""
Activity Factory for generating test activity data.
Task 5b: Test Data Factories - ActivityFactory
"""

import random
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import factory
from factory import Faker, LazyFunction
from faker import Faker as FakerInstance

# Create faker instance for use in LazyFunction
fake = FakerInstance()


class ActivityFactory(factory.Factory):
    """
    Factory for generating activity test data with different classifications.

    Creates activities across various categories, confidence levels,
    and sources
    to test activity classification and competency mapping systems.
    """

    class Meta:
        model = dict

    # Core identifiers
    id = LazyFunction(lambda: f"activity_{uuid.uuid4().hex[:8]}")
    user_id = LazyFunction(lambda: f"user_{uuid.uuid4().hex[:8]}")

    # Content and metadata
    content = Faker("sentence", nb_words=15)
    raw_content = factory.LazyAttribute(lambda obj: obj.content)
    # For preprocessing tests

    # Classification and confidence
    category = Faker(
        "random_element",
        elements=[
            "technical_work",
            "code_review",
            "mentoring",
            "planning",
            "documentation",
            "testing",
            "debugging",
            "research",
            "meetings",
            "project_management",
            "learning",
            "other",
        ],
    )

    subcategory = factory.LazyAttribute(lambda obj: _get_subcategory(obj.category))

    confidence = Faker(
        "pyfloat", left_digits=0, right_digits=2, positive=True, min_value=0.1, max_value=1.0
    )

    # Source and context
    source = Faker(
        "random_element",
        elements=["slack", "github", "jira", "confluence", "calendar", "email", "manual"],
    )

    source_id = LazyFunction(lambda: f"src_{uuid.uuid4().hex[:12]}")
    channel_id = factory.Maybe(
        decider="source",
        yes_declaration=LazyFunction(lambda: f"C{uuid.uuid4().hex[:8].upper()}"),
        no_declaration=None,
    )

    # Temporal information
    timestamp = Faker("date_time_this_year", tzinfo=UTC)
    created_at = factory.LazyAttribute(lambda obj: obj.timestamp)
    processed_at = factory.LazyAttribute(
        lambda obj: obj.timestamp + timedelta(minutes=random.randint(1, 30))
    )

    # Analysis results
    keywords = factory.LazyFunction(
        lambda: fake.random_elements(
            elements=[
                "python",
                "react",
                "api",
                "database",
                "testing",
                "bug",
                "feature",
                "review",
                "merge",
                "deploy",
                "docker",
                "kubernetes",
                "aws",
                "redis",
                "postgresql",
                "authentication",
                "security",
                "performance",
                "refactor",
            ],
            length=random.randint(1, 5),
            unique=True,
        )
    )

    # Competency mappings
    competency_mappings = factory.LazyFunction(lambda: _generate_competency_mappings())

    # Evidence and validation
    evidence_strength = Faker(
        "pyfloat", left_digits=0, right_digits=2, positive=True, min_value=0.1, max_value=1.0
    )
    human_validated = Faker("boolean", chance_of_getting_true=15)
    validation_feedback = factory.Maybe(
        "human_validated",
        yes_declaration=Faker(
            "random_element",
            elements=["correct", "incorrect_category", "incorrect_competency", "needs_review"],
        ),
        no_declaration=None,
    )

    # Processing status
    processing_status = Faker(
        "random_element", elements=["pending", "processing", "completed", "failed", "skipped"]
    )

    error_message = factory.Maybe(
        decider="processing_status",
        yes_declaration=Faker("sentence", nb_words=10),
        no_declaration=None,
    )

    @classmethod
    def create_code_review(cls, **kwargs) -> dict[str, Any]:
        """Create a code review activity."""
        content_options = [
            "Reviewed pull request #123 for authentication improvements",
            "Completed code review for user profile API changes",
            "Reviewed and approved database migration changes",
            "Provided feedback on React component refactoring",
            "Reviewed security changes for JWT token handling",
        ]

        return cls(
            content=random.choice(content_options),
            category="code_review",
            subcategory="pull_request_review",
            keywords=["code", "review", "pull", "request"],
            confidence=Faker("pyfloat", min_value=0.8, max_value=1.0),
            **kwargs,
        )

    @classmethod
    def create_mentoring_activity(cls, **kwargs) -> dict[str, Any]:
        """Create a mentoring/teaching activity."""
        content_options = [
            "Helped junior developer with React state management",
            "Mentored team member on API design best practices",
            "Conducted 1:1 session about career development",
            "Guided new hire through codebase architecture",
            "Shared knowledge about testing strategies",
        ]

        return cls(
            content=random.choice(content_options),
            category="mentoring",
            subcategory="knowledge_sharing",
            keywords=["help", "mentor", "guide", "teach"],
            confidence=Faker("pyfloat", min_value=0.7, max_value=0.95),
            **kwargs,
        )

    @classmethod
    def create_technical_work(cls, **kwargs) -> dict[str, Any]:
        """Create a technical implementation activity."""
        content_options = [
            "Implemented user authentication using JWT tokens",
            "Built REST API for user profile management",
            "Fixed critical bug in payment processing system",
            "Added Redis caching to improve response times",
            "Refactored database queries for better performance",
        ]

        return cls(
            content=random.choice(content_options),
            category="technical_work",
            subcategory="implementation",
            keywords=["implemented", "built", "fixed", "added", "refactored"],
            confidence=Faker("pyfloat", min_value=0.75, max_value=1.0),
            **kwargs,
        )

    @classmethod
    def create_documentation(cls, **kwargs) -> dict[str, Any]:
        """Create a documentation activity."""
        content_options = [
            "Updated API documentation for v2.0 release",
            "Wrote technical specification for new feature",
            "Created troubleshooting guide for common issues",
            "Documented deployment procedures for new team members",
            "Updated README with setup instructions",
        ]

        return cls(
            content=random.choice(content_options),
            category="documentation",
            subcategory="technical_writing",
            keywords=["documentation", "wrote", "updated", "guide"],
            confidence=Faker("pyfloat", min_value=0.6, max_value=0.9),
            **kwargs,
        )

    @classmethod
    def create_low_confidence_activity(cls, **kwargs) -> dict[str, Any]:
        """Create an activity with low classification confidence."""
        ambiguous_content = [
            "Had a meeting about the thing we discussed",
            "Worked on some stuff for the project",
            "Fixed various issues and made improvements",
            "Did some research and analysis for the team",
            "Attended session about work-related topics",
        ]

        return cls(
            content=random.choice(ambiguous_content),
            category="other",
            subcategory="unclear",
            confidence=Faker("pyfloat", min_value=0.1, max_value=0.4),
            keywords=[],
            **kwargs,
        )

    @classmethod
    def create_failed_processing(cls, **kwargs) -> dict[str, Any]:
        """Create an activity that failed processing."""
        return cls(
            processing_status="failed",
            error_message="Classification model timeout",
            confidence=0.0,
            category="other",
            **kwargs,
        )

    @classmethod
    def create_activity_sequence(cls, user_id: str, days: int = 30) -> list[dict[str, Any]]:
        """
        Create a sequence of activities for a user over time.

        Args:
            user_id: User ID for all activities
            days: Number of days to spread activities across

        Returns:
            List of activities ordered chronologically
        """
        activities = []
        base_date = datetime.now(UTC) - timedelta(days=days)

        # Create varied activities throughout the period
        activity_count = random.randint(20, 100)

        for _i in range(activity_count):
            # Distribute activities across the time period
            day_offset = random.randint(0, days)
            hour_offset = random.randint(8, 18)  # Work hours
            activity_time = base_date + timedelta(days=day_offset, hours=hour_offset)

            # Vary activity types with realistic distribution
            activity_type = random.choices(
                ["technical_work", "code_review", "mentoring", "documentation", "other"],
                weights=[40, 25, 10, 15, 10],
                k=1,
            )[0]

            if activity_type == "technical_work":
                activity = cls.create_technical_work(user_id=user_id, timestamp=activity_time)
            elif activity_type == "code_review":
                activity = cls.create_code_review(user_id=user_id, timestamp=activity_time)
            elif activity_type == "mentoring":
                activity = cls.create_mentoring_activity(user_id=user_id, timestamp=activity_time)
            elif activity_type == "documentation":
                activity = cls.create_documentation(user_id=user_id, timestamp=activity_time)
            else:
                activity = cls(user_id=user_id, timestamp=activity_time)

            activities.append(activity)

        # Sort by timestamp
        activities.sort(key=lambda x: x["timestamp"])
        return activities

    @classmethod
    def create_golden_dataset(cls, size: int = 1000) -> list[dict[str, Any]]:
        """
        Create golden dataset for testing classification accuracy.

        Args:
            size: Number of activities to generate

        Returns:
            List of pre-classified activities with known expected outputs
        """
        activities = []

        # Distribution of activity types in golden dataset
        distributions = {
            "technical_work": int(size * 0.35),
            "code_review": int(size * 0.25),
            "mentoring": int(size * 0.15),
            "documentation": int(size * 0.15),
            "other": int(size * 0.10),
        }

        for category, count in distributions.items():
            for _ in range(count):
                if category == "technical_work":
                    activity = cls.create_technical_work()
                elif category == "code_review":
                    activity = cls.create_code_review()
                elif category == "mentoring":
                    activity = cls.create_mentoring_activity()
                elif category == "documentation":
                    activity = cls.create_documentation()
                else:
                    activity = cls.create_low_confidence_activity()

                # Mark as golden dataset
                activity["is_golden"] = True
                activity["human_validated"] = True
                activity["validation_feedback"] = "correct"

                activities.append(activity)

        return activities


def _get_subcategory(category: str) -> str:
    """Get appropriate subcategory based on main category."""
    subcategories = {
        "technical_work": ["implementation", "bug_fixing", "refactoring", "optimization"],
        "code_review": ["pull_request_review", "architecture_review", "security_review"],
        "mentoring": ["knowledge_sharing", "pair_programming", "career_guidance"],
        "planning": ["sprint_planning", "architecture_planning", "requirement_analysis"],
        "documentation": ["technical_writing", "api_documentation", "process_documentation"],
        "testing": ["unit_testing", "integration_testing", "manual_testing"],
        "debugging": ["issue_investigation", "root_cause_analysis", "performance_debugging"],
        "research": ["technology_research", "feasibility_analysis", "market_research"],
        "meetings": ["team_standup", "planning_meeting", "review_meeting"],
        "project_management": ["task_coordination", "timeline_planning", "resource_allocation"],
        "learning": ["skill_development", "training", "certification"],
        "other": ["unclear", "administrative", "miscellaneous"],
    }

    return random.choice(subcategories.get(category, ["other"]))


def _generate_competency_mappings() -> list[dict[str, Any]]:
    """Generate competency mappings for the activity."""
    competencies = [
        {"competency_id": "tech_python", "weight": 0.8, "category": "technical_skills"},
        {"competency_id": "soft_communication", "weight": 0.6, "category": "soft_skills"},
        {"competency_id": "tech_system_design", "weight": 0.7, "category": "technical_skills"},
        {"competency_id": "lead_mentoring", "weight": 0.5, "category": "leadership"},
    ]

    # Return 1-3 random competency mappings
    return random.sample(competencies, random.randint(1, 3))
