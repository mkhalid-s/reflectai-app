"""
Competency Framework Mapping for ReflectAI

Implements  Competency Framework Mapping including:
- Dynamic framework loading with JSON-based competency definitions
- Framework schema validation using Pydantic models
- Framework hot-reloading without service restart
- Activity-to-competency mapping with skill extraction
- Multi-competency activities with weight distribution

Provides flexible competency framework management with organization-specific support.
"""

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, validator

from src.core.storage.models.activity_data import ActivityType
from src.shared import ErrorSeverity, ReflectAIError, get_logger


class FrameworkVersion(Enum):
    """Framework versioning scheme"""

    V1_0 = "1.0"
    V1_1 = "1.1"
    V2_0 = "2.0"


class SkillLevel(Enum):
    """Skill proficiency levels"""

    NOVICE = 1
    BEGINNER = 2
    INTERMEDIATE = 3
    ADVANCED = 4
    EXPERT = 5


class CompetencyFramework(BaseModel):
    """Competency framework definition"""

    framework_id: str = Field(..., description="Unique framework identifier")
    name: str = Field(..., description="Framework display name")
    version: str = Field(..., description="Framework version")
    description: str = Field(..., description="Framework description")
    organization: str | None = Field(None, description="Organization this framework belongs to")

    # Framework structure
    competencies: dict[str, dict[str, Any]] = Field(..., description="Competency definitions")
    skills: dict[str, dict[str, Any]] = Field(..., description="Skill definitions")
    levels: dict[str, dict[str, Any]] = Field(..., description="Level definitions")
    roles: dict[str, list[str]] = Field(
        default_factory=dict, description="Role-to-competency mappings"
    )

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = Field(True, description="Whether framework is active")

    @validator("competencies")
    def validate_competencies(cls, v):
        """Validate competency definitions"""
        for comp_id, comp_data in v.items():
            if "name" not in comp_data or "description" not in comp_data:
                raise ValueError(f"Competency {comp_id} missing required fields")
            if "skills" not in comp_data:
                comp_data["skills"] = []
        return v

    @validator("skills")
    def validate_skills(cls, v):
        """Validate skill definitions"""
        for skill_id, skill_data in v.items():
            if "name" not in skill_data or "description" not in skill_data:
                raise ValueError(f"Skill {skill_id} missing required fields")
            if "level_descriptions" not in skill_data:
                skill_data["level_descriptions"] = {}
        return v


class CompetencyMapping(BaseModel):
    """Mapping between activities and competencies"""

    activity_description: str = Field(..., description="Activity description")
    activity_type: ActivityType = Field(..., description="Classified activity type")

    # Primary mapping
    primary_competency: str = Field(..., description="Primary competency ID")
    primary_weight: float = Field(..., description="Weight for primary competency (0-1)")

    # Secondary mappings
    secondary_competencies: list[dict[str, Any]] = Field(
        default_factory=list, description="Secondary competencies with weights"
    )

    # Extracted skills
    extracted_skills: list[str] = Field(
        default_factory=list, description="Skills extracted from activity"
    )
    skill_confidence: dict[str, float] = Field(
        default_factory=dict, description="Confidence scores for extracted skills"
    )

    # Framework context
    framework_id: str = Field(..., description="Framework used for mapping")
    framework_version: str = Field(..., description="Framework version")

    # Quality metrics
    mapping_confidence: float = Field(..., description="Overall mapping confidence")
    extraction_method: str = Field(..., description="Method used for extraction")

    created_at: datetime = Field(default_factory=datetime.utcnow)


class SkillExtraction(BaseModel):
    """Result of skill extraction from activity"""

    activity_text: str = Field(..., description="Original activity text")
    extracted_skills: list[str] = Field(..., description="Extracted skill names")

    # Extraction details
    skill_matches: dict[str, list[str]] = Field(
        default_factory=dict, description="Skills matched with evidence"
    )
    confidence_scores: dict[str, float] = Field(
        default_factory=dict, description="Confidence per skill"
    )
    extraction_method: str = Field(..., description="Extraction method used")

    # Framework context
    framework_skills: list[str] = Field(
        default_factory=list, description="Available skills in framework"
    )
    matched_count: int = Field(0, description="Number of skills matched")
    total_available: int = Field(0, description="Total skills available in framework")

    processing_time: float = Field(..., description="Time taken for extraction")
    created_at: datetime = Field(default_factory=datetime.utcnow)


@dataclass
class CompetencyRule:
    """Rule for mapping activities to competencies"""

    activity_types: list[ActivityType]
    competency_id: str
    weight: float
    keywords: list[str] = field(default_factory=list)
    skill_indicators: list[str] = field(default_factory=list)
    context_boosts: dict[str, float] = field(default_factory=dict)


class CompetencyMapper:
    """
    Dynamic competency framework mapper

    Provides skill extraction from activities and competency mapping with
    support for multiple frameworks and hot-reloading capabilities.
    """

    def __init__(self, frameworks_directory: str | None = None):
        self.logger = get_logger("classification.competency_mapper")

        # Framework storage
        self.frameworks_directory = frameworks_directory or "data/frameworks"
        self._frameworks: dict[str, CompetencyFramework] = {}
        self._default_framework_id: str | None = None

        # Mapping rules
        self._mapping_rules: list[CompetencyRule] = []

        # Performance tracking
        self._stats = {
            "total_mappings": 0,
            "successful_extractions": 0,
            "framework_loads": 0,
            "average_confidence": 0.0,
            "frameworks_count": 0,
        }

        # Initialize with default framework
        self._load_default_framework()
        self._build_mapping_rules()

    async def map_activity_to_competencies(
        self,
        activity_description: str,
        activity_type: ActivityType,
        framework_id: str | None = None,
        user_context: dict[str, Any] | None = None,
    ) -> CompetencyMapping:
        """
        Map an activity to competencies in the specified framework

        Args:
            activity_description: Description of the activity
            activity_type: Classified activity type
            framework_id: Framework to use (default if None)
            user_context: User context for enhanced mapping

        Returns:
            CompetencyMapping with competency assignments and weights
        """
        start_time = datetime.now(UTC)

        try:
            # Get framework
            framework = self.get_framework(framework_id)
            if not framework:
                raise ValueError(f"Framework not found: {framework_id}")

            # Extract skills from activity
            skill_extraction = await self.extract_skills_from_activity(
                activity_description, framework_id, user_context
            )

            # Map to competencies
            competency_mappings = self._map_skills_to_competencies(
                skill_extraction.extracted_skills, framework, activity_type
            )

            if not competency_mappings:
                # Fallback mapping based on activity type
                competency_mappings = self._fallback_activity_mapping(activity_type, framework)

            # Select primary and secondary competencies
            primary_comp, primary_weight, secondary_comps = self._select_competencies(
                competency_mappings
            )

            # Calculate overall confidence
            mapping_confidence = self._calculate_mapping_confidence(
                skill_extraction, competency_mappings, activity_type
            )

            # Create mapping result
            mapping = CompetencyMapping(
                activity_description=activity_description,
                activity_type=activity_type,
                primary_competency=primary_comp,
                primary_weight=primary_weight,
                secondary_competencies=secondary_comps,
                extracted_skills=skill_extraction.extracted_skills,
                skill_confidence=skill_extraction.confidence_scores,
                framework_id=framework.framework_id,
                framework_version=framework.version,
                mapping_confidence=mapping_confidence,
                extraction_method=skill_extraction.extraction_method,
            )

            # Update statistics
            (datetime.now(UTC) - start_time).total_seconds()
            self._update_stats(mapping_confidence, len(skill_extraction.extracted_skills) > 0)

            return mapping

        except Exception as e:
            self.logger.error(f"Competency mapping failed: {str(e)}")

            # Create fallback mapping
            framework = self.get_framework() or self._create_minimal_framework()
            return CompetencyMapping(
                activity_description=activity_description,
                activity_type=activity_type,
                primary_competency="technical_skills",
                primary_weight=0.8,
                secondary_competencies=[],
                extracted_skills=[],
                skill_confidence={},
                framework_id=framework.framework_id,
                framework_version=framework.version,
                mapping_confidence=0.3,
                extraction_method="fallback",
            )

    async def extract_skills_from_activity(
        self,
        activity_description: str,
        framework_id: str | None = None,
        user_context: dict[str, Any] | None = None,
    ) -> SkillExtraction:
        """
        Extract skills from activity description

        Args:
            activity_description: Activity text to analyze
            framework_id: Framework to use for skill extraction
            user_context: User context for enhanced extraction

        Returns:
            SkillExtraction with extracted skills and confidence scores
        """
        start_time = datetime.now(UTC)

        # Get framework
        framework = self.get_framework(framework_id)
        if not framework:
            framework = self._create_minimal_framework()

        # Get available skills
        available_skills = list(framework.skills.keys())

        # Extract skills using multiple methods
        keyword_skills = self._extract_skills_by_keywords(activity_description, framework)
        pattern_skills = self._extract_skills_by_patterns(activity_description, framework)
        context_skills = self._extract_skills_by_context(
            activity_description, user_context or {}, framework
        )

        # Combine and score skills
        all_extracted = {}
        all_extracted.update(keyword_skills)
        all_extracted.update(pattern_skills)
        all_extracted.update(context_skills)

        # Filter and rank skills
        final_skills = []
        skill_matches = {}
        confidence_scores = {}

        for skill, evidence in all_extracted.items():
            if skill in available_skills:
                confidence = self._calculate_skill_confidence(skill, evidence, activity_description)
                if confidence > 0.3:  # Minimum threshold
                    final_skills.append(skill)
                    skill_matches[skill] = evidence
                    confidence_scores[skill] = confidence

        # Sort by confidence
        final_skills.sort(key=lambda s: confidence_scores.get(s, 0), reverse=True)

        processing_time = (datetime.now(UTC) - start_time).total_seconds()

        return SkillExtraction(
            activity_text=activity_description,
            extracted_skills=final_skills[:10],  # Top 10 skills
            skill_matches=skill_matches,
            confidence_scores=confidence_scores,
            extraction_method="hybrid_keyword_pattern_context",
            framework_skills=available_skills,
            matched_count=len(final_skills),
            total_available=len(available_skills),
            processing_time=processing_time,
        )

    def load_framework(self, framework_path: str) -> str:
        """
        Load competency framework from JSON file

        Args:
            framework_path: Path to framework JSON file

        Returns:
            Framework ID of loaded framework
        """
        try:
            with open(framework_path) as f:
                framework_data = json.load(f)

            # Validate and create framework
            framework = CompetencyFramework(**framework_data)

            # Store framework
            self._frameworks[framework.framework_id] = framework

            # Set as default if first framework
            if not self._default_framework_id:
                self._default_framework_id = framework.framework_id

            self.logger.info(f"Loaded framework: {framework.framework_id} v{framework.version}")
            self._stats["framework_loads"] += 1
            self._stats["frameworks_count"] = len(self._frameworks)

            return framework.framework_id

        except Exception as e:
            self.logger.error(f"Failed to load framework from {framework_path}: {str(e)}")
            raise ReflectAIError(
                message=f"Framework loading failed: {str(e)}", category=ErrorSeverity.HIGH
            ) from e

    def hot_reload_framework(self, framework_id: str) -> bool:
        """
        Hot-reload a framework without service restart

        Args:
            framework_id: Framework to reload

        Returns:
            True if successful, False otherwise
        """
        try:
            framework_path = Path(self.frameworks_directory) / f"{framework_id}.json"

            if not framework_path.exists():
                self.logger.warning(f"Framework file not found: {framework_path}")
                return False

            # Load new version
            new_framework_id = self.load_framework(str(framework_path))

            # Update mapping rules if needed
            self._build_mapping_rules()

            self.logger.info(f"Hot-reloaded framework: {new_framework_id}")
            return True

        except Exception as e:
            self.logger.error(f"Hot-reload failed for {framework_id}: {str(e)}")
            return False

    def get_framework(self, framework_id: str | None = None) -> CompetencyFramework | None:
        """Get framework by ID or default framework"""
        if framework_id:
            return self._frameworks.get(framework_id)
        elif self._default_framework_id:
            return self._frameworks.get(self._default_framework_id)
        else:
            return None

    def list_frameworks(self) -> list[dict[str, Any]]:
        """List all available frameworks"""
        return [
            {
                "framework_id": fw.framework_id,
                "name": fw.name,
                "version": fw.version,
                "organization": fw.organization,
                "competencies_count": len(fw.competencies),
                "skills_count": len(fw.skills),
                "is_active": fw.is_active,
            }
            for fw in self._frameworks.values()
        ]

    def get_competency_hierarchy(self, framework_id: str | None = None) -> dict[str, Any]:
        """Get competency hierarchy for a framework"""
        framework = self.get_framework(framework_id)
        if not framework:
            return {}

        hierarchy = {}

        for comp_id, comp_data in framework.competencies.items():
            hierarchy[comp_id] = {
                "name": comp_data["name"],
                "description": comp_data["description"],
                "skills": comp_data.get("skills", []),
                "skill_details": {
                    skill_id: framework.skills.get(skill_id, {})
                    for skill_id in comp_data.get("skills", [])
                    if skill_id in framework.skills
                },
            }

        return hierarchy

    def _extract_skills_by_keywords(
        self, activity_description: str, framework: CompetencyFramework
    ) -> dict[str, list[str]]:
        """Extract skills using keyword matching"""

        extracted = {}
        text_lower = activity_description.lower()

        for skill_id, skill_data in framework.skills.items():
            skill_name = skill_data["name"].lower()
            keywords = skill_data.get("keywords", [skill_name])

            matches = []
            for keyword in keywords:
                if keyword.lower() in text_lower:
                    matches.append(f"keyword:{keyword}")

            # Direct skill name match
            if skill_name in text_lower:
                matches.append(f"direct_match:{skill_name}")

            if matches:
                extracted[skill_id] = matches

        return extracted

    def _extract_skills_by_patterns(
        self, activity_description: str, framework: CompetencyFramework
    ) -> dict[str, list[str]]:
        """Extract skills using pattern matching"""

        import re

        extracted = {}

        for skill_id, skill_data in framework.skills.items():
            patterns = skill_data.get("patterns", [])

            matches = []
            for pattern in patterns:
                try:
                    if re.search(pattern, activity_description, re.IGNORECASE):
                        matches.append(f"pattern:{pattern}")
                except re.error:
                    continue  # Skip invalid patterns

            if matches:
                extracted[skill_id] = matches

        return extracted

    def _extract_skills_by_context(
        self,
        activity_description: str,
        user_context: dict[str, Any],
        framework: CompetencyFramework,
    ) -> dict[str, list[str]]:
        """Extract skills using user context"""

        extracted = {}

        user_role = user_context.get("role", "").lower()
        user_department = user_context.get("department", "").lower()
        user_skills = user_context.get("skills", [])

        for skill_id, skill_data in framework.skills.items():
            context_indicators = skill_data.get("context_indicators", [])

            matches = []

            # Role-based matching
            if any(indicator in user_role for indicator in context_indicators):
                matches.append(f"role_context:{user_role}")

            # Department-based matching
            if any(indicator in user_department for indicator in context_indicators):
                matches.append(f"dept_context:{user_department}")

            # User skills matching
            skill_name = skill_data["name"].lower()
            if any(skill_name in user_skill.lower() for user_skill in user_skills):
                matches.append(f"user_skill_match:{skill_name}")

            if matches:
                extracted[skill_id] = matches

        return extracted

    def _calculate_skill_confidence(
        self, skill_id: str, evidence: list[str], activity_description: str
    ) -> float:
        """Calculate confidence score for skill extraction"""

        confidence = 0.0

        # Base confidence from evidence count
        confidence += min(len(evidence) * 0.2, 0.6)

        # Evidence type weighting
        for ev in evidence:
            if ev.startswith("direct_match"):
                confidence += 0.3
            elif ev.startswith("keyword"):
                confidence += 0.2
            elif ev.startswith("pattern"):
                confidence += 0.25
            elif ev.startswith("role_context"):
                confidence += 0.1
            elif ev.startswith("user_skill_match"):
                confidence += 0.15

        # Length bonus for detailed descriptions
        if len(activity_description) > 50:
            confidence += 0.05

        return min(confidence, 1.0)

    def _map_skills_to_competencies(
        self,
        extracted_skills: list[str],
        framework: CompetencyFramework,
        activity_type: ActivityType,
    ) -> dict[str, float]:
        """Map extracted skills to competencies with weights"""

        competency_scores = {}

        # Map skills to competencies
        for skill_id in extracted_skills:
            # Find competencies that include this skill
            for comp_id, comp_data in framework.competencies.items():
                comp_skills = comp_data.get("skills", [])
                if skill_id in comp_skills:
                    weight = 1.0 / len(comp_skills)  # Weight inversely by skill count
                    competency_scores[comp_id] = competency_scores.get(comp_id, 0) + weight

        # Apply activity type boost
        activity_boost = self._get_activity_type_competency_boost(activity_type)
        for comp_id, boost in activity_boost.items():
            if comp_id in competency_scores:
                competency_scores[comp_id] *= 1 + boost

        # Normalize scores
        if competency_scores:
            max_score = max(competency_scores.values())
            if max_score > 0:
                competency_scores = {
                    comp_id: score / max_score for comp_id, score in competency_scores.items()
                }

        return competency_scores

    def _get_activity_type_competency_boost(self, activity_type: ActivityType) -> dict[str, float]:
        """Get competency boosts based on activity type"""

        boosts = {
            ActivityType.CODING: {"technical_skills": 0.3, "problem_solving": 0.2},
            ActivityType.DEBUGGING: {"problem_solving": 0.4, "technical_skills": 0.2},
            ActivityType.TESTING: {"quality_assurance": 0.3, "technical_skills": 0.2},
            ActivityType.MENTORING: {"leadership": 0.4, "communication": 0.3},
            ActivityType.PLANNING: {"project_management": 0.3, "leadership": 0.2},
            ActivityType.DOCUMENTATION: {"communication": 0.3, "quality_assurance": 0.2},
            ActivityType.RESEARCH: {"learning_development": 0.3, "innovation": 0.2},
        }

        return boosts.get(activity_type, {})

    def _fallback_activity_mapping(
        self, activity_type: ActivityType, framework: CompetencyFramework
    ) -> dict[str, float]:
        """Fallback mapping based purely on activity type"""

        # Default mappings from ActivityType to competency categories
        type_mappings = {
            ActivityType.CODING: [("technical_skills", 0.8), ("problem_solving", 0.6)],
            ActivityType.DEBUGGING: [("problem_solving", 0.8), ("technical_skills", 0.6)],
            ActivityType.TESTING: [("quality_assurance", 0.8), ("technical_skills", 0.5)],
            ActivityType.MENTORING: [("leadership", 0.8), ("communication", 0.6)],
            ActivityType.PLANNING: [("project_management", 0.8), ("leadership", 0.5)],
            ActivityType.DOCUMENTATION: [("communication", 0.8), ("quality_assurance", 0.4)],
            ActivityType.RESEARCH: [("learning_development", 0.8), ("innovation", 0.5)],
        }

        mappings = type_mappings.get(activity_type, [("technical_skills", 0.5)])

        # Filter to existing competencies in framework
        available_comps = set(framework.competencies.keys())

        result = {}
        for comp_id, weight in mappings:
            if comp_id in available_comps:
                result[comp_id] = weight

        # Fallback to first available competency
        if not result and available_comps:
            result[list(available_comps)[0]] = 0.5

        return result

    def _select_competencies(
        self, competency_scores: dict[str, float]
    ) -> tuple[str, float, list[dict[str, Any]]]:
        """Select primary and secondary competencies from scores"""

        if not competency_scores:
            return "technical_skills", 0.5, []

        # Sort by score
        sorted_comps = sorted(competency_scores.items(), key=lambda x: x[1], reverse=True)

        # Primary competency
        primary_comp, primary_score = sorted_comps[0]

        # Secondary competencies (top 3, excluding primary)
        secondary_comps = []
        for comp_id, score in sorted_comps[1:4]:
            if score > 0.2:  # Minimum threshold for secondary
                secondary_comps.append({"competency_id": comp_id, "weight": score})

        return primary_comp, primary_score, secondary_comps

    def _calculate_mapping_confidence(
        self,
        skill_extraction: SkillExtraction,
        competency_mappings: dict[str, float],
        activity_type: ActivityType,
    ) -> float:
        """Calculate overall mapping confidence"""

        confidence = 0.0

        # Base confidence from skill extraction
        if skill_extraction.matched_count > 0:
            extraction_conf = skill_extraction.matched_count / max(
                skill_extraction.total_available, 1
            )
            confidence += min(extraction_conf, 0.4)

        # Average skill confidence
        if skill_extraction.confidence_scores:
            avg_skill_conf = sum(skill_extraction.confidence_scores.values()) / len(
                skill_extraction.confidence_scores
            )
            confidence += avg_skill_conf * 0.3

        # Competency mapping strength
        if competency_mappings:
            max_comp_score = max(competency_mappings.values())
            confidence += max_comp_score * 0.3

        return min(confidence, 1.0)

    def _load_default_framework(self):
        """Load default competency framework"""

        # Create minimal default framework
        default_framework = self._create_default_framework()
        self._frameworks[default_framework.framework_id] = default_framework
        self._default_framework_id = default_framework.framework_id

    def _create_default_framework(self) -> CompetencyFramework:
        """Create default ReflectAI competency framework"""

        competencies = {
            "technical_skills": {
                "name": "Technical Skills",
                "description": "Programming, system design, and technical problem-solving abilities",
                "skills": [
                    "python",
                    "javascript",
                    "system_design",
                    "database_management",
                    "cloud_platforms",
                ],
            },
            "leadership": {
                "name": "Leadership",
                "description": "Ability to lead teams, make decisions, and drive initiatives",
                "skills": [
                    "team_management",
                    "decision_making",
                    "strategic_thinking",
                    "conflict_resolution",
                ],
            },
            "communication": {
                "name": "Communication",
                "description": "Ability to communicate effectively with team members and stakeholders",
                "skills": [
                    "technical_writing",
                    "presentation",
                    "stakeholder_management",
                    "documentation",
                ],
            },
            "problem_solving": {
                "name": "Problem Solving",
                "description": "Analytical thinking and troubleshooting capabilities",
                "skills": [
                    "debugging",
                    "root_cause_analysis",
                    "critical_thinking",
                    "algorithm_design",
                ],
            },
            "learning_development": {
                "name": "Learning & Development",
                "description": "Continuous learning and knowledge sharing abilities",
                "skills": ["research", "knowledge_sharing", "mentoring", "continuous_learning"],
            },
        }

        skills = {
            "python": {
                "name": "Python",
                "description": "Python programming language proficiency",
                "keywords": ["python", "django", "flask", "pandas", "numpy"],
                "patterns": [r"\bpython\b", r"\bdjango\b", r"\bflask\b"],
            },
            "javascript": {
                "name": "JavaScript",
                "description": "JavaScript programming language proficiency",
                "keywords": ["javascript", "js", "node", "react", "vue", "angular"],
                "patterns": [r"\bjavascript\b", r"\bnode\.js\b", r"\breact\b"],
            },
            "system_design": {
                "name": "System Design",
                "description": "Ability to design scalable software systems",
                "keywords": ["system design", "architecture", "scalability", "microservices"],
                "patterns": [r"\barchitecture\b", r"\bmicroservices\b", r"\bscalability\b"],
            },
            "team_management": {
                "name": "Team Management",
                "description": "Leading and managing software teams",
                "keywords": ["team lead", "management", "leadership", "scrum master"],
                "patterns": [r"\bteam\s+lead\b", r"\bmanagement\b", r"\bleadership\b"],
            },
            "technical_writing": {
                "name": "Technical Writing",
                "description": "Creating clear technical documentation",
                "keywords": ["documentation", "technical writing", "specs", "readme"],
                "patterns": [r"\bdocumentation\b", r"\btechnical\s+writing\b"],
            },
        }

        levels = {
            "1": {"name": "Novice", "description": "Learning the basics"},
            "2": {"name": "Beginner", "description": "Can perform simple tasks with guidance"},
            "3": {"name": "Intermediate", "description": "Can work independently on routine tasks"},
            "4": {"name": "Advanced", "description": "Can handle complex tasks and guide others"},
            "5": {"name": "Expert", "description": "Recognized expert who can innovate and lead"},
        }

        return CompetencyFramework(
            framework_id="reflectai_default",
            name="ReflectAI Default Framework",
            version="1.0",
            description="Default competency framework for software engineering roles",
            organization="ReflectAI",
            competencies=competencies,
            skills=skills,
            levels=levels,
            roles={
                "software_engineer": ["technical_skills", "problem_solving", "communication"],
                "senior_engineer": [
                    "technical_skills",
                    "problem_solving",
                    "communication",
                    "leadership",
                ],
                "tech_lead": ["leadership", "technical_skills", "communication", "problem_solving"],
            },
        )

    def _create_minimal_framework(self) -> CompetencyFramework:
        """Create minimal framework for fallback scenarios"""

        return CompetencyFramework(
            framework_id="minimal_fallback",
            name="Minimal Fallback Framework",
            version="1.0",
            description="Minimal framework for fallback scenarios",
            competencies={
                "technical_skills": {
                    "name": "Technical Skills",
                    "description": "Basic technical competency",
                }
            },
            skills={"general": {"name": "General", "description": "General skill"}},
            levels={"1": {"name": "Basic", "description": "Basic level"}},
        )

    def _build_mapping_rules(self):
        """Build competency mapping rules"""

        self._mapping_rules = [
            CompetencyRule(
                activity_types=[ActivityType.CODING, ActivityType.DEBUGGING],
                competency_id="technical_skills",
                weight=0.8,
                keywords=["code", "programming", "debug", "implement"],
                skill_indicators=["python", "javascript", "java"],
            ),
            CompetencyRule(
                activity_types=[ActivityType.MENTORING, ActivityType.PLANNING],
                competency_id="leadership",
                weight=0.7,
                keywords=["mentor", "lead", "plan", "manage"],
                skill_indicators=["team_management", "strategic_thinking"],
            ),
        ]

    def _update_stats(self, confidence: float, extraction_success: bool):
        """Update mapper statistics"""

        self._stats["total_mappings"] += 1

        if extraction_success:
            self._stats["successful_extractions"] += 1

        # Update average confidence
        total = self._stats["total_mappings"]
        current_avg = self._stats["average_confidence"]
        self._stats["average_confidence"] = ((current_avg * (total - 1)) + confidence) / total

    def get_mapper_stats(self) -> dict[str, Any]:
        """Get competency mapper statistics"""
        return self._stats.copy()


# Global mapper instance
_global_mapper: CompetencyMapper | None = None


def get_competency_mapper(frameworks_directory: str | None = None) -> CompetencyMapper:
    """Get global competency mapper instance"""
    global _global_mapper
    if _global_mapper is None:
        _global_mapper = CompetencyMapper(frameworks_directory)
    return _global_mapper
