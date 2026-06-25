# Conventional Commits Guide

## Overview

Conventional Commits is a specification for writing standardized commit messages that make git history machine-readable and human-friendly. This guide explains why we use them, how to write them, and the powerful automation they enable.

**Official Specification**: [conventionalcommits.org](https://www.conventionalcommits.org/)

---

## Table of Contents

- [What Are Conventional Commits?](#what-are-conventional-commits)
- [Why We Use Them](#why-we-use-them)
- [Commit Message Format](#commit-message-format)
- [Standard Types](#standard-types)
- [Practical Examples](#practical-examples)
- [Advanced Features](#advanced-features)
- [Automation Benefits](#automation-benefits)
- [Integration with Tools](#integration-with-tools)
- [Quick Reference](#quick-reference)

---

## What Are Conventional Commits?

Conventional Commits is a lightweight convention on top of commit messages that provides an easy set of rules for creating an explicit commit history.

### Basic Structure

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Minimal Example

```
feat: add user authentication
```

### Full Example

```
feat(auth): add JWT token authentication

Implement JWT-based authentication system with:
- Token generation on login
- Token validation middleware
- Refresh token mechanism

Closes #123
BREAKING CHANGE: API endpoints now require Authorization header
```

---

## Why We Use Them

### 1. 🤖 Automated Changelog Generation

Tools can parse commit messages and automatically generate `CHANGELOG.md`:

```markdown
## v0.2.0 (2025-10-15)

### Features
- add user authentication (abc123)
- add payment integration (def456)

### Bug Fixes
- resolve memory leak in worker (ghi789)

### Documentation
- update API documentation (jkl012)
```

**Command**:
```bash
git log --pretty=format:"- %s (%h)" --grep="^feat:" v0.1.0..HEAD
```

### 2. 📦 Automatic Semantic Versioning

Commits automatically determine the next version number:

| Commit Type | Version Impact | Example |
|-------------|---------------|---------|
| `feat:` | MINOR bump | 0.1.0 → 0.2.0 |
| `fix:` | PATCH bump | 0.1.0 → 0.1.1 |
| `BREAKING CHANGE:` | MAJOR bump | 0.1.0 → 1.0.0 |
| `docs:`, `chore:`, etc. | No bump | 0.1.0 → 0.1.0 |

**Tools**: `semantic-release`, `standard-version`, `release-please`

### 3. 🔍 Easy Filtering and Searching

Find specific types of changes instantly:

```bash
# All features added
git log --oneline --grep="^feat:"

# All bug fixes
git log --oneline --grep="^fix:"

# Changes in a specific scope
git log --oneline --grep="^feat(auth):"

# Changes since last release
git log v0.1.0..HEAD --oneline --grep="^feat:"

# Count features in current version
git log --oneline --grep="^feat:" | wc -l
```

### 4. 👥 Code Review Efficiency

Reviewers immediately understand the nature of changes:

- `feat:` → Check new functionality, tests, documentation
- `fix:` → Verify bug is resolved, check edge cases
- `refactor:` → Review code quality, ensure no behavior change
- `docs:` → Quick review, no code testing needed
- `test:` → Verify test coverage and quality

### 5. 🚀 CI/CD Intelligence

CI/CD pipelines can make smart decisions:

```yaml
# GitHub Actions example
- name: Determine action
  run: |
    if git log -1 --pretty=%B | grep -q "^docs:"; then
      echo "Skip tests, deploy docs only"
    elif git log -1 --pretty=%B | grep -q "^feat:"; then
      echo "Run full test suite and deploy"
    fi
```

### 6. 📊 Project Analytics

Generate insights from commit history:

```bash
# Most active areas (by scope)
git log --pretty=format:"%s" | grep -oP '(?<=\().*?(?=\))' | sort | uniq -c | sort -rn

# Feature velocity (features per month)
git log --since="1 month ago" --grep="^feat:" --oneline | wc -l

# Bug fix rate
git log --since="1 week ago" --grep="^fix:" --oneline | wc -l
```

### 7. 🎯 Clear Team Communication

Everyone understands impact at a glance:

| Type | Meaning | User Impact |
|------|---------|-------------|
| `feat:` | New feature | ✅ New capability available |
| `fix:` | Bug fix | ✅ Problem resolved |
| `docs:` | Documentation | ℹ️ Better guidance |
| `refactor:` | Code improvement | 🔧 No user-visible change |
| `perf:` | Performance | ⚡ Faster/more efficient |
| `test:` | Tests | 🧪 Better quality assurance |

---

## Commit Message Format

### Structure

```
<type>(<scope>): <subject>
<BLANK LINE>
<body>
<BLANK LINE>
<footer>
```

### Components

#### 1. Type (Required)

The type describes the **kind of change** being made.

**Standard types**:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, no logic change)
- `refactor`: Code refactoring (no feature or bug fix)
- `perf`: Performance improvement
- `test`: Adding or updating tests
- `build`: Build system changes
- `ci`: CI/CD changes
- `chore`: Other changes (dependencies, tooling)
- `revert`: Reverting a previous commit

#### 2. Scope (Optional)

The scope describes the **area** of the codebase affected.

**Examples**:
```
feat(auth): add JWT authentication
fix(database): resolve connection pool leak
docs(api): update endpoint documentation
refactor(llm): simplify provider selection
```

**Common scopes in ReflectAI**:
- `auth` - Authentication/authorization
- `api` - API endpoints
- `database` - Database operations
- `llm` - LLM integration
- `slack` - Slack integration
- `workflow` - Temporal workflows
- `version` - Version management
- `cli` - Dev CLI tools

#### 3. Subject (Required)

The subject is a **brief description** of the change.

**Rules**:
- Use imperative mood ("add" not "added" or "adds")
- Don't capitalize first letter
- No period at the end
- Maximum 50-72 characters
- Be clear and concise

**Good examples**:
```
add user authentication
fix memory leak in worker process
update API documentation
remove deprecated endpoints
```

**Bad examples**:
```
Added new feature (use "add" not "added")
Fix bugs (too vague)
Updated stuff (meaningless)
WIP (not descriptive)
```

#### 4. Body (Optional)

The body provides **detailed explanation** of the change.

**When to include**:
- Complex changes that need context
- Breaking changes
- Multiple related changes
- Migration instructions

**Format**:
- Separated from subject by blank line
- Can be multiple paragraphs
- Use bullet points for lists
- Wrap at 72 characters

**Example**:
```
feat: implement JWT authentication

Add comprehensive JWT-based authentication system:
- Token generation on login with configurable expiry
- Middleware for token validation on protected routes
- Refresh token mechanism for extended sessions
- Revocation list for invalidated tokens

The system uses RS256 algorithm for enhanced security
and integrates with existing user database.
```

#### 5. Footer (Optional)

The footer contains **metadata** about the commit.

**Common uses**:
- Reference issues: `Closes #123`, `Fixes #456`, `Refs #789`
- Breaking changes: `BREAKING CHANGE: ...`
- Co-authors: `Co-authored-by: Name <email>`
- Reviewed by: `Reviewed-by: Name <email>`

**Example**:
```
fix: resolve database connection leak

Fix connection pool exhaustion by ensuring
all connections are properly closed after use.

Closes #456
Refs #123
```

---

## Standard Types

### feat: New Feature

**When to use**: Adding new functionality that users can interact with

**Examples**:
```bash
feat: add user profile page
feat(api): add new search endpoint
feat(slack): implement interactive message buttons
feat(llm): add cost tracking for API calls
```

**Impact**:
- Triggers MINOR version bump (0.1.0 → 0.2.0)
- Appears in "Features" section of changelog
- Should include tests and documentation

### fix: Bug Fix

**When to use**: Fixing a defect or unexpected behavior

**Examples**:
```bash
fix: resolve memory leak in worker process
fix(database): correct connection timeout handling
fix(auth): prevent token expiry race condition
fix: handle null values in user preferences
```

**Impact**:
- Triggers PATCH version bump (0.1.0 → 0.1.1)
- Appears in "Bug Fixes" section of changelog
- Should reference issue number

### docs: Documentation

**When to use**: Changes to documentation only (no code changes)

**Examples**:
```bash
docs: update API endpoint documentation
docs(readme): add installation instructions
docs: fix typos in contribution guide
docs(api): add examples for authentication
```

**Impact**:
- No version bump
- May appear in "Documentation" section of changelog
- CI can skip tests and only deploy docs

### style: Code Style

**When to use**: Formatting, whitespace, semicolons (no logic change)

**Examples**:
```bash
style: format code with black
style: fix indentation in auth module
style: remove trailing whitespace
style(typescript): add missing semicolons
```

**Impact**:
- No version bump
- Usually excluded from changelog
- Can skip tests in CI (linting only)

### refactor: Code Refactoring

**When to use**: Restructuring code without changing behavior

**Examples**:
```bash
refactor: simplify user validation logic
refactor(database): extract query builder to separate class
refactor: use async/await instead of callbacks
refactor(llm): consolidate provider interfaces
```

**Impact**:
- No version bump
- May appear in "Internal Changes" section
- Requires full test suite to ensure no regression

### perf: Performance Improvement

**When to use**: Changes that improve performance

**Examples**:
```bash
perf: add caching for frequently accessed data
perf(database): optimize query with proper indexes
perf: lazy load images to reduce initial page load
perf(api): implement response compression
```

**Impact**:
- May trigger MINOR or PATCH bump
- Appears in "Performance" section of changelog
- Should include benchmarks or metrics

### test: Testing

**When to use**: Adding or updating tests

**Examples**:
```bash
test: add unit tests for authentication
test(api): add integration tests for search endpoint
test: increase coverage for user validation
test: add regression test for issue #123
```

**Impact**:
- No version bump
- Usually excluded from changelog
- CI runs extra validation

### build: Build System

**When to use**: Changes to build configuration or dependencies

**Examples**:
```bash
build: update webpack configuration
build: migrate to vite from create-react-app
build(deps): upgrade fastapi to 0.104.1
build: add typescript compilation step
```

**Impact**:
- No version bump
- May appear in "Build" section
- Should test in CI before merge

### ci: Continuous Integration

**When to use**: Changes to CI/CD configuration

**Examples**:
```bash
ci: add automated testing workflow
ci: update GitHub Actions to v4
ci(docker): optimize build cache layers
ci: add security scanning with Snyk
```

**Impact**:
- No version bump
- Usually excluded from changelog
- Test in CI pipeline

### chore: Maintenance

**When to use**: Routine tasks, dependency updates, tooling

**Examples**:
```bash
chore: update dependencies
chore: bump version 0.1.2 → 0.1.3
chore(deps): update pytest to 7.4.0
chore: clean up unused imports
```

**Impact**:
- No version bump (unless version bump itself)
- Usually excluded from changelog
- Can use dependabot for automation

### revert: Revert Previous Commit

**When to use**: Reverting a previous commit

**Format**:
```bash
revert: feat: add user authentication

This reverts commit abc123def456.
Reason: Causes regression in login flow.
```

**Impact**:
- Depends on what's being reverted
- Should explain reason for revert

---

## Practical Examples

### ReflectAI Project Examples

#### Feature Addition
```
feat(version): add automated version bump to dev CLI

Implement semantic versioning automation with:
- Parse current version from pyproject.toml
- Calculate new version based on bump type (major/minor/patch)
- Update pyproject.toml automatically
- Create git commit and optional tag
- Safety checks (clean working dir, confirmation)
- Dry-run mode for previewing changes

Usage:
  ./rai version bump patch --dry-run
  ./rai version bump minor --tag --yes

Closes #42
```

#### Bug Fix
```
fix(llm): prevent cost tracker from double-counting retries

Fix issue where failed LLM requests that were retried
were counted twice in cost tracking, leading to inflated
usage reports.

Add deduplication logic based on request ID to ensure
each request is counted exactly once regardless of retries.

Fixes #156
```

#### Documentation
```
docs: add comprehensive version management guide

Create detailed documentation covering:
- Version viewing with ./rai version
- Automated version bumping
- Semantic versioning rules
- CI/CD integration examples
- Common workflows (dev, release, hotfix)

Includes practical examples and troubleshooting section.
```

#### Refactoring
```
refactor(config): centralize version management

Move version reading from multiple locations to single
source of truth in src/version.py. Update all consumers:
- src/infrastructure/config/config_manager.py
- tests/__init__.py
- tests/conftest.py

No behavior change - version still read from pyproject.toml
```

#### Breaking Change
```
feat(api)!: redesign authentication endpoints

BREAKING CHANGE: Authentication endpoint paths have changed.

Old endpoints (removed):
- POST /api/v1/auth/login
- POST /api/v1/auth/refresh

New endpoints:
- POST /api/v2/auth/token
- POST /api/v2/auth/token/refresh

Migration guide available at docs/MIGRATION_v2.md

The new design follows OAuth 2.0 standards and improves
security with shorter-lived tokens.
```

### Multi-Line Examples

#### Complex Feature
```
feat(slack): implement interactive workflow notifications

Add rich interactive notifications for workflow status:

Features:
- Real-time status updates with progress indicators
- Interactive buttons for workflow control (pause/resume/cancel)
- Threaded messages to reduce channel noise
- Markdown formatting for readable status messages
- Error details with stack traces in thread
- Integration with Temporal workflow lifecycle

Technical changes:
- New SlackNotificationService class
- Socket mode event handlers for button interactions
- Temporal activity for sending notifications
- Retry logic with exponential backoff

Configuration:
Set SLACK_NOTIFICATIONS_ENABLED=true to enable

Closes #89
Refs #76, #82
```

#### Performance Improvement
```
perf(database): optimize competency assessment queries

Improve assessment query performance by 85%:

Before: ~2.5s for 1000 assessments
After:  ~0.4s for 1000 assessments

Changes:
- Add composite index on (user_id, assessment_date, status)
- Use bulk inserts instead of individual INSERT statements
- Implement query result caching (5 min TTL)
- Lazy load related objects to reduce initial query size
- Add database connection pooling (min=5, max=20)

Benchmarks included in tests/performance/test_assessment_performance.py

Fixes #234
```

---

## Advanced Features

### Breaking Changes

Breaking changes MUST be indicated with either:
1. `!` after type/scope
2. `BREAKING CHANGE:` footer

#### Using `!` Suffix
```
feat(api)!: remove deprecated v1 endpoints

Remove all v1 API endpoints as announced in Q3 2024.
All clients must migrate to v2 API.
```

#### Using Footer
```
feat: update authentication flow

Implement new OAuth 2.0 compliant authentication.

BREAKING CHANGE: The /api/auth/login endpoint now returns
a different JSON structure. Update your client code to use
the new 'access_token' and 'refresh_token' fields instead
of the old 'token' field.
```

### Scopes with Multiple Components

Use `/` or `.` to indicate hierarchy:

```
feat(api/auth): add OAuth2 provider
fix(slack/notifications): resolve threading issue
refactor(llm/cost-tracking): simplify calculation logic
```

### Multiple Issues

Reference multiple issues in footer:

```
fix: resolve various authentication edge cases

Handle multiple authentication edge cases:
- Expired tokens now return proper 401 status
- Concurrent logins from same user handled gracefully
- Token refresh race condition eliminated

Fixes #123, #145, #167
Refs #89
```

### Co-Authors

Credit multiple contributors:

```
feat: implement collaborative editing

Add real-time collaborative editing with conflict resolution.

Co-authored-by: Jane Doe <jane@example.com>
Co-authored-by: Bob Smith <bob@example.com>
```

### Signed-off-by

For DCO (Developer Certificate of Origin):

```
fix: resolve security vulnerability

Patch XSS vulnerability in user input sanitization.

Signed-off-by: Developer Name <dev@example.com>
```

---

## Automation Benefits

### 1. Automated Changelog Generation

**Tool**: `conventional-changelog`

```bash
# Install
npm install -g conventional-changelog-cli

# Generate CHANGELOG.md
conventional-changelog -p angular -i CHANGELOG.md -s

# Output includes all conventional commits grouped by type
```

**Example Output**:
```markdown
# Changelog

## [0.2.0](https://github.com/user/repo/compare/v0.1.0...v0.2.0) (2025-10-15)

### Features

* **auth:** add JWT authentication ([abc123](https://github.com/user/repo/commit/abc123))
* **api:** add search endpoint ([def456](https://github.com/user/repo/commit/def456))

### Bug Fixes

* **database:** resolve connection leak ([ghi789](https://github.com/user/repo/commit/ghi789))

### Documentation

* update API guide ([jkl012](https://github.com/user/repo/commit/jkl012))
```

### 2. Automatic Version Bumping

**Tool**: `semantic-release`

```bash
# Install
npm install --save-dev semantic-release

# Configure in package.json or .releaserc
{
  "release": {
    "branches": ["main"],
    "plugins": [
      "@semantic-release/commit-analyzer",
      "@semantic-release/release-notes-generator",
      "@semantic-release/changelog",
      "@semantic-release/github"
    ]
  }
}

# Run (usually in CI)
npx semantic-release
```

**How it works**:
1. Analyzes commits since last release
2. Determines version bump type (major/minor/patch)
3. Updates version in package.json/pyproject.toml
4. Generates CHANGELOG.md
5. Creates git tag
6. Creates GitHub release

### 3. Release Notes Generation

**Tool**: `release-please` (Google)

```yaml
# .github/workflows/release-please.yml
name: Release Please
on:
  push:
    branches: [main]
    
jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: google-github-actions/release-please-action@v3
        with:
          release-type: python
          package-name: reflectai
```

**Creates**:
- Automated release PRs
- Changelog entries
- Version bumps
- GitHub releases

### 4. Integration with ./rai CLI

**Enhanced version bump** (future enhancement):

```python
# src/scripts/smart_version_bump.py
def suggest_version_bump():
    """Analyze commits to suggest version bump type."""
    commits = get_commits_since_last_tag()
    
    has_breaking = any("BREAKING CHANGE" in c or "!" in c for c in commits)
    has_feat = any(c.startswith("feat:") for c in commits)
    has_fix = any(c.startswith("fix:") for c in commits)
    
    if has_breaking:
        return "major"
    elif has_feat:
        return "minor"
    elif has_fix:
        return "patch"
    else:
        return None  # No version bump needed
```

**Usage**:
```bash
./rai version bump auto  # Analyzes commits and bumps accordingly
```

---

## Integration with Tools

### 1. Commitizen - Interactive Commit Helper

```bash
# Install
pip install commitizen

# Use
cz commit

# Interactive prompts guide you through:
# - Select type
# - Enter scope
# - Write subject
# - Add body
# - Add footer
```

### 2. Commitlint - Enforce Convention

```bash
# Install
npm install --save-dev @commitlint/cli @commitlint/config-conventional

# Configure commitlint.config.js
module.exports = {
  extends: ['@commitlint/config-conventional']
};

# Add to git hooks
npx husky add .husky/commit-msg 'npx commitlint --edit $1'
```

### 3. Standard Version

```bash
# Install
npm install --save-dev standard-version

# Run
npx standard-version

# Does:
# 1. Bump version in package.json
# 2. Generate/update CHANGELOG.md
# 3. Create git commit and tag
```

### 4. GitHub Actions Integration

```yaml
name: Semantic Release
on:
  push:
    branches: [main]

jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Semantic Release
        uses: cycjimmy/semantic-release-action@v3
        with:
          branches: |
            ['main']
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

### 5. Pre-commit Hook

```bash
# .git/hooks/commit-msg
#!/bin/bash
commit_msg=$(cat "$1")

# Check if commit message follows conventional commits
if ! echo "$commit_msg" | grep -qE "^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)(\(.+\))?!?: .+"; then
    echo "Error: Commit message doesn't follow Conventional Commits format"
    echo ""
    echo "Format: <type>(<scope>): <subject>"
    echo "Types: feat, fix, docs, style, refactor, perf, test, build, ci, chore, revert"
    echo ""
    echo "Example: feat(auth): add JWT authentication"
    exit 1
fi
```

---

## Quick Reference

### Commit Type Decision Tree

```
Are you adding new functionality?
  └─ Yes → feat:

Are you fixing a bug?
  └─ Yes → fix:

Are you only changing documentation?
  └─ Yes → docs:

Are you improving code without changing behavior?
  └─ Yes → refactor:

Are you improving performance?
  └─ Yes → perf:

Are you adding/updating tests?
  └─ Yes → test:

Are you updating build configuration?
  └─ Yes → build:

Are you updating CI/CD?
  └─ Yes → ci:

Are you doing routine maintenance?
  └─ Yes → chore:

Are you only formatting code?
  └─ Yes → style:
```

### Cheat Sheet

| What I did | Type | Example |
|-----------|------|---------|
| Added new feature | `feat:` | `feat: add user dashboard` |
| Fixed a bug | `fix:` | `fix: resolve login timeout` |
| Updated docs | `docs:` | `docs: update API guide` |
| Refactored code | `refactor:` | `refactor: simplify auth logic` |
| Improved performance | `perf:` | `perf: add database caching` |
| Added tests | `test:` | `test: add auth unit tests` |
| Updated build | `build:` | `build: update webpack config` |
| Changed CI/CD | `ci:` | `ci: add security scanning` |
| Updated dependencies | `chore:` | `chore: update dependencies` |
| Formatted code | `style:` | `style: run black formatter` |

### Version Bump Rules

| Commits Since Last Release | Version Bump | Example |
|---------------------------|--------------|---------|
| Only `fix:` | PATCH | 0.1.0 → 0.1.1 |
| Any `feat:` | MINOR | 0.1.0 → 0.2.0 |
| Any `BREAKING CHANGE:` | MAJOR | 0.1.0 → 1.0.0 |
| Only `docs:`, `chore:`, `style:` | None | 0.1.0 → 0.1.0 |

### Common Commands

```bash
# Show all features
git log --oneline --grep="^feat:"

# Show all fixes
git log --oneline --grep="^fix:"

# Show commits for scope
git log --oneline --grep="^feat(auth):"

# Count features since tag
git log v0.1.0..HEAD --oneline --grep="^feat:" | wc -l

# Generate changelog between tags
git log v0.1.0..v0.2.0 --pretty=format:"- %s (%h)"

# Find breaking changes
git log --grep="BREAKING CHANGE" --grep="!:" --pretty=format:"%s"
```

---

## Resources

### Official Documentation
- [Conventional Commits Specification](https://www.conventionalcommits.org/)
- [Semantic Versioning](https://semver.org/)
- [Keep a Changelog](https://keepachangelog.com/)

### Tools
- [Commitizen](https://github.com/commitizen/cz-cli) - Interactive commit helper
- [Commitlint](https://github.com/conventional-changelog/commitlint) - Enforce conventions
- [semantic-release](https://github.com/semantic-release/semantic-release) - Automated versioning
- [standard-version](https://github.com/conventional-changelog/standard-version) - Changelog automation
- [release-please](https://github.com/googleapis/release-please) - Google's release tool

### Editor Integration
- [VSCode Extension](https://marketplace.visualstudio.com/items?itemName=vivaxy.vscode-conventional-commits)
- [IntelliJ Plugin](https://plugins.jetbrains.com/plugin/13389-conventional-commit)
- [Vim Plugin](https://github.com/ollykel/v-vim-commit)

### Further Reading
- [Angular Commit Guidelines](https://github.com/angular/angular/blob/master/CONTRIBUTING.md#commit) - Origin of the convention
- [How to Write a Git Commit Message](https://chris.beams.io/posts/git-commit/)
- [The Art of the Commit](https://alistapart.com/article/the-art-of-the-commit/)

---

## Examples from ReflectAI

### Real Commits from This Project

```
feat: Centralize version management with git tracking
refactor: Major architecture rewrite with Temporal.io
feat: Add automated version bump to dev CLI
docs: Add version history clarification
docs: Add branch cleanup analysis
feat: Add Claude AI development setup
```

### Future Commits (Examples)

```
feat(slack): add interactive workflow controls
fix(llm): prevent duplicate cost tracking
perf(database): optimize assessment queries with indexes
docs(api): add OpenAPI specification
test(workflow): add integration tests for Temporal
ci: add automated release workflow
chore(deps): update temporal-sdk to 1.5.0
```

---

## Adoption in ReflectAI

### Current Status

✅ **We are already using Conventional Commits!**

Our recent commits follow the convention:
- ✅ Type prefixes (`feat:`, `docs:`, `refactor:`)
- ✅ Clear subjects
- ✅ Appropriate scopes where needed

### Next Steps

1. **Commit Message Template**
   ```bash
   git config commit.template .gitmessage
   ```

2. **Pre-commit Hook** (optional)
   - Validate commit message format
   - Prevent non-conventional commits

3. **Automated Changelog** (future)
   - Generate CHANGELOG.md from commits
   - Include in release process

4. **Smart Version Bump** (future)
   - `./rai version bump auto`
   - Analyzes commits to suggest bump type

---

## Summary

Conventional Commits transforms git history from a simple log into a powerful automation tool that:

- ✅ Generates changelogs automatically
- ✅ Determines version bumps intelligently
- ✅ Enables powerful commit searching
- ✅ Improves code review efficiency
- ✅ Provides CI/CD intelligence
- ✅ Creates clear team communication
- ✅ Follows industry standards

**Remember**: The goal is making git history useful for humans AND machines!

---

**Last Updated**: October 1, 2025  
**Maintained By**: ReflectAI Team
