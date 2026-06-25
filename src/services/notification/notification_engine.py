"""
Notification Delivery System

Handles multi-channel notification delivery with templates and tracking.
"""

import asyncio
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any

from src.infrastructure.cache.redis_manager import RedisManager
from src.interfaces.slack.adapter import SlackAdapter as SlackClient
from src.shared import get_logger

logger = get_logger(__name__)


class NotificationChannel(Enum):
    """Notification delivery channels."""

    SLACK = "slack"
    EMAIL = "email"
    IN_APP = "in_app"
    WEBHOOK = "webhook"


class NotificationPriority(Enum):
    """Notification priority levels."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class NotificationStatus(Enum):
    """Notification delivery status."""

    PENDING = "pending"
    DELIVERED = "delivered"
    FAILED = "failed"
    RETRYING = "retrying"


@dataclass
class NotificationRequest:
    """Notification request data."""

    notification_id: str
    user_id: str
    channel: NotificationChannel
    priority: NotificationPriority
    template_id: str
    template_data: dict[str, Any]
    metadata: dict[str, Any] | None = None
    scheduled_at: datetime | None = None
    expires_at: datetime | None = None


@dataclass
class NotificationResult:
    """Notification delivery result."""

    notification_id: str
    status: NotificationStatus
    delivered_at: datetime | None = None
    error_message: str | None = None
    channel_response: dict[str, Any] | None = None


class NotificationDeliveryChannel(ABC):
    """Base class for notification delivery channels."""

    @abstractmethod
    async def deliver(
        self, recipient: str, content: dict[str, Any], metadata: dict[str, Any] | None = None
    ) -> NotificationResult:
        """Deliver notification through channel."""
        pass

    @abstractmethod
    async def validate_recipient(self, recipient: str) -> bool:
        """Validate recipient for channel."""
        pass


class SlackNotificationChannel(NotificationDeliveryChannel):
    """Slack notification delivery channel."""

    def __init__(self, slack_client: SlackClient):
        self.slack = slack_client
        self.logger = get_logger(f"{__name__}.slack")

    async def deliver(
        self, recipient: str, content: dict[str, Any], metadata: dict[str, Any] | None = None
    ) -> NotificationResult:
        """Deliver notification via Slack."""
        notification_id = metadata.get("notification_id") if metadata else str(uuid.uuid4())

        try:
            # Send Slack message
            response = await self.slack.send_message(
                channel=recipient,
                text=content.get("text", ""),
                blocks=content.get("blocks"),
                attachments=content.get("attachments"),
            )

            return NotificationResult(
                notification_id=notification_id,
                status=NotificationStatus.DELIVERED,
                delivered_at=datetime.now(UTC),
                channel_response={"ts": response.get("ts")},
            )

        except Exception as e:
            self.logger.error(f"Failed to deliver Slack notification: {str(e)}")
            return NotificationResult(
                notification_id=notification_id,
                status=NotificationStatus.FAILED,
                error_message=str(e),
            )

    async def validate_recipient(self, recipient: str) -> bool:
        """Validate Slack recipient."""
        # Check if user or channel exists
        try:
            if recipient.startswith("U"):
                # User ID
                user = await self.slack.get_user_info(recipient)
                return user is not None
            elif recipient.startswith("C"):
                # Channel ID
                channel = await self.slack.get_channel_info(recipient)
                return channel is not None
            return False
        except Exception:
            return False


class NotificationTemplateEngine:
    """Template engine for notification content generation."""

    def __init__(self, redis_manager: RedisManager):
        self.redis = redis_manager
        self.logger = get_logger(f"{__name__}.templates")
        self.templates = self._load_default_templates()
        self.template_cache_prefix = "notification:template"

    def _load_default_templates(self) -> dict[str, dict[str, Any]]:
        """Load default notification templates."""
        return {
            "competency_report_ready": {
                "slack": {
                    "text": "Your competency report is ready!",
                    "blocks": [
                        {
                            "type": "header",
                            "text": {"type": "plain_text", "text": "📊 Competency Report Ready"},
                        },
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": "Hi {{user_name}},\n\nYour *{{report_type}}* report for *{{period}}* is now available.",
                            },
                        },
                        {
                            "type": "actions",
                            "elements": [
                                {
                                    "type": "button",
                                    "text": {"type": "plain_text", "text": "View Report"},
                                    "style": "primary",
                                    "value": "{{report_id}}",
                                    "action_id": "view_report",
                                },
                                {
                                    "type": "button",
                                    "text": {"type": "plain_text", "text": "Download PDF"},
                                    "value": "{{report_id}}",
                                    "action_id": "download_pdf",
                                },
                            ],
                        },
                    ],
                }
            },
            "goal_milestone_reached": {
                "slack": {
                    "text": "Congratulations on reaching a milestone!",
                    "blocks": [
                        {
                            "type": "header",
                            "text": {"type": "plain_text", "text": "🎯 Milestone Achieved!"},
                        },
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": "Congratulations {{user_name}}! 🎉\n\nYou've completed: *{{milestone_name}}*\n\nProgress: {{progress}}%",
                            },
                        },
                    ],
                }
            },
            "weekly_summary": {
                "slack": {
                    "text": "Your weekly summary",
                    "blocks": [
                        {
                            "type": "header",
                            "text": {"type": "plain_text", "text": "📈 Weekly Summary"},
                        },
                        {
                            "type": "section",
                            "fields": [
                                {
                                    "type": "mrkdwn",
                                    "text": "*Activities Logged:*\n{{activity_count}}",
                                },
                                {
                                    "type": "mrkdwn",
                                    "text": "*Competencies Improved:*\n{{competency_count}}",
                                },
                                {"type": "mrkdwn", "text": "*Top Skill:*\n{{top_skill}}"},
                                {"type": "mrkdwn", "text": "*Growth Rate:*\n{{growth_rate}}%"},
                            ],
                        },
                    ],
                }
            },
        }

    async def render_template(
        self, template_id: str, channel: NotificationChannel, data: dict[str, Any]
    ) -> dict[str, Any]:
        """Render notification template with data."""
        # Get template
        template = self.templates.get(template_id, {})
        channel_template = template.get(channel.value, {})

        if not channel_template:
            raise ValueError(f"Template {template_id} not found for channel {channel.value}")

        # Render template (simple string replacement)
        rendered = self._render_dict(channel_template, data)

        return rendered

    def _render_dict(self, template: Any, data: dict[str, Any]) -> Any:
        """Recursively render template dictionary."""
        if isinstance(template, dict):
            return {k: self._render_dict(v, data) for k, v in template.items()}
        elif isinstance(template, list):
            return [self._render_dict(item, data) for item in template]
        elif isinstance(template, str):
            # Simple template replacement
            result = template
            for key, value in data.items():
                result = result.replace(f"{{{{{key}}}}}", str(value))
            return result
        else:
            return template


class NotificationEngine:
    """Main notification engine for multi-channel delivery."""

    def __init__(self, redis_manager: RedisManager, slack_client: SlackClient | None = None):
        self.redis = redis_manager
        self.logger = get_logger(__name__)

        # Initialize channels
        self.channels: dict[NotificationChannel, NotificationDeliveryChannel] = {}
        if slack_client:
            self.channels[NotificationChannel.SLACK] = SlackNotificationChannel(slack_client)

        # Initialize template engine
        self.template_engine = NotificationTemplateEngine(redis_manager)

        # Configuration
        self.max_retries = 3
        self.retry_delay = 60  # seconds
        self.notification_ttl = 86400  # 24 hours

        # Queue keys
        self.queue_key = "notification:queue"
        self.notification_key_prefix = "notification:data"
        self.user_preferences_key = "notification:preferences"

    async def send_notification(
        self,
        user_id: str,
        template_id: str,
        template_data: dict[str, Any],
        channels: list[NotificationChannel] | None = None,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Send notification to user."""
        notification_id = str(uuid.uuid4())

        # Get user's notification preferences
        if not channels:
            channels = await self._get_user_channels(user_id)

        # Create notification requests for each channel
        for channel in channels:
            request = NotificationRequest(
                notification_id=f"{notification_id}_{channel.value}",
                user_id=user_id,
                channel=channel,
                priority=priority,
                template_id=template_id,
                template_data=template_data,
                metadata=metadata,
            )

            # Add to queue
            await self._enqueue_notification(request)

        self.logger.info(f"Queued notification {notification_id} for user {user_id}")
        return notification_id

    async def _enqueue_notification(self, request: NotificationRequest):
        """Add notification to processing queue."""
        # Store notification data
        notification_key = f"{self.notification_key_prefix}:{request.notification_id}"
        await self.redis.set(
            notification_key, self._serialize_request(request), ttl=self.notification_ttl
        )

        # Add to priority queue
        priority_score = self._calculate_priority_score(request.priority)
        await self.redis.zadd(self.queue_key, {request.notification_id: priority_score})

    async def process_notifications(self):
        """Process notification queue."""
        while True:
            try:
                # Get highest priority notification
                notification_ids = await self.redis.zrevrange(
                    self.queue_key, 0, 0, withscores=False
                )

                if not notification_ids:
                    await asyncio.sleep(1)
                    continue

                notification_id = notification_ids[0]

                # Remove from queue
                await self.redis.zrem(self.queue_key, notification_id)

                # Process notification
                await self._deliver_notification(notification_id)

            except Exception as e:
                self.logger.error(f"Error processing notifications: {str(e)}")
                await asyncio.sleep(5)

    async def _deliver_notification(self, notification_id: str):
        """Deliver a single notification."""
        # Load notification data
        notification_key = f"{self.notification_key_prefix}:{notification_id}"
        request_data = await self.redis.get(notification_key)

        if not request_data:
            self.logger.error(f"Notification {notification_id} not found")
            return

        request = self._deserialize_request(request_data)

        # Check if expired
        if request.expires_at and datetime.now(UTC) > request.expires_at:
            self.logger.info(f"Notification {notification_id} expired")
            return

        # Get delivery channel
        channel = self.channels.get(request.channel)
        if not channel:
            self.logger.error(f"Channel {request.channel.value} not configured")
            return

        # Get recipient info
        recipient = await self._get_user_recipient(request.user_id, request.channel)
        if not recipient:
            self.logger.error(
                f"No recipient found for user {request.user_id} on channel {request.channel.value}"
            )
            return

        # Render template
        try:
            content = await self.template_engine.render_template(
                request.template_id, request.channel, request.template_data
            )
        except Exception as e:
            self.logger.error(f"Failed to render template: {str(e)}")
            return

        # Deliver notification
        result = await channel.deliver(
            recipient,
            content,
            {"notification_id": notification_id, **request.metadata}
            if request.metadata
            else {"notification_id": notification_id},
        )

        # Store result
        await self._store_result(notification_id, result)

        # Handle retry if failed
        if result.status == NotificationStatus.FAILED:
            await self._handle_retry(request)

    async def _handle_retry(self, request: NotificationRequest):
        """Handle notification retry."""
        retry_count = request.metadata.get("retry_count", 0) if request.metadata else 0

        if retry_count < self.max_retries:
            # Update retry count
            if not request.metadata:
                request.metadata = {}
            request.metadata["retry_count"] = retry_count + 1

            # Schedule retry
            request.scheduled_at = datetime.now(UTC) + timedelta(
                seconds=self.retry_delay * (retry_count + 1)
            )

            # Re-enqueue
            await self._enqueue_notification(request)
            self.logger.info(
                f"Scheduled retry {retry_count + 1} for notification {request.notification_id}"
            )
        else:
            self.logger.error(
                f"Notification {request.notification_id} failed after {self.max_retries} retries"
            )

    async def _get_user_channels(self, user_id: str) -> list[NotificationChannel]:
        """Get user's preferred notification channels."""
        prefs_key = f"{self.user_preferences_key}:{user_id}"
        preferences = await self.redis.get(prefs_key)

        if preferences:
            return [
                NotificationChannel(ch)
                for ch in preferences.get("channels", [NotificationChannel.SLACK.value])
            ]

        # Default to Slack
        return [NotificationChannel.SLACK]

    async def _get_user_recipient(self, user_id: str, channel: NotificationChannel) -> str | None:
        """Get user's recipient ID for channel."""
        # This would typically look up the user's channel-specific ID
        # For now, return the user_id for Slack (assuming it's a Slack user ID)
        if channel == NotificationChannel.SLACK:
            return user_id
        return None

    def _calculate_priority_score(self, priority: NotificationPriority) -> float:
        """Calculate priority score for queue ordering."""
        scores = {
            NotificationPriority.LOW: 1.0,
            NotificationPriority.NORMAL: 5.0,
            NotificationPriority.HIGH: 10.0,
            NotificationPriority.CRITICAL: 100.0,
        }
        # Add timestamp component to ensure FIFO within same priority
        return scores[priority] * 1000000 - datetime.now(UTC).timestamp()

    def _serialize_request(self, request: NotificationRequest) -> dict[str, Any]:
        """Serialize notification request."""
        return {
            "notification_id": request.notification_id,
            "user_id": request.user_id,
            "channel": request.channel.value,
            "priority": request.priority.value,
            "template_id": request.template_id,
            "template_data": request.template_data,
            "metadata": request.metadata,
            "scheduled_at": request.scheduled_at.isoformat() if request.scheduled_at else None,
            "expires_at": request.expires_at.isoformat() if request.expires_at else None,
        }

    def _deserialize_request(self, data: dict[str, Any]) -> NotificationRequest:
        """Deserialize notification request."""
        return NotificationRequest(
            notification_id=data["notification_id"],
            user_id=data["user_id"],
            channel=NotificationChannel(data["channel"]),
            priority=NotificationPriority(data["priority"]),
            template_id=data["template_id"],
            template_data=data["template_data"],
            metadata=data.get("metadata"),
            scheduled_at=datetime.fromisoformat(data["scheduled_at"])
            if data.get("scheduled_at")
            else None,
            expires_at=datetime.fromisoformat(data["expires_at"])
            if data.get("expires_at")
            else None,
        )

    async def _store_result(self, notification_id: str, result: NotificationResult):
        """Store notification delivery result."""
        result_key = f"notification:result:{notification_id}"
        await self.redis.set(
            result_key,
            {
                "notification_id": result.notification_id,
                "status": result.status.value,
                "delivered_at": result.delivered_at.isoformat() if result.delivered_at else None,
                "error_message": result.error_message,
                "channel_response": result.channel_response,
            },
            ttl=self.notification_ttl,
        )


# Export
__all__ = [
    "NotificationEngine",
    "NotificationChannel",
    "NotificationPriority",
    "NotificationStatus",
    "NotificationRequest",
    "NotificationResult",
    "NotificationTemplateEngine",
]
