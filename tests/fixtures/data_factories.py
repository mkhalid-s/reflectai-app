"""
Data Factories for ReflectAI Tests

Factory classes for generating consistent test data across all test phases.
Provides realistic mock data for users, activities, competencies, and more.
"""

import random
import uuid
from datetime import datetime, timedelta
from typing import Any

from faker import Faker

fake = Faker()


class UserDataFactory:
    """Factory for generating user test data"""

    @staticmethod
    def create_user(
        user_id: str | None = None,
        role: str = "developer",
        experience_level: str = "intermediate",
        **kwargs,
    ) -> dict[str, Any]:
        """Create a single user record"""
        return {
            "user_id": user_id or f"user_{uuid.uuid4().hex[:8]}",
            "email": kwargs.get("email", fake.email()),
            "name": kwargs.get("name", fake.name()),
            "role": role,
            "experience_level": experience_level,
            "join_date": kwargs.get(
                "join_date", fake.date_time_between(start_date="-2y", end_date="now")
            ),
            "active": kwargs.get("active", True),
            "department": kwargs.get("department", "Engineering"),
            "manager_id": kwargs.get("manager_id"),
            "skills": kwargs.get("skills", ["python", "javascript", "sql"]),
            "goals": kwargs.get("goals", ["improve_technical_skills", "advance_career"]),
        }

    @staticmethod
    def create_users(count: int, **kwargs) -> list[dict[str, Any]]:
        """Create multiple user records"""
        return [UserDataFactory.create_user(**kwargs) for _ in range(count)]

    @staticmethod
    def create_team(team_lead_id: str | None = None, team_size: int = 5) -> list[dict[str, Any]]:
        """Create a complete team with lead and members"""
        lead = UserDataFactory.create_user(
            user_id=team_lead_id, role="tech_lead", experience_level="senior"
        )

        members = []
        for _i in range(team_size - 1):
            member = UserDataFactory.create_user(
                role=random.choice(["developer", "senior_developer"]),
                experience_level=random.choice(["junior", "intermediate", "senior"]),
                manager_id=lead["user_id"],
            )
            members.append(member)

        return [lead] + members


class ActivityDataFactory:
    """Factory for generating activity test data"""

    ACTIVITY_TYPES = [
        "code_review",
        "documentation",
        "pair_programming",
        "testing",
        "debugging",
        "architecture_design",
        "mentoring",
        "learning",
        "meeting",
        "presentation",
        "planning",
        "deployment",
    ]

    SKILL_AREAS = [
        "python",
        "javascript",
        "sql",
        "docker",
        "kubernetes",
        "aws",
        "react",
        "nodejs",
        "git",
        "ci_cd",
        "monitoring",
        "security",
        "leadership",
        "communication",
        "problem_solving",
        "collaboration",
    ]

    @staticmethod
    def create_activity(
        user_id: str,
        activity_type: str | None = None,
        timestamp: datetime | None = None,
        **kwargs,
    ) -> dict[str, Any]:
        """Create a single activity record"""
        activity_type = activity_type or random.choice(ActivityDataFactory.ACTIVITY_TYPES)

        return {
            "activity_id": f"act_{uuid.uuid4().hex[:8]}",
            "user_id": user_id,
            "activity_type": activity_type,
            "timestamp": timestamp or fake.date_time_between(start_date="-90d", end_date="now"),
            "duration_minutes": kwargs.get("duration_minutes", random.randint(15, 240)),
            "quality_score": kwargs.get("quality_score", random.uniform(60, 95)),
            "complexity_level": kwargs.get("complexity_level", random.randint(1, 5)),
            "associated_skills": kwargs.get(
                "associated_skills",
                random.sample(ActivityDataFactory.SKILL_AREAS, k=random.randint(1, 4)),
            ),
            "metadata": kwargs.get(
                "metadata", ActivityDataFactory._generate_metadata(activity_type)
            ),
            "description": kwargs.get("description", fake.text(max_nb_chars=200)),
            "outcome": kwargs.get(
                "outcome", random.choice(["completed", "in_progress", "blocked"])
            ),
            "feedback_score": kwargs.get("feedback_score", random.uniform(3.0, 5.0)),
        }

    @staticmethod
    def create_activities(
        user_id: str,
        count: int,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        **kwargs,
    ) -> list[dict[str, Any]]:
        """Create multiple activity records for a user"""
        activities = []

        start_date = start_date or (datetime.now() - timedelta(days=90))
        end_date = end_date or datetime.now()

        for _ in range(count):
            timestamp = fake.date_time_between(start_date=start_date, end_date=end_date)
            activity = ActivityDataFactory.create_activity(
                user_id=user_id, timestamp=timestamp, **kwargs
            )
            activities.append(activity)

        return sorted(activities, key=lambda x: x["timestamp"])

    @staticmethod
    def create_activity_series(
        user_id: str, skill: str, progression: str = "improving", duration_days: int = 30
    ) -> list[dict[str, Any]]:
        """Create a series of activities showing skill progression"""
        activities = []

        base_quality = {"improving": (60, 90), "stable": (70, 80), "declining": (80, 60)}[
            progression
        ]

        for i in range(10):  # 10 activities over duration
            days_ago = duration_days - (i * duration_days // 10)
            timestamp = datetime.now() - timedelta(days=days_ago)

            # Calculate progressive quality score
            progress_factor = i / 9  # 0 to 1
            if progression == "improving":
                quality_score = (
                    base_quality[0] + (base_quality[1] - base_quality[0]) * progress_factor
                )
            elif progression == "declining":
                quality_score = (
                    base_quality[0] - (base_quality[0] - base_quality[1]) * progress_factor
                )
            else:  # stable
                quality_score = random.uniform(base_quality[0], base_quality[1])

            activity = ActivityDataFactory.create_activity(
                user_id=user_id,
                timestamp=timestamp,
                quality_score=quality_score,
                associated_skills=[skill],
                complexity_level=min(5, 2 + i // 3),  # Increasing complexity
            )
            activities.append(activity)

        return activities

    @staticmethod
    def _generate_metadata(activity_type: str) -> dict[str, Any]:
        """Generate realistic metadata based on activity type"""
        metadata_templates = {
            "code_review": {
                "repository": fake.slug(),
                "pull_request": f"#{random.randint(1, 999)}",
                "lines_changed": random.randint(10, 500),
                "files_modified": random.randint(1, 15),
            },
            "documentation": {
                "document_type": random.choice(["api_spec", "user_guide", "technical_design"]),
                "pages": random.randint(1, 20),
                "format": random.choice(["markdown", "confluence", "docx"]),
            },
            "pair_programming": {
                "partner": f"user_{uuid.uuid4().hex[:8]}",
                "feature": fake.slug(),
                "session_type": random.choice(["driver_navigator", "collaborative"]),
            },
            "meeting": {
                "meeting_type": random.choice(["standup", "planning", "retrospective", "review"]),
                "attendees_count": random.randint(3, 12),
                "agenda_items": random.randint(2, 8),
            },
            "deployment": {
                "environment": random.choice(["staging", "production"]),
                "service": fake.slug(),
                "version": f"v{random.randint(1, 10)}.{random.randint(0, 20)}.{random.randint(0, 50)}",
            },
        }

        return metadata_templates.get(activity_type, {"generic": True})


class CompetencyDataFactory:
    """Factory for generating competency test data"""

    COMPETENCIES = [
        "python",
        "javascript",
        "sql",
        "docker",
        "kubernetes",
        "aws",
        "react",
        "nodejs",
        "git",
        "testing",
        "ci_cd",
        "monitoring",
        "architecture",
        "database_design",
        "api_design",
        "security",
        "leadership",
        "communication",
        "mentoring",
        "problem_solving",
        "collaboration",
        "project_management",
        "strategic_thinking",
    ]

    @staticmethod
    def create_competency_scores(
        user_id: str | None = None,
        competencies: list[str] | None = None,
        level: str = "intermediate",
    ) -> dict[str, float]:
        """Create competency scores for a user"""
        competencies = competencies or random.sample(CompetencyDataFactory.COMPETENCIES, k=8)

        level_ranges = {
            "beginner": (40, 65),
            "intermediate": (60, 85),
            "advanced": (75, 95),
            "expert": (85, 98),
        }

        score_range = level_ranges.get(level, (60, 85))

        return {
            competency: random.uniform(score_range[0], score_range[1])
            for competency in competencies
        }

    @staticmethod
    def create_competency_progression(
        user_id: str, competency: str, months: int = 6, trend: str = "improving"
    ) -> list[dict[str, Any]]:
        """Create historical competency progression"""
        progression = []

        base_score = random.uniform(60, 70)

        for month in range(months):
            date = datetime.now() - timedelta(days=30 * (months - month))

            if trend == "improving":
                score = base_score + (month * 5) + random.uniform(-3, 3)
            elif trend == "declining":
                score = base_score + 20 - (month * 3) + random.uniform(-2, 2)
            else:  # stable
                score = base_score + 10 + random.uniform(-5, 5)

            score = max(0, min(100, score))

            progression.append(
                {
                    "user_id": user_id,
                    "competency": competency,
                    "score": score,
                    "date": date,
                    "confidence_interval": (score - 5, score + 5),
                }
            )

        return progression

    @staticmethod
    def create_framework(
        framework_id: str | None = None, name: str | None = None, competency_count: int = 12
    ) -> dict[str, Any]:
        """Create a competency framework"""
        from shared.types import CompetencyLevel

        framework_id = framework_id or f"framework_{uuid.uuid4().hex[:8]}"
        name = name or fake.catch_phrase()

        competencies = random.sample(CompetencyDataFactory.COMPETENCIES, k=competency_count)

        categories = {
            "technical": [
                c
                for c in competencies
                if c
                in [
                    "python",
                    "javascript",
                    "sql",
                    "docker",
                    "kubernetes",
                    "aws",
                    "react",
                    "nodejs",
                    "git",
                    "testing",
                    "ci_cd",
                    "monitoring",
                ]
            ],
            "design": [
                c
                for c in competencies
                if c in ["architecture", "database_design", "api_design", "security"]
            ],
            "soft_skills": [
                c
                for c in competencies
                if c
                in [
                    "leadership",
                    "communication",
                    "mentoring",
                    "problem_solving",
                    "collaboration",
                    "project_management",
                    "strategic_thinking",
                ]
            ],
        }

        # Remove empty categories
        categories = {k: v for k, v in categories.items() if v}

        return {
            "framework_id": framework_id,
            "name": name,
            "version": "1.0.0",
            "description": fake.text(max_nb_chars=200),
            "categories": categories,
            "levels": [level.value for level in CompetencyLevel],
            "created_at": fake.date_time_between(start_date="-1y", end_date="now"),
            "active": True,
        }


class RecommendationDataFactory:
    """Factory for generating recommendation test data"""

    RECOMMENDATION_TYPES = [
        "skill_development",
        "career_advancement",
        "learning_resource",
        "project_opportunity",
        "networking",
        "certification",
        "mentoring",
    ]

    PRIORITY_LEVELS = ["low", "medium", "high", "critical"]

    @staticmethod
    def create_recommendation(
        user_id: str, recommendation_type: str | None = None, **kwargs
    ) -> dict[str, Any]:
        """Create a single recommendation"""
        rec_type = recommendation_type or random.choice(
            RecommendationDataFactory.RECOMMENDATION_TYPES
        )

        return {
            "recommendation_id": f"rec_{uuid.uuid4().hex[:8]}",
            "user_id": user_id,
            "recommendation_type": rec_type,
            "title": kwargs.get("title", RecommendationDataFactory._generate_title(rec_type)),
            "description": kwargs.get("description", fake.text(max_nb_chars=300)),
            "priority_level": kwargs.get(
                "priority_level", random.choice(RecommendationDataFactory.PRIORITY_LEVELS)
            ),
            "priority_score": kwargs.get("priority_score", random.uniform(0, 100)),
            "confidence_score": kwargs.get("confidence_score", random.uniform(0.6, 0.95)),
            "actionable_steps": kwargs.get(
                "actionable_steps", RecommendationDataFactory._generate_steps(rec_type)
            ),
            "estimated_effort_hours": kwargs.get("estimated_effort_hours", random.randint(5, 80)),
            "expected_impact": kwargs.get(
                "expected_impact", random.choice(["Low", "Medium", "High"])
            ),
            "timeline": kwargs.get("timeline", f"{random.randint(1, 12)} months"),
            "resources": kwargs.get(
                "resources", RecommendationDataFactory._generate_resources(rec_type)
            ),
            "generated_at": kwargs.get("generated_at", datetime.now()),
            "expires_at": kwargs.get("expires_at", datetime.now() + timedelta(days=30)),
            "status": kwargs.get("status", "active"),
        }

    @staticmethod
    def create_development_plan(
        user_id: str, target_competencies: list[str] | None = None, duration_months: int = 6
    ) -> dict[str, Any]:
        """Create a comprehensive development plan"""
        target_competencies = target_competencies or random.sample(
            CompetencyDataFactory.COMPETENCIES, k=4
        )

        phases = []
        for i in range(3):  # 3 phases
            phase_competencies = target_competencies[i::3]  # Distribute competencies across phases
            if phase_competencies:
                phases.append(
                    {
                        "phase": i + 1,
                        "name": f"Phase {i + 1}: {fake.catch_phrase()}",
                        "duration_months": duration_months // 3,
                        "focus_competencies": phase_competencies,
                        "milestones": [
                            f"Complete {comp} fundamentals" for comp in phase_competencies
                        ],
                        "success_criteria": [
                            f"Achieve {random.randint(75, 90)}% proficiency in {comp}"
                            for comp in phase_competencies
                        ],
                    }
                )

        return {
            "plan_id": f"plan_{uuid.uuid4().hex[:8]}",
            "user_id": user_id,
            "title": f"Development Plan for {', '.join(target_competencies[:2])}...",
            "description": fake.text(max_nb_chars=400),
            "total_duration_months": duration_months,
            "target_competencies": target_competencies,
            "current_level": random.choice(["beginner", "intermediate", "advanced"]),
            "target_level": random.choice(["intermediate", "advanced", "expert"]),
            "phases": phases,
            "success_metrics": [
                "Competency score improvements",
                "Project completion rates",
                "Peer feedback scores",
            ],
            "created_at": datetime.now(),
            "status": "active",
        }

    @staticmethod
    def _generate_title(recommendation_type: str) -> str:
        """Generate appropriate title based on recommendation type"""
        titles = {
            "skill_development": f"Develop {random.choice(CompetencyDataFactory.COMPETENCIES).title()} Skills",
            "career_advancement": f"Pursue {random.choice(['Senior Developer', 'Tech Lead', 'Architect'])} Role",
            "learning_resource": f"Complete {fake.catch_phrase()} Course",
            "project_opportunity": f"Join {fake.company()} Project",
            "networking": f"Connect with {random.choice(['Industry Leaders', 'Peers', 'Mentors'])}",
            "certification": f"Earn {random.choice(['AWS', 'Azure', 'GCP', 'Kubernetes'])} Certification",
            "mentoring": f"{'Become a Mentor' if random.random() > 0.5 else 'Find a Mentor'}",
        }
        return titles.get(recommendation_type, fake.catch_phrase())

    @staticmethod
    def _generate_steps(recommendation_type: str) -> list[str]:
        """Generate actionable steps based on recommendation type"""
        steps_templates = {
            "skill_development": [
                "Complete online course or tutorial",
                "Practice with hands-on project",
                "Join study group or community",
                "Apply skills in work project",
            ],
            "career_advancement": [
                "Update resume and LinkedIn profile",
                "Network with professionals in target role",
                "Develop required skills and experience",
                "Apply for relevant positions",
            ],
            "learning_resource": [
                "Enroll in recommended course",
                "Set aside dedicated study time",
                "Complete assignments and projects",
                "Apply learnings to real scenarios",
            ],
            "certification": [
                "Review certification requirements",
                "Study relevant materials",
                "Take practice exams",
                "Schedule and take certification exam",
            ],
        }

        default_steps = [
            "Research and understand requirements",
            "Create action plan with timeline",
            "Execute plan with regular progress reviews",
            "Evaluate results and iterate",
        ]

        return steps_templates.get(recommendation_type, default_steps)

    @staticmethod
    def _generate_resources(recommendation_type: str) -> list[dict[str, str]]:
        """Generate resources based on recommendation type"""
        return [
            {
                "type": "course",
                "title": fake.catch_phrase(),
                "provider": random.choice(
                    ["Coursera", "Udemy", "LinkedIn Learning", "Pluralsight"]
                ),
                "url": fake.url(),
            },
            {
                "type": "book",
                "title": fake.catch_phrase(),
                "author": fake.name(),
                "isbn": fake.isbn13(),
            },
            {"type": "documentation", "title": "Official Documentation", "url": fake.url()},
        ]


# Utility functions for test data
def create_complete_user_profile(user_id: str | None = None) -> dict[str, Any]:
    """Create a complete user profile with all associated data"""
    user = UserDataFactory.create_user(user_id=user_id)

    return {
        "user": user,
        "activities": ActivityDataFactory.create_activities(user["user_id"], count=25),
        "competency_scores": CompetencyDataFactory.create_competency_scores(
            user_id=user["user_id"], level=user["experience_level"]
        ),
        "recommendations": [
            RecommendationDataFactory.create_recommendation(user["user_id"]) for _ in range(5)
        ],
        "development_plan": RecommendationDataFactory.create_development_plan(user["user_id"]),
    }


def create_test_scenario(scenario_type: str) -> dict[str, Any]:
    """Create complete test scenarios"""
    scenarios = {
        "new_user_onboarding": {
            "user": UserDataFactory.create_user(experience_level="beginner"),
            "activities": [],  # New user has no activities
            "competency_scores": {},
            "expected_recommendations": ["skill_development", "learning_resource"],
        },
        "experienced_user_progression": {
            "user": UserDataFactory.create_user(experience_level="advanced"),
            "activities": ActivityDataFactory.create_activities("user123", count=50),
            "competency_scores": CompetencyDataFactory.create_competency_scores(level="advanced"),
            "expected_recommendations": ["career_advancement", "mentoring"],
        },
        "team_analysis": {
            "team": UserDataFactory.create_team(team_size=8),
            "team_activities": {},  # Will be populated per user
            "team_competencies": {},  # Will be populated per user
            "expected_insights": ["team_strengths", "skill_gaps", "development_opportunities"],
        },
    }

    return scenarios.get(scenario_type, {})
