"""
Guardrails AI Configuration and Output Validation

Implements  Guardrails AI Configuration for structured output
validation, PII detection, and response quality assurance.
"""

import json
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any

# Optional imports for graceful degradation
try:
    from guardrails import Guard
    from guardrails.hub import DetectPII, ProfanityFree, RegexMatch, TwoWords, ValidJSON

    GUARDRAILS_AVAILABLE = True
except ImportError:
    GUARDRAILS_AVAILABLE = False

from src.shared import get_logger

logger = get_logger(__name__)


class ValidationResult(str, Enum):
    """Validation result status."""

    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"


@dataclass
class ValidationIssue:
    """Individual validation issue."""

    field: str
    issue_type: str
    message: str
    severity: ValidationResult
    suggested_fix: str | None = None


@dataclass
class GuardrailsResult:
    """Complete guardrails validation result."""

    is_valid: bool
    confidence_score: float
    issues: list[ValidationIssue]
    validated_data: dict[str, Any] | None = None
    raw_output: str = ""


class AgentOutputSchema(ABC):
    """Base class for agent-specific output schemas."""

    @abstractmethod
    def get_required_fields(self) -> list[str]:
        """Get list of required fields for this schema."""
        pass

    @abstractmethod
    def validate_structure(self, data: dict[str, Any]) -> list[ValidationIssue]:
        """Validate the structure of the output data."""
        pass

    @abstractmethod
    def get_schema_description(self) -> str:
        """Get human-readable schema description."""
        pass


class DataAnalystSchema(AgentOutputSchema):
    """Schema for Data Analyst agent outputs."""

    def get_required_fields(self) -> list[str]:
        return ["classification", "confidence", "evidence"]

    def validate_structure(self, data: dict[str, Any]) -> list[ValidationIssue]:
        issues = []

        # Validate classification
        if "classification" not in data:
            issues.append(
                ValidationIssue(
                    field="classification",
                    issue_type="missing_field",
                    message="Classification field is required",
                    severity=ValidationResult.FAILED,
                )
            )
        elif (
            not isinstance(data["classification"], str) or len(data["classification"].strip()) == 0
        ):
            issues.append(
                ValidationIssue(
                    field="classification",
                    issue_type="invalid_format",
                    message="Classification must be a non-empty string",
                    severity=ValidationResult.FAILED,
                )
            )

        # Validate confidence
        if "confidence" not in data:
            issues.append(
                ValidationIssue(
                    field="confidence",
                    issue_type="missing_field",
                    message="Confidence field is required",
                    severity=ValidationResult.FAILED,
                )
            )
        elif not isinstance(data["confidence"], (int, float)) or not (
            0.0 <= data["confidence"] <= 1.0
        ):
            issues.append(
                ValidationIssue(
                    field="confidence",
                    issue_type="invalid_range",
                    message="Confidence must be a number between 0.0 and 1.0",
                    severity=ValidationResult.FAILED,
                    suggested_fix="Set confidence to a value between 0.0 and 1.0",
                )
            )

        # Validate evidence
        if "evidence" not in data:
            issues.append(
                ValidationIssue(
                    field="evidence",
                    issue_type="missing_field",
                    message="Evidence field is required",
                    severity=ValidationResult.FAILED,
                )
            )
        elif not isinstance(data["evidence"], list) or len(data["evidence"]) == 0:
            issues.append(
                ValidationIssue(
                    field="evidence",
                    issue_type="insufficient_data",
                    message="Evidence must be a non-empty list",
                    severity=ValidationResult.WARNING,
                    suggested_fix="Provide at least one piece of evidence",
                )
            )

        return issues

    def get_schema_description(self) -> str:
        return "Data Analyst output with classification, confidence score (0.0-1.0), and supporting evidence list"


class CompetencySchema(AgentOutputSchema):
    """Schema for Competency Specialist agent outputs."""

    def get_required_fields(self) -> list[str]:
        return ["score", "gaps", "recommendations"]

    def validate_structure(self, data: dict[str, Any]) -> list[ValidationIssue]:
        issues = []

        # Validate score
        if "score" not in data:
            issues.append(
                ValidationIssue(
                    field="score",
                    issue_type="missing_field",
                    message="Score field is required",
                    severity=ValidationResult.FAILED,
                )
            )
        elif not isinstance(data["score"], (int, float)) or not (0.0 <= data["score"] <= 5.0):
            issues.append(
                ValidationIssue(
                    field="score",
                    issue_type="invalid_range",
                    message="Score must be a number between 0.0 and 5.0",
                    severity=ValidationResult.FAILED,
                    suggested_fix="Set score to a value between 0.0 and 5.0",
                )
            )

        # Validate gaps
        if "gaps" not in data:
            issues.append(
                ValidationIssue(
                    field="gaps",
                    issue_type="missing_field",
                    message="Gaps field is required",
                    severity=ValidationResult.FAILED,
                )
            )
        elif not isinstance(data["gaps"], list):
            issues.append(
                ValidationIssue(
                    field="gaps",
                    issue_type="invalid_format",
                    message="Gaps must be a list",
                    severity=ValidationResult.FAILED,
                )
            )

        # Validate recommendations
        if "recommendations" not in data:
            issues.append(
                ValidationIssue(
                    field="recommendations",
                    issue_type="missing_field",
                    message="Recommendations field is required",
                    severity=ValidationResult.FAILED,
                )
            )
        elif not isinstance(data["recommendations"], list) or len(data["recommendations"]) == 0:
            issues.append(
                ValidationIssue(
                    field="recommendations",
                    issue_type="insufficient_data",
                    message="Recommendations must be a non-empty list",
                    severity=ValidationResult.WARNING,
                )
            )

        return issues

    def get_schema_description(self) -> str:
        return "Competency assessment with score (0.0-5.0), identified gaps list, and recommendations list"


class CareerSchema(AgentOutputSchema):
    """Schema for Career Strategist agent outputs."""

    def get_required_fields(self) -> list[str]:
        return ["opportunities", "development_plan", "timeline"]

    def validate_structure(self, data: dict[str, Any]) -> list[ValidationIssue]:
        issues = []

        # Validate opportunities
        if "opportunities" not in data:
            issues.append(
                ValidationIssue(
                    field="opportunities",
                    issue_type="missing_field",
                    message="Opportunities field is required",
                    severity=ValidationResult.FAILED,
                )
            )
        elif not isinstance(data["opportunities"], list) or len(data["opportunities"]) == 0:
            issues.append(
                ValidationIssue(
                    field="opportunities",
                    issue_type="insufficient_data",
                    message="Opportunities must be a non-empty list",
                    severity=ValidationResult.WARNING,
                )
            )

        # Validate development_plan
        if "development_plan" not in data:
            issues.append(
                ValidationIssue(
                    field="development_plan",
                    issue_type="missing_field",
                    message="Development plan field is required",
                    severity=ValidationResult.FAILED,
                )
            )
        elif not isinstance(data["development_plan"], dict):
            issues.append(
                ValidationIssue(
                    field="development_plan",
                    issue_type="invalid_format",
                    message="Development plan must be an object/dictionary",
                    severity=ValidationResult.FAILED,
                )
            )

        # Validate timeline
        if "timeline" not in data:
            issues.append(
                ValidationIssue(
                    field="timeline",
                    issue_type="missing_field",
                    message="Timeline field is required",
                    severity=ValidationResult.FAILED,
                )
            )
        elif not isinstance(data["timeline"], str) or len(data["timeline"].strip()) == 0:
            issues.append(
                ValidationIssue(
                    field="timeline",
                    issue_type="invalid_format",
                    message="Timeline must be a non-empty string",
                    severity=ValidationResult.FAILED,
                )
            )

        return issues

    def get_schema_description(self) -> str:
        return (
            "Career guidance with opportunities list, development plan object, and timeline string"
        )


class SynthesizerSchema(AgentOutputSchema):
    """Schema for Insight Synthesizer agent outputs."""

    def get_required_fields(self) -> list[str]:
        return ["insights", "summary", "actions"]

    def validate_structure(self, data: dict[str, Any]) -> list[ValidationIssue]:
        issues = []

        # Validate insights
        if "insights" not in data:
            issues.append(
                ValidationIssue(
                    field="insights",
                    issue_type="missing_field",
                    message="Insights field is required",
                    severity=ValidationResult.FAILED,
                )
            )
        elif not isinstance(data["insights"], list) or len(data["insights"]) == 0:
            issues.append(
                ValidationIssue(
                    field="insights",
                    issue_type="insufficient_data",
                    message="Insights must be a non-empty list",
                    severity=ValidationResult.WARNING,
                )
            )

        # Validate summary
        if "summary" not in data:
            issues.append(
                ValidationIssue(
                    field="summary",
                    issue_type="missing_field",
                    message="Summary field is required",
                    severity=ValidationResult.FAILED,
                )
            )
        elif not isinstance(data["summary"], str) or len(data["summary"].strip()) < 10:
            issues.append(
                ValidationIssue(
                    field="summary",
                    issue_type="insufficient_content",
                    message="Summary must be a string with at least 10 characters",
                    severity=ValidationResult.WARNING,
                )
            )

        # Validate actions
        if "actions" not in data:
            issues.append(
                ValidationIssue(
                    field="actions",
                    issue_type="missing_field",
                    message="Actions field is required",
                    severity=ValidationResult.FAILED,
                )
            )
        elif not isinstance(data["actions"], list):
            issues.append(
                ValidationIssue(
                    field="actions",
                    issue_type="invalid_format",
                    message="Actions must be a list",
                    severity=ValidationResult.FAILED,
                )
            )

        return issues

    def get_schema_description(self) -> str:
        return "Insight synthesis with insights list, summary string, and actions list"


class PIIDetector:
    """PII detection and redaction utility."""

    def __init__(self):
        # Common PII patterns
        self.patterns = {
            "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),
            "phone": re.compile(
                r"\b(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})\b"
            ),
            "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
            "credit_card": re.compile(r"\b(?:\d{4}[-\s]?){3}\d{4}\b"),
            "ip_address": re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),
        }

    def detect_pii(self, text: str) -> list[ValidationIssue]:
        """Detect PII in text content."""
        issues = []

        for pii_type, pattern in self.patterns.items():
            matches = pattern.findall(text)
            if matches:
                issues.append(
                    ValidationIssue(
                        field="content",
                        issue_type=f"pii_{pii_type}",
                        message=f"Detected {pii_type.upper()} in response content",
                        severity=ValidationResult.FAILED,
                        suggested_fix=f"Remove or redact {pii_type} information",
                    )
                )

        return issues

    def redact_pii(self, text: str) -> str:
        """Redact PII from text content."""
        redacted_text = text

        for pii_type, pattern in self.patterns.items():
            if pii_type == "email":
                redacted_text = pattern.sub("[EMAIL_REDACTED]", redacted_text)
            elif pii_type == "phone":
                redacted_text = pattern.sub("[PHONE_REDACTED]", redacted_text)
            elif pii_type == "ssn":
                redacted_text = pattern.sub("[SSN_REDACTED]", redacted_text)
            elif pii_type == "credit_card":
                redacted_text = pattern.sub("[CC_REDACTED]", redacted_text)
            elif pii_type == "ip_address":
                redacted_text = pattern.sub("[IP_REDACTED]", redacted_text)

        return redacted_text


class GuardrailsValidator:
    """
    Comprehensive output validation system for agent responses.

    Features:
    - Schema validation per agent type using Guardrails AI
    - PII detection and redaction with Guardrails AI
    - JSON format validation
    - Confidence score validation
    - Custom validation rules
    - Graceful fallback to custom validation when Guardrails AI not available
    """

    def __init__(self):
        self.schemas = {
            "data_analyst": DataAnalystSchema(),
            "competency": CompetencySchema(),
            "career": CareerSchema(),
            "synthesizer": SynthesizerSchema(),
        }
        self.pii_detector = PIIDetector()

        # Initialize Guardrails AI guards if available
        self.guards = {}
        self._init_guardrails_guards()

        if GUARDRAILS_AVAILABLE:
            logger.info(
                "Guardrails validator initialized with Guardrails AI integration",
                extra={
                    "guardrails_available": True,
                    "schemas_count": len(self.schemas),
                    "guards_count": len(self.guards),
                },
            )
        else:
            logger.warning(
                "Guardrails validator initialized without Guardrails AI - using custom validation",
                extra={
                    "guardrails_available": False,
                    "schemas_count": len(self.schemas),
                    "install_command": "pip install guardrails-ai",
                },
            )

    def _init_guardrails_guards(self):
        """Initialize Guardrails AI guards for each agent type."""
        if not GUARDRAILS_AVAILABLE:
            return

        try:
            # Common validators for all agent types
            common_validators = [
                DetectPII(
                    pii_entities=["EMAIL_ADDRESS", "PHONE_NUMBER", "SSN", "CREDIT_CARD"],
                    on_fail="exception",
                ),
                ProfanityFree(on_fail="filter"),
            ]

            # Data Analyst Guard
            self.guards["data_analyst"] = Guard().use_many(
                common_validators
                + [
                    ValidJSON(on_fail="reask"),
                    RegexMatch(regex=r'"classification"\s*:\s*"[^"]+', on_fail="reask"),
                    RegexMatch(regex=r'"confidence"\s*:\s*[0-9.]+', on_fail="reask"),
                ]
            )

            # Competency Specialist Guard
            self.guards["competency"] = Guard().use_many(
                common_validators
                + [
                    ValidJSON(on_fail="reask"),
                    RegexMatch(regex=r'"score"\s*:\s*[0-5](\.[0-9]+)?', on_fail="reask"),
                    RegexMatch(regex=r'"gaps"\s*:\s*\[', on_fail="reask"),
                ]
            )

            # Career Strategist Guard
            self.guards["career"] = Guard().use_many(
                common_validators
                + [
                    ValidJSON(on_fail="reask"),
                    RegexMatch(regex=r'"opportunities"\s*:\s*\[', on_fail="reask"),
                    RegexMatch(regex=r'"development_plan"\s*:\s*\{', on_fail="reask"),
                ]
            )

            # Insight Synthesizer Guard
            self.guards["synthesizer"] = Guard().use_many(
                common_validators
                + [
                    ValidJSON(on_fail="reask"),
                    RegexMatch(regex=r'"insights"\s*:\s*\[', on_fail="reask"),
                    TwoWords(on_fail="filter"),  # Ensure summary has substantial content
                ]
            )

            logger.debug(
                "Guardrails AI guards initialized successfully",
                extra={"guards_created": list(self.guards.keys())},
            )

        except Exception as e:
            logger.warning(
                f"Failed to initialize Guardrails AI guards: {e}",
                extra={"error_type": type(e).__name__},
                exc_info=True,
            )
            self.guards.clear()  # Clear partial initialization

    def _validate_with_guardrails(
        self, agent_type: str, raw_output: str
    ) -> GuardrailsResult | None:
        """Validate using Guardrails AI guard for the agent type."""
        if not GUARDRAILS_AVAILABLE or agent_type not in self.guards:
            return None

        try:
            guard = self.guards[agent_type]

            # Use the guard to validate the output
            validation_outcome = guard.validate(raw_output)

            issues = []
            validated_data = None

            # Convert Guardrails validation outcome to our format
            if validation_outcome.validation_passed:
                try:
                    # Try to parse the validated output as JSON
                    validated_data = json.loads(validation_outcome.validated_output)
                except json.JSONDecodeError:
                    validated_data = {"content": validation_outcome.validated_output}

                confidence_score = 0.9  # High confidence for passed validation

                # Check for any filters applied
                if (
                    hasattr(validation_outcome, "validated_output")
                    and validation_outcome.validated_output != raw_output
                ):
                    issues.append(
                        ValidationIssue(
                            field="content",
                            issue_type="content_filtered",
                            message="Content was filtered by Guardrails AI",
                            severity=ValidationResult.WARNING,
                            suggested_fix="Review filtered content",
                        )
                    )
                    confidence_score = 0.8  # Slightly lower confidence for filtered content

            else:
                # Validation failed
                confidence_score = 0.3

                # Convert Guardrails errors to our format
                if hasattr(validation_outcome, "error_spans_in_output"):
                    for error_span in validation_outcome.error_spans_in_output:
                        issues.append(
                            ValidationIssue(
                                field=getattr(error_span, "path", "content"),
                                issue_type=getattr(error_span, "reason", "validation_failed"),
                                message=f"Guardrails validation failed: {getattr(error_span, 'reason', 'Unknown error')}",
                                severity=ValidationResult.FAILED,
                                suggested_fix="Review and correct the flagged content",
                            )
                        )

                # Try to use the original output if validation failed but data is parseable
                try:
                    validated_data = json.loads(raw_output)
                except json.JSONDecodeError:
                    validated_data = {"content": raw_output}

            result = GuardrailsResult(
                is_valid=validation_outcome.validation_passed,
                confidence_score=confidence_score,
                issues=issues,
                validated_data=validated_data,
                raw_output=raw_output,
            )

            logger.debug(
                "Guardrails AI validation completed",
                extra={
                    "agent_type": agent_type,
                    "validation_passed": validation_outcome.validation_passed,
                    "issues_count": len(issues),
                    "confidence_score": confidence_score,
                },
            )

            return result

        except Exception as e:
            logger.warning(
                f"Guardrails AI validation failed for {agent_type}: {e}",
                extra={"error_type": type(e).__name__, "agent_type": agent_type},
                exc_info=True,
            )
            return None  # Fall back to custom validation

    def validate_response(
        self, agent_type: str, raw_output: str, require_json: bool = True
    ) -> GuardrailsResult:
        """
        Validate agent response against schema and rules using Guardrails AI when available.

        Args:
            agent_type: Type of agent (data_analyst, competency, career, synthesizer)
            raw_output: Raw response from LLM
            require_json: Whether to require JSON format

        Returns:
            Validation result with issues and validated data
        """

        issues = []
        validated_data = None
        confidence_score = 0.0

        try:
            # First try Guardrails AI validation if available
            if GUARDRAILS_AVAILABLE and agent_type in self.guards:
                guardrails_result = self._validate_with_guardrails(agent_type, raw_output)
                if guardrails_result:
                    return guardrails_result

            # Fallback to custom validation
            logger.debug(
                f"Using custom validation for {agent_type}",
                extra={
                    "guardrails_available": GUARDRAILS_AVAILABLE,
                    "has_guard": agent_type in self.guards,
                },
            )

            # Check for PII first
            pii_issues = self.pii_detector.detect_pii(raw_output)
            issues.extend(pii_issues)

            # Parse JSON if required
            if require_json:
                try:
                    validated_data = json.loads(raw_output)
                except json.JSONDecodeError as e:
                    issues.append(
                        ValidationIssue(
                            field="format",
                            issue_type="invalid_json",
                            message=f"Response is not valid JSON: {str(e)}",
                            severity=ValidationResult.FAILED,
                            suggested_fix="Ensure response is valid JSON format",
                        )
                    )
                    # Try to extract JSON from response
                    validated_data = self._try_extract_json(raw_output)
            else:
                # For non-JSON responses, create a simple structure
                validated_data = {"content": raw_output}

            # Validate against schema if we have data
            if validated_data and agent_type in self.schemas:
                schema = self.schemas[agent_type]
                schema_issues = schema.validate_structure(validated_data)
                issues.extend(schema_issues)

                # Calculate confidence based on validation results
                confidence_score = self._calculate_confidence(issues, validated_data)

            # Determine overall validity
            failed_issues = [issue for issue in issues if issue.severity == ValidationResult.FAILED]
            is_valid = len(failed_issues) == 0

            result = GuardrailsResult(
                is_valid=is_valid,
                confidence_score=confidence_score,
                issues=issues,
                validated_data=validated_data,
                raw_output=raw_output,
            )

            logger.debug(
                "Response validation completed",
                extra={
                    "agent_type": agent_type,
                    "validation_method": "guardrails_ai" if GUARDRAILS_AVAILABLE else "custom",
                    "is_valid": is_valid,
                    "issues_count": len(issues),
                    "confidence_score": confidence_score,
                },
            )

            return result

        except Exception as e:
            logger.error(
                f"Validation failed with error: {e}",
                extra={"agent_type": agent_type, "error": str(e)},
                exc_info=True,
            )

            return GuardrailsResult(
                is_valid=False,
                confidence_score=0.0,
                issues=[
                    ValidationIssue(
                        field="system",
                        issue_type="validation_error",
                        message=f"Validation system error: {str(e)}",
                        severity=ValidationResult.FAILED,
                    )
                ],
                raw_output=raw_output,
            )

    def _try_extract_json(self, text: str) -> dict[str, Any] | None:
        """Try to extract JSON from malformed response."""

        # Look for JSON-like structures
        json_start = text.find("{")
        json_end = text.rfind("}")

        if json_start >= 0 and json_end > json_start:
            try:
                json_text = text[json_start : json_end + 1]
                return json.loads(json_text)
            except json.JSONDecodeError:
                pass

        return None

    def _calculate_confidence(
        self, issues: list[ValidationIssue], data: dict[str, Any] | None
    ) -> float:
        """Calculate confidence score based on validation results."""

        if not data:
            return 0.0

        # Start with base confidence
        confidence = 0.8

        # Reduce confidence for each issue
        for issue in issues:
            if issue.severity == ValidationResult.FAILED:
                confidence -= 0.3
            elif issue.severity == ValidationResult.WARNING:
                confidence -= 0.1

        # Boost confidence for well-structured data
        if isinstance(data, dict):
            required_fields = 3  # Typical number of required fields
            present_fields = len(data.keys())

            if present_fields >= required_fields:
                confidence += 0.1

        # Ensure confidence is in valid range
        return max(0.0, min(1.0, confidence))

    def get_schema_info(self, agent_type: str) -> dict[str, Any] | None:
        """Get schema information for agent type."""

        if agent_type not in self.schemas:
            return None

        schema = self.schemas[agent_type]

        return {
            "agent_type": agent_type,
            "description": schema.get_schema_description(),
            "required_fields": schema.get_required_fields(),
            "validation_rules": [
                "No PII in responses",
                "Confidence scores 0.0-1.0",
                "Required fields present",
                "Valid JSON format",
            ],
        }

    def get_validation_stats(self) -> dict[str, Any]:
        """Get validation system statistics."""

        validation_features = [
            "Schema validation",
            "PII detection",
            "JSON format validation",
            "Confidence scoring",
            "Auto-correction suggestions",
        ]

        if GUARDRAILS_AVAILABLE:
            validation_features.extend(
                [
                    "Guardrails AI integration",
                    "Advanced PII detection",
                    "Profanity filtering",
                    "Regex pattern matching",
                    "Content rewriting",
                ]
            )

        return {
            "guardrails_ai_available": GUARDRAILS_AVAILABLE,
            "schemas_available": list(self.schemas.keys()),
            "guardrails_guards": list(self.guards.keys()) if GUARDRAILS_AVAILABLE else [],
            "pii_patterns": list(self.pii_detector.patterns.keys()),
            "validation_features": validation_features,
            "validation_method": "guardrails_ai_with_fallback"
            if GUARDRAILS_AVAILABLE
            else "custom_only",
        }


# Global validator instance
_guardrails_validator: GuardrailsValidator | None = None


def get_guardrails_validator() -> GuardrailsValidator:
    """Get or create global guardrails validator instance."""
    global _guardrails_validator
    if _guardrails_validator is None:
        _guardrails_validator = GuardrailsValidator()
    return _guardrails_validator
