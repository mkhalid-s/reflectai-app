"""
Competency Factory for generating test competency data.
Task 5b: Test Data Factories - CompetencyFactory
"""

import random
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import factory
from factory import Faker, LazyFunction


class CompetencyFactory(factory.Factory):
    """
    Factory for generating competency test data with scores and evidence.

    Creates competencies across different categories, skill levels, and progression
    patterns to test competency assessment and tracking systems.
    """

    class Meta:
        model = dict

    # Core identifiers
    id = LazyFunction(lambda: f"comp_{uuid.uuid4().hex[:8]}")
    user_id = LazyFunction(lambda: f"user_{uuid.uuid4().hex[:8]}")
    competency_definition_id = LazyFunction(lambda: f"def_{uuid.uuid4().hex[:8]}")

    # Competency classification
    category = Faker(
        "random_element",
        elements=[
            "technical_skills",
            "soft_skills",
            "leadership",
            "domain_knowledge",
            "tools_and_technologies",
            "methodologies",
            "business_skills",
        ],
    )

    subcategory = factory.LazyAttribute(lambda obj: _get_subcategory(obj.category))

    # Competency identification
    name = factory.LazyAttribute(lambda obj: _get_competency_name(obj.category, obj.subcategory))
    description = factory.LazyAttribute(lambda obj: f"Competency in {obj.name.lower()}")

    # Current scoring
    score = Faker(
        "pyfloat", left_digits=1, right_digits=2, positive=True, min_value=1.0, max_value=5.0
    )
    level = factory.LazyAttribute(lambda obj: _score_to_level(obj.score))

    # Evidence and confidence
    evidence_count = Faker("random_int", min=1, max=50)
    confidence = Faker(
        "pyfloat", left_digits=0, right_digits=2, positive=True, min_value=0.3, max_value=1.0
    )

    # Progression tracking
    previous_score = factory.LazyAttribute(
        lambda obj: obj.score - random.uniform(-0.5, 0.3)  # Can go up or down slightly
    )

    trend = factory.LazyAttribute(lambda obj: _calculate_trend(obj.score, obj.previous_score))

    # Temporal information
    first_evidence_date = Faker(
        "date_time",
        start_date=datetime.now(UTC) - timedelta(days=365),
        end_date=datetime.now(UTC) - timedelta(days=30),
        tzinfo=UTC,
    )

    last_updated = Faker("date_time_this_month", tzinfo=UTC)
    last_evidence_date = factory.LazyAttribute(lambda obj: obj.last_updated)

    # Assessment metadata
    assessment_method = Faker(
        "random_element",
        elements=[
            "activity_analysis",
            "peer_feedback",
            "self_assessment",
            "manager_review",
            "project_outcome",
            "training_completion",
        ],
    )

    assessor_type = Faker(
        "random_element", elements=["ai_system", "peer", "manager", "self", "external_reviewer"]
    )

    # Validation and quality
    human_reviewed = Faker("boolean", chance_of_getting_true=25)
    validation_status = Faker(
        "random_element", elements=["pending", "validated", "disputed", "needs_review"]
    )

    # Skills breakdown
    skills = factory.LazyFunction(lambda: _generate_skills())
    skill_gaps = factory.LazyFunction(lambda: _generate_skill_gaps())

    # Goals and development
    target_score = factory.LazyAttribute(lambda obj: min(5.0, obj.score + random.uniform(0.5, 1.5)))

    development_priorities = factory.LazyFunction(lambda: _generate_development_priorities())

    # Metadata
    created_at = factory.LazyAttribute(lambda obj: obj.first_evidence_date)
    updated_at = factory.LazyAttribute(lambda obj: obj.last_updated)

    @classmethod
    def create_technical_skill(cls, skill_name: str | None = None, **kwargs) -> dict[str, Any]:
        """Create a technical skill competency."""
        skills = [
            "Python Programming",
            "JavaScript Development",
            "System Design",
            "Database Design",
            "API Development",
            "Cloud Architecture",
            "DevOps Practices",
            "Testing Strategies",
            "Security Implementation",
        ]

        name = skill_name or random.choice(skills)

        return cls(
            category="technical_skills",
            subcategory="programming_languages" if "Programming" in name else "system_architecture",
            name=name,
            score=Faker("pyfloat", min_value=2.0, max_value=5.0),
            evidence_count=Faker("random_int", min=5, max=30),
            confidence=Faker("pyfloat", min_value=0.7, max_value=1.0),
            **kwargs,
        )

    @classmethod
    def create_soft_skill(cls, skill_name: str | None = None, **kwargs) -> dict[str, Any]:
        """Create a soft skill competency."""
        skills = [
            "Communication",
            "Teamwork",
            "Problem Solving",
            "Critical Thinking",
            "Time Management",
            "Adaptability",
            "Creativity",
            "Emotional Intelligence",
        ]

        name = skill_name or random.choice(skills)

        return cls(
            category="soft_skills",
            subcategory="interpersonal" if name in ["Communication", "Teamwork"] else "cognitive",
            name=name,
            score=Faker("pyfloat", min_value=1.5, max_value=4.5),
            evidence_count=Faker("random_int", min=3, max=20),
            confidence=Faker("pyfloat", min_value=0.5, max_value=0.9),
            **kwargs,
        )

    @classmethod
    def create_leadership_skill(cls, skill_name: str | None = None, **kwargs) -> dict[str, Any]:
        """Create a leadership competency."""
        skills = [
            "Team Leadership",
            "Mentoring",
            "Strategic Planning",
            "Decision Making",
            "Conflict Resolution",
            "Change Management",
            "Vision Setting",
        ]

        name = skill_name or random.choice(skills)

        return cls(
            category="leadership",
            subcategory="people_management"
            if name in ["Team Leadership", "Mentoring"]
            else "strategic_leadership",
            name=name,
            score=Faker("pyfloat", min_value=1.0, max_value=4.0),
            evidence_count=Faker("random_int", min=1, max=15),
            confidence=Faker("pyfloat", min_value=0.4, max_value=0.8),
            **kwargs,
        )

    @classmethod
    def create_beginner_competency(cls, **kwargs) -> dict[str, Any]:
        """Create a beginner-level competency."""
        return cls(
            score=Faker("pyfloat", min_value=1.0, max_value=2.0),
            level="beginner",
            evidence_count=Faker("random_int", min=1, max=5),
            confidence=Faker("pyfloat", min_value=0.3, max_value=0.6),
            **kwargs,
        )

    @classmethod
    def create_expert_competency(cls, **kwargs) -> dict[str, Any]:
        """Create an expert-level competency."""
        return cls(
            score=Faker("pyfloat", min_value=4.5, max_value=5.0),
            level="expert",
            evidence_count=Faker("random_int", min=20, max=50),
            confidence=Faker("pyfloat", min_value=0.8, max_value=1.0),
            **kwargs,
        )

    @classmethod
    def create_improving_competency(cls, **kwargs) -> dict[str, Any]:
        """Create a competency showing improvement trend."""
        current_score = random.uniform(2.0, 4.0)
        previous_score = current_score - random.uniform(0.3, 1.0)

        return cls(
            score=current_score,
            previous_score=previous_score,
            trend="improving",
            evidence_count=Faker("random_int", min=5, max=20),
            **kwargs,
        )

    @classmethod
    def create_declining_competency(cls, **kwargs) -> dict[str, Any]:
        """Create a competency showing declining trend."""
        current_score = random.uniform(1.5, 3.5)
        previous_score = current_score + random.uniform(0.2, 0.8)

        return cls(
            score=current_score,
            previous_score=previous_score,
            trend="declining",
            evidence_count=Faker("random_int", min=1, max=10),
            **kwargs,
        )

    @classmethod
    def create_user_competency_profile(
        cls, user_id: str, role: str = "software_engineer"
    ) -> list[dict[str, Any]]:
        """
        Create a realistic competency profile for a user based on their role.

        Args:
            user_id: User ID for all competencies
            role: User's role to determine competency distribution

        Returns:
            List of competencies appropriate for the role
        """
        competencies = []

        # Role-based competency templates
        role_templates = {
            "software_engineer": {
                "technical_skills": [
                    "Python Programming",
                    "API Development",
                    "Database Design",
                    "Testing Strategies",
                ],
                "soft_skills": ["Problem Solving", "Communication", "Teamwork"],
                "tools_and_technologies": ["Git", "Docker", "AWS"],
            },
            "senior_software_engineer": {
                "technical_skills": [
                    "System Design",
                    "Cloud Architecture",
                    "Performance Optimization",
                ],
                "soft_skills": ["Critical Thinking", "Communication", "Leadership"],
                "leadership": ["Mentoring", "Technical Leadership"],
            },
            "engineering_manager": {
                "leadership": ["Team Leadership", "Strategic Planning", "Decision Making"],
                "soft_skills": ["Communication", "Emotional Intelligence", "Time Management"],
                "business_skills": ["Resource Planning", "Stakeholder Management"],
            },
        }

        template = role_templates.get(role, role_templates["software_engineer"])

        for category, skills in template.items():
            for skill in skills:
                if category == "technical_skills":
                    competency = cls.create_technical_skill(skill_name=skill, user_id=user_id)
                elif category == "soft_skills":
                    competency = cls.create_soft_skill(skill_name=skill, user_id=user_id)
                elif category == "leadership":
                    competency = cls.create_leadership_skill(skill_name=skill, user_id=user_id)
                else:
                    competency = cls(category=category, name=skill, user_id=user_id)

                competencies.append(competency)

        return competencies

    @classmethod
    def create_progression_scenario(
        cls, user_id: str, competency_name: str, months: int = 12
    ) -> list[dict[str, Any]]:
        """
        Create a competency progression scenario over time.

        Args:
            user_id: User ID
            competency_name: Name of the competency
            months: Number of months to show progression

        Returns:
            List of competency snapshots showing progression
        """
        snapshots = []
        base_date = datetime.now(UTC) - timedelta(days=months * 30)

        # Start with beginner level
        current_score = random.uniform(1.0, 2.0)
        evidence_count = 1

        for month in range(months + 1):
            # Realistic progression with some variation
            if month > 0:
                # Growth rate slows as competency increases
                growth_rate = max(0.05, 0.3 - (current_score - 1.0) * 0.1)
                growth = random.uniform(-0.1, growth_rate)  # Can have small setbacks
                current_score = min(5.0, max(1.0, current_score + growth))
                evidence_count += random.randint(0, 3)

            snapshot_date = base_date + timedelta(days=month * 30)

            snapshot = cls(
                user_id=user_id,
                name=competency_name,
                score=round(current_score, 2),
                evidence_count=evidence_count,
                last_updated=snapshot_date,
                created_at=base_date if month == 0 else None,
            )

            snapshots.append(snapshot)

        return snapshots

    @classmethod
    def create_golden_competency_dataset(cls, size: int = 500) -> list[dict[str, Any]]:
        """
        Create golden dataset for competency assessment testing.

        Args:
            size: Number of competency records to generate

        Returns:
            List of pre-validated competency assessments
        """
        competencies = []

        # Distribution across categories
        distributions = {
            "technical_skills": int(size * 0.4),
            "soft_skills": int(size * 0.3),
            "leadership": int(size * 0.15),
            "tools_and_technologies": int(size * 0.15),
        }

        for category, count in distributions.items():
            for _ in range(count):
                if category == "technical_skills":
                    competency = cls.create_technical_skill()
                elif category == "soft_skills":
                    competency = cls.create_soft_skill()
                elif category == "leadership":
                    competency = cls.create_leadership_skill()
                else:
                    competency = cls(category=category)

                # Mark as validated golden dataset
                competency["human_reviewed"] = True
                competency["validation_status"] = "validated"
                competency["is_golden"] = True

                competencies.append(competency)

        return competencies


def _get_subcategory(category: str) -> str:
    """Get appropriate subcategory based on main category."""
    subcategories = {
        "technical_skills": [
            "programming_languages",
            "frameworks",
            "system_architecture",
            "databases",
        ],
        "soft_skills": ["interpersonal", "cognitive", "emotional", "organizational"],
        "leadership": ["people_management", "strategic_leadership", "change_management"],
        "domain_knowledge": ["industry_expertise", "business_domain", "regulatory"],
        "tools_and_technologies": ["development_tools", "cloud_platforms", "monitoring"],
        "methodologies": ["agile", "devops", "testing", "security"],
        "business_skills": ["project_management", "stakeholder_management", "financial"],
    }

    return random.choice(subcategories.get(category, ["general"]))


def _get_competency_name(category: str, subcategory: str) -> str:
    """Generate competency name based on category and subcategory."""
    names = {
        ("technical_skills", "programming_languages"): [
            "Python Programming",
            "JavaScript Development",
            "Go Programming",
        ],
        ("technical_skills", "system_architecture"): [
            "System Design",
            "Microservices Architecture",
            "API Design",
        ],
        ("soft_skills", "interpersonal"): ["Communication", "Teamwork", "Collaboration"],
        ("soft_skills", "cognitive"): ["Problem Solving", "Critical Thinking", "Analytical Skills"],
        ("leadership", "people_management"): [
            "Team Leadership",
            "Mentoring",
            "Performance Management",
        ],
        ("leadership", "strategic_leadership"): [
            "Strategic Planning",
            "Vision Setting",
            "Decision Making",
        ],
    }

    key = (category, subcategory)
    return random.choice(names.get(key, [f"{category.replace('_', ' ').title()} Competency"]))


def _score_to_level(score: float) -> str:
    """Convert numerical score to level string."""
    if score < 1.5:
        return "novice"
    elif score < 2.5:
        return "beginner"
    elif score < 3.5:
        return "intermediate"
    elif score < 4.5:
        return "advanced"
    else:
        return "expert"


def _calculate_trend(current_score: float, previous_score: float) -> str:
    """Calculate trend based on score comparison."""
    if current_score > previous_score + 0.1:
        return "improving"
    elif current_score < previous_score - 0.1:
        return "declining"
    else:
        return "stable"


def _generate_skills() -> list[str]:
    """Generate list of related skills."""
    skills = [
        "debugging",
        "code_review",
        "testing",
        "documentation",
        "optimization",
        "collaboration",
        "communication",
        "mentoring",
        "planning",
        "analysis",
    ]
    return random.sample(skills, random.randint(2, 5))


def _generate_skill_gaps() -> list[str]:
    """Generate list of skill gaps for development."""
    gaps = [
        "advanced_algorithms",
        "distributed_systems",
        "performance_tuning",
        "leadership_skills",
        "public_speaking",
        "strategic_thinking",
        "project_management",
        "stakeholder_management",
    ]
    return random.sample(gaps, random.randint(1, 3))


def _generate_development_priorities() -> list[str]:
    """Generate development priorities."""
    priorities = [
        "increase_technical_depth",
        "improve_communication",
        "develop_leadership",
        "expand_domain_knowledge",
        "enhance_problem_solving",
        "build_team_skills",
    ]
    return random.sample(priorities, random.randint(1, 3))
