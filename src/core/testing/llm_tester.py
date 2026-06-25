"""
LLM Testing Framework Implementation

Comprehensive testing framework for LLM responses, agent behavior,
and system performance with golden datasets and validation methods.
"""

import json
import statistics
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any

from src.core.llm import LLMRequest, ModelTier, get_llm_gateway
from src.core.prompts import get_prompt_manager
from src.shared import get_logger

logger = get_logger(__name__)


class TestResult(str, Enum):
    """Test execution results."""

    PASS = "pass"
    FAIL = "fail"
    WARNING = "warning"
    ERROR = "error"


class ValidationMethod(str, Enum):
    """Response validation methods."""

    EXACT_MATCH = "exact_match"
    KEYWORD_PRESENCE = "keyword_presence"
    JSON_STRUCTURE = "json_structure"
    CONFIDENCE_THRESHOLD = "confidence_threshold"
    FORMAT_VALIDATION = "format_validation"
    SEMANTIC_SIMILARITY = "semantic_similarity"


@dataclass
class TestCase:
    """Individual test case definition."""

    name: str
    description: str
    input_data: dict[str, Any]
    expected_output: str | None = None
    validation_methods: list[ValidationMethod] = field(default_factory=list)
    validation_criteria: dict[str, Any] = field(default_factory=dict)
    timeout_seconds: int = 30
    tags: list[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.validation_methods:
            self.validation_methods = [ValidationMethod.FORMAT_VALIDATION]


@dataclass
class TestExecution:
    """Test execution result with detailed metrics."""

    test_case: TestCase
    result: TestResult
    actual_output: str
    execution_time_ms: float
    issues: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class TestSuite:
    """Collection of related test cases."""

    name: str
    description: str
    test_cases: list[TestCase] = field(default_factory=list)
    setup_function: Callable | None = None
    teardown_function: Callable | None = None

    def add_test_case(self, test_case: TestCase):
        """Add test case to suite."""
        self.test_cases.append(test_case)

    def get_test_cases_by_tag(self, tag: str) -> list[TestCase]:
        """Get test cases with specific tag."""
        return [tc for tc in self.test_cases if tag in tc.tags]


class ResponseValidator:
    """Validates LLM responses against various criteria."""

    def __init__(self):
        self.validation_functions = {
            ValidationMethod.EXACT_MATCH: self._validate_exact_match,
            ValidationMethod.KEYWORD_PRESENCE: self._validate_keyword_presence,
            ValidationMethod.JSON_STRUCTURE: self._validate_json_structure,
            ValidationMethod.CONFIDENCE_THRESHOLD: self._validate_confidence_threshold,
            ValidationMethod.FORMAT_VALIDATION: self._validate_format,
            ValidationMethod.SEMANTIC_SIMILARITY: self._validate_semantic_similarity,
        }

    def validate_response(
        self, actual_output: str, test_case: TestCase, metadata: dict[str, Any] | None = None
    ) -> tuple[TestResult, list[str]]:
        """
        Validate response against test case criteria.

        Args:
            actual_output: Actual LLM response
            test_case: Test case with validation criteria
            metadata: Additional metadata from execution

        Returns:
            Tuple of (result, issues_list)
        """

        issues = []
        has_failures = False
        has_warnings = False

        # Run each validation method
        for method in test_case.validation_methods:
            if method in self.validation_functions:
                try:
                    method_issues = self.validation_functions[method](
                        actual_output, test_case, metadata
                    )

                    # Categorize issues
                    for issue in method_issues:
                        if "fail" in issue.lower() or "error" in issue.lower():
                            has_failures = True
                        else:
                            has_warnings = True
                        issues.append(f"{method.value}: {issue}")

                except Exception as e:
                    has_failures = True
                    issues.append(f"{method.value}: Validation error - {str(e)}")

        # Determine overall result
        if has_failures:
            return TestResult.FAIL, issues
        elif has_warnings:
            return TestResult.WARNING, issues
        else:
            return TestResult.PASS, issues

    def _validate_exact_match(
        self, actual_output: str, test_case: TestCase, metadata: dict[str, Any] | None
    ) -> list[str]:
        """Validate exact match against expected output."""

        issues = []

        if test_case.expected_output is None:
            return ["No expected output specified for exact match validation"]

        actual_clean = actual_output.strip()
        expected_clean = test_case.expected_output.strip()

        if actual_clean != expected_clean:
            issues.append(
                f"Exact match failed. Expected: '{expected_clean[:100]}...', "
                f"Got: '{actual_clean[:100]}...'"
            )

        return issues

    def _validate_keyword_presence(
        self, actual_output: str, test_case: TestCase, metadata: dict[str, Any] | None
    ) -> list[str]:
        """Validate presence of required keywords."""

        issues = []
        required_keywords = test_case.validation_criteria.get("required_keywords", [])
        forbidden_keywords = test_case.validation_criteria.get("forbidden_keywords", [])

        actual_lower = actual_output.lower()

        # Check required keywords
        for keyword in required_keywords:
            if keyword.lower() not in actual_lower:
                issues.append(f"Missing required keyword: '{keyword}'")

        # Check forbidden keywords
        for keyword in forbidden_keywords:
            if keyword.lower() in actual_lower:
                issues.append(f"Contains forbidden keyword: '{keyword}'")

        return issues

    def _validate_json_structure(
        self, actual_output: str, test_case: TestCase, metadata: dict[str, Any] | None
    ) -> list[str]:
        """Validate JSON structure and required fields."""

        issues = []
        required_fields = test_case.validation_criteria.get("required_fields", [])

        try:
            # Try to extract JSON from output
            json_start = actual_output.find("{")
            json_end = actual_output.rfind("}")

            if json_start == -1 or json_end == -1:
                issues.append("No JSON structure found in output")
                return issues

            json_text = actual_output[json_start : json_end + 1]
            parsed_json = json.loads(json_text)

            # Check required fields
            for field in required_fields:
                if field not in parsed_json:
                    issues.append(f"Missing required JSON field: '{field}'")

            # Validate field types if specified
            field_types = test_case.validation_criteria.get("field_types", {})
            for field, expected_type in field_types.items():
                if field in parsed_json:
                    actual_type = type(parsed_json[field]).__name__
                    if actual_type != expected_type:
                        issues.append(
                            f"Field '{field}' has wrong type: expected {expected_type}, got {actual_type}"
                        )

        except json.JSONDecodeError as e:
            issues.append(f"Invalid JSON format: {str(e)}")
        except Exception as e:
            issues.append(f"JSON validation error: {str(e)}")

        return issues

    def _validate_confidence_threshold(
        self, actual_output: str, test_case: TestCase, metadata: dict[str, Any] | None
    ) -> list[str]:
        """Validate confidence scores meet thresholds."""

        issues = []
        min_confidence = test_case.validation_criteria.get("min_confidence", 0.7)

        # Try to extract confidence from JSON
        try:
            json_start = actual_output.find("{")
            json_end = actual_output.rfind("}")

            if json_start >= 0 and json_end > json_start:
                json_text = actual_output[json_start : json_end + 1]
                parsed_json = json.loads(json_text)

                confidence = parsed_json.get("confidence")
                if confidence is not None:
                    if not isinstance(confidence, (int, float)):
                        issues.append("Confidence is not a number")
                    elif confidence < 0.0 or confidence > 1.0:
                        issues.append(f"Confidence out of range [0.0, 1.0]: {confidence}")
                    elif confidence < min_confidence:
                        issues.append(
                            f"Confidence below threshold: {confidence} < {min_confidence}"
                        )
                else:
                    issues.append("Confidence field not found in JSON response")

        except json.JSONDecodeError:
            issues.append("Cannot extract confidence: Invalid JSON format")
        except Exception as e:
            issues.append(f"Confidence validation error: {str(e)}")

        return issues

    def _validate_format(
        self, actual_output: str, test_case: TestCase, metadata: dict[str, Any] | None
    ) -> list[str]:
        """Validate general format requirements."""

        issues = []
        criteria = test_case.validation_criteria

        # Check minimum length
        min_length = criteria.get("min_length", 0)
        if len(actual_output) < min_length:
            issues.append(f"Output too short: {len(actual_output)} < {min_length}")

        # Check maximum length
        max_length = criteria.get("max_length", 10000)
        if len(actual_output) > max_length:
            issues.append(f"Output too long: {len(actual_output)} > {max_length}")

        # Check for empty response
        if not actual_output.strip():
            issues.append("Empty output")

        # Check for error indicators
        error_indicators = ["error", "failed", "exception", "traceback"]
        actual_lower = actual_output.lower()

        for indicator in error_indicators:
            if indicator in actual_lower:
                issues.append(f"Output contains error indicator: '{indicator}'")

        return issues

    def _validate_semantic_similarity(
        self, actual_output: str, test_case: TestCase, metadata: dict[str, Any] | None
    ) -> list[str]:
        """Validate semantic similarity to expected output."""

        issues = []

        if test_case.expected_output is None:
            return ["No expected output for semantic similarity comparison"]

        # Simple token-based similarity for production
        # production+ could use embedding-based similarity
        similarity_threshold = test_case.validation_criteria.get("similarity_threshold", 0.7)

        actual_tokens = set(actual_output.lower().split())
        expected_tokens = set(test_case.expected_output.lower().split())

        if not actual_tokens and not expected_tokens:
            return issues  # Both empty, consider similar

        if not actual_tokens or not expected_tokens:
            issues.append("One output is empty while the other is not")
            return issues

        # Jaccard similarity
        intersection = len(actual_tokens.intersection(expected_tokens))
        union = len(actual_tokens.union(expected_tokens))
        similarity = intersection / union if union > 0 else 0.0

        if similarity < similarity_threshold:
            issues.append(f"Low semantic similarity: {similarity:.2f} < {similarity_threshold}")

        return issues


class LLMTester:
    """
    Comprehensive LLM testing framework.

    Features:
    - Golden dataset testing
    - Response validation with multiple methods
    - Performance benchmarking
    - Cost calculation validation
    - Mock LLM testing
    - Regression testing
    """

    def __init__(self, test_data_dir: str | None = None):
        self.llm_gateway = get_llm_gateway()
        self.prompt_manager = get_prompt_manager()
        self.validator = ResponseValidator()

        # Test data directory
        if test_data_dir:
            self.test_data_dir = Path(test_data_dir)
        else:
            self.test_data_dir = Path(__file__).parent.parent.parent / "test_data" / "llm"

        self.test_data_dir.mkdir(parents=True, exist_ok=True)

        # Test execution history
        self.execution_history: list[TestExecution] = []

        # Test suites
        self.test_suites: dict[str, TestSuite] = {}

        logger.info("LLM Tester initialized", extra={"test_data_dir": str(self.test_data_dir)})

        # Load existing test suites
        self._load_test_suites()

        # Create default test suites if none exist
        if not self.test_suites:
            self._create_default_test_suites()

    async def run_test_case(self, test_case: TestCase) -> TestExecution:
        """Execute a single test case."""

        start_time = time.time()

        try:
            logger.debug(f"Running test case: {test_case.name}")

            # Execute the test based on input data type
            if "llm_request" in test_case.input_data:
                actual_output, metadata = await self._execute_llm_test(test_case)
            elif "agent_request" in test_case.input_data:
                actual_output, metadata = await self._execute_agent_test(test_case)
            elif "prompt_template" in test_case.input_data:
                actual_output, metadata = await self._execute_prompt_test(test_case)
            else:
                raise ValueError(
                    f"Unknown test case input type: {list(test_case.input_data.keys())}"
                )

            # Validate response
            result, issues = self.validator.validate_response(actual_output, test_case, metadata)

        except Exception as e:
            actual_output = f"ERROR: {str(e)}"
            result = TestResult.ERROR
            issues = [f"Test execution failed: {str(e)}"]
            metadata = {"error": str(e)}

        # Calculate execution time
        execution_time = (time.time() - start_time) * 1000

        # Create execution record
        execution = TestExecution(
            test_case=test_case,
            result=result,
            actual_output=actual_output,
            execution_time_ms=execution_time,
            issues=issues,
            metadata=metadata,
        )

        # Store in history
        self.execution_history.append(execution)

        logger.debug(
            f"Test case completed: {test_case.name}",
            extra={
                "result": result.value,
                "execution_time_ms": execution_time,
                "issues_count": len(issues),
            },
        )

        return execution

    async def _execute_llm_test(self, test_case: TestCase) -> tuple[str, dict[str, Any]]:
        """Execute LLM-specific test."""

        llm_request_data = test_case.input_data["llm_request"]

        # Create LLM request
        llm_request = LLMRequest(
            messages=llm_request_data["messages"],
            model_tier=ModelTier(llm_request_data.get("model_tier", "tier_1")),
            user_id=llm_request_data.get("user_id", "test_user"),
            request_id=f"test_{int(time.time())}",
            temperature=llm_request_data.get("temperature", 0.7),
            max_tokens=llm_request_data.get("max_tokens", 1000),
        )

        # Execute request
        response = await self.llm_gateway.process_request(llm_request)

        metadata = {
            "model_used": response.model_used,
            "provider_used": response.provider_used,
            "tokens_used": response.tokens_used,
            "cost_usd": response.cost_usd,
            "processing_time_ms": response.processing_time_ms,
            "from_cache": response.from_cache,
        }

        return response.content, metadata

    async def _execute_agent_test(self, test_case: TestCase) -> tuple[str, dict[str, Any]]:
        """Execute agent-specific test."""

        agent_request_data = test_case.input_data["agent_request"]

        # This would integrate with actual agent execution
        # For now, return a mock response
        metadata = {"test_type": "agent", "mock": True}
        mock_response = f"Agent response for: {agent_request_data.get('content', 'test')}"

        return mock_response, metadata

    async def _execute_prompt_test(self, test_case: TestCase) -> tuple[str, dict[str, Any]]:
        """Execute prompt template test."""

        prompt_data = test_case.input_data["prompt_template"]

        # Render prompt
        prompt = self.prompt_manager.get_prompt(
            prompt_data["name"], variables=prompt_data.get("variables", {})
        )

        metadata = {
            "prompt_name": prompt_data["name"],
            "variables_count": len(prompt_data.get("variables", {})),
            "prompt_length": len(prompt),
        }

        return prompt, metadata

    async def run_test_suite(self, suite_name: str) -> list[TestExecution]:
        """Run all test cases in a test suite."""

        if suite_name not in self.test_suites:
            raise ValueError(f"Test suite '{suite_name}' not found")

        suite = self.test_suites[suite_name]

        logger.info(
            f"Running test suite: {suite_name}", extra={"test_cases": len(suite.test_cases)}
        )

        # Run setup if provided
        if suite.setup_function:
            await suite.setup_function()

        try:
            # Run all test cases
            executions = []
            for test_case in suite.test_cases:
                execution = await self.run_test_case(test_case)
                executions.append(execution)

            # Generate summary
            passed = len([e for e in executions if e.result == TestResult.PASS])
            failed = len([e for e in executions if e.result == TestResult.FAIL])
            warnings = len([e for e in executions if e.result == TestResult.WARNING])
            errors = len([e for e in executions if e.result == TestResult.ERROR])

            logger.info(
                f"Test suite completed: {suite_name}",
                extra={
                    "total_tests": len(executions),
                    "passed": passed,
                    "failed": failed,
                    "warnings": warnings,
                    "errors": errors,
                },
            )

            return executions

        finally:
            # Run teardown if provided
            if suite.teardown_function:
                await suite.teardown_function()

    def _load_test_suites(self):
        """Load test suites from disk."""

        for suite_file in self.test_data_dir.glob("*_suite.json"):
            try:
                self._load_test_suite_file(suite_file)
            except Exception as e:
                logger.error(f"Failed to load test suite {suite_file}: {e}")

    def _load_test_suite_file(self, suite_file: Path):
        """Load a single test suite file."""

        with open(suite_file, encoding="utf-8") as f:
            data = json.load(f)

        # Create test suite
        suite = TestSuite(name=data["name"], description=data.get("description", ""))

        # Load test cases
        for tc_data in data.get("test_cases", []):
            validation_methods = [
                ValidationMethod(method)
                for method in tc_data.get("validation_methods", ["format_validation"])
            ]

            test_case = TestCase(
                name=tc_data["name"],
                description=tc_data.get("description", ""),
                input_data=tc_data["input_data"],
                expected_output=tc_data.get("expected_output"),
                validation_methods=validation_methods,
                validation_criteria=tc_data.get("validation_criteria", {}),
                timeout_seconds=tc_data.get("timeout_seconds", 30),
                tags=tc_data.get("tags", []),
            )

            suite.add_test_case(test_case)

        self.test_suites[suite.name] = suite

        logger.info(f"Loaded test suite: {suite.name} ({len(suite.test_cases)} test cases)")

    def _create_default_test_suites(self):
        """Create default test suites."""

        logger.info("Creating default test suites")

        # Activity Classification Test Suite
        classification_suite = TestSuite(
            name="activity_classification", description="Test activity classification accuracy"
        )

        classification_tests = [
            TestCase(
                name="technical_activity_classification",
                description="Test classification of technical activities",
                input_data={
                    "llm_request": {
                        "messages": [
                            {
                                "role": "user",
                                "content": "Classify this activity: Fixed a critical bug in the payment processing system by analyzing logs and implementing a robust error handling mechanism.",
                            }
                        ],
                        "model_tier": "tier_1",
                    }
                },
                validation_methods=[
                    ValidationMethod.KEYWORD_PRESENCE,
                    ValidationMethod.JSON_STRUCTURE,
                ],
                validation_criteria={
                    "required_keywords": ["technical", "problem solving", "bug"],
                    "required_fields": ["classification", "confidence"],
                },
                tags=["classification", "technical"],
            ),
            TestCase(
                name="leadership_activity_classification",
                description="Test classification of leadership activities",
                input_data={
                    "llm_request": {
                        "messages": [
                            {
                                "role": "user",
                                "content": "Classify this activity: Led a cross-functional team meeting to align on project goals, facilitated discussion, and assigned responsibilities to team members.",
                            }
                        ],
                        "model_tier": "tier_1",
                    }
                },
                validation_methods=[
                    ValidationMethod.KEYWORD_PRESENCE,
                    ValidationMethod.JSON_STRUCTURE,
                ],
                validation_criteria={
                    "required_keywords": ["leadership", "team", "facilitation"],
                    "required_fields": ["classification", "confidence"],
                },
                tags=["classification", "leadership"],
            ),
        ]

        for test in classification_tests:
            classification_suite.add_test_case(test)

        # Competency Assessment Test Suite
        assessment_suite = TestSuite(
            name="competency_assessment", description="Test competency level assessments"
        )

        assessment_tests = [
            TestCase(
                name="senior_level_assessment",
                description="Test assessment of senior-level competency",
                input_data={
                    "llm_request": {
                        "messages": [
                            {
                                "role": "user",
                                "content": "Assess competency level: Mentored 3 junior developers, conducted code reviews, designed system architecture, and led technical decision making for the team.",
                            }
                        ],
                        "model_tier": "tier_2",
                    }
                },
                validation_methods=[
                    ValidationMethod.JSON_STRUCTURE,
                    ValidationMethod.CONFIDENCE_THRESHOLD,
                ],
                validation_criteria={
                    "required_fields": ["score", "gaps", "recommendations"],
                    "min_confidence": 0.7,
                },
                tags=["assessment", "senior"],
            )
        ]

        for test in assessment_tests:
            assessment_suite.add_test_case(test)

        # Prompt Template Test Suite
        prompt_suite = TestSuite(
            name="prompt_templates", description="Test prompt template rendering"
        )

        prompt_tests = [
            TestCase(
                name="analysis_agent_prompt",
                description="Test analysis agent prompt template",
                input_data={
                    "prompt_template": {
                        "name": "agents/analysis_agent",
                        "variables": {
                            "task_description": "Test task",
                            "user_context": {"level": "Senior", "role": "Engineer"},
                        },
                    }
                },
                validation_methods=[
                    ValidationMethod.FORMAT_VALIDATION,
                    ValidationMethod.KEYWORD_PRESENCE,
                ],
                validation_criteria={
                    "min_length": 100,
                    "required_keywords": ["analyze", "competency", "JSON"],
                },
                tags=["prompts", "analysis"],
            )
        ]

        for test in prompt_tests:
            prompt_suite.add_test_case(test)

        # Add suites to collection
        self.test_suites["activity_classification"] = classification_suite
        self.test_suites["competency_assessment"] = assessment_suite
        self.test_suites["prompt_templates"] = prompt_suite

        # Save to disk
        self._save_test_suites()

    def _save_test_suites(self):
        """Save test suites to disk."""

        for _name, suite in self.test_suites.items():
            self._save_test_suite(suite)

    def _save_test_suite(self, suite: TestSuite):
        """Save single test suite to disk."""

        suite_file = self.test_data_dir / f"{suite.name}_suite.json"

        data = {
            "name": suite.name,
            "description": suite.description,
            "test_cases": [
                {
                    "name": tc.name,
                    "description": tc.description,
                    "input_data": tc.input_data,
                    "expected_output": tc.expected_output,
                    "validation_methods": [method.value for method in tc.validation_methods],
                    "validation_criteria": tc.validation_criteria,
                    "timeout_seconds": tc.timeout_seconds,
                    "tags": tc.tags,
                }
                for tc in suite.test_cases
            ],
        }

        with open(suite_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        logger.debug(f"Saved test suite to {suite_file}")

    def generate_test_report(
        self, executions: list[TestExecution], output_file: str | None = None
    ) -> str:
        """Generate comprehensive test report."""

        if not executions:
            return "No test executions to report"

        # Calculate statistics
        total_tests = len(executions)
        passed = len([e for e in executions if e.result == TestResult.PASS])
        failed = len([e for e in executions if e.result == TestResult.FAIL])
        warnings = len([e for e in executions if e.result == TestResult.WARNING])
        errors = len([e for e in executions if e.result == TestResult.ERROR])

        avg_execution_time = statistics.mean([e.execution_time_ms for e in executions])
        total_cost = sum([e.metadata.get("cost_usd", 0.0) for e in executions])

        # Build report
        report_lines = [
            "# LLM Testing Report",
            f"Generated: {datetime.now(UTC).isoformat()}",
            "",
            "## Summary",
            f"- Total Tests: {total_tests}",
            f"- Passed: {passed} ({passed / total_tests * 100:.1f}%)",
            f"- Failed: {failed} ({failed / total_tests * 100:.1f}%)",
            f"- Warnings: {warnings} ({warnings / total_tests * 100:.1f}%)",
            f"- Errors: {errors} ({errors / total_tests * 100:.1f}%)",
            f"- Average Execution Time: {avg_execution_time:.1f}ms",
            f"- Total Cost: ${total_cost:.4f}",
            "",
        ]

        # Failed tests details
        if failed > 0 or errors > 0:
            report_lines.extend(["## Failed/Error Tests", ""])

            for execution in executions:
                if execution.result in [TestResult.FAIL, TestResult.ERROR]:
                    report_lines.extend(
                        [
                            f"### {execution.test_case.name}",
                            f"- Result: {execution.result.value}",
                            f"- Execution Time: {execution.execution_time_ms:.1f}ms",
                            f"- Issues: {'; '.join(execution.issues)}",
                            "",
                        ]
                    )

        # Performance analysis
        if total_cost > 0:
            report_lines.extend(
                [
                    "## Cost Analysis",
                    f"- Total Cost: ${total_cost:.4f}",
                    f"- Average Cost per Test: ${total_cost / total_tests:.4f}",
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
        """Get LLM tester statistics."""

        recent_executions = [
            e for e in self.execution_history if (datetime.now(UTC) - e.timestamp).days < 7
        ]

        return {
            "test_suites": {
                "total": len(self.test_suites),
                "test_cases": sum(len(suite.test_cases) for suite in self.test_suites.values()),
            },
            "executions": {
                "total": len(self.execution_history),
                "recent_week": len(recent_executions),
            },
            "recent_results": {
                "passed": len([e for e in recent_executions if e.result == TestResult.PASS]),
                "failed": len([e for e in recent_executions if e.result == TestResult.FAIL]),
                "warnings": len([e for e in recent_executions if e.result == TestResult.WARNING]),
                "errors": len([e for e in recent_executions if e.result == TestResult.ERROR]),
            },
            "suites_available": list(self.test_suites.keys()),
        }


# Global LLM tester instance
_llm_tester: LLMTester | None = None


def get_llm_tester() -> LLMTester:
    """Get or create global LLM tester instance."""
    global _llm_tester
    if _llm_tester is None:
        _llm_tester = LLMTester()
    return _llm_tester
