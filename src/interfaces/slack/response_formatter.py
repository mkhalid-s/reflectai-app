"""
Slack Response Formatter using Block Kit

Implements Requirements 17, 19: Rich, interactive responses with fast-loading layouts
and user-friendly formatting for various response types.
"""

from datetime import datetime
from typing import Any

from src.shared import get_logger

logger = get_logger(__name__)


class ResponseFormatter:
    """
    Creates rich Slack Block Kit responses for various interaction types.

    Features:
    - Rich Block Kit layouts
    - Interactive elements
    - Consistent formatting
    - Accessibility support
    """

    def __init__(self):
        logger.info("Response formatter initialized")

    def create_greeting_blocks(self, user_id: str) -> list[dict[str, Any]]:
        """Create greeting response with interactive elements."""
        return [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"👋 Hello <@{user_id}>! I'm *ReflectAI*, your competency development assistant.",
                },
            },
            {"type": "divider"},
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "🎯 *What I can help you with:*\\n• Competency analysis and skill assessment\\n• Career development guidance\\n• Progress tracking and reports\\n• Learning recommendations",
                },
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "📊 Start Analysis", "emoji": True},
                        "value": "start_analysis",
                        "action_id": "start_analysis_button",
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "📈 View Reports", "emoji": True},
                        "value": "view_reports",
                        "action_id": "view_reports_button",
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "❓ Get Help", "emoji": True},
                        "value": "get_help",
                        "action_id": "get_help_button",
                    },
                ],
            },
        ]

    def create_dm_greeting_blocks(self, user_id: str) -> list[dict[str, Any]]:
        """Create personalized DM greeting with quick actions."""
        return [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "👋 Hi there! I'm *ReflectAI*. I'm here to help you with competency development and career growth.",
                },
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": "💡 *Quick Start Options:*"},
                "accessory": {
                    "type": "image",
                    "image_url": "https://via.placeholder.com/75x75/4285F4/FFFFFF?text=AI",
                    "alt_text": "ReflectAI",
                },
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": "*📊 Analysis*\\nAnalyze your activities and skills",
                    },
                    {"type": "mrkdwn", "text": "*📈 Reports*\\nGenerate progress reports"},
                    {"type": "mrkdwn", "text": "*🎯 Goals*\\nSet development targets"},
                    {"type": "mrkdwn", "text": "*💬 Chat*\\nAsk questions anytime"},
                ],
            },
        ]

    def create_coming_soon_blocks(self, feature_name: str) -> list[dict[str, Any]]:
        """Create 'coming soon' blocks for features in development."""
        return [
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"🚀 *{feature_name}* is coming soon!"},
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"I'm being enhanced with {feature_name.lower()} capabilities. This powerful feature will be available in the next update!",
                },
            },
            {
                "type": "context",
                "elements": [{"type": "mrkdwn", "text": "🔧 *Production Next Release"}],
            },
        ]

    def create_help_blocks(self) -> list[dict[str, Any]]:
        """Create comprehensive help blocks."""
        return [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": "🤖 ReflectAI Help Center", "emoji": True},
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*How to interact with me:*\\n• Mention me (@ReflectAI) in any channel\\n• Send me a direct message\\n• Use slash commands like `/reflect`",
                },
            },
            {"type": "divider"},
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*🎯 Current Capabilities:*\\n• System information and help\\n• Basic conversation and guidance\\n• Feature previews and roadmap",
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*🚀 Coming Soon:*\\n• Competency analysis with AI agents\\n• Detailed progress reports\\n• Skill development recommendations\\n• Career guidance workflows",
                },
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": "💡 *Tip:* Try asking about specific features or saying hello to get started!",
                    }
                ],
            },
        ]

    def create_command_help_blocks(self) -> list[dict[str, Any]]:
        """Create help blocks for slash commands."""
        return [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": "⚡ ReflectAI Commands", "emoji": True},
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": "*`/reflect help`*\\nShow this help message"},
                    {"type": "mrkdwn", "text": "*`/reflect status`*\\nCheck system status"},
                    {
                        "type": "mrkdwn",
                        "text": "*`/reflect analyze [text]`*\\nRequest analysis (coming soon)",
                    },
                    {
                        "type": "mrkdwn",
                        "text": "*`/reflect report`*\\nGenerate reports (coming soon)",
                    },
                ],
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": "🔧 *Most features are being implemented in production*",
                    }
                ],
            },
        ]

    def create_processing_blocks(self, request_text: str) -> list[dict[str, Any]]:
        """Create blocks showing request processing status."""
        return [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"⏳ *Processing your request:* {request_text[:100]}{'...' if len(request_text) > 100 else ''}",
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "🤖 I'm working on this! Advanced processing capabilities are coming in production with AI agent integration.",
                },
            },
        ]

    def create_comprehensive_help_blocks(self, user_id: str) -> list[dict[str, Any]]:
        """Create comprehensive help documentation."""
        return [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "📚 ReflectAI Complete Guide",
                    "emoji": True,
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"Welcome <@{user_id}>! Here's everything you need to know about ReflectAI:",
                },
            },
            {"type": "divider"},
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*🏗️ Current Status: production Complete*\\nSecure foundation with error handling, logging, configuration, and development tools all implemented and tested.",
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*🚧 In Development: production*\\n• Slack integration (you're seeing this!)\\n• AI agent system (Analysis + Advisor)\\n• Temporal workflow orchestration\\n• Core business logic",
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*📝 How to Use:*\\n• Mention @ReflectAI in channels\\n• Send direct messages\\n• Use `/reflect` commands\\n• Visit the Home tab",
                },
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"🤖 ReflectAI v2.0.0 | ReflectAI Platform | {datetime.now().strftime('%Y-%m-%d')}",
                    }
                ],
            },
        ]

    def create_error_blocks(
        self, error_message: str, recovery_suggestions: list[str] = None
    ) -> list[dict[str, Any]]:
        """Create user-friendly error message blocks."""
        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"⚠️ *Oops! Something went wrong*\\n{error_message}",
                },
            }
        ]

        if recovery_suggestions:
            blocks.append(
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*💡 Try this:*\\n"
                        + "\\n".join(f"• {suggestion}" for suggestion in recovery_suggestions),
                    },
                }
            )

        blocks.append(
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": "🔄 You can try again, or contact support if the issue persists.",
                    }
                ],
            }
        )

        return blocks

    def create_status_blocks(self) -> list[dict[str, Any]]:
        """Create system status blocks."""
        return [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": "🔍 ReflectAI System Status", "emoji": True},
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": "*Production* ✅ Complete\\nFoundation systems active",
                    },
                    {
                        "type": "mrkdwn",
                        "text": "*Production* 🚧 In Progress\\nSlack integration active",
                    },
                    {
                        "type": "mrkdwn",
                        "text": "*AI Agents:* ⏳ Coming Soon\\nAnalysis + Advisor agents",
                    },
                    {
                        "type": "mrkdwn",
                        "text": "*Workflows:* ⏳ Coming Soon\\nTemporal orchestration",
                    },
                ],
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"🤖 All core systems operational | Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                    }
                ],
            },
        ]
