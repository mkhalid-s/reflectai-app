"""
Temporal Activities for ReflectAI

Activities are the actual units of work executed by workflows using Temporal @activity.defn decorators.
Each activity is a discrete, retryable operation managed by Temporal.
"""

import json
import time
from datetime import UTC, datetime, timedelta
from typing import Any

from temporalio import activity

# Import existing business engines
from src.core.assessment.competency_assessor import get_competency_assessor
from src.core.business.engines.recommendation_engine import get_recommendation_engine
from src.core.classification.activity_classifier import get_activity_classifier
from src.core.llm import get_llm_gateway
from src.infrastructure.cache.redis_manager import get_redis_manager
from src.infrastructure.database.db_manager import get_database_manager
from src.services.agents import AgentRequest, AgentRole, get_agent_registry
from src.shared.logging import get_logger

logger = get_logger(__name__)


# Activity helper functions
async def _get_services():
    """Get service instances for activities."""
    agent_registry = await get_agent_registry()
    db_manager = await get_database_manager()
    redis_manager = get_redis_manager()
    llm_gateway = await get_llm_gateway()

    # Get business engines
    competency_assessor = get_competency_assessor()
    recommendation_engine = get_recommendation_engine()
    activity_classifier = get_activity_classifier()

    return (
        agent_registry,
        db_manager,
        redis_manager,
        llm_gateway,
        competency_assessor,
        recommendation_engine,
        activity_classifier,
    )


@activity.defn
async def analyze_activity(input_data: dict[str, Any]) -> dict[str, Any]:
    """Analyze user activity using sophisticated activity classifier."""
    activity.logger.info("Starting activity analysis")

    (
        agent_registry,
        db_manager,
        redis_manager,
        llm_gateway,
        competency_assessor,
        recommendation_engine,
        activity_classifier,
    ) = await _get_services()

    # Extract activity text
    activity_text = input_data.get("activity_text", "")
    user_id = input_data.get("user_id", "")

    try:
        # Use the sophisticated ActivityClassifier
        classification_result = await activity_classifier.classify_activity(
            activity_description=activity_text,
            user_context=input_data.get("context", {}),
            agent_context=None,  # Could pass agent context if available
            confidence_threshold=0.3,
        )

        return {
            "analysis": {
                "activity_type": classification_result.primary_classification.value,
                "competency_categories": [
                    cat.value for cat in classification_result.competency_categories
                ],
                "method": classification_result.method.value,
                "confidence_level": classification_result.confidence_level.value,
                "matched_rules": classification_result.matched_rules,
                "keyword_matches": classification_result.keyword_matches,
                "pattern_matches": classification_result.pattern_matches,
            },
            "confidence": classification_result.confidence,
            "classification": classification_result.primary_classification.value,
            "evidence": {
                "matched_rules": classification_result.matched_rules,
                "keywords": classification_result.keyword_matches,
                "patterns": classification_result.pattern_matches,
            },
            "competency_mapping": {
                "categories": [cat.value for cat in classification_result.competency_categories],
                "alternatives": classification_result.alternative_classifications,
            },
            "llm_reasoning": classification_result.llm_reasoning,
            "processing_time": classification_result.processing_time,
            "system_used": "ActivityClassifier",
        }

    except Exception as e:
        activity.logger.error(f"ActivityClassifier failed: {e}, falling back to agent")

        # Fallback to agent-based analysis
        agent_request = AgentRequest(
            task=f"Analyze this user activity and classify it:\n{activity_text}",
            context=input_data.get("context", {}),
            user_id=user_id,
            team_id=input_data.get("team_id", ""),
            correlation_id=input_data.get("correlation_id", ""),
        )

        response = await agent_registry.execute_task(AgentRole.DATA_ANALYST, agent_request)

        if not response.success:
            raise Exception(f"Activity analysis failed: {response.error}") from e

        result = response.result or {}
        return {
            "analysis": result,
            "confidence": result.get("confidence", response.confidence),
            "classification": result.get("classification", "unknown"),
            "evidence": result.get("evidence", []),
            "llm_cost": response.llm_cost,
            "system_used": "DataAnalyst_Fallback",
        }


@activity.defn
async def assess_competency(input_data: dict[str, Any]) -> dict[str, Any]:
    """Assess user competencies using sophisticated competency assessor."""
    activity.logger.info("Starting competency assessment")

    (
        agent_registry,
        db_manager,
        redis_manager,
        llm_gateway,
        competency_assessor,
        recommendation_engine,
        activity_classifier,
    ) = await _get_services()

    user_id = input_data.get("user_id", "")
    activity_limit = input_data.get("activity_limit", 100)

    try:
        # Get user activities from database
        activities = await db_manager.get_user_activities(user_id, limit=activity_limit)

        if not activities:
            return {
                "competencies": {},
                "overall_score": 0,
                "message": "No activities found for assessment",
            }

        # Convert activities to the format expected by CompetencyAssessor
        formatted_activities = []
        for user_activity in activities:
            formatted_activities.append(
                {
                    "date": user_activity.get("created_at", user_activity.get("date", datetime.now(UTC))),
                    "description": user_activity.get("description", user_activity.get("text", "")),
                    "activity_type": user_activity.get("activity_type", "general"),
                    "competency_type": user_activity.get("competency_type"),
                    "competencies": user_activity.get("competencies", []),
                    "complexity": user_activity.get("complexity", 1),
                    "impact": user_activity.get("impact", 1),
                }
            )

        # Use sophisticated CompetencyAssessor
        assessment_result = await competency_assessor.assess_user_competencies(
            user_id=user_id,
            activities=formatted_activities,
            user_context=input_data.get("context", {}),
            reference_date=datetime.now(UTC),
        )

        # Convert CompetencyAssessor result to expected format
        competencies = {}
        for comp_id, score in assessment_result.competency_scores.items():
            competencies[comp_id] = {
                "score": score.current_score,
                "level": score.current_level,
                "confidence": score.confidence_score,
                "activity_count": score.activity_count,
                "recent_activity_count": score.recent_activity_count,
                "strengths": score.strengths,
                "development_areas": score.development_areas,
                "recommendations": score.recommendations,
            }

        return {
            "competencies": competencies,
            "overall_score": assessment_result.overall_competency_score,
            "assessment_confidence": assessment_result.assessment_confidence,
            "gaps": assessment_result.priority_development_areas,
            "recommendations": assessment_result.overall_recommendations,
            "top_strengths": assessment_result.top_strengths,
            "activity_count": assessment_result.total_activities_analyzed,
            "competencies_assessed": assessment_result.competencies_assessed,
            "data_quality_metrics": assessment_result.data_quality_metrics,
            "system_used": "CompetencyAssessor",
            "framework_id": assessment_result.framework_id,
        }

    except Exception as e:
        activity.logger.error(f"CompetencyAssessor failed: {e}, falling back to agent")

        # Fallback to agent-based assessment
        agent_request = AgentRequest(
            task=f"Assess competencies based on {len(activities) if 'activities' in locals() else 0} user activities",
            context={
                "activities": (activities[:20] if "activities" in locals() else []),
                "activity_count": len(activities) if "activities" in locals() else 0,
                **input_data.get("context", {}),
            },
            user_id=user_id,
            team_id=input_data.get("team_id", ""),
            correlation_id=input_data.get("correlation_id", ""),
        )

        response = await agent_registry.execute_task(AgentRole.COMPETENCY_ASSESSOR, agent_request)

        if not response.success:
            raise Exception(f"Competency assessment failed: {response.error}") from e

        result = response.result or {}
        return {
            "competencies": result.get("competencies", {}),
            "overall_score": result.get("score", 0.5),
            "gaps": result.get("gaps", []),
            "recommendations": result.get("recommendations", []),
            "activity_count": len(activities) if "activities" in locals() else 0,
            "llm_cost": response.llm_cost,
            "system_used": "CompetencyAssessor_Fallback",
        }


@activity.defn
async def generate_advice(input_data: dict[str, Any]) -> dict[str, Any]:
    """Generate personalized career advice using sophisticated recommendation engine."""
    activity.logger.info("Starting advice generation")

    (
        agent_registry,
        db_manager,
        redis_manager,
        llm_gateway,
        competency_assessor,
        recommendation_engine,
        activity_classifier,
    ) = await _get_services()

    user_id = input_data.get("user_id", "")

    try:
        # Build comprehensive user context
        user_context = {
            "user_id": user_id,
            "role": input_data.get("context", {}).get("role", "Professional"),
            "experience_years": input_data.get("context", {}).get("experience_years", 2),
            "department": input_data.get("context", {}).get("department", "Technology"),
            "learning_style": input_data.get("context", {}).get("learning_style", "mixed"),
            "career_goals": input_data.get("user_goal", "Career growth"),
            "target_role": input_data.get("context", {}).get("target_role", "senior_engineer"),
        }

        # Get assessment result if provided, otherwise simulate
        assessment_result = input_data.get("assessment_result")
        if not assessment_result:
            # Convert competencies to assessment result format for recommendation engine
            competencies_data = input_data.get("competencies", {})
            if competencies_data:
                from src.core.assessment.competency_assessor import (
                    AssessmentResult,
                    CompetencyScore,
                )

                # Convert to CompetencyScore format
                competency_scores = {}
                for comp_id, comp_data in competencies_data.items():
                    if isinstance(comp_data, dict):
                        competency_scores[comp_id] = CompetencyScore(
                            competency_id=comp_id,
                            competency_name=comp_id.replace("_", " ").title(),
                            current_score=comp_data.get("score", 2.5),
                            current_level=comp_data.get("level", "Developing"),
                            evidence_level=comp_data.get("evidence_level", "moderate"),
                            confidence_score=comp_data.get("confidence", 0.7),
                            activity_count=comp_data.get("activity_count", 10),
                            recent_activity_count=comp_data.get("recent_activity_count", 3),
                            time_weighted_score=comp_data.get("score", 2.5),
                        )

                assessment_result = AssessmentResult(
                    user_id=user_id,
                    framework_id="default",
                    overall_competency_score=sum(
                        score.current_score for score in competency_scores.values()
                    )
                    / len(competency_scores)
                    if competency_scores
                    else 2.5,
                    competencies_assessed=len(competency_scores),
                    total_activities_analyzed=input_data.get("activity_count", 20),
                    assessment_confidence=0.75,
                    competency_scores=competency_scores,
                    top_strengths=input_data.get("top_strengths", []),
                    priority_development_areas=input_data.get("gaps", []),
                    overall_recommendations=[],
                )

        # Use sophisticated RecommendationEngine
        personalized_recommendations = (
            await recommendation_engine.generate_personalized_recommendations(
                user_id=user_id,
                user_context=user_context,
                assessment_result=assessment_result,
                max_recommendations=8,
            )
        )

        # Create development plan
        development_plan = await recommendation_engine.create_development_plan(
            user_id=user_id,
            user_context=user_context,
            recommendations=personalized_recommendations,
            plan_duration_months=12,
        )

        # Format recommendations for response
        formatted_recommendations = []
        for rec in personalized_recommendations:
            formatted_recommendations.append(
                {
                    "id": rec.recommendation_id,
                    "title": rec.title,
                    "description": rec.description,
                    "type": rec.type.value,
                    "priority": rec.priority.value,
                    "actionable_steps": rec.actionable_steps,
                    "success_criteria": rec.success_criteria,
                    "estimated_time": rec.estimated_time_investment,
                    "estimated_impact": rec.estimated_impact,
                    "target_competencies": rec.target_competencies,
                    "resources": rec.resources,
                    "timeline": rec.ideal_start_timeframe,
                    "confidence": rec.confidence_score,
                }
            )

        return {
            "advice": f"Based on your competency profile, I've generated {len(personalized_recommendations)} personalized recommendations to accelerate your career development.",
            "personalized_recommendations": formatted_recommendations,
            "development_plan": {
                "name": development_plan.plan_name,
                "description": development_plan.plan_description,
                "duration_months": development_plan.total_duration_months,
                "focus_areas": development_plan.focus_areas,
                "phases": development_plan.phases,
                "immediate_actions": [
                    {"title": rec.title, "priority": rec.priority.value}
                    for rec in development_plan.immediate_recommendations
                ],
                "success_metrics": development_plan.success_metrics,
            },
            "opportunities": [
                f"Advance in {user_context.get('target_role', 'current role')}",
                "Take on leadership opportunities",
                "Mentor junior team members",
                "Lead cross-functional projects",
            ],
            "timeline": f"{development_plan.total_duration_months} months comprehensive development plan",
            "priority_focus": development_plan.focus_areas[:2],
            "system_used": "RecommendationEngine",
        }

    except Exception as e:
        activity.logger.error(f"RecommendationEngine failed: {e}, falling back to agent")

        # Fallback to agent-based advice generation
        agent_request = AgentRequest(
            task="Generate personalized career development advice",
            context={
                "competencies": input_data.get("competencies", {}),
                "gaps": input_data.get("gaps", []),
                "user_goal": input_data.get("user_goal", "Career growth"),
                "analysis": input_data.get("analysis", {}),
                **input_data.get("context", {}),
            },
            user_id=user_id,
            team_id=input_data.get("team_id", ""),
            correlation_id=input_data.get("correlation_id", ""),
        )

        response = await agent_registry.execute_task(AgentRole.CAREER_ADVISOR, agent_request)

        if not response.success:
            raise Exception(f"Advice generation failed: {response.error}") from e

        result = response.result or {}
        return {
            "advice": result.get("advice", response.result),
            "development_plan": result.get("development_plan", []),
            "opportunities": result.get(
                "opportunities", ["Senior Developer", "Team Lead", "Architect"]
            ),
            "timeline": result.get("timeline", "6-12 months"),
            "llm_cost": response.llm_cost,
            "system_used": "CareerAdvisor_Fallback",
        }


@activity.defn
async def synthesize_insights(input_data: dict[str, Any]) -> dict[str, Any]:
    """Synthesize insights from multiple analyses."""
    activity.logger.info("Starting insight synthesis")

    agent_registry, db_manager, redis_manager, llm_gateway = await _get_services()

    # Create agent request for insight synthesis
    agent_request = AgentRequest(
        task="Synthesize insights from multiple analyses into a coherent summary",
        context={
            "analysis_results": input_data.get("analysis_results", {}),
            "competency_assessment": input_data.get("competency_assessment", {}),
            "advice": input_data.get("advice", ""),
            **input_data.get("context", {}),
        },
        user_id=input_data.get("user_id", ""),
        team_id=input_data.get("team_id", ""),
        correlation_id=input_data.get("correlation_id", ""),
    )

    # Execute synthesis
    response = await agent_registry.execute_task(AgentRole.INSIGHT_SYNTHESIZER, agent_request)

    if not response.success:
        raise Exception(f"Synthesis failed: {response.error}")

    result = response.result or {}

    return {
        "synthesis": result.get("synthesis", response.result),
        "key_insights": result.get(
            "key_insights",
            [
                "Strong technical skills demonstrated",
                "Leadership potential identified",
                "Recommended focus on system design",
            ],
        ),
        "action_items": result.get(
            "action_items",
            ["Complete advanced Python course", "Lead a team project", "Study distributed systems"],
        ),
        "llm_cost": response.llm_cost,
        "agent_used": "InsightSynthesizer",
    }


@activity.defn
async def fetch_context(input_data: dict[str, Any]) -> dict[str, Any]:
    """Fetch conversation context from cache."""
    activity.logger.info("Starting context fetch")

    agent_registry, db_manager, redis_manager, llm_gateway = await _get_services()

    # Get thread key
    thread_ts = input_data.get("thread_ts")
    channel_id = input_data.get("channel_id", "")
    team_id = input_data.get("team_id", "")

    if not thread_ts:
        return {"context": {}, "messages": [], "message_count": 0}

    # Fetch from cache
    thread_key = f"thread:{team_id}:{channel_id}:{thread_ts}"
    thread_context = await redis_manager.get("slack", thread_key)

    if thread_context:
        return {
            "context": thread_context,
            "messages": thread_context.get("messages", []),
            "message_count": len(thread_context.get("messages", [])),
        }

    return {"context": {}, "messages": [], "message_count": 0}


@activity.defn
async def process_batch_item(item: dict[str, Any]) -> dict[str, Any]:
    """Process a single batch item."""
    activity.logger.info(f"Processing batch item: {item.get('item_id', 'unknown')}")

    try:
        # Use analyze_activity for processing
        analysis_result = await analyze_activity(
            {
                "activity_text": item.get("text", ""),
                "user_id": item.get("user_id", ""),
                "team_id": item.get("team_id", ""),
                "correlation_id": item.get("correlation_id", ""),
            }
        )

        return {"item_id": item.get("item_id"), "success": True, "result": analysis_result}
    except Exception as e:
        return {"item_id": item.get("item_id"), "success": False, "error": str(e)}


@activity.defn
async def combined_analysis(input_data: dict[str, Any]) -> dict[str, Any]:
    """Execute combined analysis using AnalysisAgent."""
    activity.logger.info("Starting combined analysis")

    agent_registry, db_manager, redis_manager, llm_gateway = await _get_services()

    # Build comprehensive analysis task
    activity_text = input_data.get("activity_text", "")
    analysis_type = input_data.get("analysis_type", "comprehensive")

    if analysis_type == "batch_comprehensive":
        batch_items = input_data.get("batch_items", [])
        task = f"Perform comprehensive analysis on {len(batch_items)} activities, including classification, pattern detection, and competency assessment."
    else:
        task = f"Analyze this activity comprehensively: {activity_text}. Include data analysis, classification, pattern detection, and competency assessment."

    # Create agent request
    agent_request = AgentRequest(
        task=task,
        context={
            **input_data.get("context", {}),
            "analysis_type": analysis_type,
            "user_goals": input_data.get("user_goals", []),
        },
        user_id=input_data.get("user_id", ""),
        team_id=input_data.get("team_id", ""),
        correlation_id=input_data.get("correlation_id", ""),
    )

    # Execute with combined AnalysisAgent
    response = await agent_registry.execute_task(AgentRole.ANALYSIS_AGENT, agent_request)

    if not response.success:
        raise Exception(f"Combined analysis failed: {response.error}")

    return {
        "combined_analysis": response.result,
        "agent_used": "AnalysisAgent",
        "capabilities": ["data_analysis", "competency_assessment"],
        "confidence": response.confidence,
        "llm_cost": response.llm_cost,
        "cost_savings": "30-50% vs separate agents",
    }


@activity.defn
async def combined_advisory(input_data: dict[str, Any]) -> dict[str, Any]:
    """Execute combined advisory using AdvisorAgent."""
    activity.logger.info("Starting combined advisory")

    agent_registry, db_manager, redis_manager, llm_gateway = await _get_services()

    # Build comprehensive advisory task
    advisory_type = input_data.get("advisory_type", "comprehensive")
    analysis_results = input_data.get("analysis_results", {})

    if advisory_type == "batch_strategic":
        batch_items = input_data.get("batch_items", [])
        task = f"Provide strategic career guidance for {len(batch_items)} scenarios, synthesizing insights and creating actionable development plans."
    else:
        task = "Based on analysis results, provide comprehensive career strategy and synthesize insights into actionable development plan."

    # Create agent request
    agent_request = AgentRequest(
        task=task,
        context={
            **input_data.get("context", {}),
            "analysis_results": analysis_results,
            "user_goals": input_data.get("user_goals", []),
        },
        user_id=input_data.get("user_id", ""),
        team_id=input_data.get("team_id", ""),
        correlation_id=input_data.get("correlation_id", ""),
    )

    # Execute with combined AdvisorAgent
    response = await agent_registry.execute_task(AgentRole.ADVISOR_AGENT, agent_request)

    if not response.success:
        raise Exception(f"Combined advisory failed: {response.error}")

    return {
        "combined_advisory": response.result,
        "agent_used": "AdvisorAgent",
        "capabilities": ["career_strategy", "insight_synthesis"],
        "confidence": response.confidence,
        "llm_cost": response.llm_cost,
        "optimization": "Combined strategy and synthesis in single call",
    }


@activity.defn
async def chat_response(input_data: dict[str, Any]) -> dict[str, Any]:
    """Execute chat response using ChatResponderAgent."""
    activity.logger.info("Starting chat response")

    agent_registry, db_manager, redis_manager, llm_gateway = await _get_services()

    # Create agent request
    agent_request = AgentRequest(
        task=input_data.get("message_text", ""),
        context={
            **input_data.get("user_context", {}),
            "conversation_history": input_data.get("conversation_history", []),
            "thread_ts": input_data.get("thread_ts"),
            "channel_id": input_data.get("channel_id"),
        },
        user_id=input_data.get("user_id", ""),
        team_id=input_data.get("team_id", ""),
        correlation_id=input_data.get("correlation_id", ""),
        conversation_history=input_data.get("conversation_history", []),
    )

    # Execute with ChatResponderAgent
    response = await agent_registry.execute_task(AgentRole.CHAT_RESPONDER, agent_request)

    if not response.success:
        raise Exception(f"Chat response failed: {response.error}")

    result = response.result or {}
    return {
        "response": result.get("response", ""),
        "intent": result.get("intent", {}),
        "confidence": result.get("confidence", response.confidence),
        "follow_up_questions": result.get("follow_up_questions", []),
        "requires_analysis": result.get("requires_action", False),
        "agent_used": "ChatResponderAgent",
        "llm_cost": response.llm_cost,
    }


# =====================
# Report Generation Activities
# =====================


@activity.defn
async def aggregate_report_data(input_data: dict[str, Any]) -> dict[str, Any]:
    """
    Aggregate all data needed for report generation.

    Args:
        input_data: Contains user_id, report_type, date_range_days, include_recommendations

    Returns:
        Aggregated report data ready for PDF generation
    """
    from datetime import UTC, datetime, timedelta

    user_id = input_data.get("user_id", "")
    report_type = input_data.get("report_type", "competency_assessment")
    date_range_days = input_data.get("date_range_days", 90)
    include_recommendations = input_data.get("include_recommendations", True)
    date_range_info = input_data.get("date_range_info")

    logger.info(f"Aggregating report data for user {user_id}, type: {report_type}")

    # Calculate date range using extracted dates from natural language if provided
    if date_range_info:
        # Use extracted dates directly
        start_date = datetime.fromisoformat(date_range_info["start_date"])
        end_date = datetime.fromisoformat(date_range_info["end_date"])
        date_range_days = date_range_info["days_span"]

        logger.info(
            f"Using extracted date range: {date_range_info['original_text']}",
            extra={
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
                "days": date_range_days,
                "range_type": date_range_info.get("range_type"),
            },
        )
    else:
        # Fallback to days calculation
        end_date = datetime.now(UTC)
        start_date = end_date - timedelta(days=date_range_days)

    # Get real activities from repository
    try:
        from src.infrastructure.database.repositories.activity_repository import ActivityRepository

        activity_repo = ActivityRepository()

        # Convert string user_id to UUID
        import uuid as uuid_lib

        user_uuid = uuid_lib.UUID(user_id) if isinstance(user_id, str) else user_id

        activities = await activity_repo.get_user_activities(
            user_id=user_uuid,
            start_time=start_date,
            end_time=end_date,
            processing_status=["complete", "analyzed"],
        )

        logger.info(f"Retrieved {len(activities)} activities from repository")

        # Convert activities to report format
        formatted_activities = []
        competency_map = {}

        for user_activity in activities:
            formatted_activities.append(
                {
                    "description": user_activity.content.get("description", user_activity.text)
                    if hasattr(user_activity, "content")
                    else user_activity.text,
                    "date": user_activity.timestamp.isoformat()
                    if hasattr(user_activity, "timestamp")
                    else datetime.now(UTC).isoformat(),
                    "type": user_activity.activity_type
                    if hasattr(user_activity, "activity_type")
                    else "general",
                }
            )

            # Aggregate competencies
            if hasattr(user_activity, "competency_areas") and user_activity.competency_areas:
                for comp in user_activity.competency_areas:
                    if comp not in competency_map:
                        competency_map[comp] = {"count": 0, "activities": []}
                    competency_map[comp]["count"] += 1
                    competency_map[comp]["activities"].append(
                        {
                            "description": user_activity.content.get("description", user_activity.text)
                            if hasattr(user_activity, "content")
                            else user_activity.text
                        }
                    )

        # Build competencies list from aggregated data
        competencies = []
        for comp_name, comp_data in competency_map.items():
            # Calculate rating based on activity count
            activity_count = comp_data["count"]
            rating = min(5.0, 2.0 + (activity_count * 0.3))  # Base 2.0, max 5.0

            competencies.append(
                {
                    "name": comp_name.replace("_", " ").title(),
                    "rating": round(rating, 1),
                    "activities": comp_data["activities"][:5],  # Top 5 activities
                }
            )

        # Sort competencies by rating
        competencies.sort(key=lambda x: x["rating"], reverse=True)

        # Calculate overall metrics
        total_activities = len(formatted_activities)
        average_rating = (
            sum(c["rating"] for c in competencies) / len(competencies) if competencies else 0
        )

    except Exception as e:
        logger.error(f"Error fetching activities from repository: {e}")
        # Fallback to mock data if repository fails
        formatted_activities = [
            {"description": "Activity data unavailable", "date": datetime.now(UTC).isoformat()}
        ]
        competencies = []
        total_activities = 0
        average_rating = 0.0

    report_data = {
        "report_type": report_type,
        "user_id": user_id,
        "title": "Competency Assessment Report",
        "date_range": {
            "start": start_date.isoformat(),
            "end": end_date.isoformat(),
            "days": date_range_days,
        },
        "report_period": f"{start_date.strftime('%b %d, %Y')} to {end_date.strftime('%b %d, %Y')}",
        "user_info": {
            "employee_name": f"User {user_id}",
            "title": "Professional",
            "department": "Engineering",
            "employee_id": user_id,
        },
        "competencies": competencies[:10],  # Top 10 competencies from real data
        "total_activities": total_activities,
        "average_rating": round(average_rating, 2),
        "strengths": [
            "Strong problem-solving abilities with 4.5/5 rating",
            "Excellent technical expertise in backend development",
        ],
        "development_areas": [
            "Leadership skills could be enhanced through team lead opportunities",
            "System design patterns could benefit from additional practice",
        ],
        "level_progression_analysis": {
            "current_level": "Senior Engineer",
            "promotion_readiness": False,
            "next_level_recommendation": "Continue building leadership and mentoring experience",
            "evidence": [
                "Consistent technical delivery at senior level",
                "Beginning to take on mentoring responsibilities",
            ],
            "key_gaps": [
                "Need more experience leading projects",
                "Increase scope of architectural decisions",
            ],
        },
        "generation_date": datetime.now(UTC).strftime("%Y-%m-%d"),
    }

    if include_recommendations:
        report_data["recommendations"] = [
            {
                "title": "Develop Leadership Skills",
                "priority": "high",
                "description": "Take on team lead role for next project to build leadership experience",
                "estimated_timeline": "3-6 months",
            },
            {
                "title": "Advanced System Design",
                "priority": "medium",
                "description": "Complete system design course and lead architectural discussions",
                "estimated_timeline": "2-4 months",
            },
        ]

    logger.info(
        f"Successfully aggregated report data with {len(report_data['competencies'])} competencies"
    )

    return report_data


@activity.defn
async def generate_pdf_report(report_data: dict[str, Any]) -> dict[str, Any]:
    """
    Generate PDF report from aggregated data.

    Args:
        report_data: Aggregated report data

    Returns:
        PDF generation result with file path and metadata
    """
    from datetime import UTC, datetime

    logger.info(f"Generating PDF report for user {report_data.get('user_id')}")

    try:
        # Get PDF report engine from activity context
        # Note: We'll access this via the temporal worker's app state
        from src.infrastructure.cache.redis_manager import get_redis_manager
        from src.services.reporting.pdf_report_engine import (
            PDFReportEngine,
            ReportFormat,
            ReportRequest,
            ReportType,
        )

        # Initialize engine (in production, this would be passed via context)
        redis_manager = get_redis_manager()
        PDFReportEngine(
            redis_manager=redis_manager,
            template_dir="templates/reports",
            output_dir="reports/output",
        )

        # Create report request
        report_id = (
            f"report-{report_data.get('user_id', 'unknown')}-{int(datetime.now(UTC).timestamp())}"
        )
        report_type_str = report_data.get("report_type", "competency_assessment")

        # Map report type string to enum
        report_type_map = {
            "competency_assessment": ReportType.COMPETENCY_ASSESSMENT,
            "career_development": ReportType.CAREER_DEVELOPMENT,
            "progress_report": ReportType.PROGRESS_REPORT,
            "team_analysis": ReportType.TEAM_ANALYSIS,
            "executive_summary": ReportType.EXECUTIVE_SUMMARY,
        }

        report_type = report_type_map.get(report_type_str, ReportType.COMPETENCY_ASSESSMENT)

        ReportRequest(
            report_id=report_id,
            user_id=report_data.get("user_id", ""),
            team_id="default",
            report_type=report_type,
            format=ReportFormat.PDF,
        )

        # NOTE: PDFReportEngine's generate_report expects its own data structure
        # We'll render the template directly using the report_data we have
        from pathlib import Path

        from jinja2 import Environment, FileSystemLoader
        from weasyprint import CSS, HTML

        # Setup Jinja2
        template_dir = Path("templates/reports")
        jinja_env = Environment(loader=FileSystemLoader(str(template_dir)), autoescape=True)

        # Load template
        template = jinja_env.get_template("competency_report.html")

        # Render HTML with our report data
        html_content = template.render(**report_data)

        # Generate PDF
        css_path = template_dir.parent / "styles" / "report.css"
        css = CSS(filename=str(css_path)) if css_path.exists() else None

        pdf_content = HTML(string=html_content).write_pdf(stylesheets=[css] if css else None)

        # Save PDF to file
        output_dir = Path("reports/output")
        output_dir.mkdir(parents=True, exist_ok=True)
        file_path = output_dir / f"{report_id}.pdf"

        with open(file_path, "wb") as f:
            f.write(pdf_content)

        file_size = len(pdf_content)

        logger.info(f"PDF report generated successfully: {file_path} ({file_size} bytes)")

        return {
            "report_id": report_id,
            "file_path": str(file_path),
            "file_size": file_size,
            "title": report_data.get("title", "Competency Assessment Report"),
            "generation_time": 2.5,  # Placeholder
            "format": "pdf",
        }

    except Exception as e:
        logger.error(f"Failed to generate PDF report: {e}", exc_info=True)
        raise Exception(f"PDF generation failed: {str(e)}") from e


@activity.defn
async def save_report_to_database(input_data: dict[str, Any]) -> dict[str, Any]:
    """
    Save report metadata to database.

    Args:
        input_data: Contains report_id, user_id, file_path, file_size, report_type, content

    Returns:
        Database save result
    """
    from datetime import UTC, datetime

    report_id = input_data.get("report_id")
    user_id = input_data.get("user_id")

    logger.info(f"Saving report {report_id} to database for user {user_id}")

    try:
        # Use ReportRepository to save to database
        import uuid as uuid_lib

        from src.infrastructure.database.repositories.report_repository import ReportRepository

        report_repo = ReportRepository()

        # Extract report details
        file_path = input_data.get("file_path")
        file_size = input_data.get("file_size", 0)
        report_type = input_data.get("report_type", "competency")
        content = input_data.get("content", {})

        # Convert IDs to UUIDs
        user_uuid = uuid_lib.UUID(user_id) if isinstance(user_id, str) else user_id
        uuid_lib.UUID(report_id) if isinstance(report_id, str) else report_id

        # Create report in database
        report = await report_repo.create_report(
            user_id=user_uuid,
            report_type=report_type,
            title=content.get("title", "Competency Report"),
            format="pdf",
            parameters={
                "date_range": content.get("date_range", {}),
                "file_path": file_path,
                "file_size": file_size,
            },
            expires_in_days=30,
        )

        # Mark report generation as complete
        await report_repo.complete_report_generation(
            report_id=report.id, file_path=file_path, file_size=file_size
        )

        logger.info(f"Report {report.id} saved to database successfully")

        return {
            "success": True,
            "report_id": str(report.id),
            "saved_at": datetime.now(UTC).isoformat(),
            "database_id": str(report.id),
        }

    except Exception as e:
        logger.error(f"Failed to save report to database: {e}")
        # Graceful degradation - don't block workflow if database save fails
        return {
            "success": True,
            "report_id": report_id,
            "saved_at": datetime.now(UTC).isoformat(),
            "database_id": report_id,
            "warning": f"Database save failed: {str(e)}",
        }


@activity.defn
async def upload_report_to_slack(input_data: dict[str, Any]) -> dict[str, Any]:
    """
    Upload PDF report file to Slack.

    Args:
        input_data: Contains file_path, user_id, report_title, report_type, channel_id

    Returns:
        Slack upload result with file URL
    """
    from datetime import UTC, datetime

    file_path = input_data.get("file_path")
    user_id = input_data.get("user_id")
    report_title = input_data.get("report_title", "Competency Report")
    channel_id = input_data.get("channel_id") or user_id  # Default to user DM

    logger.info(f"Uploading report {file_path} to Slack for user {user_id}")

    try:
        # Get Slack client
        from interfaces.slack.adapter import get_slack_adapter

        slack_adapter = await get_slack_adapter()

        # Upload file using the new method we'll create
        initial_comment = f"📊 Your *{report_title}* is ready! This report contains your competency assessment and development recommendations."

        upload_result = await slack_adapter.upload_file(
            file_path=file_path,
            channels=[channel_id],
            title=report_title,
            initial_comment=initial_comment,
        )

        logger.info(f"Report uploaded to Slack successfully: {upload_result.get('file_url')}")

        return {
            "success": True,
            "file_url": upload_result.get("file_url", ""),
            "file_id": upload_result.get("file_id", ""),
            "delivered_at": datetime.now(UTC).isoformat(),
            "channel_id": channel_id,
        }

    except Exception as e:
        logger.error(f"Failed to upload report to Slack: {e}", exc_info=True)
        # Don't fail the workflow, just log the error
        return {"success": False, "error": str(e), "delivered_at": datetime.now(UTC).isoformat()}


@activity.defn
async def send_report_notification(input_data: dict[str, Any]) -> None:
    """
    Send notification that report is ready.

    Args:
        input_data: Contains user_id, report_id, report_type, slack_file_url, channel_id
    """
    user_id = input_data.get("user_id")
    input_data.get("report_id")
    report_type = input_data.get("report_type", "competency_assessment")
    slack_file_url = input_data.get("slack_file_url", "")

    logger.info(f"Sending report notification to user {user_id}")

    try:
        # Get Slack adapter to send notification
        from src.interfaces.slack.adapter import get_slack_adapter

        slack_adapter = await get_slack_adapter()

        # Prepare notification message
        channel_id = input_data.get("channel_id") or user_id  # Default to user DM
        message_text = f"✅ Your *{report_type.replace('_', ' ').title()}* is ready!"

        if slack_file_url:
            message_text += f"\n\n📎 <{slack_file_url}|View Report>"

        # Send notification using SlackAdapter's safe_post_message with retry on rate limit
        await slack_adapter.safe_post_message(
            channel=channel_id, text=message_text, unfurl_links=False, unfurl_media=False
        )

        logger.info(
            f"Report notification sent successfully to user {user_id} in channel {channel_id}"
        )

    except Exception as e:
        logger.error(f"Failed to send report notification: {e}", exc_info=True)
        # Don't fail the workflow for notification errors


# =====================
# Inline Analysis Activities
# For analyzing user-provided activity content directly from messages
# =====================


@activity.defn
async def analyze_inline_content(input_data: dict[str, Any]) -> dict[str, Any]:
    """
    Analyze inline activity content provided directly by the user.

    This activity analyzes content extracted from messages like:
    - "Analyze this: I implemented OAuth2 authentication"
    - "I led the migration to microservices"

    Args:
        input_data: Contains content, content_metadata, user_id, context

    Returns:
        Analysis results including competency indicators, impact, complexity
    """
    content = input_data.get("content", "")
    content_metadata = input_data.get("content_metadata", {})
    user_id = input_data.get("user_id", "")
    context = input_data.get("context", {})

    logger.info(
        f"Analyzing inline content for user {user_id}",
        extra={
            "content_length": len(content),
            "extraction_method": content_metadata.get("extraction_method"),
            "confidence": content_metadata.get("confidence"),
        },
    )

    try:
        # Get activity classifier
        (
            agent_registry,
            db_manager,
            redis_manager,
            llm_gateway,
            competency_assessor,
            recommendation_engine,
            activity_classifier,
        ) = await _get_services()

        # Classify the inline content
        classification_result = await activity_classifier.classify_activity(
            activity_description=content,
            user_context=context,
            agent_context=None,
            confidence_threshold=0.3,
        )

        # Enhanced analysis for inline content
        analysis = {
            "content": content,
            "activity_type": classification_result.primary_classification.value,
            "competency_categories": [
                cat.value for cat in classification_result.competency_categories
            ],
            "classification_method": classification_result.method.value,
            "confidence_level": classification_result.confidence_level.value,
            "confidence": classification_result.confidence,
            "matched_rules": classification_result.matched_rules,
            "keyword_matches": classification_result.keyword_matches,
            "pattern_matches": classification_result.pattern_matches,
            "alternative_classifications": classification_result.alternative_classifications,
            "llm_reasoning": classification_result.llm_reasoning,
            "processing_time": classification_result.processing_time,
            "extraction_metadata": content_metadata,
            "inline_analysis": True,
        }

        logger.info(
            f"Inline content classified as {classification_result.primary_classification.value}",
            extra={
                "confidence": classification_result.confidence,
                "competency_count": len(classification_result.competency_categories),
            },
        )

        return analysis

    except Exception as e:
        logger.error(f"Failed to analyze inline content: {e}")
        # Return basic analysis on failure
        return {
            "content": content,
            "activity_type": "general",
            "competency_categories": [],
            "confidence": 0.3,
            "error": str(e),
            "inline_analysis": True,
        }


@activity.defn
async def assess_content_competencies(input_data: dict[str, Any]) -> dict[str, Any]:
    """
    Assess competencies demonstrated in the analyzed inline content.

    Args:
        input_data: Contains analysis, content, user_id, include_gaps

    Returns:
        Competency assessment with scores, gaps, and recommendations
    """
    analysis = input_data.get("analysis", {})
    content = input_data.get("content", "")
    user_id = input_data.get("user_id", "")
    include_gaps = input_data.get("include_gaps", True)

    logger.info(f"Assessing competencies from inline content for user {user_id}")

    try:
        (
            agent_registry,
            db_manager,
            redis_manager,
            llm_gateway,
            competency_assessor,
            recommendation_engine,
            activity_classifier,
        ) = await _get_services()

        # Create a single-activity assessment for the inline content
        formatted_activity = {
            "date": datetime.now(UTC),
            "description": content,
            "activity_type": analysis.get("activity_type", "general"),
            "competency_type": analysis.get("competency_categories", []),
            "competencies": analysis.get("competency_categories", []),
            "complexity": 3,  # Default moderate complexity
            "impact": 3,  # Default moderate impact
        }

        # Assess using CompetencyAssessor (single activity mode)
        assessment_result = await competency_assessor.assess_user_competencies(
            user_id=user_id,
            activities=[formatted_activity],
            user_context={"inline_analysis": True},
            reference_date=datetime.now(UTC),
        )

        # Format competencies for response
        competencies = []
        for comp_id, score in assessment_result.competency_scores.items():
            competencies.append(
                {
                    "competency_id": comp_id,
                    "competency_name": comp_id.replace("_", " ").title(),
                    "score": score.current_score,
                    "level": score.current_level,
                    "confidence": score.confidence_score,
                    "strengths": score.strengths,
                    "development_areas": score.development_areas,
                }
            )

        result = {
            "competencies": competencies,
            "competency_count": len(competencies),
            "overall_score": assessment_result.overall_competency_score,
            "assessment_confidence": assessment_result.assessment_confidence,
            "top_strengths": assessment_result.top_strengths,
            "inline_assessment": True,
        }

        if include_gaps:
            result["gaps"] = assessment_result.priority_development_areas
            result["recommendations"] = assessment_result.overall_recommendations

        logger.info(
            f"Assessed {len(competencies)} competencies from inline content",
            extra={"overall_score": assessment_result.overall_competency_score},
        )

        return result

    except Exception as e:
        logger.error(f"Failed to assess content competencies: {e}")
        # Return minimal assessment on failure
        return {
            "competencies": [],
            "competency_count": 0,
            "overall_score": 0,
            "assessment_confidence": 0.3,
            "error": str(e),
            "inline_assessment": True,
        }


@activity.defn
async def format_inline_report(input_data: dict[str, Any]) -> dict[str, Any]:
    """
    Format inline analysis results as Slack blocks or PDF.

    Args:
        input_data: Contains analysis, competencies, output_format, user_id, report_metadata

    Returns:
        Formatted report ready for delivery
    """
    analysis = input_data.get("analysis", {})
    competencies = input_data.get("competencies", {})
    output_format = input_data.get("output_format", "slack_blocks")
    user_id = input_data.get("user_id", "")
    report_metadata = input_data.get("report_metadata", {})

    logger.info(
        f"Formatting inline report as {output_format} for user {user_id}",
        extra={"competency_count": competencies.get("competency_count", 0)},
    )

    try:
        if output_format == "slack_blocks":
            # Format as Slack Block Kit JSON
            content_preview = report_metadata.get("content_preview", analysis.get("content", ""))[
                :150
            ]
            competency_list = competencies.get("competencies", [])

            blocks = [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": "📊 Inline Activity Analysis",
                        "emoji": True,
                    },
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Activity:*\n>{content_preview}{'...' if len(content_preview) >= 150 else ''}",
                    },
                },
                {"type": "divider"},
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*Type:*\n{analysis.get('activity_type', 'General').replace('_', ' ').title()}",
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Confidence:*\n{analysis.get('confidence', 0):.0%}",
                        },
                    ],
                },
            ]

            # Add competencies section
            if competency_list:
                blocks.append(
                    {
                        "type": "section",
                        "text": {"type": "mrkdwn", "text": "*Demonstrated Competencies:*"},
                    }
                )

                for comp in competency_list[:5]:  # Show top 5
                    comp_name = comp.get("competency_name", "Unknown")
                    comp_level = comp.get("level", "Developing")
                    comp_score = comp.get("score", 0)

                    blocks.append(
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": f"• *{comp_name}*\n  Level: {comp_level} ({comp_score:.1f}/5.0)",
                            },
                        }
                    )

            # Add overall score
            overall_score = competencies.get("overall_score", 0)
            blocks.append({"type": "divider"})
            blocks.append(
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Overall Assessment:* {overall_score:.1f}/5.0",
                    },
                }
            )

            # Add recommendations if available
            recommendations = competencies.get("recommendations", [])
            if recommendations:
                blocks.append(
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "*Development Recommendations:*\n"
                            + "\n".join([f"• {rec}" for rec in recommendations[:3]]),
                        },
                    }
                )

            formatted_report = {
                "format": "slack_blocks",
                "blocks": blocks,
                "text": f"Inline Activity Analysis for user {user_id}",  # Fallback text
                "metadata": report_metadata,
            }

        else:
            # PDF format (simplified - would use PDF generator in production)
            formatted_report = {
                "format": "pdf",
                "title": "Inline Activity Analysis",
                "content": {
                    "activity": analysis.get("content", ""),
                    "activity_type": analysis.get("activity_type", "general"),
                    "confidence": analysis.get("confidence", 0),
                    "competencies": competencies.get("competencies", []),
                    "overall_score": competencies.get("overall_score", 0),
                    "recommendations": competencies.get("recommendations", []),
                },
                "metadata": report_metadata,
            }

        logger.info(f"Successfully formatted inline report as {output_format}")
        return formatted_report

    except Exception as e:
        logger.error(f"Failed to format inline report: {e}")
        # Return error message in Slack blocks format
        return {
            "format": "slack_blocks",
            "blocks": [
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": f"⚠️ *Error formatting report:* {str(e)}"},
                }
            ],
            "text": "Error formatting inline report",
            "error": str(e),
        }


@activity.defn
async def deliver_report(input_data: dict[str, Any]) -> dict[str, Any]:
    """
    Deliver formatted report to Slack channel or as file.

    Args:
        input_data: Contains formatted_report, user_id, channel_id, thread_ts,
                   delivery_method, report_type

    Returns:
        Delivery result with timestamp and delivery details
    """
    formatted_report = input_data.get("formatted_report", {})
    user_id = input_data.get("user_id", "")
    channel_id = input_data.get("channel_id")
    thread_ts = input_data.get("thread_ts")
    delivery_method = input_data.get("delivery_method", "slack")
    report_type = input_data.get("report_type", "inline_analysis")

    logger.info(
        f"Delivering {report_type} report via {delivery_method}",
        extra={"user_id": user_id, "channel_id": channel_id},
    )

    try:
        if delivery_method == "slack" and formatted_report.get("format") == "slack_blocks":
            # Use actual Slack client to post message
            from src.interfaces.slack.adapter import get_slack_adapter

            slack_adapter = await get_slack_adapter()
            start_time = time.time()

            # Post message with blocks
            response = await slack_adapter.app.client.chat_postMessage(
                channel=channel_id or user_id,
                blocks=formatted_report.get("blocks", []),
                text=formatted_report.get("text", "Inline Activity Analysis Report"),
                thread_ts=thread_ts,
            )

            processing_time = time.time() - start_time

            logger.info(
                "Delivered Slack blocks report successfully",
                extra={
                    "channel_id": response.get("channel"),
                    "message_ts": response.get("ts"),
                    "processing_time": processing_time,
                },
            )

            delivery_result = {
                "success": True,
                "delivery_method": "slack",
                "channel_id": response.get("channel"),
                "thread_ts": thread_ts,
                "message_ts": response.get("ts"),
                "delivered_at": datetime.now(UTC).isoformat(),
                "processing_time": processing_time,
                "report_type": report_type,
                "blocks_count": len(formatted_report.get("blocks", [])),
            }

        elif delivery_method == "file":
            # Generate and upload actual file to Slack
            import os

            from src.interfaces.slack.adapter import get_slack_adapter

            slack_adapter = await get_slack_adapter()
            start_time = time.time()

            # Get file path from formatted report
            file_path = formatted_report.get("file_path")
            if not file_path or not os.path.exists(file_path):
                raise ValueError(f"Report file not found: {file_path}")

            file_size = os.path.getsize(file_path)
            file_title = formatted_report.get(
                "title", f"{report_type.replace('_', ' ').title()} Report"
            )

            # Upload file to Slack
            response = await slack_adapter.app.client.files_upload_v2(
                channels=channel_id or user_id,
                file=file_path,
                title=file_title,
                initial_comment=f"📊 {file_title}",
                thread_ts=thread_ts,
            )

            processing_time = time.time() - start_time

            logger.info(
                "Delivered file report successfully",
                extra={
                    "file_path": file_path,
                    "file_size": file_size,
                    "processing_time": processing_time,
                },
            )

            delivery_result = {
                "success": True,
                "delivery_method": "file",
                "file_path": file_path,
                "file_size": file_size,
                "file_url": response.get("file", {}).get("permalink"),
                "delivered_at": datetime.now(UTC).isoformat(),
                "processing_time": processing_time,
                "report_type": report_type,
            }

        else:
            raise ValueError(f"Unsupported delivery method: {delivery_method}")

        logger.info(
            f"Successfully delivered {report_type} report",
            extra={"delivery_method": delivery_method},
        )

        return delivery_result

    except Exception as e:
        logger.error(f"Failed to deliver report: {e}")
        return {
            "success": False,
            "delivery_method": delivery_method,
            "error": str(e),
            "delivered_at": datetime.now(UTC).isoformat(),
        }


# =====================
# Quick Summary Activities
# For generating lightweight Slack-native competency summaries
# =====================


@activity.defn
async def fetch_summary_data(input_data: dict[str, Any]) -> dict[str, Any]:
    """
    Fetch lightweight summary data for quick Slack reports.

    Args:
        input_data: Contains user_id, summary_type, time_period, max_activities, max_competencies

    Returns:
        Summary data with recent activities and top competencies
    """
    user_id = input_data.get("user_id", "")
    summary_type = input_data.get("summary_type", "competency")
    time_period = input_data.get("time_period", "recent")
    max_activities = input_data.get("max_activities", 10)
    max_competencies = input_data.get("max_competencies", 5)

    logger.info(
        f"Fetching summary data for user {user_id}",
        extra={"summary_type": summary_type, "time_period": time_period},
    )

    start_time = time.time()

    try:
        (
            agent_registry,
            db_manager,
            redis_manager,
            llm_gateway,
            competency_assessor,
            recommendation_engine,
            activity_classifier,
        ) = await _get_services()

        # Calculate date range based on time_period
        end_date = datetime.now(UTC)
        if time_period == "this_week":
            start_date = end_date - timedelta(days=7)
        elif time_period == "this_month":
            start_date = end_date - timedelta(days=30)
        else:  # "recent"
            start_date = end_date - timedelta(days=14)  # Last 2 weeks

        # Fetch real data from ActivityRepository
        import uuid as uuid_lib

        from src.infrastructure.database.repositories.activity_repository import ActivityRepository

        activity_repo = ActivityRepository()

        # Convert user_id to UUID
        user_uuid = uuid_lib.UUID(user_id) if isinstance(user_id, str) else user_id

        # Fetch user activities from database
        activities = await activity_repo.get_user_activities(
            user_id=user_uuid,
            start_time=start_date,
            end_time=end_date,
            processing_status=["complete", "analyzed"],
        )

        logger.info(f"Retrieved {len(activities)} activities from repository for summary")

        # Aggregate competency data from real activities
        competency_map = {}
        recent_activities_list = []

        for user_activity in activities[:max_activities]:
            # Add to recent activities list
            recent_activities_list.append(
                {
                    "description": user_activity.content.get("description", user_activity.text)
                    if hasattr(user_activity, "content")
                    else user_activity.text,
                    "date": user_activity.timestamp.isoformat(),
                }
            )

            # Aggregate competencies
            if hasattr(user_activity, "competency_areas") and user_activity.competency_areas:
                for comp in user_activity.competency_areas:
                    if comp not in competency_map:
                        competency_map[comp] = {"count": 0, "recent_activity": None}
                    competency_map[comp]["count"] += 1
                    if not competency_map[comp]["recent_activity"]:
                        competency_map[comp]["recent_activity"] = user_activity

        # Calculate competency scores and levels
        top_competencies = []
        for comp_name, comp_data in sorted(
            competency_map.items(), key=lambda x: x[1]["count"], reverse=True
        )[:max_competencies]:
            activity_count = comp_data["count"]

            # Calculate score based on activity count (2.0 - 5.0 scale)
            score = min(5.0, 2.0 + (activity_count * 0.3))

            # Determine level
            if score >= 4.5:
                level = "Expert"
            elif score >= 4.0:
                level = "Advanced"
            elif score >= 3.0:
                level = "Proficient"
            else:
                level = "Developing"

            # Simple trend indicator (would need historical data for real trend)
            trend = "→"  # Stable for now

            top_competencies.append(
                {
                    "name": comp_name.replace("_", " ").title(),
                    "score": round(score, 1),
                    "level": level,
                    "trend": trend,
                }
            )

        # Calculate overall score
        overall_score = (
            sum(c["score"] for c in top_competencies) / len(top_competencies)
            if top_competencies
            else 0
        )

        summary_data = {
            "user_id": user_id,
            "summary_type": summary_type,
            "time_period": time_period,
            "date_range": {"start": start_date.isoformat(), "end": end_date.isoformat()},
            "top_competencies": top_competencies,
            "recent_activities": recent_activities_list,
            "overall_score": round(overall_score, 2),
            "activity_count": len(activities),
            "competency_count": len(competency_map),
            "processing_time": time.time() - start_time,
        }

        logger.info(
            f"Fetched summary data with {summary_data['activity_count']} activities",
            extra={"overall_score": summary_data["overall_score"]},
        )

        return summary_data

    except Exception as e:
        logger.error(f"Failed to fetch summary data: {e}")
        return {
            "user_id": user_id,
            "summary_type": summary_type,
            "error": str(e),
            "processing_time": time.time() - start_time,
        }


@activity.defn
async def format_slack_summary(input_data: dict[str, Any]) -> dict[str, Any]:
    """
    Format summary data as Slack Block Kit JSON.

    Args:
        input_data: Contains summary_data, summary_type, include_recommendations, user_id

    Returns:
        Formatted Slack blocks ready to post
    """
    summary_data = input_data.get("summary_data", {})
    input_data.get("summary_type", "competency")
    include_recommendations = input_data.get("include_recommendations", False)
    user_id = input_data.get("user_id", "")

    logger.info(f"Formatting Slack summary for user {user_id}")

    start_time = time.time()

    try:
        top_competencies = summary_data.get("top_competencies", [])
        recent_activities = summary_data.get("recent_activities", [])
        overall_score = summary_data.get("overall_score", 0)
        time_period = summary_data.get("time_period", "recent")

        # Build Slack blocks
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"📊 Competency Summary - {time_period.replace('_', ' ').title()}",
                    "emoji": True,
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Overall Score:* {overall_score:.1f}/5.0 {'⭐' * int(overall_score)}",
                },
            },
            {"type": "divider"},
            {"type": "section", "text": {"type": "mrkdwn", "text": "*Top Competencies:*"}},
        ]

        # Add top competencies
        for comp in top_competencies:
            comp_name = comp.get("name", "Unknown")
            comp_score = comp.get("score", 0)
            comp_level = comp.get("level", "Developing")
            comp_trend = comp.get("trend", "→")

            blocks.append(
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"• *{comp_name}* {comp_trend}\n  {comp_level} - {comp_score:.1f}/5.0",
                    },
                }
            )

        # Add recent activities
        if recent_activities:
            blocks.append({"type": "divider"})
            blocks.append(
                {"type": "section", "text": {"type": "mrkdwn", "text": "*Recent Activities:*"}}
            )

            for act in recent_activities[:5]:  # Show max 5
                act_date = datetime.fromisoformat(act["date"]).strftime("%b %d")
                blocks.append(
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"• {act['description']}\n  _{act_date}_",
                        },
                    }
                )

        # Add recommendations if requested
        if include_recommendations:
            blocks.append({"type": "divider"})
            blocks.append(
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*💡 Quick Recommendations:*\n• Continue building leadership experience\n• Focus on advanced system design patterns\n• Consider technical mentorship opportunities",
                    },
                }
            )

        # Add footer
        blocks.append({"type": "divider"})
        blocks.append(
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"Generated on {datetime.now(UTC).strftime('%B %d, %Y at %I:%M %p UTC')} | Want a detailed PDF report? Ask me to 'generate a full report'",
                    }
                ],
            }
        )

        formatted_result = {
            "blocks": blocks,
            "text": f"Competency Summary for user {user_id}",  # Fallback text
            "processing_time": time.time() - start_time,
        }

        logger.info(f"Formatted {len(blocks)} Slack blocks")
        return formatted_result

    except Exception as e:
        logger.error(f"Failed to format Slack summary: {e}")
        # Return error block
        return {
            "blocks": [
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": f"⚠️ *Error formatting summary:* {str(e)}"},
                }
            ],
            "text": "Error formatting summary",
            "error": str(e),
            "processing_time": time.time() - start_time,
        }


@activity.defn
async def post_slack_message(input_data: dict[str, Any]) -> dict[str, Any]:
    """
    Post formatted message to Slack channel.

    Args:
        input_data: Contains blocks, text, channel_id, thread_ts, user_id

    Returns:
        Slack post result with message_ts and channel_id
    """
    blocks = input_data.get("blocks", [])
    text = input_data.get("text", "Message")
    channel_id = input_data.get("channel_id")
    thread_ts = input_data.get("thread_ts")
    user_id = input_data.get("user_id", "")

    logger.info(
        f"Posting Slack message to channel {channel_id}",
        extra={"user_id": user_id, "block_count": len(blocks)},
    )

    start_time = time.time()

    try:
        # Use actual Slack client to post message
        from src.interfaces.slack.adapter import get_slack_adapter

        slack_adapter = await get_slack_adapter()

        # Post message with blocks to Slack
        response = await slack_adapter.app.client.chat_postMessage(
            channel=channel_id or user_id, blocks=blocks, text=text, thread_ts=thread_ts
        )

        result = {
            "success": True,
            "message_ts": response.get("ts"),
            "channel_id": response.get("channel"),
            "thread_ts": thread_ts,
            "delivered_at": datetime.now(UTC).isoformat(),
            "processing_time": time.time() - start_time,
            "blocks_posted": len(blocks),
        }

        logger.info(
            "Successfully posted Slack message",
            extra={"message_ts": result["message_ts"], "channel_id": result["channel_id"]},
        )

        return result

    except Exception as e:
        logger.error(f"Failed to post Slack message: {e}")
        return {
            "success": False,
            "error": str(e),
            "delivered_at": datetime.now(UTC).isoformat(),
            "processing_time": time.time() - start_time,
        }


# Export all activity functions for workflows to import
__all__ = [
    "analyze_activity",
    "assess_competency",
    "generate_advice",
    "synthesize_insights",
    "fetch_context",
    "process_batch_item",
    "combined_analysis",
    "combined_advisory",
    "chat_response",
    "aggregate_report_data",
    "generate_pdf_report",
    "save_report_to_database",
    "upload_report_to_slack",
    "send_report_notification",
    # Inline analysis activities
    "analyze_inline_content",
    "assess_content_competencies",
    "format_inline_report",
    "deliver_report",
    # Quick summary activities
    "fetch_summary_data",
    "format_slack_summary",
    "post_slack_message",
]
