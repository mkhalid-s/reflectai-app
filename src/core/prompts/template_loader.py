"""
Template Loader for Prompt Management

Handles loading of prompt templates from various sources with validation
and environment-specific configurations.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.shared import get_logger

from .prompt_manager import PromptTemplate, PromptType

logger = get_logger(__name__)


@dataclass
class LoaderConfig:
    """Configuration for template loading."""

    base_path: Path
    environments: list[str] = None
    file_extensions: list[str] = None
    encoding: str = "utf-8"
    validate_on_load: bool = True

    def __post_init__(self):
        if self.environments is None:
            self.environments = ["development", "staging", "production"]
        if self.file_extensions is None:
            self.file_extensions = [".txt", ".md", ".j2"]


class TemplateLoader:
    """
    Advanced template loading with environment support and validation.

    Features:
    - Environment-specific template loading
    - Template inheritance and overrides
    - Batch loading and validation
    - Template hot-reloading support
    """

    def __init__(self, config: LoaderConfig):
        self.config = config
        self.loaded_templates: dict[str, PromptTemplate] = {}

        logger.info(
            "Template loader initialized",
            extra={
                "base_path": str(config.base_path),
                "environments": config.environments,
                "extensions": config.file_extensions,
            },
        )

    def load_all_templates(self) -> dict[str, PromptTemplate]:
        """Load all templates from the configured directory structure."""

        templates = {}

        if not self.config.base_path.exists():
            logger.warning(f"Template directory does not exist: {self.config.base_path}")
            return templates

        # Load base templates first
        base_templates = self._load_templates_from_directory(self.config.base_path)
        templates.update(base_templates)

        # Load environment-specific overrides
        for env in self.config.environments:
            env_dir = self.config.base_path / "environments" / env
            if env_dir.exists():
                env_templates = self._load_templates_from_directory(env_dir, env_suffix=env)
                templates.update(env_templates)

        self.loaded_templates = templates

        logger.info(f"Loaded {len(templates)} templates", extra={"template_count": len(templates)})

        return templates

    def _load_templates_from_directory(
        self, directory: Path, env_suffix: str | None = None
    ) -> dict[str, PromptTemplate]:
        """Load templates from a specific directory."""

        templates = {}

        for ext in self.config.file_extensions:
            pattern = f"**/*{ext}"

            for template_file in directory.rglob(pattern):
                try:
                    template = self._load_single_template(template_file, env_suffix)
                    if template:
                        templates[template.name] = template
                except Exception as e:
                    logger.error(
                        f"Failed to load template from {template_file}: {e}", exc_info=True
                    )

        return templates

    def _load_single_template(
        self, template_file: Path, env_suffix: str | None = None
    ) -> PromptTemplate | None:
        """Load a single template file."""

        # Read file content
        try:
            content = template_file.read_text(encoding=self.config.encoding)
        except Exception as e:
            logger.error(f"Failed to read template file {template_file}: {e}")
            return None

        # Determine template name and type
        relative_path = template_file.relative_to(self.config.base_path)
        template_name = self._generate_template_name(relative_path, env_suffix)
        prompt_type = self._determine_prompt_type(relative_path)

        # Extract metadata and content
        metadata, clean_content = self._parse_template_content(content)

        # Extract variables
        variables = self._extract_template_variables(clean_content)

        # Create template
        template = PromptTemplate(
            name=template_name,
            content=clean_content,
            prompt_type=prompt_type,
            variables=variables,
            description=metadata.get("description", ""),
            version=metadata.get("version", "1.0"),
            tags=metadata.get("tags", []),
        )

        # Validate if configured
        if self.config.validate_on_load:
            validation_errors = self._validate_template(template)
            if validation_errors:
                logger.warning(
                    f"Template validation warnings for {template_name}: {validation_errors}"
                )

        return template

    def _generate_template_name(self, relative_path: Path, env_suffix: str | None = None) -> str:
        """Generate template name from file path."""

        # Use path structure to create hierarchical name
        parts = list(relative_path.parts[:-1])  # Exclude filename
        filename = relative_path.stem  # Filename without extension

        if parts:
            template_name = "/".join(parts + [filename])
        else:
            template_name = filename

        # Add environment suffix if provided
        if env_suffix:
            template_name = f"{template_name}.{env_suffix}"

        return template_name

    def _determine_prompt_type(self, relative_path: Path) -> PromptType:
        """Determine prompt type from file path."""

        path_parts = relative_path.parts

        if len(path_parts) > 0:
            first_dir = path_parts[0].lower()

            if first_dir == "agents":
                return PromptType.AGENT
            elif first_dir == "tools":
                return PromptType.TOOL
            elif first_dir == "system":
                return PromptType.SYSTEM
            elif first_dir == "validation":
                return PromptType.VALIDATION

        return PromptType.SYSTEM  # Default

    def _parse_template_content(self, content: str) -> tuple[dict[str, Any], str]:
        """Parse template content to extract metadata and clean content."""

        lines = content.split("\n")

        # Check for YAML frontmatter
        if lines and lines[0].strip() == "---":
            metadata_lines = []
            content_start = 0

            # Find end of frontmatter
            for i, line in enumerate(lines[1:], 1):
                if line.strip() == "---":
                    content_start = i + 1
                    break
                metadata_lines.append(line)
            else:
                # No closing ---, treat as regular content
                return {}, content

            # Parse metadata (simplified YAML parsing)
            metadata = self._parse_simple_yaml(metadata_lines)
            clean_content = "\n".join(lines[content_start:])

            return metadata, clean_content

        return {}, content

    def _parse_simple_yaml(self, yaml_lines: list[str]) -> dict[str, Any]:
        """Simple YAML parsing for metadata."""

        metadata = {}

        for line in yaml_lines:
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            if ":" in line:
                key, value = line.split(":", 1)
                key = key.strip()
                value = value.strip()

                # Remove quotes
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                elif value.startswith("'") and value.endswith("'"):
                    value = value[1:-1]

                # Handle lists
                if value.startswith("[") and value.endswith("]"):
                    # Simple list parsing
                    items = value[1:-1].split(",")
                    value = [item.strip().strip("\"'") for item in items if item.strip()]

                # Handle numbers
                elif value.isdigit():
                    value = int(value)
                elif value.replace(".", "").isdigit():
                    value = float(value)

                # Handle booleans
                elif value.lower() in ("true", "false"):
                    value = value.lower() == "true"

                metadata[key] = value

        return metadata

    def _extract_template_variables(self, content: str) -> list[str]:
        """Extract variable names from template content."""

        import re

        variables = set()

        # Jinja2 variables: {{ variable }}
        jinja_vars = re.findall(r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}", content)
        variables.update(jinja_vars)

        # Jinja2 control structures: {% if variable %}
        control_vars = re.findall(r"\{\%\s*(?:if|for|set)\s+([a-zA-Z_][a-zA-Z0-9_]*)", content)
        variables.update(control_vars)

        # Simple string format variables: {variable}
        simple_vars = re.findall(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}", content)
        variables.update(simple_vars)

        return sorted(variables)

    def _validate_template(self, template: PromptTemplate) -> list[str]:
        """Validate template content and structure."""

        issues = []

        # Check for empty content
        if not template.content.strip():
            issues.append("Template content is empty")

        # Check for undefined variables in Jinja2 context
        # This is a simplified check - full validation would require Jinja2 compilation

        # Check for balanced brackets
        open_brackets = template.content.count("{")
        close_brackets = template.content.count("}")
        if open_brackets != close_brackets:
            issues.append("Unbalanced brackets in template")

        # Check for required fields based on prompt type
        if template.prompt_type == PromptType.AGENT:
            if "task" not in template.content.lower():
                issues.append("Agent prompt should reference task or instructions")

        return issues

    def load_template_by_name(self, name: str) -> PromptTemplate | None:
        """Load a specific template by name."""

        if name in self.loaded_templates:
            return self.loaded_templates[name]

        # Try to find and load the template
        for ext in self.config.file_extensions:
            template_file = self.config.base_path / f"{name}{ext}"
            if template_file.exists():
                return self._load_single_template(template_file)

        return None

    def get_template_dependencies(self, template_name: str) -> list[str]:
        """Get list of templates that this template depends on (includes/extends)."""

        template = self.loaded_templates.get(template_name)
        if not template:
            return []

        dependencies = []

        # Look for Jinja2 includes/extends
        import re

        # {% include "template_name" %}
        includes = re.findall(r'\{\%\s*include\s+"([^"]+)"\s*\%\}', template.content)
        dependencies.extend(includes)

        # {% extends "template_name" %}
        extends = re.findall(r'\{\%\s*extends\s+"([^"]+)"\s*\%\}', template.content)
        dependencies.extend(extends)

        return dependencies

    def validate_all_templates(self) -> dict[str, list[str]]:
        """Validate all loaded templates and return issues."""

        validation_results = {}

        for name, template in self.loaded_templates.items():
            issues = self._validate_template(template)
            if issues:
                validation_results[name] = issues

        return validation_results

    def get_loader_stats(self) -> dict[str, Any]:
        """Get template loader statistics."""

        return {
            "total_templates": len(self.loaded_templates),
            "templates_by_type": {
                prompt_type.value: len(
                    [t for t in self.loaded_templates.values() if t.prompt_type == prompt_type]
                )
                for prompt_type in PromptType
            },
            "environments_configured": self.config.environments,
            "file_extensions": self.config.file_extensions,
            "base_path": str(self.config.base_path),
        }
