"""
Golden Datasets for LLM Testing

Minimal implementation to support the testing framework.
Classes defined here are placeholders for full golden dataset functionality.
"""

from dataclasses import dataclass
from typing import Any


@dataclass
class GoldenDatasetManager:
    """Manager for golden datasets used in LLM testing."""

    def __init__(self) -> None:
        self.datasets: dict[str, Any] = {}

    def load_dataset(self, name: str) -> dict[str, Any] | None:
        """Load a golden dataset by name."""
        return self.datasets.get(name)

    def get_available_datasets(self) -> list[str]:
        """Get list of available dataset names."""
        return list(self.datasets.keys())


@dataclass
class ResponseValidator:
    """Validator for LLM responses against golden datasets."""

    def __init__(self) -> None:
        self.validation_rules: dict[str, Any] = {}

    def validate_response(self, response: str, expected: str) -> dict[str, Any]:
        """Validate response against expected output."""
        return {
            "valid": response == expected,
            "similarity_score": 1.0 if response == expected else 0.0,
            "errors": [] if response == expected else ["Response mismatch"],
        }


# Global instances
_golden_dataset_manager: GoldenDatasetManager | None = None
_response_validator: ResponseValidator | None = None


def get_golden_dataset_manager() -> GoldenDatasetManager:
    """Get or create global golden dataset manager instance."""
    global _golden_dataset_manager
    if _golden_dataset_manager is None:
        _golden_dataset_manager = GoldenDatasetManager()
    return _golden_dataset_manager


def get_response_validator() -> ResponseValidator:
    """Get or create global response validator instance."""
    global _response_validator
    if _response_validator is None:
        _response_validator = ResponseValidator()
    return _response_validator
