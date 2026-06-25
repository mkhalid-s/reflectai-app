"""
Slack App Factory and Initialization

Provides centralized Slack app creation and management for both Socket Mode
and HTTP Mode, ensuring consistent configuration across the application.
"""

from typing import Any

from slack_bolt.async_app import AsyncApp

from src.infrastructure.config import get_secrets_manager
from src.shared import ErrorCategory, ErrorSeverity, ReflectAIError, get_logger

logger = get_logger(__name__)

# Global singleton instance
_slack_app_instance: AsyncApp | None = None


async def get_slack_app(mode: str | None = None) -> AsyncApp:
    """
    Get or create singleton Slack AsyncApp instance.

    Args:
        mode: Optional mode override ('socket' or 'http').
              If not provided, auto-detects based on available tokens.

    Returns:
        Configured AsyncApp instance

    Raises:
        ReflectAIError: If Slack credentials are not configured
    """
    global _slack_app_instance

    if _slack_app_instance is not None:
        logger.debug("Returning existing Slack app instance")
        return _slack_app_instance

    try:
        # Get Slack secrets
        secrets = get_secrets_manager()
        slack_secrets = secrets.get_slack_secrets()

        # Validate required credentials
        bot_token = slack_secrets.get("bot_token")
        signing_secret = slack_secrets.get("signing_secret")

        if not bot_token:
            raise ReflectAIError(
                message="SLACK_BOT_TOKEN is required but not configured",
                error_code="SLACK_CONFIG_MISSING",
                category=ErrorCategory.CONFIGURATION_ERROR,
                severity=ErrorSeverity.CRITICAL,
                recovery_suggestions=[
                    "Set SLACK_BOT_TOKEN in environment variables",
                    "Check Doppler configuration if using Doppler",
                    "Verify .env file contains SLACK_BOT_TOKEN",
                ],
            )

        if not signing_secret:
            raise ReflectAIError(
                message="SLACK_SIGNING_SECRET is required but not configured",
                error_code="SLACK_CONFIG_MISSING",
                category=ErrorCategory.CONFIGURATION_ERROR,
                severity=ErrorSeverity.CRITICAL,
                recovery_suggestions=[
                    "Set SLACK_SIGNING_SECRET in environment variables",
                    "Check Doppler configuration if using Doppler",
                    "Verify .env file contains SLACK_SIGNING_SECRET",
                ],
            )

        # Auto-detect mode if not provided
        if mode is None:
            app_token = slack_secrets.get("app_token")
            mode = "socket" if app_token else "http"
            logger.info(f"Auto-detected Slack mode: {mode}")

        # Check if OAuth is configured (client_id and client_secret from secrets)
        client_id = slack_secrets.get("client_id")
        client_secret = slack_secrets.get("client_secret")

        # Create AsyncApp with appropriate configuration
        if mode == "socket":
            # Socket Mode configuration (for development/staging)
            if client_id and client_secret:
                # OAuth mode - requires installation flow
                _slack_app_instance = AsyncApp(
                    token=bot_token,
                    signing_secret=signing_secret,
                    process_before_response=True,
                )
                logger.info("Created Slack app in Socket Mode (OAuth enabled)")
            else:
                # Simple bot token mode - disable OAuth auto-detection
                # Setting oauth_settings=None explicitly disables OAuth even if
                # SLACK_CLIENT_ID/SLACK_CLIENT_SECRET env vars exist
                _slack_app_instance = AsyncApp(
                    token=bot_token,
                    signing_secret=signing_secret,
                    process_before_response=True,
                    oauth_settings=None,  # Explicitly disable OAuth
                )
                logger.info("Created Slack app in Socket Mode (simple bot token auth)")

        else:
            # HTTP Mode configuration (for production)
            _slack_app_instance = AsyncApp(
                token=bot_token,
                signing_secret=signing_secret,
                process_before_response=True,
            )
            logger.info("Created Slack app in HTTP Mode")

        return _slack_app_instance

    except ReflectAIError:
        # Re-raise ReflectAIError as-is
        raise

    except Exception as e:
        logger.error(
            f"Failed to create Slack app: {e}",
            exc_info=True,
        )
        raise ReflectAIError(
            message=f"Slack app initialization failed: {str(e)}",
            error_code="SLACK_INIT_FAILED",
            category=ErrorCategory.SLACK_API_ERROR,
            severity=ErrorSeverity.CRITICAL,
            recovery_suggestions=[
                "Check Slack credentials are valid",
                "Verify network connectivity to Slack API",
                "Review application logs for details",
            ],
            cause=e,
        ) from e


def reset_slack_app() -> None:
    """
    Reset the singleton Slack app instance.

    Useful for testing or when credentials change at runtime.
    """
    global _slack_app_instance
    _slack_app_instance = None
    logger.info("Slack app instance reset")


async def get_slack_app_health() -> dict[str, Any]:
    """
    Get health status of Slack app.

    Returns:
        Dictionary with health status information
    """
    global _slack_app_instance

    if _slack_app_instance is None:
        return {
            "status": "not_initialized",
            "initialized": False,
            "error": "Slack app not initialized",
        }

    try:
        # Test authentication
        auth_response = await _slack_app_instance.client.auth_test()

        if auth_response.get("ok"):
            return {
                "status": "healthy",
                "initialized": True,
                "bot_id": auth_response.get("bot_id"),
                "team_id": auth_response.get("team_id"),
                "team_name": auth_response.get("team"),
                "user_id": auth_response.get("user_id"),
            }
        else:
            return {
                "status": "unhealthy",
                "initialized": True,
                "error": auth_response.get("error", "Unknown error"),
            }

    except Exception as e:
        logger.error(f"Slack health check failed: {e}")
        return {
            "status": "unhealthy",
            "initialized": True,
            "error": str(e),
        }
