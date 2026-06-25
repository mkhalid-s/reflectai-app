"""
Framework Validator for ReflectAI

Implements comprehensive validation for competency frameworks including:
- Schema validation using Pydantic models
- Content validation and integrity checks
- Cross-reference validation between competencies and skills
- Performance and optimization recommendations

Ensures framework quality and consistency.
"""

from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from src.core.classification.competency_mapper import CompetencyFramework
from src.shared import get_logger


class ValidationSeverity(Enum):
    """Validation issue severity levels"""

    ERROR = "error"  # Must be fixed
    WARNING = "warning"  # Should be addressed
    INFO = "info"  # Informational
    OPTIMIZATION = "optimization"  # Performance/quality suggestions


class ValidationCategory(Enum):
    """Validation check categories"""

    SCHEMA = "schema"  # Basic schema validation
    CONTENT = "content"  # Content validation
    REFERENCES = "references"  # Cross-reference validation
    COMPLETENESS = "completeness"  # Completeness checks
    CONSISTENCY = "consistency"  # Consistency checks
    PERFORMANCE = "performance"  # Performance optimization
    BEST_PRACTICES = "best_practices"  # Best practice recommendations


class ValidationIssue(BaseModel):
    """Individual validation issue"""

    category: ValidationCategory = Field(..., description="Issue category")
    severity: ValidationSeverity = Field(..., description="Issue severity")
    code: str = Field(..., description="Issue code")
    message: str = Field(..., description="Human-readable message")
    details: str | None = Field(None, description="Additional details")
    location: str | None = Field(None, description="Location in framework")
    suggestion: str | None = Field(None, description="Suggested fix")

    # Context information
    affected_items: list[str] = Field(default_factory=list, description="Affected framework items")
    related_items: list[str] = Field(default_factory=list, description="Related framework items")


class ValidationResult(BaseModel):
    """Framework validation result"""

    framework_id: str = Field(..., description="Framework ID")
    framework_name: str = Field(..., description="Framework name")
    validation_timestamp: datetime = Field(default_factory=datetime.utcnow)

    # Validation summary
    is_valid: bool = Field(..., description="Overall validation status")
    has_errors: bool = Field(..., description="Has blocking errors")
    has_warnings: bool = Field(..., description="Has warnings")

    # Issues by severity
    errors: list[ValidationIssue] = Field(default_factory=list, description="Error-level issues")
    warnings: list[ValidationIssue] = Field(
        default_factory=list, description="Warning-level issues"
    )
    info: list[ValidationIssue] = Field(default_factory=list, description="Info-level issues")
    optimizations: list[ValidationIssue] = Field(
        default_factory=list, description="Optimization suggestions"
    )

    # Statistics
    total_issues: int = Field(0, description="Total number of issues")
    validation_score: float = Field(0.0, description="Validation score (0-100)")

    # Framework metrics
    competency_count: int = Field(0, description="Number of competencies")
    skill_count: int = Field(0, description="Number of skills")
    role_count: int = Field(0, description="Number of roles")

    # Performance metrics
    validation_time: float = Field(0.0, description="Time taken for validation")


class ValidationError(Exception):
    """Exception raised during validation"""

    def __init__(self, message: str, issues: list[ValidationIssue] = None):
        super().__init__(message)
        self.issues = issues or []


class FrameworkValidator:
    """
    Comprehensive competency framework validator

    Performs multiple levels of validation including schema, content,
    cross-references, and optimization recommendations.
    """

    def __init__(self):
        self.logger = get_logger("frameworks.validator")

        # Validation rules configuration
        self._validation_rules = self._build_validation_rules()

        # Performance tracking
        self._stats = {
            "total_validations": 0,
            "passed_validations": 0,
            "failed_validations": 0,
            "average_validation_time": 0.0,
            "common_issues": {},
        }

    async def validate_framework(self, framework: CompetencyFramework) -> ValidationResult:
        """
        Perform comprehensive framework validation

        Args:
            framework: Framework to validate

        Returns:
            ValidationResult with all issues and recommendations
        """
        start_time = datetime.now(UTC)

        try:
            self._stats["total_validations"] += 1

            # Initialize result
            result = ValidationResult(
                framework_id=framework.framework_id,
                framework_name=framework.name,
                competency_count=len(framework.competencies),
                skill_count=len(framework.skills),
                role_count=len(framework.roles),
            )

            # Perform validation checks
            all_issues = []

            # 1. Schema validation
            schema_issues = await self._validate_schema(framework)
            all_issues.extend(schema_issues)

            # 2. Content validation
            content_issues = await self._validate_content(framework)
            all_issues.extend(content_issues)

            # 3. Cross-reference validation
            reference_issues = await self._validate_references(framework)
            all_issues.extend(reference_issues)

            # 4. Completeness validation
            completeness_issues = await self._validate_completeness(framework)
            all_issues.extend(completeness_issues)

            # 5. Consistency validation
            consistency_issues = await self._validate_consistency(framework)
            all_issues.extend(consistency_issues)

            # 6. Performance optimization
            performance_issues = await self._validate_performance(framework)
            all_issues.extend(performance_issues)

            # 7. Best practices
            best_practice_issues = await self._validate_best_practices(framework)
            all_issues.extend(best_practice_issues)

            # Categorize issues by severity
            self._categorize_issues(result, all_issues)

            # Calculate validation metrics
            self._calculate_validation_metrics(result, all_issues)

            # Calculate validation time
            result.validation_time = (datetime.now(UTC) - start_time).total_seconds()

            # Update statistics
            self._update_stats(result)

            self.logger.info(
                f"Validated framework {framework.framework_id}: {result.validation_score:.1f}/100"
            )

            return result

        except Exception as e:
            self.logger.error(f"Framework validation failed: {str(e)}")
            raise ValidationError(f"Validation failed: {str(e)}") from e

    async def _validate_schema(self, framework: CompetencyFramework) -> list[ValidationIssue]:
        """Validate basic schema requirements"""

        issues = []

        # Required fields validation (already handled by Pydantic, but we can add custom checks)
        if not framework.framework_id:
            issues.append(
                ValidationIssue(
                    category=ValidationCategory.SCHEMA,
                    severity=ValidationSeverity.ERROR,
                    code="SCHEMA_001",
                    message="Framework ID is required",
                    location="framework_id",
                )
            )

        if not framework.name:
            issues.append(
                ValidationIssue(
                    category=ValidationCategory.SCHEMA,
                    severity=ValidationSeverity.ERROR,
                    code="SCHEMA_002",
                    message="Framework name is required",
                    location="name",
                )
            )

        if not framework.version:
            issues.append(
                ValidationIssue(
                    category=ValidationCategory.SCHEMA,
                    severity=ValidationSeverity.WARNING,
                    code="SCHEMA_003",
                    message="Framework version is recommended",
                    location="version",
                    suggestion="Add a semantic version like '1.0.0'",
                )
            )

        # ID format validation
        if (
            framework.framework_id
            and not framework.framework_id.replace("_", "").replace("-", "").isalnum()
        ):
            issues.append(
                ValidationIssue(
                    category=ValidationCategory.SCHEMA,
                    severity=ValidationSeverity.WARNING,
                    code="SCHEMA_004",
                    message="Framework ID should contain only alphanumeric characters, hyphens, and underscores",
                    location="framework_id",
                    suggestion="Use format like 'company_engineering_v1'",
                )
            )

        return issues

    async def _validate_content(self, framework: CompetencyFramework) -> list[ValidationIssue]:
        """Validate framework content quality"""

        issues = []

        # Competency validation
        for comp_id, comp_data in framework.competencies.items():
            # Name validation
            if not comp_data.get("name"):
                issues.append(
                    ValidationIssue(
                        category=ValidationCategory.CONTENT,
                        severity=ValidationSeverity.ERROR,
                        code="CONTENT_001",
                        message=f"Competency '{comp_id}' missing name",
                        location=f"competencies.{comp_id}.name",
                    )
                )

            # Description validation
            if not comp_data.get("description"):
                issues.append(
                    ValidationIssue(
                        category=ValidationCategory.CONTENT,
                        severity=ValidationSeverity.ERROR,
                        code="CONTENT_002",
                        message=f"Competency '{comp_id}' missing description",
                        location=f"competencies.{comp_id}.description",
                    )
                )
            elif len(comp_data["description"]) < 10:
                issues.append(
                    ValidationIssue(
                        category=ValidationCategory.CONTENT,
                        severity=ValidationSeverity.WARNING,
                        code="CONTENT_003",
                        message=f"Competency '{comp_id}' description is too short",
                        location=f"competencies.{comp_id}.description",
                        suggestion="Provide a more detailed description (at least 10 characters)",
                    )
                )

            # Skills validation
            comp_skills = comp_data.get("skills", [])
            if not comp_skills:
                issues.append(
                    ValidationIssue(
                        category=ValidationCategory.CONTENT,
                        severity=ValidationSeverity.WARNING,
                        code="CONTENT_004",
                        message=f"Competency '{comp_id}' has no associated skills",
                        location=f"competencies.{comp_id}.skills",
                        suggestion="Add relevant skills to make competency assessment possible",
                    )
                )

        # Skill validation
        for skill_id, skill_data in framework.skills.items():
            # Name validation
            if not skill_data.get("name"):
                issues.append(
                    ValidationIssue(
                        category=ValidationCategory.CONTENT,
                        severity=ValidationSeverity.ERROR,
                        code="CONTENT_005",
                        message=f"Skill '{skill_id}' missing name",
                        location=f"skills.{skill_id}.name",
                    )
                )

            # Description validation
            if not skill_data.get("description"):
                issues.append(
                    ValidationIssue(
                        category=ValidationCategory.CONTENT,
                        severity=ValidationSeverity.ERROR,
                        code="CONTENT_006",
                        message=f"Skill '{skill_id}' missing description",
                        location=f"skills.{skill_id}.description",
                    )
                )

            # Keywords validation
            keywords = skill_data.get("keywords", [])
            if not keywords:
                issues.append(
                    ValidationIssue(
                        category=ValidationCategory.CONTENT,
                        severity=ValidationSeverity.INFO,
                        code="CONTENT_007",
                        message=f"Skill '{skill_id}' has no keywords",
                        location=f"skills.{skill_id}.keywords",
                        suggestion="Add keywords to improve activity classification accuracy",
                    )
                )

        return issues

    async def _validate_references(self, framework: CompetencyFramework) -> list[ValidationIssue]:
        """Validate cross-references between framework components"""

        issues = []

        # Check competency-skill references
        for comp_id, comp_data in framework.competencies.items():
            comp_skills = comp_data.get("skills", [])
            for skill_id in comp_skills:
                if skill_id not in framework.skills:
                    issues.append(
                        ValidationIssue(
                            category=ValidationCategory.REFERENCES,
                            severity=ValidationSeverity.ERROR,
                            code="REF_001",
                            message=f"Competency '{comp_id}' references unknown skill '{skill_id}'",
                            location=f"competencies.{comp_id}.skills",
                            affected_items=[comp_id],
                            related_items=[skill_id],
                        )
                    )

        # Check role-competency references
        for role_id, role_competencies in framework.roles.items():
            for comp_id in role_competencies:
                if comp_id not in framework.competencies:
                    issues.append(
                        ValidationIssue(
                            category=ValidationCategory.REFERENCES,
                            severity=ValidationSeverity.ERROR,
                            code="REF_002",
                            message=f"Role '{role_id}' references unknown competency '{comp_id}'",
                            location=f"roles.{role_id}",
                            affected_items=[role_id],
                            related_items=[comp_id],
                        )
                    )

        # Check for orphaned skills (skills not referenced by any competency)
        referenced_skills = set()
        for comp_data in framework.competencies.values():
            referenced_skills.update(comp_data.get("skills", []))

        orphaned_skills = set(framework.skills.keys()) - referenced_skills
        if orphaned_skills:
            issues.append(
                ValidationIssue(
                    category=ValidationCategory.REFERENCES,
                    severity=ValidationSeverity.WARNING,
                    code="REF_003",
                    message=f"Found {len(orphaned_skills)} orphaned skills not referenced by any competency",
                    details=f"Orphaned skills: {', '.join(sorted(orphaned_skills))}",
                    suggestion="Consider removing unused skills or adding them to relevant competencies",
                    affected_items=list(orphaned_skills),
                )
            )

        return issues

    async def _validate_completeness(self, framework: CompetencyFramework) -> list[ValidationIssue]:
        """Validate framework completeness"""

        issues = []

        # Check minimum framework size
        if len(framework.competencies) < 2:
            issues.append(
                ValidationIssue(
                    category=ValidationCategory.COMPLETENESS,
                    severity=ValidationSeverity.WARNING,
                    code="COMP_001",
                    message="Framework has very few competencies (< 2)",
                    suggestion="Consider adding more competencies for comprehensive assessment",
                )
            )

        if len(framework.skills) < 5:
            issues.append(
                ValidationIssue(
                    category=ValidationCategory.COMPLETENESS,
                    severity=ValidationSeverity.WARNING,
                    code="COMP_002",
                    message="Framework has very few skills (< 5)",
                    suggestion="Add more skills for detailed competency assessment",
                )
            )

        # Check for essential competency areas
        essential_areas = ["technical_skills", "communication", "leadership", "problem_solving"]
        framework_comp_ids = set(framework.competencies.keys())
        framework_comp_names = {
            comp_data["name"].lower() for comp_data in framework.competencies.values()
        }

        missing_areas = []
        for area in essential_areas:
            if area not in framework_comp_ids and not any(
                area.replace("_", " ") in name for name in framework_comp_names
            ):
                missing_areas.append(area)

        if missing_areas:
            issues.append(
                ValidationIssue(
                    category=ValidationCategory.COMPLETENESS,
                    severity=ValidationSeverity.INFO,
                    code="COMP_003",
                    message=f"Framework may be missing common competency areas: {', '.join(missing_areas)}",
                    suggestion="Consider adding these common competency areas if relevant to your organization",
                )
            )

        # Check role definitions
        if not framework.roles:
            issues.append(
                ValidationIssue(
                    category=ValidationCategory.COMPLETENESS,
                    severity=ValidationSeverity.INFO,
                    code="COMP_004",
                    message="Framework has no role definitions",
                    suggestion="Add role definitions to enable role-based competency assessment",
                )
            )

        return issues

    async def _validate_consistency(self, framework: CompetencyFramework) -> list[ValidationIssue]:
        """Validate framework consistency"""

        issues = []

        # Check naming consistency
        comp_names = [comp_data["name"] for comp_data in framework.competencies.values()]
        skill_names = [skill_data["name"] for skill_data in framework.skills.values()]

        # Check for duplicate names
        comp_name_counts = {}
        for name in comp_names:
            comp_name_counts[name] = comp_name_counts.get(name, 0) + 1

        for name, count in comp_name_counts.items():
            if count > 1:
                issues.append(
                    ValidationIssue(
                        category=ValidationCategory.CONSISTENCY,
                        severity=ValidationSeverity.ERROR,
                        code="CONS_001",
                        message=f"Duplicate competency name: '{name}' appears {count} times",
                        suggestion="Ensure all competency names are unique",
                    )
                )

        skill_name_counts = {}
        for name in skill_names:
            skill_name_counts[name] = skill_name_counts.get(name, 0) + 1

        for name, count in skill_name_counts.items():
            if count > 1:
                issues.append(
                    ValidationIssue(
                        category=ValidationCategory.CONSISTENCY,
                        severity=ValidationSeverity.ERROR,
                        code="CONS_002",
                        message=f"Duplicate skill name: '{name}' appears {count} times",
                        suggestion="Ensure all skill names are unique",
                    )
                )

        # Check ID naming conventions
        for comp_id in framework.competencies.keys():
            if not comp_id.islower():
                issues.append(
                    ValidationIssue(
                        category=ValidationCategory.CONSISTENCY,
                        severity=ValidationSeverity.WARNING,
                        code="CONS_003",
                        message=f"Competency ID '{comp_id}' not in lowercase",
                        suggestion="Use lowercase IDs for consistency (e.g., 'technical_skills')",
                    )
                )

        for skill_id in framework.skills.keys():
            if not skill_id.islower():
                issues.append(
                    ValidationIssue(
                        category=ValidationCategory.CONSISTENCY,
                        severity=ValidationSeverity.WARNING,
                        code="CONS_004",
                        message=f"Skill ID '{skill_id}' not in lowercase",
                        suggestion="Use lowercase IDs for consistency (e.g., 'python_programming')",
                    )
                )

        return issues

    async def _validate_performance(self, framework: CompetencyFramework) -> list[ValidationIssue]:
        """Validate performance characteristics"""

        issues = []

        # Check framework size for performance
        if len(framework.skills) > 100:
            issues.append(
                ValidationIssue(
                    category=ValidationCategory.PERFORMANCE,
                    severity=ValidationSeverity.OPTIMIZATION,
                    code="PERF_001",
                    message=f"Framework has many skills ({len(framework.skills)})",
                    suggestion="Consider grouping related skills or using hierarchical structure for better performance",
                )
            )

        if len(framework.competencies) > 20:
            issues.append(
                ValidationIssue(
                    category=ValidationCategory.PERFORMANCE,
                    severity=ValidationSeverity.OPTIMIZATION,
                    code="PERF_002",
                    message=f"Framework has many competencies ({len(framework.competencies)})",
                    suggestion="Consider grouping competencies into categories for better usability",
                )
            )

        # Check for overly complex skill keywords
        for skill_id, skill_data in framework.skills.items():
            keywords = skill_data.get("keywords", [])
            if len(keywords) > 20:
                issues.append(
                    ValidationIssue(
                        category=ValidationCategory.PERFORMANCE,
                        severity=ValidationSeverity.OPTIMIZATION,
                        code="PERF_003",
                        message=f"Skill '{skill_id}' has many keywords ({len(keywords)})",
                        location=f"skills.{skill_id}.keywords",
                        suggestion="Limit keywords to most relevant terms for better classification performance",
                    )
                )

        return issues

    async def _validate_best_practices(
        self, framework: CompetencyFramework
    ) -> list[ValidationIssue]:
        """Validate against best practices"""

        issues = []

        # Check for level descriptions in skills
        skills_without_levels = []
        for skill_id, skill_data in framework.skills.items():
            if "level_descriptions" not in skill_data or not skill_data["level_descriptions"]:
                skills_without_levels.append(skill_id)

        if skills_without_levels:
            issues.append(
                ValidationIssue(
                    category=ValidationCategory.BEST_PRACTICES,
                    severity=ValidationSeverity.INFO,
                    code="BP_001",
                    message=f"{len(skills_without_levels)} skills missing level descriptions",
                    suggestion="Add level descriptions to help users understand proficiency expectations",
                    affected_items=skills_without_levels,
                )
            )

        # Check for skill patterns (for better classification)
        skills_without_patterns = []
        for skill_id, skill_data in framework.skills.items():
            if "patterns" not in skill_data or not skill_data["patterns"]:
                skills_without_patterns.append(skill_id)

        if len(skills_without_patterns) > len(framework.skills) * 0.5:
            issues.append(
                ValidationIssue(
                    category=ValidationCategory.BEST_PRACTICES,
                    severity=ValidationSeverity.INFO,
                    code="BP_002",
                    message="Many skills missing regex patterns for classification",
                    suggestion="Add regex patterns to improve activity classification accuracy",
                )
            )

        # Check for framework metadata
        if not framework.organization:
            issues.append(
                ValidationIssue(
                    category=ValidationCategory.BEST_PRACTICES,
                    severity=ValidationSeverity.INFO,
                    code="BP_003",
                    message="Framework missing organization information",
                    suggestion="Add organization field for better framework management",
                )
            )

        return issues

    def _categorize_issues(self, result: ValidationResult, all_issues: list[ValidationIssue]):
        """Categorize issues by severity"""

        for issue in all_issues:
            if issue.severity == ValidationSeverity.ERROR:
                result.errors.append(issue)
            elif issue.severity == ValidationSeverity.WARNING:
                result.warnings.append(issue)
            elif issue.severity == ValidationSeverity.INFO:
                result.info.append(issue)
            elif issue.severity == ValidationSeverity.OPTIMIZATION:
                result.optimizations.append(issue)

        result.total_issues = len(all_issues)
        result.has_errors = len(result.errors) > 0
        result.has_warnings = len(result.warnings) > 0
        result.is_valid = not result.has_errors

    def _calculate_validation_metrics(
        self, result: ValidationResult, all_issues: list[ValidationIssue]
    ):
        """Calculate validation score and metrics"""

        # Base score
        score = 100.0

        # Deduct points for issues
        for issue in all_issues:
            if issue.severity == ValidationSeverity.ERROR:
                score -= 10.0
            elif issue.severity == ValidationSeverity.WARNING:
                score -= 3.0
            elif issue.severity == ValidationSeverity.INFO:
                score -= 1.0
            # Optimization suggestions don't affect score

        # Bonus points for good practices
        if result.competency_count >= 5:
            score += 2.0
        if result.skill_count >= 10:
            score += 2.0
        if result.role_count >= 3:
            score += 2.0

        # Ensure score is in valid range
        result.validation_score = max(0.0, min(100.0, score))

    def _build_validation_rules(self) -> dict[str, Any]:
        """Build validation rules configuration"""

        return {
            "min_competencies": 2,
            "min_skills": 5,
            "max_competencies": 20,
            "max_skills": 100,
            "min_description_length": 10,
            "max_keywords_per_skill": 20,
            "required_competency_fields": ["name", "description"],
            "required_skill_fields": ["name", "description"],
            "recommended_competency_areas": [
                "technical_skills",
                "communication",
                "leadership",
                "problem_solving",
            ],
        }

    def _update_stats(self, result: ValidationResult):
        """Update validator statistics"""

        if result.is_valid:
            self._stats["passed_validations"] += 1
        else:
            self._stats["failed_validations"] += 1

        # Update average validation time
        total = self._stats["total_validations"]
        current_avg = self._stats["average_validation_time"]
        self._stats["average_validation_time"] = (
            (current_avg * (total - 1)) + result.validation_time
        ) / total

        # Track common issues
        for issue in result.errors + result.warnings:
            self._stats["common_issues"][issue.code] = (
                self._stats["common_issues"].get(issue.code, 0) + 1
            )

    def get_validator_stats(self) -> dict[str, Any]:
        """Get validator statistics"""
        stats = self._stats.copy()
        stats["success_rate"] = (
            self._stats["passed_validations"] / max(self._stats["total_validations"], 1)
        ) * 100
        return stats

    async def validate_framework_file(self, framework_data: dict[str, Any]) -> ValidationResult:
        """Validate framework from raw dictionary data"""

        try:
            # First try to create framework object (this validates basic schema)
            framework = CompetencyFramework(**framework_data)

            # Then perform comprehensive validation
            return await self.validate_framework(framework)

        except Exception as e:
            # Return validation result with schema errors
            return ValidationResult(
                framework_id=framework_data.get("framework_id", "unknown"),
                framework_name=framework_data.get("name", "unknown"),
                is_valid=False,
                has_errors=True,
                has_warnings=False,
                errors=[
                    ValidationIssue(
                        category=ValidationCategory.SCHEMA,
                        severity=ValidationSeverity.ERROR,
                        code="SCHEMA_000",
                        message=f"Framework schema validation failed: {str(e)}",
                    )
                ],
                validation_score=0.0,
            )


# Global validator instance
_global_validator: FrameworkValidator | None = None


def get_framework_validator() -> FrameworkValidator:
    """Get global framework validator instance"""
    global _global_validator
    if _global_validator is None:
        _global_validator = FrameworkValidator()
    return _global_validator
