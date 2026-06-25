"""
Slack Block Builder for ReflectAI

Provides utility methods to build Slack Block Kit messages for various scenarios.
"""

from typing import Any


class SlackBlockBuilder:
    """
    Builder class for creating Slack Block Kit formatted messages.

    Provides methods for error messages, progress updates, analysis results,
    and generic responses following Slack's Block Kit best practices.
    """

    def build_error_message(
        self, error_message: str, show_support_contact: bool = False
    ) -> list[dict[str, Any]]:
        """
        Build an error message block.

        Args:
            error_message: The error message to display
            show_support_contact: Whether to show support contact information

        Returns:
            List of Slack blocks
        """
        blocks = [
            {"type": "header", "text": {"type": "plain_text", "text": "⚠️ Error", "emoji": True}},
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*Error Details:*\n{error_message}"},
            },
        ]

        if show_support_contact:
            blocks.append(
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "_If this issue persists, please contact support._",
                    },
                }
            )

        return blocks

    def build_progress_message(
        self, status_text: str, progress_percentage: int | None = None
    ) -> list[dict[str, Any]]:
        """
        Build a progress update message block.

        Args:
            status_text: The status message to display
            progress_percentage: Optional progress percentage (0-100)

        Returns:
            List of Slack blocks
        """
        blocks = [{"type": "section", "text": {"type": "mrkdwn", "text": f"⏳ *{status_text}*"}}]

        if progress_percentage is not None:
            # Create a simple progress bar using emoji
            filled = int(progress_percentage / 10)
            empty = 10 - filled
            progress_bar = "🟩" * filled + "⬜" * empty

            blocks.append(
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": f"{progress_bar} {progress_percentage}%"},
                }
            )

        return blocks

    def build_analysis_result(
        self,
        analysis: dict[str, Any],
        advice: dict[str, Any] | None = None,
        cost_usd: float = 0.0,
    ) -> list[dict[str, Any]]:
        """
        Build an analysis result message block.

        Args:
            analysis: Dictionary containing analysis results
            advice: Optional advice or recommendations
            cost_usd: Cost of the analysis in USD

        Returns:
            List of Slack blocks
        """
        blocks = [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": "✅ Analysis Complete", "emoji": True},
            }
        ]

        # Add analysis summary
        if "summary" in analysis:
            blocks.append(
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": f"*Summary:*\n{analysis['summary']}"},
                }
            )

        # Add key insights
        if "insights" in analysis and isinstance(analysis["insights"], list):
            insights_text = "\n".join([f"• {insight}" for insight in analysis["insights"]])
            blocks.append(
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": f"*Key Insights:*\n{insights_text}"},
                }
            )

        # Add competency scores if available
        if "competencies" in analysis and isinstance(analysis["competencies"], dict):
            comp_text = "\n".join(
                [f"• *{name}:* {score}/10" for name, score in analysis["competencies"].items()]
            )
            blocks.append(
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": f"*Competency Scores:*\n{comp_text}"},
                }
            )

        # Add advice if provided
        if advice:
            advice_text = advice.get("text", str(advice))
            blocks.extend(
                [
                    {"type": "divider"},
                    {
                        "type": "section",
                        "text": {"type": "mrkdwn", "text": f"*💡 Recommendations:*\n{advice_text}"},
                    },
                ]
            )

        # Add cost information if non-zero
        if cost_usd > 0:
            blocks.append(
                {
                    "type": "context",
                    "elements": [
                        {"type": "mrkdwn", "text": f"_Analysis cost: ${cost_usd:.3f} USD_"}
                    ],
                }
            )

        return blocks

    def build_generic_result(
        self, result: dict[str, Any], title: str = "Result"
    ) -> list[dict[str, Any]]:
        """
        Build a generic result message block.

        Args:
            result: Dictionary containing result data
            title: Title for the result block

        Returns:
            List of Slack blocks
        """
        blocks = [
            {"type": "header", "text": {"type": "plain_text", "text": f"📊 {title}", "emoji": True}}
        ]

        # Add status if available
        if "status" in result:
            status_emoji = "✅" if result["status"] == "success" else "⚠️"
            blocks.append(
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"{status_emoji} *Status:* {result['status']}",
                    },
                }
            )

        # Add message if available
        if "message" in result:
            blocks.append(
                {"type": "section", "text": {"type": "mrkdwn", "text": result["message"]}}
            )

        # Add data section if available
        if "data" in result and isinstance(result["data"], dict):
            data_lines = []
            for key, value in result["data"].items():
                # Format key: remove underscores, capitalize
                formatted_key = key.replace("_", " ").title()
                data_lines.append(f"• *{formatted_key}:* {value}")

            if data_lines:
                blocks.append(
                    {"type": "section", "text": {"type": "mrkdwn", "text": "\n".join(data_lines)}}
                )

        # Add timestamp if available
        if "timestamp" in result:
            blocks.append(
                {
                    "type": "context",
                    "elements": [
                        {"type": "mrkdwn", "text": f"_Generated at: {result['timestamp']}_"}
                    ],
                }
            )

        return blocks

    def build_workflow_status_message(
        self, workflow_id: str, status: str, message: str | None = None
    ) -> list[dict[str, Any]]:
        """
        Build a workflow status message block.

        Args:
            workflow_id: The workflow ID
            status: Current workflow status
            message: Optional status message

        Returns:
            List of Slack blocks
        """
        status_emoji = {"RUNNING": "⏳", "COMPLETED": "✅", "FAILED": "❌", "CANCELLED": "🚫"}.get(
            status, "ℹ️"
        )

        blocks = [
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"{status_emoji} *Workflow Status:* {status}"},
            }
        ]

        if message:
            blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": message}})

        blocks.append(
            {
                "type": "context",
                "elements": [{"type": "mrkdwn", "text": f"_Workflow ID: {workflow_id}_"}],
            }
        )

        return blocks

    def build_welcome_message(self, user_name: str | None = None) -> list[dict[str, Any]]:
        """
        Build a welcome message block.

        Args:
            user_name: Optional user name for personalization

        Returns:
            List of Slack blocks
        """
        greeting = f"👋 Welcome{f', {user_name}' if user_name else ''}!"

        return [
            {"type": "header", "text": {"type": "plain_text", "text": greeting, "emoji": True}},
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "I'm ReflectAI, your competency development assistant. I can help you:\n\n"
                    "• 📊 Analyze your activities and skills\n"
                    "• 🎯 Assess your competencies\n"
                    "• 💡 Provide personalized career advice\n"
                    "• 📈 Generate development reports",
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*Get started by:*\n"
                    "• Asking me to analyze your recent work\n"
                    "• Requesting a competency assessment\n"
                    "• Asking for career development advice",
                },
            },
        ]
