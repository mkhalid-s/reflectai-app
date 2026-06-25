"""
Temporal Workflow Definitions for ReflectAI

Defines workflow logic using Temporal.io patterns with @workflow.defn decorators.
"""

import asyncio
from datetime import timedelta
from typing import Any

from temporalio import workflow
from temporalio.common import RetryPolicy

from src.shared.logging import get_logger

from .models import (
    WorkflowRequest,
)

logger = get_logger(__name__)


# Common retry policy for all activities
DEFAULT_RETRY_POLICY = RetryPolicy(
    initial_interval=timedelta(seconds=1),
    backoff_coefficient=2.0,
    maximum_interval=timedelta(seconds=60),
    maximum_attempts=3,
)


@workflow.defn
class SequentialAnalysisWorkflow:
    """Sequential workflow for analyzing activities and generating insights."""

    @workflow.run
    async def run(self, request: WorkflowRequest) -> dict[str, Any]:
        """Execute sequential analysis workflow."""
        workflow_id = workflow.info().workflow_id
        logger.info(f"Starting sequential analysis workflow {workflow_id}")

        # Import activity functions (will be defined in activities.py)
        from .activities import (
            analyze_activity,
            assess_competency,
            generate_advice,
            synthesize_insights,
        )

        # Step 1: Analyze activity
        activity_text = request.input_data.get("activity_text", "")
        analysis_result = await workflow.execute_activity(
            analyze_activity,
            {"activity_text": activity_text, "context": request.input_data},
            start_to_close_timeout=timedelta(minutes=2),
            retry_policy=DEFAULT_RETRY_POLICY,
        )

        # Step 2: Assess competencies
        competency_result = await workflow.execute_activity(
            assess_competency,
            {"activity_limit": 50, "user_id": request.user_id, "context": request.input_data},
            start_to_close_timeout=timedelta(minutes=2),
            retry_policy=DEFAULT_RETRY_POLICY,
        )

        # Step 3: Generate advice
        advice_result = await workflow.execute_activity(
            generate_advice,
            {
                "competencies": competency_result.get("competencies", {}),
                "gaps": competency_result.get("gaps", []),
                "user_goal": request.input_data.get("user_goal", "Career growth"),
                "analysis": analysis_result,
            },
            start_to_close_timeout=timedelta(minutes=2),
            retry_policy=DEFAULT_RETRY_POLICY,
        )

        # Step 4: Synthesize insights
        synthesis_result = await workflow.execute_activity(
            synthesize_insights,
            {
                "analysis_results": analysis_result,
                "competency_assessment": competency_result,
                "advice": advice_result.get("advice", ""),
            },
            start_to_close_timeout=timedelta(minutes=2),
            retry_policy=DEFAULT_RETRY_POLICY,
        )

        return {
            "analysis": analysis_result,
            "competencies": competency_result,
            "advice": advice_result,
            "synthesis": synthesis_result,
            "total_llm_cost": sum(
                [
                    analysis_result.get("llm_cost", 0),
                    competency_result.get("llm_cost", 0),
                    advice_result.get("llm_cost", 0),
                    synthesis_result.get("llm_cost", 0),
                ]
            ),
        }


@workflow.defn
class ParallelAnalysisWorkflow:
    """Parallel workflow for concurrent activity processing."""

    @workflow.run
    async def run(self, request: WorkflowRequest) -> dict[str, Any]:
        """Execute parallel analysis workflow."""
        workflow_id = workflow.info().workflow_id
        logger.info(f"Starting parallel analysis workflow {workflow_id}")

        from .activities import analyze_activity, assess_competency, generate_advice

        # Execute analysis and competency assessment in parallel
        analysis_task = workflow.execute_activity(
            analyze_activity,
            {"activity_text": request.input_data.get("activity_text", "")},
            start_to_close_timeout=timedelta(minutes=2),
            retry_policy=DEFAULT_RETRY_POLICY,
        )

        competency_task = workflow.execute_activity(
            assess_competency,
            {"activity_limit": 50, "user_id": request.user_id},
            start_to_close_timeout=timedelta(minutes=2),
            retry_policy=DEFAULT_RETRY_POLICY,
        )

        # Wait for both to complete
        analysis_result, competency_result = await asyncio.gather(analysis_task, competency_task)

        # Generate advice based on results
        advice_result = await workflow.execute_activity(
            generate_advice,
            {
                "competencies": competency_result.get("competencies", {}),
                "gaps": competency_result.get("gaps", []),
                "analysis": analysis_result,
            },
            start_to_close_timeout=timedelta(minutes=2),
            retry_policy=DEFAULT_RETRY_POLICY,
        )

        return {
            "analysis": analysis_result,
            "competencies": competency_result,
            "advice": advice_result,
            "execution_pattern": "parallel",
        }


@workflow.defn
class BatchProcessingWorkflow:
    """Workflow for processing multiple items in batch."""

    @workflow.run
    async def run(self, request: WorkflowRequest) -> dict[str, Any]:
        """Execute batch processing workflow."""
        workflow_id = workflow.info().workflow_id
        logger.info(f"Starting batch processing workflow {workflow_id}")

        if not request.batch_items:
            return {"error": "No batch items provided", "processed": 0}

        from .activities import process_batch_item

        # Process items in batches
        batch_size = 10
        results = []

        for i in range(0, len(request.batch_items), batch_size):
            batch = request.batch_items[i : i + batch_size]

            # Process batch items in parallel
            batch_tasks = []
            for item in batch:
                task = workflow.execute_activity(
                    process_batch_item,
                    item,
                    start_to_close_timeout=timedelta(seconds=30),
                    retry_policy=DEFAULT_RETRY_POLICY,
                )
                batch_tasks.append(task)

            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            results.extend(batch_results)

        # Aggregate results
        successful = [r for r in results if isinstance(r, dict) and r.get("success")]
        failed = [r for r in results if not (isinstance(r, dict) and r.get("success"))]

        return {
            "processed": len(results),
            "successful": len(successful),
            "failed": len(failed),
            "results": results[:10],  # Return first 10 for summary
            "batch_id": request.input_data.get("batch_id"),
        }


@workflow.defn
class ConversationWorkflow:
    """Workflow for handling conversational interactions."""

    @workflow.run
    async def run(self, request: WorkflowRequest) -> dict[str, Any]:
        """Execute conversation workflow."""
        workflow_id = workflow.info().workflow_id
        logger.info(f"Starting conversation workflow {workflow_id}")

        from .activities import analyze_activity, fetch_context, generate_advice

        # Step 1: Fetch conversation context
        context_result = await workflow.execute_activity(
            fetch_context,
            {
                "thread_ts": request.thread_ts,
                "channel_id": request.input_data.get("channel_id", ""),
            },
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=DEFAULT_RETRY_POLICY,
        )

        # Step 2: Analyze user message with context
        message_text = request.input_data.get("message_text", "")
        conversation_history = context_result.get("messages", [])

        analysis_result = await workflow.execute_activity(
            analyze_activity,
            {"activity_text": message_text, "context": conversation_history},
            start_to_close_timeout=timedelta(minutes=2),
            retry_policy=DEFAULT_RETRY_POLICY,
        )

        # Step 3: Generate contextual response
        response_needed = analysis_result.get("classification") != "greeting"

        if response_needed:
            advice_result = await workflow.execute_activity(
                generate_advice,
                {
                    "analysis": analysis_result,
                    "conversation_context": context_result,
                    "user_question": message_text,
                },
                start_to_close_timeout=timedelta(minutes=2),
                retry_policy=DEFAULT_RETRY_POLICY,
            )
        else:
            advice_result = {
                "advice": "Hello! How can I help you with your professional development today?"
            }

        return {
            "conversation_context": context_result,
            "analysis": analysis_result,
            "response": advice_result.get("advice", ""),
            "thread_ts": request.thread_ts,
            "should_create_thread": response_needed and not request.thread_ts,
        }


@workflow.defn
class OptimizedAnalysisWorkflow:
    """Optimized workflow using combined agents for 60% faster execution."""

    @workflow.run
    async def run(self, request: WorkflowRequest) -> dict[str, Any]:
        """Execute optimized analysis workflow with combined agent."""
        workflow_id = workflow.info().workflow_id
        logger.info(f"Starting optimized analysis workflow {workflow_id}")

        from .activities import combined_advisory, combined_analysis

        # Single combined analysis activity
        activity_text = request.input_data.get("activity_text", "")
        analysis_result = await workflow.execute_activity(
            combined_analysis,
            {
                "activity_text": activity_text,
                "analysis_type": "comprehensive",
                "context": request.input_data.get("context", {}),
                "user_goals": request.input_data.get("user_goals", []),
            },
            start_to_close_timeout=timedelta(minutes=2),
            retry_policy=DEFAULT_RETRY_POLICY,
        )

        # Combined advisory activity
        advisory_result = await workflow.execute_activity(
            combined_advisory,
            {
                "analysis_results": analysis_result,
                "user_goals": request.input_data.get("user_goals", ["Career growth"]),
                "advisory_type": "comprehensive",
                "context": request.input_data.get("context", {}),
            },
            start_to_close_timeout=timedelta(minutes=2),
            retry_policy=DEFAULT_RETRY_POLICY,
        )

        return {
            "combined_analysis": analysis_result,
            "combined_advisory": advisory_result,
            "optimization_stats": {
                "agents_used": 2,
                "execution_pattern": "combined_optimized",
                "estimated_time_savings": "60%",
                "estimated_cost_savings": analysis_result.get("cost_savings", "30-50%"),
            },
            "total_llm_cost": analysis_result.get("llm_cost", 0)
            + advisory_result.get("llm_cost", 0),
        }


@workflow.defn
class ReportGenerationWorkflow:
    """Workflow for generating and delivering competency reports."""

    @workflow.run
    async def run(self, request: WorkflowRequest) -> dict[str, Any]:
        """Execute report generation workflow."""
        workflow_id = workflow.info().workflow_id
        logger.info(f"Starting report generation workflow {workflow_id}")

        from .activities import (
            aggregate_report_data,
            generate_pdf_report,
            save_report_to_database,
            send_report_notification,
            upload_report_to_slack,
        )

        # Step 1: Aggregate report data
        logger.info(f"Aggregating report data for user {request.user_id}")
        report_data = await workflow.execute_activity(
            aggregate_report_data,
            {
                "user_id": request.user_id,
                "report_type": request.input_data.get("report_type", "competency_assessment"),
                "date_range_days": request.input_data.get("date_range_days", 90),
                "include_recommendations": request.input_data.get("include_recommendations", True),
            },
            start_to_close_timeout=timedelta(minutes=2),
            retry_policy=DEFAULT_RETRY_POLICY,
        )

        # Step 2: Generate PDF report
        logger.info(f"Generating PDF report for user {request.user_id}")
        pdf_result = await workflow.execute_activity(
            generate_pdf_report,
            report_data,
            start_to_close_timeout=timedelta(minutes=3),
            retry_policy=DEFAULT_RETRY_POLICY,
        )

        # Step 3: Save report to database
        logger.info(f"Saving report {pdf_result['report_id']} to database")
        db_result = await workflow.execute_activity(
            save_report_to_database,
            {
                "report_id": pdf_result["report_id"],
                "user_id": request.user_id,
                "file_path": pdf_result["file_path"],
                "file_size": pdf_result["file_size"],
                "report_type": report_data["report_type"],
                "content": report_data,
            },
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=DEFAULT_RETRY_POLICY,
        )

        # Step 4: Upload to Slack
        logger.info(f"Uploading report to Slack for user {request.user_id}")
        slack_result = await workflow.execute_activity(
            upload_report_to_slack,
            {
                "file_path": pdf_result["file_path"],
                "user_id": request.user_id,
                "report_title": pdf_result["title"],
                "report_type": report_data["report_type"],
                "channel_id": request.input_data.get("channel_id"),
            },
            start_to_close_timeout=timedelta(minutes=1),
            retry_policy=DEFAULT_RETRY_POLICY,
        )

        # Step 5: Send notification
        logger.info(f"Sending report notification to user {request.user_id}")
        await workflow.execute_activity(
            send_report_notification,
            {
                "user_id": request.user_id,
                "report_id": db_result["report_id"],
                "report_type": report_data["report_type"],
                "slack_file_url": slack_result["file_url"],
                "channel_id": request.input_data.get("channel_id"),
            },
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=DEFAULT_RETRY_POLICY,
        )

        return {
            "success": True,
            "report_id": db_result["report_id"],
            "file_path": pdf_result["file_path"],
            "file_size": pdf_result["file_size"],
            "slack_file_url": slack_result["file_url"],
            "generation_time": pdf_result["generation_time"],
            "report_type": report_data["report_type"],
            "delivered_at": slack_result["delivered_at"],
        }


@workflow.defn
class InlineAnalysisReportWorkflow:
    """
    Workflow for analyzing inline activity content and generating instant reports.

    This workflow handles the inline analysis use case where users provide
    activity descriptions directly in their messages (e.g., "Analyze this: I implemented OAuth2").
    It extracts, analyzes, and delivers competency insights in real-time.

    Flow:
    1. analyze_inline_content - Parse and analyze the provided content
    2. assess_content_competencies - Identify demonstrated competencies
    3. format_inline_report - Format results as Slack blocks or PDF
    4. deliver_report - Send to Slack channel or thread

    Example usage:
        User: "Analyze this: I led the implementation of a microservices platform"
        Result: Instant competency assessment delivered to Slack
    """

    @workflow.run
    async def run(self, request: WorkflowRequest) -> dict[str, Any]:
        """Execute inline analysis report workflow."""
        workflow_id = workflow.info().workflow_id
        logger.info(f"Starting inline analysis report workflow {workflow_id}")

        from .activities import (
            analyze_inline_content,
            assess_content_competencies,
            deliver_report,
            format_inline_report,
        )

        # Extract content from request
        inline_content = request.input_data.get("inline_content", "")
        content_metadata = request.input_data.get("content_metadata", {})
        output_format = request.input_data.get("output_format", "slack_blocks")

        logger.info(
            f"Processing inline content analysis for user {request.user_id}",
            extra={
                "content_length": len(inline_content),
                "extraction_method": content_metadata.get("extraction_method"),
                "confidence": content_metadata.get("confidence"),
                "output_format": output_format,
            },
        )

        # Step 1: Analyze inline content
        logger.info(f"Analyzing inline content: {inline_content[:100]}...")
        analysis_result = await workflow.execute_activity(
            analyze_inline_content,
            {
                "content": inline_content,
                "content_metadata": content_metadata,
                "user_id": request.user_id,
                "context": request.input_data.get("context", {}),
            },
            start_to_close_timeout=timedelta(minutes=2),
            retry_policy=DEFAULT_RETRY_POLICY,
        )

        # Step 2: Assess competencies from the content
        logger.info("Assessing competencies from analyzed content")
        competency_result = await workflow.execute_activity(
            assess_content_competencies,
            {
                "analysis": analysis_result,
                "content": inline_content,
                "user_id": request.user_id,
                "include_gaps": request.input_data.get("include_gap_analysis", True),
            },
            start_to_close_timeout=timedelta(minutes=2),
            retry_policy=DEFAULT_RETRY_POLICY,
        )

        # Step 3: Format the inline report
        logger.info(f"Formatting inline report as {output_format}")
        format_result = await workflow.execute_activity(
            format_inline_report,
            {
                "analysis": analysis_result,
                "competencies": competency_result,
                "output_format": output_format,
                "user_id": request.user_id,
                "report_metadata": {
                    "extraction_method": content_metadata.get("extraction_method"),
                    "confidence": content_metadata.get("confidence"),
                    "content_preview": inline_content[:200],
                },
            },
            start_to_close_timeout=timedelta(minutes=1),
            retry_policy=DEFAULT_RETRY_POLICY,
        )

        # Step 4: Deliver the report
        logger.info(f"Delivering inline report to user {request.user_id}")
        delivery_result = await workflow.execute_activity(
            deliver_report,
            {
                "formatted_report": format_result,
                "user_id": request.user_id,
                "channel_id": request.input_data.get("channel_id"),
                "thread_ts": request.thread_ts,
                "delivery_method": "slack" if output_format == "slack_blocks" else "file",
                "report_type": "inline_analysis",
            },
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=DEFAULT_RETRY_POLICY,
        )

        return {
            "success": True,
            "workflow_type": "inline_analysis",
            "content_analyzed": inline_content[:200],
            "analysis": analysis_result,
            "competencies": competency_result.get("competencies", []),
            "competency_count": len(competency_result.get("competencies", [])),
            "gaps_identified": competency_result.get("gaps", []),
            "formatted_report": format_result,
            "delivery": delivery_result,
            "total_llm_cost": (
                analysis_result.get("llm_cost", 0) + competency_result.get("llm_cost", 0)
            ),
            "processing_time": delivery_result.get("processing_time"),
            "delivered_at": delivery_result.get("delivered_at"),
        }


@workflow.defn
class QuickSummaryWorkflow:
    """
    Workflow for generating quick Slack-native competency summaries.

    This workflow provides lightweight, instant feedback without PDF generation.
    Designed for quick status checks and casual progress reviews delivered
    directly in Slack using Block Kit formatting.

    Flow:
    1. fetch_summary_data - Get recent activities and competency snapshot
    2. format_slack_summary - Format as rich Slack blocks
    3. post_slack_message - Post directly to Slack channel

    Example usage:
        User: "Show me my competency summary"
        Result: Instant Slack blocks with top competencies, recent activities

    Differences from ReportGenerationWorkflow:
    - No PDF generation (faster)
    - Slack-only output
    - Simplified data aggregation
    - 30-60 second execution vs 5 minutes
    """

    @workflow.run
    async def run(self, request: WorkflowRequest) -> dict[str, Any]:
        """Execute quick summary workflow."""
        workflow_id = workflow.info().workflow_id
        logger.info(f"Starting quick summary workflow {workflow_id}")

        from .activities import fetch_summary_data, format_slack_summary, post_slack_message

        # Extract parameters from request
        user_id = request.user_id
        summary_type = request.input_data.get("summary_type", "competency")
        time_period = request.input_data.get(
            "time_period", "recent"
        )  # recent, this_week, this_month
        include_recommendations = request.input_data.get("include_recommendations", False)

        logger.info(
            f"Processing quick summary for user {user_id}",
            extra={
                "summary_type": summary_type,
                "time_period": time_period,
                "include_recommendations": include_recommendations,
            },
        )

        # Step 1: Fetch summary data
        logger.info(f"Fetching summary data for user {user_id}")
        summary_data = await workflow.execute_activity(
            fetch_summary_data,
            {
                "user_id": user_id,
                "summary_type": summary_type,
                "time_period": time_period,
                "max_activities": 10,  # Keep it lightweight
                "max_competencies": 5,  # Show top 5 only
            },
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=DEFAULT_RETRY_POLICY,
        )

        # Step 2: Format as Slack blocks
        logger.info("Formatting Slack summary")
        formatted_blocks = await workflow.execute_activity(
            format_slack_summary,
            {
                "summary_data": summary_data,
                "summary_type": summary_type,
                "include_recommendations": include_recommendations,
                "user_id": user_id,
            },
            start_to_close_timeout=timedelta(seconds=15),
            retry_policy=DEFAULT_RETRY_POLICY,
        )

        # Step 3: Post to Slack
        logger.info("Posting summary to Slack")
        slack_result = await workflow.execute_activity(
            post_slack_message,
            {
                "blocks": formatted_blocks.get("blocks", []),
                "text": formatted_blocks.get("text", "Competency Summary"),
                "channel_id": request.input_data.get("channel_id"),
                "thread_ts": request.thread_ts,
                "user_id": user_id,
            },
            start_to_close_timeout=timedelta(seconds=15),
            retry_policy=DEFAULT_RETRY_POLICY,
        )

        return {
            "success": True,
            "workflow_type": "quick_summary",
            "summary_type": summary_type,
            "time_period": time_period,
            "competency_count": summary_data.get("competency_count", 0),
            "activity_count": summary_data.get("activity_count", 0),
            "slack_result": slack_result,
            "message_ts": slack_result.get("message_ts"),
            "channel_id": slack_result.get("channel_id"),
            "delivered_at": slack_result.get("delivered_at"),
            "total_processing_time": (
                summary_data.get("processing_time", 0)
                + formatted_blocks.get("processing_time", 0)
                + slack_result.get("processing_time", 0)
            ),
        }
