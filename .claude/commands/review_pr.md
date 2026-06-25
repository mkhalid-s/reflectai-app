---
description: Analyze uncommitted changes, run quality checks, validate ReflectAI patterns, and generate PR description
---

# Review Pull Request - Prepare Changes for PR

Analyze current uncommitted changes and prepare for pull request submission.

## PR Review Process

### Step 1: Change Analysis (2 minutes)
1. **Run git status** - Identify all uncommitted changes
2. **Run git diff** - Analyze actual code changes
3. **Identify affected modules** - Core, services, interfaces, infrastructure
4. **Check for untracked files** - Ensure nothing important is missing
5. **Review commit history** - Check for unpushed commits

### Step 2: Quality Checks (3-5 minutes)
1. **Run linting** - `./rai check lint` for code quality
2. **Run type checking** - `./rai check type` with mypy
3. **Run security scan** - `./rai check security` with bandit
4. **Run tests** - `./rai test` with coverage analysis
5. **Check test coverage** - Ensure 80%+ coverage maintained

### Step 3: ReflectAI-Specific Validation (2-3 minutes)
1. **Async pattern check** - Verify all I/O operations use async/await
2. **Error handling** - Ensure proper use of `src.shared.exceptions`
3. **LLM cost tracking** - Verify cost tracking for all LLM calls
4. **Temporal determinism** - Check workflow code for non-deterministic operations
5. **Slack response timing** - Verify 3-second response requirement met
6. **Database patterns** - Check async SQLAlchemy usage
7. **Logging patterns** - Verify correlation IDs and structured logging

### Step 4: Impact Analysis (2 minutes)
1. **Performance impact** - Identify potential performance implications
2. **Breaking changes** - List any breaking API changes
3. **Database migrations** - Check if migrations are needed
4. **Configuration changes** - Note any new environment variables
5. **Dependency changes** - List added/updated/removed dependencies
6. **Cost implications** - Assess LLM usage cost impact

### Step 5: PR Description Generation (2 minutes)
1. **Summarize changes** - High-level summary of what changed
2. **Group by category** - Feature, fix, refactor, docs, test
3. **List affected files** - Key files modified
4. **Create test plan** - How to test the changes
5. **Note breaking changes** - Highlight any breaking changes
6. **Document risks** - List potential risks or concerns

## ReflectAI PR Standards

### Commit & PR Message Requirements
**CRITICAL - MUST FOLLOW**:
- ❌ **NO "Claude Code" references**
- ❌ **NO "Claude" mentions**
- ❌ **NO AI generation tags or footers**
- ❌ **NO "Co-Authored-By: Claude" lines**
- ❌ **NO "Generated with" statements**
- ✅ **Professional, concise messages**
- ✅ **Short and precise descriptions**
- ✅ **Conventional Commits format**

### Commit Message Format
Follow Conventional Commits specification:
```
<type>: <short description>

<concise body - 3-5 bullet points max>
- Key change 1
- Key change 2
- Key change 3

Impact: <one-line summary>
Files: <count> changed, <+/-> lines
```

Types: feat, fix, refactor, docs, test, chore, perf, ci

### PR Checklist
- [ ] All tests passing
- [ ] Coverage >80%
- [ ] Linting passed
- [ ] Type checking passed
- [ ] Security scan clean
- [ ] Documentation updated
- [ ] Breaking changes documented
- [ ] Configuration changes documented
- [ ] Performance impact assessed
- [ ] Manual testing completed

### Critical Checks
- [ ] Async patterns validated
- [ ] Error handling uses `src.shared.exceptions`
- [ ] LLM calls track costs
- [ ] Temporal workflows are deterministic
- [ ] Slack responses <3 seconds
- [ ] Database operations are async
- [ ] Logging includes correlation IDs

## Example Output

```markdown
# Pull Request Review

## Summary
Analyzed X files with Y changes across Z modules

### Quality Status
✅ Linting: Passed
✅ Type Checking: Passed
⚠️  Security: 1 issue found (details below)
✅ Tests: 145/145 passed (92% coverage)

### ReflectAI Compliance
✅ Async patterns validated
✅ Error handling compliant
⚠️  Temporal: 1 determinism issue (line 145)
✅ Database patterns correct

## Suggested PR Title
feat: add LLM streaming support with connection leak fix

## Suggested PR Description
Summary of changes, test plan, and impact analysis...
(NO AI references, professional and concise)

## Action Items
- [ ] Fix security issue in src/[file].py:45
- [ ] Fix Temporal determinism in src/[file].py:145
- [ ] Complete manual testing
```

**Remember**:
- A good PR review catches issues before they reach production
- All commit messages and PR descriptions must be professional and AI-brand free
