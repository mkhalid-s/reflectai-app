"""
Goal Tracker Tool for Advisor Agent

Implements goal tracking part of
- Track and update user development goals
- Goal progress monitoring and milestone tracking
- Integration with recommendations and competency assessments
- SMART goal framework implementation

Used by Advisor Agent for managing user career development goals.
"""

from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from ..base_tool import Tool, ToolError, ToolPermission, ToolRequest


class GoalStatus(Enum):
    """Goal status tracking"""

    DRAFT = "draft"
    ACTIVE = "active"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    PAUSED = "paused"
    CANCELLED = "cancelled"
    OVERDUE = "overdue"


class GoalPriority(Enum):
    """Goal priority levels"""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Goal(BaseModel):
    """Individual goal definition"""

    id: str = Field(..., description="Unique goal ID")
    user_id: str = Field(..., description="User who owns this goal")
    title: str = Field(..., description="Goal title")
    description: str = Field(..., description="Detailed goal description")

    # SMART goal framework
    specific: str = Field(..., description="Specific goal definition")
    measurable: str = Field(..., description="How success will be measured")
    achievable: str = Field(..., description="Why this goal is achievable")
    relevant: str = Field(..., description="How this goal relates to career")
    time_bound: str = Field(..., description="Timeline for completion")

    # Goal metadata
    status: GoalStatus = Field(GoalStatus.DRAFT, description="Current goal status")
    priority: GoalPriority = Field(GoalPriority.MEDIUM, description="Goal priority")
    category: str = Field("career_development", description="Goal category")
    tags: list[str] = Field(default_factory=list, description="Goal tags")

    # Timeline and progress
    created_at: datetime = Field(default_factory=datetime.utcnow)
    start_date: datetime | None = Field(None, description="Goal start date")
    target_date: datetime = Field(..., description="Target completion date")
    completed_at: datetime | None = Field(None, description="Actual completion date")

    # Progress tracking
    progress_percentage: float = Field(0.0, description="Progress percentage (0-100)")
    milestones: list[dict[str, Any]] = Field(default_factory=list, description="Goal milestones")

    # Relationships
    related_competencies: list[str] = Field(
        default_factory=list, description="Related competency areas"
    )
    related_recommendations: list[str] = Field(
        default_factory=list, description="Related recommendation IDs"
    )
    parent_goal_id: str | None = Field(None, description="Parent goal if this is a sub-goal")
    sub_goals: list[str] = Field(default_factory=list, description="Sub-goal IDs")

    # Tracking and notes
    notes: list[dict[str, Any]] = Field(
        default_factory=list, description="Progress notes and updates"
    )
    last_updated: datetime = Field(default_factory=datetime.utcnow)


class GoalRequest(BaseModel):
    """Request for goal operations"""

    operation: str = Field(..., description="Goal operation to perform")
    user_id: str = Field(..., description="User ID")
    goal_id: str | None = Field(None, description="Goal ID for operations on existing goals")
    goal_data: dict[str, Any] | None = Field(
        None, description="Goal data for create/update operations"
    )
    filters: dict[str, Any] | None = Field(None, description="Filters for query operations")


class GoalResult(BaseModel):
    """Result of goal operations"""

    operation: str = Field(..., description="Operation performed")
    success: bool = Field(..., description="Operation success status")
    goal: Goal | None = Field(None, description="Goal object for single goal operations")
    goals: list[Goal] | None = Field(None, description="List of goals for multi-goal operations")
    message: str | None = Field(None, description="Operation result message")
    execution_time: float = Field(..., description="Operation execution time")


class GoalTrackerTool(Tool):
    """
    Tool for tracking and managing user career development goals

    Provides CRUD operations for goals, progress tracking, and milestone management.
    Integrates with recommendation system and competency assessments.
    """

    def __init__(self):
        super().__init__(
            name="goal_tracker",
            description="Track and manage user career development goals with progress monitoring",
            required_permissions=[ToolPermission.READ_WRITE],
            timeout=30,
        )

        # In-memory storage for demo (would use database in production)
        self._goals_storage: dict[str, Goal] = {}

    async def _execute_operation(
        self, request: ToolRequest, agent_context: Any | None = None
    ) -> GoalResult:
        """Execute goal tracking operation"""

        if request.operation != "goal_operation":
            raise ToolError(
                message=f"Unknown operation: {request.operation}",
                tool_name=self.name,
                operation=request.operation,
            )

        # Parse request parameters
        try:
            goal_request = GoalRequest(**request.parameters)
        except Exception as e:
            raise ToolError(
                message=f"Invalid request parameters: {str(e)}",
                tool_name=self.name,
                operation=request.operation,
            ) from e

        start_time = datetime.now(UTC)

        # Route to specific operation handler
        operation_handlers = {
            "create_goal": self._create_goal,
            "update_goal": self._update_goal,
            "get_goal": self._get_goal,
            "list_goals": self._list_goals,
            "delete_goal": self._delete_goal,
            "update_progress": self._update_progress,
            "add_milestone": self._add_milestone,
            "add_note": self._add_note,
        }

        handler = operation_handlers.get(goal_request.operation)
        if not handler:
            raise ToolError(
                message=f"Unsupported goal operation: {goal_request.operation}",
                tool_name=self.name,
                operation=request.operation,
            )

        try:
            result = await handler(goal_request)
            result.execution_time = (datetime.now(UTC) - start_time).total_seconds()
            return result

        except Exception as e:
            raise ToolError(
                message=f"Goal operation failed: {str(e)}",
                tool_name=self.name,
                operation=request.operation,
                details={"goal_operation": goal_request.operation},
            ) from e

    async def _create_goal(self, request: GoalRequest) -> GoalResult:
        """Create a new goal"""

        if not request.goal_data:
            raise ToolError(
                message="Goal data required for create operation",
                tool_name=self.name,
                operation="create_goal",
            )

        # Generate goal ID
        goal_id = f"goal_{request.user_id}_{int(datetime.now(UTC).timestamp())}"

        # Create goal object
        goal_data = request.goal_data.copy()
        goal_data.update(
            {
                "id": goal_id,
                "user_id": request.user_id,
                "created_at": datetime.now(UTC),
                "last_updated": datetime.now(UTC),
            }
        )

        goal = Goal(**goal_data)

        # Store goal
        self._goals_storage[goal_id] = goal

        self.logger.info(f"Created goal {goal_id} for user {request.user_id}")

        return GoalResult(
            operation=request.operation,
            success=True,
            goal=goal,
            message=f"Goal '{goal.title}' created successfully",
            execution_time=0.0,
        )

    async def _update_goal(self, request: GoalRequest) -> GoalResult:
        """Update an existing goal"""

        if not request.goal_id or not request.goal_data:
            raise ToolError(
                message="Goal ID and goal data required for update operation",
                tool_name=self.name,
                operation="update_goal",
            )

        # Get existing goal
        goal = self._goals_storage.get(request.goal_id)
        if not goal:
            raise ToolError(
                message=f"Goal not found: {request.goal_id}",
                tool_name=self.name,
                operation="update_goal",
            )

        # Update goal fields
        goal_dict = goal.model_dump()
        goal_dict.update(request.goal_data)
        goal_dict["last_updated"] = datetime.now(UTC)

        updated_goal = Goal(**goal_dict)
        self._goals_storage[request.goal_id] = updated_goal

        return GoalResult(
            operation=request.operation,
            success=True,
            goal=updated_goal,
            message=f"Goal '{updated_goal.title}' updated successfully",
            execution_time=0.0,
        )

    async def _get_goal(self, request: GoalRequest) -> GoalResult:
        """Get a specific goal"""

        if not request.goal_id:
            raise ToolError(
                message="Goal ID required for get operation",
                tool_name=self.name,
                operation="get_goal",
            )

        goal = self._goals_storage.get(request.goal_id)
        if not goal:
            return GoalResult(
                operation=request.operation,
                success=False,
                message=f"Goal not found: {request.goal_id}",
                execution_time=0.0,
            )

        return GoalResult(operation=request.operation, success=True, goal=goal, execution_time=0.0)

    async def _list_goals(self, request: GoalRequest) -> GoalResult:
        """List goals for a user with optional filtering"""

        # Filter goals by user
        user_goals = [
            goal for goal in self._goals_storage.values() if goal.user_id == request.user_id
        ]

        # Apply additional filters if provided
        if request.filters:
            filters = request.filters

            if "status" in filters:
                target_status = GoalStatus(filters["status"])
                user_goals = [g for g in user_goals if g.status == target_status]

            if "priority" in filters:
                target_priority = GoalPriority(filters["priority"])
                user_goals = [g for g in user_goals if g.priority == target_priority]

            if "category" in filters:
                user_goals = [g for g in user_goals if g.category == filters["category"]]

            if "overdue" in filters and filters["overdue"]:
                now = datetime.now(UTC)
                user_goals = [
                    g
                    for g in user_goals
                    if g.target_date < now and g.status != GoalStatus.COMPLETED
                ]

        # Sort by priority and creation date
        priority_order = {
            GoalPriority.CRITICAL: 4,
            GoalPriority.HIGH: 3,
            GoalPriority.MEDIUM: 2,
            GoalPriority.LOW: 1,
        }

        user_goals.sort(key=lambda g: (priority_order[g.priority], g.created_at), reverse=True)

        return GoalResult(
            operation=request.operation,
            success=True,
            goals=user_goals,
            message=f"Found {len(user_goals)} goals",
            execution_time=0.0,
        )

    async def _delete_goal(self, request: GoalRequest) -> GoalResult:
        """Delete a goal"""

        if not request.goal_id:
            raise ToolError(
                message="Goal ID required for delete operation",
                tool_name=self.name,
                operation="delete_goal",
            )

        goal = self._goals_storage.get(request.goal_id)
        if not goal:
            return GoalResult(
                operation=request.operation,
                success=False,
                message=f"Goal not found: {request.goal_id}",
                execution_time=0.0,
            )

        # Remove goal
        del self._goals_storage[request.goal_id]

        return GoalResult(
            operation=request.operation,
            success=True,
            message=f"Goal '{goal.title}' deleted successfully",
            execution_time=0.0,
        )

    async def _update_progress(self, request: GoalRequest) -> GoalResult:
        """Update goal progress"""

        if (
            not request.goal_id
            or not request.goal_data
            or "progress_percentage" not in request.goal_data
        ):
            raise ToolError(
                message="Goal ID and progress_percentage required for progress update",
                tool_name=self.name,
                operation="update_progress",
            )

        goal = self._goals_storage.get(request.goal_id)
        if not goal:
            raise ToolError(
                message=f"Goal not found: {request.goal_id}",
                tool_name=self.name,
                operation="update_progress",
            )

        # Update progress
        new_progress = float(request.goal_data["progress_percentage"])
        old_progress = goal.progress_percentage

        goal.progress_percentage = min(max(new_progress, 0.0), 100.0)
        goal.last_updated = datetime.now(UTC)

        # Add progress note
        progress_note = {
            "type": "progress_update",
            "timestamp": datetime.now(UTC).isoformat(),
            "old_progress": old_progress,
            "new_progress": goal.progress_percentage,
            "note": request.goal_data.get("note", "Progress updated"),
        }
        goal.notes.append(progress_note)

        # Auto-complete if 100%
        if goal.progress_percentage >= 100.0 and goal.status != GoalStatus.COMPLETED:
            goal.status = GoalStatus.COMPLETED
            goal.completed_at = datetime.now(UTC)

        return GoalResult(
            operation=request.operation,
            success=True,
            goal=goal,
            message=f"Progress updated to {goal.progress_percentage}%",
            execution_time=0.0,
        )

    async def _add_milestone(self, request: GoalRequest) -> GoalResult:
        """Add milestone to a goal"""

        if not request.goal_id or not request.goal_data:
            raise ToolError(
                message="Goal ID and milestone data required",
                tool_name=self.name,
                operation="add_milestone",
            )

        goal = self._goals_storage.get(request.goal_id)
        if not goal:
            raise ToolError(
                message=f"Goal not found: {request.goal_id}",
                tool_name=self.name,
                operation="add_milestone",
            )

        # Create milestone
        milestone = {
            "id": f"milestone_{int(datetime.now(UTC).timestamp())}",
            "title": request.goal_data.get("title", "New milestone"),
            "description": request.goal_data.get("description", ""),
            "target_date": request.goal_data.get("target_date"),
            "completed": False,
            "created_at": datetime.now(UTC).isoformat(),
        }

        goal.milestones.append(milestone)
        goal.last_updated = datetime.now(UTC)

        return GoalResult(
            operation=request.operation,
            success=True,
            goal=goal,
            message=f"Milestone '{milestone['title']}' added successfully",
            execution_time=0.0,
        )

    async def _add_note(self, request: GoalRequest) -> GoalResult:
        """Add note to a goal"""

        if not request.goal_id or not request.goal_data or "note" not in request.goal_data:
            raise ToolError(
                message="Goal ID and note required", tool_name=self.name, operation="add_note"
            )

        goal = self._goals_storage.get(request.goal_id)
        if not goal:
            raise ToolError(
                message=f"Goal not found: {request.goal_id}",
                tool_name=self.name,
                operation="add_note",
            )

        # Add note
        note = {
            "type": "user_note",
            "timestamp": datetime.now(UTC).isoformat(),
            "note": request.goal_data["note"],
            "author": request.goal_data.get("author", "system"),
        }

        goal.notes.append(note)
        goal.last_updated = datetime.now(UTC)

        return GoalResult(
            operation=request.operation,
            success=True,
            goal=goal,
            message="Note added successfully",
            execution_time=0.0,
        )

    def get_supported_operations(self) -> list[str]:
        """Get list of supported operations"""
        return ["goal_operation"]

    def get_goal_operations(self) -> list[str]:
        """Get list of supported goal operations"""
        return [
            "create_goal",
            "update_goal",
            "get_goal",
            "list_goals",
            "delete_goal",
            "update_progress",
            "add_milestone",
            "add_note",
        ]


# Auto-register for tool discovery
GoalTrackerTool._auto_register = True
GoalTrackerTool._category = "advisor"
GoalTrackerTool._version = None  # Version loaded from config
