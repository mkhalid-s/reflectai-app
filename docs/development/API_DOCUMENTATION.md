# ReflectAI API Documentation

## Overview

The ReflectAI Platform provides a comprehensive REST API for competency tracking, career development, and professional growth analytics.

**Base URL**: `https://api.reflectai.com/v1`

## Authentication

All API requests require authentication using Bearer tokens:

```http
Authorization: Bearer <token>
```

### Obtaining a Token

```http
POST /auth/token
Content-Type: application/json

{
  "user_id": "U123456",
  "team_id": "T789012"
}
```

**Response**:
```json
{
  "token": "eyJhbGciOiJIUzI1NiIs...",
  "expires_at": "2024-12-31T23:59:59Z"
}
```

## Core Endpoints

### Activities

#### Log Activity

```http
POST /activities
Content-Type: application/json

{
  "description": "Implemented caching layer for API endpoints",
  "activity_type": "development",
  "duration_minutes": 120,
  "tags": ["backend", "performance", "redis"]
}
```

**Response**:
```json
{
  "activity_id": "act_123",
  "user_id": "U123456",
  "created_at": "2024-01-15T10:30:00Z",
  "competencies_affected": [
    {
      "name": "Technical Expertise",
      "impact": 0.8
    },
    {
      "name": "System Design",
      "impact": 0.6
    }
  ]
}
```

#### Get Activities

```http
GET /activities?start_date=2024-01-01&end_date=2024-01-31&limit=50
```

**Response**:
```json
{
  "activities": [
    {
      "activity_id": "act_123",
      "description": "Implemented caching layer",
      "activity_type": "development",
      "created_at": "2024-01-15T10:30:00Z",
      "duration_minutes": 120
    }
  ],
  "total": 150,
  "page": 1,
  "has_more": true
}
```

### Competencies

#### Get Competency Assessment

```http
GET /competencies/assessment
```

**Response**:
```json
{
  "user_id": "U123456",
  "assessment_date": "2024-01-15T00:00:00Z",
  "competencies": [
    {
      "name": "Technical Expertise",
      "current_score": 78.5,
      "previous_score": 75.2,
      "trend": "improving",
      "percentile": 85,
      "evidence_count": 42
    },
    {
      "name": "Leadership",
      "current_score": 65.3,
      "previous_score": 64.1,
      "trend": "stable",
      "percentile": 70,
      "evidence_count": 18
    }
  ],
  "overall_score": 72.4,
  "strengths": ["Technical Expertise", "Problem Solving"],
  "development_areas": ["Communication", "Strategic Thinking"]
}
```

#### Compare with Role Requirements

```http
GET /competencies/compare?target_role=staff_engineer
```

**Response**:
```json
{
  "current_role": "senior_engineer",
  "target_role": "staff_engineer",
  "gap_analysis": [
    {
      "competency": "System Design",
      "current": 70,
      "required": 85,
      "gap": 15
    },
    {
      "competency": "Technical Leadership",
      "current": 60,
      "required": 80,
      "gap": 20
    }
  ],
  "readiness_score": 68,
  "estimated_time_months": 6
}
```

### Career Development

#### Get Career Advice

```http
POST /career/advice
Content-Type: application/json

{
  "focus_area": "system_design",
  "target_role": "staff_engineer",
  "timeframe_months": 6
}
```

**Response**:
```json
{
  "recommendations": [
    {
      "priority": "high",
      "action": "Lead a cross-team architecture initiative",
      "competency": "System Design",
      "expected_impact": 3.5,
      "resources": [
        {
          "type": "course",
          "title": "Designing Data-Intensive Applications",
          "url": "https://..."
        }
      ]
    },
    {
      "priority": "medium",
      "action": "Mentor junior engineers",
      "competency": "Technical Leadership",
      "expected_impact": 2.8
    }
  ],
  "milestones": [
    {
      "month": 1,
      "goal": "Complete system design course",
      "success_criteria": "Pass certification exam"
    },
    {
      "month": 3,
      "goal": "Lead first architecture review",
      "success_criteria": "Successful implementation of proposed design"
    }
  ]
}
```

### Goals

#### Create Goal

```http
POST /goals
Content-Type: application/json

{
  "title": "Become Staff Engineer",
  "description": "Develop skills required for staff engineer role",
  "target_date": "2024-12-31",
  "competencies": ["System Design", "Technical Leadership"],
  "success_metrics": [
    {
      "metric": "System Design Score",
      "target": 85
    }
  ]
}
```

**Response**:
```json
{
  "goal_id": "goal_456",
  "status": "active",
  "created_at": "2024-01-15T10:30:00Z",
  "milestones": [
    {
      "milestone_id": "ms_789",
      "title": "Q1 - Foundation",
      "due_date": "2024-03-31",
      "tasks": []
    }
  ]
}
```

#### Track Goal Progress

```http
GET /goals/{goal_id}/progress
```

**Response**:
```json
{
  "goal_id": "goal_456",
  "overall_progress": 35,
  "days_remaining": 350,
  "on_track": true,
  "milestone_progress": [
    {
      "milestone_id": "ms_789",
      "title": "Q1 - Foundation",
      "progress": 70,
      "completed_tasks": 7,
      "total_tasks": 10
    }
  ],
  "competency_progress": [
    {
      "competency": "System Design",
      "start_score": 70,
      "current_score": 75,
      "target_score": 85,
      "progress_percentage": 33
    }
  ]
}
```

### Reports

#### Generate Report

```http
POST /reports/generate
Content-Type: application/json

{
  "report_type": "competency_assessment",
  "format": "pdf",
  "period": {
    "start": "2024-01-01",
    "end": "2024-01-31"
  },
  "include_sections": [
    "executive_summary",
    "competency_details",
    "peer_comparison",
    "recommendations"
  ]
}
```

**Response**:
```json
{
  "report_id": "rpt_abc123",
  "status": "generating",
  "estimated_completion": "2024-01-15T10:35:00Z",
  "webhook_url": "https://api.reflectai.com/v1/reports/rpt_abc123/status"
}
```

#### Download Report

```http
GET /reports/{report_id}/download
```

**Response**: Binary PDF data

### Analytics

#### Get Trends

```http
GET /analytics/trends?timeframe=monthly&months=6
```

**Response**:
```json
{
  "trends": [
    {
      "competency": "Technical Expertise",
      "data_points": [
        {"month": "2023-08", "score": 72},
        {"month": "2023-09", "score": 73.5},
        {"month": "2023-10", "score": 75},
        {"month": "2023-11", "score": 76.2},
        {"month": "2023-12", "score": 77.8},
        {"month": "2024-01", "score": 78.5}
      ],
      "trend_line": "y = 1.3x + 72",
      "r_squared": 0.92,
      "projection_next_month": 79.8
    }
  ],
  "insights": [
    {
      "type": "positive_trend",
      "message": "Technical Expertise showing consistent improvement",
      "confidence": 0.92
    }
  ]
}
```

#### Get Activity Patterns

```http
GET /analytics/patterns
```

**Response**:
```json
{
  "patterns": [
    {
      "pattern_type": "peak_productivity",
      "description": "Most productive hours: 9AM-12PM",
      "confidence": 0.85,
      "data": {
        "peak_hours": [9, 10, 11],
        "activities_count": 156,
        "average_impact": 0.78
      }
    },
    {
      "pattern_type": "skill_focus",
      "description": "Heavy focus on backend development",
      "confidence": 0.91,
      "data": {
        "primary_activities": ["coding", "system_design", "code_review"],
        "percentage": 68
      }
    }
  ]
}
```

## Slack Integration

### Commands

The following Slack slash commands are available:

- `/reflect analyze` - Analyze recent work activities
- `/reflect competencies` - View competency assessment
- `/reflect advice [area]` - Get career development advice
- `/reflect report` - Generate a report
- `/reflect goals` - View and manage goals

### Interactive Messages

The bot responds to natural language messages:

```
User: Analyze my work from last week
Bot: Analyzing your activities from Jan 8-14...

📊 Weekly Analysis:
- Activities logged: 23
- Total hours: 38.5
- Top competencies developed:
  • Technical Expertise (+2.3)
  • Problem Solving (+1.8)
  • Collaboration (+1.2)

💡 Insights:
- You spent 65% of time on deep technical work
- Collaboration increased by 20% this week
- Consider balancing with strategic planning activities
```

## Rate Limits

| Endpoint Category | Rate Limit | Window |
|------------------|------------|--------|
| Authentication | 10 requests | 1 minute |
| Activity Logging | 100 requests | 1 minute |
| Analytics | 20 requests | 1 minute |
| Report Generation | 10 requests | 1 hour |
| General API | 1000 requests | 1 minute |

## Error Responses

All errors follow a consistent format:

```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Too many requests. Please retry after 30 seconds.",
    "details": {
      "limit": 100,
      "remaining": 0,
      "reset_at": "2024-01-15T10:31:00Z"
    }
  },
  "request_id": "req_xyz789"
}
```

### Common Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `UNAUTHORIZED` | 401 | Invalid or missing authentication |
| `FORBIDDEN` | 403 | Insufficient permissions |
| `NOT_FOUND` | 404 | Resource not found |
| `VALIDATION_ERROR` | 400 | Invalid request parameters |
| `RATE_LIMIT_EXCEEDED` | 429 | Too many requests |
| `INTERNAL_ERROR` | 500 | Server error |

## Webhooks

Configure webhooks to receive real-time notifications:

```http
POST /webhooks
Content-Type: application/json

{
  "url": "https://your-app.com/webhook",
  "events": [
    "goal.completed",
    "milestone.achieved",
    "report.ready",
    "competency.improved"
  ],
  "secret": "your_webhook_secret"
}
```

### Webhook Payload

```json
{
  "event": "goal.completed",
  "timestamp": "2024-01-15T10:30:00Z",
  "data": {
    "goal_id": "goal_456",
    "user_id": "U123456",
    "title": "Become Staff Engineer",
    "completed_at": "2024-01-15T10:30:00Z"
  },
  "signature": "sha256=abc123..."
}
```

## SDK Support

### Python

```python
from reflectai import Client

client = Client(api_key="your_api_key")

# Log activity
activity = client.activities.create(
    description="Implemented new feature",
    activity_type="development",
    duration_minutes=120
)

# Get competency assessment
assessment = client.competencies.get_assessment()
print(f"Overall score: {assessment.overall_score}")
```

### JavaScript/TypeScript

```typescript
import { ReflectAI } from '@reflectai/sdk';

const client = new ReflectAI({ apiKey: 'your_api_key' });

// Log activity
const activity = await client.activities.create({
  description: 'Implemented new feature',
  activityType: 'development',
  durationMinutes: 120
});

// Get competency assessment
const assessment = await client.competencies.getAssessment();
console.log(`Overall score: ${assessment.overallScore}`);
```

## Support

- **Documentation**: https://docs.reflectai.com
- **Status Page**: https://status.reflectai.com
- **Support Email**: support@reflectai.com
- **API Changelog**: https://docs.reflectai.com/changelog