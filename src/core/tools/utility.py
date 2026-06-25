"""
Utility Tools for ReflectAI Agents

Provides general-purpose utility tools for common operations.
"""

import hashlib
import json
from datetime import UTC, datetime
from typing import Any

from src.core.tools.base_tool import Tool
from src.shared import get_logger

logger = get_logger(__name__)


class TextProcessorTool(Tool):
    """Tool for text processing operations."""

    name = "text_processor"
    description = "Process and manipulate text data"
    category = "utility"

    async def execute(
        self, operation: str, text: str, options: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Process text with specified operation."""
        try:
            logger.info(
                "Text processor tool called",
                extra={"operation": operation, "text_length": len(text)},
            )

            result_text = text
            if operation == "uppercase":
                result_text = text.upper()
            elif operation == "lowercase":
                result_text = text.lower()
            elif operation == "trim":
                result_text = text.strip()
            elif operation == "word_count":
                return {
                    "success": True,
                    "operation": operation,
                    "result": len(text.split()),
                    "original_length": len(text),
                }

            return {
                "success": True,
                "operation": operation,
                "result": result_text,
                "original_length": len(text),
                "processed_length": len(result_text),
            }

        except Exception as e:
            logger.error(f"Text processing failed: {e}")
            return {"success": False, "error": str(e), "message": "Text processing failed"}


class DataValidatorTool(Tool):
    """Tool for data validation operations."""

    name = "data_validator"
    description = "Validate data against schemas and rules"
    category = "utility"

    async def execute(
        self,
        data: dict[str, Any] | list[Any],
        validation_type: str,
        rules: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Validate data against specified rules."""
        try:
            logger.info(
                "Data validator tool called",
                extra={"validation_type": validation_type, "data_type": type(data).__name__},
            )

            # Basic validation implementation
            errors = []
            is_valid = True

            if validation_type == "required_fields" and isinstance(data, dict):
                required = rules.get("required", []) if rules else []
                for field in required:
                    if field not in data or data[field] is None:
                        errors.append(f"Missing required field: {field}")
                        is_valid = False

            return {
                "success": True,
                "is_valid": is_valid,
                "validation_type": validation_type,
                "errors": errors,
                "validated_at": datetime.now(UTC).isoformat(),
            }

        except Exception as e:
            logger.error(f"Data validation failed: {e}")
            return {"success": False, "error": str(e), "message": "Data validation failed"}


class HashGeneratorTool(Tool):
    """Tool for generating hashes and checksums."""

    name = "hash_generator"
    description = "Generate hashes and checksums for data"
    category = "utility"

    async def execute(self, data: str, algorithm: str = "sha256") -> dict[str, Any]:
        """Generate hash for provided data."""
        try:
            logger.info(
                "Hash generator tool called",
                extra={"algorithm": algorithm, "data_length": len(data)},
            )

            warning_message = None
            if algorithm == "md5":
                # MD5 is cryptographically broken - only use for non-security purposes
                hash_value = hashlib.md5(data.encode(), usedforsecurity=False).hexdigest()
                warning_message = "MD5 is deprecated for security. Use SHA256 for new applications."
            elif algorithm == "sha1":
                # SHA1 is cryptographically weak - only use for non-security purposes
                hash_value = hashlib.sha1(data.encode(), usedforsecurity=False).hexdigest()
                warning_message = "SHA1 is deprecated for security. Use SHA256 for new applications."
            elif algorithm == "sha256":
                hash_value = hashlib.sha256(data.encode()).hexdigest()
            else:
                raise ValueError(f"Unsupported algorithm: {algorithm}")

            result = {
                "success": True,
                "algorithm": algorithm,
                "hash": hash_value,
                "data_length": len(data),
                "generated_at": datetime.now(UTC).isoformat(),
            }

            if warning_message:
                result["warning"] = warning_message
                logger.warning(
                    f"Weak hash algorithm used: {algorithm}",
                    extra={"algorithm": algorithm}
                )

            return result

        except Exception as e:
            logger.error(f"Hash generation failed: {e}")
            return {"success": False, "error": str(e), "message": "Hash generation failed"}


class JsonProcessorTool(Tool):
    """Tool for JSON processing operations."""

    name = "json_processor"
    description = "Process and manipulate JSON data"
    category = "utility"

    async def execute(
        self,
        operation: str,
        data: str | dict[str, Any] | list[Any],
        options: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Process JSON data with specified operation."""
        try:
            logger.info("JSON processor tool called", extra={"operation": operation})

            if operation == "parse":
                if isinstance(data, str):
                    parsed_data = json.loads(data)
                    return {
                        "success": True,
                        "operation": operation,
                        "result": parsed_data,
                        "type": type(parsed_data).__name__,
                    }
                else:
                    return {
                        "success": True,
                        "operation": operation,
                        "result": data,
                        "message": "Data already parsed",
                    }

            elif operation == "stringify":
                if isinstance(data, str):
                    return {
                        "success": True,
                        "operation": operation,
                        "result": data,
                        "message": "Data already string",
                    }
                else:
                    stringified = json.dumps(data, default=str, indent=2)
                    return {
                        "success": True,
                        "operation": operation,
                        "result": stringified,
                        "length": len(stringified),
                    }

            else:
                raise ValueError(f"Unsupported operation: {operation}")

        except Exception as e:
            logger.error(f"JSON processing failed: {e}")
            return {"success": False, "error": str(e), "message": "JSON processing failed"}


# Export available tools
__all__ = ["TextProcessorTool", "DataValidatorTool", "HashGeneratorTool", "JsonProcessorTool"]
