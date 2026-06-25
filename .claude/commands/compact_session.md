---
description: Perform context compaction to optimize AI development session efficiency and preserve development state
---

# Context Compaction for ReflectAI Development

Perform context compaction to optimize AI development session efficiency.

## When to Use This Command

### Automatic Triggers (Use When Any Apply)
- **Context feels "heavy"** - responses are getting less accurate or unfocused
- **After 3-4 file modifications** - prevent context pollution
- **Context usage >60%** - maintain optimal 40-60% range
- **Before module switching** - when moving between core/, services/, interfaces/
- **Session duration >45 minutes** - regular maintenance
- **Before starting tests** - clean context for test implementation
- **When taking breaks** - preserve state for later resumption

### Manual Triggers
- **Error rate increasing** - responses are becoming less helpful
- **Off-topic responses** - AI is bringing in irrelevant context
- **Slow response times** - context processing is taking longer
- **Complex task completion** - finished a major implementation milestone

## Compaction Process

### Step 1: Session Summary
1. **What was accomplished** in the current session
2. **Files modified** with brief descriptions of changes
3. **Current task status** - what's completed vs in-progress
4. **Key decisions made** during implementation
5. **Important insights discovered** while working

### Step 2: Context Preservation
1. **Critical findings** that must not be lost
2. **Active debugging information** if troubleshooting issues
3. **Incomplete work details** - exactly where you left off
4. **Dependencies identified** during the session
5. **Test requirements** discovered or planned

### Step 3: State Management
1. **Git branch status** - current branch and uncommitted changes
2. **Development server state** - what's running, what needs restart
3. **Next immediate action** - specific next step to take
4. **Blockers or questions** - issues that need resolution
5. **Context for handoff** - what someone else would need to know

## Output Format

```markdown
# 🔄 Session Compaction: [DATE] [TIME]

## ✅ Completed This Session
- **[Task/Feature]**: [Brief description] - Modified: `[file_paths]`
- **[Task/Feature]**: [Brief description] - Modified: `[file_paths]`
- **[Task/Feature]**: [Brief description] - Modified: `[file_paths]`

## 🔍 Key Insights Discovered
- **[Finding 1]**: [Why this matters for ReflectAI development]
- **[Decision Made]**: [Rationale and impact]
- **[Technical Discovery]**: [How this affects future work]

## 📁 Current State
- **Active Branch**: `[git_branch_name]`
- **Modified Files**:
  - `[file_path]`: [What changed and why]
  - `[file_path]`: [What changed and why]
- **Development Server**: [Running/Stopped - any issues?]
- **Tests Status**: [Passing/Failing - which ones?]

## 🎯 Immediate Next Action
**[Specific next step to take when resuming work]**

## 🚧 In Progress / Incomplete
- **[Task Name]**: [Current status and what's left to do]
- **[Blocker/Question]**: [What needs to be resolved]

## 🔗 Dependencies & Integration Points
- **Database changes**: [Any schema or data changes made/needed]
- **LLM integration**: [Provider changes or cost implications]
- **Slack integration**: [Event handling or API changes]
- **Temporal workflows**: [Workflow or activity modifications]

## 📋 Context for Next Session
[2-3 sentences describing the current state and what to resume with. Include any important mental context that would be lost otherwise.]

## 🧪 Testing Requirements
- **Tests to run**: `[specific test commands or files]`
- **Test scenarios to add**: [What needs testing that doesn't exist yet]
- **Integration testing**: [Any external service testing needed]

## 💡 Notes for Future Development
- **Patterns observed**: [Code patterns that worked well or should be avoided]
- **Performance considerations**: [Any performance implications discovered]
- **Security considerations**: [Any security-related findings or needs]

---
*Context freed: Estimated [XX]% context capacity regained*
*Next session restore: Use `/resume_session` with this summary*
```

## Context Management Guidelines

### Before Compaction
1. **Save any unsaved work** - commit or stash changes appropriately
2. **Document current debugging state** - error messages, stack traces, etc.
3. **Note current mental model** - your understanding of what you're building
4. **Record test results** - what's passing, what's failing, what needs testing

### After Compaction
1. **Context is reset** - start fresh with clean context window
2. **Use the summary** - reference the compaction output for continuation
3. **Restore minimal context** - only load what's needed for immediate work
4. **Verify current state** - check git status, running services, test status

## ReflectAI-Specific Compaction Notes

### Critical Context to Preserve
- **LLM Cost Tracking**: Any budget implications or cost considerations discovered
- **Temporal Workflow State**: Deterministic requirements or workflow modifications
- **Slack Integration Timing**: Response timing requirements or threading needs
- **Database Async Patterns**: Async/await patterns that worked or caused issues
- **Development Server State**: Which services are running and their health

### Integration Awareness
- **External Service Health**: Note any issues with PostgreSQL, Redis, LLM providers
- **Configuration Changes**: Environment variables or settings modified
- **API Endpoint Changes**: Any FastAPI route modifications or additions
- **Error Handling Updates**: New error scenarios discovered or handled

### Performance Context
- **Response Time Observations**: Any performance issues or improvements noted
- **Resource Usage**: Memory, CPU, or network usage patterns observed
- **Cache Effectiveness**: Redis caching patterns that worked or didn't work
- **Database Query Efficiency**: Query performance observations

## Success Metrics
- **Context efficiency restored** to 40-60% range
- **Response quality improved** after compaction
- **Session continuity maintained** - can resume effectively
- **No critical information lost** - all important state preserved

Remember: The goal is to maintain optimal AI performance while preserving all critical development context. Frequent intentional compaction is key to sustained productivity in AI-assisted development.