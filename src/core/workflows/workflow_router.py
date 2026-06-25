"""
Workflow Router for ReflectAI

Routes user requests to appropriate workflows based on content analysis,
user context, and system state. Integrates with Temporal workflows.
"""

import uuid
from dataclasses import dataclass
from enum import Enum
from typing import Any

from src.services.workflow.models import (
    WorkflowRequest,
    WorkflowResponse,
    WorkflowStatus,
    WorkflowType,
)
from src.shared import get_config, get_logger

# Try to import temporal client, use fallback if not available
try:
    from src.services.workflow.temporal_client import get_temporal_client

    TEMPORAL_AVAILABLE = True
except ImportError:
    TEMPORAL_AVAILABLE = False
    import warnings

    warnings.warn(
        "Temporal workflow client not available. Workflow routing will use fallback implementation.",
        ImportWarning,
        stacklevel=2,
    )

    def get_temporal_client():
        """Fallback temporal client."""
        return None


from src.core.classification.intent_analyzer import get_intent_analyzer
from src.core.conversation.intelligence import ConversationIntelligence

logger = get_logger(__name__)


class RoutingDecision(Enum):
    """Possible routing decisions for user requests."""

    GREETING = "greeting"
    HELP = "help"
    SEQUENTIAL_ANALYSIS = "sequential_analysis"
    BATCH_ANALYSIS = "batch_analysis"
    CONVERSATION = "conversation"
    REPORT_GENERATION = "report_generation"
    INLINE_ANALYSIS = "inline_analysis"
    QUICK_SUMMARY = "quick_summary"
    ERROR = "error"


@dataclass
class RoutingContext:
    """Context for routing decisions."""

    user_id: str
    content: str
    thread_id: str | None = None
    channel_type: str = "channel"
    user_profile: dict[str, Any] | None = None
    conversation_history: list[dict[str, Any]] | None = None
    correlation_id: str | None = None
    priority: int = 0
    metadata: dict[str, Any] | None = None


@dataclass
class RoutingResult:
    """Result of workflow routing decision."""

    decision: RoutingDecision
    workflow_id: str | None = None
    workflow_type: WorkflowType | None = None
    estimated_cost: float | None = None
    estimated_duration: int | None = None
    message: str | None = None
    requires_confirmation: bool = False


class WorkflowRouter:
    """
    Routes user requests to appropriate workflows.

    Analyzes user input, context, and system state to determine
    the best workflow execution strategy.
    """

    def __init__(self):
        self.config = get_config()
        self.temporal_client = None
        self.intent_analyzer = get_intent_analyzer()
        self.conversation_intelligence = ConversationIntelligence()

        # Routing configuration
        self.batch_threshold = 5  # Number of items to trigger batch processing
        self.cost_threshold = 1.0  # USD cost threshold for confirmation

        # Active workflows tracking
        self.active_workflows: dict[str, WorkflowResponse] = {}

    async def initialize(self):
        """Initialize the workflow router."""
        try:
            # Initialize temporal client if available
            if TEMPORAL_AVAILABLE:
                self.temporal_client = await get_temporal_client()
            else:
                self.temporal_client = None

            # Intent analyzer is already initialized via get_intent_analyzer()
            # Conversation intelligence uses existing components

            logger.info(
                "Workflow router initialized successfully",
                temporal_available=self.temporal_client is not None,
                temporal_client_available=TEMPORAL_AVAILABLE,
            )

        except Exception as e:
            logger.error(f"Failed to initialize workflow router: {e}")
            raise

    async def route_request(self, context: RoutingContext) -> RoutingResult:
        """
        Route a user request to the appropriate workflow.

        Args:
            context: The routing context containing user request and metadata

        Returns:
            RoutingResult with the routing decision and workflow details
        """
        try:
            logger.info(
                f"Routing request for user {context.user_id}",
                extra={
                    "correlation_id": context.correlation_id,
                    "content_length": len(context.content),
                    "has_thread": context.thread_id is not None,
                },
            )

            # Step 1: Use ConversationIntelligence for sophisticated intent analysis
            intent_analysis_result = await self.conversation_intelligence.analyze_message(
                message=context.content,
                user_id=context.user_id,
                thread_id=context.thread_id,
                channel_id=context.metadata.get("channel_id") if context.metadata else None,
            )

            # Step 2: Check for simple responses that don't need workflows
            if intent_analysis_result.intent.value == "general_chat":
                return RoutingResult(
                    decision=RoutingDecision.GREETING,
                    message="Hello! I'm here to help you analyze your competencies and career development.",
                )

            if intent_analysis_result.intent.value == "help_request":
                return RoutingResult(
                    decision=RoutingDecision.HELP,
                    message="I can help you analyze activities, assess competencies, provide career advice, generate reports, and more. Try asking me about your recent work or projects!",
                )

            # Step 3: Check for ongoing conversation
            if context.thread_id and intent_analysis_result.intent.value == "conversation":
                return await self._route_conversation(context, intent_analysis_result)

            # Step 4: Route based on intent type from sophisticated analyzer
            return await self._route_by_intent_type(context, intent_analysis_result)

        except Exception as e:
            logger.error(f"Error routing request: {e}", exc_info=True)
            return RoutingResult(
                decision=RoutingDecision.ERROR,
                message="I encountered an error processing your request. Please try again.",
            )

    async def _route_by_intent_type(
        self, context: RoutingContext, intent_result: Any
    ) -> RoutingResult:
        """Route based on sophisticated intent analysis result."""

        intent_type = intent_result.intent.value

        # Check if inline content was extracted - route to inline analysis workflow
        if hasattr(intent_result, "extracted_content") and intent_result.extracted_content:
            logger.info(
                "Inline content detected, routing to inline analysis workflow",
                extra={
                    "content_length": len(intent_result.extracted_content.get("raw_text", "")),
                    "extraction_method": intent_result.extracted_content.get("extraction_method"),
                    "confidence": intent_result.extracted_content.get("confidence"),
                },
            )
            return await self._route_inline_analysis(context, intent_result)

        # Map intent types to routing decisions
        if intent_type in ["activity_classification", "competency_analysis"]:
            # Determine if batch processing is needed
            if (
                self._should_use_batch_processing(context)
                or not intent_result.needs_clarification
            ):
                return await self._route_batch_analysis(context, intent_result)
            else:
                return await self._route_sequential_analysis(context, intent_result)

        elif intent_type == "career_advice":
            return await self._route_career_advice_workflow(context, intent_result)

        elif intent_type == "report_request":
            # Distinguish between quick summary and full PDF report based on user language
            # Quick summary keywords: "summary", "show me", "what are", "top skills"
            # Full report keywords: "generate report", "pdf", "full report", "detailed"
            content_lower = context.content.lower()
            is_quick_summary = any(
                keyword in content_lower
                for keyword in [
                    "summary",
                    "show me",
                    "what are my",
                    "top skills",
                    "top competencies",
                    "how am i",
                    "quick",
                    "status",
                ]
            ) and not any(
                keyword in content_lower
                for keyword in [
                    "pdf",
                    "generate report",
                    "full report",
                    "detailed report",
                    "comprehensive",
                ]
            )

            if is_quick_summary:
                logger.info("Routing to quick summary (lightweight Slack report)")
                return await self._route_quick_summary(context, intent_result)
            else:
                logger.info("Routing to full report generation (PDF)")
                return await self._route_report_generation(context, intent_result)

        elif intent_type == "goal_management":
            return await self._route_goal_management(context, intent_result)

        elif intent_type == "resource_discovery":
            return await self._route_resource_discovery(context, intent_result)

        else:
            # Default to sequential analysis for unknown intents
            return await self._route_sequential_analysis(context, intent_result)

    async def _route_sequential_analysis(
        self, context: RoutingContext, intent_result: Any
    ) -> RoutingResult:
        """Route to sequential analysis workflow."""

        workflow_id = f"seq_analysis_{uuid.uuid4().hex[:8]}"

        # Create workflow request
        workflow_request = WorkflowRequest(
            workflow_type=WorkflowType.SEQUENTIAL_ANALYSIS,
            user_id=context.user_id,
            team_id=context.user_profile.get("team_id", "default")
            if context.user_profile
            else "default",
            correlation_id=context.correlation_id or workflow_id,
            input_data={
                "content": context.content,
                "intent": intent_result.__dict__
                if hasattr(intent_result, "__dict__")
                else str(intent_result),
                "user_profile": context.user_profile,
                "conversation_history": context.conversation_history,
            },
            conversation_id=context.thread_id,
            thread_ts=context.thread_id,
            priority=context.priority,
        )

        # Start workflow
        try:
            from src.services.workflow.workflows import SequentialAnalysisWorkflow

            workflow_response = await self.temporal_client.start_workflow(
                SequentialAnalysisWorkflow, workflow_request, workflow_id
            )

            # Track active workflow
            self.active_workflows[workflow_id] = workflow_response

            return RoutingResult(
                decision=RoutingDecision.SEQUENTIAL_ANALYSIS,
                workflow_id=workflow_id,
                workflow_type=WorkflowType.SEQUENTIAL_ANALYSIS,
                estimated_duration=120,  # 2 minutes
                estimated_cost=0.15,  # $0.15 USD
            )

        except Exception as e:
            logger.error(f"Failed to start sequential analysis workflow: {e}")
            return RoutingResult(
                decision=RoutingDecision.ERROR,
                message="Unable to start analysis workflow. Please try again.",
            )

    async def _route_batch_analysis(
        self, context: RoutingContext, intent_result: Any
    ) -> RoutingResult:
        """Route to batch analysis workflow."""

        workflow_id = f"batch_analysis_{uuid.uuid4().hex[:8]}"

        # Extract batch items from context
        batch_items = self._extract_batch_items(context)
        estimated_cost = len(batch_items) * 0.10  # $0.10 per item

        workflow_request = WorkflowRequest(
            workflow_type=WorkflowType.BATCH_PROCESSING,
            user_id=context.user_id,
            team_id=context.user_profile.get("team_id", "default")
            if context.user_profile
            else "default",
            correlation_id=context.correlation_id or workflow_id,
            input_data={"content": context.content, "batch_items": batch_items},
            batch_items=batch_items,
            priority=context.priority,
            timeout_seconds=600,  # 10 minutes for batch processing
        )

        # Check if cost requires confirmation
        requires_confirmation = estimated_cost > self.cost_threshold

        if not requires_confirmation:
            # Start workflow immediately
            try:
                from src.services.workflow.workflows import BatchProcessingWorkflow

                workflow_response = await self.temporal_client.start_workflow(
                    BatchProcessingWorkflow, workflow_request, workflow_id
                )

                self.active_workflows[workflow_id] = workflow_response

            except Exception as e:
                logger.error(f"Failed to start batch analysis workflow: {e}")
                return RoutingResult(
                    decision=RoutingDecision.ERROR,
                    message="Unable to start batch analysis workflow.",
                )

        return RoutingResult(
            decision=RoutingDecision.BATCH_ANALYSIS,
            workflow_id=workflow_id if not requires_confirmation else None,
            workflow_type=WorkflowType.BATCH_PROCESSING,
            estimated_cost=estimated_cost,
            estimated_duration=len(batch_items) * 30,  # 30 seconds per item
            requires_confirmation=requires_confirmation,
            message=f"Batch processing {len(batch_items)} items"
            + (f" (estimated cost: ${estimated_cost:.2f})" if requires_confirmation else ""),
        )

    async def _route_conversation(
        self, context: RoutingContext, intent_result: Any
    ) -> RoutingResult:
        """Route to conversation workflow."""

        workflow_id = f"conversation_{uuid.uuid4().hex[:8]}"

        workflow_request = WorkflowRequest(
            workflow_type=WorkflowType.CONVERSATION,
            user_id=context.user_id,
            team_id=context.user_profile.get("team_id", "default")
            if context.user_profile
            else "default",
            correlation_id=context.correlation_id or workflow_id,
            input_data={
                "content": context.content,
                "conversation_history": context.conversation_history,
                "thread_id": context.thread_id,
            },
            conversation_id=context.thread_id,
            thread_ts=context.thread_id,
        )

        try:
            from src.services.workflow.workflows import ConversationWorkflow

            workflow_response = await self.temporal_client.start_workflow(
                ConversationWorkflow, workflow_request, workflow_id
            )

            self.active_workflows[workflow_id] = workflow_response

            return RoutingResult(
                decision=RoutingDecision.CONVERSATION,
                workflow_id=workflow_id,
                workflow_type=WorkflowType.CONVERSATION,
                estimated_duration=30,  # 30 seconds
            )

        except Exception as e:
            logger.error(f"Failed to start conversation workflow: {e}")
            return RoutingResult(
                decision=RoutingDecision.ERROR, message="Unable to continue conversation."
            )

    async def cancel_workflow(self, workflow_id: str) -> bool:
        """Cancel a running workflow."""
        try:
            success = await self.temporal_client.cancel_workflow(workflow_id)

            if success and workflow_id in self.active_workflows:
                # Update local tracking
                workflow = self.active_workflows[workflow_id]
                workflow.status = WorkflowStatus.CANCELLED

            return success

        except Exception as e:
            logger.error(f"Error cancelling workflow {workflow_id}: {e}")
            return False

    async def route_workflow(self, workflow_request: WorkflowRequest, user_id: str) -> RoutingResult:
        """
        Route a workflow request directly (compatibility method for conversation_manager).

        This method provides a simplified interface for starting workflows when you
        already have a fully-formed WorkflowRequest. Used primarily by Slack conversation
        manager for fire-and-forget workflow execution.

        Args:
            workflow_request: Pre-configured workflow request
            user_id: User ID for logging (redundant with workflow_request.user_id)

        Returns:
            RoutingResult with workflow ID and status
        """
        logger.info(
            f"Direct workflow routing for user {user_id}",
            extra={
                "workflow_type": workflow_request.workflow_type.value,
                "correlation_id": workflow_request.correlation_id,
                "has_temporal_client": self.temporal_client is not None,
            }
        )

        # Verify Temporal client is available
        if not self.temporal_client:
            logger.error("Temporal client not initialized - cannot route workflow")
            return RoutingResult(
                decision=RoutingDecision.ERROR,
                message="Workflow system not ready. Please try again in a moment."
            )

        # Generate workflow ID
        workflow_id = f"wf-{uuid.uuid4()}"

        try:
            # Map workflow type to workflow class
            from src.services.workflow.workflows import (
                BatchProcessingWorkflow,
                ConversationWorkflow,
                InlineAnalysisReportWorkflow,
                ParallelAnalysisWorkflow,
                QuickSummaryWorkflow,
                ReportGenerationWorkflow,
                SequentialAnalysisWorkflow,
            )

            # Map workflow types to their classes (ALL 8 TYPES SUPPORTED)
            workflow_class_map = {
                WorkflowType.SEQUENTIAL_ANALYSIS: SequentialAnalysisWorkflow,
                WorkflowType.PARALLEL_ANALYSIS: ParallelAnalysisWorkflow,
                WorkflowType.BATCH_PROCESSING: BatchProcessingWorkflow,
                WorkflowType.CONVERSATION: ConversationWorkflow,
                WorkflowType.REPORT_GENERATION: ReportGenerationWorkflow,
                WorkflowType.COMPETENCY_ASSESSMENT: SequentialAnalysisWorkflow,
                WorkflowType.INLINE_ANALYSIS: InlineAnalysisReportWorkflow,
                WorkflowType.QUICK_SUMMARY: QuickSummaryWorkflow,
            }

            workflow_class = workflow_class_map.get(
                workflow_request.workflow_type,
                SequentialAnalysisWorkflow  # Default fallback
            )

            logger.info(
                f"Starting workflow {workflow_id}",
                extra={
                    "workflow_class": workflow_class.__name__,
                    "workflow_type": workflow_request.workflow_type.value,
                }
            )

            # Start workflow via Temporal client
            workflow_response = await self.temporal_client.start_workflow(
                workflow_class=workflow_class,
                request=workflow_request,
                workflow_id=workflow_id
            )

            # Track active workflow
            self.active_workflows[workflow_id] = workflow_response

            logger.info(
                f"Workflow {workflow_id} started successfully",
                extra={
                    "workflow_type": workflow_request.workflow_type.value,
                    "status": workflow_response.status.value,
                }
            )

            return RoutingResult(
                decision=RoutingDecision.SEQUENTIAL_ANALYSIS,
                workflow_id=workflow_id,
                workflow_type=workflow_request.workflow_type,
                estimated_duration=workflow_request.timeout_seconds,
                estimated_cost=0.15,  # Base cost estimate
                message=f"Workflow {workflow_id} started successfully"
            )

        except Exception as e:
            logger.error(
                f"Failed to start workflow {workflow_id}",
                exc_info=True,
                extra={
                    "error": str(e),
                    "workflow_type": workflow_request.workflow_type.value,
                    "user_id": user_id,
                }
            )
            return RoutingResult(
                decision=RoutingDecision.ERROR,
                message=f"Failed to start workflow: {str(e)}"
            )

    async def get_workflow_status(self, workflow_id: str) -> dict[str, Any]:
        """
        Get workflow status and results from Temporal.

        Args:
            workflow_id: The workflow ID to check

        Returns:
            Dictionary containing:
            - status: Workflow status (RUNNING, COMPLETED, FAILED, etc.)
            - workflow_id: The workflow ID
            - result: Workflow result (if completed)
            - error: Error message (if failed)
            - started_at: Start timestamp
            - completed_at: Completion timestamp (if completed)
        """
        logger.debug(
            f"Getting workflow status for {workflow_id}",
            extra={"workflow_id": workflow_id}
        )

        if not self.temporal_client:
            logger.error("Temporal client not initialized")
            return {
                "status": "ERROR",
                "workflow_id": workflow_id,
                "error": "Temporal client not initialized"
            }

        try:
            workflow_response = await self.temporal_client.get_workflow_status(workflow_id)

            if not workflow_response:
                logger.warning(f"Workflow {workflow_id} not found")
                return {
                    "status": "NOT_FOUND",
                    "workflow_id": workflow_id
                }

            return {
                "status": workflow_response.status.value,
                "workflow_id": workflow_id,
                "result": workflow_response.result,
                "error": workflow_response.error,
                "started_at": workflow_response.started_at,
                "completed_at": workflow_response.completed_at,
            }

        except Exception as e:
            logger.error(
                f"Failed to get workflow status for {workflow_id}: {e}",
                exc_info=True,
                extra={"workflow_id": workflow_id}
            )
            return {
                "status": "ERROR",
                "workflow_id": workflow_id,
                "error": str(e)
            }

    def _should_use_batch_processing(self, context: RoutingContext) -> bool:
        """Determine if batch processing should be used."""
        # Simple heuristics for batch processing
        content = context.content.lower()

        # Check for batch indicators
        batch_keywords = [
            "multiple",
            "several",
            "many",
            "all",
            "batch",
            "bulk",
            "projects",
            "activities",
            "tasks",
            "list of",
        ]

        return any(keyword in content for keyword in batch_keywords)

    def _extract_batch_items(self, context: RoutingContext) -> list[dict[str, Any]]:
        """Extract individual items from batch request."""
        # This is a simplified implementation
        # In practice, you'd use NLP to parse structured lists

        content = context.content
        items = []

        # Try to find list patterns
        lines = content.split("\n")
        for i, line in enumerate(lines):
            line = line.strip()
            if line and (
                line.startswith("-") or line.startswith("*") or line.startswith(f"{i + 1}.")
            ):
                items.append(
                    {"item_id": f"item_{i}", "content": line.lstrip("-*0123456789. "), "order": i}
                )

        # If no structured list found, create single item
        if not items:
            items.append({"item_id": "item_0", "content": content, "order": 0})

        return items

    async def _has_active_conversation(self, thread_id: str) -> bool:
        """Check if there's an active conversation in the thread."""
        try:
            # Check with context manager
            context = await self.context_manager.get_thread_context(thread_id)
            return context is not None and len(context.get("messages", [])) > 0

        except Exception as e:
            logger.error(f"Error checking active conversation: {e}")
            return False

    async def _route_career_advice_workflow(
        self, context: RoutingContext, intent_result: Any
    ) -> RoutingResult:
        """Route to career advice workflow."""
        workflow_id = f"career_advice_{uuid.uuid4().hex[:8]}"

        # Use OptimizedAnalysisWorkflow for career advice
        return await self._create_workflow_result(
            workflow_id=workflow_id,
            workflow_type=WorkflowType.SEQUENTIAL_ANALYSIS,
            decision=RoutingDecision.CONVERSATION,
            context=context,
            intent_result=intent_result,
            estimated_duration=90,  # 1.5 minutes
        )

    async def _route_report_generation(
        self, context: RoutingContext, intent_result: Any
    ) -> RoutingResult:
        """Route to report generation workflow."""
        workflow_id = f"report_gen_{uuid.uuid4().hex[:8]}"

        # Extract report parameters from intent or context
        report_type = "competency_assessment"  # Default
        date_range_days = 90  # Default to last 90 days
        date_range_info = None

        # Try to extract from intent_result if available
        if hasattr(intent_result, "__dict__"):
            intent_dict = intent_result.__dict__
            report_type = intent_dict.get("report_type", report_type)
            date_range_days = intent_dict.get("date_range_days", date_range_days)

        # Extract date range from natural language if provided by intent analyzer
        if hasattr(intent_result, "extracted_date_range") and intent_result.extracted_date_range:
            date_info = intent_result.extracted_date_range
            date_range_days = date_info.get("days_span", 90)
            date_range_info = date_info

            logger.info(
                f"Using extracted date range: {date_info.get('original_text')}",
                extra={
                    "workflow_id": workflow_id,
                    "start_date": date_info.get("start_date"),
                    "end_date": date_info.get("end_date"),
                    "days_span": date_range_days,
                    "range_type": date_info.get("range_type"),
                },
            )

        # Create workflow request
        workflow_request = WorkflowRequest(
            workflow_type=WorkflowType.REPORT_GENERATION,
            user_id=context.user_id,
            team_id=context.user_profile.get("team_id", "default")
            if context.user_profile
            else "default",
            correlation_id=context.correlation_id or workflow_id,
            input_data={
                "content": context.content,
                "report_type": report_type,
                "date_range_days": date_range_days,
                "date_range_info": date_range_info,  # NEW: Pass full date range info
                "include_recommendations": True,
                "channel_id": context.metadata.get("channel_id") if context.metadata else None,
            },
            conversation_id=context.thread_id,
            thread_ts=context.thread_id,
            priority=context.priority,
        )

        # Start workflow
        try:
            from src.services.workflow.workflows import ReportGenerationWorkflow

            workflow_response = await self.temporal_client.start_workflow(
                ReportGenerationWorkflow, workflow_request, workflow_id
            )

            # Track active workflow
            self.active_workflows[workflow_id] = workflow_response

            return RoutingResult(
                decision=RoutingDecision.REPORT_GENERATION,
                workflow_id=workflow_id,
                workflow_type=WorkflowType.REPORT_GENERATION,
                estimated_duration=300,  # 5 minutes
                estimated_cost=0.05,  # $0.05 USD (low cost, mostly PDF generation)
                message="Generating your competency report. This may take a few minutes.",
            )

        except Exception as e:
            logger.error(f"Failed to start report generation workflow: {e}", exc_info=True)
            return RoutingResult(
                decision=RoutingDecision.ERROR,
                message="Unable to start report generation. Please try again.",
            )

    async def _route_inline_analysis(
        self, context: RoutingContext, intent_result: Any
    ) -> RoutingResult:
        """
        Route to inline analysis workflow.

        Handles requests where users provide activity content directly in their message:
        - "Analyze this: I implemented OAuth2 authentication"
        - "I led the migration to microservices"
        """
        workflow_id = f"inline_analysis_{uuid.uuid4().hex[:8]}"

        # Extract inline content from intent result
        extracted_content = intent_result.extracted_content
        inline_content = extracted_content.get("cleaned_text") or extracted_content.get("raw_text")

        # Create content metadata
        content_metadata = {
            "extraction_method": extracted_content.get("extraction_method"),
            "confidence": extracted_content.get("confidence"),
            "trigger_phrase": extracted_content.get("trigger_phrase"),
            "raw_text": extracted_content.get("raw_text"),
        }

        logger.info(
            "Routing to inline analysis workflow",
            extra={
                "workflow_id": workflow_id,
                "content_length": len(inline_content),
                "extraction_method": content_metadata["extraction_method"],
                "confidence": content_metadata["confidence"],
            },
        )

        # Create workflow request
        workflow_request = WorkflowRequest(
            workflow_type=WorkflowType.INLINE_ANALYSIS,
            user_id=context.user_id,
            team_id=context.user_profile.get("team_id", "default")
            if context.user_profile
            else "default",
            correlation_id=context.correlation_id or workflow_id,
            input_data={
                "inline_content": inline_content,
                "content_metadata": content_metadata,
                "output_format": "slack_blocks",  # Default to Slack blocks for instant feedback
                "include_gap_analysis": True,
                "context": {
                    "user_profile": context.user_profile,
                    "conversation_history": context.conversation_history,
                    "original_message": context.content,
                },
                "channel_id": context.metadata.get("channel_id") if context.metadata else None,
            },
            conversation_id=context.thread_id,
            thread_ts=context.thread_id,
            priority=context.priority,
        )

        # Start workflow
        try:
            from src.services.workflow.workflows import InlineAnalysisReportWorkflow

            workflow_response = await self.temporal_client.start_workflow(
                InlineAnalysisReportWorkflow, workflow_request, workflow_id
            )

            # Track active workflow
            self.active_workflows[workflow_id] = workflow_response

            return RoutingResult(
                decision=RoutingDecision.INLINE_ANALYSIS,
                workflow_id=workflow_id,
                workflow_type=WorkflowType.INLINE_ANALYSIS,
                estimated_duration=60,  # 1 minute for inline analysis
                estimated_cost=0.08,  # $0.08 USD (single activity analysis)
                message=f"Analyzing your activity: {inline_content[:100]}{'...' if len(inline_content) > 100 else ''}",
            )

        except Exception as e:
            logger.error(f"Failed to start inline analysis workflow: {e}", exc_info=True)
            return RoutingResult(
                decision=RoutingDecision.ERROR,
                message="Unable to start inline analysis. Please try again.",
            )

    async def _route_quick_summary(
        self, context: RoutingContext, intent_result: Any
    ) -> RoutingResult:
        """
        Route to quick summary workflow.

        Handles requests for lightweight Slack-native competency summaries:
        - "Show me my competency summary"
        - "What are my top skills?"
        - "How am I doing this week?"
        """
        workflow_id = f"quick_summary_{uuid.uuid4().hex[:8]}"

        # Determine summary type and time period from intent
        summary_type = "competency"  # Default
        time_period = "recent"  # Default to recent (last 2 weeks)
        include_recommendations = False

        # Try to extract from intent_result if available
        if hasattr(intent_result, "__dict__"):
            intent_dict = intent_result.__dict__
            summary_type = intent_dict.get("summary_type", summary_type)
            time_period = intent_dict.get("time_period", time_period)
            include_recommendations = intent_dict.get("include_recommendations", False)

        # Detect time period from message content
        content_lower = context.content.lower()
        if "this week" in content_lower or "weekly" in content_lower:
            time_period = "this_week"
        elif "this month" in content_lower or "monthly" in content_lower:
            time_period = "this_month"

        logger.info(
            "Routing to quick summary workflow",
            extra={
                "workflow_id": workflow_id,
                "summary_type": summary_type,
                "time_period": time_period,
            },
        )

        # Create workflow request
        workflow_request = WorkflowRequest(
            workflow_type=WorkflowType.QUICK_SUMMARY,
            user_id=context.user_id,
            team_id=context.user_profile.get("team_id", "default")
            if context.user_profile
            else "default",
            correlation_id=context.correlation_id or workflow_id,
            input_data={
                "summary_type": summary_type,
                "time_period": time_period,
                "include_recommendations": include_recommendations,
                "channel_id": context.metadata.get("channel_id") if context.metadata else None,
            },
            conversation_id=context.thread_id,
            thread_ts=context.thread_id,
            priority=context.priority,
        )

        # Start workflow
        try:
            from src.services.workflow.workflows import QuickSummaryWorkflow

            workflow_response = await self.temporal_client.start_workflow(
                QuickSummaryWorkflow, workflow_request, workflow_id
            )

            # Track active workflow
            self.active_workflows[workflow_id] = workflow_response

            return RoutingResult(
                decision=RoutingDecision.QUICK_SUMMARY,
                workflow_id=workflow_id,
                workflow_type=WorkflowType.QUICK_SUMMARY,
                estimated_duration=45,  # 45 seconds for quick summary
                estimated_cost=0.02,  # $0.02 USD (very lightweight)
                message=f"Generating your {time_period.replace('_', ' ')} competency summary...",
            )

        except Exception as e:
            logger.error(f"Failed to start quick summary workflow: {e}", exc_info=True)
            return RoutingResult(
                decision=RoutingDecision.ERROR,
                message="Unable to generate summary. Please try again.",
            )

    async def _route_goal_management(
        self, context: RoutingContext, intent_result: Any
    ) -> RoutingResult:
        """Route to goal management workflow."""
        workflow_id = f"goal_mgmt_{uuid.uuid4().hex[:8]}"

        return await self._create_workflow_result(
            workflow_id=workflow_id,
            workflow_type=WorkflowType.CONVERSATION,
            decision=RoutingDecision.CONVERSATION,
            context=context,
            intent_result=intent_result,
            estimated_duration=60,  # 1 minute
        )

    async def _route_resource_discovery(
        self, context: RoutingContext, intent_result: Any
    ) -> RoutingResult:
        """Route to resource discovery workflow."""
        workflow_id = f"resource_disc_{uuid.uuid4().hex[:8]}"

        return await self._create_workflow_result(
            workflow_id=workflow_id,
            workflow_type=WorkflowType.CONVERSATION,
            decision=RoutingDecision.CONVERSATION,
            context=context,
            intent_result=intent_result,
            estimated_duration=45,  # 45 seconds
        )

    async def _create_workflow_result(
        self,
        workflow_id: str,
        workflow_type: WorkflowType,
        decision: RoutingDecision,
        context: RoutingContext,
        intent_result: Any,
        estimated_duration: int,
    ) -> RoutingResult:
        """Helper method to create workflow result."""

        # Create workflow request with enhanced data from intent analysis
        workflow_request = WorkflowRequest(
            workflow_type=workflow_type,
            user_id=context.user_id,
            team_id=context.user_profile.get("team_id", "default")
            if context.user_profile
            else "default",
            correlation_id=context.correlation_id or workflow_id,
            input_data={
                "content": context.content,
                "intent_analysis": {
                    "intent": intent_result.primary_intent.value,
                    "confidence": intent_result.confidence,
                    "needs_clarification": intent_result.needs_clarification,
                    "extracted_entities": getattr(intent_result, "extracted_content", {}),
                },
                "user_profile": context.user_profile,
                "conversation_history": context.conversation_history,
            },
            conversation_id=context.thread_id,
            thread_ts=context.thread_id,
            priority=context.priority,
        )

        try:
            # Start workflow using Temporal client
            from src.services.workflow.workflows import (
                BatchProcessingWorkflow,
                ConversationWorkflow,
                SequentialAnalysisWorkflow,
            )

            workflow_class_map = {
                WorkflowType.SEQUENTIAL_ANALYSIS: SequentialAnalysisWorkflow,
                WorkflowType.BATCH_PROCESSING: BatchProcessingWorkflow,
                WorkflowType.CONVERSATION: ConversationWorkflow,
            }

            workflow_class = workflow_class_map.get(workflow_type, SequentialAnalysisWorkflow)
            workflow_response = await self.temporal_client.start_workflow(
                workflow_class, workflow_request, workflow_id
            )

            # Track active workflow
            self.active_workflows[workflow_id] = workflow_response

            return RoutingResult(
                decision=decision,
                workflow_id=workflow_id,
                workflow_type=workflow_type,
                estimated_duration=estimated_duration,
                estimated_cost=0.15,  # Base cost
                message=f"Started {decision.value} workflow",
            )

        except Exception as e:
            logger.error(f"Failed to start workflow: {e}")
            return RoutingResult(
                decision=RoutingDecision.ERROR, message=f"Unable to start workflow: {str(e)}"
            )

    async def cleanup(self):
        """Clean up resources."""
        try:
            # Clear active workflows tracking
            self.active_workflows.clear()

            # Cleanup ConversationIntelligence
            if hasattr(self.conversation_intelligence, "cleanup"):
                await self.conversation_intelligence.cleanup()

            logger.info("Workflow router cleanup completed")

        except Exception as e:
            logger.error(f"Error during workflow router cleanup: {e}")


# Singleton instance
_workflow_router: WorkflowRouter | None = None


async def get_workflow_router() -> WorkflowRouter:
    """Get the workflow router singleton."""
    global _workflow_router

    if _workflow_router is None:
        _workflow_router = WorkflowRouter()
        await _workflow_router.initialize()

    return _workflow_router
