# Claude Code Optimization Guide for ReflectAI

**Generated**: October 13, 2025
**Purpose**: Accelerate development using Claude Code features, tools, and best practices

## 🎯 Executive Summary

This guide provides actionable recommendations to leverage Claude Code's advanced features for faster, more efficient development on the ReflectAI platform.

---

## 📊 Current Status

### ✅ Already Implemented
- 13 specialized slash commands (`/test_module`, `/debug_error`, `/llm_cost_analysis`, etc.)
- Comprehensive CLAUDE.md project documentation
- `./rai` CLI tool allow-listed
- Well-structured permission system

### 🆕 Newly Added (Today)
- `/quick_test` - Fast unit test runner
- `/db_inspect` - Database inspection
- `/temporal_status` - Temporal workflow monitoring
- `/cache_status` - Redis cache monitoring
- `/llm_costs` - LLM cost tracking
- `/async_check` - Async pattern validation

---

## 🚀 High-Impact Recommendations

### 1. Install MCP Servers (Model Context Protocol)

MCP servers provide Claude with direct access to external tools and services. **Priority order:**

#### 🔴 Critical Priority

**PostgreSQL MCP Server**
```bash
# Install
git clone https://github.com/modelcontextprotocol/servers.git
cd servers/src/postgres
npm install

# Configure in ~/.config/claude/claude_desktop_config.json
{
  "mcpServers": {
    "postgres": {
      "command": "node",
      "args": ["/path/to/servers/src/postgres/index.js"],
      "env": {
        "PGHOST": "localhost",
        "PGPORT": "5432",
        "PGUSER": "reflectai",
        "PGPASSWORD": "devpassword",
        "PGDATABASE": "reflectai"
      }
    }
  }
}
```

**Benefits:**
- Natural language database queries: "Show me all users with competency level > 4"
- Schema inspection without manual SQL
- Automatic query optimization suggestions

**GitHub MCP Server**
```bash
# Install via Claude CLI
claude mcp add --transport http github https://api.githubcopilot.com/mcp/

# Authenticate
claude mcp auth github
```

**Benefits:**
- Automatic PR reviews with ReflectAI patterns
- Issue analysis and linking
- Commit history analysis

#### 🟡 High Priority

**Filesystem MCP Server**
```bash
cd servers/src/filesystem
npm install

# Add to config
{
  "mcpServers": {
    "filesystem": {
      "command": "node",
      "args": ["/path/to/servers/src/filesystem/index.js"],
      "env": {
        "ALLOWED_DIRECTORIES": "/Users/mshaikh/CascadeProjects/reflectai-platform"
      }
    }
  }
}
```

**Sequential Thinking MCP Server**
```bash
npm install -g @modelcontextprotocol/server-sequential-thinking

# Add to config
{
  "mcpServers": {
    "sequential-thinking": {
      "command": "mcp-server-sequential-thinking"
    }
  }
}
```

**Benefits:**
- Break down complex Temporal workflows
- Step-by-step debugging
- Better architectural planning

#### 🟢 Medium Priority

**Memory Bank MCP Server** - Maintains context across sessions
**Brave Search MCP Server** - Research external APIs and patterns

---

### 2. Configure Development Hooks

Add to `.claude/settings.local.json`:

```json
{
  "permissions": {
    "allow": ["...existing permissions..."]
  },
  "hooks": [
    {
      "name": "Auto-lint Python files",
      "event": "PostToolUse",
      "matcher": {
        "tool": "Edit",
        "path": "src/**/*.py"
      },
      "command": "./rai check lint $FILE_PATH"
    },
    {
      "name": "Auto-run test after editing",
      "event": "PostToolUse",
      "matcher": {
        "tool": "Edit",
        "path": "tests/**/*.py"
      },
      "command": "pdm run pytest $FILE_PATH -v --tb=short -x"
    },
    {
      "name": "Format code on session end",
      "event": "Stop",
      "command": "./rai check format"
    },
    {
      "name": "Quick test before commits",
      "event": "UserPromptSubmit",
      "matcher": {
        "prompt_contains": ["commit", "create PR", "push"]
      },
      "command": "./rai test unit -m 'not slow' --exitfirst"
    },
    {
      "name": "Type check critical files",
      "event": "PostToolUse",
      "matcher": {
        "tool": "Edit",
        "path": [
          "src/core/llm/**/*.py",
          "src/services/workflow/**/*.py",
          "src/interfaces/slack/**/*.py"
        ]
      },
      "command": "./rai check type $FILE_PATH"
    },
    {
      "name": "Notify on long operations",
      "event": "Stop",
      "command": "osascript -e 'display notification \"Claude Code task completed\" with title \"ReflectAI\"'"
    }
  ],
  "outputStyle": "default"
}
```

**Hook Benefits:**
- ✅ Automatic code quality checks
- ✅ Faster feedback loops
- ✅ Prevent committing broken code
- ✅ Desktop notifications for long tasks

---

### 3. Optimize CLAUDE.md Files

**Current:** Single `CLAUDE.md` (3000+ lines)
**Recommended:** Modular per-folder approach

Create focused context files:

```bash
# Core LLM context
.claude/contexts/llm.md

# Temporal workflow patterns
.claude/contexts/temporal.md

# Slack integration specifics
.claude/contexts/slack.md

# Database and storage
.claude/contexts/database.md

# Testing strategies
.claude/contexts/testing.md
```

**In main CLAUDE.md**, add:
```markdown
## Additional Context
- LLM Gateway: See `.claude/contexts/llm.md`
- Temporal Workflows: See `.claude/contexts/temporal.md`
- Slack Integration: See `.claude/contexts/slack.md`
- Database Patterns: See `.claude/contexts/database.md`
- Testing: See `.claude/contexts/testing.md`
```

**Benefits:**
- Reduced token usage (150-200 line limit per file)
- Faster context loading
- More focused AI responses

---

### 4. Enhanced Workflow Patterns

#### Pattern 1: Test-Driven Development Flow
```bash
# 1. Create test first
/quick_test tests/unit/core/llm/test_new_feature.py

# 2. Implement feature
[Claude implements based on failing test]

# 3. Validate
/quick_test tests/unit/core/llm/test_new_feature.py

# 4. Check coverage
/fix_coverage src/core/llm/
```

#### Pattern 2: Database-First Development
```bash
# 1. Inspect current schema
/db_inspect

# 2. Design new models
[Claude creates Pydantic models]

# 3. Create migration
./rai db migrate

# 4. Test with natural language queries (MCP)
"Show me the new competency_scores table structure"
```

#### Pattern 3: Temporal Workflow Development
```bash
# 1. Check current workflow health
/temporal_status

# 2. Research existing patterns
/research_module src/services/workflow/

# 3. Implement new workflow
[Claude develops workflow.py and activities.py]

# 4. Validate determinism
/validate_async src/services/workflow/
```

#### Pattern 4: Performance Optimization
```bash
# 1. Check LLM costs
/llm_costs

# 2. Identify expensive operations
[Analyze results]

# 3. Check cache status
/cache_status

# 4. Optimize with caching
[Claude adds Redis caching]

# 5. Verify improvement
/llm_costs
```

---

### 5. Best Practices from Research

#### Context Management
- **Use `/clear` frequently** - Start each new task with a clean context
- **Be specific** - "Add caching to the competency assessment workflow" vs "improve performance"
- **Provide examples** - Show existing patterns you want to follow

#### Prompt Engineering
- **Use thinking modes** - "Think through the architecture first, then implement"
- **Request validation** - "After implementing, create tests and validate async patterns"
- **Iterate incrementally** - Small PRs > big bang changes

#### Quality Assurance
- **Always specify coverage** - "/fix_coverage should reach 85%+"
- **Test before committing** - Use hooks or explicit commands
- **Review with subagents** - "/review_pr for architectural patterns"

#### Async Development (Critical for ReflectAI)
- **Use `/async_check`** before committing any I/O code
- **Validate blocking calls** - Check for `requests.*` without async
- **Test with async fixtures** - Use `pytest-asyncio` patterns

---

## 🛠️ Tool-Specific Optimizations

### For LLM Gateway Development
```bash
# Quick validation workflow
/research_module src/core/llm/gateway.py
/async_check src/core/llm/
/llm_costs
/test_module src/core/llm/
```

### For Temporal Workflow Development
```bash
# Workflow health check
/temporal_status
/validate_async src/services/workflow/
/test_module src/services/workflow/ --temporal
```

### For Slack Integration
```bash
# Integration testing
/research_module src/interfaces/slack/
/async_check src/interfaces/slack/
/test_module src/interfaces/slack/
```

### For Database Changes
```bash
# Schema evolution
/db_inspect
[Make changes]
./rai db migrate
/test_module tests/integration/database/
```

---

## 📈 Productivity Metrics to Track

After implementing these optimizations, track:

1. **Development Velocity**
   - Time from feature request to PR
   - Number of iterations before passing CI/CD
   - Bug discovery rate (earlier = better)

2. **Code Quality**
   - Test coverage percentage (target: 85%+)
   - Linting errors per commit
   - Type checking pass rate

3. **AI Efficiency**
   - Context switches per session (should decrease)
   - Questions asked per feature (should decrease)
   - Successful first-time implementations (should increase)

---

## 🔧 Implementation Checklist

### Week 1: Foundation
- [ ] Install PostgreSQL MCP Server
- [ ] Install GitHub MCP Server
- [ ] Configure basic hooks (linting, formatting)
- [ ] Test new slash commands

### Week 2: Optimization
- [ ] Add Filesystem MCP Server
- [ ] Add Sequential Thinking MCP Server
- [ ] Split CLAUDE.md into modular contexts
- [ ] Create workflow-specific documentation

### Week 3: Advanced Features
- [ ] Configure advanced hooks (pre-commit tests)
- [ ] Add Memory Bank MCP Server
- [ ] Create team workflow guidelines
- [ ] Train team on new slash commands

---

## 🎓 Learning Resources

### Official Documentation
- [Claude Code Best Practices](https://www.anthropic.com/engineering/claude-code-best-practices)
- [MCP Protocol Documentation](https://docs.claude.com/en/docs/claude-code/mcp)
- [Slash Commands Guide](https://docs.claude.com/en/docs/claude-code/slash-commands)
- [Hooks Guide](https://docs.claude.com/en/docs/claude-code/hooks-guide)

### Community Resources
- [Awesome Claude Code](https://github.com/hesreallyhim/awesome-claude-code)
- [MCP Servers Repository](https://github.com/modelcontextprotocol/servers)
- [Claude Code Cheatsheet](https://shipyard.build/blog/claude-code-cheat-sheet/)

### ReflectAI-Specific
- Project README.md
- CLAUDE.md (main project context)
- `.claude/commands/` (all slash commands)
- This guide!

---

## 🚨 Common Pitfalls to Avoid

1. **Don't overload context** - Split large CLAUDE.md files
2. **Don't skip hooks** - Even if they slow you down initially
3. **Don't ignore MCP servers** - They're game-changers for productivity
4. **Don't forget `/clear`** - Old context causes confused responses
5. **Don't batch commits** - Small, focused commits with tests
6. **Don't skip async validation** - ReflectAI is async-first

---

## 📞 Getting Help

- **Claude Code Issues**: [GitHub Issues](https://github.com/anthropics/claude-code/issues)
- **MCP Problems**: Check MCP server logs and configuration
- **ReflectAI Questions**: Use `/research_module` to understand existing code
- **Workflow Confusion**: Use `/create_plan` before implementing

---

## 🎯 Success Metrics

After implementing these recommendations, you should see:

- **50% faster feature development** - Better context, fewer iterations
- **30% fewer bugs** - Automatic testing and validation
- **80%+ test coverage** - Enforced by hooks and commands
- **Reduced context switching** - MCP servers provide direct access
- **Better code quality** - Automated checks catch issues early

---

## 📝 Changelog

- **2025-10-13**: Initial guide created
  - Added 6 new slash commands
  - Documented MCP server recommendations
  - Created hook configuration examples
  - Added workflow patterns

---

*This guide is a living document. Update it as you discover new patterns and optimizations!*
