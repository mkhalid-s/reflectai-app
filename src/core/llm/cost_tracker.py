"""
LLM Cost Tracking and Optimization

Implements  Cost Tracking Infrastructure with real-time monitoring,
budget management, and cost attribution by user/department.

Model pricing configuration based on tiered selection:
- Tier 1 (Analysis): claude-3-5-haiku ($0.25/$1.25 per 1M tokens)
- Tier 2 (Advice): gpt-4o ($2.50/$10.00 per 1M tokens)
- Tier 3 (Conversation): gpt-4o-mini ($0.15/$0.60 per 1M tokens)
"""

import asyncio
import json
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any
from uuid import uuid4

from src.shared import get_logger

# Database manager import (lazy loaded to avoid circular imports)
_db_manager = None


def _get_db_manager():
    """Lazy load database manager to avoid circular imports."""
    global _db_manager
    if _db_manager is None:
        try:
            from src.infrastructure.database.db_manager import get_database_manager

            _db_manager = get_database_manager()
        except Exception as e:
            logger.warning(f"Could not load database manager: {e}")
            _db_manager = None
    return _db_manager


logger = get_logger(__name__)


class ModelTier(str, Enum):
    """Model tier classification."""

    TIER_1_ANALYSIS = "tier_1_analysis"
    TIER_2_ADVICE = "tier_2_advice"
    TIER_3_CONVERSATION = "tier_3_conversation"


# Model pricing configuration (per 1M tokens)
MODEL_PRICING = {
    "claude-3-5-haiku": {
        "provider": "anthropic",
        "tier": ModelTier.TIER_1_ANALYSIS,
        "input_cost_per_1m": 0.25,  # $0.25 per 1M input tokens
        "output_cost_per_1m": 1.25,  # $1.25 per 1M output tokens
        "context_window": 128000,
        "max_output": 8192,
    },
    "gpt-4o": {
        "provider": "openai",
        "tier": ModelTier.TIER_2_ADVICE,
        "input_cost_per_1m": 2.50,  # $2.50 per 1M input tokens
        "output_cost_per_1m": 10.00,  # $10.00 per 1M output tokens
        "context_window": 128000,
        "max_output": 16384,
    },
    "gpt-4o-mini": {
        "provider": "openai",
        "tier": ModelTier.TIER_3_CONVERSATION,
        "input_cost_per_1m": 0.15,  # $0.15 per 1M input tokens
        "output_cost_per_1m": 0.60,  # $0.60 per 1M output tokens
        "context_window": 128000,
        "max_output": 16384,
    },
    # Fallback models
    "claude-3-5-sonnet": {
        "provider": "anthropic",
        "tier": ModelTier.TIER_1_ANALYSIS,
        "input_cost_per_1m": 3.00,
        "output_cost_per_1m": 15.00,
        "context_window": 200000,
        "max_output": 8192,
    },
    "gpt-3.5-turbo": {
        "provider": "openai",
        "tier": ModelTier.TIER_3_CONVERSATION,
        "input_cost_per_1m": 0.50,
        "output_cost_per_1m": 1.50,
        "context_window": 16385,
        "max_output": 4096,
    },
}


@dataclass
class CostRecord:
    """Individual cost record for tracking."""

    record_id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    user_id: str = ""
    model_name: str = ""
    provider_name: str = ""
    tokens_used: dict[str, int] = field(default_factory=dict)
    cost_usd: float = 0.0
    request_type: str = "general"  # analysis, advice, conversation, etc.
    department: str | None = None


@dataclass
class BudgetAlert:
    """Budget alert configuration."""

    name: str
    budget_usd: float
    period: str  # daily, weekly, monthly
    threshold_percent: float  # 80, 90, 100
    alert_channels: list[str] = field(default_factory=list)  # slack, email


@dataclass
class CostSummary:
    """Cost summary for reporting."""

    total_cost: float
    total_requests: int
    average_cost_per_request: float
    cost_by_model: dict[str, float]
    cost_by_provider: dict[str, float]
    cost_by_user: dict[str, float]
    period_start: datetime
    period_end: datetime


class CostTracker:
    """
    LLM cost tracking and budget management system.

    Features:
    - Real-time cost calculation and attribution
    - Budget management with alerting
    - Cost optimization recommendations
    - Usage analytics and reporting
    """

    def __init__(self, max_records_in_memory: int = 10000):
        # Cost records storage with bounded size to prevent memory leak
        # Using deque with maxlen ensures automatic eviction of oldest records
        self._cost_records: deque[CostRecord] = deque(maxlen=max_records_in_memory)
        self._max_records = max_records_in_memory

        # Budget management
        self._budgets: dict[str, BudgetAlert] = {}
        self._budget_usage: dict[str, float] = defaultdict(float)

        # Cost aggregations for performance
        self._hourly_costs: dict[str, float] = defaultdict(float)  # hour -> cost
        self._daily_costs: dict[str, float] = defaultdict(float)  # date -> cost
        self._user_costs: dict[str, float] = defaultdict(float)  # user_id -> cost
        self._model_costs: dict[str, float] = defaultdict(float)  # model -> cost

        # Performance metrics
        self._total_cost = 0.0
        self._total_requests = 0

        # Cleanup tracking
        self._last_cleanup = datetime.now(UTC)
        self._cleanup_interval = timedelta(hours=1)  # Cleanup old aggregations hourly

        # Database persistence infrastructure
        self.db_manager = _get_db_manager()
        self._persist_queue: asyncio.Queue[CostRecord] = asyncio.Queue(maxsize=1000)
        self._persist_task: asyncio.Task | None = None
        self._is_shutting_down = False
        self._persistence_enabled = self.db_manager is not None

        # Initialize default budgets
        self._initialize_default_budgets()

        # Start background persistence if database is available
        if self._persistence_enabled:
            self._start_background_persistence()
            logger.info(
                "Cost tracker initialized with database persistence",
                extra={
                    "max_records_in_memory": max_records_in_memory,
                    "persistence_enabled": True,
                },
            )
        else:
            logger.info(
                "Cost tracker initialized (in-memory only)",
                extra={
                    "max_records_in_memory": max_records_in_memory,
                    "persistence_enabled": False,
                },
            )

    def _initialize_default_budgets(self):
        """Initialize default budget alerts."""

        # Daily budget alert
        daily_budget = BudgetAlert(
            name="daily_total",
            budget_usd=50.0,
            period="daily",
            threshold_percent=80.0,
            alert_channels=["slack"],
        )

        # Monthly budget alert
        monthly_budget = BudgetAlert(
            name="monthly_total",
            budget_usd=1000.0,
            period="monthly",
            threshold_percent=90.0,
            alert_channels=["slack", "email"],
        )

        self._budgets["daily_total"] = daily_budget
        self._budgets["monthly_total"] = monthly_budget

    def calculate_cost(
        self, model_name: str, tokens_used: dict[str, int], is_batch: bool = False
    ) -> float:
        """
        Calculate cost for LLM usage based on model pricing.

        Args:
            model_name: Name of the model used
            tokens_used: Token usage breakdown
            is_batch: Whether this is part of batch processing (30-50% discount)

        Returns:
            Cost in USD
        """
        if model_name not in MODEL_PRICING:
            logger.warning(f"Unknown model {model_name}, using default pricing")
            # Default pricing if model not found
            input_cost_per_1m = 1.00
            output_cost_per_1m = 2.00
        else:
            pricing = MODEL_PRICING[model_name]
            input_cost_per_1m = pricing["input_cost_per_1m"]
            output_cost_per_1m = pricing["output_cost_per_1m"]

        # Calculate base cost
        prompt_tokens = tokens_used.get("prompt_tokens", 0)
        completion_tokens = tokens_used.get("completion_tokens", 0)

        input_cost = (prompt_tokens / 1_000_000) * input_cost_per_1m
        output_cost = (completion_tokens / 1_000_000) * output_cost_per_1m
        total_cost = input_cost + output_cost

        # Apply batch processing discount (40% reduction)
        if is_batch:
            total_cost *= 0.6  # 40% cost reduction for batch processing
            logger.debug("Batch processing discount applied: 40% reduction")

        return round(total_cost, 6)  # 6 decimal places for micro-costs

    def _cleanup_old_aggregations(self):
        """Clean up aggregations older than 30 days to prevent unbounded growth."""
        now = datetime.now(UTC)

        # Only cleanup once per hour
        if now - self._last_cleanup < self._cleanup_interval:
            return

        cutoff_date = now - timedelta(days=30)

        # Clean up hourly costs older than 30 days
        hourly_keys_to_remove = [
            key
            for key in self._hourly_costs.keys()
            if datetime.strptime(key[:13], "%Y-%m-%d-%H").replace(tzinfo=UTC) < cutoff_date
        ]

        for key in hourly_keys_to_remove:
            del self._hourly_costs[key]

        # Clean up daily costs older than 30 days
        daily_keys_to_remove = [
            key
            for key in self._daily_costs.keys()
            if datetime.strptime(key, "%Y-%m-%d").replace(tzinfo=UTC) < cutoff_date
        ]

        for key in daily_keys_to_remove:
            del self._daily_costs[key]

        self._last_cleanup = now

        if hourly_keys_to_remove or daily_keys_to_remove:
            logger.info(
                "Cleaned up old cost aggregations",
                extra={
                    "hourly_removed": len(hourly_keys_to_remove),
                    "daily_removed": len(daily_keys_to_remove),
                },
            )

    def record_request(
        self,
        user_id: str,
        model_name: str,
        provider_name: str,
        tokens_used: dict[str, int],
        cost_usd: float | None = None,
        request_type: str = "general",
        department: str | None = None,
        is_batch: bool = False,
    ):
        """
        Record a new LLM request cost.

        Args:
            user_id: User who made the request
            model_name: Model used
            provider_name: LLM provider
            tokens_used: Token usage breakdown
            cost_usd: Calculated cost in USD (auto-calculated if None)
            request_type: Type of request (analysis, advice, etc.)
            department: User's department (optional)
            is_batch: Whether this is part of batch processing
        """

        # Auto-calculate cost if not provided
        if cost_usd is None:
            cost_usd = self.calculate_cost(model_name, tokens_used, is_batch)

        record = CostRecord(
            user_id=user_id,
            model_name=model_name,
            provider_name=provider_name,
            tokens_used=tokens_used,
            cost_usd=cost_usd,
            request_type=request_type,
            department=department,
        )

        # Store record (deque automatically evicts oldest when full)
        self._cost_records.append(record)

        # Queue record for database persistence (async, non-blocking)
        self._queue_for_persistence(record)

        # Update aggregations
        self._update_aggregations(record)

        # Periodic cleanup of old aggregations
        self._cleanup_old_aggregations()

        # Check budget alerts
        self._check_budget_alerts(record)

        logger.debug(
            "Cost record created",
            extra={
                "user_id": user_id,
                "model": model_name,
                "cost_usd": cost_usd,
                "tokens": tokens_used.get("total_tokens", 0),
                "is_batch": is_batch,
                "records_in_memory": len(self._cost_records),
            },
        )

    def _update_aggregations(self, record: CostRecord):
        """Update cost aggregations for performance."""

        # Time-based aggregations
        hour_key = record.timestamp.strftime("%Y-%m-%d-%H")
        date_key = record.timestamp.strftime("%Y-%m-%d")

        self._hourly_costs[hour_key] += record.cost_usd
        self._daily_costs[date_key] += record.cost_usd

        # User/model aggregations
        self._user_costs[record.user_id] += record.cost_usd
        self._model_costs[record.model_name] += record.cost_usd

        # Global totals
        self._total_cost += record.cost_usd
        self._total_requests += 1

        # Budget usage
        for _budget_name, budget in self._budgets.items():
            usage_key = self._get_budget_usage_key(budget, record.timestamp)
            self._budget_usage[usage_key] += record.cost_usd

    def _check_budget_alerts(self, record: CostRecord):
        """Check if any budgets have been exceeded."""

        for _budget_name, budget in self._budgets.items():
            usage_key = self._get_budget_usage_key(budget, record.timestamp)
            current_usage = self._budget_usage[usage_key]

            threshold_amount = budget.budget_usd * (budget.threshold_percent / 100)

            if current_usage >= threshold_amount:
                self._trigger_budget_alert(budget, current_usage, usage_key)

    def _get_budget_usage_key(self, budget: BudgetAlert, timestamp: datetime) -> str:
        """Generate usage key for budget tracking."""

        if budget.period == "daily":
            return f"{budget.name}:{timestamp.strftime('%Y-%m-%d')}"
        elif budget.period == "weekly":
            # Get Monday of the week
            monday = timestamp - timedelta(days=timestamp.weekday())
            return f"{budget.name}:{monday.strftime('%Y-%m-%d')}"
        elif budget.period == "monthly":
            return f"{budget.name}:{timestamp.strftime('%Y-%m')}"
        else:
            return f"{budget.name}:total"

    def _trigger_budget_alert(self, budget: BudgetAlert, current_usage: float, usage_key: str):
        """Trigger budget alert notification."""

        usage_percent = (current_usage / budget.budget_usd) * 100

        logger.warning(
            f"Budget alert triggered: {budget.name}",
            extra={
                "budget_name": budget.name,
                "budget_usd": budget.budget_usd,
                "current_usage": current_usage,
                "usage_percent": usage_percent,
                "threshold_percent": budget.threshold_percent,
                "period": budget.period,
            },
        )

        # Send alert notifications
        asyncio.create_task(
            self._send_budget_alert(
                budget=budget, current_usage=current_usage, usage_percent=usage_percent
            )
        )

    async def _send_budget_alert(
        self, budget: BudgetAlert, current_usage: float, usage_percent: float
    ):
        """Send budget alert notifications via available channels."""
        try:
            alert_message = (
                f"🚨 *LLM Budget Alert*\n"
                f"• Budget: {budget.name}\n"
                f"• Period: {budget.period}\n"
                f"• Limit: ${budget.budget_usd:.2f}\n"
                f"• Current Usage: ${current_usage:.2f} ({usage_percent:.1f}%)\n"
                f"• Threshold: {budget.threshold_percent}%"
            )

            # Send to Slack if available
            try:
                from src.infrastructure.config import get_secrets_manager

                secrets = get_secrets_manager()
                webhook_url = secrets.get_secret("SLACK_WEBHOOK_URL")
                if webhook_url:
                    await self._send_slack_alert(alert_message)
            except Exception:
                pass  # Slack alerting is optional

            # Send to monitoring system
            from src.infrastructure.monitoring import get_monitoring_manager

            monitoring = get_monitoring_manager()
            await monitoring.record_alert(
                alert_type="budget_threshold",
                severity="warning",
                message=alert_message,
                metadata={
                    "budget_name": budget.name,
                    "usage_percent": usage_percent,
                    "current_usage_usd": current_usage,
                },
            )

            # Log to audit trail
            from src.core.security import get_audit_logger

            audit = get_audit_logger()
            await audit.log_event(
                event_type="BUDGET_ALERT",
                details={"budget": budget.name, "usage": current_usage, "percent": usage_percent},
            )

        except Exception as e:
            logger.error(f"Failed to send budget alert: {str(e)}")

    async def _send_slack_alert(self, message: str):
        """Send alert to Slack via webhook."""
        import aiohttp

        try:
            from src.infrastructure.config import get_secrets_manager

            secrets = get_secrets_manager()
            webhook_url = secrets.get_secret("SLACK_WEBHOOK_URL")
            if not webhook_url:
                return
        except Exception:
            return  # Slack alerting is optional

        try:
            async with aiohttp.ClientSession() as session:
                await session.post(
                    webhook_url, json={"text": message}, timeout=aiohttp.ClientTimeout(total=5)
                )
        except Exception as e:
            logger.warning(f"Failed to send Slack alert: {str(e)}")

    def _start_background_persistence(self):
        """Start background task for database persistence."""
        if self._persist_task is None or self._persist_task.done():
            self._persist_task = asyncio.create_task(self._persistence_worker())
            logger.info("Started cost record persistence background task")

    async def _persistence_worker(self):
        """
        Background worker that persists cost records to database.

        Batches records and flushes every 10 seconds or when batch reaches 100 records.
        Handles graceful shutdown by flushing remaining records.
        """
        batch_size = 100
        batch: list[CostRecord] = []
        batch_timeout = 10.0  # seconds

        logger.info("Cost persistence worker started")

        try:
            while not self._is_shutting_down:
                try:
                    # Wait for records with timeout (batch every 10 seconds)
                    record = await asyncio.wait_for(
                        self._persist_queue.get(), timeout=batch_timeout
                    )
                    batch.append(record)

                    # Flush batch if full
                    if len(batch) >= batch_size:
                        await self._flush_batch(batch)
                        batch = []

                except asyncio.TimeoutError:
                    # Timeout - flush any pending records
                    if batch:
                        await self._flush_batch(batch)
                        batch = []

        except asyncio.CancelledError:
            logger.info("Cost persistence worker cancelled - flushing remaining records")
            # Flush remaining records on shutdown
            if batch:
                await self._flush_batch(batch)
            raise

        except Exception as e:
            logger.error(f"Cost persistence worker error: {e}", exc_info=True)

        finally:
            # Final flush on shutdown
            if batch and not self._is_shutting_down:
                try:
                    await self._flush_batch(batch)
                except Exception as e:
                    logger.error(f"Failed to flush final batch: {e}")

            logger.info("Cost persistence worker stopped")

    async def _flush_batch(self, batch: list[CostRecord]):
        """
        Flush batch of records to database.

        Args:
            batch: List of cost records to persist
        """
        if not batch or not self.db_manager:
            return

        try:
            # Build bulk insert query
            query = """
                INSERT INTO cost_records (
                    record_id, timestamp, user_id, model_name, provider_name, model_tier,
                    prompt_tokens, completion_tokens, total_tokens, cost_usd,
                    request_type, department, correlation_id
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
            """

            # Execute batch insert
            async with self.db_manager.pool.acquire() as conn:
                async with conn.transaction():
                    # Use executemany for batch insert
                    await conn.executemany(
                        query,
                        [
                            (
                                record.record_id,
                                record.timestamp,
                                record.user_id,
                                record.model_name,
                                record.provider_name,
                                MODEL_PRICING.get(record.model_name, {}).get(
                                    "tier", ModelTier.TIER_3_CONVERSATION
                                ),
                                record.tokens_used.get("prompt_tokens", 0),
                                record.tokens_used.get("completion_tokens", 0),
                                record.tokens_used.get("total_tokens", 0),
                                record.cost_usd,
                                record.request_type,
                                record.department,
                                None,  # correlation_id - not in CostRecord dataclass yet
                            )
                            for record in batch
                        ],
                    )

            logger.debug(
                f"Flushed {len(batch)} cost records to database",
                extra={"batch_size": len(batch), "total_cost": sum(r.cost_usd for r in batch)},
            )

        except Exception as e:
            logger.error(
                f"Failed to flush cost records batch: {e}",
                extra={"batch_size": len(batch)},
                exc_info=True,
            )

    def _queue_for_persistence(self, record: CostRecord):
        """
        Queue cost record for async persistence to database.

        Args:
            record: Cost record to persist
        """
        if not self._persistence_enabled:
            return

        try:
            # Non-blocking put - if queue is full, log warning and skip
            self._persist_queue.put_nowait(record)
        except asyncio.QueueFull:
            logger.warning(
                "Persistence queue full - dropping record",
                extra={"queue_size": self._persist_queue.qsize()},
            )

    async def shutdown(self):
        """
        Gracefully shutdown cost tracker and flush remaining records.

        Call this before application shutdown to ensure all records are persisted.
        """
        logger.info("Shutting down cost tracker...")
        self._is_shutting_down = True

        # Cancel persistence worker and wait for it to finish
        if self._persist_task and not self._persist_task.done():
            self._persist_task.cancel()
            try:
                await self._persist_task
            except asyncio.CancelledError:
                pass

        logger.info("Cost tracker shutdown complete")

    def get_usage_summary(
        self, start_date: datetime | None = None, end_date: datetime | None = None
    ) -> CostSummary:
        """
        Get cost usage summary for specified period.

        Args:
            start_date: Start of period (default: 30 days ago)
            end_date: End of period (default: now)

        Returns:
            Cost summary with breakdowns
        """

        if not end_date:
            end_date = datetime.now(UTC)
        if not start_date:
            start_date = end_date - timedelta(days=30)

        # Filter records by date range
        period_records = [
            record for record in self._cost_records if start_date <= record.timestamp <= end_date
        ]

        if not period_records:
            return CostSummary(
                total_cost=0.0,
                total_requests=0,
                average_cost_per_request=0.0,
                cost_by_model={},
                cost_by_provider={},
                cost_by_user={},
                period_start=start_date,
                period_end=end_date,
            )

        # Calculate aggregations
        total_cost = sum(record.cost_usd for record in period_records)
        total_requests = len(period_records)

        # Group by various dimensions
        cost_by_model = defaultdict(float)
        cost_by_provider = defaultdict(float)
        cost_by_user = defaultdict(float)

        for record in period_records:
            cost_by_model[record.model_name] += record.cost_usd
            cost_by_provider[record.provider_name] += record.cost_usd
            cost_by_user[record.user_id] += record.cost_usd

        return CostSummary(
            total_cost=total_cost,
            total_requests=total_requests,
            average_cost_per_request=total_cost / total_requests,
            cost_by_model=dict(cost_by_model),
            cost_by_provider=dict(cost_by_provider),
            cost_by_user=dict(cost_by_user),
            period_start=start_date,
            period_end=end_date,
        )

    def get_user_usage(self, user_id: str, days: int = 30) -> dict[str, Any]:
        """Get usage statistics for specific user."""

        end_date = datetime.now(UTC)
        start_date = end_date - timedelta(days=days)

        user_records = [
            record
            for record in self._cost_records
            if record.user_id == user_id and start_date <= record.timestamp <= end_date
        ]

        if not user_records:
            return {"user_id": user_id, "total_cost": 0.0, "total_requests": 0, "period_days": days}

        total_cost = sum(record.cost_usd for record in user_records)
        total_tokens = sum(record.tokens_used.get("total_tokens", 0) for record in user_records)

        # Group by request type
        cost_by_type = defaultdict(float)
        requests_by_type = defaultdict(int)

        for record in user_records:
            cost_by_type[record.request_type] += record.cost_usd
            requests_by_type[record.request_type] += 1

        return {
            "user_id": user_id,
            "total_cost": total_cost,
            "total_requests": len(user_records),
            "total_tokens": total_tokens,
            "average_cost_per_request": total_cost / len(user_records),
            "cost_by_type": dict(cost_by_type),
            "requests_by_type": dict(requests_by_type),
            "period_days": days,
        }

    def get_model_performance(self) -> dict[str, Any]:
        """Get model performance and cost analysis."""

        model_stats = defaultdict(
            lambda: {
                "total_cost": 0.0,
                "total_requests": 0,
                "total_tokens": 0,
                "average_cost_per_request": 0.0,
                "average_tokens_per_request": 0.0,
            }
        )

        for record in self._cost_records:
            stats = model_stats[record.model_name]
            stats["total_cost"] += record.cost_usd
            stats["total_requests"] += 1
            stats["total_tokens"] += record.tokens_used.get("total_tokens", 0)

        # Calculate averages
        for _model, stats in model_stats.items():
            if stats["total_requests"] > 0:
                stats["average_cost_per_request"] = stats["total_cost"] / stats["total_requests"]
                stats["average_tokens_per_request"] = (
                    stats["total_tokens"] / stats["total_requests"]
                )

        return dict(model_stats)

    def get_budget_status(self) -> dict[str, Any]:
        """Get current budget status and usage."""

        budget_status = {}

        for budget_name, budget in self._budgets.items():
            current_time = datetime.now(UTC)
            usage_key = self._get_budget_usage_key(budget, current_time)
            current_usage = self._budget_usage.get(usage_key, 0.0)

            usage_percent = (
                (current_usage / budget.budget_usd) * 100 if budget.budget_usd > 0 else 0
            )
            remaining_budget = max(0, budget.budget_usd - current_usage)

            budget_status[budget_name] = {
                "budget_usd": budget.budget_usd,
                "current_usage": current_usage,
                "usage_percent": usage_percent,
                "remaining_budget": remaining_budget,
                "threshold_percent": budget.threshold_percent,
                "period": budget.period,
                "exceeded": usage_percent >= budget.threshold_percent,
            }

        return budget_status

    def add_budget_alert(self, budget: BudgetAlert):
        """Add new budget alert configuration."""
        self._budgets[budget.name] = budget
        logger.info(f"Added budget alert: {budget.name} (${budget.budget_usd} {budget.period})")

    def get_cost_optimization_recommendations(self) -> list[dict[str, Any]]:
        """Generate cost optimization recommendations."""

        recommendations = []
        model_perf = self.get_model_performance()

        # Find expensive models with low usage
        for model, stats in model_perf.items():
            if stats["average_cost_per_request"] > 0.10 and stats["total_requests"] < 10:
                recommendations.append(
                    {
                        "type": "model_optimization",
                        "title": f"Consider cheaper model for {model}",
                        "description": f"Model {model} has high cost per request (${stats['average_cost_per_request']:.3f}) with low usage",
                        "potential_savings": "30-60%",
                        "action": "Evaluate tier-1 or tier-2 models for this use case",
                    }
                )

        # Check for batch processing opportunities
        batch_eligible = self._analyze_batch_opportunities()
        if batch_eligible > 5:
            recommendations.append(
                {
                    "type": "batch_optimization",
                    "title": "Enable batch processing for multiple activities",
                    "description": f"Found {batch_eligible} requests that could be batched",
                    "potential_savings": "30-50%",
                    "action": "Batch similar requests to reduce API costs by 40%",
                }
            )

        # Check for caching opportunities
        recent_records = list(self._cost_records)[-100:]  # Last 100 requests
        if recent_records:
            duplicate_requests = len(recent_records) - len(
                {
                    (r.user_id, r.model_name, str(r.tokens_used.get("prompt_tokens", 0)))
                    for r in recent_records
                }
            )

            if duplicate_requests > 5:
                recommendations.append(
                    {
                        "type": "caching_optimization",
                        "title": "Enable aggressive caching",
                        "description": f"Found {duplicate_requests} similar requests in recent history",
                        "potential_savings": "20-40%",
                        "action": "Enable aggressive caching strategy for repeated queries",
                    }
                )

        # Recommend model tier optimization
        tier_usage = self._analyze_tier_usage()
        if tier_usage.get("tier_2_percentage", 0) > 30:
            recommendations.append(
                {
                    "type": "tier_optimization",
                    "title": "Optimize model tier selection",
                    "description": f"High usage of expensive Tier 2 models ({tier_usage['tier_2_percentage']:.1f}%)",
                    "potential_savings": "20-40%",
                    "action": "Review if some Tier 2 requests can use Tier 1 models",
                }
            )

        return recommendations

    def _analyze_batch_opportunities(self) -> int:
        """Analyze how many requests could have been batched."""
        if not self._cost_records:
            return 0

        # Group requests by user and time window (5 minutes)
        batch_windows = defaultdict(list)
        for record in list(self._cost_records)[-100:]:  # Last 100 requests
            window_key = f"{record.user_id}:{record.timestamp.strftime('%Y-%m-%d-%H-%M')[:14]}"
            batch_windows[window_key].append(record)

        # Count windows with multiple requests
        batch_eligible = sum(1 for requests in batch_windows.values() if len(requests) >= 2)
        return batch_eligible

    def _analyze_tier_usage(self) -> dict[str, float]:
        """Analyze model tier usage distribution."""
        if not self._cost_records:
            return {}

        tier_counts = defaultdict(int)
        for record in self._cost_records:
            if record.model_name in MODEL_PRICING:
                tier = MODEL_PRICING[record.model_name]["tier"]
                tier_counts[tier] += 1

        total = sum(tier_counts.values())
        if total == 0:
            return {}

        return {
            "tier_1_percentage": (tier_counts[ModelTier.TIER_1_ANALYSIS] / total) * 100,
            "tier_2_percentage": (tier_counts[ModelTier.TIER_2_ADVICE] / total) * 100,
            "tier_3_percentage": (tier_counts[ModelTier.TIER_3_CONVERSATION] / total) * 100,
        }

    def get_batch_savings_summary(self) -> dict[str, Any]:
        """Get summary of savings from batch processing."""

        batch_records = [r for r in self._cost_records if "batch" in r.request_type.lower()]
        regular_records = [r for r in self._cost_records if "batch" not in r.request_type.lower()]

        if not batch_records:
            return {
                "batch_requests": 0,
                "savings_usd": 0,
                "savings_percentage": 0,
                "message": "No batch processing detected",
            }

        # Calculate actual vs potential costs
        batch_actual_cost = sum(r.cost_usd for r in batch_records)
        batch_token_count = sum(r.tokens_used.get("total_tokens", 0) for r in batch_records)

        # Estimate what cost would have been without batching
        batch_potential_cost = batch_actual_cost / 0.6  # Reverse the 40% discount
        savings = batch_potential_cost - batch_actual_cost

        return {
            "batch_requests": len(batch_records),
            "regular_requests": len(regular_records),
            "batch_actual_cost": batch_actual_cost,
            "batch_potential_cost": batch_potential_cost,
            "savings_usd": savings,
            "savings_percentage": 40.0,  # Fixed 40% savings for batch
            "tokens_processed": batch_token_count,
            "average_batch_size": batch_token_count / max(1, len(batch_records)),
        }

    def export_records(self, start_date: datetime, end_date: datetime) -> str:
        """Export cost records as JSON for analysis."""

        period_records = [
            record for record in self._cost_records if start_date <= record.timestamp <= end_date
        ]

        # Convert to serializable format
        export_data = []
        for record in period_records:
            export_data.append(
                {
                    "record_id": record.record_id,
                    "timestamp": record.timestamp.isoformat(),
                    "user_id": record.user_id,
                    "model_name": record.model_name,
                    "provider_name": record.provider_name,
                    "tokens_used": record.tokens_used,
                    "cost_usd": record.cost_usd,
                    "request_type": record.request_type,
                    "department": record.department,
                }
            )

        return json.dumps(export_data, indent=2)

    def get_tracker_stats(self) -> dict[str, Any]:
        """Get cost tracker statistics."""

        return {
            "total_records": len(self._cost_records),
            "total_cost": self._total_cost,
            "total_requests": self._total_requests,
            "average_cost_per_request": self._total_cost / self._total_requests
            if self._total_requests > 0
            else 0,
            "unique_users": len({record.user_id for record in self._cost_records}),
            "unique_models": len({record.model_name for record in self._cost_records}),
            "budgets_configured": len(self._budgets),
            "oldest_record": min((r.timestamp for r in self._cost_records), default=None),
            "newest_record": max((r.timestamp for r in self._cost_records), default=None),
        }


# Global cost tracker instance
_cost_tracker: CostTracker | None = None


def get_cost_tracker() -> CostTracker:
    """Get or create global cost tracker instance."""
    global _cost_tracker
    if _cost_tracker is None:
        _cost_tracker = CostTracker()
    return _cost_tracker
