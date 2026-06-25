"""
Resource Finder Tool for Advisor Agent

Implements resource finding part of
- Find external learning resources and opportunities
- Course recommendations, certifications, conferences, books
- Integration with skill gaps and career goals
- Content curation and relevance scoring

Used by Advisor Agent for discovering relevant learning resources.
"""

from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from ..base_tool import Tool, ToolError, ToolPermission, ToolRequest


class ResourceType(Enum):
    """Types of learning resources"""

    COURSE = "course"
    BOOK = "book"
    CERTIFICATION = "certification"
    CONFERENCE = "conference"
    WORKSHOP = "workshop"
    ARTICLE = "article"
    VIDEO = "video"
    PODCAST = "podcast"
    TUTORIAL = "tutorial"
    DOCUMENTATION = "documentation"
    PROJECT = "project"
    MENTOR = "mentor"


class ResourceFormat(Enum):
    """Resource delivery formats"""

    ONLINE = "online"
    IN_PERSON = "in_person"
    HYBRID = "hybrid"
    SELF_PACED = "self_paced"
    LIVE = "live"
    RECORDED = "recorded"


class ResourceLevel(Enum):
    """Resource difficulty/experience levels"""

    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"
    ALL_LEVELS = "all_levels"


class ResourceRequest(BaseModel):
    """Request for finding resources"""

    skills: list[str] = Field(..., description="Skills to find resources for")
    resource_types: list[ResourceType] | None = Field(
        None, description="Types of resources to find"
    )
    formats: list[ResourceFormat] | None = Field(None, description="Preferred resource formats")
    level: ResourceLevel | None = Field(None, description="Target skill level")
    max_cost: float | None = Field(None, description="Maximum cost filter")
    max_duration: int | None = Field(None, description="Maximum duration in hours")
    free_only: bool = Field(False, description="Only show free resources")
    recent_only: bool = Field(False, description="Only show recent resources (last 2 years)")
    max_results: int = Field(20, description="Maximum number of results")
    user_preferences: dict[str, Any] | None = Field(
        None, description="User preferences and history"
    )


class LearningResource(BaseModel):
    """Individual learning resource"""

    id: str = Field(..., description="Unique resource ID")
    title: str = Field(..., description="Resource title")
    description: str = Field(..., description="Resource description")
    type: ResourceType = Field(..., description="Type of resource")
    format: ResourceFormat = Field(..., description="Delivery format")
    level: ResourceLevel = Field(..., description="Target skill level")

    # Provider information
    provider: str = Field(..., description="Resource provider/author")
    url: str | None = Field(None, description="Resource URL")

    # Metadata
    skills_covered: list[str] = Field(..., description="Skills covered by this resource")
    duration_hours: float | None = Field(None, description="Estimated duration in hours")
    cost: float | None = Field(None, description="Cost in USD (0 for free)")
    language: str = Field("English", description="Primary language")
    published_date: datetime | None = Field(None, description="Publication/creation date")

    # Quality indicators
    rating: float | None = Field(None, description="Average rating (0-5)")
    num_reviews: int | None = Field(None, description="Number of reviews")
    completion_rate: float | None = Field(None, description="Completion rate for courses")

    # Relevance scoring
    relevance_score: float = Field(..., description="Relevance score for user query (0-1)")
    match_reasons: list[str] = Field(default_factory=list, description="Why this resource matches")

    # Requirements and outcomes
    prerequisites: list[str] = Field(default_factory=list, description="Prerequisites")
    learning_outcomes: list[str] = Field(
        default_factory=list, description="Expected learning outcomes"
    )

    # Additional metadata
    tags: list[str] = Field(default_factory=list, description="Resource tags")
    difficulty_indicators: dict[str, Any] = Field(
        default_factory=dict, description="Difficulty indicators"
    )


class ResourceResult(BaseModel):
    """Result of resource finding"""

    query_skills: list[str] = Field(..., description="Skills that were searched")
    total_found: int = Field(..., description="Total resources found")
    resources: list[LearningResource] = Field(..., description="Found resources")

    # Search metadata
    search_time: float = Field(..., description="Time taken to search")
    filters_applied: dict[str, Any] = Field(
        default_factory=dict, description="Filters that were applied"
    )

    # Aggregated insights
    resource_type_distribution: dict[str, int] = Field(
        default_factory=dict, description="Distribution by type"
    )
    cost_analysis: dict[str, Any] = Field(default_factory=dict, description="Cost analysis")
    provider_distribution: dict[str, int] = Field(
        default_factory=dict, description="Distribution by provider"
    )


class ResourceFinderTool(Tool):
    """
    Tool for finding external learning resources and opportunities

    Searches curated database of learning resources and provides personalized
    recommendations based on skill gaps and career goals.
    """

    def __init__(self):
        super().__init__(
            name="resource_finder",
            description="Find external learning resources including courses, books, certifications, and conferences",
            required_permissions=[ToolPermission.READ_ONLY],
            timeout=30,
        )

        # Resource database (simplified - in production would be external APIs/databases)
        self._resource_database = self._build_resource_database()

        # Skill-to-resource mappings
        self._skill_mappings = self._build_skill_mappings()

    async def _execute_operation(
        self, request: ToolRequest, agent_context: Any | None = None
    ) -> ResourceResult:
        """Execute resource finding operation"""

        if request.operation != "find_resources":
            raise ToolError(
                message=f"Unknown operation: {request.operation}",
                tool_name=self.name,
                operation=request.operation,
            )

        # Parse request parameters
        try:
            resource_request = ResourceRequest(**request.parameters)
        except Exception as e:
            raise ToolError(
                message=f"Invalid request parameters: {str(e)}",
                tool_name=self.name,
                operation=request.operation,
            ) from e

        start_time = datetime.now(UTC)

        try:
            # Find resources
            resources = await self._find_matching_resources(resource_request)

            # Score and rank resources
            scored_resources = self._score_and_rank_resources(resources, resource_request)

            # Apply final filtering and limits
            final_resources = scored_resources[: resource_request.max_results]

            # Generate analytics
            search_time = (datetime.now(UTC) - start_time).total_seconds()
            analytics = self._generate_search_analytics(final_resources, resource_request)

            return ResourceResult(
                query_skills=resource_request.skills,
                total_found=len(final_resources),
                resources=final_resources,
                search_time=search_time,
                filters_applied=self._get_applied_filters(resource_request),
                **analytics,
            )

        except Exception as e:
            raise ToolError(
                message=f"Resource search failed: {str(e)}",
                tool_name=self.name,
                operation=request.operation,
                details={"skills": resource_request.skills},
            ) from e

    async def _find_matching_resources(self, request: ResourceRequest) -> list[LearningResource]:
        """Find resources matching the request criteria"""

        matching_resources = []

        for resource in self._resource_database:
            # Check skill match
            skill_match = any(
                skill.lower() in [s.lower() for s in resource.skills_covered]
                for skill in request.skills
            )

            if not skill_match:
                continue

            # Apply filters
            if not self._passes_filters(resource, request):
                continue

            matching_resources.append(resource)

        return matching_resources

    def _passes_filters(self, resource: LearningResource, request: ResourceRequest) -> bool:
        """Check if resource passes the request filters"""

        # Resource type filter
        if request.resource_types and resource.type not in request.resource_types:
            return False

        # Format filter
        if request.formats and resource.format not in request.formats:
            return False

        # Level filter
        if (
            request.level
            and resource.level != request.level
            and resource.level != ResourceLevel.ALL_LEVELS
        ):
            return False

        # Cost filters
        if request.free_only and (resource.cost is None or resource.cost > 0):
            return False

        if (
            request.max_cost is not None
            and resource.cost is not None
            and resource.cost > request.max_cost
        ):
            return False

        # Duration filter
        if request.max_duration is not None and resource.duration_hours is not None:
            if resource.duration_hours > request.max_duration:
                return False

        # Recent only filter
        if request.recent_only and resource.published_date:
            cutoff_date = datetime.now(UTC).replace(year=datetime.now(UTC).year - 2)
            if resource.published_date < cutoff_date:
                return False

        return True

    def _score_and_rank_resources(
        self, resources: list[LearningResource], request: ResourceRequest
    ) -> list[LearningResource]:
        """Score and rank resources by relevance"""

        for resource in resources:
            score = 0.0
            match_reasons = []

            # Skill matching score
            matched_skills = [
                skill
                for skill in request.skills
                if any(
                    skill.lower() in covered_skill.lower()
                    for covered_skill in resource.skills_covered
                )
            ]
            skill_score = len(matched_skills) / len(request.skills)
            score += skill_score * 0.4

            if matched_skills:
                match_reasons.append(
                    f"Covers {len(matched_skills)} of {len(request.skills)} requested skills"
                )

            # Quality indicators
            if resource.rating:
                rating_score = resource.rating / 5.0
                score += rating_score * 0.2
                match_reasons.append(f"High rating ({resource.rating}/5.0)")

            if resource.num_reviews and resource.num_reviews > 10:
                review_score = min(resource.num_reviews / 1000, 1.0)
                score += review_score * 0.1
                if resource.num_reviews > 100:
                    match_reasons.append(f"Well-reviewed ({resource.num_reviews} reviews)")

            # Completion rate for courses
            if resource.completion_rate:
                completion_score = resource.completion_rate
                score += completion_score * 0.1
                if resource.completion_rate > 0.7:
                    match_reasons.append(f"High completion rate ({resource.completion_rate:.1%})")

            # Recency bonus
            if resource.published_date:
                days_old = (datetime.now(UTC) - resource.published_date).days
                if days_old < 365:
                    recency_score = max(0, (365 - days_old) / 365) * 0.1
                    score += recency_score
                    if days_old < 180:
                        match_reasons.append("Recently published")

            # Free resources get small bonus
            if resource.cost == 0:
                score += 0.05
                match_reasons.append("Free resource")

            # User preference matching
            if request.user_preferences:
                pref_score = self._calculate_preference_score(resource, request.user_preferences)
                score += pref_score * 0.05

            resource.relevance_score = min(score, 1.0)
            resource.match_reasons = match_reasons

        # Sort by relevance score
        resources.sort(key=lambda r: r.relevance_score, reverse=True)

        return resources

    def _calculate_preference_score(
        self, resource: LearningResource, preferences: dict[str, Any]
    ) -> float:
        """Calculate preference-based scoring"""

        score = 0.0

        # Preferred providers
        if "preferred_providers" in preferences:
            if resource.provider in preferences["preferred_providers"]:
                score += 0.3

        # Preferred formats
        if "preferred_formats" in preferences:
            if resource.format.value in preferences["preferred_formats"]:
                score += 0.2

        # Learning style preferences
        if "learning_style" in preferences:
            style = preferences["learning_style"]
            if style == "visual" and resource.type in [ResourceType.VIDEO, ResourceType.TUTORIAL]:
                score += 0.2
            elif style == "reading" and resource.type in [
                ResourceType.BOOK,
                ResourceType.ARTICLE,
                ResourceType.DOCUMENTATION,
            ]:
                score += 0.2
            elif style == "interactive" and resource.type in [
                ResourceType.COURSE,
                ResourceType.PROJECT,
                ResourceType.WORKSHOP,
            ]:
                score += 0.2

        return min(score, 1.0)

    def _generate_search_analytics(
        self, resources: list[LearningResource], request: ResourceRequest
    ) -> dict[str, Any]:
        """Generate analytics about the search results"""

        # Resource type distribution
        type_dist = {}
        for resource in resources:
            type_name = resource.type.value
            type_dist[type_name] = type_dist.get(type_name, 0) + 1

        # Provider distribution
        provider_dist = {}
        for resource in resources:
            provider_dist[resource.provider] = provider_dist.get(resource.provider, 0) + 1

        # Cost analysis
        costs = [r.cost for r in resources if r.cost is not None]
        free_count = len([r for r in resources if r.cost == 0])

        cost_analysis = {
            "free_resources": free_count,
            "paid_resources": len(resources) - free_count,
            "avg_cost": sum(costs) / len(costs) if costs else 0,
            "max_cost": max(costs) if costs else 0,
            "min_paid_cost": min([c for c in costs if c > 0]) if [c for c in costs if c > 0] else 0,
        }

        return {
            "resource_type_distribution": type_dist,
            "provider_distribution": provider_dist,
            "cost_analysis": cost_analysis,
        }

    def _get_applied_filters(self, request: ResourceRequest) -> dict[str, Any]:
        """Get summary of filters that were applied"""

        filters = {}

        if request.resource_types:
            filters["resource_types"] = [rt.value for rt in request.resource_types]

        if request.formats:
            filters["formats"] = [f.value for f in request.formats]

        if request.level:
            filters["level"] = request.level.value

        if request.max_cost is not None:
            filters["max_cost"] = request.max_cost

        if request.free_only:
            filters["free_only"] = True

        if request.recent_only:
            filters["recent_only"] = True

        return filters

    def _build_resource_database(self) -> list[LearningResource]:
        """Build sample resource database"""

        # In production, this would connect to external APIs and databases
        resources = []

        # Python resources
        resources.append(
            LearningResource(
                id="python_course_1",
                title="Complete Python Bootcamp",
                description="Comprehensive Python programming course from basics to advanced",
                type=ResourceType.COURSE,
                format=ResourceFormat.ONLINE,
                level=ResourceLevel.BEGINNER,
                provider="Udemy",
                url="https://udemy.com/python-bootcamp",
                skills_covered=[
                    "Python",
                    "Programming Fundamentals",
                    "Object-Oriented Programming",
                ],
                duration_hours=40,
                cost=89.99,
                rating=4.6,
                num_reviews=250000,
                completion_rate=0.68,
                published_date=datetime(2023, 1, 15),
                relevance_score=0.0,
                learning_outcomes=[
                    "Write Python programs from scratch",
                    "Understand OOP principles",
                    "Build web applications with Flask",
                ],
                tags=["python", "beginner", "comprehensive"],
            )
        )

        # System Design resources
        resources.append(
            LearningResource(
                id="sysdesign_book_1",
                title="Designing Data-Intensive Applications",
                description="Deep dive into the principles and practices of data system architecture",
                type=ResourceType.BOOK,
                format=ResourceFormat.SELF_PACED,
                level=ResourceLevel.ADVANCED,
                provider="O'Reilly",
                skills_covered=["System Design", "Database Architecture", "Distributed Systems"],
                duration_hours=30,
                cost=45.00,
                rating=4.8,
                num_reviews=1500,
                published_date=datetime(2017, 3, 1),
                relevance_score=0.0,
                learning_outcomes=[
                    "Design scalable data architectures",
                    "Understand distributed system trade-offs",
                    "Choose appropriate data storage solutions",
                ],
                prerequisites=["Database fundamentals", "Programming experience"],
                tags=["system-design", "advanced", "architecture"],
            )
        )

        # Leadership resources
        resources.append(
            LearningResource(
                id="leadership_course_1",
                title="Engineering Leadership Certificate",
                description="Develop leadership skills specifically for engineering managers",
                type=ResourceType.CERTIFICATION,
                format=ResourceFormat.ONLINE,
                level=ResourceLevel.INTERMEDIATE,
                provider="Stanford Continuing Studies",
                skills_covered=["Leadership", "Team Management", "Strategic Thinking"],
                duration_hours=80,
                cost=2500.00,
                rating=4.7,
                num_reviews=120,
                completion_rate=0.85,
                published_date=datetime(2023, 9, 1),
                relevance_score=0.0,
                learning_outcomes=[
                    "Lead engineering teams effectively",
                    "Make strategic technical decisions",
                    "Develop high-performing teams",
                ],
                prerequisites=["3+ years engineering experience"],
                tags=["leadership", "management", "certification"],
            )
        )

        # Free resources
        resources.append(
            LearningResource(
                id="react_tutorial_1",
                title="React Official Tutorial",
                description="Official React tutorial covering core concepts and modern patterns",
                type=ResourceType.TUTORIAL,
                format=ResourceFormat.ONLINE,
                level=ResourceLevel.BEGINNER,
                provider="React Team",
                url="https://reactjs.org/tutorial",
                skills_covered=["React", "JavaScript", "Frontend Development"],
                duration_hours=8,
                cost=0,
                rating=4.5,
                num_reviews=5000,
                completion_rate=0.72,
                published_date=datetime(2023, 6, 1),
                relevance_score=0.0,
                learning_outcomes=[
                    "Build React applications",
                    "Understand component lifecycle",
                    "Manage state effectively",
                ],
                tags=["react", "frontend", "free", "official"],
            )
        )

        return resources

    def _build_skill_mappings(self) -> dict[str, list[str]]:
        """Build mappings between skills and resource categories"""

        return {
            "python": ["Python", "Programming", "Backend Development"],
            "react": ["React", "Frontend Development", "JavaScript"],
            "system_design": ["System Design", "Architecture", "Scalability"],
            "leadership": ["Leadership", "Management", "Team Building"],
            "machine_learning": ["Machine Learning", "Data Science", "AI"],
        }

    def get_supported_operations(self) -> list[str]:
        """Get list of supported operations"""
        return ["find_resources"]

    def get_resource_types(self) -> list[str]:
        """Get list of supported resource types"""
        return [rt.value for rt in ResourceType]


# Auto-register for tool discovery
ResourceFinderTool._auto_register = True
ResourceFinderTool._category = "advisor"
ResourceFinderTool._version = None  # Version loaded from config
