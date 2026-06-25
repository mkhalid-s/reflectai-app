# ReflectAI Error Handling Patterns and Standards

## Overview

This document defines comprehensive error handling patterns and standards for the ReflectAI fresh implementation. These patterns ensure consistent error handling across all components, proper error propagation, user-friendly error messages, and effective error recovery strategies.

## Core Error Handling Principles

1. **Fail Fast, Recover Gracefully**: Detect errors early and provide meaningful recovery options
2. **User-Friendly Messages**: Convert technical errors to actionable user guidance
3. **Structured Logging**: All errors logged with structured context for debugging
4. **Error Classification**: Consistent error categorization for proper handling
5. **Graceful Degradation**: System continues operating with reduced functionality when possible
6. **Circuit Breaker Pattern**: Prevent cascade failures in distributed components

## Error Classification System

### Error Severity Levels

```python
from enum import Enum

class ErrorSeverity(str, Enum):
    CRITICAL = "critical"    # System-wide failure, immediate attention required
    ERROR = "error"         # Feature failure, affects user experience
    WARNING = "warning"     # Degraded performance, fallback used
    INFO = "info"          # Expected errors (rate limits, user input)
    DEBUG = "debug"        # Development/troubleshooting information
```

### Error Categories

```python
class ErrorCategory(str, Enum):
    # System Errors
    DATABASE_ERROR = "database_error"
    NETWORK_ERROR = "network_error"
    CONFIGURATION_ERROR = "configuration_error"
    INFRASTRUCTURE_ERROR = "infrastructure_error"
    
    # Integration Errors
    SLACK_API_ERROR = "slack_api_error"
    LLM_PROVIDER_ERROR = "llm_provider_error"
    TEMPORAL_ERROR = "temporal_error"
    EXTERNAL_API_ERROR = "external_api_error"
    
    # Business Logic Errors
    VALIDATION_ERROR = "validation_error"
    AUTHORIZATION_ERROR = "authorization_error"
    BUSINESS_RULE_ERROR = "business_rule_error"
    DATA_INTEGRITY_ERROR = "data_integrity_error"
    
    # User Errors
    INPUT_ERROR = "input_error"
    PERMISSION_ERROR = "permission_error"
    RATE_LIMIT_ERROR = "rate_limit_error"
    RESOURCE_NOT_FOUND = "resource_not_found"
```

## Base Error Classes

### Custom Exception Hierarchy

```python
from typing import Any, Dict, Optional
import uuid
from datetime import datetime

class ReflectAIError(Exception):
    """Base exception class for all ReflectAI errors"""
    
    def __init__(
        self,
        message: str,
        error_code: str,
        category: ErrorCategory,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        context: Optional[Dict[str, Any]] = None,
        user_message: Optional[str] = None,
        recovery_suggestions: Optional[list[str]] = None,
        cause: Optional[Exception] = None
    ):
        super().__init__(message)
        self.error_id = str(uuid.uuid4())
        self.timestamp = datetime.utcnow()
        self.message = message
        self.error_code = error_code
        self.category = category
        self.severity = severity
        self.context = context or {}
        self.user_message = user_message or self._generate_user_message()
        self.recovery_suggestions = recovery_suggestions or []
        self.cause = cause
        
    def _generate_user_message(self) -> str:
        """Generate user-friendly error message based on category"""
        user_messages = {
            ErrorCategory.DATABASE_ERROR: "We're experiencing database issues. Please try again in a few moments.",
            ErrorCategory.SLACK_API_ERROR: "There's an issue connecting to Slack. Your request will be retried automatically.",
            ErrorCategory.LLM_PROVIDER_ERROR: "Our AI analysis service is temporarily unavailable. Please try again shortly.",
            ErrorCategory.VALIDATION_ERROR: "There was an issue with your request. Please check your input and try again.",
            ErrorCategory.RATE_LIMIT_ERROR: "You're sending requests too quickly. Please wait a moment before trying again.",
            ErrorCategory.AUTHORIZATION_ERROR: "You don't have permission to perform this action.",
            ErrorCategory.RESOURCE_NOT_FOUND: "The requested information couldn't be found."
        }
        return user_messages.get(self.category, "An unexpected error occurred. Please try again.")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for logging and serialization"""
        return {
            "error_id": self.error_id,
            "timestamp": self.timestamp.isoformat(),
            "message": self.message,
            "error_code": self.error_code,
            "category": self.category.value,
            "severity": self.severity.value,
            "context": self.context,
            "user_message": self.user_message,
            "recovery_suggestions": self.recovery_suggestions,
            "cause": str(self.cause) if self.cause else None
        }

# Specialized Error Classes
class DatabaseError(ReflectAIError):
    def __init__(self, message: str, query: Optional[str] = None, **kwargs):
        context = kwargs.get('context', {})
        if query:
            context['query'] = query
        kwargs['context'] = context
        super().__init__(
            message=message,
            error_code="DB_ERROR",
            category=ErrorCategory.DATABASE_ERROR,
            severity=ErrorSeverity.ERROR,
            **kwargs
        )

class SlackAPIError(ReflectAIError):
    def __init__(self, message: str, api_method: str, response_code: Optional[int] = None, **kwargs):
        context = kwargs.get('context', {})
        context.update({
            'api_method': api_method,
            'response_code': response_code
        })
        kwargs['context'] = context
        super().__init__(
            message=message,
            error_code="SLACK_API_ERROR",
            category=ErrorCategory.SLACK_API_ERROR,
            severity=ErrorSeverity.WARNING,
            **kwargs
        )

class LLMProviderError(ReflectAIError):
    def __init__(self, message: str, provider: str, model: Optional[str] = None, **kwargs):
        context = kwargs.get('context', {})
        context.update({
            'provider': provider,
            'model': model
        })
        kwargs['context'] = context
        super().__init__(
            message=message,
            error_code="LLM_PROVIDER_ERROR",
            category=ErrorCategory.LLM_PROVIDER_ERROR,
            severity=ErrorSeverity.ERROR,
            **kwargs
        )

class ValidationError(ReflectAIError):
    def __init__(self, message: str, field: Optional[str] = None, value: Any = None, **kwargs):
        context = kwargs.get('context', {})
        context.update({
            'field': field,
            'invalid_value': str(value) if value is not None else None
        })
        kwargs['context'] = context
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            category=ErrorCategory.VALIDATION_ERROR,
            severity=ErrorSeverity.INFO,
            user_message=f"Invalid {field}: {message}" if field else message,
            **kwargs
        )

class TemporalWorkflowError(ReflectAIError):
    def __init__(self, message: str, workflow_id: Optional[str] = None, activity: Optional[str] = None, **kwargs):
        context = kwargs.get('context', {})
        context.update({
            'workflow_id': workflow_id,
            'activity': activity
        })
        kwargs['context'] = context
        super().__init__(
            message=message,
            error_code="TEMPORAL_WORKFLOW_ERROR",
            category=ErrorCategory.TEMPORAL_ERROR,
            severity=ErrorSeverity.ERROR,
            **kwargs
        )
```

## Error Handling Patterns

### 1. Database Error Handling

```python
from contextlib import asynccontextmanager
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from asyncpg.exceptions import PostgreSQLError

@asynccontextmanager
async def database_error_handler(operation_name: str):
    """Context manager for database operations with standardized error handling"""
    try:
        yield
    except IntegrityError as e:
        logger.error(
            "Database integrity constraint violation",
            operation=operation_name,
            error=str(e),
            exc_info=True
        )
        raise DatabaseError(
            message=f"Data integrity error in {operation_name}",
            error_code="DB_INTEGRITY_ERROR",
            context={"operation": operation_name, "constraint": str(e)},
            user_message="There was a conflict with existing data. Please check your input.",
            recovery_suggestions=["Verify the data doesn't already exist", "Check for required fields"],
            cause=e
        )
    except PostgreSQLError as e:
        logger.error(
            "PostgreSQL database error",
            operation=operation_name,
            error=str(e),
            sqlstate=e.sqlstate,
            exc_info=True
        )
        raise DatabaseError(
            message=f"Database error in {operation_name}",
            error_code="DB_CONNECTION_ERROR",
            context={"operation": operation_name, "sqlstate": e.sqlstate},
            recovery_suggestions=["Retry the operation", "Check database connectivity"],
            cause=e
        )
    except SQLAlchemyError as e:
        logger.error(
            "SQLAlchemy error",
            operation=operation_name,
            error=str(e),
            exc_info=True
        )
        raise DatabaseError(
            message=f"Database operation failed: {operation_name}",
            context={"operation": operation_name},
            cause=e
        )

# Usage Example
async def create_user_activity(user_id: str, content: str) -> Activity:
    async with database_error_handler("create_user_activity"):
        activity = Activity(user_id=user_id, content=content)
        session.add(activity)
        await session.commit()
        return activity
```

### 2. External API Error Handling

```python
import asyncio
from typing import TypeVar, Callable, Any
import httpx

T = TypeVar('T')

class CircuitBreaker:
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half_open
    
    async def call(self, func: Callable[..., T], *args, **kwargs) -> T:
        if self.state == "open":
            if self._should_attempt_reset():
                self.state = "half_open"
            else:
                raise ReflectAIError(
                    message="Circuit breaker is open",
                    error_code="CIRCUIT_BREAKER_OPEN",
                    category=ErrorCategory.INFRASTRUCTURE_ERROR,
                    severity=ErrorSeverity.WARNING,
                    user_message="Service is temporarily unavailable. Please try again later."
                )
        
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise
    
    def _should_attempt_reset(self) -> bool:
        return (
            self.last_failure_time and 
            (asyncio.get_event_loop().time() - self.last_failure_time) >= self.recovery_timeout
        )
    
    def _on_success(self):
        self.failure_count = 0
        self.state = "closed"
    
    def _on_failure(self):
        self.failure_count += 1
        self.last_failure_time = asyncio.get_event_loop().time()
        if self.failure_count >= self.failure_threshold:
            self.state = "open"

async def slack_api_call_with_retry(
    method: str,
    url: str,
    circuit_breaker: CircuitBreaker,
    max_retries: int = 3,
    **kwargs
) -> Any:
    """Slack API call with retry logic and circuit breaker"""
    
    async def _make_request():
        async with httpx.AsyncClient() as client:
            response = await client.request(method, url, **kwargs)
            
            if response.status_code == 429:  # Rate limited
                retry_after = int(response.headers.get('Retry-After', 60))
                raise SlackAPIError(
                    message=f"Slack API rate limit exceeded",
                    api_method=method,
                    response_code=429,
                    context={"retry_after": retry_after, "url": url},
                    user_message=f"Please wait {retry_after} seconds before trying again.",
                    recovery_suggestions=[f"Wait {retry_after} seconds and retry"]
                )
            
            if response.status_code >= 400:
                raise SlackAPIError(
                    message=f"Slack API error: {response.text}",
                    api_method=method,
                    response_code=response.status_code,
                    context={"url": url, "response": response.text}
                )
            
            return response.json()
    
    for attempt in range(max_retries + 1):
        try:
            return await circuit_breaker.call(_make_request)
        except SlackAPIError as e:
            if e.context.get('response_code') == 429 and attempt < max_retries:
                # Exponential backoff for rate limits
                wait_time = min(2 ** attempt, 60)
                await asyncio.sleep(wait_time)
                continue
            raise
        except Exception as e:
            if attempt < max_retries:
                wait_time = 2 ** attempt
                await asyncio.sleep(wait_time)
                continue
            raise
```

### 3. LLM Provider Error Handling

```python
from typing import Optional, Dict, Any

class LLMProviderManager:
    def __init__(self):
        self.providers = {
            'claude': {'url': 'https://api.anthropic.com', 'priority': 1},
            'openai': {'url': 'https://api.openai.com', 'priority': 2}
        }
        self.circuit_breakers = {
            provider: CircuitBreaker() for provider in self.providers
        }
    
    async def call_with_fallback(
        self,
        prompt: str,
        preferred_provider: str = 'claude',
        model_params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Call LLM with automatic fallback to alternative providers"""
        
        # Sort providers by priority, preferred first
        sorted_providers = sorted(
            self.providers.items(),
            key=lambda x: (x[0] != preferred_provider, x[1]['priority'])
        )
        
        last_error = None
        
        for provider_name, provider_config in sorted_providers:
            try:
                circuit_breaker = self.circuit_breakers[provider_name]
                
                result = await circuit_breaker.call(
                    self._call_provider,
                    provider_name,
                    prompt,
                    model_params or {}
                )
                
                logger.info(
                    "LLM call successful",
                    provider=provider_name,
                    prompt_length=len(prompt),
                    fallback_used=provider_name != preferred_provider
                )
                
                return result
                
            except Exception as e:
                last_error = e
                logger.warning(
                    "LLM provider failed, trying next",
                    provider=provider_name,
                    error=str(e),
                    remaining_providers=len(sorted_providers) - sorted_providers.index((provider_name, provider_config)) - 1
                )
                continue
        
        # All providers failed
        raise LLMProviderError(
            message="All LLM providers failed",
            provider="all",
            context={"tried_providers": list(self.providers.keys())},
            user_message="AI analysis is temporarily unavailable. Please try again in a few minutes.",
            recovery_suggestions=["Wait a few minutes and try again", "Contact support if the issue persists"],
            cause=last_error
        )
    
    async def _call_provider(self, provider: str, prompt: str, params: Dict[str, Any]) -> Dict[str, Any]:
        # Implementation specific to each provider
        pass
```

### 4. Temporal Workflow Error Handling

```python
from temporalio import workflow, activity
from temporalio.exceptions import ActivityError, WorkflowError
from temporalio.common import RetryPolicy
from datetime import timedelta

# Activity-level error handling
@activity.defn
async def process_user_activity(activity_data: Dict[str, Any]) -> Dict[str, Any]:
    """Process user activity with comprehensive error handling"""
    
    activity.heartbeat("Starting activity processing")
    
    try:
        # Validate input data
        if not activity_data.get('user_id'):
            raise ValidationError(
                message="Missing user_id in activity data",
                field="user_id",
                value=activity_data.get('user_id'),
                user_message="Invalid activity data provided"
            )
        
        # Process the activity
        result = await _process_activity_internal(activity_data)
        
        activity.heartbeat("Activity processing complete")
        return result
        
    except ValidationError:
        # Don't retry validation errors
        activity.logger.error(
            "Activity validation failed",
            activity_data=activity_data,
            exc_info=True
        )
        raise  # Re-raise without conversion
        
    except DatabaseError as e:
        # Log and convert for Temporal
        activity.logger.error(
            "Database error in activity processing",
            error_id=e.error_id,
            context=e.context,
            exc_info=True
        )
        raise ActivityError(
            message=f"Database error: {e.message}",
            cause=e,
            retry=True  # This error is retryable
        )
        
    except LLMProviderError as e:
        # Log and decide on retry
        activity.logger.error(
            "LLM provider error in activity processing",
            error_id=e.error_id,
            context=e.context,
            exc_info=True
        )
        raise ActivityError(
            message=f"LLM error: {e.message}",
            cause=e,
            retry=e.severity != ErrorSeverity.CRITICAL
        )
        
    except Exception as e:
        # Catch-all for unexpected errors
        activity.logger.error(
            "Unexpected error in activity processing",
            error=str(e),
            activity_data=activity_data,
            exc_info=True
        )
        raise ActivityError(
            message=f"Unexpected error: {str(e)}",
            cause=e,
            retry=False  # Don't retry unexpected errors
        )

# Workflow-level error handling
@workflow.defn
class ActivityAnalysisWorkflow:
    @workflow.run
    async def run(self, user_id: str, activities: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze user activities with error handling and compensation"""
        
        workflow_state = {
            'user_id': user_id,
            'total_activities': len(activities),
            'processed_activities': [],
            'failed_activities': [],
            'errors': []
        }
        
        # Process activities with individual error handling
        for i, activity_data in enumerate(activities):
            try:
                result = await workflow.execute_activity(
                    process_user_activity,
                    activity_data,
                    start_to_close_timeout=timedelta(minutes=5),
                    retry_policy=RetryPolicy(
                        initial_interval=timedelta(seconds=1),
                        maximum_interval=timedelta(minutes=1),
                        maximum_attempts=3,
                        non_retryable_error_types=[ValidationError.__name__]
                    )
                )
                workflow_state['processed_activities'].append(result)
                
            except ActivityError as e:
                workflow_state['failed_activities'].append({
                    'activity_index': i,
                    'activity_data': activity_data,
                    'error': str(e)
                })
                workflow_state['errors'].append({
                    'type': 'activity_error',
                    'activity_index': i,
                    'message': str(e)
                })
                
                # Send notification about failed activity
                await workflow.execute_activity(
                    send_error_notification,
                    {
                        'user_id': user_id,
                        'error_type': 'activity_processing_failed',
                        'error_message': str(e),
                        'context': {'activity_index': i}
                    },
                    start_to_close_timeout=timedelta(minutes=1)
                )
        
        # Determine workflow outcome
        if len(workflow_state['processed_activities']) == 0:
            # Complete failure
            raise TemporalWorkflowError(
                message="All activities failed to process",
                workflow_id=workflow.info().workflow_id,
                context=workflow_state,
                user_message="We couldn't process any of your activities. Please try again or contact support.",
                recovery_suggestions=["Try submitting activities individually", "Contact support"]
            )
        
        elif len(workflow_state['failed_activities']) > 0:
            # Partial failure - log warning but continue
            workflow.logger.warning(
                "Workflow completed with partial failures",
                workflow_state=workflow_state
            )
        
        return {
            'status': 'completed',
            'results': workflow_state['processed_activities'],
            'failures': workflow_state['failed_activities'],
            'summary': {
                'total': len(activities),
                'succeeded': len(workflow_state['processed_activities']),
                'failed': len(workflow_state['failed_activities'])
            }
        }
```

### 5. User-Facing Error Handling

```python
from slack_sdk.web.async_client import AsyncWebClient
from slack_sdk.errors import SlackApiError

class UserErrorHandler:
    def __init__(self, slack_client: AsyncWebClient):
        self.slack_client = slack_client
    
    async def handle_error_for_user(
        self,
        error: ReflectAIError,
        user_id: str,
        channel: Optional[str] = None,
        thread_ts: Optional[str] = None
    ):
        """Handle error by notifying user with appropriate message and actions"""
        
        # Create error response blocks
        error_blocks = self._build_error_blocks(error)
        
        try:
            if channel and thread_ts:
                # Reply in thread
                await self.slack_client.chat_postMessage(
                    channel=channel,
                    thread_ts=thread_ts,
                    blocks=error_blocks,
                    text=error.user_message  # Fallback text
                )
            else:
                # Send DM to user
                await self.slack_client.chat_postMessage(
                    channel=user_id,
                    blocks=error_blocks,
                    text=error.user_message
                )
            
            # Log error notification sent
            logger.info(
                "Error notification sent to user",
                error_id=error.error_id,
                user_id=user_id,
                channel=channel,
                notification_method="slack"
            )
            
        except SlackApiError as e:
            # Failed to notify user via Slack
            logger.error(
                "Failed to send error notification to user",
                error_id=error.error_id,
                user_id=user_id,
                slack_error=str(e),
                exc_info=True
            )
            
            # Store notification for retry or alternative delivery
            await self._store_failed_notification(error, user_id, str(e))
    
    def _build_error_blocks(self, error: ReflectAIError) -> List[Dict[str, Any]]:
        """Build Slack Block Kit representation of error"""
        
        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"❌ *{error.user_message}*"
                }
            }
        ]
        
        # Add recovery suggestions if available
        if error.recovery_suggestions:
            suggestions_text = "\n".join([f"• {suggestion}" for suggestion in error.recovery_suggestions])
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*What you can try:*\n{suggestions_text}"
                }
            })
        
        # Add action buttons based on error type
        action_elements = []
        
        if error.category in [ErrorCategory.TEMPORAL_ERROR, ErrorCategory.LLM_PROVIDER_ERROR]:
            action_elements.append({
                "type": "button",
                "text": {"type": "plain_text", "text": "🔄 Retry"},
                "style": "primary",
                "action_id": "retry_operation",
                "value": error.error_id
            })
        
        if error.severity in [ErrorSeverity.ERROR, ErrorSeverity.CRITICAL]:
            action_elements.append({
                "type": "button",
                "text": {"type": "plain_text", "text": "🆘 Get Help"},
                "action_id": "get_support",
                "value": error.error_id
            })
        
        if action_elements:
            blocks.append({
                "type": "actions",
                "elements": action_elements
            })
        
        # Add error ID for support reference (only for non-user errors)
        if error.severity in [ErrorSeverity.ERROR, ErrorSeverity.CRITICAL]:
            blocks.append({
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"Error ID: `{error.error_id}` | {error.timestamp.strftime('%Y-%m-%d %H:%M:%S')} UTC"
                    }
                ]
            })
        
        return blocks
    
    async def _store_failed_notification(self, error: ReflectAIError, user_id: str, failure_reason: str):
        """Store failed notification for retry or alternative delivery"""
        # Implementation would store in database for retry logic
        pass
```

## Error Monitoring and Alerting

### Error Metrics Collection

```python
from prometheus_client import Counter, Histogram, Enum

# Error metrics
error_counter = Counter(
    'reflectai_errors_total',
    'Total number of errors by category and severity',
    ['category', 'severity', 'component']
)

error_duration = Histogram(
    'reflectai_error_handling_duration_seconds',
    'Time spent handling errors',
    ['category', 'handler_type']
)

error_recovery_success = Counter(
    'reflectai_error_recovery_attempts_total',
    'Error recovery attempts and outcomes',
    ['category', 'recovery_type', 'outcome']
)

def track_error_metrics(error: ReflectAIError, component: str):
    """Track error metrics for monitoring and alerting"""
    error_counter.labels(
        category=error.category.value,
        severity=error.severity.value,
        component=component
    ).inc()
```

### Error Alerting Rules

```yaml
# Prometheus alerting rules for ReflectAI errors
groups:
  - name: reflectai.errors
    rules:
      - alert: HighErrorRate
        expr: rate(reflectai_errors_total[5m]) > 0.1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value }} errors per second"
      
      - alert: CriticalError
        expr: increase(reflectai_errors_total{severity="critical"}[5m]) > 0
        for: 0m
        labels:
          severity: critical
        annotations:
          summary: "Critical error occurred"
          description: "{{ $value }} critical errors in the last 5 minutes"
      
      - alert: DatabaseErrorSpike
        expr: increase(reflectai_errors_total{category="database_error"}[10m]) > 10
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "Database error spike"
          description: "{{ $value }} database errors in the last 10 minutes"
```

## Testing Error Handling

### Error Handling Test Patterns

```python
import pytest
from unittest.mock import AsyncMock, patch

class TestErrorHandling:
    
    @pytest.mark.asyncio
    async def test_database_error_handling(self):
        """Test database error handling and recovery"""
        
        with patch('sqlalchemy.ext.asyncio.session.commit') as mock_commit:
            mock_commit.side_effect = IntegrityError("Duplicate key", None, None)
            
            with pytest.raises(DatabaseError) as exc_info:
                await create_user_activity("user123", "test activity")
            
            error = exc_info.value
            assert error.category == ErrorCategory.DATABASE_ERROR
            assert error.error_code == "DB_INTEGRITY_ERROR"
            assert "integrity" in error.user_message.lower()
            assert len(error.recovery_suggestions) > 0
    
    @pytest.mark.asyncio
    async def test_llm_provider_fallback(self):
        """Test LLM provider fallback mechanism"""
        
        llm_manager = LLMProviderManager()
        
        with patch.object(llm_manager, '_call_provider') as mock_call:
            # First provider fails, second succeeds
            mock_call.side_effect = [
                LLMProviderError("Provider 1 failed", "claude"),
                {"result": "success", "provider": "openai"}
            ]
            
            result = await llm_manager.call_with_fallback("test prompt", "claude")
            
            assert result["result"] == "success"
            assert result["provider"] == "openai"
            assert mock_call.call_count == 2
    
    @pytest.mark.asyncio
    async def test_user_error_notification(self):
        """Test user error notification system"""
        
        mock_slack_client = AsyncMock()
        error_handler = UserErrorHandler(mock_slack_client)
        
        error = ValidationError(
            message="Invalid input",
            field="activity_content",
            value="",
            recovery_suggestions=["Provide valid activity content"]
        )
        
        await error_handler.handle_error_for_user(
            error=error,
            user_id="U123456",
            channel="C789012",
            thread_ts="1234567890.123456"
        )
        
        mock_slack_client.chat_postMessage.assert_called_once()
        call_args = mock_slack_client.chat_postMessage.call_args
        
        assert call_args.kwargs['channel'] == "C789012"
        assert call_args.kwargs['thread_ts'] == "1234567890.123456"
        assert len(call_args.kwargs['blocks']) > 0
        assert "Invalid input" in call_args.kwargs['text']
```

## Implementation Guidelines

### 1. Error Handling Checklist

For every new component, ensure:

- [ ] Custom exceptions inherit from appropriate base classes
- [ ] All exceptions include user-friendly messages
- [ ] Recovery suggestions are provided when possible
- [ ] Errors are logged with structured context
- [ ] Metrics are collected for monitoring
- [ ] Circuit breaker pattern used for external services
- [ ] Retry logic implemented where appropriate
- [ ] User notifications sent for user-facing errors

### 2. Code Review Guidelines

When reviewing error handling code:

- [ ] Errors are caught at appropriate levels
- [ ] Error messages are informative but not overly technical
- [ ] Sensitive information is not exposed in error messages
- [ ] Error context includes relevant debugging information
- [ ] Recovery actions are clearly defined
- [ ] Error handling doesn't mask underlying issues
- [ ] Performance impact of error handling is minimal

### 3. Documentation Requirements

Each error handling implementation should include:

- Clear description of error conditions
- Expected error types and when they occur
- Recovery strategies and user actions
- Monitoring and alerting considerations
- Testing strategies for error scenarios

This error handling framework provides comprehensive, consistent, and user-friendly error management across the entire ReflectAI system.