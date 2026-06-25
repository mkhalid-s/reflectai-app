# ReflectAI Developer Guide

## 🚀 Quick Start

### First Time Setup
```bash
# Clone the repository
git clone https://github.com/your-org/reflectai-platform
cd reflectai-platform

# Run complete setup (installs deps, sets up DB, Redis, secrets)
./rai setup all

# Start the application
./rai run app
```

That's it! You're ready to develop.

## 📚 Table of Contents

1. [Development CLI](#development-cli)
2. [Common Tasks](#common-tasks)
3. [Environment Setup](#environment-setup)
4. [Testing](#testing)
5. [Code Quality](#code-quality)
6. [Database Operations](#database-operations)
7. [Docker Development](#docker-development)
8. [Troubleshooting](#troubleshooting)

## 🎮 Development CLI

All development tasks are managed through the `./rai` CLI tool. This is your single entry point for everything.

### Getting Help
```bash
./rai help              # Show all available commands
./rai version          # Show version information
```

### Command Structure
```
./rai <command> [subcommand] [options]
```

## 🔧 Common Tasks

### Daily Development Workflow

#### 1. Start Your Day
```bash
# Pull latest changes
git pull

# Update dependencies if needed
./rai setup deps

# Run migrations if any
./rai db migrate

# Start the app
./rai run app
```

#### 2. Before Committing Code
```bash
# Run all quality checks
./rai check

# Run tests
./rai test

# Fix any issues
./rai check format    # Auto-format code
./rai check lint      # Fix linting issues
```

#### 3. Clean Up
```bash
# Clean cache and temporary files
./rai clean cache

# Stop Docker containers
./rai clean docker
```

## 🛠 Environment Setup

### Initial Setup
```bash
# Complete setup for new developers
./rai setup all
```

This command will:
1. Install Python dependencies
2. Setup PostgreSQL database
3. Setup Redis
4. Configure environment variables
5. Install pre-commit hooks

### Individual Setup Commands
```bash
./rai setup deps       # Install Python dependencies only
./rai setup db         # Setup PostgreSQL only
./rai setup redis      # Setup Redis only
./rai setup secrets    # Configure .env file only
```

### Environment Variables

The `.env` file contains all configuration. It's created automatically from `.env.example`:

```env
# Core Settings
ENVIRONMENT=development
DEBUG=true

# Database
DATABASE_URL=postgresql://reflectai:reflectai@localhost:5432/reflectai

# Redis
REDIS_URL=redis://localhost:6379

# Slack (get from Slack App settings)
SLACK_BOT_TOKEN=xoxb-...
SLACK_APP_TOKEN=xapp-...
SLACK_SIGNING_SECRET=...

# OpenAI (optional)
OPENAI_API_KEY=sk-...
```

## 🧪 Testing

### Run All Tests
```bash
./rai test                # Run all tests
./rai test-unit          # Run unit tests only
./rai test-coverage      # Run with coverage report
```

### Test Coverage
After running tests with coverage:
- Terminal report shows immediately
- HTML report available at `htmlcov/index.html`

### Writing Tests
Tests are located in the `tests/` directory:
```
tests/
├── unit/           # Unit tests
├── integration/    # Integration tests
└── fixtures/       # Test data
```

## 🎯 Code Quality

### Run All Checks
```bash
./rai check              # Run all quality checks
```

### Individual Checks
```bash
./rai check lint         # Run linter (Ruff)
./rai check format       # Format code (Ruff formatter)
./rai check type         # Type checking (MyPy)
./rai check security     # Security scan (Bandit + Safety)
```

### Pre-commit Hooks
Pre-commit hooks run automatically before each commit. To run manually:
```bash
pre-commit run --all-files
```

## 💾 Database Operations

### Migrations
```bash
./rai db migrate         # Run pending migrations
./rai db reset          # Reset database (WARNING: deletes all data!)
./rai db seed           # Seed with test data
```

### Database Access
```bash
# Connect to PostgreSQL
psql postgresql://reflectai:reflectai@localhost:5432/reflectai

# Connect to Redis
redis-cli
```

## 🐳 Docker Development

### Run in Docker
```bash
./rai run docker        # Start all services in Docker
```

### Docker Compose Commands
```bash
docker-compose up       # Start all services
docker-compose down     # Stop all services
docker-compose logs -f  # View logs
docker-compose ps       # List running containers
```

### Clean Docker Resources
```bash
./rai clean docker      # Stop and remove containers
```

## 🔍 Troubleshooting

### Common Issues

#### Port Already in Use
```bash
# Find process using port 8000
lsof -i :8000

# Kill the process
kill -9 <PID>
```

#### Database Connection Failed
```bash
# Check if PostgreSQL is running
docker ps | grep postgres

# Restart PostgreSQL
docker restart reflectai-postgres

# Check connection
psql postgresql://reflectai:reflectai@localhost:5432/reflectai
```

#### Redis Connection Failed
```bash
# Check if Redis is running
docker ps | grep redis

# Restart Redis
docker restart reflectai-redis

# Test connection
redis-cli ping
```

#### Dependencies Out of Sync
```bash
# Update all dependencies
./rai setup deps

# If using PDM
pdm sync

# If using pip
pip install -r requirements.txt
```

#### Clean Start
```bash
# Nuclear option - clean everything and start fresh
./rai clean
./rai setup all
```

## 📝 Project Structure

```
reflectai-platform/
├── src/                    # Source code
│   ├── app.py             # FastAPI application
│   ├── main.py            # Application entry point
│   ├── core/              # Core business logic
│   ├── interfaces/        # External interfaces (Slack, etc.)
│   ├── infrastructure/    # Database, cache, etc.
│   └── services/          # Business services
│
├── tests/                  # Test files
│   ├── unit/              # Unit tests
│   └── integration/       # Integration tests
│
├── scripts/               # Development scripts (being phased out)
├── config/                # Configuration files
├── docs/                  # Documentation
│
├── dev                    # Unified development CLI (THIS IS THE MAIN TOOL!)
├── Makefile              # Legacy support (calls ./rai)
├── docker-compose.yml    # Docker development setup
├── pyproject.toml        # Python project configuration
├── .env.example          # Environment variables template
└── .env                  # Local environment variables (git-ignored)
```

## 🎓 Best Practices

### 1. Always Use the CLI
Don't run Python scripts directly. Use `./rai` commands:
- ❌ `python src/main.py`
- ✅ `./rai run app`

### 2. Check Before Commit
Always run checks before committing:
```bash
./rai check
./rai test
```

### 3. Keep Dependencies Updated
Regularly update dependencies:
```bash
./rai setup deps
```

### 4. Use Virtual Environments
The project uses PDM/venv automatically. Don't install packages globally.

### 5. Document Your Changes
- Update this guide if you add new dev commands
- Add docstrings to your code
- Update README.md for user-facing changes

## 🚧 Migration from Old Scripts

If you're used to the old scattered scripts, here's the mapping:

| Old Command | New Command |
|------------|------------|
| `python scripts/dev.py install` | `./rai setup deps` |
| `scripts/setup_local_db.sh` | `./rai setup db` |
| `scripts/setup_redis_dev.py` | `./rai setup redis` |
| `make lint` | `./rai check lint` |
| `make test` | `./rai test` |
| `docker-compose up` | `./rai run docker` |
| `python scripts/validate_system.py` | `./rai check` |

## 💡 Pro Tips

1. **Tab Completion**: Add to your shell:
   ```bash
   # Add to ~/.bashrc or ~/.zshrc
   alias d='./rai'
   ```

2. **Watch Mode**: For continuous testing:
   ```bash
   watch -n 2 './rai test unit'
   ```

3. **Quick Checks**: Before pushing:
   ```bash
   ./rai check && ./rai test && git push
   ```

4. **Environment Info**: Check your setup:
   ```bash
   ./rai version
   ```

## 🆘 Getting Help

1. **CLI Help**: `./rai help`
2. **Documentation**: This file and `/docs` directory
3. **Team Chat**: Post in #reflectai-dev channel
4. **Issues**: Create a GitHub issue

---

Happy coding! 🚀 Remember: When in doubt, run `./rai help`