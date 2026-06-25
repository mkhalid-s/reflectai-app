# Version Management

## Overview

ReflectAI uses a centralized version management system where **pyproject.toml** is the single source of truth for version numbers. The system automatically includes git commit information for traceability.

## Architecture

```
pyproject.toml (version = "0.1.2-alpha")
         ↓
    src/version.py (reads and enriches)
         ↓
    ┌────┴────┬─────────────┬──────────────┐
    ↓         ↓             ↓              ↓
src/__init__ config_manager  FastAPI app   ./rai CLI
```

## Version Format

### Standard Format
- **Base Version**: `0.1.2-alpha` (from pyproject.toml)
- **Full Version**: `0.1.2-alpha+c6782b3` (with git commit)
- **Dirty Version**: `0.1.2-alpha+c6782b3.dirty` (uncommitted changes)

### Semantic Versioning
We follow [Semantic Versioning](https://semver.org/):
- `MAJOR.MINOR.PATCH[-PRERELEASE]`
- Example: `0.1.2-alpha`, `1.0.0`, `1.2.3-beta`

## Usage

### Command Line

Check version information using the unified dev CLI:

```bash
# Full version information (default)
./rai version

# Version number only
./rai version --short
# Output: 0.1.2-alpha

# Full version with git commit
./rai version --full
# Output: 0.1.2-alpha+c6782b3

# Git commit hash only
./rai version --commit
# Output: c6782b3

# Git branch name
./rai version --branch
# Output: feature/0.1.2-alpha

# JSON output (for scripts/CI)
./rai version --json
```

### Python Code

```python
# Import version functions
from src.version import (
    get_version_string,      # Full version with git info
    get_short_version,       # Just the version number
    get_version_info,        # Complete info dictionary
    __version__,             # Module-level version constant
    __git_commit__,          # Git commit hash
    __git_branch__,          # Git branch name
)

# Get version string
version = get_version_string()
# "0.1.2-alpha+c6782b3" or "0.1.2-alpha+c6782b3.dirty"

# Get short version
version = get_short_version()
# "0.1.2-alpha"

# Get comprehensive info
info = get_version_info()
# {
#     "version": "0.1.2-alpha",
#     "version_full": "0.1.2-alpha+c6782b3",
#     "git_commit": "c6782b3",
#     "git_branch": "feature/0.1.2-alpha",
#     "git_dirty": false,
#     "build_date": "2025-10-01T12:00:00Z",
#     "environment": "development",
#     "python_version": "3.11.5"
# }
```

### FastAPI Integration

Version information is automatically available in the FastAPI application:

```python
# GET /health endpoint includes version
{
    "status": "healthy",
    "version": "0.1.2-alpha+c6782b3",
    "git_commit": "c6782b3",
    "environment": "development"
}

# GET /version endpoint for detailed version info
{
    "version": "0.1.2-alpha",
    "version_full": "0.1.2-alpha+c6782b3",
    "git_commit": "c6782b3",
    "git_branch": "feature/0.1.2-alpha",
    "build_date": "2025-10-01T12:00:00Z"
}
```

## Updating Version

### Manual Update (Development)

Edit `pyproject.toml`:

```toml
[project]
name = "reflectai"
version = "0.1.2-alpha"  # ← Update this line
```

The change is automatically picked up by `src/version.py`.

### Automated Update (Using ./rai CLI) ✨

**Recommended**: Use the built-in version bump command:

```bash
# Patch bump (bug fixes): 0.1.2-alpha → 0.1.3
./rai version bump patch

# Minor bump (new features): 0.1.2-alpha → 0.2.0
./rai version bump minor

# Major bump (breaking changes): 0.1.2-alpha → 1.0.0
./rai version bump major

# Remove prerelease (stable release): 0.1.2-alpha → 0.1.2
./rai version bump release

# Change prerelease type: 0.1.2-alpha → 0.1.2-beta
./rai version bump beta

# Preview changes without applying (dry run)
./rai version bump patch --dry-run

# Auto-confirm (skip prompt)
./rai version bump patch --yes

# Create git tag automatically
./rai version bump patch --tag

# Push changes and tags to remote
./rai version bump patch --tag --push

# Force bump with uncommitted changes
./rai version bump patch --force
```

**What the bump command does:**
1. ✅ Parses current version from pyproject.toml
2. ✅ Calculates new version using semantic versioning rules
3. ✅ Updates pyproject.toml with new version
4. ✅ Creates git commit with descriptive message
5. ✅ Optionally creates git tag (with --tag flag)
6. ✅ Optionally pushes to remote (with --push flag)
7. ✅ Safety checks (clean working directory, confirmation)
8. ✅ Rollback on failure

### Automated Update (CI/CD)

For production builds, set environment variable:

```bash
export APP_VERSION="0.2.0"
```

Priority order:
1. `APP_VERSION` environment variable (for production)
2. `pyproject.toml` version (for development)
3. Fallback: `"0.1.2-alpha"`

### Git Information

Git commit and branch are automatically detected:

```bash
# Git info from git commands (preferred)
git rev-parse --short=7 HEAD  # Commit hash
git branch --show-current      # Branch name

# Git info from environment (CI/CD)
export GIT_COMMIT="abc123"
export GIT_BRANCH="main"
```

## Version in Configuration

The application configuration automatically uses the centralized version:

```python
from src.infrastructure.config import get_config_manager

config = get_config_manager().get_config()
print(config.app.version)  # "0.1.2-alpha"
```

**Note**: Configuration no longer has hardcoded version - it reads from `src/version.py`.

## Testing

Test files automatically use the centralized version:

```python
# In tests
from src.version import __version__

def test_version():
    assert __version__ == "0.1.2-alpha"
```

**Updated files**:
- `tests/__init__.py` - Uses centralized version
- `tests/fixtures/__init__.py` - Uses centralized version
- `tests/conftest.py` - Mock config uses centralized version

## CI/CD Integration

### GitHub Actions Example

```yaml
- name: Get version info
  run: |
    VERSION=$(./rai version --short)
    COMMIT=$(./rai version --commit)
    echo "VERSION=$VERSION" >> $GITHUB_ENV
    echo "COMMIT=$COMMIT" >> $GITHUB_ENV

- name: Build with version
  run: |
    docker build \
      --build-arg APP_VERSION=${{ env.VERSION }} \
      --build-arg GIT_COMMIT=${{ env.COMMIT }} \
      -t reflectai:${{ env.VERSION }} .
```

### Docker Build

```dockerfile
ARG APP_VERSION="0.1.2-alpha"
ARG GIT_COMMIT="unknown"

ENV APP_VERSION=${APP_VERSION}
ENV GIT_COMMIT=${GIT_COMMIT}
```

## Best Practices

### ✅ Do

- Update version in `pyproject.toml` only (or use `./rai version bump`)
- Use `./rai version bump` for automated version management
- Use `get_version_string()` for display with git info
- Use `get_short_version()` for version comparison
- Use `get_version_info()` for comprehensive API responses
- Set `APP_VERSION` env var in production builds
- Include version in all API responses
- Log version on application startup
- Create git tags for releases
- Follow semantic versioning conventions
- Use `--dry-run` to preview version changes

### ❌ Don't

- Hardcode version strings in code
- Modify version in multiple places
- Skip version updates for releases
- Ignore dirty working directory warnings
- Use version for security decisions (use semantic checks)
- Skip testing before version bumps
- Force bump without good reason

## Common Workflows

### Development Workflow

```bash
# 1. Check current version
./rai version

# 2. Make changes and commit
git add .
git commit -m "feat: add new feature"

# 3. Bump version for feature (minor)
./rai version bump minor --yes

# 4. Push changes
git push origin HEAD --tags
```

### Release Workflow

```bash
# 1. Ensure working directory is clean
git status

# 2. Preview version bump
./rai version bump release --dry-run

# 3. Create release version with tag
./rai version bump release --tag --yes

# 4. Push release
git push origin HEAD --tags

# 5. Verify version
./rai version
```

### Hotfix Workflow

```bash
# 1. Checkout main/production branch
git checkout main

# 2. Apply hotfix
git cherry-pick <commit-hash>

# 3. Bump patch version
./rai version bump patch --tag --yes

# 4. Push hotfix
git push origin main --tags
```

### Prerelease Workflow

```bash
# Start alpha
./rai version bump alpha --yes
# Output: 0.1.2-alpha

# Progress to beta
./rai version bump beta --yes  
# Output: 0.1.2-beta

# Progress to release candidate
./rai version bump rc --yes
# Output: 0.1.2-rc

# Final release
./rai version bump release --tag --yes
# Output: 0.1.2
```

## Version History

| Version | Date | Description |
|---------|------|-------------|
| 0.1.2-alpha | 2025-10-01 | Centralized version management, git tracking |
| 0.1.1-alpha | 2025-09-30 | Branch cleanup, documentation improvements |
| 0.1.0-alpha | 2025-09-15 | Initial Temporal.io integration |

## Troubleshooting

### Version shows "unknown"

**Cause**: Cannot read from pyproject.toml or git commands fail

**Solution**:
```bash
# Check pyproject.toml exists
ls -la pyproject.toml

# Check git is available
git --version

# Set fallback environment variables
export APP_VERSION="0.1.2-alpha"
export GIT_COMMIT="abc123"
export GIT_BRANCH="main"
```

### Version shows "dirty"

**Cause**: Uncommitted changes in working directory

**Solution**:
```bash
# Check what's dirty
git status

# Commit or stash changes
git add .
git commit -m "Update version"
# or
git stash
```

### Version not updating

**Cause**: Module caching in Python

**Solution**:
```bash
# Remove Python cache
find . -type d -name __pycache__ -exec rm -rf {} +
find . -type f -name "*.pyc" -delete

# Restart application
./rai run app
```

## Related Files

- `pyproject.toml` - Single source of truth for version
- `src/version.py` - Version module with git integration
- `src/__init__.py` - Exports `__version__`
- `src/infrastructure/config/config_manager.py` - Uses centralized version
- `tests/__init__.py` - Test version tracking
- `dev` - CLI with version command

## References

- [Semantic Versioning](https://semver.org/)
- [PEP 440 - Version Identification](https://peps.python.org/pep-0440/)
- [Git Version Tagging](https://git-scm.com/book/en/v2/Git-Basics-Tagging)
