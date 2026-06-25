"""
Tests for ReflectAI Validation Framework

Basic tests to verify validation components work correctly.
Note: This module is not actively integrated but kept for future use.
"""

from uuid import uuid4

from src.shared.validation import (
    DataValidator,
    ValidationResult,
    ValidationRule,
    ValidationSchema,
    ValidationType,
    get_validator,
    validate_data,
)


class TestValidationRule:
    """Test ValidationRule dataclass."""

    def test_basic_rule_creation(self):
        """Test creating a basic validation rule."""
        rule = ValidationRule(
            field_name="email",
            validation_type=ValidationType.EMAIL,
            required=True,
        )

        assert rule.field_name == "email"
        assert rule.validation_type == ValidationType.EMAIL
        assert rule.required is True


class TestValidationSchema:
    """Test ValidationSchema dataclass."""

    def test_schema_creation(self):
        """Test creating a validation schema."""
        rules = [
            ValidationRule(field_name="name", validation_type=ValidationType.STRING, required=True),
            ValidationRule(
                field_name="age", validation_type=ValidationType.INTEGER, required=False
            ),
        ]

        schema = ValidationSchema(name="user_schema", rules=rules)

        assert schema.name == "user_schema"
        assert len(schema.rules) == 2
        assert schema.strict is False


class TestDataValidator:
    """Test DataValidator class."""

    def test_validator_initialization(self):
        """Test validator initializes correctly."""
        validator = DataValidator()

        assert isinstance(validator.schemas, dict)
        assert len(validator.schemas) == 0

    def test_register_schema(self):
        """Test registering a validation schema."""
        validator = DataValidator()
        schema = ValidationSchema(
            name="test_schema",
            rules=[ValidationRule(field_name="test", validation_type=ValidationType.STRING)],
        )

        validator.register_schema(schema)

        assert "test_schema" in validator.schemas
        assert validator.schemas["test_schema"] == schema


class TestStringValidation:
    """Test string validation."""

    def test_validate_string_success(self):
        """Test successful string validation."""
        validator = DataValidator()
        schema = ValidationSchema(
            name="test",
            rules=[ValidationRule(field_name="name", validation_type=ValidationType.STRING)],
        )

        result = validator.validate({"name": "John Doe"}, schema=schema)

        assert result.valid is True
        assert result.sanitized_data["name"] == "John Doe"

    def test_validate_string_strips_whitespace(self):
        """Test string validation strips whitespace."""
        validator = DataValidator()
        schema = ValidationSchema(
            name="test",
            rules=[ValidationRule(field_name="name", validation_type=ValidationType.STRING)],
        )

        result = validator.validate({"name": "  John Doe  "}, schema=schema)

        assert result.valid is True
        assert result.sanitized_data["name"] == "John Doe"

    def test_validate_string_length_constraints(self):
        """Test string length constraints."""
        validator = DataValidator()
        schema = ValidationSchema(
            name="test",
            rules=[
                ValidationRule(
                    field_name="name",
                    validation_type=ValidationType.STRING,
                    min_length=3,
                    max_length=10,
                )
            ],
        )

        # Too short
        result = validator.validate({"name": "AB"}, schema=schema)
        assert result.valid is False

        # Just right
        result = validator.validate({"name": "John"}, schema=schema)
        assert result.valid is True

        # Too long
        result = validator.validate({"name": "A" * 11}, schema=schema)
        assert result.valid is False


class TestIntegerValidation:
    """Test integer validation."""

    def test_validate_integer_success(self):
        """Test successful integer validation."""
        validator = DataValidator()
        schema = ValidationSchema(
            name="test",
            rules=[ValidationRule(field_name="age", validation_type=ValidationType.INTEGER)],
        )

        result = validator.validate({"age": 25}, schema=schema)

        assert result.valid is True
        assert result.sanitized_data["age"] == 25

    def test_validate_integer_from_string(self):
        """Test integer validation from string."""
        validator = DataValidator()
        schema = ValidationSchema(
            name="test",
            rules=[ValidationRule(field_name="age", validation_type=ValidationType.INTEGER)],
        )

        result = validator.validate({"age": "25"}, schema=schema)

        assert result.valid is True
        assert result.sanitized_data["age"] == 25

    def test_validate_integer_rejects_boolean(self):
        """Test integer validation rejects boolean."""
        validator = DataValidator()
        schema = ValidationSchema(
            name="test",
            rules=[ValidationRule(field_name="age", validation_type=ValidationType.INTEGER)],
        )

        result = validator.validate({"age": True}, schema=schema)

        assert result.valid is False

    def test_validate_integer_range(self):
        """Test integer range constraints."""
        validator = DataValidator()
        schema = ValidationSchema(
            name="test",
            rules=[
                ValidationRule(
                    field_name="age",
                    validation_type=ValidationType.INTEGER,
                    min_value=0,
                    max_value=120,
                )
            ],
        )

        # Too low
        result = validator.validate({"age": -1}, schema=schema)
        assert result.valid is False

        # Just right
        result = validator.validate({"age": 25}, schema=schema)
        assert result.valid is True

        # Too high
        result = validator.validate({"age": 121}, schema=schema)
        assert result.valid is False


class TestEmailValidation:
    """Test email validation."""

    def test_validate_email_success(self):
        """Test successful email validation."""
        validator = DataValidator()
        schema = ValidationSchema(
            name="test",
            rules=[ValidationRule(field_name="email", validation_type=ValidationType.EMAIL)],
        )

        result = validator.validate({"email": "test@example.com"}, schema=schema)

        assert result.valid is True
        assert result.sanitized_data["email"] == "test@example.com"

    def test_validate_email_normalizes(self):
        """Test email validation normalizes to lowercase."""
        validator = DataValidator()
        schema = ValidationSchema(
            name="test",
            rules=[ValidationRule(field_name="email", validation_type=ValidationType.EMAIL)],
        )

        result = validator.validate({"email": "TEST@EXAMPLE.COM"}, schema=schema)

        assert result.valid is True
        assert result.sanitized_data["email"] == "test@example.com"

    def test_validate_email_invalid(self):
        """Test email validation rejects invalid emails."""
        validator = DataValidator()
        schema = ValidationSchema(
            name="test",
            rules=[ValidationRule(field_name="email", validation_type=ValidationType.EMAIL)],
        )

        invalid_emails = [
            "notanemail",
            "@example.com",
            "test@",
            "test@@example.com",
        ]

        for email in invalid_emails:
            result = validator.validate({"email": email}, schema=schema)
            assert result.valid is False, f"Email '{email}' should be invalid"


class TestUUIDValidation:
    """Test UUID validation."""

    def test_validate_uuid_success(self):
        """Test successful UUID validation."""
        validator = DataValidator()
        schema = ValidationSchema(
            name="test",
            rules=[ValidationRule(field_name="id", validation_type=ValidationType.UUID)],
        )

        test_uuid = str(uuid4())
        result = validator.validate({"id": test_uuid}, schema=schema)

        assert result.valid is True
        assert result.sanitized_data["id"] == test_uuid

    def test_validate_uuid_from_uuid_object(self):
        """Test UUID validation from UUID object."""
        validator = DataValidator()
        schema = ValidationSchema(
            name="test",
            rules=[ValidationRule(field_name="id", validation_type=ValidationType.UUID)],
        )

        test_uuid = uuid4()
        result = validator.validate({"id": test_uuid}, schema=schema)

        assert result.valid is True
        assert result.sanitized_data["id"] == str(test_uuid)

    def test_validate_uuid_invalid(self):
        """Test UUID validation rejects invalid UUIDs."""
        validator = DataValidator()
        schema = ValidationSchema(
            name="test",
            rules=[ValidationRule(field_name="id", validation_type=ValidationType.UUID)],
        )

        result = validator.validate({"id": "not-a-uuid"}, schema=schema)

        assert result.valid is False


class TestEnumValidation:
    """Test enum validation."""

    def test_validate_enum_success(self):
        """Test successful enum validation."""
        validator = DataValidator()
        schema = ValidationSchema(
            name="test",
            rules=[
                ValidationRule(
                    field_name="status",
                    validation_type=ValidationType.ENUM,
                    enum_values=["pending", "active", "completed"],
                )
            ],
        )

        result = validator.validate({"status": "active"}, schema=schema)

        assert result.valid is True
        assert result.sanitized_data["status"] == "active"

    def test_validate_enum_invalid(self):
        """Test enum validation rejects invalid values."""
        validator = DataValidator()
        schema = ValidationSchema(
            name="test",
            rules=[
                ValidationRule(
                    field_name="status",
                    validation_type=ValidationType.ENUM,
                    enum_values=["pending", "active", "completed"],
                )
            ],
        )

        result = validator.validate({"status": "invalid"}, schema=schema)

        assert result.valid is False


class TestRequiredFields:
    """Test required field validation."""

    def test_required_field_present(self):
        """Test validation passes when required field present."""
        validator = DataValidator()
        schema = ValidationSchema(
            name="test",
            rules=[
                ValidationRule(
                    field_name="name", validation_type=ValidationType.STRING, required=True
                )
            ],
        )

        result = validator.validate({"name": "John"}, schema=schema)

        assert result.valid is True

    def test_required_field_missing(self):
        """Test validation fails when required field missing."""
        validator = DataValidator()
        schema = ValidationSchema(
            name="test",
            rules=[
                ValidationRule(
                    field_name="name", validation_type=ValidationType.STRING, required=True
                )
            ],
        )

        result = validator.validate({}, schema=schema)

        assert result.valid is False
        assert len(result.errors) > 0


class TestGlobalValidator:
    """Test global validator instance and utility functions."""

    def test_get_validator(self):
        """Test getting global validator instance."""
        validator = get_validator()

        assert isinstance(validator, DataValidator)

    def test_validate_data_function(self):
        """Test validate_data utility function."""
        schema = ValidationSchema(
            name="test",
            rules=[ValidationRule(field_name="name", validation_type=ValidationType.STRING)],
        )

        result = validate_data({"name": "Test"}, schema=schema)

        assert result.valid is True


class TestValidationResult:
    """Test ValidationResult class."""

    def test_validation_result_initialization(self):
        """Test ValidationResult initializes correctly."""
        result = ValidationResult(valid=True)

        assert result.valid is True
        assert isinstance(result.errors, list)
        assert isinstance(result.warnings, list)
        assert len(result.errors) == 0

    def test_add_error(self):
        """Test adding error to validation result."""
        result = ValidationResult(valid=True)

        result.add_error("field", "error message", "invalid_value")

        assert result.valid is False
        assert len(result.errors) == 1

    def test_add_warning(self):
        """Test adding warning to validation result."""
        result = ValidationResult(valid=True)

        result.add_warning("warning message")

        assert result.valid is True  # Warnings don't invalidate
        assert len(result.warnings) == 1
