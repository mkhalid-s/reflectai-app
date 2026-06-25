"""
Comprehensive Slack Slash Commands for ReflectAI

Implements
- /reflect: Start competency analysis conversation
- /analyze: Request detailed analysis of recent activities
- /report: Generate and download competency report
- /help: Get help and learn about features
- /status: Check system status (dev/staging only)
- /debug: Debug information and diagnostics (dev only)
"""

import json
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from src.infrastructure.config import get_config_manager
from src.infrastructure.events.event_deduplicator import DeduplicationConfig, get_event_deduplicator
from src.infrastructure.monitoring import get_or_create_correlation_id
from src.shared import get_logger

from .response_formatter import ResponseFormatter
from .threading import ThreadingManager

logger = get_logger(__name__)


class SlackSlashCommands:
    """
    Comprehensive slash command handlers for ReflectAI.

    Implements all slash commands specified in
    - Command validation and parameter parsing
    - Redis-based deduplication
    - Environment-specific commands (debug/status)
    - Comprehensive help system
    - Error handling and recovery
    """

    def __init__(
        self,
        response_formatter: ResponseFormatter,
        threading_manager: ThreadingManager | None = None,
    ):
        self.response_formatter = response_formatter
        self.threading_manager = threading_manager
        self.config = get_config_manager().get_config()

        # Initialize Redis-based deduplication
        self.deduplicator = None
        self._init_deduplication()

        # Command routing map
        self.command_handlers = {
            "/reflect": self.handle_reflect_command,
            "/analyze": self.handle_analyze_command,
            "/report": self.handle_report_command,
            "/help": self.handle_help_command,
        }

        # Add development commands for non-production environments
        if self.config.app.environment != "production":
            self.command_handlers.update(
                {
                    "/status": self.handle_status_command,
                    "/debug": self.handle_debug_command,
                }
            )

        logger.info(
            "Slack slash commands initialized",
            extra={
                "command_count": len(self.command_handlers),
                "environment": self.config.app.environment,
            },
        )

    async def _init_deduplication(self):
        """Initialize Redis-based command deduplication."""
        try:
            dedup_config = DeduplicationConfig(
                default_ttl_seconds=300,  # 5 minutes for command deduplication
                key_prefix="slack_command_dedup",
                temporal_window_seconds=60,  # 1 minute temporal window
                enable_metrics=True,
            )
            self.deduplicator = await get_event_deduplicator(dedup_config)
            logger.info("Redis command deduplication initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize Redis command deduplication: {e}", exc_info=True)

    async def route_command(
        self, command: str, ack: Callable, respond: Callable, command_data: dict[str, Any]
    ):
        """
        Route slash command to appropriate handler.

        Args:
            command: Command name (e.g., "/reflect")
            ack: Slack acknowledgment function
            respond: Slack response function
            command_data: Command data from Slack
        """
        try:
            # Acknowledge immediately
            await ack()

            # Check for duplicate command
            user_id = command_data.get("user_id")
            if await self._is_duplicate_command(command_data, command, user_id):
                logger.debug(f"Duplicate {command} command, skipping", extra={"user_id": user_id})
                return

            # Route to appropriate handler
            if command in self.command_handlers:
                await self.command_handlers[command](respond, command_data)
            else:
                await self._handle_unknown_command(respond, command, command_data)

        except Exception as e:
            logger.error(
                f"Error processing {command} command: {e}",
                extra={"command": command, "user_id": command_data.get("user_id")},
                exc_info=True,
            )

            await respond(
                {
                    "response_type": "ephemeral",
                    "text": "Sorry, I encountered an error processing your command. Please try again.",
                }
            )

    async def handle_reflect_command(self, respond: Callable, command_data: dict[str, Any]):
        """
        Handle /reflect command - Start competency analysis conversation.

        Usage: /reflect [time period] [competency area]
        Examples:
        - /reflect
        - /reflect last week
        - /reflect communication skills
        - /reflect last month leadership
        """
        correlation_id = get_or_create_correlation_id()
        user_id = command_data.get("user_id")
        text = command_data.get("text", "").strip()

        logger.info(
            "Processing /reflect command",
            extra={"correlation_id": correlation_id, "user_id": user_id, "command_text": text},
        )

        try:
            if not text or text.lower() == "help":
                # Show help for reflect command
                await respond(
                    {
                        "response_type": "ephemeral",
                        "text": "ReflectAI Competency Analysis",
                        "blocks": self._create_reflect_help_blocks(),
                    }
                )
                return

            # Parse command parameters
            params = self._parse_reflect_params(text)

            # Create interactive blocks for analysis initiation
            blocks = self._create_reflect_analysis_blocks(
                user_id=user_id,
                time_period=params.get("time_period", "last week"),
                competency_area=params.get("competency_area", "overall"),
            )

            await respond(
                {
                    "response_type": "in_channel",
                    "text": f"Starting competency analysis for {params.get('time_period', 'last week')}...",
                    "blocks": blocks,
                }
            )

        except Exception as e:
            logger.error(f"Error in /reflect command: {e}", exc_info=True)
            await respond(
                {
                    "response_type": "ephemeral",
                    "text": "Failed to start analysis. Please try again with `/reflect help` for usage information.",
                }
            )

    async def handle_analyze_command(self, respond: Callable, command_data: dict[str, Any]):
        """
        Handle /analyze command - Request detailed analysis of recent activities.

        Usage: /analyze [days] [focus area]
        Examples:
        - /analyze
        - /analyze 7
        - /analyze 14 communication
        - /analyze 30 leadership skills
        """
        correlation_id = get_or_create_correlation_id()
        user_id = command_data.get("user_id")
        text = command_data.get("text", "").strip()

        logger.info(
            "Processing /analyze command",
            extra={"correlation_id": correlation_id, "user_id": user_id, "command_text": text},
        )

        try:
            if text.lower() == "help":
                await respond(
                    {
                        "response_type": "ephemeral",
                        "text": "ReflectAI Activity Analysis",
                        "blocks": self._create_analyze_help_blocks(),
                    }
                )
                return

            # Parse analysis parameters
            params = self._parse_analyze_params(text)
            days = params.get("days", 7)
            focus_area = params.get("focus_area", "all activities")

            # Create analysis request blocks
            blocks = self._create_analysis_request_blocks(
                user_id=user_id, days=days, focus_area=focus_area
            )

            await respond(
                {
                    "response_type": "in_channel",
                    "text": f"Analyzing your {focus_area} from the last {days} days...",
                    "blocks": blocks,
                }
            )

        except Exception as e:
            logger.error(f"Error in /analyze command: {e}", exc_info=True)
            await respond(
                {
                    "response_type": "ephemeral",
                    "text": "Failed to start analysis. Please try again with `/analyze help` for usage information.",
                }
            )

    async def handle_report_command(self, respond: Callable, command_data: dict[str, Any]):
        """
        Handle /report command - Generate and download competency report.

        Usage: /report [format] [time period]
        Examples:
        - /report
        - /report pdf
        - /report pdf last month
        - /report summary last week
        """
        correlation_id = get_or_create_correlation_id()
        user_id = command_data.get("user_id")
        text = command_data.get("text", "").strip()

        logger.info(
            "Processing /report command",
            extra={"correlation_id": correlation_id, "user_id": user_id, "command_text": text},
        )

        try:
            if text.lower() == "help":
                await respond(
                    {
                        "response_type": "ephemeral",
                        "text": "ReflectAI Report Generation",
                        "blocks": self._create_report_help_blocks(),
                    }
                )
                return

            # Parse report parameters
            params = self._parse_report_params(text)
            format_type = params.get("format", "pdf")
            time_period = params.get("time_period", "last month")

            # Create report generation blocks
            blocks = self._create_report_generation_blocks(
                user_id=user_id, format_type=format_type, time_period=time_period
            )

            await respond(
                {
                    "response_type": "ephemeral",  # Reports are private
                    "text": f"Generating your {format_type} competency report for {time_period}...",
                    "blocks": blocks,
                }
            )

        except Exception as e:
            logger.error(f"Error in /report command: {e}", exc_info=True)
            await respond(
                {
                    "response_type": "ephemeral",
                    "text": "Failed to generate report. Please try again with `/report help` for usage information.",
                }
            )

    async def handle_help_command(self, respond: Callable, command_data: dict[str, Any]):
        """
        Handle /help command - Get help and learn about features.

        Usage: /help [topic]
        Examples:
        - /help
        - /help commands
        - /help analysis
        - /help reports
        """
        user_id = command_data.get("user_id")
        text = command_data.get("text", "").strip()

        logger.info("Processing /help command", extra={"user_id": user_id, "help_topic": text})

        try:
            # Determine help topic
            topic = text.lower() if text else "general"

            if topic == "commands":
                blocks = self._create_commands_help_blocks()
            elif topic == "analysis":
                blocks = self._create_analysis_help_blocks()
            elif topic == "reports":
                blocks = self._create_reports_help_blocks()
            else:
                blocks = self._create_general_help_blocks(user_id)

            await respond(
                {
                    "response_type": "ephemeral",
                    "text": "ReflectAI Help & Documentation",
                    "blocks": blocks,
                }
            )

        except Exception as e:
            logger.error(f"Error in /help command: {e}", exc_info=True)
            await respond(
                {
                    "response_type": "ephemeral",
                    "text": "I can help you with ReflectAI features. Try `/help commands` for a list of available commands.",
                }
            )

    async def handle_status_command(self, respond: Callable, command_data: dict[str, Any]):
        """
        Handle /status command - Check system status (dev/staging only).

        Usage: /status [component]
        Examples:
        - /status
        - /status database
        - /status cache
        - /status llm
        """
        user_id = command_data.get("user_id")
        text = command_data.get("text", "").strip()

        logger.info("Processing /status command", extra={"user_id": user_id, "component": text})

        try:
            component = text.lower() if text else "all"

            # Get system status information
            status_info = await self._get_system_status(component)

            blocks = self._create_status_blocks(status_info, component)

            await respond(
                {
                    "response_type": "ephemeral",
                    "text": f"ReflectAI System Status - {component.title()}",
                    "blocks": blocks,
                }
            )

        except Exception as e:
            logger.error(f"Error in /status command: {e}", exc_info=True)
            await respond(
                {
                    "response_type": "ephemeral",
                    "text": "Failed to retrieve system status. Please try again.",
                }
            )

    async def handle_debug_command(self, respond: Callable, command_data: dict[str, Any]):
        """
        Handle /debug command - Debug information (development only).

        Usage: /debug [component]
        Examples:
        - /debug
        - /debug cache
        - /debug events
        - /debug metrics
        """
        if self.config.app.environment == "production":
            await respond(
                {
                    "response_type": "ephemeral",
                    "text": "Debug commands are not available in production.",
                }
            )
            return

        user_id = command_data.get("user_id")
        text = command_data.get("text", "").strip()

        logger.info(
            "Processing /debug command", extra={"user_id": user_id, "debug_component": text}
        )

        try:
            component = text.lower() if text else "general"

            # Get debug information
            debug_info = await self._get_debug_info(component)

            blocks = self._create_debug_blocks(debug_info, component)

            await respond(
                {
                    "response_type": "ephemeral",
                    "text": f"ReflectAI Debug Info - {component.title()}",
                    "blocks": blocks,
                }
            )

        except Exception as e:
            logger.error(f"Error in /debug command: {e}", exc_info=True)
            await respond(
                {
                    "response_type": "ephemeral",
                    "text": "Failed to retrieve debug information. Please try again.",
                }
            )

    async def _handle_unknown_command(
        self, respond: Callable, command: str, command_data: dict[str, Any]
    ):
        """Handle unknown slash commands."""
        available_commands = list(self.command_handlers.keys())

        await respond(
            {
                "response_type": "ephemeral",
                "text": f"Unknown command: `{command}`",
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"I don't recognize the command `{command}`.",
                        },
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "*Available commands:*\n"
                            + "\n".join(f"• `{cmd}`" for cmd in available_commands),
                        },
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "Use `/help` for detailed information about each command.",
                        },
                    },
                ],
            }
        )

    async def _is_duplicate_command(
        self, command_data: dict[str, Any], command: str, user_id: str | None = None
    ) -> bool:
        """Check if command is a duplicate using Redis deduplication."""
        if self.deduplicator:
            try:
                custom_key_fields = ["user_id", "command", "text", "trigger_id"]

                result = await self.deduplicator.check_and_store(
                    event_data=command_data,
                    event_type=f"slash_command_{command.lstrip('/')}",
                    user_id=user_id,
                    custom_key_fields=custom_key_fields,
                )

                return result.is_duplicate

            except Exception as e:
                logger.warning(
                    f"Redis command deduplication failed: {e}",
                    extra={"command": command, "user_id": user_id},
                )

        return False

    def _parse_reflect_params(self, text: str) -> dict[str, Any]:
        """Parse /reflect command parameters."""
        params = {"time_period": "last week", "competency_area": "overall"}

        if not text:
            return params

        words = text.lower().split()

        # Look for time period keywords
        time_patterns = {
            "today": "today",
            "yesterday": "yesterday",
            "week": "last week",
            "month": "last month",
            "quarter": "last quarter",
        }

        for word in words:
            for pattern, period in time_patterns.items():
                if pattern in word:
                    params["time_period"] = period
                    break

        # Look for competency area keywords
        competency_patterns = {
            "leadership": "leadership",
            "communication": "communication",
            "technical": "technical skills",
            "collaboration": "collaboration",
            "problem": "problem solving",
            "creativity": "creativity",
            "adaptability": "adaptability",
        }

        for word in words:
            for pattern, competency in competency_patterns.items():
                if pattern in word:
                    params["competency_area"] = competency
                    break

        return params

    def _parse_analyze_params(self, text: str) -> dict[str, Any]:
        """Parse /analyze command parameters."""
        params = {"days": 7, "focus_area": "all activities"}

        if not text:
            return params

        words = text.split()

        # Look for number of days
        for word in words:
            if word.isdigit():
                days = int(word)
                if 1 <= days <= 365:  # Reasonable bounds
                    params["days"] = days
                break

        # Look for focus area
        focus_patterns = {
            "communication": "communication",
            "leadership": "leadership",
            "meetings": "meetings",
            "collaboration": "collaboration",
            "coding": "coding",
            "development": "development",
        }

        text_lower = text.lower()
        for pattern, focus in focus_patterns.items():
            if pattern in text_lower:
                params["focus_area"] = focus
                break

        return params

    def _parse_report_params(self, text: str) -> dict[str, Any]:
        """Parse /report command parameters."""
        params = {"format": "pdf", "time_period": "last month"}

        if not text:
            return params

        text_lower = text.lower()

        # Look for format
        if "pdf" in text_lower:
            params["format"] = "pdf"
        elif "summary" in text_lower:
            params["format"] = "summary"
        elif "detailed" in text_lower:
            params["format"] = "detailed"

        # Look for time period
        if "week" in text_lower:
            params["time_period"] = "last week"
        elif "month" in text_lower:
            params["time_period"] = "last month"
        elif "quarter" in text_lower:
            params["time_period"] = "last quarter"

        return params

    def _create_reflect_help_blocks(self) -> list[dict[str, Any]]:
        """Create help blocks for /reflect command."""
        return [
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": "*🔍 /reflect* - Start competency analysis"},
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*Usage:*\n• `/reflect` - General analysis\n• `/reflect last week` - Specific time period\n• `/reflect communication` - Focus area\n• `/reflect last month leadership` - Combined parameters",
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*Examples:*\n• `/reflect` - Analyze overall competencies from last week\n• `/reflect communication skills` - Focus on communication\n• `/reflect last quarter` - Quarterly analysis",
                },
            },
        ]

    def _create_analyze_help_blocks(self) -> list[dict[str, Any]]:
        """Create help blocks for /analyze command."""
        return [
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": "*📊 /analyze* - Detailed activity analysis"},
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*Usage:*\n• `/analyze` - Last 7 days, all activities\n• `/analyze 14` - Specific number of days\n• `/analyze communication` - Focus on area\n• `/analyze 30 leadership` - Days + focus area",
                },
            },
        ]

    def _create_report_help_blocks(self) -> list[dict[str, Any]]:
        """Create help blocks for /report command."""
        return [
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": "*📄 /report* - Generate competency reports"},
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*Formats:*\n• `pdf` - Complete PDF report\n• `summary` - Brief summary\n• `detailed` - Comprehensive analysis",
                },
            },
        ]

    def _create_reflect_analysis_blocks(
        self, user_id: str, time_period: str, competency_area: str
    ) -> list[dict[str, Any]]:
        """Create blocks for reflect analysis initiation."""
        return [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"🔍 *Starting Competency Analysis*\n*Period:* {time_period}\n*Focus:* {competency_area}",
                },
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "Start Analysis"},
                        "value": f"start_analysis_{user_id}_{time_period}_{competency_area}",
                        "action_id": "start_competency_analysis",
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "Customize"},
                        "value": f"customize_analysis_{user_id}",
                        "action_id": "customize_analysis",
                    },
                ],
            },
        ]

    def _create_analysis_request_blocks(
        self, user_id: str, days: int, focus_area: str
    ) -> list[dict[str, Any]]:
        """Create blocks for analysis request."""
        return [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"📊 *Activity Analysis Request*\n*Timeframe:* Last {days} days\n*Focus:* {focus_area}",
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "I'll analyze your activities and provide insights on your competency development.",
                },
            },
        ]

    def _create_report_generation_blocks(
        self, user_id: str, format_type: str, time_period: str
    ) -> list[dict[str, Any]]:
        """Create blocks for report generation."""
        return [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"📄 *Generating Report*\n*Format:* {format_type.upper()}\n*Period:* {time_period}",
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "Your report is being generated. You'll receive a notification when it's ready for download.",
                },
            },
        ]

    def _create_general_help_blocks(self, user_id: str) -> list[dict[str, Any]]:
        """Create general help blocks."""
        commands = list(self.command_handlers.keys())

        return [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*🤖 ReflectAI - AI-Powered Competency Analysis*\n\nI help you understand and develop your professional competencies through intelligent analysis of your work activities.",
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*Available Commands:*\n"
                    + "\n".join(f"• `{cmd}`" for cmd in commands[:4]),
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*Quick Start:*\n• Use `/reflect` to start an analysis\n• Try `/analyze` for detailed insights\n• Generate reports with `/report`",
                },
            },
        ]

    def _create_commands_help_blocks(self) -> list[dict[str, Any]]:
        """Create command-specific help blocks."""
        return [
            {"type": "section", "text": {"type": "mrkdwn", "text": "*📋 Available Commands*"}},
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": "*🔍 /reflect*\nStart competency analysis"},
                    {"type": "mrkdwn", "text": "*📊 /analyze*\nDetailed activity analysis"},
                    {"type": "mrkdwn", "text": "*📄 /report*\nGenerate reports"},
                    {"type": "mrkdwn", "text": "*❓ /help*\nGet help and documentation"},
                ],
            },
        ]

    def _create_analysis_help_blocks(self) -> list[dict[str, Any]]:
        """Create analysis-specific help blocks."""
        return [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*📈 Analysis Features*\n\nReflectAI analyzes your activities to provide insights on:",
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "• *Leadership* - Team coordination, decision-making\n• *Communication* - Messaging patterns, collaboration\n• *Technical Skills* - Problem-solving, innovation\n• *Adaptability* - Learning, change management",
                },
            },
        ]

    def _create_reports_help_blocks(self) -> list[dict[str, Any]]:
        """Create reports-specific help blocks."""
        return [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*📊 Report Types*\n\nGenerate comprehensive competency reports:",
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "• *PDF Reports* - Complete analysis with charts\n• *Summary* - Quick overview of key insights\n• *Detailed* - In-depth competency breakdown",
                },
            },
        ]

    async def _get_system_status(self, component: str) -> dict[str, Any]:
        """Get system status information."""
        # This would integrate with actual health check systems
        return {
            "status": "healthy",
            "component": component,
            "timestamp": datetime.now(UTC).isoformat(),
            "environment": self.config.app.environment,
            "version": self.config.app.version,
        }

    async def _get_debug_info(self, component: str) -> dict[str, Any]:
        """Get debug information."""
        debug_info = {
            "timestamp": datetime.now(UTC).isoformat(),
            "environment": self.config.app.environment,
            "component": component,
        }

        if component == "cache" and self.deduplicator:
            try:
                metrics = await self.deduplicator.get_metrics()
                debug_info["deduplication_metrics"] = metrics
            except Exception as e:
                debug_info["deduplication_error"] = str(e)

        return debug_info

    def _create_status_blocks(
        self, status_info: dict[str, Any], component: str
    ) -> list[dict[str, Any]]:
        """Create status display blocks."""
        status_emoji = "🟢" if status_info.get("status") == "healthy" else "🔴"

        return [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"{status_emoji} *System Status - {component.title()}*",
                },
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Status:* {status_info.get('status', 'unknown')}"},
                    {
                        "type": "mrkdwn",
                        "text": f"*Environment:* {status_info.get('environment', 'unknown')}",
                    },
                ],
            },
        ]

    def _create_debug_blocks(
        self, debug_info: dict[str, Any], component: str
    ) -> list[dict[str, Any]]:
        """Create debug information blocks."""
        return [
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"🔧 *Debug Info - {component.title()}*"},
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"```\n{json.dumps(debug_info, indent=2, default=str)}\n```",
                },
            },
        ]


# Global instance
_slash_commands: SlackSlashCommands | None = None


def get_slash_commands(
    response_formatter: ResponseFormatter, threading_manager: ThreadingManager | None = None
) -> SlackSlashCommands:
    """Get or create global slash commands instance."""
    global _slash_commands
    if _slash_commands is None:
        _slash_commands = SlackSlashCommands(response_formatter, threading_manager)
    return _slash_commands
