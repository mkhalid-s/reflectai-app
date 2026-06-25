"""
Competency Framework Loader for ReflectAI

Implements JSON-based framework loading with validation and hot-reloading capabilities.
Supports multiple organizations and framework versioning.
"""

import json
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from src.core.classification.competency_mapper import CompetencyFramework
from src.shared import get_logger


class LoadStatus(Enum):
    """Framework loading status"""

    SUCCESS = "success"
    FAILED = "failed"
    VALIDATION_ERROR = "validation_error"
    FILE_NOT_FOUND = "file_not_found"
    INVALID_JSON = "invalid_json"


class FrameworkLoadResult(BaseModel):
    """Result of framework loading operation"""

    framework_id: str | None = Field(None, description="Loaded framework ID")
    status: LoadStatus = Field(..., description="Loading status")
    framework: CompetencyFramework | None = Field(None, description="Loaded framework")
    errors: list[str] = Field(default_factory=list, description="Loading errors")
    warnings: list[str] = Field(default_factory=list, description="Loading warnings")
    load_time: float = Field(..., description="Time taken to load")
    file_path: str = Field(..., description="Source file path")
    loaded_at: datetime = Field(default_factory=datetime.utcnow)


class CompetencyFrameworkLoader:
    """JSON-based competency framework loader with validation and hot-reloading"""

    def __init__(self, frameworks_directory: str = "data/frameworks"):
        self.logger = get_logger("frameworks.loader")
        self.frameworks_directory = Path(frameworks_directory)
        self.frameworks_directory.mkdir(parents=True, exist_ok=True)

        # Loaded frameworks cache
        self._loaded_frameworks: dict[str, CompetencyFramework] = {}
        self._load_results: dict[str, FrameworkLoadResult] = {}

        # File watching for hot-reload (simplified)
        self._file_timestamps: dict[str, float] = {}

        # Statistics
        self._stats = {"total_loads": 0, "successful_loads": 0, "failed_loads": 0, "hot_reloads": 0}

    async def load_framework(self, framework_file: str) -> FrameworkLoadResult:
        """Load a competency framework from JSON file"""

        start_time = datetime.now(UTC)
        file_path = self.frameworks_directory / framework_file

        self._stats["total_loads"] += 1

        try:
            # Check if file exists
            if not file_path.exists():
                result = FrameworkLoadResult(
                    status=LoadStatus.FILE_NOT_FOUND,
                    errors=[f"Framework file not found: {file_path}"],
                    load_time=0.0,
                    file_path=str(file_path),
                )
                self._stats["failed_loads"] += 1
                return result

            # Read and parse JSON
            try:
                with open(file_path, encoding="utf-8") as f:
                    framework_data = json.load(f)
            except json.JSONDecodeError as e:
                result = FrameworkLoadResult(
                    status=LoadStatus.INVALID_JSON,
                    errors=[f"Invalid JSON in framework file: {str(e)}"],
                    load_time=0.0,
                    file_path=str(file_path),
                )
                self._stats["failed_loads"] += 1
                return result

            # Validate and create framework
            try:
                framework = CompetencyFramework(**framework_data)

                # Additional validation
                validation_errors, warnings = self._validate_framework_content(framework)

                if validation_errors:
                    result = FrameworkLoadResult(
                        status=LoadStatus.VALIDATION_ERROR,
                        errors=validation_errors,
                        warnings=warnings,
                        load_time=(datetime.now(UTC) - start_time).total_seconds(),
                        file_path=str(file_path),
                    )
                    self._stats["failed_loads"] += 1
                    return result

                # Store framework
                self._loaded_frameworks[framework.framework_id] = framework

                # Update file timestamp for hot-reload tracking
                self._file_timestamps[framework.framework_id] = file_path.stat().st_mtime

                # Create success result
                result = FrameworkLoadResult(
                    framework_id=framework.framework_id,
                    status=LoadStatus.SUCCESS,
                    framework=framework,
                    warnings=warnings,
                    load_time=(datetime.now(UTC) - start_time).total_seconds(),
                    file_path=str(file_path),
                )

                self._load_results[framework.framework_id] = result
                self._stats["successful_loads"] += 1

                self.logger.info(f"Successfully loaded framework: {framework.framework_id}")
                return result

            except Exception as e:
                result = FrameworkLoadResult(
                    status=LoadStatus.VALIDATION_ERROR,
                    errors=[f"Framework validation failed: {str(e)}"],
                    load_time=(datetime.now(UTC) - start_time).total_seconds(),
                    file_path=str(file_path),
                )
                self._stats["failed_loads"] += 1
                return result

        except Exception as e:
            result = FrameworkLoadResult(
                status=LoadStatus.FAILED,
                errors=[f"Unexpected error loading framework: {str(e)}"],
                load_time=(datetime.now(UTC) - start_time).total_seconds(),
                file_path=str(file_path),
            )
            self._stats["failed_loads"] += 1
            return result

    async def load_all_frameworks(self) -> list[FrameworkLoadResult]:
        """Load all framework files in the frameworks directory"""

        results = []

        # Find all JSON files in frameworks directory
        json_files = list(self.frameworks_directory.glob("*.json"))

        if not json_files:
            self.logger.warning(f"No framework files found in {self.frameworks_directory}")
            return results

        # Load each framework
        for json_file in json_files:
            result = await self.load_framework(json_file.name)
            results.append(result)

        successful_count = len([r for r in results if r.status == LoadStatus.SUCCESS])
        self.logger.info(f"Loaded {successful_count}/{len(results)} frameworks successfully")

        return results

    async def hot_reload_framework(self, framework_id: str) -> FrameworkLoadResult:
        """Hot-reload a specific framework if it has changed"""

        self._stats["hot_reloads"] += 1

        # Find the framework file
        framework_file = None
        for json_file in self.frameworks_directory.glob("*.json"):
            try:
                with open(json_file) as f:
                    data = json.load(f)
                    if data.get("framework_id") == framework_id:
                        framework_file = json_file.name
                        break
            except Exception:
                continue

        if not framework_file:
            return FrameworkLoadResult(
                status=LoadStatus.FILE_NOT_FOUND,
                errors=[f"Framework file not found for ID: {framework_id}"],
                load_time=0.0,
                file_path="unknown",
            )

        # Check if file has been modified
        file_path = self.frameworks_directory / framework_file
        current_mtime = file_path.stat().st_mtime
        last_mtime = self._file_timestamps.get(framework_id, 0)

        if current_mtime <= last_mtime:
            self.logger.info(f"Framework {framework_id} unchanged, skipping reload")
            # Return cached result
            cached_result = self._load_results.get(framework_id)
            if cached_result:
                return cached_result

        # Reload framework
        self.logger.info(f"Hot-reloading framework: {framework_id}")
        result = await self.load_framework(framework_file)

        return result

    async def reload_all_frameworks(self) -> list[FrameworkLoadResult]:
        """Reload all frameworks, checking for changes"""

        results = []

        # Get list of currently loaded frameworks
        loaded_ids = list(self._loaded_frameworks.keys())

        # Reload each framework
        for framework_id in loaded_ids:
            result = await self.hot_reload_framework(framework_id)
            results.append(result)

        # Also check for new framework files
        json_files = list(self.frameworks_directory.glob("*.json"))
        for json_file in json_files:
            try:
                with open(json_file) as f:
                    data = json.load(f)
                    framework_id = data.get("framework_id")
                    if framework_id and framework_id not in loaded_ids:
                        # New framework file found
                        result = await self.load_framework(json_file.name)
                        results.append(result)
            except Exception:
                continue

        return results

    def get_framework(self, framework_id: str) -> CompetencyFramework | None:
        """Get a loaded framework by ID"""
        return self._loaded_frameworks.get(framework_id)

    def list_loaded_frameworks(self) -> list[str]:
        """Get list of loaded framework IDs"""
        return list(self._loaded_frameworks.keys())

    def get_load_result(self, framework_id: str) -> FrameworkLoadResult | None:
        """Get load result for a framework"""
        return self._load_results.get(framework_id)

    def get_loader_stats(self) -> dict[str, Any]:
        """Get loader statistics"""
        stats = self._stats.copy()
        stats["loaded_frameworks_count"] = len(self._loaded_frameworks)
        stats["success_rate"] = (
            self._stats["successful_loads"] / max(self._stats["total_loads"], 1)
        ) * 100
        return stats

    def _validate_framework_content(
        self, framework: CompetencyFramework
    ) -> tuple[list[str], list[str]]:
        """Validate framework content and structure"""

        errors = []
        warnings = []

        # Check competencies reference valid skills
        for comp_id, comp_data in framework.competencies.items():
            comp_skills = comp_data.get("skills", [])
            for skill_id in comp_skills:
                if skill_id not in framework.skills:
                    errors.append(f"Competency {comp_id} references unknown skill: {skill_id}")

        # Check for orphaned skills (not referenced by any competency)
        referenced_skills = set()
        for comp_data in framework.competencies.values():
            referenced_skills.update(comp_data.get("skills", []))

        orphaned_skills = set(framework.skills.keys()) - referenced_skills
        if orphaned_skills:
            warnings.append(
                f"Orphaned skills (not referenced by any competency): {', '.join(orphaned_skills)}"
            )

        # Check role mappings reference valid competencies
        for role, competencies in framework.roles.items():
            for comp_id in competencies:
                if comp_id not in framework.competencies:
                    errors.append(f"Role {role} references unknown competency: {comp_id}")

        # Check for missing required fields
        required_comp_fields = ["name", "description"]
        for comp_id, comp_data in framework.competencies.items():
            for field in required_comp_fields:
                if field not in comp_data:
                    errors.append(f"Competency {comp_id} missing required field: {field}")

        required_skill_fields = ["name", "description"]
        for skill_id, skill_data in framework.skills.items():
            for field in required_skill_fields:
                if field not in skill_data:
                    errors.append(f"Skill {skill_id} missing required field: {field}")

        # Check for reasonable framework size
        if len(framework.competencies) < 2:
            warnings.append("Framework has very few competencies (< 2)")
        elif len(framework.competencies) > 20:
            warnings.append("Framework has many competencies (> 20), consider grouping")

        if len(framework.skills) < 5:
            warnings.append("Framework has very few skills (< 5)")
        elif len(framework.skills) > 100:
            warnings.append("Framework has many skills (> 100), consider optimization")

        return errors, warnings

    async def create_sample_framework(
        self, filename: str = "sample_framework.json"
    ) -> FrameworkLoadResult:
        """Create a sample framework file for testing/demonstration"""

        sample_framework = {
            "framework_id": "sample_engineering",
            "name": "Sample Software Engineering Framework",
            "version": "1.0",
            "description": "Sample competency framework for software engineering roles",
            "organization": "Sample Organization",
            "competencies": {
                "technical_skills": {
                    "name": "Technical Skills",
                    "description": "Programming and technical problem-solving abilities",
                    "skills": ["python", "javascript", "system_design", "databases"],
                },
                "leadership": {
                    "name": "Leadership",
                    "description": "Leading teams and driving initiatives",
                    "skills": ["team_management", "decision_making", "strategic_thinking"],
                },
                "communication": {
                    "name": "Communication",
                    "description": "Effective communication with team and stakeholders",
                    "skills": ["technical_writing", "presentations", "documentation"],
                },
            },
            "skills": {
                "python": {
                    "name": "Python Programming",
                    "description": "Proficiency in Python programming language",
                    "keywords": ["python", "django", "flask", "pandas"],
                    "level_descriptions": {
                        "1": "Basic syntax knowledge",
                        "2": "Can write simple scripts",
                        "3": "Can build applications",
                        "4": "Advanced patterns and optimization",
                        "5": "Expert-level architecture and mentoring",
                    },
                },
                "javascript": {
                    "name": "JavaScript Programming",
                    "description": "Proficiency in JavaScript and related technologies",
                    "keywords": ["javascript", "node", "react", "vue"],
                    "level_descriptions": {
                        "1": "Basic syntax and DOM manipulation",
                        "2": "Can build simple interactive pages",
                        "3": "Can develop full applications",
                        "4": "Advanced frameworks and patterns",
                        "5": "Expert-level architecture and performance",
                    },
                },
                "system_design": {
                    "name": "System Design",
                    "description": "Designing scalable software systems",
                    "keywords": ["architecture", "scalability", "microservices", "distributed"],
                },
                "databases": {
                    "name": "Database Management",
                    "description": "Database design and management skills",
                    "keywords": ["sql", "nosql", "postgresql", "mongodb"],
                },
                "team_management": {
                    "name": "Team Management",
                    "description": "Leading and managing software teams",
                    "keywords": ["leadership", "management", "scrum", "agile"],
                },
                "decision_making": {
                    "name": "Decision Making",
                    "description": "Making effective technical and business decisions",
                    "keywords": ["analysis", "judgment", "strategy"],
                },
                "strategic_thinking": {
                    "name": "Strategic Thinking",
                    "description": "Long-term planning and strategic analysis",
                    "keywords": ["strategy", "planning", "vision"],
                },
                "technical_writing": {
                    "name": "Technical Writing",
                    "description": "Creating clear technical documentation",
                    "keywords": ["documentation", "writing", "communication"],
                },
                "presentations": {
                    "name": "Presentations",
                    "description": "Delivering effective presentations",
                    "keywords": ["presenting", "communication", "public speaking"],
                },
                "documentation": {
                    "name": "Documentation",
                    "description": "Creating and maintaining project documentation",
                    "keywords": ["docs", "readme", "wiki", "specifications"],
                },
            },
            "levels": {
                "1": {"name": "Novice", "description": "Learning the basics"},
                "2": {"name": "Beginner", "description": "Can perform simple tasks with guidance"},
                "3": {"name": "Intermediate", "description": "Can work independently"},
                "4": {"name": "Advanced", "description": "Can handle complex tasks"},
                "5": {"name": "Expert", "description": "Recognized expert and mentor"},
            },
            "roles": {
                "junior_engineer": ["technical_skills"],
                "senior_engineer": ["technical_skills", "communication"],
                "tech_lead": ["technical_skills", "leadership", "communication"],
                "engineering_manager": ["leadership", "communication", "technical_skills"],
            },
        }

        # Write to file
        file_path = self.frameworks_directory / filename

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(sample_framework, f, indent=2, ensure_ascii=False)

            self.logger.info(f"Created sample framework: {file_path}")

            # Load the framework
            return await self.load_framework(filename)

        except Exception as e:
            return FrameworkLoadResult(
                status=LoadStatus.FAILED,
                errors=[f"Failed to create sample framework: {str(e)}"],
                load_time=0.0,
                file_path=str(file_path),
            )


# Global loader instance
_global_loader: CompetencyFrameworkLoader | None = None


def get_framework_loader(
    frameworks_directory: str = "data/frameworks",
) -> CompetencyFrameworkLoader:
    """Get global framework loader instance"""
    global _global_loader
    if _global_loader is None:
        _global_loader = CompetencyFrameworkLoader(frameworks_directory)
    return _global_loader
