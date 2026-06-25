# Contributing to ReflectAI

Thank you for your interest in contributing to ReflectAI.

## Ways to Contribute

- Report reproducible bugs
- Suggest focused improvements
- Improve documentation and examples
- Add tests for existing behavior
- Submit small, reviewable pull requests

## Development Setup

Use Python 3.11 or 3.12. The project uses PDM and the `rai` helper CLI.

```bash
./rai setup all
./rai test
./rai check
```

## Pull Request Guidelines

- Keep changes focused and explain the motivation.
- Add or update tests for behavior changes.
- Update documentation when public behavior or setup changes.
- Do not include secrets, internal endpoints, generated credentials, or local settings.
- Follow the existing async, FastAPI, Temporal, Slack, and LLM gateway patterns in the codebase.

## Commit Messages

Prefer concise conventional-style messages, for example:

```text
fix: handle missing assessment data
feat: add competency trend summary
chore: update workflow cache settings
```

## Code of Conduct

By participating, you agree to follow `CODE_OF_CONDUCT.md`.
