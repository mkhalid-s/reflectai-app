"""
Golden Datasets for ReflectAI Testing
Task 5d: Golden Datasets

Provides pre-validated datasets for testing classification accuracy,
competency assessment, and conversation handling.
"""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from tests.factories import ActivityFactory, CompetencyFactory, EventFactory


class GoldenDatasets:
    """
    Manager for golden datasets used in testing.

    Golden datasets provide known input/output pairs for validating
    the accuracy of AI systems and data processing pipelines.
    """

    def __init__(self, data_dir: Path | None = None):
        self.data_dir = data_dir or Path(__file__).parent / "data"
        self.data_dir.mkdir(exist_ok=True)

    def generate_classification_dataset(self, size: int = 1000) -> list[dict[str, Any]]:
        """
        Generate golden dataset for activity classification testing.

        Task 5d requirement: 1000 pre-classified activities

        Args:
            size: Number of classified activities to generate

        Returns:
            List of activities with validated classifications
        """
        print(f"Generating classification dataset with {size} activities...")

        # Create dataset with ActivityFactory
        activities = ActivityFactory.create_golden_dataset(size=size)

        # Add validation metadata
        for activity in activities:
            activity.update(
                {
                    "validation_metadata": {
                        "validated_by": "domain_expert",
                        "validation_date": datetime.now(UTC).isoformat(),
                        "confidence_score": 1.0,  # Golden data is 100% confident
                        "validation_notes": "Manually validated for golden dataset",
                    },
                    "test_expectations": {
                        "expected_category": activity["category"],
                        "expected_subcategory": activity["subcategory"],
                        "min_confidence": 0.8,
                        "should_match_keywords": activity["keywords"],
                    },
                }
            )

        # Save to file
        dataset_file = self.data_dir / "classification_dataset.json"
        with open(dataset_file, "w") as f:
            json.dump(activities, f, indent=2, default=str)

        print(f"Classification dataset saved to {dataset_file}")
        return activities

    def generate_competency_dataset(self, size: int = 500) -> list[dict[str, Any]]:
        """
        Generate golden dataset for competency assessment testing.

        Task 5d requirement: Complete competency progression scenarios

        Args:
            size: Number of competency records to generate

        Returns:
            List of competencies with validated assessments
        """
        print(f"Generating competency dataset with {size} competencies...")

        # Create dataset with CompetencyFactory
        competencies = CompetencyFactory.create_golden_competency_dataset(size=size)

        # Add progression scenarios
        progression_scenarios = []
        user_ids = list({comp["user_id"] for comp in competencies[:50]})  # First 50 users

        for user_id in user_ids[:10]:  # Create progressions for 10 users
            for competency_name in ["Python Programming", "System Design", "Leadership"]:
                progression = CompetencyFactory.create_progression_scenario(
                    user_id=user_id, competency_name=competency_name, months=12
                )
                progression_scenarios.extend(progression)

        # Combine competencies and progressions
        all_competencies = competencies + progression_scenarios

        # Add test expectations
        for competency in all_competencies:
            competency.update(
                {
                    "test_expectations": {
                        "score_range": {
                            "min": max(1.0, competency["score"] - 0.2),
                            "max": min(5.0, competency["score"] + 0.2),
                        },
                        "expected_level": competency["level"],
                        "min_evidence_count": max(1, competency["evidence_count"] - 2),
                    }
                }
            )

        # Save to file
        dataset_file = self.data_dir / "competency_dataset.json"
        with open(dataset_file, "w") as f:
            json.dump(all_competencies, f, indent=2, default=str)

        print(f"Competency dataset saved to {dataset_file}")
        return all_competencies

    def generate_conversation_dataset(self, size: int = 200) -> list[dict[str, Any]]:
        """
        Generate golden dataset for conversation testing.

        Task 5d requirement: Multi-turn conversation examples

        Args:
            size: Number of conversation scenarios to generate

        Returns:
            List of conversation scenarios with expected responses
        """
        print(f"Generating conversation dataset with {size} conversations...")

        conversations = []

        # Conversation templates
        conversation_templates = {
            "competency_inquiry": {
                "turns": [
                    {"role": "user", "content": "What are my strongest technical skills?"},
                    {
                        "role": "assistant",
                        "content": "Based on your recent activity, your strongest technical skills are Python programming (4.2/5), API development (3.8/5), and system design (3.5/5).",
                    },
                    {"role": "user", "content": "How can I improve my system design skills?"},
                    {
                        "role": "assistant",
                        "content": "To improve your system design skills, I recommend: 1) Review architecture patterns, 2) Practice with real-world scenarios, 3) Study scalability principles.",
                    },
                ],
                "expected_outcomes": {
                    "should_identify_strengths": True,
                    "should_provide_recommendations": True,
                    "should_reference_user_data": True,
                },
            },
            "activity_summary": {
                "turns": [
                    {"role": "user", "content": "What did I accomplish this week?"},
                    {
                        "role": "assistant",
                        "content": "This week you completed 8 code reviews, implemented 3 new features, and mentored 2 team members. Your activity shows strong technical execution and leadership.",
                    },
                    {"role": "user", "content": "Which activities had the most impact?"},
                    {
                        "role": "assistant",
                        "content": "Your mentoring sessions had high impact, helping junior developers with React and API design. The authentication system implementation was also significant.",
                    },
                ],
                "expected_outcomes": {
                    "should_summarize_activities": True,
                    "should_highlight_impact": True,
                    "should_be_specific": True,
                },
            },
            "career_guidance": {
                "turns": [
                    {"role": "user", "content": "What should I focus on for my next promotion?"},
                    {
                        "role": "assistant",
                        "content": "For promotion to Senior Engineer, focus on: 1) Leading more technical decisions, 2) Mentoring junior developers, 3) Improving system design skills.",
                    },
                    {"role": "user", "content": "How long might this take?"},
                    {
                        "role": "assistant",
                        "content": "Based on your current progression rate, with focused effort on these areas, you could be promotion-ready in 6-9 months.",
                    },
                ],
                "expected_outcomes": {
                    "should_provide_actionable_advice": True,
                    "should_set_realistic_timeline": True,
                    "should_align_with_role_requirements": True,
                },
            },
        }

        # Generate conversations based on templates
        for i in range(size):
            template_name = list(conversation_templates.keys())[i % len(conversation_templates)]
            template = conversation_templates[template_name]

            user_id = f"user_{i // len(conversation_templates) + 1}"

            conversation = {
                "id": f"conv_{i:04d}",
                "user_id": user_id,
                "conversation_type": template_name,
                "turns": template["turns"],
                "expected_outcomes": template["expected_outcomes"],
                "metadata": {
                    "created_at": datetime.now(UTC).isoformat(),
                    "context": {
                        "user_role": "software_engineer",
                        "user_level": "mid",
                        "organization": "tech_company",
                    },
                },
                "test_assertions": {
                    "response_time_max_ms": 5000,
                    "should_maintain_context": True,
                    "should_be_helpful": True,
                    "should_be_accurate": True,
                },
            }

            conversations.append(conversation)

        # Save to file
        dataset_file = self.data_dir / "conversation_dataset.json"
        with open(dataset_file, "w") as f:
            json.dump(conversations, f, indent=2, default=str)

        print(f"Conversation dataset saved to {dataset_file}")
        return conversations

    def generate_error_dataset(self, size: int = 100) -> list[dict[str, Any]]:
        """
        Generate golden dataset for error handling testing.

        Task 5d requirement: Known error scenarios and edge cases

        Args:
            size: Number of error scenarios to generate

        Returns:
            List of error scenarios with expected handling
        """
        print(f"Generating error dataset with {size} error scenarios...")

        error_scenarios = []

        # Error scenario templates
        error_templates = {
            "invalid_input": {
                "input": {"content": "", "user_id": None},
                "expected_error": "VALIDATION_ERROR",
                "expected_message": "Invalid input: content and user_id are required",
                "should_retry": False,
            },
            "malformed_data": {
                "input": {"content": "Valid content", "timestamp": "invalid-date"},
                "expected_error": "DATA_FORMAT_ERROR",
                "expected_message": "Invalid timestamp format",
                "should_retry": False,
            },
            "service_timeout": {
                "input": {"user_id": "valid_user", "timeout_simulation": True},
                "expected_error": "SERVICE_TIMEOUT",
                "expected_message": "Request timed out after 30 seconds",
                "should_retry": True,
                "max_retries": 3,
            },
            "resource_exhausted": {
                "input": {"batch_size": 10000},
                "expected_error": "RESOURCE_EXHAUSTED",
                "expected_message": "Insufficient resources to process request",
                "should_retry": True,
                "max_retries": 2,
            },
            "dependency_failure": {
                "input": {"user_id": "valid_user", "force_db_failure": True},
                "expected_error": "DEPENDENCY_ERROR",
                "expected_message": "Database connection failed",
                "should_retry": True,
                "max_retries": 5,
            },
        }

        # Generate error scenarios
        for i in range(size):
            template_name = list(error_templates.keys())[i % len(error_templates)]
            template = error_templates[template_name]

            scenario = {
                "id": f"error_{i:04d}",
                "scenario_type": template_name,
                "input_data": template["input"],
                "expected_error": {
                    "error_code": template["expected_error"],
                    "error_message": template["expected_message"],
                    "should_retry": template.get("should_retry", False),
                    "max_retries": template.get("max_retries", 0),
                },
                "test_assertions": {
                    "should_log_error": True,
                    "should_not_crash": True,
                    "should_return_error_response": True,
                    "response_time_max_ms": 1000,
                },
                "recovery_expectations": {
                    "should_graceful_degrade": True,
                    "should_preserve_user_data": True,
                    "should_notify_monitoring": True,
                },
            }

            error_scenarios.append(scenario)

        # Save to file
        dataset_file = self.data_dir / "error_dataset.json"
        with open(dataset_file, "w") as f:
            json.dump(error_scenarios, f, indent=2, default=str)

        print(f"Error dataset saved to {dataset_file}")
        return error_scenarios

    def generate_performance_dataset(self, size: int = 50) -> list[dict[str, Any]]:
        """
        Generate dataset for performance testing.

        Args:
            size: Number of performance test scenarios

        Returns:
            List of performance test scenarios
        """
        print(f"Generating performance dataset with {size} scenarios...")

        performance_scenarios = []

        for i in range(size):
            # Vary load characteristics
            scenario_type = ["light_load", "medium_load", "heavy_load", "spike_load"][i % 4]

            load_configs = {
                "light_load": {"users": 10, "duration_minutes": 5, "rps": 5},
                "medium_load": {"users": 100, "duration_minutes": 15, "rps": 50},
                "heavy_load": {"users": 500, "duration_minutes": 30, "rps": 200},
                "spike_load": {"users": 1000, "duration_minutes": 2, "rps": 500},
            }

            config = load_configs[scenario_type]

            scenario = {
                "id": f"perf_{i:04d}",
                "scenario_type": scenario_type,
                "load_configuration": config,
                "performance_expectations": {
                    "avg_response_time_ms": 500 if scenario_type != "spike_load" else 2000,
                    "p95_response_time_ms": 1000 if scenario_type != "spike_load" else 5000,
                    "error_rate_percent": 1.0 if scenario_type != "spike_load" else 5.0,
                    "throughput_min_rps": config["rps"] * 0.8,
                },
                "test_data": {
                    "user_activities": ActivityFactory.create_golden_dataset(config["users"]),
                    "competency_updates": CompetencyFactory.create_golden_competency_dataset(
                        config["users"] // 2
                    ),
                    "events": EventFactory.create_high_volume_events(config["users"] * 10),
                },
            }

            performance_scenarios.append(scenario)

        # Save to file
        dataset_file = self.data_dir / "performance_dataset.json"
        with open(dataset_file, "w") as f:
            json.dump(performance_scenarios, f, indent=2, default=str)

        print(f"Performance dataset saved to {dataset_file}")
        return performance_scenarios

    def generate_all_datasets(self) -> dict[str, list[dict[str, Any]]]:
        """
        Generate all golden datasets.

        Returns:
            Dictionary containing all datasets
        """
        print("Generating all golden datasets...")

        datasets = {
            "classification": self.generate_classification_dataset(1000),
            "competency": self.generate_competency_dataset(500),
            "conversation": self.generate_conversation_dataset(200),
            "error": self.generate_error_dataset(100),
            "performance": self.generate_performance_dataset(50),
        }

        # Generate summary
        summary = {
            "generated_at": datetime.now(UTC).isoformat(),
            "total_records": sum(len(dataset) for dataset in datasets.values()),
            "datasets": {
                name: {"count": len(dataset), "file": f"{name}_dataset.json"}
                for name, dataset in datasets.items()
            },
        }

        summary_file = self.data_dir / "dataset_summary.json"
        with open(summary_file, "w") as f:
            json.dump(summary, f, indent=2, default=str)

        print(f"All datasets generated successfully. Summary saved to {summary_file}")
        return datasets

    def load_dataset(self, dataset_name: str) -> list[dict[str, Any]]:
        """Load a specific golden dataset."""
        dataset_file = self.data_dir / f"{dataset_name}_dataset.json"

        if not dataset_file.exists():
            raise FileNotFoundError(f"Dataset file not found: {dataset_file}")

        with open(dataset_file) as f:
            return json.load(f)

    def get_dataset_summary(self) -> dict[str, Any]:
        """Get summary of available datasets."""
        summary_file = self.data_dir / "dataset_summary.json"

        if not summary_file.exists():
            return {"error": "No datasets generated yet"}

        with open(summary_file) as f:
            return json.load(f)


# Global instance for easy access
golden_datasets = GoldenDatasets()


def generate_all_golden_datasets():
    """Utility function to generate all golden datasets."""
    return golden_datasets.generate_all_datasets()


if __name__ == "__main__":
    # Generate all datasets when run as script
    print("Generating ReflectAI Golden Datasets...")
    datasets = generate_all_golden_datasets()
    print(f"Generated {sum(len(d) for d in datasets.values())} total records")
    print("Golden datasets ready for testing!")
