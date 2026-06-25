# Slack Integration Architecture
**Version**: 0.1.2-alpha
**Last Updated**: October 5, 2025
**Status**: Production-Ready

## Overview

The ReflectAI Slack integration provides real-time conversational AI capabilities through a sophisticated, mode-agnostic architecture that supports both Socket Mode (WebSocket) and HTTP Mode (Webhooks).

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                          Slack Platform                             │
│                  (WebSocket / HTTP Webhooks)                        │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      SlackAdapter (Mode-Agnostic)                   │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ • Auto-detect Socket/HTTP mode                               │  │
│  │ • Initialize appropriate authentication                       │  │
│  │ • Rate-limited API calls (_api_call_with_retry)             │  │
│  │ • Health monitoring                                           │  │
│  └──────────────────────────────────────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    SlackSocketHandler (Event Processing)            │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ • 3-second event acknowledgment                              │  │
│  │ • EventDeduplicator (Redis-based)                            │  │
│  │ • Route to ConversationManager                               │  │
│  └──────────────────────────────────────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     ConversationManager (Orchestration)              │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ • ConversationIntelligence (intent analysis)                 │  │
│  │ • ThreadingManager (hybrid strategy)                         │  │
│  │ • ResponseFormatter (Block Kit)                              │  │
│  │ • Redis context management (24hr TTL)                        │  │
│  └──────────────────────────────────────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│               WorkflowIntegration (Temporal Bridge)                  │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ • WorkflowRouter (route to appropriate workflows)            │  │
│  │ • _monitor_workflow (150-iteration timeout = 5 minutes)      │  │
│  │ • Enhanced error handling (network, timeout, API errors)     │  │
│  │ • BlockBuilder (Slack Block Kit formatting)                  │  │
│  └──────────────────────────────────────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      Temporal Workflows                              │
│                 (Competency Analysis, Assessments)                   │
└─────────────────────────────────────────────────────────────────────┘
```

## Core Components

### 1. SlackAdapter (`src/interfaces/slack/adapter.py`)

**Purpose**: Mode-agnostic initialization and API client management

**Features**:
- **Mode Detection**: Auto-detects Socket Mode vs HTTP Mode based on environment variables
- **Authentication**: Handles BOT_TOKEN, APP_TOKEN (Socket), SIGNING_SECRET (HTTP)
- **Rate Limiting**: Simple retry mechanism for 429 rate limit errors
- **Health Checks**: Real-time status monitoring

**Key Methods**:
```python
async def initialize() -> bool
async def _api_call_with_retry(method_name, max_retries=1, **kwargs)
async def safe_post_message(**kwargs)
async def safe_update_message(**kwargs)
def get_health_status() -> Dict[str, Any]
```

**Rate Limiting Configuration**:
```bash
# .env
SLACK_RATE_LIMIT_RETRIES=1  # Number of retries on 429 errors
```

### 2. SlackSocketHandler (`src/interfaces/slack/socket_handler.py`)

**Purpose**: Event handling and 3-second acknowledgment compliance

**Features**:
- **Fast Acknowledgment**: Responds within 3 seconds (Slack requirement)
- **Event Deduplication**: Redis-based duplicate event prevention
- **Event Routing**: Routes to ConversationManager for processing

**Threading Strategy**: Delegates to ThreadingManager

### 3. ConversationManager (`src/interfaces/slack/conversation_manager.py`)

**Purpose**: Orchestrates conversation flow and context management

**Features**:
- **Conversation Intelligence**: Intent classification and context analysis
- **Threading Manager**: Hybrid strategy (Requirement 22)
  - No threading in DMs
  - Threading for complex workflows in channels
- **Context Management**: Redis-backed conversation state (24hr TTL)
- **Response Formatting**: Block Kit message formatting

### 4. WorkflowIntegration (`src/interfaces/slack/workflow_integration.py`)

**Purpose**: Bridges Slack events to Temporal workflows

**Features**:
- **Workflow Routing**: Routes user requests to appropriate workflows
- **Workflow Monitoring**: 150-iteration timeout (5 minutes)
- **Enhanced Error Handling**: Specific handling for network, timeout, and API errors
- **User Profile Loading**: Cached user profile with graceful fallback
- **Progress Updates**: Real-time status updates during workflow execution

**Key Methods**:
```python
async def handle_message_event(event, say, ack)
async def handle_slash_command(command, ack, respond)
async def _monitor_workflow(workflow_id, slack_context, say, message_ts)
async def _load_user_profile(user_id) -> Dict[str, Any]
async def _send_error_response(slack_context, say, error_message)
async def _send_workflow_failure(workflow_id, slack_context, say)
async def _update_progress(slack_context, message_ts, status_text)
```

## Rate Limit Handling

### Current Implementation: Simple Retry (Option B)

The Slack integration uses a pragmatic approach to rate limiting:

**Approach**: One-time retry on 429 rate limit errors
- Respects `Retry-After` header from Slack API
- Logs rate limit events for monitoring (WARNING level)
- Suitable for low-to-medium traffic applications (human-paced conversations)

**Implementation Details**:
```python
# SlackAdapter._api_call_with_retry()
# - Catches SlackApiError with error="rate_limited"
# - Sleeps for retry_after seconds (from header or default 1s)
# - Retries once (configurable)
# - Logs all retry attempts
```

**User-Facing Behavior**:
- Existing `say()` function continues to work unchanged
- New `safe_post_message()` and `safe_update_message()` methods available for critical paths
- Transparent to end users (retries happen automatically)

### When to Upgrade to Full Rate Limiting

**Upgrade indicators**:
1. ✅ Seeing >5 rate limit events per day in logs
2. ✅ User complaints about slow responses
3. ✅ Adding bulk messaging features
4. ✅ Scaling to 50+ concurrent users

**How to upgrade**:
1. Replace `_api_call_with_retry()` with full `RateLimitedWebClient` wrapper
2. See `docs/implementation_plans/SLACK_FIXES_SURGICAL_PLAN_FINAL.md` Phase 1
3. Effort: 0.4 days additional (total 0.5 days)

### Slack Rate Limit Resources
- [Slack Rate Limits Documentation](https://api.slack.com/docs/rate-limits)
- Typical limits: ~1 req/sec per channel, ~50 req/min workspace-wide
- Tier 1 methods (chat.postMessage): ~1 req/sec
- Tier 2 methods (users.info): ~20 req/min

## Error Handling Strategy

### Multi-Level Error Handling

The integration implements comprehensive error handling at multiple levels:

#### 1. Network Layer Errors (`httpx.NetworkError`)
**Handling**: Graceful fallback with user-friendly messages
**Example**: "I'm having trouble connecting to our services. Please try again in a moment."

#### 2. Timeout Errors (`httpx.TimeoutException`)
**Handling**: Retry with exponential backoff or inform user
**Example**: "Your request is taking longer than expected. Please try again."

#### 3. Slack API Errors (`SlackApiError`)
**Handling**: Specific error code handling
**Examples**:
- `rate_limited` → Retry with Retry-After header
- `user_not_found` → Return minimal profile
- `message_not_found` → Log warning, continue gracefully

#### 4. Workflow Timeout Errors
**Handling**: 150-iteration timeout (5 minutes)
**Example**: "Workflow monitoring timed out after 300 seconds. The workflow may still be running."

### Error Response Pattern

All error handlers follow this pattern:
```python
try:
    # Operation
except httpx.NetworkError as e:
    logger.error("Network error", extra={"error": str(e), "error_type": "network"})
    await self._send_error_response(context, say, "Network issue. Try again.")
except httpx.TimeoutException as e:
    logger.error("Timeout", extra={"error": str(e), "error_type": "timeout"})
    await self._send_error_response(context, say, "Timeout. Try again.")
except SlackApiError as e:
    logger.error("Slack API error", extra={"error": e.response.get("error")})
    await self._send_error_response(context, say, "Slack issue. Try again.")
except Exception as e:
    logger.error("Unexpected error", extra={"error": str(e)}, exc_info=True)
    await self._send_error_response(context, say, "Unexpected error. Team notified.")
```

## Threading Strategy (Requirement 22)

### Hybrid Threading Approach

The integration uses a sophisticated threading strategy managed by `ThreadingManager`:

**Rules**:
1. **No threading in Direct Messages (DMs)** - unless explicitly requested
2. **Threading for complex workflows in channels** - keeps channel clean
3. **Continue existing threads** - maintains conversation context
4. **User preference override** - respects user threading settings

**Implementation**:
```python
def _should_use_thread(slack_context: SlackContext) -> bool:
    # No threading in DMs (unless configured)
    if slack_context.is_direct_message and not use_threading_in_dm:
        return False

    # Always thread in channels for complex workflows
    if not slack_context.is_direct_message and thread_for_complex_workflows:
        return True

    # Continue existing thread
    if slack_context.thread_ts:
        return True

    return use_threading_in_channels and not slack_context.is_direct_message
```

## Event Deduplication

### Redis-Based Deduplication

**Purpose**: Prevent duplicate processing of Slack events (network retries, user double-clicks)

**Implementation**:
- Event ID stored in Redis with 5-minute TTL
- First occurrence: Process event, store ID
- Duplicate: Return early with log message

**Key**: `slack_event:{event_id}`
**TTL**: 300 seconds (5 minutes)

## Conversation Context Management

### Redis-Backed State

**Purpose**: Maintain conversation context across multiple messages

**Storage**:
- **Key Pattern**: `conversation:{user_id}:{thread_ts}`
- **TTL**: 24 hours (86400 seconds)
- **Content**: Intent history, user profile, workflow IDs, message history

**Cleanup**: Automatic TTL expiration

## Monitoring and Observability

### Health Checks

**Endpoint**: `SlackAdapter.get_health_status()`

**Returns**:
```json
{
  "mode": "socket",
  "initialized": true,
  "sdk_available": true,
  "app_configured": true,
  "client_ready": true,
  "handler_ready": true
}
```

### Key Metrics to Monitor

1. **Rate Limit Events**
   ```bash
   grep "Rate limited by Slack API" logs/app.log | wc -l
   ```
   **Alert Threshold**: >5 per day

2. **Workflow Timeouts**
   ```bash
   grep "Workflow monitoring timeout" logs/app.log
   ```
   **Alert Threshold**: >2 per day

3. **Network Errors**
   ```bash
   grep "Network error" logs/app.log | grep "slack"
   ```
   **Alert Threshold**: >10 per hour

4. **Event Deduplication Rate**
   ```bash
   grep "Duplicate Slack event ignored" logs/app.log
   ```
   **Expected**: <5% of total events

### Logging Patterns

All logs include structured extra fields for filtering:
```python
logger.error(
    "Error message",
    extra={
        "error": str(e),
        "error_type": "network",
        "user_id": "U123",
        "channel_id": "C123",
        "workflow_id": "wf_123"
    },
    exc_info=True
)
```

## Configuration

### Environment Variables

```bash
# Slack Bot Configuration
SLACK_BOT_TOKEN=xoxb-...           # Required for all modes
SLACK_APP_TOKEN=xapp-...           # Required for Socket Mode
SLACK_SIGNING_SECRET=...           # Required for HTTP Mode
SLACK_CLIENT_ID=...                # OAuth flow
SLACK_CLIENT_SECRET=...            # OAuth flow

# Rate Limiting (Optional)
SLACK_RATE_LIMIT_RETRIES=1        # Number of retries on 429 errors
```

### Mode Detection

**Socket Mode** (detected if `SLACK_APP_TOKEN` present):
- Uses WebSocket connection
- Real-time event delivery
- No need for public endpoint
- Best for development and small deployments

**HTTP Mode** (detected if `SLACK_SIGNING_SECRET` present):
- Uses webhook endpoint
- Requires public HTTPS endpoint
- More scalable for production
- Best for high-traffic deployments

## Performance Characteristics

### Latency Targets

- **Event Acknowledgment**: <3 seconds (Slack requirement)
- **Simple Message Response**: <2 seconds
- **Workflow Start**: <5 seconds
- **Workflow Completion**: <5 minutes (timeout)

### Throughput

- **Socket Mode**: ~100 messages/minute
- **HTTP Mode**: ~500 messages/minute (with proper scaling)
- **Rate Limit**: ~1 message/second per channel (Slack limit)

### Resource Usage

- **Memory**: ~50MB per worker (Python process)
- **Redis**: ~1KB per conversation context
- **Connections**: 1 persistent WebSocket (Socket Mode) or HTTP workers

## Testing Strategy

### Test Coverage

1. **Unit Tests**:
   - SlackAdapter mode detection
   - Rate limit retry logic
   - Error handling for all error types

2. **Integration Tests**:
   - `test_simple_retry.py` - 5 tests for rate limiting
   - `test_workflow_monitoring.py` - 3 tests for timeout handling
   - `test_error_handling.py` - 8 tests for error scenarios

3. **Manual Testing**:
   - Send burst of messages to trigger rate limits
   - Simulate network errors (disconnect WiFi)
   - Test workflow timeout (5+ minute workflow)

### Test Commands

```bash
# Run all Slack integration tests
./rai test tests/integration/test_simple_retry.py
./rai test tests/integration/test_workflow_monitoring.py
./rai test tests/integration/test_error_handling.py

# Run with coverage
./rai test --cov=src/interfaces/slack
```

## Deployment Considerations

### Development Environment

```bash
# 1. Install dependencies
./rai setup deps

# 2. Configure environment
cp .env.example .env
# Edit .env with Slack tokens

# 3. Start in Socket Mode (easier for development)
export SLACK_APP_TOKEN=xapp-...
./rai run app
```

### Production Environment

**Recommendations**:
1. Use **HTTP Mode** for better scalability
2. Deploy behind load balancer with SSL termination
3. Configure proper webhook endpoint: `https://your-domain.com/slack/events`
4. Monitor rate limit events daily
5. Set up alerts for workflow timeouts

### Scaling Strategy

**Horizontal Scaling**:
- HTTP Mode: Add more workers behind load balancer
- Socket Mode: Use Slack's multi-org support (one connection per workspace)

**Vertical Scaling**:
- Increase worker memory for larger conversation contexts
- Optimize Redis connection pooling

## Troubleshooting

### Common Issues

1. **"Slack adapter initialization failed"**
   - Check environment variables are set
   - Verify bot token has correct scopes
   - Check network connectivity to Slack

2. **"Rate limited by Slack API"**
   - Normal for burst traffic
   - Automatic retry will handle
   - If frequent (>5/day), consider upgrading rate limiting

3. **"Workflow monitoring timeout"**
   - Workflow taking >5 minutes
   - Check Temporal worker status
   - Consider increasing timeout for long-running workflows

4. **"Duplicate Slack event ignored"**
   - Normal behavior (network retries)
   - If excessive (>5% of events), check Redis connectivity

### Debug Commands

```bash
# Check Slack adapter health
curl http://localhost:8000/health/slack

# View recent Slack errors
tail -f logs/app.log | grep "slack" | grep "ERROR"

# Monitor rate limits
watch -n 5 'grep "Rate limited" logs/app.log | wc -l'

# Check Redis connectivity
redis-cli PING
redis-cli KEYS "slack_event:*" | wc -l
```

## Future Enhancements

### Short-term (v0.1.3)
- [ ] Add metrics collection (Prometheus/Datadog)
- [ ] Implement webhook signature verification
- [ ] Add Slack interactive components support

### Medium-term (v0.2.0)
- [ ] Upgrade to full rate limiting wrapper (if needed)
- [ ] Add support for Slack app home tab
- [ ] Implement message shortcuts

### Long-term (v1.0.0)
- [ ] Multi-workspace support
- [ ] Advanced conversation analytics
- [ ] Slack Connect support (external organizations)

## References

- [Slack Bolt Framework Documentation](https://slack.dev/bolt-python/)
- [Slack API Rate Limits](https://api.slack.com/docs/rate-limits)
- [Slack Socket Mode](https://api.slack.com/apis/connections/socket)
- [Slack Block Kit](https://api.slack.com/block-kit)

---

**Document Version**: 1.0
**Implementation Status**: Production-Ready (v0.1.2-alpha)
**Last Review**: October 5, 2025
