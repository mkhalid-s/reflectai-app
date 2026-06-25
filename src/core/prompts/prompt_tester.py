"""
Prompt Testing and Validation Utilities

Provides tools for testing prompt templates with golden datasets and
validating prompt effectiveness for different scenarios.
"""

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any

from src.shared import get_logger

from .prompt_manager import PromptValidationError, get_prompt_manager

logger = get_logger(__name__)


class TestResult(str, Enum):
    """Test result status."""

    PASS = "pass"
    FAIL = "fail"
    WARNING = "warning"


@dataclass
class TestCase:
    """Individual test case for prompt validation."""

    name: str
    prompt_name: str
    input_variables: dict[str, Any]
    expected_output: str | None = None
    expected_keywords: list[str] = field(default_factory=list)
    expected_json_fields: list[str] = field(default_factory=list)
    min_length: int | None = None
    max_length: int | None = None
    description: str = ""
    tags: list[str] = field(default_factory=list)


@dataclass
class TestExecution:
    """Result of executing a test case."""

    test_case: TestCase
    result: TestResult
    actual_output: str
    issues: list[str] = field(default_factory=list)
    execution_time_ms: float = 0.0
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class GoldenDataset:
    """Collection of test cases for comprehensive prompt validation."""

    name: str
    description: str
    test_cases: list[TestCase]
    created_at: datetime = field(default_factory=datetime.utcnow)
    version: str = "1.0"

    def add_test_case(self, test_case: TestCase):
        """Add a test case to the dataset."""
        self.test_cases.append(test_case)

    def get_test_cases_by_prompt(self, prompt_name: str) -> list[TestCase]:
        """Get all test cases for a specific prompt."""
        return [tc for tc in self.test_cases if tc.prompt_name == prompt_name]

    def get_test_cases_by_tag(self, tag: str) -> list[TestCase]:
        """Get all test cases with a specific tag."""
        return [tc for tc in self.test_cases if tag in tc.tags]


class PromptTester:
    """
    Comprehensive prompt testing and validation system.

    Features:
    - Golden dataset testing with expected outputs
    - Automated validation of prompt rendering
    - Performance testing and benchmarking
    - Regression testing for prompt changes
    - Test report generation
    """

    def __init__(self, datasets_dir: str | None = None):
        self.prompt_manager = get_prompt_manager()

        # Set datasets directory
        if datasets_dir:
            self.datasets_dir = Path(datasets_dir)
        else:
            # Default to src/test_data/prompts directory
            self.datasets_dir = Path(__file__).parent.parent.parent / "test_data" / "prompts"

        self.datasets_dir.mkdir(parents=True, exist_ok=True)

        # Loaded datasets
        self.datasets: dict[str, GoldenDataset] = {}

        # Test execution history
        self.execution_history: list[TestExecution] = []

        logger.info("Prompt tester initialized", extra={"datasets_dir": str(self.datasets_dir)})

        # Load existing datasets
        self._load_datasets()

        # Create default datasets if none exist
        if not self.datasets:
            self._create_default_datasets()

    def run_test_case(self, test_case: TestCase) -> TestExecution:
        """Execute a single test case."""

        start_time = datetime.now(UTC)
        issues = []

        try:
            # Render prompt with test variables
            actual_output = self.prompt_manager.get_prompt(
                test_case.prompt_name, test_case.input_variables
            )

            # Validate output
            validation_issues = self._validate_output(test_case, actual_output)
            issues.extend(validation_issues)

            # Determine result
            if not issues:
                result = TestResult.PASS
            elif any("fail" in issue.lower() for issue in issues):
                result = TestResult.FAIL
            else:
                result = TestResult.WARNING

        except Exception as e:
            actual_output = f"ERROR: {str(e)}"
            issues.append(f"Prompt rendering failed: {str(e)}")
            result = TestResult.FAIL

        # Calculate execution time
        execution_time = (datetime.now(UTC) - start_time).total_seconds() * 1000

        # Create test execution record
        execution = TestExecution(
            test_case=test_case,
            result=result,
            actual_output=actual_output,
            issues=issues,
            execution_time_ms=execution_time,
        )

        # Store in history
        self.execution_history.append(execution)

        logger.debug(
            f"Test case executed: {test_case.name}",
            extra={
                "result": result.value,
                "execution_time_ms": execution_time,
                "issues_count": len(issues),
            },
        )

        return execution

    def _validate_output(self, test_case: TestCase, actual_output: str) -> list[str]:
        """Validate test output against expected criteria."""

        issues = []

        # Check exact match if provided
        if test_case.expected_output:
            if actual_output.strip() != test_case.expected_output.strip():
                issues.append("Output does not match expected content")

        # Check for expected keywords
        for keyword in test_case.expected_keywords:
            if keyword.lower() not in actual_output.lower():
                issues.append(f"Missing expected keyword: {keyword}")

        # Check length constraints
        if test_case.min_length and len(actual_output) < test_case.min_length:
            issues.append(f"Output too short: {len(actual_output)} < {test_case.min_length}")

        if test_case.max_length and len(actual_output) > test_case.max_length:
            issues.append(f"Output too long: {len(actual_output)} > {test_case.max_length}")

        # Check JSON structure if expected
        if test_case.expected_json_fields:
            json_issues = self._validate_json_output(actual_output, test_case.expected_json_fields)
            issues.extend(json_issues)

        return issues

    def _validate_json_output(self, output: str, expected_fields: list[str]) -> list[str]:
        """Validate JSON structure in output."""

        issues = []

        try:
            # Try to extract JSON from output
            json_start = output.find("{")
            json_end = output.rfind("}")

            if json_start == -1 or json_end == -1:
                issues.append("No JSON structure found in output")
                return issues

            json_text = output[json_start : json_end + 1]
            parsed_json = json.loads(json_text)

            # Check for required fields
            for field in expected_fields:
                if field not in parsed_json:
                    issues.append(f"Missing required JSON field: {field}")

        except json.JSONDecodeError as e:
            issues.append(f"Invalid JSON format: {str(e)}")
        except Exception as e:
            issues.append(f"JSON validation error: {str(e)}")

        return issues

    def run_dataset(self, dataset_name: str) -> list[TestExecution]:
        """Run all test cases in a dataset."""

        if dataset_name not in self.datasets:
            raise PromptValidationError(f"Dataset '{dataset_name}' not found")

        dataset = self.datasets[dataset_name]
        executions = []

        logger.info(f"Running dataset: {dataset_name} ({len(dataset.test_cases)} test cases)")

        for test_case in dataset.test_cases:
            execution = self.run_test_case(test_case)
            executions.append(execution)

        # Generate summary
        passed = len([e for e in executions if e.result == TestResult.PASS])
        failed = len([e for e in executions if e.result == TestResult.FAIL])
        warnings = len([e for e in executions if e.result == TestResult.WARNING])

        logger.info(
            f"Dataset execution completed: {dataset_name}",
            extra={
                "total_tests": len(executions),
                "passed": passed,
                "failed": failed,
                "warnings": warnings,
            },
        )

        return executions

    def run_all_datasets(self) -> dict[str, list[TestExecution]]:
        """Run all loaded datasets."""

        results = {}

        for dataset_name in self.datasets.keys():
            try:
                results[dataset_name] = self.run_dataset(dataset_name)
            except Exception as e:
                logger.error(f"Failed to run dataset {dataset_name}: {e}")
                results[dataset_name] = []

        return results

    def create_dataset(self, name: str, description: str) -> GoldenDataset:
        """Create a new test dataset."""

        dataset = GoldenDataset(name=name, description=description, test_cases=[])

        self.datasets[name] = dataset

        logger.info(f"Created new dataset: {name}")

        return dataset

    def _load_datasets(self):
        """Load datasets from the datasets directory."""

        if not self.datasets_dir.exists():
            return

        for dataset_file in self.datasets_dir.glob("*.json"):
            try:
                self._load_dataset_file(dataset_file)
            except Exception as e:
                logger.error(f"Failed to load dataset {dataset_file}: {e}")

    def _load_dataset_file(self, dataset_file: Path):
        """Load a single dataset file."""

        with open(dataset_file, encoding="utf-8") as f:
            data = json.load(f)

        # Create dataset
        dataset = GoldenDataset(
            name=data["name"],
            description=data.get("description", ""),
            test_cases=[],
            version=data.get("version", "1.0"),
        )

        # Load test cases
        for tc_data in data.get("test_cases", []):
            test_case = TestCase(
                name=tc_data["name"],
                prompt_name=tc_data["prompt_name"],
                input_variables=tc_data["input_variables"],
                expected_output=tc_data.get("expected_output"),
                expected_keywords=tc_data.get("expected_keywords", []),
                expected_json_fields=tc_data.get("expected_json_fields", []),
                min_length=tc_data.get("min_length"),
                max_length=tc_data.get("max_length"),
                description=tc_data.get("description", ""),
                tags=tc_data.get("tags", []),
            )
            dataset.add_test_case(test_case)

        self.datasets[dataset.name] = dataset

        logger.info(f"Loaded dataset: {dataset.name} ({len(dataset.test_cases)} test cases)")

    def _create_default_datasets(self):
        """Create default test datasets."""

        logger.info("Creating default test datasets")

        # Analysis Agent Dataset
        analysis_dataset = self.create_dataset(
            name="analysis_agent_tests", description="Test cases for Analysis Agent prompts"
        )

        # Test cases for analysis agent
        test_cases = [
            TestCase(
                name="basic_activity_analysis",
                prompt_name="agents/analysis_agent",
                input_variables={
                    "task_description": "Analyze the following activity: Led a team meeting to discuss project requirements and assigned tasks to team members.",
                    "user_context": {
                        "level": "Senior",
                        "department": "Engineering",
                        "role": "Tech Lead",
                    },
                },
                expected_keywords=[
                    "classification",
                    "confidence",
                    "evidence",
                    "leadership",
                    "project management",
                ],
                expected_json_fields=[
                    "classification",
                    "confidence",
                    "evidence",
                    "recommendations",
                ],
                min_length=100,
                tags=["agent", "analysis", "leadership"],
            ),
            TestCase(
                name="technical_activity_analysis",
                prompt_name="agents/analysis_agent",
                input_variables={
                    "task_description": "Analyze the following activity: Debugged a complex performance issue in the payment processing system, identified the root cause, and implemented a fix.",
                    "user_context": {
                        "level": "Mid-level",
                        "department": "Engineering",
                        "role": "Software Engineer",
                    },
                },
                expected_keywords=["technical", "problem solving", "analysis", "debugging"],
                expected_json_fields=["classification", "confidence", "evidence"],
                min_length=100,
                tags=["agent", "analysis", "technical"],
            ),
            TestCase(
                name="communication_activity_analysis",
                prompt_name="agents/analysis_agent",
                input_variables={
                    "task_description": "Analyze the following activity: Presented project updates to stakeholders, explained technical decisions, and gathered feedback on requirements.",
                    "user_context": {
                        "level": "Senior",
                        "department": "Product",
                        "role": "Product Manager",
                    },
                },
                expected_keywords=["communication", "presentation", "stakeholder management"],
                expected_json_fields=["classification", "confidence", "evidence"],
                min_length=100,
                tags=["agent", "analysis", "communication"],
            ),
        ]

        for test_case in test_cases:
            analysis_dataset.add_test_case(test_case)

        # Advisor Agent Dataset
        advisor_dataset = self.create_dataset(
            name="advisor_agent_tests", description="Test cases for Advisor Agent prompts"
        )

        advisor_test_cases = [
            TestCase(
                name="career_guidance_request",
                prompt_name="agents/advisor_agent",
                input_variables={
                    "task_description": "Provide career guidance for advancing from Senior Engineer to Tech Lead role.",
                    "user_context": {
                        "level": "Senior",
                        "department": "Engineering",
                        "role": "Software Engineer",
                        "career_goals": "Tech Lead position",
                    },
                    "analysis_results": "Strong technical skills, needs leadership experience",
                },
                expected_keywords=["opportunities", "development_plan", "leadership", "timeline"],
                expected_json_fields=["opportunities", "development_plan", "timeline"],
                min_length=150,
                tags=["agent", "advisor", "career"],
            ),
            TestCase(
                name="development_planning",
                prompt_name="agents/advisor_agent",
                input_variables={
                    "task_description": "Create a development plan for improving presentation and communication skills.",
                    "user_context": {
                        "level": "Mid-level",
                        "department": "Engineering",
                        "role": "Software Engineer",
                    },
                    "analysis_results": "Technical competency strong, communication needs development",
                },
                expected_keywords=["development_plan", "communication", "presentation", "timeline"],
                expected_json_fields=["development_plan", "timeline", "actions"],
                min_length=150,
                tags=["agent", "advisor", "development"],
            ),
        ]

        for test_case in advisor_test_cases:
            advisor_dataset.add_test_case(test_case)

        # Tool Tests Dataset
        tools_dataset = self.create_dataset(
            name="tools_tests", description="Test cases for tool prompts"
        )

        tool_test_cases = [
            TestCase(
                name="activity_classification",
                prompt_name="tools/activity_classifier",
                input_variables={
                    "activity_text": "Organized and facilitated a retrospective meeting with the development team to identify process improvements."
                },
                expected_keywords=["classification", "confidence", "leadership", "facilitation"],
                expected_json_fields=["classification", "confidence", "evidence"],
                min_length=50,
                tags=["tool", "classification"],
            ),
            TestCase(
                name="competency_assessment",
                prompt_name="tools/competency_assessor",
                input_variables={
                    "activity_text": "Mentored a junior developer, provided code reviews, and guided them through complex technical decisions.",
                    "competency_area": "Leadership",
                },
                expected_keywords=["score", "mentoring", "leadership", "assessment"],
                expected_json_fields=["score", "gaps", "recommendations"],
                min_length=50,
                tags=["tool", "assessment"],
            ),
        ]

        for test_case in tool_test_cases:
            tools_dataset.add_test_case(test_case)

        # Save datasets to disk
        self._save_datasets()

    def _save_datasets(self):
        """Save all datasets to disk."""

        for _name, dataset in self.datasets.items():
            self._save_dataset(dataset)

    def _save_dataset(self, dataset: GoldenDataset):
        """Save a single dataset to disk."""

        dataset_file = self.datasets_dir / f"{dataset.name}.json"

        data = {
            "name": dataset.name,
            "description": dataset.description,
            "version": dataset.version,
            "created_at": dataset.created_at.isoformat(),
            "test_cases": [
                {
                    "name": tc.name,
                    "prompt_name": tc.prompt_name,
                    "input_variables": tc.input_variables,
                    "expected_output": tc.expected_output,
                    "expected_keywords": tc.expected_keywords,
                    "expected_json_fields": tc.expected_json_fields,
                    "min_length": tc.min_length,
                    "max_length": tc.max_length,
                    "description": tc.description,
                    "tags": tc.tags,
                }
                for tc in dataset.test_cases
            ],
        }

        with open(dataset_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        logger.debug(f"Saved dataset to {dataset_file}")

    def generate_test_report(
        self, executions: list[TestExecution], output_file: str | None = None
    ) -> str:
        """Generate comprehensive test report."""

        if not executions:
            return "No test executions to report"

        # Calculate summary statistics
        total_tests = len(executions)
        passed = len([e for e in executions if e.result == TestResult.PASS])
        failed = len([e for e in executions if e.result == TestResult.FAIL])
        warnings = len([e for e in executions if e.result == TestResult.WARNING])

        avg_execution_time = sum(e.execution_time_ms for e in executions) / total_tests

        # Generate report
        report_lines = [
            "# Prompt Testing Report",
            f"Generated: {datetime.now(UTC).isoformat()}",
            "",
            "## Summary",
            f"- Total Tests: {total_tests}",
            f"- Passed: {passed} ({passed / total_tests * 100:.1f}%)",
            f"- Failed: {failed} ({failed / total_tests * 100:.1f}%)",
            f"- Warnings: {warnings} ({warnings / total_tests * 100:.1f}%)",
            f"- Average Execution Time: {avg_execution_time:.1f}ms",
            "",
        ]

        # Group by result status
        if failed > 0:
            report_lines.extend(["## Failed Tests", ""])

            for execution in executions:
                if execution.result == TestResult.FAIL:
                    report_lines.extend(
                        [
                            f"### {execution.test_case.name}",
                            f"- Prompt: {execution.test_case.prompt_name}",
                            f"- Issues: {', '.join(execution.issues)}",
                            f"- Execution Time: {execution.execution_time_ms:.1f}ms",
                            "",
                        ]
                    )

        if warnings > 0:
            report_lines.extend(["## Warnings", ""])

            for execution in executions:
                if execution.result == TestResult.WARNING:
                    report_lines.extend(
                        [
                            f"### {execution.test_case.name}",
                            f"- Prompt: {execution.test_case.prompt_name}",
                            f"- Issues: {', '.join(execution.issues)}",
                            "",
                        ]
                    )

        report = "\n".join(report_lines)

        # Save to file if specified
        if output_file:
            output_path = Path(output_file)
            output_path.write_text(report, encoding="utf-8")
            logger.info(f"Test report saved to {output_path}")

        return report

    def get_tester_stats(self) -> dict[str, Any]:
        """Get prompt tester statistics."""

        recent_executions = [
            e for e in self.execution_history if (datetime.now(UTC) - e.timestamp).days < 7
        ]

        return {
            "datasets": {
                "total": len(self.datasets),
                "test_cases": sum(len(d.test_cases) for d in self.datasets.values()),
            },
            "executions": {
                "total": len(self.execution_history),
                "recent_week": len(recent_executions),
                "recent_results": {
                    "passed": len([e for e in recent_executions if e.result == TestResult.PASS]),
                    "failed": len([e for e in recent_executions if e.result == TestResult.FAIL]),
                    "warnings": len(
                        [e for e in recent_executions if e.result == TestResult.WARNING]
                    ),
                },
            },
            "datasets_available": list(self.datasets.keys()),
        }


# Global prompt tester instance
_prompt_tester: PromptTester | None = None


def get_prompt_tester() -> PromptTester:
    """Get or create global prompt tester instance."""
    global _prompt_tester
    if _prompt_tester is None:
        _prompt_tester = PromptTester()
    return _prompt_tester
