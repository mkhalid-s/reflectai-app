"""
Comprehensive Validation Middleware for ReflectAI

Provides input validation, data sanitization, and schema validation
across all platform components with consistent error handling.
"""

import re
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from re import Pattern
from typing import Any
from uuid import UUID

import structlog

from .exceptions import ValidationError

logger = structlog.get_logger(__name__)


class ValidationType(str, Enum):
    """Types of validation to perform."""

    REQUIRED = "required"
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    EMAIL = "email"
    UUID = "uuid"
    DATE = "date"
    LIST = "list"
    DICT = "dict"
    REGEX = "regex"
    ENUM = "enum"
    RANGE = "range"
    LENGTH = "length"
    CUSTOM = "custom"


@dataclass
class ValidationRule:
    """Individual validation rule specification."""

    field_name: str
    validation_type: ValidationType
    required: bool = False

    # Type-specific constraints
    min_value: int | float | None = None
    max_value: int | float | None = None
    min_length: int | None = None
    max_length: int | None = None
    pattern: Pattern | None = None
    enum_values: list[Any] | None = None
    custom_validator: Callable[[Any], bool] | None = None

    # Error messages
    error_message: str | None = None
    user_message: str | None = None

    # Additional context
    description: str | None = None
    example: Any | None = None


@dataclass
class ValidationSchema:
    """Collection of validation rules for a data structure."""

    name: str
    rules: list[ValidationRule]
    strict: bool = False  # If True, reject unknown fields
    description: str | None = None


@dataclass
class ValidationResult:
    """Result of validation operation."""

    valid: bool
    errors: list[ValidationError] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    sanitized_data: dict[str, Any] | None = None

    def add_error(
        self, field: str, message: str, value: Any = None, user_message: str | None = None
    ):
        """Add validation error."""
        self.valid = False
        self.errors.append(
            ValidationError(
                message=f"Validation failed for field '{field}': {message}",
                field=field,
                value=value,
            )
        )

    def add_warning(self, message: str):
        """Add validation warning."""
        self.warnings.append(message)


class DataValidator:
    """
    Comprehensive data validator with support for multiple validation types
    and customizable rules.
    """

    def __init__(self):
        self.schemas: dict[str, ValidationSchema] = {}
        self._email_pattern = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
        self._uuid_pattern = re.compile(
            r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.IGNORECASE
        )

    def register_schema(self, schema: ValidationSchema):
        """Register a validation schema."""
        self.schemas[schema.name] = schema
        logger.info("Validation schema registered", schema_name=schema.name)

    def validate(
        self,
        data: dict[str, Any],
        schema_name: str | None = None,
        schema: ValidationSchema | None = None,
    ) -> ValidationResult:
        """
        Validate data against a schema.

        Args:
            data: Data to validate
            schema_name: Name of registered schema to use
            schema: Schema instance to use (overrides schema_name)

        Returns:
            ValidationResult with errors, warnings, and sanitized data
        """
        if schema is None:
            if schema_name is None:
                raise ValueError("Either schema_name or schema must be provided")

            if schema_name not in self.schemas:
                raise ValueError(f"Schema '{schema_name}' not found")

            schema = self.schemas[schema_name]

        result = ValidationResult(valid=True, sanitized_data={})

        # Check for required fields
        for rule in schema.rules:
            if rule.required and rule.field_name not in data:
                result.add_error(
                    rule.field_name,
                    "Field is required",
                    user_message=rule.user_message or f"{rule.field_name} is required",
                )

        # Validate present fields
        for field_name, value in data.items():
            # Find matching rule
            rule = next((r for r in schema.rules if r.field_name == field_name), None)

            if rule is None:
                if schema.strict:
                    result.add_error(field_name, "Unknown field", value)
                else:
                    result.add_warning(f"Unknown field '{field_name}' will be ignored")
                continue

            # Perform validation
            field_result = self._validate_field(field_name, value, rule)

            if not field_result.valid:
                result.errors.extend(field_result.errors)
                result.valid = False
            else:
                result.sanitized_data[field_name] = field_result.sanitized_data.get(
                    field_name, value
                )

        return result

    def _validate_field(
        self, field_name: str, value: Any, rule: ValidationRule
    ) -> ValidationResult:
        """Validate a single field against a rule."""
        result = ValidationResult(valid=True, sanitized_data={field_name: value})

        # Handle None values
        if value is None:
            if rule.required:
                result.add_error(field_name, "Cannot be None", value, rule.user_message)
            return result

        # Type validation
        try:
            validated_value = self._validate_type(value, rule)
            result.sanitized_data[field_name] = validated_value
        except ValidationError as e:
            result.errors.append(e)
            result.valid = False
            return result

        # Constraint validation
        try:
            self._validate_constraints(field_name, validated_value, rule, result)
        except ValidationError as e:
            result.errors.append(e)
            result.valid = False

        return result

    def _validate_type(self, value: Any, rule: ValidationRule) -> Any:
        """Validate and convert value based on type."""
        validation_type = rule.validation_type

        if validation_type == ValidationType.STRING:
            return self._validate_string(value, rule)
        elif validation_type == ValidationType.INTEGER:
            return self._validate_integer(value, rule)
        elif validation_type == ValidationType.FLOAT:
            return self._validate_float(value, rule)
        elif validation_type == ValidationType.BOOLEAN:
            return self._validate_boolean(value, rule)
        elif validation_type == ValidationType.EMAIL:
            return self._validate_email(value, rule)
        elif validation_type == ValidationType.UUID:
            return self._validate_uuid(value, rule)
        elif validation_type == ValidationType.DATE:
            return self._validate_date(value, rule)
        elif validation_type == ValidationType.LIST:
            return self._validate_list(value, rule)
        elif validation_type == ValidationType.DICT:
            return self._validate_dict(value, rule)
        elif validation_type == ValidationType.REGEX:
            return self._validate_regex(value, rule)
        elif validation_type == ValidationType.ENUM:
            return self._validate_enum(value, rule)
        elif validation_type == ValidationType.CUSTOM:
            return self._validate_custom(value, rule)
        else:
            return value

    def _validate_string(self, value: Any, rule: ValidationRule) -> str:
        """Validate string value."""
        if not isinstance(value, str):
            try:
                value = str(value)
            except Exception as e:
                raise ValidationError(
                    f"Cannot convert {type(value).__name__} to string", field=rule.field_name
                ) from e

        # Sanitize: strip whitespace
        value = value.strip()

        return value

    def _validate_integer(self, value: Any, rule: ValidationRule) -> int:
        """Validate integer value."""
        if isinstance(value, bool):  # bool is instance of int in Python
            raise ValidationError(
                "Boolean value not allowed for integer field", field=rule.field_name
            )

        if isinstance(value, int):
            return value

        if isinstance(value, str):
            try:
                return int(value)
            except ValueError as e:
                raise ValidationError(
                    f"Cannot convert '{value}' to integer", field=rule.field_name
                ) from e

        if isinstance(value, float):
            if value.is_integer():
                return int(value)
            else:
                raise ValidationError(
                    "Float with decimal part cannot be converted to integer", field=rule.field_name
                )

        raise ValidationError(
            f"Cannot convert {type(value).__name__} to integer", field=rule.field_name
        )

    def _validate_float(self, value: Any, rule: ValidationRule) -> float:
        """Validate float value."""
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return float(value)

        if isinstance(value, str):
            try:
                return float(value)
            except ValueError as e:
                raise ValidationError(
                    f"Cannot convert '{value}' to float", field=rule.field_name
                ) from e

        raise ValidationError(
            f"Cannot convert {type(value).__name__} to float", field=rule.field_name
        )

    def _validate_boolean(self, value: Any, rule: ValidationRule) -> bool:
        """Validate boolean value."""
        if isinstance(value, bool):
            return value

        if isinstance(value, str):
            lower_value = value.lower()
            if lower_value in ("true", "1", "yes", "on"):
                return True
            elif lower_value in ("false", "0", "no", "off"):
                return False

        if isinstance(value, int):
            return bool(value)

        raise ValidationError(f"Cannot convert '{value}' to boolean", field=rule.field_name)

    def _validate_email(self, value: Any, rule: ValidationRule) -> str:
        """Validate email address."""
        if not isinstance(value, str):
            raise ValidationError("Email must be a string", field=rule.field_name)

        email = value.strip().lower()

        if not self._email_pattern.match(email):
            raise ValidationError("Invalid email format", field=rule.field_name)

        return email

    def _validate_uuid(self, value: Any, rule: ValidationRule) -> str:
        """Validate UUID."""
        if isinstance(value, UUID):
            return str(value)

        if not isinstance(value, str):
            raise ValidationError("UUID must be a string", field=rule.field_name)

        uuid_str = value.strip()

        if not self._uuid_pattern.match(uuid_str):
            raise ValidationError("Invalid UUID format", field=rule.field_name)

        return uuid_str

    def _validate_date(self, value: Any, rule: ValidationRule) -> datetime:
        """Validate date value."""
        if isinstance(value, datetime):
            return value

        if isinstance(value, str):
            try:
                # Try common date formats
                for fmt in ["%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"]:
                    try:
                        return datetime.strptime(value, fmt)
                    except ValueError:
                        continue

                # Try ISO format
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
            except (ValueError, TypeError) as e:
                raise ValidationError(f"Cannot parse date '{value}'", field=rule.field_name) from e

        raise ValidationError(
            f"Cannot convert {type(value).__name__} to date", field=rule.field_name
        )

    def _validate_list(self, value: Any, rule: ValidationRule) -> list[Any]:
        """Validate list value."""
        if not isinstance(value, list):
            raise ValidationError("Value must be a list", field=rule.field_name)

        return value

    def _validate_dict(self, value: Any, rule: ValidationRule) -> dict[str, Any]:
        """Validate dictionary value."""
        if not isinstance(value, dict):
            raise ValidationError("Value must be a dictionary", field=rule.field_name)

        return value

    def _validate_regex(self, value: Any, rule: ValidationRule) -> str:
        """Validate value against regex pattern."""
        if not isinstance(value, str):
            value = str(value)

        if rule.pattern is None:
            raise ValueError(f"Pattern required for regex validation of field '{rule.field_name}'")

        if not rule.pattern.match(value):
            raise ValidationError(
                "Value does not match required pattern",
                field=rule.field_name,
                user_message=rule.user_message or f"Invalid format for {rule.field_name}",
            )

        return value

    def _validate_enum(self, value: Any, rule: ValidationRule) -> Any:
        """Validate value against enum values."""
        if rule.enum_values is None:
            raise ValueError(
                f"Enum values required for enum validation of field '{rule.field_name}'"
            )

        if value not in rule.enum_values:
            raise ValidationError(
                f"Value must be one of: {', '.join(map(str, rule.enum_values))}",
                field=rule.field_name,
            )

        return value

    def _validate_custom(self, value: Any, rule: ValidationRule) -> Any:
        """Validate using custom validator function."""
        if rule.custom_validator is None:
            raise ValueError(
                f"Custom validator required for custom validation of field '{rule.field_name}'"
            )

        try:
            if not rule.custom_validator(value):
                raise ValidationError(
                    rule.error_message or "Custom validation failed",
                    field=rule.field_name,
                    user_message=rule.user_message,
                )
        except ValidationError:
            raise
        except Exception as e:
            raise ValidationError(f"Custom validator error: {str(e)}", field=rule.field_name) from e

        return value

    def _validate_constraints(
        self, field_name: str, value: Any, rule: ValidationRule, result: ValidationResult
    ):
        """Validate value constraints (range, length, etc.)."""

        # Range validation
        if rule.min_value is not None or rule.max_value is not None:
            if not isinstance(value, (int, float)):
                result.add_error(
                    field_name, "Range constraints only apply to numeric values", value
                )
                return

            if rule.min_value is not None and value < rule.min_value:
                result.add_error(
                    field_name, f"Value must be at least {rule.min_value}", value, rule.user_message
                )
                return

            if rule.max_value is not None and value > rule.max_value:
                result.add_error(
                    field_name, f"Value must be at most {rule.max_value}", value, rule.user_message
                )
                return

        # Length validation
        if rule.min_length is not None or rule.max_length is not None:
            if not hasattr(value, "__len__"):
                result.add_error(
                    field_name, "Length constraints only apply to values with length", value
                )
                return

            length = len(value)

            if rule.min_length is not None and length < rule.min_length:
                result.add_error(
                    field_name,
                    f"Length must be at least {rule.min_length}",
                    value,
                    rule.user_message,
                )
                return

            if rule.max_length is not None and length > rule.max_length:
                result.add_error(
                    field_name,
                    f"Length must be at most {rule.max_length}",
                    value,
                    rule.user_message,
                )
                return


# Global validator instance
_global_validator = DataValidator()


def get_validator() -> DataValidator:
    """Get the global data validator instance."""
    return _global_validator


def validate_data(
    data: dict[str, Any],
    schema_name: str | None = None,
    schema: ValidationSchema | None = None,
) -> ValidationResult:
    """Convenience function to validate data using global validator."""
    return _global_validator.validate(data, schema_name, schema)


# Common validation schemas
def create_workflow_request_schema() -> ValidationSchema:
    """Create validation schema for workflow requests."""
    return ValidationSchema(
        name="workflow_request",
        rules=[
            ValidationRule(
                field_name="workflow_type",
                validation_type=ValidationType.ENUM,
                enum_values=["sequential_analysis", "batch_processing", "conversation"],
                required=True,
                user_message="Please select a valid workflow type",
            ),
            ValidationRule(
                field_name="user_id",
                validation_type=ValidationType.STRING,
                required=True,
                min_length=1,
                max_length=255,
            ),
            ValidationRule(
                field_name="team_id",
                validation_type=ValidationType.STRING,
                required=True,
                min_length=1,
                max_length=255,
            ),
            ValidationRule(
                field_name="correlation_id", validation_type=ValidationType.UUID, required=False
            ),
            ValidationRule(
                field_name="input_data", validation_type=ValidationType.DICT, required=True
            ),
            ValidationRule(
                field_name="priority",
                validation_type=ValidationType.INTEGER,
                min_value=1,
                max_value=10,
                required=False,
            ),
        ],
        description="Validation schema for workflow execution requests",
    )


def create_user_activity_schema() -> ValidationSchema:
    """Create validation schema for user activity data."""
    return ValidationSchema(
        name="user_activity",
        rules=[
            ValidationRule(
                field_name="activity_text",
                validation_type=ValidationType.STRING,
                required=True,
                min_length=10,
                max_length=2000,
                user_message="Please provide a detailed description of your activity (10-2000 characters)",
            ),
            ValidationRule(
                field_name="context", validation_type=ValidationType.DICT, required=False
            ),
            ValidationRule(
                field_name="timestamp", validation_type=ValidationType.DATE, required=False
            ),
            ValidationRule(
                field_name="categories", validation_type=ValidationType.LIST, required=False
            ),
        ],
        description="Validation schema for user activity submissions",
    )


# Register common schemas
def initialize_common_schemas():
    """Initialize commonly used validation schemas."""
    validator = get_validator()
    validator.register_schema(create_workflow_request_schema())
    validator.register_schema(create_user_activity_schema())

    logger.info("Common validation schemas initialized")


# NOTE: Auto-initialization disabled to prevent import side effects
# Uncomment the line below if you need schemas initialized automatically:
# initialize_common_schemas()
