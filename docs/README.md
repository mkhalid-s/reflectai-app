# ReflectAI Platform Documentation

Welcome to the ReflectAI platform documentation. This directory contains all technical documentation, guides, and analysis reports.

## 📚 Documentation Structure

**Current**: 16 active documentation files (streamlined from 33)

```
docs/
├── architecture/          # System architecture (4 files)
│   ├── SYSTEM_ARCHITECTURE.md  # ⭐ Complete system design (2,375 lines, ALL details)
│   ├── SLACK_INTEGRATION_ARCHITECTURE.md  # Slack-specific patterns
│   ├── MULTI_AGENT_SYSTEM.md              # AI agent orchestration
│   └── MODEL_SPECIFICATION.md             # Domain models
├── classification/        # Classification v2.0 design (2 files, not yet implemented)
│   ├── README.md                   # Executive summary
│   └── ARCHITECTURE_DESIGN.md      # Complete v2.0 specification
├── cli/                   # CLI documentation (1 file)
│   └── RAI_CLI_GUIDE.md           # 209-command reference
├── development/           # Developer guides (2 files)
│   ├── DEVELOPER_GUIDE.md         # Primary dev reference
│   └── API_DOCUMENTATION.md       # API endpoints
├── deployment/            # Deployment & operations (3 files)
│   ├── DEPLOYMENT_GUIDE.md        # Deployment procedures
│   ├── OPERATIONS_MANUAL.md       # Daily operations
│   └── MONITORING.md              # Observability setup
├── security/              # Security (1 file)
│   └── SECURITY_GUIDE.md
├── archive/               # Archived documentation (10+ files)
│   ├── README.md                  # Archive inventory
│   ├── OVERVIEW.md, TECHNOLOGY_STACK.md, ENTERPRISE_ARCH.md
│   ├── CONVENTIONAL_COMMITS_GUIDE.md, INTENT_SYSTEM_IMPROVEMENTS.md
│   ├── QUICK_REFERENCE.md
│   └── classification-design/ (4 supporting design files)
├── README.md              # This file (documentation index)
├── REDIS_MIGRATION_GUIDE.md  # ⭐ Complete Redis 8 migration guide (1,704 lines)
└── VERSION_MANAGEMENT.md     # Version control procedures
```

## 🚀 Quick Start Guides

### For Developers Getting Started
1. **[Development Guide](./development/DEVELOPER_GUIDE.md)** - Start here
2. **[API Documentation](./development/API_DOCUMENTATION.md)** - API reference
3. **[RAI CLI Guide](./cli/RAI_CLI_GUIDE.md)** - CLI reference

### For Understanding the System
1. **[System Architecture](./architecture/SYSTEM_ARCHITECTURE.md)** - ⭐ Complete system design
2. **[Slack Integration Architecture](./architecture/SLACK_INTEGRATION_ARCHITECTURE.md)** - Slack integration design
3. **[Multi-Agent System](./architecture/MULTI_AGENT_SYSTEM.md)** - AI agent orchestration

### For CLI Management
1. **[RAI CLI Guide](./cli/RAI_CLI_GUIDE.md)** - Complete CLI reference with 209 commands

### For Deployment
1. **[Deployment Guide](./deployment/DEPLOYMENT_GUIDE.md)** - How to deploy
2. **[Operations Manual](./deployment/OPERATIONS_MANUAL.md)** - Day-to-day ops
3. **[Monitoring](./deployment/MONITORING.md)** - Monitoring setup

## 📖 Key Documents

### Current Status (November 2025)

**Version**: 0.1.2-alpha
**Application Status**: Active Development
**Python**: 3.11-3.12 required
**Documentation Status**: Recently consolidated (Nov 23, 2025)

### Architecture
- **[System Architecture](./architecture/SYSTEM_ARCHITECTURE.md)** - ⭐ Complete platform design (2,375 lines)
  - All layers, components, data flows with detailed diagrams
  - Event deduplication, conversation context, competency management
  - Gap analysis, report workflows, Temporal orchestration
  - LLM Gateway (EnterpriseGateway, OpenAI, Anthropic via LiteLLM)
  - **Replaces**: OVERVIEW.md, TECHNOLOGY_STACK.md, ENTERPRISE_ARCH.md (now archived)
- [Slack Integration Architecture](./architecture/SLACK_INTEGRATION_ARCHITECTURE.md) - Slack-specific patterns
- [Multi-Agent System](./architecture/MULTI_AGENT_SYSTEM.md) - AI agent orchestration
- [Model Specification](./architecture/MODEL_SPECIFICATION.md) - Domain data models

### Redis 8 Migration
- **[Redis Migration Guide](./REDIS_MIGRATION_GUIDE.md)** - ⭐ Complete migration guide (1,704 lines)
  - All procedures, diagrams, troubleshooting, scripts
  - **Replaces**: 3 separate migration docs (now deleted)

### Classification System v2.0 (Design Phase)
- [Classification README](./classification/README.md) - 3-tier architecture overview
- [Architecture Design](./classification/ARCHITECTURE_DESIGN.md) - Complete v2.0 specification
- **Status**: Design complete, implementation pending
- **Note**: 4 supporting design files archived to archive/classification-design/

### Development
- [Developer Guide](./development/DEVELOPER_GUIDE.md)
- [API Documentation](./development/API_DOCUMENTATION.md)

### CLI Tool
- [RAI CLI Guide](./cli/RAI_CLI_GUIDE.md) - Complete 209-command reference

### Version Management & Git
- [Version Management](./VERSION_MANAGEMENT.md) - Version control and bumping
- [Conventional Commits Guide](./archive/CONVENTIONAL_COMMITS_GUIDE.md) - Commit message standards (archived)

### Other Guides
- [Security Guide](./security/SECURITY_GUIDE.md)

## 🔍 Finding What You Need

### "I want to use the CLI tool"
→ Start with [RAI CLI Guide](./cli/RAI_CLI_GUIDE.md)

### "I want to understand the codebase"
→ Start with [System Architecture](./architecture/SYSTEM_ARCHITECTURE.md) for complete system design, or [Developer Guide](./development/DEVELOPER_GUIDE.md) for development setup

### "I want to contribute code"
→ Start with [Developer Guide](./development/DEVELOPER_GUIDE.md)

### "I want to deploy the application"
→ Start with [Deployment Guide](./deployment/DEPLOYMENT_GUIDE.md)

### "I want to understand the architecture"
→ Start with [System Architecture](./architecture/SYSTEM_ARCHITECTURE.md) for comprehensive diagrams and complete platform details

### "I want to use the API"
→ Start with [API Documentation](./development/API_DOCUMENTATION.md)

### "I need to migrate Redis to v8"
→ Start with [Redis Migration Guide](./REDIS_MIGRATION_GUIDE.md) for complete migration procedures

## 📊 Current State Summary

**Version**: 0.1.2-alpha
**Status**: Active Development
**Python**: 3.11-3.12 required
**CLI Tool**: RAI with 209 commands (100% complete)

### What Works
- ✅ Excellent architecture and design patterns
- ✅ Sophisticated competency assessment algorithms
- ✅ Complete LLM gateway with multi-provider support
- ✅ Comprehensive database layer with TimescaleDB
- ✅ Event system and monitoring
- ✅ Temporal workflow orchestration
- ✅ Slack integration with socket mode
- ✅ Comprehensive CLI tool (RAI) for all operations

### Key Features
- 🚀 FastAPI async backend
- 🐘 PostgreSQL + TimescaleDB
- 🔴 Redis caching
- ⏰ Temporal workflow engine
- 💬 Slack integration
- 🤖 Multi-provider LLM gateway
- 🔧 209-command CLI tool

## 🛠️ Contributing to Documentation

When adding new documentation:

1. Choose the appropriate directory:
   - `architecture/` - Design and architecture docs
   - `cli/` - CLI tool documentation
   - `development/` - Developer guides and references
   - `deployment/` - Deployment and ops guides
   - `security/` - Security-related docs
   - `archive/` - Archived/historical documentation

2. Follow the naming convention:
   - Use UPPER_CASE for important docs
   - Use descriptive names
   - Add `.md` extension

3. Update this README.md with links

4. Update last modified date at bottom

## 📝 Documentation Standards

- Use Markdown format
- Include table of contents for long documents
- Add last updated date at the bottom
- Use emoji for visual categorization (optional)
- Keep documents focused and single-purpose
- Link to related documents

## 🔗 External Resources

- [Project Repository](https://github.com/your-org/reflectai-platform)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Temporal Documentation](https://docs.temporal.io/)
- [Slack API Documentation](https://api.slack.com/)

---

## 📦 Aggressive Documentation Cleanup (November 23, 2025)

**What Changed:**
- ✅ Consolidated Redis docs (**7 → 1 file**, single comprehensive guide)
- ✅ Created SYSTEM_ARCHITECTURE.md (2,375 lines with ALL platform details)
- ✅ Archived **10 docs**: completed work plans, generic guides, superseded architecture docs
- ✅ Consolidated classification docs (**6 → 2 files**)
- ✅ Archived 4 supporting classification design files
- ✅ Fixed all CLI references (./dev → ./rai)

**Result:**
- **33 files → 16 active files** (52% reduction)
- **Removed ~240KB of redundancy and outdated content**
- Single source of truth for architecture (SYSTEM_ARCHITECTURE.md)
- Single source of truth for Redis migration (REDIS_MIGRATION_GUIDE.md)
- Clean archive system (10 archived docs with clear inventory)
- All critical implementation details verified and documented

---

*Last Updated: November 23, 2025*
*Documentation Version: 5.0* (Aggressively streamlined: 33 → 16 active files, comprehensive architecture)
