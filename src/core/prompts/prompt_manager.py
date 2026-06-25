"""
Prompt Manager Implementation

Core prompt management system with template loading, caching, and validation.
Supports environment-specific variations and dynamic variable injection.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any

try:
    from jinja2 import Environment, FileSystemLoader, Template, TemplateError, select_autoescape

    JINJA2_AVAILABLE = True
except ImportError:
    JINJA2_AVAILABLE = False

from src.infrastructure.config import get_config_manager
from src.shared import ErrorCategory, ErrorSeverity, ReflectAIError, get_logger

logger = get_logger(__name__)


class PromptType(str, Enum):
    """Types of prompts in the system."""

    AGENT = "agent"  # Agent system prompts
    TOOL = "tool"  # Tool-specific prompts
    SYSTEM = "system"  # System messages (greeting, help, error)
    VALIDATION = "validation"  # Validation and formatting prompts


@dataclass
class PromptTemplate:
    """Prompt template with metadata."""

    name: str
    content: str
    prompt_type: PromptType
    variables: list[str]
    description: str = ""
    created_at: datetime = None
    last_modified: datetime = None
    version: str = "1.0"
    tags: list[str] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now(UTC)
        if self.last_modified is None:
            self.last_modified = datetime.now(UTC)
        if self.tags is None:
            self.tags = []


class PromptValidationError(ReflectAIError):
    """Raised when prompt validation fails."""

    def __init__(self, message: str, prompt_name: str = "", validation_errors: list[str] = None):
        super().__init__(
            message=message,
            error_code="PROMPT_VALIDATION_ERROR",
            category=ErrorCategory.VALIDATION_ERROR,
            severity=ErrorSeverity.ERROR,
            context={"prompt_name": prompt_name, "validation_errors": validation_errors or []},
        )


class PromptManager:
    """
    Centralized prompt management system.

    Features:
    - File-based prompt storage with Jinja2 templates
    - Environment-specific prompt variations
    - In-memory caching for performance
    - Prompt validation and testing support
    - Usage tracking and analytics
    """

    def __init__(self, prompts_dir: str | None = None):
        self.config = get_config_manager().get_config()

        # Set prompts directory
        if prompts_dir:
            self.prompts_dir = Path(prompts_dir)
        else:
            # Default to src/prompts directory
            self.prompts_dir = Path(__file__).parent.parent.parent / "prompts"

        # Ensure directory exists
        self.prompts_dir.mkdir(parents=True, exist_ok=True)

        # Jinja2 environment
        self.jinja_env = None
        if JINJA2_AVAILABLE:
            self.jinja_env = Environment(
                loader=FileSystemLoader(str(self.prompts_dir)),
                autoescape=select_autoescape(
                    enabled_extensions=("html", "xml", "jinja2"), default=True
                ),
                trim_blocks=True,
                lstrip_blocks=True,
                keep_trailing_newline=True,
            )

        # In-memory cache
        self._template_cache: dict[str, PromptTemplate] = {}
        self._compiled_templates: dict[str, Template] = {}

        # Usage tracking
        self._usage_stats: dict[str, int] = {}
        self._load_stats = {"loads": 0, "cache_hits": 0, "cache_misses": 0}

        # Environment
        self.environment = (
            self.config.app.environment
            if hasattr(self.config.app, "environment")
            else "development"
        )

        logger.info(
            "Prompt manager initialized",
            extra={
                "prompts_dir": str(self.prompts_dir),
                "environment": self.environment,
                "jinja2_available": JINJA2_AVAILABLE,
            },
        )

        # Load all prompts at startup
        self.reload_prompts()

    def get_prompt(
        self,
        name: str,
        variables: dict[str, Any] | None = None,
        environment: str | None = None,
    ) -> str:
        """
        Get rendered prompt with variable substitution.

        Args:
            name: Prompt name (e.g., "analysis_agent", "greeting")
            variables: Variables to substitute in template
            environment: Environment override (dev/staging/prod)

        Returns:
            Rendered prompt content

        Raises:
            PromptValidationError: If prompt not found or rendering fails
        """

        # Track usage
        self._usage_stats[name] = self._usage_stats.get(name, 0) + 1

        # Try environment-specific version first
        env_name = environment or self.environment
        env_specific_name = f"{name}.{env_name}"

        template = None
        if env_specific_name in self._template_cache:
            template = self._template_cache[env_specific_name]
            template_name = env_specific_name
        elif name in self._template_cache:
            template = self._template_cache[name]
            template_name = name
        else:
            raise PromptValidationError(f"Prompt template '{name}' not found", prompt_name=name)

        # Render template with variables
        try:
            if JINJA2_AVAILABLE and template_name in self._compiled_templates:
                # Use Jinja2 for rendering
                jinja_template = self._compiled_templates[template_name]
                rendered = jinja_template.render(variables or {})
            else:
                # Simple string substitution fallback
                rendered = self._simple_render(template.content, variables or {})

            logger.debug(
                f"Rendered prompt '{name}'",
                extra={
                    "template_name": template_name,
                    "variables_count": len(variables) if variables else 0,
                },
            )

            return rendered

        except Exception as e:
            logger.error(
                f"Failed to render prompt '{name}': {e}",
                extra={"template_name": template_name, "error": str(e)},
                exc_info=True,
            )

            raise PromptValidationError(
                f"Failed to render prompt '{name}': {str(e)}",
                prompt_name=name,
                validation_errors=[str(e)],
            ) from e

    def _simple_render(self, content: str, variables: dict[str, Any]) -> str:
        """Simple variable substitution when Jinja2 is not available."""

        rendered = content

        for key, value in variables.items():
            placeholder = f"{{{{{key}}}}}"  # {{variable}} format
            rendered = rendered.replace(placeholder, str(value))

        return rendered

    def reload_prompts(self):
        """Reload all prompts from disk."""

        logger.info("Reloading prompts from disk")

        self._template_cache.clear()
        self._compiled_templates.clear()

        # Load prompts from directory structure
        self._load_prompts_from_directory()

        # Create default prompts if none exist
        if not self._template_cache:
            self._create_default_prompts()

        logger.info(
            f"Loaded {len(self._template_cache)} prompt templates",
            extra={"templates": list(self._template_cache.keys())},
        )

    def _load_prompts_from_directory(self):
        """Load prompts from the prompts directory structure."""

        if not self.prompts_dir.exists():
            logger.warning(f"Prompts directory does not exist: {self.prompts_dir}")
            return

        # Scan for prompt files
        for prompt_file in self.prompts_dir.rglob("*.txt"):
            try:
                self._load_prompt_file(prompt_file)
            except Exception as e:
                logger.error(f"Failed to load prompt file {prompt_file}: {e}", exc_info=True)

        # Also scan for .md files (markdown prompts)
        for prompt_file in self.prompts_dir.rglob("*.md"):
            try:
                self._load_prompt_file(prompt_file)
            except Exception as e:
                logger.error(f"Failed to load prompt file {prompt_file}: {e}", exc_info=True)

    def _load_prompt_file(self, prompt_file: Path):
        """Load individual prompt file."""

        # Determine prompt type from directory structure
        relative_path = prompt_file.relative_to(self.prompts_dir)
        path_parts = relative_path.parts

        if len(path_parts) >= 2:
            prompt_type_str = path_parts[0]  # agents, tools, system, etc.
            try:
                prompt_type = PromptType(prompt_type_str)
            except ValueError:
                prompt_type = PromptType.SYSTEM
        else:
            prompt_type = PromptType.SYSTEM

        # Generate prompt name from file path
        prompt_name = prompt_file.stem  # filename without extension

        # Read content
        content = prompt_file.read_text(encoding="utf-8")

        # Extract metadata from content if present (YAML frontmatter)
        metadata = self._extract_metadata(content)
        if metadata:
            content = self._remove_metadata(content)

        # Extract variables from content
        variables = self._extract_variables(content)

        # Create template
        template = PromptTemplate(
            name=prompt_name,
            content=content.strip(),
            prompt_type=prompt_type,
            variables=variables,
            description=metadata.get("description", ""),
            version=metadata.get("version", "1.0"),
            tags=metadata.get("tags", []),
        )

        # Store in cache
        self._template_cache[prompt_name] = template

        # Compile Jinja2 template if available
        if JINJA2_AVAILABLE:
            try:
                jinja_template = self.jinja_env.from_string(content)
                self._compiled_templates[prompt_name] = jinja_template
            except TemplateError as e:
                logger.warning(f"Failed to compile Jinja2 template for '{prompt_name}': {e}")

        logger.debug(f"Loaded prompt template: {prompt_name}")

    def _extract_metadata(self, content: str) -> dict[str, Any]:
        """Extract YAML frontmatter metadata from prompt content."""

        lines = content.split("\n")
        if not lines or not lines[0].strip() == "---":
            return {}

        # Find end of frontmatter
        end_line = -1
        for i, line in enumerate(lines[1:], 1):
            if line.strip() == "---":
                end_line = i
                break

        if end_line == -1:
            return {}

        # Extract YAML content (simplified parsing for production)
        yaml_content = "\n".join(lines[1:end_line])
        metadata = {}

        # Simple key-value parsing (replace with proper YAML parser in production+)
        for line in yaml_content.split("\n"):
            if ":" in line:
                key, value = line.split(":", 1)
                key = key.strip()
                value = value.strip().strip("\"'")

                # Handle lists (simplified)
                if value.startswith("[") and value.endswith("]"):
                    value = [item.strip().strip("\"'") for item in value[1:-1].split(",")]

                metadata[key] = value

        return metadata

    def _remove_metadata(self, content: str) -> str:
        """Remove YAML frontmatter from content."""

        lines = content.split("\n")
        if not lines or not lines[0].strip() == "---":
            return content

        # Find end of frontmatter
        for i, line in enumerate(lines[1:], 1):
            if line.strip() == "---":
                return "\n".join(lines[i + 1 :])

        return content

    def _extract_variables(self, content: str) -> list[str]:
        """Extract variable names from template content."""

        import re

        # Find Jinja2 variables {{ variable_name }}
        variables = set()

        # Pattern for {{ variable }}
        jinja_pattern = r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}"
        matches = re.findall(jinja_pattern, content)
        variables.update(matches)

        # Pattern for {% if variable %} etc.
        control_pattern = r"\{\%\s*(?:if|for|set)\s+([a-zA-Z_][a-zA-Z0-9_]*)"
        control_matches = re.findall(control_pattern, content)
        variables.update(control_matches)

        return sorted(variables)

    def _create_default_prompts(self):
        """Create default prompts if none exist."""

        logger.info("Creating default prompts")

        # Create directory structure
        (self.prompts_dir / "agents").mkdir(exist_ok=True)
        (self.prompts_dir / "tools").mkdir(exist_ok=True)
        (self.prompts_dir / "system").mkdir(exist_ok=True)

        # Default agent prompts
        default_prompts = {
            "agents/analysis_agent.txt": """---
description: Analysis Agent system prompt for data processing and competency assessment
version: 1.0
tags: [agent, analysis, competency]
---

You are the Analysis Agent for ReflectAI, a competency development system. Your role is to:

1. Analyze user activities and classify competency areas
2. Assess skill levels and identify development opportunities
3. Process data accurately and provide structured insights
4. Handle conversations with helpful, professional responses
5. Guide users through analysis workflows

You use evidence-based analysis and provide actionable insights. Be thorough but concise.

{% if user_context %}
User Context:
{% if user_context.level %}
- Current Level: {{ user_context.level }}
{% endif %}
{% if user_context.department %}
- Department: {{ user_context.department }}
{% endif %}
{% if user_context.role %}
- Role: {{ user_context.role }}
{% endif %}
{% endif %}

{% if previous_results %}
Previous Analysis Results:
{{ previous_results }}
{% endif %}

Task: {{ task_description }}

Provide your analysis in the following JSON format:
{
  "classification": "competency area identified",
  "confidence": 0.8,
  "evidence": ["evidence point 1", "evidence point 2"],
  "recommendations": ["recommendation 1", "recommendation 2"],
  "skill_level": "current level assessment",
  "gaps": ["gap 1", "gap 2"]
}""",
            "agents/advisor_agent.txt": """---
description: Advisor Agent system prompt for career guidance and insights synthesis
version: 1.0
tags: [agent, advisor, career]
---

You are the Advisor Agent for ReflectAI, a competency development system. Your role is to:

1. Provide strategic career guidance and development advice
2. Synthesize insights from analysis results into actionable recommendations
3. Create personalized development plans and learning paths
4. Offer strategic perspective on competency growth
5. Generate comprehensive reports and summaries

You provide thoughtful, strategic advice that balances immediate development needs with long-term career goals. Your responses are actionable, encouraging, and professionally grounded.

{% if user_context %}
User Profile:
{% if user_context.level %}
- Current Level: {{ user_context.level }}
{% endif %}
{% if user_context.department %}
- Department: {{ user_context.department }}
{% endif %}
{% if user_context.role %}
- Role: {{ user_context.role }}
{% endif %}
{% if user_context.career_goals %}
- Career Goals: {{ user_context.career_goals }}
{% endif %}
{% endif %}

{% if analysis_results %}
Analysis Results to Build Upon:
{{ analysis_results }}
{% endif %}

Task: {{ task_description }}

Provide your guidance in the following JSON format:
{
  "opportunities": ["opportunity 1", "opportunity 2"],
  "development_plan": {
    "objectives": ["objective 1", "objective 2"],
    "timeline": "suggested timeline",
    "milestones": ["milestone 1", "milestone 2"]
  },
  "timeline": "overall development timeline",
  "insights": ["key insight 1", "key insight 2"],
  "summary": "executive summary of recommendations",
  "actions": ["action 1", "action 2"]
}""",
            "tools/activity_classifier.txt": """---
description: Tool for classifying user activities by competency area
version: 1.0
tags: [tool, classification]
---

Classify the following activity into appropriate competency areas:

Activity: {{ activity_text }}

Consider these competency areas:
- Technical Skills
- Leadership
- Communication
- Problem Solving
- Project Management
- Innovation
- Collaboration
- Analysis
- Strategy

Provide classification in JSON format:
{
  "classification": "primary competency area",
  "confidence": 0.8,
  "evidence": ["evidence for classification"],
  "secondary_areas": ["other relevant areas"]
}""",
            "tools/competency_assessor.txt": """---
description: Tool for assessing competency levels
version: 1.0
tags: [tool, assessment]
---

Assess the competency level demonstrated in this activity:

Activity: {{ activity_text }}
Competency Area: {{ competency_area }}

Use this scale:
1. Novice - Limited experience, requires guidance
2. Advanced Beginner - Some experience, can perform basic tasks
3. Competent - Solid understanding, can handle routine situations
4. Proficient - Deep understanding, adapts to complex situations
5. Expert - Extensive experience, mentors others

Provide assessment in JSON format:
{
  "score": 3.5,
  "gaps": ["areas needing development"],
  "recommendations": ["specific development suggestions"],
  "evidence": ["evidence supporting the score"]
}""",
            "system/greeting.txt": """---
description: System greeting message
version: 1.0
tags: [system, greeting]
---

Hello {{ user_name }}! 👋

I'm ReflectAI, your competency development assistant. I'm here to help you:

• Analyze your work activities and identify competencies
• Assess your skill levels and development opportunities
• Provide personalized career guidance and recommendations
• Create development plans tailored to your goals

How can I assist you with your professional development today?""",
            "system/help.txt": """---
description: System help message
version: 1.0
tags: [system, help]
---

**ReflectAI Help**

I can help you with:

**📊 Activity Analysis**
- Share your recent work activities or projects
- I'll identify the competencies demonstrated
- Get skill level assessments and feedback

**🚀 Career Guidance**
- Discuss your career goals and aspirations
- Receive personalized development recommendations
- Create structured development plans

**📈 Progress Tracking**
- Review your competency growth over time
- Get insights on your development journey
- Identify areas for continued focus

**Getting Started:**
Simply describe a recent work activity, project, or challenge you've worked on, and I'll provide analysis and insights to help with your professional development.

Need specific help? Just ask! I'm here to support your growth journey.""",
            "system/error_handling.txt": """---
description: System error handling message template
version: 1.0
tags: [system, error]
---

I apologize, but I encountered an issue while processing your request.

Error: {{ error_message }}

{% if suggestions %}
Here are some suggestions:
{% for suggestion in suggestions %}
• {{ suggestion }}
{% endfor %}
{% endif %}

Please try again, or if the issue persists, contact support. I'm here to help with your competency development needs.""",
        }

        # Create prompt files
        for filepath, content in default_prompts.items():
            full_path = self.prompts_dir / filepath
            full_path.parent.mkdir(parents=True, exist_ok=True)

            if not full_path.exists():
                full_path.write_text(content, encoding="utf-8")
                logger.info(f"Created default prompt: {filepath}")

        # Reload to pick up new prompts
        self._load_prompts_from_directory()

    def list_prompts(self, prompt_type: PromptType | None = None) -> list[str]:
        """List available prompt names."""

        if prompt_type:
            return [
                name
                for name, template in self._template_cache.items()
                if template.prompt_type == prompt_type
            ]

        return list(self._template_cache.keys())

    def get_prompt_info(self, name: str) -> PromptTemplate | None:
        """Get prompt template metadata."""
        return self._template_cache.get(name)

    def validate_prompt(self, name: str, variables: dict[str, Any]) -> list[str]:
        """Validate that all required variables are provided."""

        template = self._template_cache.get(name)
        if not template:
            return [f"Prompt '{name}' not found"]

        errors = []

        # Check required variables
        missing_vars = set(template.variables) - set(variables.keys())
        for var in missing_vars:
            errors.append(f"Missing required variable: {var}")

        return errors

    def get_usage_stats(self) -> dict[str, Any]:
        """Get prompt usage statistics."""

        total_usage = sum(self._usage_stats.values())

        # Sort by usage
        sorted_usage = sorted(self._usage_stats.items(), key=lambda x: x[1], reverse=True)

        return {
            "total_prompts": len(self._template_cache),
            "total_usage": total_usage,
            "most_used": sorted_usage[:10],
            "cache_stats": self._load_stats.copy(),
            "prompts_by_type": {
                prompt_type.value: len(
                    [t for t in self._template_cache.values() if t.prompt_type == prompt_type]
                )
                for prompt_type in PromptType
            },
        }

    def test_prompt(self, name: str, test_variables: dict[str, Any]) -> dict[str, Any]:
        """Test prompt rendering with provided variables."""

        try:
            rendered = self.get_prompt(name, test_variables)

            return {
                "success": True,
                "rendered_prompt": rendered,
                "character_count": len(rendered),
                "variables_used": list(test_variables.keys()),
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "variables_provided": list(test_variables.keys()),
            }


# Global prompt manager instance
_prompt_manager: PromptManager | None = None


def get_prompt_manager() -> PromptManager:
    """Get or create global prompt manager instance."""
    global _prompt_manager
    if _prompt_manager is None:
        _prompt_manager = PromptManager()
    return _prompt_manager
