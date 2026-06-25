"""
Mode-Agnostic Slack Adapter for ReflectAI

Implements Requirements 12 & 16: Seamless Socket Mode and HTTP Mode integration
with identical event processing logic and configuration-based mode switching.
"""

import asyncio
import os
from collections.abc import Callable
from enum import Enum
from typing import Any

# Optional Slack SDK imports with fallbacks
try:
    from slack_bolt import App
    from slack_bolt.adapter.socket_mode import SocketModeHandler
    from slack_sdk import WebClient
    from slack_sdk.socket_mode import SocketModeClient

    SLACK_SDK_AVAILABLE = True
except ImportError:
    SLACK_SDK_AVAILABLE = False

    # Mock classes for when Slack SDK is not available
    class App:
        def __init__(self, **kwargs):
            self.client = None

    class SocketModeHandler:
        def __init__(self, app, client):
            pass

        def start(self):
            pass

    class WebClient:
        def __init__(self, token):
            pass

    class SocketModeClient:
        def __init__(self, app_token):
            pass


from src.infrastructure.config import get_secrets_manager
from src.shared import ErrorCategory, ErrorSeverity, ReflectAIError, get_logger

logger = get_logger(__name__)


class SlackMode(str, Enum):
    """Slack connection modes."""

    SOCKET = "socket"
    HTTP = "http"


class SlackAdapter:
    """
    Unified Slack adapter that works identically in Socket Mode and HTTP Mode.

    Features:
    - Configuration-based mode switching
    - Identical event handler registration
    - Automatic authentication handling
    - Health monitoring for both modes
    """

    def __init__(self, mode: SlackMode | None = None):
        self.mode = mode or self._detect_mode()
        self.app: App | None = None
        self.handler: SocketModeHandler | None = None
        self.client: WebClient | None = None
        self._initialized = False

        logger.info(
            "Initializing Slack adapter",
            extra={"mode": self.mode.value, "sdk_available": SLACK_SDK_AVAILABLE},
        )

    def _detect_mode(self) -> SlackMode:
        """Auto-detect Slack mode from environment."""
        # Socket mode requires APP_TOKEN, HTTP mode uses SIGNING_SECRET
        secrets_manager = get_secrets_manager()

        app_token = secrets_manager.get_secret("SLACK_APP_TOKEN")
        signing_secret = secrets_manager.get_secret("SLACK_SIGNING_SECRET")

        if app_token:
            logger.info("Detected Socket Mode (SLACK_APP_TOKEN present)")
            return SlackMode.SOCKET
        elif signing_secret:
            logger.info("Detected HTTP Mode (SLACK_SIGNING_SECRET present)")
            return SlackMode.HTTP
        else:
            logger.warning("No Slack credentials found, defaulting to Socket Mode")
            return SlackMode.SOCKET

    async def initialize(self) -> bool:
        """Initialize Slack app with appropriate authentication for the detected mode."""
        if self._initialized:
            return True

        if not SLACK_SDK_AVAILABLE:
            logger.warning("Slack SDK not available - using mock mode for testing")
            self._initialized = True
            return True

        try:
            secrets_manager = get_secrets_manager()

            if self.mode == SlackMode.SOCKET:
                await self._initialize_socket_mode(secrets_manager)
            else:
                await self._initialize_http_mode(secrets_manager)

            self._initialized = True
            logger.info(f"Slack adapter initialized successfully in {self.mode.value} mode")
            return True

        except Exception as e:
            logger.error(
                "Failed to initialize Slack adapter",
                extra={"mode": self.mode.value, "error": str(e)},
                exc_info=True,
            )
            raise ReflectAIError(
                message=f"Slack adapter initialization failed in {self.mode.value} mode: {str(e)}",
                error_code="SLACK_INIT_FAILED",
                category=ErrorCategory.SLACK_API_ERROR,
                severity=ErrorSeverity.CRITICAL,
                context={"mode": self.mode.value},
                recovery_suggestions=[
                    "Check Slack credentials in secrets manager",
                    "Verify network connectivity to Slack",
                    "Check Slack app configuration",
                ],
                cause=e,
            ) from e

    async def _initialize_socket_mode(self, secrets_manager):
        """Initialize for Socket Mode."""
        bot_token = secrets_manager.get_secret("SLACK_BOT_TOKEN", required=True)
        app_token = secrets_manager.get_secret("SLACK_APP_TOKEN", required=True)

        # Create Slack app for Socket Mode
        self.app = App(
            token=bot_token,
            # Socket mode doesn't need signing secret
            process_before_response=True,
        )

        # Create Socket Mode handler
        socket_client = SocketModeClient(app_token=app_token)
        self.handler = SocketModeHandler(self.app, socket_client)
        self.client = self.app.client

        logger.info("Socket Mode initialized successfully")

    async def _initialize_http_mode(self, secrets_manager):
        """Initialize for HTTP Mode."""
        bot_token = secrets_manager.get_secret("SLACK_BOT_TOKEN", required=True)
        signing_secret = secrets_manager.get_secret("SLACK_SIGNING_SECRET", required=True)

        # Create Slack app for HTTP Mode
        self.app = App(token=bot_token, signing_secret=signing_secret, process_before_response=True)

        self.client = self.app.client

        logger.info("HTTP Mode initialized successfully")

    def register_event_handler(self, event_type: str, handler: Callable):
        """Register event handler (works for both modes)."""
        if not self.app:
            raise ReflectAIError(
                message="Slack app not initialized",
                error_code="SLACK_NOT_INITIALIZED",
                category=ErrorCategory.SLACK_API_ERROR,
                severity=ErrorSeverity.ERROR,
            )

        self.app.event(event_type)(handler)
        logger.debug(f"Registered event handler for {event_type}")

    def register_command_handler(self, command: str, handler: Callable):
        """Register slash command handler (works for both modes)."""
        if not self.app:
            raise ReflectAIError(
                message="Slack app not initialized",
                error_code="SLACK_NOT_INITIALIZED",
                category=ErrorCategory.SLACK_API_ERROR,
                severity=ErrorSeverity.ERROR,
            )

        self.app.command(command)(handler)
        logger.debug(f"Registered command handler for {command}")

    def register_home_tab_handler(self, handler: Callable):
        """Register Home tab handler (works for both modes)."""
        if not self.app:
            raise ReflectAIError(
                message="Slack app not initialized",
                error_code="SLACK_NOT_INITIALIZED",
                category=ErrorCategory.SLACK_API_ERROR,
                severity=ErrorSeverity.ERROR,
            )

        self.app.event("app_home_opened")(handler)
        logger.debug("Registered Home tab handler")

    async def _api_call_with_retry(self, method_name: str, max_retries: int = 1, **kwargs) -> Any:
        """
        Execute Slack API call with simple retry on rate limit.

        Handles rate limit (429) errors with one retry using Retry-After header.
        For more complex scenarios, upgrade to full rate limiting wrapper.

        Args:
            method_name: API method name (e.g., 'chat_postMessage')
            max_retries: Number of retries on rate limit (default: 1)
            **kwargs: Arguments passed to the API method

        Returns:
            API method result

        Raises:
            SlackApiError: If retry fails or non-retriable error
            ReflectAIError: If client not initialized
        """
        from slack_sdk.errors import SlackApiError

        if not self.client:
            raise ReflectAIError(
                message="Slack client not initialized",
                error_code="SLACK_NOT_INITIALIZED",
                category=ErrorCategory.SLACK_API_ERROR,
                severity=ErrorSeverity.ERROR,
            )

        method = getattr(self.client, method_name)
        last_error = None

        for attempt in range(max_retries + 1):
            try:
                result = await method(**kwargs)

                # Log successful retry
                if attempt > 0:
                    logger.info(
                        f"Slack API call succeeded after {attempt} retry(s)",
                        extra={
                            "method": method_name,
                            "attempt": attempt,
                            "channel": kwargs.get("channel"),
                        },
                    )

                return result

            except SlackApiError as e:
                last_error = e

                # Only retry rate limit errors
                if e.response.get("error") == "rate_limited":
                    if attempt >= max_retries:
                        logger.error(
                            f"Rate limit retry exhausted for {method_name}",
                            extra={
                                "method": method_name,
                                "channel": kwargs.get("channel"),
                                "attempt": attempt,
                            },
                        )
                        raise

                    # Use Retry-After header if present, otherwise 1 second
                    retry_after = e.response.get("retry_after", 1)

                    logger.warning(
                        f"Rate limited by Slack API, retrying after {retry_after}s",
                        extra={
                            "method": method_name,
                            "retry_after": retry_after,
                            "channel": kwargs.get("channel"),
                            "attempt": attempt + 1,
                        },
                    )

                    await asyncio.sleep(float(retry_after))
                    continue

                else:
                    # Non-retriable error, fail immediately
                    logger.error(
                        f"Non-retriable Slack API error: {e.response.get('error')}",
                        extra={
                            "method": method_name,
                            "error": e.response.get("error"),
                            "channel": kwargs.get("channel"),
                        },
                    )
                    raise

        # Should not reach here, but just in case
        raise last_error

    async def safe_post_message(self, **kwargs) -> Any:
        """
        Safe chat.postMessage with automatic retry on rate limit.

        Usage:
            await adapter.safe_post_message(channel="C123", text="Hello") from e

        Args:
            **kwargs: Arguments passed to chat_postMessage

        Returns:
            Slack API response
        """
        return await self._api_call_with_retry("chat_postMessage", **kwargs)

    async def safe_update_message(self, **kwargs) -> Any:
        """
        Safe chat.update with automatic retry on rate limit.

        Usage:
            await adapter.safe_update_message(
                channel="C123",
                ts="123.456",
                text="Updated"
            )

        Args:
            **kwargs: Arguments passed to chat_update

        Returns:
            Slack API response
        """
        return await self._api_call_with_retry("chat_update", **kwargs)

    async def upload_file(
        self,
        file_path: str,
        channels: list[str],
        title: str | None = None,
        initial_comment: str | None = None,
    ) -> dict[str, Any]:
        """
        Upload file to Slack channel(s) using files_upload_v2 API.

        Args:
            file_path: Path to file to upload
            channels: List of channel IDs to send file to
            title: Optional file title
            initial_comment: Optional message to include with file

        Returns:
            Dict with file_url, file_id, and success status
        """

        if not self.client:
            raise ReflectAIError(
                message="Slack client not initialized",
                error_code="SLACK_NOT_INITIALIZED",
                category=ErrorCategory.SLACK_API_ERROR,
                severity=ErrorSeverity.ERROR,
            )

        if not os.path.exists(file_path):
            raise ReflectAIError(
                message=f"File not found: {file_path}",
                error_code="FILE_NOT_FOUND",
                category=ErrorCategory.VALIDATION_ERROR,
                severity=ErrorSeverity.ERROR,
            )

        try:
            logger.info(
                "Uploading file to Slack",
                extra={"file_path": file_path, "channels": channels, "title": title},
            )

            # Open and upload file
            with open(file_path, "rb") as file_content:
                response = await self.client.files_upload_v2(
                    channel=",".join(channels) if len(channels) > 1 else channels[0],
                    file=file_content,
                    filename=os.path.basename(file_path),
                    title=title or os.path.basename(file_path),
                    initial_comment=initial_comment,
                )

            if response.get("ok"):
                file_data = response.get("file", {})
                result = {
                    "success": True,
                    "file_url": file_data.get("permalink", ""),
                    "file_id": file_data.get("id", ""),
                    "file_name": file_data.get("name", ""),
                }

                logger.info(
                    "File uploaded successfully",
                    extra={"file_id": result["file_id"], "file_url": result["file_url"]},
                )

                return result
            else:
                error_msg = response.get("error", "Unknown error")
                logger.error(f"File upload failed: {error_msg}")
                raise ReflectAIError(
                    message=f"File upload failed: {error_msg}",
                    error_code="FILE_UPLOAD_FAILED",
                    category=ErrorCategory.SLACK_API_ERROR,
                    severity=ErrorSeverity.ERROR,
                )

        except Exception as e:
            logger.error(
                f"Failed to upload file to Slack: {e}",
                extra={"file_path": file_path, "error": str(e)},
                exc_info=True,
            )

            if isinstance(e, ReflectAIError):
                raise

            raise ReflectAIError(
                message=f"File upload error: {str(e)}",
                error_code="FILE_UPLOAD_ERROR",
                category=ErrorCategory.SLACK_API_ERROR,
                severity=ErrorSeverity.ERROR,
                cause=e,
            ) from e

    async def start(self):
        """Start the Slack adapter (mode-specific)."""
        if not self._initialized:
            await self.initialize()

        if not SLACK_SDK_AVAILABLE:
            logger.info("Slack SDK not available - running in mock mode")
            return

        try:
            if self.mode == SlackMode.SOCKET:
                logger.info("Starting Socket Mode handler")
                self.handler.start()
            else:
                logger.info("HTTP Mode ready - listening for webhooks")
                # HTTP mode starts when web server starts

        except Exception as e:
            logger.error("Failed to start Slack adapter", extra={"error": str(e)}, exc_info=True)
            raise

    async def stop(self):
        """Stop the Slack adapter gracefully."""
        logger.info(f"Stopping Slack adapter ({self.mode.value} mode)")

        if self.handler and hasattr(self.handler, "close"):
            self.handler.close()

        self._initialized = False
        logger.info("Slack adapter stopped")

    def get_health_status(self) -> dict[str, Any]:
        """Get health status of Slack integration."""
        return {
            "mode": self.mode.value,
            "initialized": self._initialized,
            "sdk_available": SLACK_SDK_AVAILABLE,
            "app_configured": self.app is not None,
            "client_ready": self.client is not None,
            "handler_ready": self.handler is not None if self.mode == SlackMode.SOCKET else True,
        }


# Singleton instance
_slack_adapter_instance: SlackAdapter | None = None


async def get_slack_adapter() -> SlackAdapter:
    """Get or create singleton Slack adapter instance."""
    global _slack_adapter_instance

    if _slack_adapter_instance is None:
        _slack_adapter_instance = SlackAdapter()
        await _slack_adapter_instance.initialize()
        logger.info("Slack adapter singleton initialized")

    return _slack_adapter_instance
