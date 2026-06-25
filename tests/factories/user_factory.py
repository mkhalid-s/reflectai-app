"""
User Factory for generating test user data.
Task 5b: Test Data Factories - UserFactory
"""

import uuid
from datetime import UTC, datetime
from typing import Any

import factory
from factory import Faker, LazyFunction
from faker import Faker as FakerInstance

# Create faker instance for use in LazyFunction
fake = FakerInstance()


class UserFactory(factory.Factory):
    """
    Factory for generating user test data with varied profiles and levels.

    Generates users across different roles, levels, and organizations
    to test various user scenarios.
    """

    class Meta:
        model = dict

    # Core identifiers
    id = LazyFunction(lambda: f"user_{uuid.uuid4().hex[:8]}")
    slack_user_id = LazyFunction(lambda: f"U{uuid.uuid4().hex[:8].upper()}")
    organization_id = LazyFunction(lambda: f"org_{uuid.uuid4().hex[:8]}")

    # Personal information
    email = Faker("email")
    name = Faker("name")
    first_name = factory.LazyAttribute(lambda obj: obj.name.split()[0])
    last_name = factory.LazyAttribute(lambda obj: obj.name.split()[-1])

    # Professional information
    role = Faker(
        "random_element",
        elements=[
            "software_engineer",
            "senior_software_engineer",
            "staff_engineer",
            "engineering_manager",
            "senior_engineering_manager",
            "director",
            "product_manager",
            "senior_product_manager",
            "data_scientist",
            "senior_data_scientist",
            "devops_engineer",
            "security_engineer",
            "qa_engineer",
            "design_lead",
            "research_scientist",
        ],
    )

    level = Faker(
        "random_element",
        elements=["junior", "mid", "senior", "staff", "principal", "manager", "director"],
    )

    department = Faker(
        "random_element",
        elements=[
            "Engineering",
            "Product",
            "Design",
            "Data Science",
            "DevOps",
            "Security",
            "QA",
            "Research",
            "Marketing",
            "Sales",
        ],
    )

    # Experience and skills
    years_of_experience = Faker("random_int", min=0, max=25)
    skills = Faker(
        "random_elements",
        elements=[
            "python",
            "javascript",
            "react",
            "nodejs",
            "aws",
            "docker",
            "kubernetes",
            "postgresql",
            "redis",
            "machine_learning",
            "system_design",
            "api_design",
            "testing",
            "ci_cd",
            "monitoring",
        ],
        length=5,
        unique=True,
    )

    # Activity and engagement metrics
    activity_count = Faker("random_int", min=0, max=1000)
    last_activity_date = Faker("date_time_this_year", tzinfo=UTC)
    engagement_score = Faker(
        "pyfloat", left_digits=1, right_digits=2, positive=True, max_value=10.0
    )

    # Timestamps
    created_at = Faker("date_time_this_year", tzinfo=UTC)
    updated_at = factory.LazyAttribute(lambda obj: obj.created_at)

    # Status and flags
    is_active = Faker("boolean", chance_of_getting_true=90)
    is_verified = Faker("boolean", chance_of_getting_true=80)
    onboarding_completed = Faker("boolean", chance_of_getting_true=85)

    # Preferences and settings
    timezone = Faker("timezone")
    notification_preferences = factory.LazyFunction(
        lambda: {
            "email": fake.boolean(chance_of_getting_true=70),
            "slack": fake.boolean(chance_of_getting_true=90),
            "push": fake.boolean(chance_of_getting_true=60),
        }
    )

    privacy_settings = factory.LazyFunction(
        lambda: {
            "profile_visibility": fake.random_element(elements=["public", "team", "private"]),
            "activity_sharing": fake.boolean(chance_of_getting_true=75),
            "analytics_opt_in": fake.boolean(chance_of_getting_true=80),
        }
    )

    @classmethod
    def create_junior_engineer(cls, **kwargs) -> dict[str, Any]:
        """Create a junior software engineer."""
        return cls(
            role="software_engineer",
            level="junior",
            years_of_experience=factory.Faker("random_int", min=0, max=2),
            skills=["python", "git", "testing"],
            **kwargs,
        )

    @classmethod
    def create_senior_engineer(cls, **kwargs) -> dict[str, Any]:
        """Create a senior software engineer."""
        return cls(
            role="senior_software_engineer",
            level="senior",
            years_of_experience=factory.Faker("random_int", min=5, max=15),
            skills=["python", "javascript", "system_design", "aws", "mentoring"],
            **kwargs,
        )

    @classmethod
    def create_engineering_manager(cls, **kwargs) -> dict[str, Any]:
        """Create an engineering manager."""
        return cls(
            role="engineering_manager",
            level="manager",
            department="Engineering",
            years_of_experience=factory.Faker("random_int", min=8, max=20),
            skills=["leadership", "project_management", "system_design", "python"],
            **kwargs,
        )

    @classmethod
    def create_data_scientist(cls, **kwargs) -> dict[str, Any]:
        """Create a data scientist."""
        return cls(
            role="data_scientist",
            level=factory.Faker("random_element", elements=["mid", "senior"]),
            department="Data Science",
            skills=["python", "machine_learning", "statistics", "sql", "data_visualization"],
            **kwargs,
        )

    @classmethod
    def create_inactive_user(cls, **kwargs) -> dict[str, Any]:
        """Create an inactive user for testing edge cases."""
        return cls(
            is_active=False,
            activity_count=0,
            last_activity_date=factory.Faker(
                "date_time", end_datetime=datetime(2023, 1, 1, tzinfo=UTC)
            ),
            engagement_score=0.0,
            **kwargs,
        )

    @classmethod
    def create_highly_active_user(cls, **kwargs) -> dict[str, Any]:
        """Create a highly active user for testing high-volume scenarios."""
        return cls(
            activity_count=factory.Faker("random_int", min=500, max=2000),
            engagement_score=factory.Faker("pyfloat", min_value=8.0, max_value=10.0),
            last_activity_date=factory.Faker("date_time_this_month", tzinfo=UTC),
            **kwargs,
        )

    @classmethod
    def create_batch(cls, count: int, **kwargs) -> list[dict[str, Any]]:
        """Create multiple users at once."""
        return [cls(**kwargs) for _ in range(count)]

    @classmethod
    def create_team(
        cls,
        team_size: int = 5,
        manager_kwargs: dict | None = None,
        member_kwargs: dict | None = None,
    ) -> dict[str, Any]:
        """
        Create a team with one manager and multiple team members.

        Returns:
            Dict with 'manager' and 'members' keys
        """
        manager_kwargs = manager_kwargs or {}
        member_kwargs = member_kwargs or {}

        # Create team manager
        manager = cls.create_engineering_manager(**manager_kwargs)

        # Create team members
        members = []
        for _ in range(team_size):
            member = cls(
                organization_id=manager["organization_id"],
                department=manager["department"],
                **member_kwargs,
            )
            members.append(member)

        return {
            "manager": manager,
            "members": members,
            "team_id": f"team_{uuid.uuid4().hex[:8]}",
            "team_size": team_size + 1,  # Including manager
        }

    @classmethod
    def create_diverse_organization(cls, size: int = 20) -> dict[str, Any]:
        """
        Create a diverse organization with mixed roles and levels.

        Args:
            size: Total number of users to create

        Returns:
            Dict with organization data and user breakdown
        """
        org_id = f"org_{uuid.uuid4().hex[:8]}"

        # Distribution percentages
        junior_pct = 0.3
        mid_pct = 0.35
        senior_pct = 0.25
        manager_pct = 0.1

        users = []

        # Create junior developers
        junior_count = int(size * junior_pct)
        users.extend(
            [cls.create_junior_engineer(organization_id=org_id) for _ in range(junior_count)]
        )

        # Create mid-level developers
        mid_count = int(size * mid_pct)
        users.extend([cls(level="mid", organization_id=org_id) for _ in range(mid_count)])

        # Create senior developers
        senior_count = int(size * senior_pct)
        users.extend(
            [cls.create_senior_engineer(organization_id=org_id) for _ in range(senior_count)]
        )

        # Create managers
        manager_count = int(size * manager_pct)
        users.extend(
            [cls.create_engineering_manager(organization_id=org_id) for _ in range(manager_count)]
        )

        # Fill remaining slots
        remaining = size - len(users)
        users.extend([cls(organization_id=org_id) for _ in range(remaining)])

        return {
            "organization_id": org_id,
            "users": users,
            "total_users": len(users),
            "breakdown": {
                "junior": junior_count,
                "mid": mid_count,
                "senior": senior_count,
                "managers": manager_count,
                "others": remaining,
            },
        }
