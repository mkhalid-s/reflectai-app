"""
Prompt Management System for ReflectAI

Implements  Simple prompt management for agents and tools with:
- File-based prompt templates with Jinja2
- Environment-specific variations
- Dynamic variable injection
- Prompt validation and testing utilities

Provides centralized prompt management for consistency and easy updates.
"""

from .prompt_manager import PromptManager, PromptTemplate, PromptValidationError, get_prompt_manager
from .prompt_tester import GoldenDataset, PromptTester
from .template_loader import TemplateLoader

__all__ = [
    "PromptManager",
    "PromptTemplate",
    "PromptValidationError",
    "get_prompt_manager",
    "TemplateLoader",
    "PromptTester",
    "GoldenDataset",
]
