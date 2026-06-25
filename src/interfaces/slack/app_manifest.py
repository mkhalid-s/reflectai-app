"""
Slack App Manifest Generator for ReflectAI

Implements  Slack App Configuration with required scopes and event subscriptions.
Generates and manages Slack app manifests for different environments and deployment modes.
"""

import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from src.infrastructure.config import get_config_manager, get_secrets_manager
from src.shared import get_logger

logger = get_logger(__name__)


class SlackEnvironment(str, Enum):
    """Slack deployment environments."""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


@dataclass
class SlackManifestConfig:
    """Configuration for Slack app manifest."""

    app_name: str = "ReflectAI"
    description: str = "AI-powered competency analysis and career development assistant"
    environment: SlackEnvironment = SlackEnvironment.DEVELOPMENT

    # OAuth settings
    redirect_urls: list[str] = field(default_factory=list)
    request_url: str | None = None
    event_request_url: str | None = None
    interactive_request_url: str | None = None

    # App settings
    always_online: bool = True
    token_rotation_enabled: bool = True

    # Customization
    background_color: str = "#2c3e50"
    long_description: str = """
ReflectAI is an intelligent career development assistant that analyzes your work activities
and provides personalized insights for professional growth. Get competency assessments,
career recommendations, and actionable development plans - all through Slack.

Key Features:
• Automatic activity analysis and competency scoring
• Personalized career development recommendations
• Weekly progress reports and insights
• Proactive coaching and guidance
• Privacy-first approach with secure data handling

Transform your career growth with AI-powered insights, delivered seamlessly in Slack.
    """.strip()

    def get_app_name_for_env(self) -> str:
        """Get environment-specific app name."""
        if self.environment == SlackEnvironment.PRODUCTION:
            return self.app_name
        else:
            return f"{self.app_name} ({self.environment.value.title()})"


class SlackManifestGenerator:
    """
    Generates Slack app manifests with appropriate scopes and configurations.

    Features:
    - Environment-specific configurations
    - Required scopes for ReflectAI functionality
    - Event subscriptions for all relevant Slack events
    - Slash command definitions
    - Interactive component settings
    """

    def __init__(self, config: SlackManifestConfig | None = None):
        self.config = config or SlackManifestConfig()
        self.secrets_manager = get_secrets_manager()
        self.app_config = get_config_manager().get_config()

        logger.info(
            "Slack manifest generator initialized",
            extra={"environment": self.config.environment.value},
        )

    def generate_manifest(self) -> dict[str, Any]:
        """
        Generate complete Slack app manifest.

        Returns:
            Dictionary containing the complete Slack app manifest
        """
        manifest = {
            "display_information": self._generate_display_information(),
            "features": self._generate_features(),
            "oauth_config": self._generate_oauth_config(),
            "settings": self._generate_settings(),
        }

        # Add environment-specific configurations
        if self.config.environment != SlackEnvironment.PRODUCTION:
            manifest["display_information"]["name"] += f" ({self.config.environment.value.title()})"

        logger.info(
            "Slack manifest generated",
            extra={
                "app_name": manifest["display_information"]["name"],
                "scopes_count": len(manifest["oauth_config"]["scopes"]["bot"]),
                "events_count": len(manifest["features"]["bot_user"]["event_mentions"]),
            },
        )

        return manifest

    def _generate_display_information(self) -> dict[str, Any]:
        """Generate display information section."""
        return {
            "name": self.config.get_app_name_for_env(),
            "description": self.config.description,
            "background_color": self.config.background_color,
            "long_description": self.config.long_description,
        }

    def _generate_features(self) -> dict[str, Any]:
        """Generate features section with bot user, home tab, and slash commands."""
        return {
            "app_home": {
                "home_tab_enabled": True,
                "messages_tab_enabled": True,
                "messages_tab_read_only_enabled": False,
            },
            "bot_user": {
                "display_name": self.config.get_app_name_for_env(),
                "always_online": self.config.always_online,
                "event_mentions": self._get_event_subscriptions(),
            },
            "slash_commands": self._generate_slash_commands(),
            "unfurl_domains": [],  # No URL unfurling needed for ReflectAI
            "shortcuts": [],  # Shortcuts can be added later if needed
        }

    def _generate_oauth_config(self) -> dict[str, Any]:
        """Generate OAuth configuration with required scopes."""
        base_url = self._get_base_url()

        return {
            "redirect_urls": self.config.redirect_urls or [f"{base_url}/slack/oauth/callback"],
            "scopes": {
                "bot": self._get_bot_scopes(),
                "user": [],  # Bot-only implementation as per specification
            },
            "token_rotation_enabled": self.config.token_rotation_enabled,
        }

    def _generate_settings(self) -> dict[str, Any]:
        """Generate settings section with event subscriptions and interactivity."""
        base_url = self._get_base_url()

        settings = {
            "event_subscriptions": {
                "request_url": self.config.event_request_url or f"{base_url}/slack/events",
                "bot_events": self._get_event_subscriptions(),
            },
            "interactivity": {
                "is_enabled": True,
                "request_url": self.config.interactive_request_url
                or f"{base_url}/slack/interactive",
            },
            "org_deploy_enabled": False,
            "socket_mode_enabled": self._is_socket_mode_enabled(),
            "token_rotation_enabled": self.config.token_rotation_enabled,
        }

        return settings

    def _get_bot_scopes(self) -> list[str]:
        """
        Get required bot scopes for ReflectAI functionality.

        Scopes based on
        - chat:write: Send messages and responses
        - app_mentions:read: Respond to @mentions
        - im:history: Read direct message history for context
        - channels:history: Read channel message history for analysis
        - app_configurations:write: Update app configuration (admin)
        """
        return [
            # Core messaging capabilities
            "chat:write",
            "chat:write.public",
            # Event listening
            "app_mentions:read",
            "channels:history",
            "groups:history",
            "im:history",
            "mpim:history",
            # User and workspace information
            "users:read",
            "users:read.email",
            "team:read",
            # App Home and interactions
            "im:write",
            "app_home:write",
            # Slash commands
            "commands",
            # File access for potential report sharing
            "files:write",
            # Additional scopes for comprehensive functionality
            "channels:read",
            "groups:read",
            "mpim:read",
            "im:read",
            # Admin capabilities (for configuration updates)
            "app_configurations:write",
        ]

    def _get_event_subscriptions(self) -> list[str]:
        """
        Get event subscriptions for all relevant Slack events.

        Events based on
        - message.channels, message.groups, message.im, message.mpim
        - app_mention, app_home_opened, team_join
        """
        return [
            # Message events for activity analysis
            "message.channels",
            "message.groups",
            "message.im",
            "message.mpim",
            # Mention events for direct interaction
            "app_mention",
            # Home tab events
            "app_home_opened",
            # User lifecycle events
            "team_join",
            "user_change",
            # Additional useful events
            "app_uninstalled",
            "tokens_revoked",
        ]

    def _generate_slash_commands(self) -> list[dict[str, Any]]:
        """
        Generate slash command definitions.

        Commands based on
        - /reflect, /analyze, /help, /report
        """
        base_url = self._get_base_url()

        commands = [
            {
                "command": "/reflect",
                "description": "Start a competency analysis conversation",
                "usage_hint": "[time period] [competency area]",
                "should_escape": False,
                "url": f"{base_url}/slack/commands/reflect",
            },
            {
                "command": "/analyze",
                "description": "Request detailed analysis of your recent activities",
                "usage_hint": "[days] [focus area]",
                "should_escape": False,
                "url": f"{base_url}/slack/commands/analyze",
            },
            {
                "command": "/report",
                "description": "Generate and download your competency report",
                "usage_hint": "[format] [time period]",
                "should_escape": False,
                "url": f"{base_url}/slack/commands/report",
            },
            {
                "command": "/help",
                "description": "Get help and learn about ReflectAI features",
                "usage_hint": "[topic]",
                "should_escape": False,
                "url": f"{base_url}/slack/commands/help",
            },
        ]

        # Add development-specific commands for non-production environments
        if self.config.environment != SlackEnvironment.PRODUCTION:
            commands.extend(
                [
                    {
                        "command": "/debug",
                        "description": "Debug information and diagnostics (dev only)",
                        "usage_hint": "[component]",
                        "should_escape": False,
                        "url": f"{base_url}/slack/commands/debug",
                    },
                    {
                        "command": "/status",
                        "description": "Check system status and health (dev only)",
                        "usage_hint": "",
                        "should_escape": False,
                        "url": f"{base_url}/slack/commands/status",
                    },
                ]
            )

        return commands

    def _get_base_url(self) -> str:
        """Get base URL for the application."""
        # Try to get from configuration or secrets
        base_url = self.secrets_manager.get_secret("SLACK_APP_BASE_URL")

        if not base_url:
            # Fallback based on environment
            if self.config.environment == SlackEnvironment.PRODUCTION:
                base_url = "https://api.reflectai.app"
            elif self.config.environment == SlackEnvironment.STAGING:
                base_url = "https://staging-api.reflectai.app"
            else:
                base_url = "https://dev-api.reflectai.app"

        return base_url.rstrip("/")

    def _is_socket_mode_enabled(self) -> bool:
        """Check if Socket Mode should be enabled."""
        # Enable Socket Mode for development, disable for production
        if self.config.environment == SlackEnvironment.DEVELOPMENT:
            return True

        # Check if APP_TOKEN is available (indicates Socket Mode preference)
        app_token = self.secrets_manager.get_secret("SLACK_APP_TOKEN", required=False)
        return bool(app_token)

    def export_manifest_json(self, file_path: str | None = None) -> str:
        """
        Export manifest as JSON file.

        Args:
            file_path: Optional custom file path

        Returns:
            Path to the exported manifest file
        """
        manifest = self.generate_manifest()

        if not file_path:
            env_suffix = (
                f"_{self.config.environment.value}"
                if self.config.environment != SlackEnvironment.PRODUCTION
                else ""
            )
            file_path = f"slack_app_manifest{env_suffix}.json"

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)

        logger.info(f"Slack manifest exported to {file_path}")
        return file_path

    def validate_manifest(self) -> dict[str, Any]:
        """
        Validate the generated manifest.

        Returns:
            Validation results with any issues found
        """
        manifest = self.generate_manifest()
        issues = []
        warnings = []

        # Check required sections
        required_sections = ["display_information", "features", "oauth_config", "settings"]
        for section in required_sections:
            if section not in manifest:
                issues.append(f"Missing required section: {section}")

        # Check scopes
        bot_scopes = manifest.get("oauth_config", {}).get("scopes", {}).get("bot", [])
        required_scopes = ["chat:write", "app_mentions:read", "im:history", "channels:history"]

        for scope in required_scopes:
            if scope not in bot_scopes:
                issues.append(f"Missing required bot scope: {scope}")

        # Check event subscriptions
        bot_events = (
            manifest.get("settings", {}).get("event_subscriptions", {}).get("bot_events", [])
        )
        required_events = ["message.channels", "message.im", "app_mention"]

        for event in required_events:
            if event not in bot_events:
                issues.append(f"Missing required bot event: {event}")

        # Check URLs
        base_url = self._get_base_url()
        if not base_url.startswith("https://"):
            warnings.append("Base URL should use HTTPS for production")

        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
            "scopes_count": len(bot_scopes),
            "events_count": len(bot_events),
            "commands_count": len(manifest.get("features", {}).get("slash_commands", [])),
        }


# Convenience functions
def generate_slack_manifest(
    environment: SlackEnvironment = SlackEnvironment.DEVELOPMENT,
    app_name: str = "ReflectAI",
    **kwargs,
) -> dict[str, Any]:
    """
    Generate Slack app manifest for the specified environment.

    Args:
        environment: Target environment
        app_name: App name
        **kwargs: Additional configuration options

    Returns:
        Complete Slack app manifest
    """
    config = SlackManifestConfig(app_name=app_name, environment=environment, **kwargs)

    generator = SlackManifestGenerator(config)
    return generator.generate_manifest()


def export_slack_manifest(
    environment: SlackEnvironment = SlackEnvironment.DEVELOPMENT,
    file_path: str | None = None,
    **kwargs,
) -> str:
    """
    Export Slack app manifest to JSON file.

    Args:
        environment: Target environment
        file_path: Optional custom file path
        **kwargs: Additional configuration options

    Returns:
        Path to exported file
    """
    config = SlackManifestConfig(environment=environment, **kwargs)

    generator = SlackManifestGenerator(config)
    return generator.export_manifest_json(file_path)


def validate_slack_manifest(
    environment: SlackEnvironment = SlackEnvironment.DEVELOPMENT, **kwargs
) -> dict[str, Any]:
    """
    Validate Slack app manifest for the specified environment.

    Args:
        environment: Target environment
        **kwargs: Additional configuration options

    Returns:
        Validation results
    """
    config = SlackManifestConfig(environment=environment, **kwargs)

    generator = SlackManifestGenerator(config)
    return generator.validate_manifest()


# Example usage and testing
if __name__ == "__main__":
    # Generate manifest for development
    dev_manifest = generate_slack_manifest(SlackEnvironment.DEVELOPMENT)
    print("Development manifest generated:")
    print(json.dumps(dev_manifest, indent=2))

    # Validate manifest
    validation = validate_slack_manifest(SlackEnvironment.DEVELOPMENT)
    print(f"\nValidation result: {'✅ PASSED' if validation['valid'] else '❌ FAILED'}")

    if validation["issues"]:
        print("Issues found:")
        for issue in validation["issues"]:
            print(f"  - {issue}")

    if validation["warnings"]:
        print("Warnings:")
        for warning in validation["warnings"]:
            print(f"  - {warning}")
