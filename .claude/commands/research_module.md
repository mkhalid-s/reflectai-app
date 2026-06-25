---
description: Deep research of a ReflectAI module including dependencies, usage patterns, tests, and integration points
argument-hint: [module path]
---

# Research ReflectAI Module

Research the specified module in the ReflectAI codebase: $ARGUMENTS

## Research Process

### Step 1: File Analysis
1. **Read the target module file completely** to understand its structure
2. **Identify the module's primary purpose** and responsibilities
3. **Document key classes, functions, and methods** with their purposes
4. **Note any configuration or environment dependencies**

### Step 2: Dependency Mapping
1. **Analyze imports** - both standard library and custom ReflectAI modules
2. **Identify external service dependencies** (Redis, PostgreSQL, LLM providers, Slack)
3. **Map integration points** with other ReflectAI modules
4. **Check for async/await patterns** and their proper usage

### Step 3: Test Coverage Analysis
1. **Find corresponding test files** in the `tests/` directory
2. **Assess test coverage completeness** for the module
3. **Identify untested code paths** or missing test scenarios
4. **Note testing patterns used** (mocking strategies, async test patterns)

### Step 4: Usage Pattern Discovery
1. **Search codebase** for imports and usage of this module
2. **Identify calling patterns** and how the module is typically used
3. **Find configuration references** in settings or environment files
4. **Document API endpoints** that use this module (if applicable)

### Step 5: Integration Points Analysis
1. **Database interactions** - identify models, queries, migrations
2. **External service calls** - LLM providers, Slack API, etc.
3. **Temporal workflow integration** - activities, workflows, or signals
4. **Error handling patterns** and logging practices

## Output Format

```markdown
# Module Analysis: [MODULE_NAME]

## Overview
- **File Path**: `[full_path_to_module]`
- **Primary Purpose**: [What this module does in 1-2 sentences]
- **Module Type**: [Core Logic / Service Layer / Interface / Infrastructure]
- **Last Modified**: [If available from git]

## Key Components

### Classes
- **ClassName**: [Purpose and key methods]
- **ClassName**: [Purpose and key methods]

### Functions
- **function_name()**: [Purpose and parameters]
- **function_name()**: [Purpose and parameters]

### Constants/Configuration
- **CONFIG_NAME**: [Purpose and typical values]

## Dependencies Analysis

### Internal Dependencies (ReflectAI modules)
- `src.core.module`: [How it's used]
- `src.services.module`: [How it's used]

### External Dependencies
- **Database**: [Tables/models accessed]
- **Redis**: [Keys/patterns used]
- **LLM Services**: [Providers and usage patterns]
- **Slack API**: [Endpoints and event types]
- **Third-party Libraries**: [Key external packages]

## Integration Points

### Async Patterns
- [List async functions and their purposes]
- [Error handling in async operations]

### Error Handling
- [Exception types raised]
- [Error logging and monitoring]

### Configuration
- [Environment variables used]
- [Settings classes or config files]

## Test Coverage Status

### Test Files Found
- `tests/[path]/test_[module].py`: [Coverage description]

### Test Patterns Used
- [Async test patterns]
- [Mocking strategies for external services]
- [Test fixtures and setup]

### Coverage Gaps
- [Functions/methods without tests]
- [Error scenarios not covered]
- [Integration test needs]

## Usage Patterns Across Codebase

### Direct Usage
- `[module_path]`: [How this module is imported and used]
- `[module_path]`: [How this module is imported and used]

### API Integration
- **Endpoints**: [API routes that use this module]
- **Workflow Integration**: [Temporal workflows/activities using this module]
- **Event Handlers**: [Slack event handlers using this module]

## Performance Considerations
- [Database query patterns and optimization opportunities]
- [Caching strategies in use]
- [Async operation efficiency]
- [Resource usage patterns]

## Technical Debt & Improvement Opportunities
- [TODO comments found in code]
- [Outdated patterns or deprecated usage]
- [Missing error handling or logging]
- [Documentation gaps]

## Risk Assessment for Modifications
- **Low Risk**: [Safe areas to modify]
- **Medium Risk**: [Areas requiring careful testing]
- **High Risk**: [Critical paths requiring extensive testing]

## Related Modules
- [Modules that work closely with this one]
- [Modules that might be affected by changes]

## Key Insights for Development
- [Important patterns to follow when modifying]
- [Common gotchas or pitfalls to avoid]
- [Best practices demonstrated in this module]
```

## Research Guidelines

### Context Focus
- **Current State Analysis**: Document what IS, not what SHOULD BE
- **Integration Awareness**: Pay special attention to Temporal, Slack, and LLM integrations
- **Async Pattern Recognition**: Identify proper async/await usage throughout ReflectAI
- **Cost Consciousness**: Note LLM usage patterns and cost implications

### Quality Standards
- **Specific File References**: Include exact file paths and line numbers where helpful
- **Concrete Examples**: Show actual code patterns, not generic descriptions
- **ReflectAI Context**: Always relate findings back to the ReflectAI architecture
- **Actionable Insights**: Provide information that helps with future development decisions

### Special Attention Areas
- **LLM Cost Tracking**: Any usage of LLM services and cost tracking patterns
- **Temporal Determinism**: Workflow code that must be deterministic
- **Slack Response Timing**: Code that must respond quickly to Slack events
- **Database Async Patterns**: Proper async database usage
- **Error Handling**: How errors are caught, logged, and handled

Remember: The goal is to provide comprehensive understanding that enables confident, efficient development work on this module.