# Directory Structure Validation Checklist

## Phase 1: Essential Directories (Day 1)

### Root Level
- [ ] `.backup/` - For moving old implementation
- [ ] `.kiro/specs/reflectai-fresh-implementation/` - Specifications
- [ ] `src/` - Main source code
- [ ] `config/` - Configuration files
- [ ] `tests/` - Test suite
- [ ] `docs/` - Documentation

### Core Source Structure
- [ ] `src/core/` - Core business domain
- [ ] `src/infrastructure/` - Technical infrastructure  
- [ ] `src/interfaces/` - External interfaces
- [ ] `src/services/` - Application services
- [ ] `src/shared/` - Shared utilities

### Basic Test Structure
- [ ] `tests/unit/` - Unit tests
- [ ] `tests/fixtures/` - Test data
- [ ] `tests/conftest.py` - Test configuration

### Configuration Structure
- [ ] `config/environments/` - Environment configs
- [ ] `pyproject.toml` - Poetry configuration
- [ ] `.gitignore` - Git ignore rules

## Phase 2+: Complete Structure (As Needed)

### Detailed Core Modules (Create when implementing)
- [ ] `src/core/agents/` - Multi-agent system
- [ ] `src/core/tools/` - Tool framework
- [ ] `src/core/workflows/` - Temporal workflows
- [ ] `src/core/models/` - Domain models
- [ ] `src/core/business/` - Business logic

### Infrastructure Details (Create when implementing)
- [ ] `src/infrastructure/database/` - Database layer
- [ ] `src/infrastructure/cache/` - Caching layer
- [ ] `src/infrastructure/messaging/` - Event streaming
- [ ] `src/infrastructure/monitoring/` - Observability
- [ ] `src/infrastructure/security/` - Security components

### Interface Details (Create when implementing)
- [ ] `src/interfaces/slack/` - Slack integration
- [ ] `src/interfaces/api/` - REST API
- [ ] `src/interfaces/webhooks/` - Webhook handlers

## Validation Rules

### Python Package Rules
- Each directory with Python code must have `__init__.py`
- Use snake_case for Python files
- Use clear, descriptive names

### Configuration File Rules
- Use `.yaml` extension for config files
- Use kebab-case or snake_case consistently
- Group related configs together

## Quick Validation Command

For basic validation, run:
```bash
# Check if essential directories exist
for dir in src config tests docs; do
  [ -d "$dir" ] && echo "✓ $dir exists" || echo "✗ $dir missing"
done

# Check for __init__.py in Python packages
find src -type d -name "*.py" -o -type d | while read dir; do
  if [ -d "$dir" ] && ls "$dir"/*.py 2>/dev/null | grep -q .; then
    [ -f "$dir/__init__.py" ] || echo "Missing __init__.py in $dir"
  fi
done
```

## Notes

- **Phase 1**: Focus on essential structure only
- **Phase 2+**: Add detailed subdirectories as needed
- **Don't over-engineer**: Create directories when you need them
- **Keep it simple**: This is a checklist, not a strict enforcement tool