---
description: Design new feature from scratch with complete architecture, data models, integrations, and implementation plan
argument-hint: [feature description]
---

# Design Feature - Architecture and Implementation Plan

Design a new feature from scratch with complete architecture: $ARGUMENTS

## Design Process

### Step 1: Requirements (2-3 min)
1. Understand the goal and problem
2. Define scope (in/out)
3. Identify users and use cases
4. Success criteria
5. Technical constraints

### Step 2: Architecture (3-5 min)
1. Identify affected layers (core/services/interfaces/infrastructure)
2. Design data models (Pydantic, database schemas)
3. Plan integrations (DB, Redis, LLM, Temporal, Slack)
4. Design API contracts
5. Plan error handling

### Step 3: ReflectAI Integration (2-3 min)
1. LLM usage and cost implications
2. Temporal workflows for long-running ops
3. Slack interaction requirements
4. Database design and migrations
5. Caching strategy

### Step 4: Technical Specs (3-4 min)
1. Module structure and file organization
2. Dependencies and new packages
3. Configuration and environment variables
4. Performance targets
5. Security considerations

### Step 5: Implementation (2-3 min)
1. Break into development phases
2. Identify risks and mitigations
3. Test strategy (unit/integration/e2e)
4. Rollout and deployment plan
5. Monitoring and metrics

## Design Checklist

### ReflectAI Standards
- [ ] All I/O operations are async
- [ ] Uses `src.shared.exceptions` for errors
- [ ] LLM costs tracked if applicable
- [ ] Temporal determinism if using workflows
- [ ] Slack responses <3s if user-facing
- [ ] Database operations use async patterns
- [ ] Structured logging with correlation IDs

### Quality Requirements
- [ ] Clear problem statement
- [ ] Complete data models
- [ ] All integrations identified
- [ ] Performance requirements specified
- [ ] Security addressed
- [ ] Test strategy defined
- [ ] Deployment plan documented
- [ ] Monitoring planned

Remember: Good design prevents implementation rework!
