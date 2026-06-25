---
description: Create detailed, actionable implementation plan with phases, testing strategy, and risk assessment
argument-hint: [feature or task description]
---

# Create Implementation Plan for ReflectAI

Create a detailed, actionable implementation plan for ReflectAI development work: $ARGUMENTS

## Planning Methodology

### Phase 1: Requirements Analysis (5 minutes)
1. **Clarify the objective** - What exactly needs to be built or fixed?
2. **Understand business value** - Why is this important to ReflectAI users?
3. **Define success criteria** - How will we know when it's complete and working?
4. **Identify scope boundaries** - What's included and what's explicitly excluded?

### Phase 2: Technical Discovery (10 minutes)
1. **Research existing patterns** - How do similar features work in ReflectAI?
2. **Identify affected modules** - Which parts of the codebase will change?
3. **Map dependencies** - What external services, internal modules, or data are needed?
4. **Assess integration complexity** - How does this interact with LLM, Temporal, Slack, DB?

### Phase 3: Risk Assessment (5 minutes)
1. **Technical risks** - What could go wrong during implementation?
2. **Performance implications** - Will this affect response times or resource usage?
3. **Data consistency** - Are there database or cache consistency concerns?
4. **External service dependencies** - What happens if LLM providers, Slack, or DB are down?

### Phase 4: Implementation Strategy (10 minutes)
1. **Break down into phases** - What's the logical sequence of development?
2. **Identify testing strategy** - Unit tests, integration tests, manual verification?
3. **Plan rollback strategy** - How to quickly revert if something goes wrong?
4. **Consider deployment** - Any special deployment or configuration requirements?

## Implementation Plan Template

```markdown
# 📋 Implementation Plan: [FEATURE/TASK NAME]

## 🎯 Objective
**What**: [Clear, specific description of what will be built/fixed]
**Why**: [Business value and user impact]
**Success Criteria**:
- [ ] [Specific, measurable outcome 1]
- [ ] [Specific, measurable outcome 2]
- [ ] [Specific, measurable outcome 3]

## 📊 Technical Analysis

### Current State
- **Existing functionality**: [What currently exists in this area]
- **Relevant modules**: [Key files and their current state]
- **Current limitations**: [What doesn't work or what's missing]

### Target State
- **New functionality**: [What will be added or changed]
- **Integration points**: [How this connects to existing systems]
- **Performance expectations**: [Response time, throughput, resource usage requirements]

### Affected Components
```yaml
modules:
  core:
    - path: src/core/[module]/
      changes: [description of changes needed]
  services:
    - path: src/services/[module]/
      changes: [description of changes needed]
  interfaces:
    - path: src/interfaces/[module]/
      changes: [description of changes needed]
  infrastructure:
    - path: src/infrastructure/[module]/
      changes: [description of changes needed]

external_dependencies:
  - service: [PostgreSQL/Redis/LLM/Slack]
    impact: [how this change affects the external service]
```

## 🔧 Implementation Phases

### Phase 1: Foundation
**Estimated Time**: [X hours]
**Prerequisites**: [What must be completed before starting]

**Tasks**:
- [ ] [Specific task 1] - File: `[file_path]`
- [ ] [Specific task 2] - File: `[file_path]`
- [ ] [Specific task 3] - File: `[file_path]`

**Validation**:
- [ ] [How to verify this phase is complete]
- [ ] [Tests to run or checks to perform]

### Phase 2: Core Implementation
**Estimated Time**: [X hours]
**Prerequisites**: [Phase 1 complete + any other requirements]

**Tasks**:
- [ ] [Specific task 1] - File: `[file_path]`
- [ ] [Specific task 2] - File: `[file_path]`
- [ ] [Specific task 3] - File: `[file_path]`

**Validation**:
- [ ] [How to verify this phase is complete]
- [ ] [Tests to run or checks to perform]

### Phase 3: Integration & Testing
**Estimated Time**: [X hours]
**Prerequisites**: [Phase 2 complete]

**Tasks**:
- [ ] [Integration task 1]
- [ ] [Test implementation task]
- [ ] [End-to-end verification task]

**Validation**:
- [ ] [Integration tests pass]
- [ ] [Performance requirements met]
- [ ] [Error handling works correctly]

### Phase 4: Documentation & Deployment
**Estimated Time**: [X hours]
**Prerequisites**: [Phase 3 complete and validated]

**Tasks**:
- [ ] [Documentation updates]
- [ ] [Configuration changes]
- [ ] [Deployment preparation]

**Validation**:
- [ ] [Documentation is accurate and complete]
- [ ] [Ready for production deployment]

## 🧪 Testing Strategy

### Unit Tests
- **Location**: `tests/unit/[module_path]/`
- **Focus**: [What aspects need unit testing]
- **Coverage target**: 80%+ for new code
- **Key test cases**:
  - [ ] [Happy path scenario]
  - [ ] [Error handling scenario]
  - [ ] [Edge case scenario]

### Integration Tests
- **Location**: `tests/integration/`
- **Focus**: [Integration points to test]
- **External service mocking**: [What needs to be mocked vs real services]
- **Key integration scenarios**:
  - [ ] [Database integration scenario]
  - [ ] [LLM provider integration scenario]
  - [ ] [Slack API integration scenario]

### Manual Testing
- **Test environment setup**: [How to set up for manual testing]
- **Test scenarios**: [Step-by-step scenarios to verify manually]
- **Performance testing**: [How to verify performance requirements]

## 🚨 Risk Mitigation

### Technical Risks
- **Risk**: [Specific technical risk]
  - **Likelihood**: [High/Medium/Low]
  - **Impact**: [High/Medium/Low]
  - **Mitigation**: [How to prevent or handle this risk]

### Performance Risks
- **Risk**: [Performance degradation in specific area]
  - **Mitigation**: [Caching strategy, optimization approach, monitoring]

### Integration Risks
- **Risk**: [External service dependency failure]
  - **Mitigation**: [Fallback strategy, retry logic, graceful degradation]

## 📈 Success Metrics

### Functional Metrics
- [ ] All success criteria met
- [ ] All tests passing (unit + integration)
- [ ] Performance requirements met
- [ ] Error handling working correctly

### Quality Metrics
- [ ] Code coverage >80% for new code
- [ ] No new security vulnerabilities
- [ ] Documentation updated and accurate
- [ ] Follows ReflectAI coding patterns

### Operational Metrics
- [ ] No degradation in existing functionality
- [ ] Response time requirements met
- [ ] Resource usage within acceptable limits
- [ ] Monitoring and alerting in place

## 🔄 Rollback Plan

### Rollback Triggers
- [What conditions would trigger a rollback]
- [How to detect if rollback is needed]

### Rollback Process
1. [Step-by-step rollback procedure]
2. [How to verify rollback was successful]
3. [Communication plan for rollback]

## 💡 Implementation Notes

### ReflectAI-Specific Considerations
- **Async Patterns**: [Any specific async/await requirements]
- **Cost Tracking**: [LLM usage cost implications]
- **Response Timing**: [Slack response time requirements]
- **Temporal Workflows**: [Deterministic code requirements]
- **Database Patterns**: [Specific database considerations]

### Development Environment
- **Local setup**: [Any special local development needs]
- **Dependencies**: [New packages or services needed]
- **Configuration**: [Environment variables or settings to add]

### Monitoring & Observability
- **Logging**: [What should be logged for debugging]
- **Metrics**: [What metrics should be tracked]
- **Alerts**: [What conditions should trigger alerts]

---

## 📝 Plan Review Checklist

Before starting implementation, verify:
- [ ] Objective is clear and measurable
- [ ] All affected components identified
- [ ] Dependencies and risks assessed
- [ ] Testing strategy is comprehensive
- [ ] Rollback plan exists
- [ ] Time estimates are realistic
- [ ] Success criteria are specific and verifiable

**Estimated Total Time**: [Sum of all phase estimates]
**Risk Level**: [High/Medium/Low based on risk assessment]

---

*Plan created: [DATE/TIME]*
*Ready for implementation: [YES/NO - complete review checklist first]*
```

## Planning Guidelines

### Focus Areas for ReflectAI
1. **Integration Complexity**: Always consider how changes affect LLM, Temporal, Slack, and DB
2. **Async Patterns**: Plan for proper async/await usage throughout
3. **Cost Implications**: Consider LLM usage costs in feature design
4. **Response Timing**: Plan for Slack's 3-second response requirement
5. **Data Consistency**: Consider database and cache consistency needs
6. **Error Handling**: Plan comprehensive error handling and user feedback

### Quality Standards
- **Specificity**: Tasks should be specific enough to implement directly
- **Testability**: Every task should have clear verification criteria
- **Realistic Timing**: Base time estimates on similar past work
- **Risk Awareness**: Identify and plan for likely failure scenarios

### Success Criteria
- **Measurable**: Use specific metrics, not vague descriptions
- **User-focused**: Consider impact on actual ReflectAI users
- **Technical**: Include performance and quality requirements
- **Operational**: Consider monitoring and maintenance needs

Remember: Time spent in thorough planning saves hours of implementation rework. A good plan should make implementation feel like following a recipe rather than solving puzzles.