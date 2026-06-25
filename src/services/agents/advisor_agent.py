"""
Combined Advisor Agent for ReflectAI

Combines career strategy and insight synthesis capabilities into a single
efficient agent as specified in Phase 1 simplifications.

Capabilities:
- Career path planning and strategic advice (from CareerStrategist)
- Multi-source insight synthesis and narrative creation (from InsightSynthesizer)
- Development plan creation and opportunity identification
- Coherent professional storytelling and recommendation generation
"""

import json
from datetime import UTC, datetime
from typing import Any

from src.shared.logging import get_logger

from .base import AgentCapability, AgentRequest, BaseAgent

logger = get_logger(__name__)


class AdvisorAgent(BaseAgent):
    """
    Combined Advisor Agent specialized in career strategy and insight synthesis.

    This agent combines the functionality of CareerStrategist and InsightSynthesizer
    to provide comprehensive advisory services per Phase 1 specifications.

    Capabilities:
    - Career path planning and strategic advice
    - Multi-source insight synthesis
    - Development plan creation
    - Professional narrative generation
    - Opportunity identification and prioritization
    """

    def __init__(self):
        super().__init__(
            name="AdvisorAgent",
            description="Combined expert at career strategy and insight synthesis",
            capabilities=[
                AgentCapability.ADVICE,
                AgentCapability.SYNTHESIS,
                AgentCapability.PLANNING,
            ],
        )

        # Career development frameworks (from CareerStrategist)
        self.career_stages = [
            "Entry Level",
            "Junior",
            "Mid-Level",
            "Senior",
            "Lead",
            "Principal",
            "Staff",
            "Distinguished",
        ]

        self.development_areas = [
            "Technical Excellence",
            "Leadership",
            "Communication",
            "Business Acumen",
            "Innovation",
            "Mentorship",
        ]

        # Insight synthesis frameworks
        self.insight_categories = [
            "strategic",
            "tactical",
            "developmental",
            "risk_mitigation",
            "opportunity",
        ]

        # Register combined tools
        self.register_tool("provide_career_advice", self._provide_career_advice)
        self.register_tool("create_development_plan", self._create_development_plan)
        self.register_tool("synthesize_insights", self._synthesize_insights)
        self.register_tool("create_narrative", self._create_professional_narrative)
        self.register_tool("identify_opportunities", self._identify_opportunities)
        self.register_tool("comprehensive_advisory", self._comprehensive_advisory)

    async def _run(self, request: AgentRequest) -> dict[str, Any]:
        """
        Execute combined advisory task.

        This method intelligently routes to the appropriate advisory method
        or performs comprehensive advisory combining multiple capabilities.

        Args:
            request: The advisory request

        Returns:
            Combined advisory results
        """
        task = request.task.lower()
        context = request.context

        # Route to appropriate advisory method
        if "advice" in task or "recommend" in task:
            return await self._provide_comprehensive_advice(context)
        elif "plan" in task or "development" in task:
            return await self._create_strategic_development_plan(context)
        elif "synthesize" in task or "insights" in task:
            return await self._perform_insight_synthesis(context)
        elif "narrative" in task or "story" in task:
            return await self._create_professional_story(context)
        elif "opportunity" in task:
            return await self._identify_strategic_opportunities(context)
        elif "comprehensive" in task or "full" in task:
            return await self._provide_comprehensive_advisory(context)
        else:
            # Default to comprehensive advisory
            return await self._provide_combined_advisory(request.task, context)

    async def _provide_comprehensive_advice(self, context: dict[str, Any]) -> dict[str, Any]:
        """Provide comprehensive career advice with synthesized insights."""
        competencies = context.get("competencies", {})
        analysis_results = context.get("analysis_results", {})
        goals = context.get("goals", [])
        challenges = context.get("challenges", [])
        current_role = context.get("current_role", "Software Developer")

        # Combined prompt that provides both career advice AND synthesizes insights
        prompt = f"""Provide comprehensive career advisory combining strategic advice with synthesized insights:

Current Role: {current_role}
Competency Assessment: {json.dumps(competencies, indent=2)}
Analysis Results: {json.dumps(analysis_results, indent=2)}
Career Goals: {goals}
Current Challenges: {challenges}

Development Areas Framework:
{json.dumps(self.development_areas, indent=2)}

Career Stages:
{json.dumps(self.career_stages, indent=2)}

Provide comprehensive advisory with:
{{
    "strategic_advice": {{
        "immediate_actions": ["action1", "action2"],
        "short_term_strategy": ["strategy1", "strategy2"],
        "long_term_positioning": "vision statement",
        "key_relationships": ["relationship1", "relationship2"],
        "priority_skills": ["skill1", "skill2"]
    }},
    "synthesized_insights": {{
        "key_themes": ["theme1", "theme2"],
        "critical_findings": ["finding1", "finding2"],
        "strategic_insights": ["insight1", "insight2"],
        "data_connections": ["connection1", "connection2"]
    }},
    "development_recommendations": {{
        "learning_priorities": ["priority1", "priority2"],
        "experience_gaps": ["gap1", "gap2"],
        "certification_suggestions": ["cert1", "cert2"],
        "mentorship_needs": ["need1", "need2"]
    }},
    "opportunity_identification": {{
        "internal_opportunities": ["opp1", "opp2"],
        "external_opportunities": ["opp1", "opp2"],
        "emerging_trends": ["trend1", "trend2"],
        "market_positioning": "positioning advice"
    }},
    "risk_assessment": {{
        "potential_risks": ["risk1", "risk2"],
        "mitigation_strategies": ["strategy1", "strategy2"],
        "contingency_plans": ["plan1", "plan2"]
    }},
    "success_metrics": {{
        "milestones": ["milestone1", "milestone2"],
        "kpis": ["kpi1", "kpi2"],
        "timeline": "6-12 months"
    }}
}}"""

        response = await self.think(prompt, require_json=True, user_id=context.get("user_id"))

        try:
            comprehensive_advice = json.loads(response)
        except json.JSONDecodeError:
            comprehensive_advice = {
                "strategic_advice": {"immediate_actions": []},
                "synthesized_insights": {},
                "raw_response": response,
            }

        # Create professional narrative from the advice
        narrative = await self._generate_narrative_from_advice(comprehensive_advice, context)
        comprehensive_advice["professional_narrative"] = narrative

        # Store comprehensive advice
        if user_id := context.get("user_id"):
            await self.remember(f"comprehensive_advice:{user_id}", comprehensive_advice, ttl=86400)

        return {
            "comprehensive_advice": comprehensive_advice,
            "current_role": current_role,
            "timestamp": datetime.now(UTC).isoformat(),
            "type": "comprehensive_advice",
        }

    async def _create_strategic_development_plan(self, context: dict[str, Any]) -> dict[str, Any]:
        """Create strategic development plan with insight synthesis."""
        current_level = context.get("current_level", "Mid-Level")
        target_role = context.get("target_role", "Senior Developer")
        timeline = context.get("timeline", "12 months")
        gaps = context.get("gaps", [])
        competencies = context.get("competencies", {})
        analysis_results = context.get("analysis_results", {})

        prompt = f"""Create a strategic professional development plan with synthesized insights:

Current Situation:
- Current Level: {current_level}
- Target Role: {target_role}
- Timeline: {timeline}
- Identified Gaps: {gaps}

Data Sources:
- Competencies: {json.dumps(competencies, indent=2)}
- Analysis Results: {json.dumps(analysis_results, indent=2)}

Career Framework:
- Stages: {json.dumps(self.career_stages, indent=2)}
- Development Areas: {json.dumps(self.development_areas, indent=2)}

Create comprehensive development plan:
{{
    "executive_summary": {{
        "current_state": "assessment of where user is now",
        "target_state": "clear description of target role/level",
        "key_transformation": "main areas of growth needed",
        "success_probability": "high/medium/low with reasoning"
    }},
    "quarterly_roadmap": {{
        "q1_objectives": ["obj1", "obj2"],
        "q2_objectives": ["obj1", "obj2"],
        "q3_objectives": ["obj1", "obj2"],
        "q4_objectives": ["obj1", "obj2"]
    }},
    "development_pillars": {{
        "technical_growth": {{
            "current_level": 0-10,
            "target_level": 0-10,
            "key_skills": ["skill1", "skill2"],
            "learning_path": ["step1", "step2"],
            "projects": ["project1", "project2"]
        }},
        "leadership_growth": {{
            "current_level": 0-10,
            "target_level": 0-10,
            "key_skills": ["skill1", "skill2"],
            "experiences": ["exp1", "exp2"],
            "mentorship": "guidance on mentoring others"
        }},
        "strategic_growth": {{
            "current_level": 0-10,
            "target_level": 0-10,
            "business_acumen": ["area1", "area2"],
            "industry_knowledge": ["knowledge1", "knowledge2"],
            "networking": ["activity1", "activity2"]
        }}
    }},
    "success_metrics": {{
        "milestones": [
            {{
                "month": 3,
                "achievement": "milestone description",
                "measurement": "how to measure"
            }}
        ],
        "kpis": ["metric1", "metric2"],
        "review_schedule": "monthly/quarterly check-ins"
    }},
    "resource_allocation": {{
        "learning_time": "X hours per week",
        "project_work": "percentage of time",
        "networking": "activities per month",
        "budget": "for courses/conferences"
    }},
    "risk_mitigation": {{
        "potential_obstacles": ["obstacle1", "obstacle2"],
        "mitigation_strategies": ["strategy1", "strategy2"],
        "backup_plans": ["plan1", "plan2"]
    }}
}}"""

        response = await self.think(prompt, require_json=True, user_id=context.get("user_id"))

        try:
            development_plan = json.loads(response)
        except json.JSONDecodeError:
            development_plan = {
                "executive_summary": {"current_state": "Analysis in progress"},
                "error": "Failed to parse development plan",
                "raw_response": response,
            }

        # Generate insights about the plan
        plan_insights = await self._synthesize_plan_insights(development_plan, context)
        development_plan["strategic_insights"] = plan_insights

        # Store development plan
        if user_id := context.get("user_id"):
            await self.remember(f"dev_plan:{user_id}", development_plan, ttl=2592000)  # 30 days

        return {
            "development_plan": development_plan,
            "target_role": target_role,
            "timeline": timeline,
            "timestamp": datetime.now(UTC).isoformat(),
            "type": "strategic_development_plan",
        }

    async def _perform_insight_synthesis(self, context: dict[str, Any]) -> dict[str, Any]:
        """Perform comprehensive insight synthesis with career implications."""
        analysis_data = context.get("analysis", {})
        competency_data = context.get("competencies", {})
        advice_data = context.get("advice", {})
        additional_data = context.get("additional_data", {})

        prompt = f"""Perform comprehensive insight synthesis with career strategy focus:

Data Sources:
- Analysis Results: {json.dumps(analysis_data, indent=2)}
- Competency Assessment: {json.dumps(competency_data, indent=2)}
- Previous Advice: {json.dumps(advice_data, indent=2)}
- Additional Context: {json.dumps(additional_data, indent=2)}

Development Framework:
- Career Stages: {json.dumps(self.career_stages, indent=2)}
- Development Areas: {json.dumps(self.development_areas, indent=2)}

Synthesize insights with:
{{
    "executive_summary": {{
        "key_story": "overarching narrative from all data",
        "transformation_opportunity": "main growth opportunity identified",
        "confidence_level": 0.0-1.0,
        "data_quality_assessment": "strong/moderate/weak"
    }},
    "strategic_themes": [
        {{
            "theme": "theme name",
            "evidence": ["evidence1", "evidence2"],
            "implications": "what this means for career",
            "priority": "high/medium/low"
        }}
    ],
    "critical_insights": [
        {{
            "insight": "key insight statement",
            "source_data": "which data revealed this",
            "career_impact": "how this affects career progression",
            "actionability": "immediate/short-term/long-term"
        }}
    ],
    "pattern_recognition": {{
        "strengths_pattern": "consistent strengths across data",
        "growth_pattern": "areas showing development",
        "risk_pattern": "potential challenges or blind spots",
        "opportunity_pattern": "emerging opportunities"
    }},
    "synthesized_recommendations": {{
        "immediate_priorities": ["priority1", "priority2"],
        "strategic_investments": ["investment1", "investment2"],
        "relationship_building": ["relationship1", "relationship2"],
        "capability_development": ["capability1", "capability2"]
    }},
    "success_predictors": {{
        "positive_indicators": ["indicator1", "indicator2"],
        "risk_factors": ["risk1", "risk2"],
        "critical_success_factors": ["factor1", "factor2"]
    }}
}}"""

        response = await self.think(prompt, require_json=True, user_id=context.get("user_id"))

        try:
            synthesis = json.loads(response)
        except json.JSONDecodeError:
            synthesis = {
                "executive_summary": {"key_story": "Synthesis in progress"},
                "error": "Failed to parse synthesis",
                "raw_response": response,
            }

        # Create narrative from synthesis
        narrative = await self._create_synthesis_narrative(synthesis)
        synthesis["professional_narrative"] = narrative

        # Prioritize insights by impact
        prioritized_insights = self._prioritize_insights_by_impact(synthesis)
        synthesis["prioritized_insights"] = prioritized_insights

        return {
            "insight_synthesis": synthesis,
            "data_sources": len([d for d in [analysis_data, competency_data, advice_data] if d]),
            "timestamp": datetime.now(UTC).isoformat(),
            "type": "insight_synthesis",
        }

    async def _identify_strategic_opportunities(self, context: dict[str, Any]) -> dict[str, Any]:
        """Identify strategic career opportunities with synthesized insights."""
        competencies = context.get("competencies", {})
        market_trends = context.get("market_trends", [])
        company_context = context.get("company_context", {})
        industry = context.get("industry", "Technology")

        prompt = f"""Identify strategic career opportunities with comprehensive analysis:

Current Situation:
- Competencies: {json.dumps(competencies, indent=2)}
- Market Trends: {market_trends}
- Company Context: {json.dumps(company_context, indent=2)}
- Industry: {industry}

Career Framework:
- Stages: {json.dumps(self.career_stages, indent=2)}
- Development Areas: {json.dumps(self.development_areas, indent=2)}

Identify opportunities with synthesis:
{{
    "opportunity_landscape": {{
        "internal_opportunities": [
            {{
                "opportunity": "role/project description",
                "requirements": ["req1", "req2"],
                "timeline": "availability timeline",
                "competitive_advantage": "why user is well-positioned",
                "development_needs": ["need1", "need2"]
            }}
        ],
        "external_opportunities": [
            {{
                "market_segment": "segment name",
                "roles": ["role1", "role2"],
                "growth_potential": "high/medium/low",
                "entry_requirements": ["req1", "req2"],
                "compensation_range": "range if known"
            }}
        ],
        "emerging_opportunities": [
            {{
                "trend": "emerging trend",
                "opportunity": "how this creates opportunity",
                "preparation_time": "how long to prepare",
                "competitive_moat": "advantages to build"
            }}
        ]
    }},
    "strategic_positioning": {{
        "unique_value_proposition": "user's unique strengths",
        "competitive_advantages": ["advantage1", "advantage2"],
        "positioning_strategy": "how to position in market",
        "brand_building": ["activity1", "activity2"]
    }},
    "opportunity_prioritization": [
        {{
            "opportunity": "opportunity name",
            "attractiveness": 0-10,
            "feasibility": 0-10,
            "timeline": "time to pursue",
            "next_steps": ["step1", "step2"]
        }}
    ],
    "market_intelligence": {{
        "industry_trends": ["trend1", "trend2"],
        "skill_demand": ["in-demand1", "in-demand2"],
        "salary_trends": "market compensation trends",
        "geographic_considerations": ["location1", "location2"]
    }}
}}"""

        response = await self.think(prompt, require_json=True, user_id=context.get("user_id"))

        try:
            opportunities = json.loads(response)
        except json.JSONDecodeError:
            opportunities = {
                "opportunity_landscape": {},
                "error": "Failed to parse opportunities",
                "raw_response": response,
            }

        # Generate action plan for top opportunities
        action_plan = await self._create_opportunity_action_plan(opportunities)
        opportunities["action_plan"] = action_plan

        return {
            "strategic_opportunities": opportunities,
            "industry": industry,
            "timestamp": datetime.now(UTC).isoformat(),
            "type": "strategic_opportunities",
        }

    async def _provide_comprehensive_advisory(self, context: dict[str, Any]) -> dict[str, Any]:
        """Provide comprehensive advisory combining all capabilities."""
        # Perform all advisory functions in sequence
        results = {}

        # 1. Comprehensive Advice
        comprehensive_advice = await self._provide_comprehensive_advice(context)
        results["comprehensive_advice"] = comprehensive_advice

        # 2. Strategic Development Plan
        if context.get("target_role"):
            development_plan = await self._create_strategic_development_plan(context)
            results["development_plan"] = development_plan

        # 3. Insight Synthesis
        synthesis_context = {
            "analysis": context.get("analysis_results", {}),
            "competencies": context.get("competencies", {}),
            "advice": comprehensive_advice.get("comprehensive_advice", {}),
            "additional_data": context,
        }
        insight_synthesis = await self._perform_insight_synthesis(synthesis_context)
        results["insight_synthesis"] = insight_synthesis

        # 4. Strategic Opportunities
        opportunity_analysis = await self._identify_strategic_opportunities(context)
        results["strategic_opportunities"] = opportunity_analysis

        # 5. Generate master narrative
        master_narrative = await self._create_master_narrative(results, context)
        results["master_narrative"] = master_narrative

        return {
            "comprehensive_advisory": results,
            "timestamp": datetime.now(UTC).isoformat(),
            "type": "comprehensive_advisory",
        }

    async def _provide_combined_advisory(
        self, task: str, context: dict[str, Any]
    ) -> dict[str, Any]:
        """Provide combined advisory for general requests."""
        prompt = f"""Provide comprehensive career advisory combining strategy and insight synthesis:

Request: {task}
Context: {json.dumps(context, indent=2)}

Career Development Framework:
- Stages: {json.dumps(self.career_stages, indent=2)}
- Development Areas: {json.dumps(self.development_areas, indent=2)}

Provide combined advisory including:
1. Strategic career advice and recommendations
2. Synthesized insights from available data
3. Professional development suggestions
4. Opportunity identification
5. Actionable next steps

Focus on practical, strategic guidance for career advancement."""

        response = await self.think(prompt, user_id=context.get("user_id"))

        # Structure the response
        structured_advisory = await self._structure_combined_response(response, context)

        return {
            "combined_advisory": structured_advisory,
            "raw_advice": response,
            "task": task,
            "timestamp": datetime.now(UTC).isoformat(),
            "type": "combined_advisory",
        }

    # Tool implementations
    async def _provide_career_advice(
        self, competencies: dict[str, Any], goals: list[str], challenges: list[str]
    ) -> dict[str, Any]:
        """Tool: Provide career advice."""
        return await self._provide_comprehensive_advice(
            {"competencies": competencies, "goals": goals, "challenges": challenges}
        )

    async def _create_development_plan(
        self, current_level: str, target_role: str, timeline: str, gaps: list[str]
    ) -> dict[str, Any]:
        """Tool: Create development plan."""
        return await self._create_strategic_development_plan(
            {
                "current_level": current_level,
                "target_role": target_role,
                "timeline": timeline,
                "gaps": gaps,
            }
        )

    async def _synthesize_insights(
        self,
        analysis_data: dict[str, Any],
        competency_data: dict[str, Any],
        additional_data: dict[str, Any] = None,
    ) -> dict[str, Any]:
        """Tool: Synthesize insights from multiple sources."""
        return await self._perform_insight_synthesis(
            {
                "analysis": analysis_data,
                "competencies": competency_data,
                "additional_data": additional_data or {},
            }
        )

    async def _create_professional_narrative(self, synthesis_data: dict[str, Any]) -> str:
        """Tool: Create professional narrative."""
        result = await self._perform_insight_synthesis({"analysis": synthesis_data})
        return result.get("insight_synthesis", {}).get("professional_narrative", "")

    async def _identify_opportunities(
        self, competencies: dict[str, Any], industry: str = "Technology"
    ) -> dict[str, Any]:
        """Tool: Identify strategic opportunities."""
        return await self._identify_strategic_opportunities(
            {"competencies": competencies, "industry": industry}
        )

    async def _comprehensive_advisory(self, context: dict[str, Any]) -> dict[str, Any]:
        """Tool: Provide comprehensive advisory."""
        return await self._provide_comprehensive_advisory(context)

    # Helper methods
    async def _generate_narrative_from_advice(
        self, advice: dict[str, Any], context: dict[str, Any]
    ) -> str:
        """Generate professional narrative from advice."""
        prompt = f"""Create a compelling professional narrative from this career advice:

Advice Summary: {json.dumps(advice, indent=2)}
Context: {json.dumps(context, indent=2)}

Create a professional narrative that:
1. Tells a coherent story about career progression
2. Highlights key strengths and achievements
3. Addresses development opportunities
4. Ends with clear next steps
5. Is suitable for professional contexts

Keep it engaging and motivational (3-4 paragraphs)."""

        return await self.think(prompt, user_id=context.get("user_id"))

    async def _synthesize_plan_insights(
        self, plan: dict[str, Any], context: dict[str, Any]
    ) -> dict[str, Any]:
        """Synthesize insights about the development plan."""
        prompt = f"""Analyze this development plan and provide strategic insights:

Development Plan: {json.dumps(plan, indent=2)}
Context: {json.dumps(context, indent=2)}

Provide insights about:
1. Plan feasibility and realism
2. Key success factors
3. Potential risks and mitigation
4. Resource requirements
5. Expected outcomes

Format as strategic analysis."""

        response = await self.think(prompt, user_id=context.get("user_id"))
        return {"plan_analysis": response, "confidence": 0.8}

    async def _create_synthesis_narrative(self, synthesis: dict[str, Any]) -> str:
        """Create narrative from synthesis."""
        prompt = f"""Create a professional narrative from this insight synthesis:

Synthesis: {json.dumps(synthesis, indent=2)}

Create a compelling narrative that:
1. Presents the key story from the data
2. Highlights critical insights
3. Shows professional growth trajectory
4. Includes actionable recommendations
5. Ends with motivational next steps"""

        return await self.think(prompt)

    async def _create_opportunity_action_plan(
        self, opportunities: dict[str, Any]
    ) -> dict[str, Any]:
        """Create action plan for identified opportunities."""
        prompt = f"""Create an action plan from these opportunities:

Opportunities: {json.dumps(opportunities, indent=2)}

Provide structured action plan with:
1. Top 3 opportunities to pursue
2. Specific next steps for each
3. Timeline and milestones
4. Resource requirements
5. Success metrics"""

        response = await self.think(prompt)
        return {"action_plan": response}

    async def _create_master_narrative(
        self, results: dict[str, Any], context: dict[str, Any]
    ) -> str:
        """Create master professional narrative."""
        prompt = f"""Create a master professional narrative from comprehensive advisory results:

Advisory Results: {json.dumps(results, indent=2)}
Context: {json.dumps(context, indent=2)}

Create a compelling master narrative that:
1. Integrates all advisory components
2. Tells a cohesive professional story
3. Highlights transformation opportunity
4. Provides clear direction
5. Motivates action

This should be suitable for sharing with leadership or during reviews."""

        return await self.think(prompt, user_id=context.get("user_id"))

    async def _structure_combined_response(
        self, response: str, context: dict[str, Any]
    ) -> dict[str, Any]:
        """Structure a combined response."""
        # Simple parsing to structure the response
        return {
            "advisory_content": response,
            "context_used": list(context.keys()),
            "structured": True,
        }

    def _prioritize_insights_by_impact(self, synthesis: dict[str, Any]) -> list[dict[str, Any]]:
        """Prioritize insights by career impact."""
        insights = []

        # Extract insights from synthesis
        if critical_insights := synthesis.get("critical_insights", []):
            for insight in critical_insights:
                if isinstance(insight, dict):
                    insights.append(
                        {
                            "insight": insight.get("insight", ""),
                            "priority": "high" if insight.get("career_impact") else "medium",
                            "actionability": insight.get("actionability", "unknown"),
                        }
                    )

        # Sort by priority and return top 5
        insights.sort(
            key=lambda x: {"high": 3, "medium": 2, "low": 1}.get(x["priority"], 0), reverse=True
        )
        return insights[:5]
