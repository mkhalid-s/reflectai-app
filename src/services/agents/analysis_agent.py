"""
Combined Analysis Agent for ReflectAI

Combines data analysis and competency assessment capabilities into a single
efficient agent as specified in Phase 1 simplifications.

Capabilities:
- Activity classification and pattern detection (from DataAnalyst)
- Competency assessment and skill evaluation (from CompetencySpecialist)
- Trend analysis and growth trajectory mapping
- Gap analysis and recommendations
"""

import json
from datetime import UTC, datetime
from typing import Any

from src.shared.logging import get_logger

from .base import AgentCapability, AgentRequest, BaseAgent

logger = get_logger(__name__)


class AnalysisAgent(BaseAgent):
    """
    Combined Analysis Agent specialized in data analysis and competency assessment.

    This agent combines the functionality of DataAnalyst and CompetencySpecialist
    to reduce system complexity and improve efficiency per Phase 1 specifications.

    Capabilities:
    - Activity classification and pattern detection
    - Competency assessment and skill evaluation
    - Trend analysis over time
    - Gap analysis and growth planning
    """

    def __init__(self):
        super().__init__(
            name="AnalysisAgent",
            description="Combined expert at analyzing activities and assessing competencies",
            capabilities=[
                AgentCapability.ANALYSIS,
                AgentCapability.ASSESSMENT,
                AgentCapability.RESEARCH,
                AgentCapability.PLANNING,
            ],
        )

        # Competency framework (from CompetencySpecialist)
        self.competency_framework = {
            "technical": [
                "Programming",
                "Architecture",
                "Debugging",
                "Testing",
                "DevOps",
                "Security",
                "Performance",
                "Documentation",
            ],
            "leadership": [
                "Team Management",
                "Mentoring",
                "Decision Making",
                "Strategic Planning",
                "Conflict Resolution",
                "Delegation",
            ],
            "communication": [
                "Presentation",
                "Writing",
                "Active Listening",
                "Stakeholder Management",
                "Negotiation",
                "Facilitation",
            ],
            "analytical": [
                "Problem Solving",
                "Data Analysis",
                "Critical Thinking",
                "Research",
                "Innovation",
                "Process Improvement",
            ],
        }

        # Register combined tools
        self.register_tool("classify_activity", self._classify_activity)
        self.register_tool("assess_competencies", self._assess_competencies)
        self.register_tool("analyze_patterns", self._analyze_patterns)
        self.register_tool("analyze_trends", self._analyze_trends)
        self.register_tool("gap_analysis", self._gap_analysis)
        self.register_tool("comprehensive_analysis", self._comprehensive_analysis)

    async def _run(self, request: AgentRequest) -> dict[str, Any]:
        """
        Execute combined analysis task.

        This method intelligently routes to the appropriate analysis type
        or performs comprehensive analysis combining multiple capabilities.

        Args:
            request: The analysis request

        Returns:
            Combined analysis results
        """
        task = request.task.lower()
        context = request.context

        # Route to appropriate analysis method
        if "classify" in task:
            return await self._perform_classification(request.task, context, request.user_id)
        elif "assess" in task or "competenc" in task:
            return await self._perform_competency_assessment(context, request.user_id)
        elif "pattern" in task:
            return await self._perform_pattern_analysis(request.task, context, request.user_id)
        elif "trend" in task:
            return await self._perform_trend_analysis(request.task, context, request.user_id)
        elif "gap" in task:
            return await self._perform_gap_analysis(context, request.user_id)
        elif "comprehensive" in task or "full" in task:
            return await self._perform_comprehensive_analysis(context, request.user_id)
        else:
            # Default to combined analysis
            return await self._perform_combined_analysis(request.task, context, request.user_id)

    async def _perform_classification(
        self, task: str, context: dict[str, Any], user_id: str | None = None
    ) -> dict[str, Any]:
        """Perform activity classification with competency mapping."""
        activity_text = context.get("activity_text", task)
        user_profile = context.get("user_profile", {})

        # Combined prompt that does both classification AND competency mapping
        prompt = f"""Analyze this workplace activity for both classification and competencies:

Activity: {activity_text}
User Profile: {json.dumps(user_profile, indent=2)}

Competency Framework:
{json.dumps(self.competency_framework, indent=2)}

Provide a comprehensive JSON response with:
{{
    "classification": {{
        "primary_category": "category name",
        "secondary_categories": ["category1", "category2"],
        "confidence": 0.0-1.0,
        "evidence": ["reason1", "reason2"]
    }},
    "competencies": {{
        "identified_skills": ["skill1", "skill2"],
        "competency_mapping": {{
            "technical": ["Programming", "Testing"],
            "leadership": ["Decision Making"],
            "communication": [],
            "analytical": ["Problem Solving"]
        }},
        "skill_level_demonstrated": {{
            "Programming": 7,
            "Testing": 6,
            "Decision Making": 5
        }}
    }},
    "insights": {{
        "complexity_level": "beginner/intermediate/advanced/expert",
        "growth_indicators": ["indicator1", "indicator2"],
        "development_opportunities": ["opportunity1", "opportunity2"]
    }}
}}

Categories: technical, leadership, communication, planning, learning, administrative"""

        response = await self.think(prompt, require_json=True, user_id=context.get("user_id"))

        try:
            analysis = json.loads(response)
        except json.JSONDecodeError:
            analysis = {
                "classification": {"primary_category": "unknown", "confidence": 0.5},
                "competencies": {},
                "raw_response": response,
            }

        # Store combined result
        await self.remember(f"analysis:{hash(activity_text)}", analysis, ttl=3600)

        return {
            "analysis": analysis,
            "activity": activity_text,
            "timestamp": datetime.now(UTC).isoformat(),
            "type": "classification_with_competency",
        }

    async def _perform_competency_assessment(self, context: dict[str, Any]) -> dict[str, Any]:
        """Perform comprehensive competency assessment."""
        activities = context.get("activities", [])
        user_profile = context.get("user_profile", {})

        # Prepare activities summary
        activities_summary = self._summarize_activities(activities)

        prompt = f"""Perform comprehensive competency assessment:

Activities Summary:
{activities_summary}

User Profile: {json.dumps(user_profile, indent=2)}

Competency Framework:
{json.dumps(self.competency_framework, indent=2)}

Provide detailed JSON assessment:
{{
    "competency_scores": {{
        "technical": {{"Programming": 0-10, "Architecture": 0-10, ...}},
        "leadership": {{"Team Management": 0-10, "Mentoring": 0-10, ...}},
        "communication": {{"Presentation": 0-10, "Writing": 0-10, ...}},
        "analytical": {{"Problem Solving": 0-10, "Data Analysis": 0-10, ...}}
    }},
    "assessment_summary": {{
        "top_strengths": ["strength1", "strength2", "strength3"],
        "areas_for_improvement": ["area1", "area2", "area3"],
        "overall_level": "Junior/Mid/Senior/Lead/Principal",
        "confidence": 0.0-1.0,
        "evidence_quality": "weak/moderate/strong"
    }},
    "growth_indicators": {{
        "trending_up": ["skill1", "skill2"],
        "trending_down": ["skill3"],
        "stable": ["skill4", "skill5"]
    }},
    "recommendations": {{
        "immediate_focus": ["priority1", "priority2"],
        "medium_term_goals": ["goal1", "goal2"],
        "certifications": ["cert1", "cert2"]
    }}
}}"""

        response = await self.think(prompt, require_json=True, user_id=context.get("user_id"))

        try:
            assessment = json.loads(response)
        except json.JSONDecodeError:
            assessment = self._get_default_assessment()

        # Calculate overall score
        assessment["overall_score"] = self._calculate_overall_score(
            assessment.get("competency_scores", {})
        )

        # Store assessment
        if user_id := context.get("user_id"):
            await self.remember(f"assessment:{user_id}", assessment, ttl=86400)

        return {
            "assessment": assessment,
            "activity_count": len(activities),
            "timestamp": datetime.now(UTC).isoformat(),
            "type": "competency_assessment",
        }

    async def _perform_pattern_analysis(self, task: str, context: dict[str, Any]) -> dict[str, Any]:
        """Detect patterns with competency implications."""
        activities = context.get("activities", [])

        if not activities:
            return {"patterns": [], "message": "No activities provided for pattern analysis"}

        activities_text = "\n".join(
            [
                f"- {act.get('type', 'unknown')}: {act.get('description', '')}"
                for act in activities[:50]  # Limit for context
            ]
        )

        prompt = f"""Analyze patterns with competency development insights:

Activities:
{activities_text}

Identify:
1. Recurring work patterns and behaviors
2. Skill progression and competency development patterns
3. Time-based patterns and productivity cycles
4. Collaboration and leadership patterns
5. Areas of focus and specialization trends
6. Competency gaps revealed by activity patterns
7. Growth opportunities indicated by patterns

Provide insights about professional development trajectory."""

        response = await self.think(prompt, user_id=context.get("user_id"))

        return {
            "patterns": response,
            "activity_count": len(activities),
            "analysis_depth": min(len(activities), 50),
            "timestamp": datetime.now(UTC).isoformat(),
            "type": "pattern_analysis",
        }

    async def _perform_trend_analysis(self, task: str, context: dict[str, Any]) -> dict[str, Any]:
        """Analyze trends with competency progression."""
        activities = context.get("activities", [])
        time_period = context.get("time_period", "30_days")

        # Group activities by time and competency
        time_buckets = self._bucket_activities_by_time(activities, time_period)
        competency_trends = self._analyze_competency_trends(activities)

        prompt = f"""Analyze trends with competency development focus:

Activity Distribution Over {time_period}:
{json.dumps(time_buckets, indent=2)}

Competency Trends:
{json.dumps(competency_trends, indent=2)}

Analyze:
1. Growth or decline in specific competency areas
2. Emerging skills and capabilities
3. Changes in work complexity and responsibility
4. Productivity and quality trends
5. Professional development trajectory
6. Skill utilization patterns
7. Recommendations for accelerated growth"""

        response = await self.think(prompt, user_id=context.get("user_id"))

        return {
            "trends": response,
            "time_period": time_period,
            "data_points": len(time_buckets),
            "competency_trends": competency_trends,
            "timestamp": datetime.now(UTC).isoformat(),
            "type": "trend_analysis",
        }

    async def _perform_gap_analysis(self, context: dict[str, Any]) -> dict[str, Any]:
        """Perform skill gap analysis."""
        current_competencies = context.get("current_competencies", {})
        target_role = context.get("target_role", "Senior Developer")
        activities = context.get("activities", [])

        # If no current competencies provided, assess from activities
        if not current_competencies and activities:
            assessment_result = await self._perform_competency_assessment(context)
            current_competencies = assessment_result.get("assessment", {}).get(
                "competency_scores", {}
            )

        prompt = f"""Perform comprehensive gap analysis:

Current Competencies: {json.dumps(current_competencies, indent=2)}
Target Role: {target_role}
Recent Activities: {len(activities)} activities analyzed

Required Competencies for {target_role}:
{json.dumps(self.competency_framework, indent=2)}

Provide detailed gap analysis:
{{
    "critical_gaps": [
        {{
            "competency": "skill_name",
            "current_level": 0-10,
            "required_level": 0-10,
            "gap_size": "small/medium/large",
            "priority": "high/medium/low",
            "estimated_time": "weeks/months"
        }}
    ],
    "development_plan": {{
        "immediate_actions": ["action1", "action2"],
        "3_month_goals": ["goal1", "goal2"],
        "6_month_goals": ["goal1", "goal2"],
        "learning_resources": ["resource1", "resource2"],
        "practical_experiences": ["experience1", "experience2"]
    }},
    "career_readiness": {{
        "overall_readiness": "0-100%",
        "key_blockers": ["blocker1", "blocker2"],
        "quick_wins": ["win1", "win2"],
        "timeline_estimate": "months to role readiness"
    }}
}}"""

        response = await self.think(prompt, require_json=True, user_id=context.get("user_id"))

        try:
            gap_analysis = json.loads(response)
        except json.JSONDecodeError:
            gap_analysis = {"error": "Failed to parse gap analysis", "raw_response": response}

        return {
            "gap_analysis": gap_analysis,
            "target_role": target_role,
            "current_level": self._assess_current_level(current_competencies),
            "timestamp": datetime.now(UTC).isoformat(),
            "type": "gap_analysis",
        }

    async def _perform_comprehensive_analysis(self, context: dict[str, Any]) -> dict[str, Any]:
        """Perform comprehensive combined analysis."""
        # This combines classification, assessment, patterns, trends, and gaps
        activities = context.get("activities", [])

        # Perform multiple analysis types in sequence
        results = {}

        # 1. Competency Assessment
        if activities:
            assessment = await self._perform_competency_assessment(context)
            results["competency_assessment"] = assessment

            # Use assessment results for gap analysis
            current_competencies = assessment.get("assessment", {}).get("competency_scores", {})
            context["current_competencies"] = current_competencies

        # 2. Pattern Analysis
        if activities:
            patterns = await self._perform_pattern_analysis("analyze patterns", context)
            results["pattern_analysis"] = patterns

        # 3. Trend Analysis
        if activities:
            trends = await self._perform_trend_analysis("analyze trends", context)
            results["trend_analysis"] = trends

        # 4. Gap Analysis (if target role provided)
        if context.get("target_role"):
            gaps = await self._perform_gap_analysis(context)
            results["gap_analysis"] = gaps

        # 5. Generate summary insights
        summary = await self._generate_comprehensive_summary(results, context)
        results["executive_summary"] = summary

        return {
            "comprehensive_analysis": results,
            "timestamp": datetime.now(UTC).isoformat(),
            "type": "comprehensive_analysis",
        }

    async def _perform_combined_analysis(
        self, task: str, context: dict[str, Any]
    ) -> dict[str, Any]:
        """Perform combined analysis for general requests."""
        prompt = f"""Perform combined data analysis and competency assessment:

Task: {task}
Context: {json.dumps(context, indent=2)}

Competency Framework:
{json.dumps(self.competency_framework, indent=2)}

Provide comprehensive analysis combining:
1. Data insights and patterns
2. Competency implications
3. Skill development opportunities
4. Professional growth recommendations
5. Actionable next steps

Focus on practical, actionable insights for professional development."""

        response = await self.think(prompt, user_id=context.get("user_id"))

        return {
            "analysis": response,
            "task": task,
            "timestamp": datetime.now(UTC).isoformat(),
            "type": "combined_analysis",
        }

    async def _generate_comprehensive_summary(
        self, results: dict[str, Any], context: dict[str, Any]
    ) -> dict[str, Any]:
        """Generate executive summary of comprehensive analysis."""
        prompt = f"""Generate executive summary from comprehensive analysis:

Analysis Results:
{json.dumps(results, indent=2)}

Context:
{json.dumps(context, indent=2)}

Provide concise executive summary with:
{{
    "key_findings": ["finding1", "finding2", "finding3"],
    "competency_highlights": {{
        "top_strengths": ["strength1", "strength2"],
        "priority_gaps": ["gap1", "gap2"]
    }},
    "recommendations": {{
        "immediate": ["action1", "action2"],
        "short_term": ["goal1", "goal2"],
        "long_term": ["objective1", "objective2"]
    }},
    "success_metrics": ["metric1", "metric2"],
    "confidence_level": 0.0-1.0
}}"""

        response = await self.think(prompt, require_json=True, user_id=context.get("user_id"))

        try:
            return json.loads(response)
        except json.JSONDecodeError:
            return {"summary": response, "type": "text"}

    # Tool implementations
    async def _classify_activity(
        self, activity_text: str, user_profile: dict[str, Any] = None
    ) -> dict[str, Any]:
        """Tool: Classify activity with competency mapping."""
        return await self._perform_classification(
            activity_text, {"activity_text": activity_text, "user_profile": user_profile or {}}
        )

    async def _assess_competencies(
        self, activities: list[dict[str, Any]], user_profile: dict[str, Any] = None
    ) -> dict[str, Any]:
        """Tool: Assess competencies from activities."""
        return await self._perform_competency_assessment(
            {"activities": activities, "user_profile": user_profile or {}}
        )

    async def _analyze_patterns(self, activities: list[dict[str, Any]]) -> dict[str, Any]:
        """Tool: Analyze patterns with competency insights."""
        return await self._perform_pattern_analysis("analyze patterns", {"activities": activities})

    async def _analyze_trends(
        self, activities: list[dict[str, Any]], time_period: str = "30_days"
    ) -> dict[str, Any]:
        """Tool: Analyze trends with competency progression."""
        return await self._perform_trend_analysis(
            "analyze trends", {"activities": activities, "time_period": time_period}
        )

    async def _gap_analysis(
        self, current_competencies: dict[str, Any], target_role: str
    ) -> dict[str, Any]:
        """Tool: Perform gap analysis."""
        return await self._perform_gap_analysis(
            {"current_competencies": current_competencies, "target_role": target_role}
        )

    async def _comprehensive_analysis(
        self,
        activities: list[dict[str, Any]],
        user_profile: dict[str, Any] = None,
        target_role: str = None,
    ) -> dict[str, Any]:
        """Tool: Perform comprehensive combined analysis."""
        return await self._perform_comprehensive_analysis(
            {
                "activities": activities,
                "user_profile": user_profile or {},
                "target_role": target_role,
            }
        )

    # Helper methods
    def _summarize_activities(self, activities: list[dict[str, Any]]) -> str:
        """Summarize activities for assessment."""
        if not activities:
            return "No activities provided"

        summary = []
        for i, activity in enumerate(activities[:30], 1):  # Limit to 30
            activity_type = activity.get("type", "unknown")
            description = activity.get("description", "")
            date = activity.get("date", "")

            summary.append(f"{i}. [{activity_type}] {description} ({date})")

        return "\n".join(summary)

    def _calculate_overall_score(self, competency_scores: dict[str, Any]) -> float:
        """Calculate overall competency score."""
        total_score = 0
        total_count = 0

        for _category, skills in competency_scores.items():
            if isinstance(skills, dict):
                for _skill, score in skills.items():
                    if isinstance(score, (int, float)):
                        total_score += score
                        total_count += 1

        return round(total_score / total_count, 2) if total_count > 0 else 0.0

    def _bucket_activities_by_time(
        self, activities: list[dict[str, Any]], period: str
    ) -> dict[str, int]:
        """Group activities into time buckets."""
        buckets = {}

        for activity in activities:
            activity_type = activity.get("type", "unknown")
            if activity_type not in buckets:
                buckets[activity_type] = 0
            buckets[activity_type] += 1

        return buckets

    def _analyze_competency_trends(self, activities: list[dict[str, Any]]) -> dict[str, Any]:
        """Analyze competency trends in activities."""
        competency_counts = dict.fromkeys(self.competency_framework.keys(), 0)

        # Simple trend analysis - count activities by competency category
        for activity in activities:
            activity_type = activity.get("type", "").lower()

            if any(tech in activity_type for tech in ["code", "program", "debug", "test"]):
                competency_counts["technical"] += 1
            elif any(lead in activity_type for lead in ["lead", "manage", "mentor"]):
                competency_counts["leadership"] += 1
            elif any(comm in activity_type for comm in ["present", "write", "meet"]):
                competency_counts["communication"] += 1
            elif any(anal in activity_type for anal in ["analyze", "research", "solve"]):
                competency_counts["analytical"] += 1

        return competency_counts

    def _assess_current_level(self, competencies: dict[str, Any]) -> str:
        """Assess current professional level from competencies."""
        if not competencies:
            return "Unknown"

        avg_score = self._calculate_overall_score(competencies)

        if avg_score >= 8.0:
            return "Principal/Staff"
        elif avg_score >= 7.0:
            return "Senior"
        elif avg_score >= 5.0:
            return "Mid-level"
        elif avg_score >= 3.0:
            return "Junior"
        else:
            return "Entry-level"

    def _get_default_assessment(self) -> dict[str, Any]:
        """Get default assessment structure."""
        return {
            "competency_scores": {},
            "assessment_summary": {
                "top_strengths": [],
                "areas_for_improvement": [],
                "overall_level": "Unknown",
                "confidence": 0.0,
            },
            "growth_indicators": {"trending_up": [], "trending_down": [], "stable": []},
            "recommendations": {
                "immediate_focus": [],
                "medium_term_goals": [],
                "certifications": [],
            },
        }
