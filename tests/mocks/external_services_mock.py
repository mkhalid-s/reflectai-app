#!/usr/bin/env python3
"""
External Services Mock Infrastructure for ReflectAI Testing

Provides comprehensive external service mocking including:
- OAuth2/OIDC authentication flows
- Email service simulation
- Webhook delivery simulation
- HTTP client mocking
- Third-party API simulation
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
from unittest.mock import AsyncMock


class AuthProvider(str, Enum):
    """OAuth/OIDC providers for testing."""

    GOOGLE = "google"
    MICROSOFT = "microsoft"
    SLACK = "slack"
    CUSTOM = "custom"


@dataclass
class MockOAuthCredentials:
    """Mock OAuth credentials configuration."""

    client_id: str
    client_secret: str
    redirect_uri: str = "http://localhost:3000/callback"
    scope: list[str] = field(default_factory=lambda: ["openid", "profile", "email"])
    provider: AuthProvider = AuthProvider.CUSTOM


@dataclass
class MockTokenResponse:
    """Mock OAuth token response."""

    access_token: str
    token_type: str = "Bearer"
    expires_in: int = 3600
    refresh_token: str | None = None
    scope: str = "openid profile email"
    provider: AuthProvider = AuthProvider.CUSTOM


@dataclass
class MockEmailMessage:
    """Mock email message configuration."""

    to: list[str]
    subject: str
    body: str
    from_email: str = "noreply@reflectai.com"
    html_body: str | None = None
    attachments: list[dict] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class MockWebhookDelivery:
    """Mock webhook delivery configuration."""

    url: str
    payload: dict[str, Any]
    headers: dict[str, str] = field(default_factory=dict)
    method: str = "POST"
    timeout: float = 30.0
    retry_count: int = 0
    timestamp: datetime = field(default_factory=datetime.now)


class ExternalServiceMock:
    """Comprehensive external service mock."""

    def __init__(self):
        self.oauth_credentials: dict[str, MockOAuthCredentials] = {}
        self.token_history: list[MockTokenResponse] = []
        self.email_history: list[MockEmailMessage] = []
        self.webhook_history: list[MockWebhookDelivery] = []
        self.http_call_history: list[dict] = []

    def create_oauth_mock(self, provider: AuthProvider = AuthProvider.CUSTOM) -> AsyncMock:
        """Create a mock OAuth2/OIDC service."""
        mock_oauth = AsyncMock()

        async def mock_authorize_url(client_id: str, redirect_uri: str, **kwargs):
            return f"https://{provider}.com/oauth/authorize?client_id={client_id}&redirect_uri={redirect_uri}"

        async def mock_exchange_code(code: str, client_id: str, client_secret: str, **kwargs):
            token = f"mock_access_token_{provider.value}_{len(self.token_history)}"
            refresh_token = f"mock_refresh_token_{provider.value}_{len(self.token_history)}"

            token_response = MockTokenResponse(
                access_token=token,
                refresh_token=refresh_token,
                expires_in=3600,
                scope="openid profile email",
                provider=provider,
            )

            self.token_history.append(token_response)

            return {
                "access_token": token,
                "token_type": "Bearer",
                "expires_in": 3600,
                "refresh_token": refresh_token,
                "scope": "openid profile email",
            }

        async def mock_refresh_token(
            refresh_token: str, client_id: str, client_secret: str, **kwargs
        ):
            token = f"refreshed_token_{provider.value}_{len(self.token_history)}"

            token_response = MockTokenResponse(
                access_token=token, expires_in=3600, provider=provider
            )

            self.token_history.append(token_response)

            return {"access_token": token, "token_type": "Bearer", "expires_in": 3600}

        async def mock_get_user_info(access_token: str):
            # Extract provider from token
            provider_name = access_token.split("_")[2] if "_" in access_token else "custom"

            return {
                "sub": f"mock_user_{provider_name}",
                "email": f"user@{provider_name}.com",
                "name": f"Mock User {provider_name.title()}",
                "picture": f"https://{provider_name}.com/avatar.jpg",
                "provider": provider_name,
            }

        # Set up mock methods
        mock_oauth.authorize_url = mock_authorize_url
        mock_oauth.exchange_code = mock_exchange_code
        mock_oauth.refresh_token = mock_refresh_token
        mock_oauth.get_user_info = mock_get_user_info

        return mock_oauth

    def create_email_mock(self, provider: str = "smtp") -> AsyncMock:
        """Create a mock email service."""
        mock_email = AsyncMock()

        async def mock_send_email(to: list[str], subject: str, body: str, **kwargs):
            email_message = MockEmailMessage(
                to=to,
                subject=subject,
                body=body,
                from_email=kwargs.get("from_email", "noreply@reflectai.com"),
                html_body=kwargs.get("html_body"),
                attachments=kwargs.get("attachments", []),
            )

            self.email_history.append(email_message)

            return {
                "message_id": f"msg_{len(self.email_history)}",
                "status": "sent",
                "provider": provider,
                "recipients": to,
            }

        async def mock_send_bulk_email(recipients: list[dict], template: str, **kwargs):
            sent_count = 0
            for recipient in recipients:
                email_message = MockEmailMessage(
                    to=[recipient["email"]],
                    subject=kwargs.get("subject", "Bulk Email"),
                    body=template.format(**recipient),
                    from_email=kwargs.get("from_email", "noreply@reflectai.com"),
                )
                self.email_history.append(email_message)
                sent_count += 1

            return {
                "status": "completed",
                "sent_count": sent_count,
                "total_count": len(recipients),
                "provider": provider,
            }

        # Set up mock methods
        mock_email.send = mock_send_email
        mock_email.send_bulk = mock_send_bulk_email

        return mock_email

    def create_webhook_mock(self, service: str = "generic") -> AsyncMock:
        """Create a mock webhook delivery service."""
        mock_webhook = AsyncMock()

        async def mock_deliver_webhook(url: str, payload: dict, **kwargs):
            webhook_delivery = MockWebhookDelivery(
                url=url,
                payload=payload,
                headers=kwargs.get("headers", {"Content-Type": "application/json"}),
                method=kwargs.get("method", "POST"),
                timeout=kwargs.get("timeout", 30.0),
            )

            self.webhook_history.append(webhook_delivery)

            # Simulate network delay
            await asyncio.sleep(0.1)

            return {
                "status_code": 200,
                "response": "OK",
                "webhook_id": f"wh_{len(self.webhook_history)}",
                "delivered_at": datetime.now().isoformat(),
            }

        async def mock_deliver_bulk_webhooks(webhooks: list[dict], **kwargs):
            delivered = 0
            failed = 0

            for webhook in webhooks:
                try:
                    result = await mock_deliver_webhook(
                        webhook["url"], webhook["payload"], headers=webhook.get("headers", {})
                    )
                    if result["status_code"] == 200:
                        delivered += 1
                    else:
                        failed += 1
                except Exception:
                    failed += 1

            return {
                "status": "completed",
                "delivered": delivered,
                "failed": failed,
                "total": len(webhooks),
            }

        # Set up mock methods
        mock_webhook.deliver = mock_deliver_webhook
        mock_webhook.deliver_bulk = mock_deliver_bulk_webhooks

        return mock_webhook

    def create_http_client_mock(self) -> AsyncMock:
        """Create a mock HTTP client for external API calls."""
        mock_client = AsyncMock()

        async def mock_get(url: str, **kwargs):
            call_record = {
                "method": "GET",
                "url": url,
                "timestamp": datetime.now().isoformat(),
                "kwargs": kwargs,
            }
            self.http_call_history.append(call_record)

            # Simulate different responses based on URL
            if "api.github.com" in url:
                return {"status_code": 200, "json": lambda: {"message": "GitHub API"}}
            elif "api.slack.com" in url:
                return {"status_code": 200, "json": lambda: {"ok": True}}
            else:
                return {"status_code": 200, "json": lambda: {"status": "success"}}

        async def mock_post(url: str, json: dict = None, **kwargs):
            call_record = {
                "method": "POST",
                "url": url,
                "payload": json,
                "timestamp": datetime.now().isoformat(),
                "kwargs": kwargs,
            }
            self.http_call_history.append(call_record)

            return {"status_code": 201, "json": lambda: {"id": "created", "status": "created"}}

        async def mock_put(url: str, json: dict = None, **kwargs):
            call_record = {
                "method": "PUT",
                "url": url,
                "payload": json,
                "timestamp": datetime.now().isoformat(),
                "kwargs": kwargs,
            }
            self.http_call_history.append(call_record)

            return {"status_code": 200, "json": lambda: {"status": "updated"}}

        # Set up mock methods
        mock_client.get = mock_get
        mock_client.post = mock_post
        mock_client.put = mock_put

        return mock_client

    def register_oauth_credentials(self, provider: AuthProvider, credentials: MockOAuthCredentials):
        """Register OAuth credentials for testing."""
        self.oauth_credentials[provider.value] = credentials

    def get_oauth_history(self) -> list[MockTokenResponse]:
        """Get OAuth token exchange history."""
        return self.token_history.copy()

    def get_email_history(self) -> list[MockEmailMessage]:
        """Get email sending history."""
        return self.email_history.copy()

    def get_webhook_history(self) -> list[MockWebhookDelivery]:
        """Get webhook delivery history."""
        return self.webhook_history.copy()

    def get_http_call_history(self) -> list[dict]:
        """Get HTTP client call history."""
        return self.http_call_history.copy()

    def clear_history(self):
        """Clear all service call history."""
        self.token_history.clear()
        self.email_history.clear()
        self.webhook_history.clear()
        self.http_call_history.clear()

    def get_service_stats(self) -> dict[str, int]:
        """Get statistics about service usage."""
        return {
            "oauth_tokens": len(self.token_history),
            "emails_sent": len(self.email_history),
            "webhooks_delivered": len(self.webhook_history),
            "http_calls": len(self.http_call_history),
        }


class MockServiceRegistry:
    """Registry for managing multiple mock services."""

    def __init__(self):
        self.oauth_mocks: dict[AuthProvider, AsyncMock] = {}
        self.email_mocks: dict[str, AsyncMock] = {}
        self.webhook_mocks: dict[str, AsyncMock] = {}
        self.http_client_mock: AsyncMock | None = None

    def get_oauth_mock(self, provider: AuthProvider = AuthProvider.CUSTOM) -> AsyncMock:
        """Get or create OAuth mock for provider."""
        if provider not in self.oauth_mocks:
            self.oauth_mocks[provider] = ExternalServiceMock().create_oauth_mock(provider)
        return self.oauth_mocks[provider]

    def get_email_mock(self, provider: str = "smtp") -> AsyncMock:
        """Get or create email mock for provider."""
        if provider not in self.email_mocks:
            self.email_mocks[provider] = ExternalServiceMock().create_email_mock(provider)
        return self.email_mocks[provider]

    def get_webhook_mock(self, service: str = "generic") -> AsyncMock:
        """Get or create webhook mock for service."""
        if service not in self.webhook_mocks:
            self.webhook_mocks[service] = ExternalServiceMock().create_webhook_mock(service)
        return self.webhook_mocks[service]

    def get_http_client_mock(self) -> AsyncMock:
        """Get HTTP client mock."""
        if self.http_client_mock is None:
            self.http_client_mock = ExternalServiceMock().create_http_client_mock()
        return self.http_client_mock

    def reset_all_mocks(self):
        """Reset all mock services."""
        self.oauth_mocks.clear()
        self.email_mocks.clear()
        self.webhook_mocks.clear()
        self.http_client_mock = None


# Global instances for easy access
external_service_mock = ExternalServiceMock()
service_registry = MockServiceRegistry()


def get_external_service_mock() -> ExternalServiceMock:
    """Get the global external service mock instance."""
    return external_service_mock


def get_service_registry() -> MockServiceRegistry:
    """Get the global service registry."""
    return service_registry


def create_mock_credentials(provider: AuthProvider = AuthProvider.CUSTOM) -> MockOAuthCredentials:
    """Create mock OAuth credentials for testing."""
    return MockOAuthCredentials(
        client_id=f"mock_client_{provider.value}",
        client_secret=f"mock_secret_{provider.value}",
        provider=provider,
    )


def create_mock_email_message(to: list[str], subject: str, body: str) -> MockEmailMessage:
    """Create a mock email message for testing."""
    return MockEmailMessage(to=to, subject=subject, body=body)


def create_mock_webhook(url: str, payload: dict) -> MockWebhookDelivery:
    """Create a mock webhook delivery for testing."""
    return MockWebhookDelivery(url=url, payload=payload)
