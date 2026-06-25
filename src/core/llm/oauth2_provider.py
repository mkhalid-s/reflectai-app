"""
OAuth 2.0 Provider Authentication for LLM Gateway

Implements OAuth 2.0 authentication for LLM providers that require it,
supporting various flows including client credentials, authorization code,
and JWT bearer token authentication.

Supported providers:
- Azure OpenAI (Client Credentials Flow)
- Google Cloud AI (Service Account JWT)
- Anthropic Claude (API Key + Bearer Token)
- AWS Bedrock (AWS SigV4 + IAM Roles)
- Custom providers with OAuth 2.0 endpoints
"""

import json
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any

try:
    import httpx
    import jwt

    OAUTH_DEPENDENCIES_AVAILABLE = True
except ImportError:
    OAUTH_DEPENDENCIES_AVAILABLE = False
    httpx = None
    jwt = None

from src.infrastructure.cache.redis_manager import get_redis_manager
from src.infrastructure.config import get_secrets_manager
from src.shared import ErrorCategory, ErrorSeverity, ReflectAIError, get_logger

logger = get_logger(__name__)


class OAuth2FlowType(str, Enum):
    """OAuth 2.0 flow types supported."""

    CLIENT_CREDENTIALS = "client_credentials"
    AUTHORIZATION_CODE = "authorization_code"
    JWT_BEARER = "jwt_bearer"
    SERVICE_ACCOUNT = "service_account"
    API_KEY_BEARER = "api_key_bearer"
    AWS_SIGV4 = "aws_sigv4"


class TokenType(str, Enum):
    """Token types for different providers."""

    BEARER = "Bearer"
    JWT = "JWT"
    BASIC = "Basic"
    AWS4_HMAC_SHA256 = "AWS4-HMAC-SHA256"


@dataclass
class OAuth2Token:
    """OAuth 2.0 token with metadata."""

    access_token: str
    token_type: str = "Bearer"
    expires_in: int = 3600
    refresh_token: str | None = None
    scope: str | None = None
    issued_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def is_expired(self) -> bool:
        """Check if token is expired."""
        expiry_time = self.issued_at + timedelta(seconds=self.expires_in)
        # Add 5 minute buffer for safety
        return datetime.now(UTC) > (expiry_time - timedelta(minutes=5))

    @property
    def expires_at(self) -> datetime:
        """Get token expiration time."""
        return self.issued_at + timedelta(seconds=self.expires_in)


@dataclass
class OAuth2ProviderConfig:
    """OAuth 2.0 provider configuration."""

    provider_name: str
    flow_type: OAuth2FlowType
    client_id: str | None = None
    client_secret: str | None = None
    token_url: str | None = None
    auth_url: str | None = None
    scope: str | None = None
    audience: str | None = None

    # Service account specific
    service_account_key: dict[str, Any] | None = None

    # API Key specific
    api_key: str | None = None
    api_key_header: str = "Authorization"

    # AWS specific
    aws_region: str | None = None
    aws_access_key_id: str | None = None
    aws_secret_access_key: str | None = None
    aws_session_token: str | None = None

    # Additional parameters
    additional_params: dict[str, Any] = field(default_factory=dict)


class OAuth2Provider:
    """
    OAuth 2.0 authentication provider for LLM services.

    Handles various OAuth 2.0 flows and provider-specific authentication
    patterns with token caching and refresh capabilities.
    """

    def __init__(self):
        self.secrets_manager = get_secrets_manager()
        self.redis_manager = get_redis_manager()
        self._token_cache: dict[str, OAuth2Token] = {}
        self._http_client: httpx.AsyncClient | None = None

        # Provider configurations
        self._provider_configs: dict[str, OAuth2ProviderConfig] = {}
        self._initialize_provider_configs()

        if not OAUTH_DEPENDENCIES_AVAILABLE:
            logger.warning(
                "OAuth dependencies not available",
                extra={
                    "missing_packages": ["httpx", "PyJWT"],
                    "install_command": "pip install httpx PyJWT",
                },
            )

        logger.info("OAuth 2.0 provider initialized")

    async def _get_http_client(self):
        """Get or create HTTP client for OAuth requests."""
        if not OAUTH_DEPENDENCIES_AVAILABLE or httpx is None:
            raise ReflectAIError(
                message="OAuth dependencies not available. Install with: pip install httpx PyJWT",
                error_code="OAUTH_DEPENDENCIES_MISSING",
                severity=ErrorSeverity.HIGH,
                category=ErrorCategory.SYSTEM,
            )

        if self._http_client is None:
            self._http_client = httpx.AsyncClient(
                timeout=httpx.Timeout(30.0), headers={"User-Agent": "ReflectAI-OAuth-Client/1.0"}
            )
        return self._http_client

    def _initialize_provider_configs(self):
        """Initialize configurations for supported OAuth providers."""

        # Azure OpenAI (Client Credentials Flow)
        self._provider_configs["azure_openai"] = OAuth2ProviderConfig(
            provider_name="azure_openai",
            flow_type=OAuth2FlowType.CLIENT_CREDENTIALS,
            token_url="https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token",
            scope="https://cognitiveservices.azure.com/.default",
        )

        # Google Cloud AI (Service Account JWT)
        self._provider_configs["google_cloud"] = OAuth2ProviderConfig(
            provider_name="google_cloud",
            flow_type=OAuth2FlowType.SERVICE_ACCOUNT,
            token_url="https://oauth2.googleapis.com/token",
            scope="https://www.googleapis.com/auth/cloud-platform",
        )

        # Anthropic Claude (API Key Bearer)
        self._provider_configs["anthropic"] = OAuth2ProviderConfig(
            provider_name="anthropic",
            flow_type=OAuth2FlowType.API_KEY_BEARER,
            api_key_header="x-api-key",
        )

        # AWS Bedrock (AWS SigV4)
        self._provider_configs["aws_bedrock"] = OAuth2ProviderConfig(
            provider_name="aws_bedrock", flow_type=OAuth2FlowType.AWS_SIGV4, aws_region="us-east-1"
        )

        # OpenAI (API Key Bearer)
        self._provider_configs["openai"] = OAuth2ProviderConfig(
            provider_name="openai",
            flow_type=OAuth2FlowType.API_KEY_BEARER,
            api_key_header="Authorization",
        )

    async def get_authentication_headers(
        self,
        provider_name: str,
        request_url: str | None = None,
        request_method: str = "POST",
        request_body: str | None = None,
    ) -> dict[str, str]:
        """
        Get authentication headers for the specified provider.

        Args:
            provider_name: Name of the LLM provider
            request_url: URL of the request (needed for some auth types)
            request_method: HTTP method (for AWS SigV4)
            request_body: Request body (for AWS SigV4)

        Returns:
            Dictionary of authentication headers
        """
        if provider_name not in self._provider_configs:
            logger.warning(f"Unknown OAuth provider: {provider_name}")
            return {}

        config = self._provider_configs[provider_name]

        try:
            if config.flow_type == OAuth2FlowType.CLIENT_CREDENTIALS:
                return await self._get_client_credentials_headers(config)

            elif config.flow_type == OAuth2FlowType.SERVICE_ACCOUNT:
                return await self._get_service_account_headers(config)

            elif config.flow_type == OAuth2FlowType.API_KEY_BEARER:
                return await self._get_api_key_headers(config)

            elif config.flow_type == OAuth2FlowType.AWS_SIGV4:
                return await self._get_aws_sigv4_headers(
                    config, request_url, request_method, request_body
                )

            else:
                logger.warning(f"Unsupported OAuth flow: {config.flow_type}")
                return {}

        except Exception as e:
            logger.error(
                f"Authentication failed for provider {provider_name}: {e}",
                extra={"provider": provider_name, "flow": config.flow_type.value},
                exc_info=True,
            )
            raise ReflectAIError(
                message=f"Authentication failed for {provider_name}",
                error_code="OAUTH_AUTH_FAILED",
                category=ErrorCategory.AUTHENTICATION_ERROR,
                severity=ErrorSeverity.HIGH,
                context={"provider": provider_name, "flow": config.flow_type.value},
                recovery_suggestions=[
                    "Check provider credentials",
                    "Verify OAuth configuration",
                    "Check network connectivity",
                ],
                cause=e,
            ) from e

    async def _get_client_credentials_headers(self, config: OAuth2ProviderConfig) -> dict[str, str]:
        """Get headers using OAuth 2.0 Client Credentials flow."""
        if not OAUTH_DEPENDENCIES_AVAILABLE:
            raise ReflectAIError(
                message="OAuth dependencies not available",
                error_code="OAUTH_DEPENDENCIES_MISSING",
                category=ErrorCategory.CONFIGURATION_ERROR,
                severity=ErrorSeverity.CRITICAL,
            )

        # Check cache first
        cache_key = f"oauth_token_{config.provider_name}"
        cached_token = await self._get_cached_token(cache_key)

        if cached_token and not cached_token.is_expired:
            return {"Authorization": f"{cached_token.token_type} {cached_token.access_token}"}

        # Get credentials from secrets manager
        client_id = self.secrets_manager.get_secret(
            f"{config.provider_name.upper()}_CLIENT_ID", required=True
        )
        client_secret = self.secrets_manager.get_secret(
            f"{config.provider_name.upper()}_CLIENT_SECRET", required=True
        )

        # Handle Azure-specific token URL
        token_url = config.token_url
        if config.provider_name == "azure_openai":
            tenant_id = self.secrets_manager.get_secret("AZURE_TENANT_ID", required=True)
            token_url = token_url.format(tenant_id=tenant_id)

        # Request access token
        http_client = await self._get_http_client()

        token_data = {
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
            "scope": config.scope,
        }

        response = await http_client.post(
            token_url,
            data=token_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        if response.status_code != 200:
            raise ReflectAIError(
                message=f"Token request failed with status {response.status_code}",
                error_code="OAUTH_TOKEN_REQUEST_FAILED",
                category=ErrorCategory.AUTHENTICATION_ERROR,
                severity=ErrorSeverity.HIGH,
                context={"status_code": response.status_code, "response": response.text},
            )

        token_response = response.json()

        # Create and cache token
        token = OAuth2Token(
            access_token=token_response["access_token"],
            token_type=token_response.get("token_type", "Bearer"),
            expires_in=token_response.get("expires_in", 3600),
            scope=token_response.get("scope"),
        )

        await self._cache_token(cache_key, token)

        return {"Authorization": f"{token.token_type} {token.access_token}"}

    async def _get_service_account_headers(self, config: OAuth2ProviderConfig) -> dict[str, str]:
        """Get headers using Service Account JWT flow (Google Cloud)."""
        if not OAUTH_DEPENDENCIES_AVAILABLE:
            raise ReflectAIError(
                message="OAuth dependencies not available for JWT generation",
                error_code="OAUTH_JWT_DEPENDENCIES_MISSING",
                category=ErrorCategory.CONFIGURATION_ERROR,
                severity=ErrorSeverity.CRITICAL,
            )

        # Check cache first
        cache_key = f"oauth_token_{config.provider_name}"
        cached_token = await self._get_cached_token(cache_key)

        if cached_token and not cached_token.is_expired:
            return {"Authorization": f"Bearer {cached_token.access_token}"}

        # Get service account key from secrets
        service_account_key_json = self.secrets_manager.get_secret(
            "GOOGLE_CLOUD_SERVICE_ACCOUNT_KEY", required=True
        )

        try:
            service_account_key = json.loads(service_account_key_json)
        except json.JSONDecodeError as e:
            raise ReflectAIError(
                message="Invalid service account key JSON",
                error_code="INVALID_SERVICE_ACCOUNT_KEY",
                category=ErrorCategory.CONFIGURATION_ERROR,
                severity=ErrorSeverity.CRITICAL,
                cause=e,
            ) from e

        # Create JWT assertion
        now = int(time.time())
        payload = {
            "iss": service_account_key["client_email"],
            "sub": service_account_key["client_email"],
            "aud": config.token_url,
            "iat": now,
            "exp": now + 3600,
            "scope": config.scope,
        }

        # Sign JWT
        private_key = service_account_key["private_key"]
        assertion = jwt.encode(payload, private_key, algorithm="RS256")

        # Exchange JWT for access token
        http_client = await self._get_http_client()

        token_data = {
            "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
            "assertion": assertion,
        }

        response = await http_client.post(
            config.token_url,
            data=token_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        if response.status_code != 200:
            raise ReflectAIError(
                message=f"JWT token exchange failed with status {response.status_code}",
                error_code="OAUTH_JWT_EXCHANGE_FAILED",
                category=ErrorCategory.AUTHENTICATION_ERROR,
                severity=ErrorSeverity.HIGH,
                context={"status_code": response.status_code, "response": response.text},
            )

        token_response = response.json()

        # Create and cache token
        token = OAuth2Token(
            access_token=token_response["access_token"],
            token_type="Bearer",
            expires_in=token_response.get("expires_in", 3600),
        )

        await self._cache_token(cache_key, token)

        return {"Authorization": f"Bearer {token.access_token}"}

    async def _get_api_key_headers(self, config: OAuth2ProviderConfig) -> dict[str, str]:
        """Get headers using API key authentication."""
        api_key_env_var = f"{config.provider_name.upper()}_API_KEY"
        api_key = self.secrets_manager.get_secret(api_key_env_var, required=True)

        if config.api_key_header == "Authorization":
            return {"Authorization": f"Bearer {api_key}"}
        else:
            return {config.api_key_header: api_key}

    async def _get_aws_sigv4_headers(
        self,
        config: OAuth2ProviderConfig,
        request_url: str | None,
        request_method: str,
        request_body: str | None,
    ) -> dict[str, str]:
        """Get headers using AWS Signature Version 4."""
        # This is a simplified implementation
        # In production, use boto3's SigV4 implementation

        self.secrets_manager.get_secret("AWS_ACCESS_KEY_ID", required=True)
        self.secrets_manager.get_secret("AWS_SECRET_ACCESS_KEY", required=True)
        aws_session_token = self.secrets_manager.get_secret("AWS_SESSION_TOKEN", required=False)

        headers = {"X-Amz-Security-Token": aws_session_token} if aws_session_token else {}

        # In a real implementation, you would:
        # 1. Parse the request URL to get service, region, etc.
        # 2. Create canonical request
        # 3. Create string to sign
        # 4. Calculate signature
        # 5. Create authorization header

        # For now, return basic headers
        # This should be replaced with proper AWS SigV4 implementation
        logger.warning(
            "AWS SigV4 implementation is simplified. Use boto3 for production.",
            extra={"provider": config.provider_name},
        )

        return headers

    async def _get_cached_token(self, cache_key: str) -> OAuth2Token | None:
        """Get token from cache."""
        try:
            if cache_key in self._token_cache:
                return self._token_cache[cache_key]

            # Check Redis cache if available
            cached_data = await self.redis_manager.get("llm", cache_key)

            if cached_data:
                return OAuth2Token(
                    access_token=cached_data["access_token"],
                    token_type=cached_data.get("token_type", "Bearer"),
                    expires_in=cached_data.get("expires_in", 3600),
                    refresh_token=cached_data.get("refresh_token"),
                    scope=cached_data.get("scope"),
                    issued_at=datetime.fromisoformat(cached_data["issued_at"]),
                )
        except Exception as e:
            logger.warning(f"Failed to get cached token: {e}")

        return None

    async def _cache_token(self, cache_key: str, token: OAuth2Token):
        """Cache token for reuse."""
        try:
            # Store in memory cache
            self._token_cache[cache_key] = token

            # Store in Redis cache if available
            token_data = {
                "access_token": token.access_token,
                "token_type": token.token_type,
                "expires_in": token.expires_in,
                "refresh_token": token.refresh_token,
                "scope": token.scope,
                "issued_at": token.issued_at.isoformat(),
            }

            # Cache for slightly less than token expiry
            ttl = max(token.expires_in - 300, 60)  # At least 1 minute, 5 min buffer
            await self.redis_manager.set("llm", cache_key, token_data, ttl_override=ttl)

            logger.debug(f"Token cached for {cache_key} with TTL {ttl}s")

        except Exception as e:
            logger.warning(f"Failed to cache token: {e}")

    def register_custom_provider(self, provider_name: str, config: OAuth2ProviderConfig):
        """Register a custom OAuth provider configuration."""
        self._provider_configs[provider_name] = config
        logger.info(f"Registered custom OAuth provider: {provider_name}")

    def get_supported_providers(self) -> list[str]:
        """Get list of supported OAuth providers."""
        return list(self._provider_configs.keys())

    async def health_check(self) -> dict[str, Any]:
        """Check OAuth provider health."""
        health_status = {
            "oauth_enabled": OAUTH_DEPENDENCIES_AVAILABLE,
            "supported_providers": self.get_supported_providers(),
            "cached_tokens": len(self._token_cache),
            "provider_configs": len(self._provider_configs),
        }

        if not OAUTH_DEPENDENCIES_AVAILABLE:
            health_status["status"] = "degraded"
            health_status["missing_dependencies"] = ["httpx", "PyJWT"]
        else:
            health_status["status"] = "healthy"

        return health_status

    async def cleanup(self):
        """Clean up resources."""
        if self._http_client:
            await self._http_client.aclose()

        self._token_cache.clear()
        logger.info("OAuth provider cleaned up")


# Global OAuth provider instance
_oauth_provider: OAuth2Provider | None = None


async def get_oauth_provider() -> OAuth2Provider:
    """Get or create global OAuth provider instance."""
    global _oauth_provider
    if _oauth_provider is None:
        _oauth_provider = OAuth2Provider()
    return _oauth_provider


async def get_llm_auth_headers(
    provider_name: str,
    request_url: str | None = None,
    request_method: str = "POST",
    request_body: str | None = None,
) -> dict[str, str]:
    """
    Convenience function to get authentication headers for LLM providers.

    Args:
        provider_name: Name of the LLM provider
        request_url: URL of the request (needed for some auth types)
        request_method: HTTP method
        request_body: Request body

    Returns:
        Dictionary of authentication headers
    """
    oauth_provider = await get_oauth_provider()
    return await oauth_provider.get_authentication_headers(
        provider_name=provider_name,
        request_url=request_url,
        request_method=request_method,
        request_body=request_body,
    )


async def register_custom_oauth_provider(
    provider_name: str, flow_type: OAuth2FlowType, **kwargs
) -> None:
    """
    Register a custom OAuth provider.

    Args:
        provider_name: Name of the provider
        flow_type: OAuth flow type
        **kwargs: Additional configuration parameters
    """
    config = OAuth2ProviderConfig(provider_name=provider_name, flow_type=flow_type, **kwargs)

    oauth_provider = await get_oauth_provider()
    oauth_provider.register_custom_provider(provider_name, config)
