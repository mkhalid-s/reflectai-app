# ReflectAI

ReflectAI is an AI-powered competency analysis system for teams and organizations. It combines assessment workflows, LLM-assisted analysis, Slack interactions, and reporting tools to help identify skill strengths, gaps, and development opportunities.

## Features

- Competency assessment and gap analysis
- LLM gateway integration with provider failover, cost tracking, and caching
- Slack-based interaction patterns for team workflows
- Temporal workflow orchestration for long-running processing
- FastAPI backend with PostgreSQL, Redis, and Prometheus-friendly monitoring
- Docker and Kubernetes deployment assets

## Getting Started

This project uses Python 3.11 or 3.12 and PDM for dependency management.

```bash
./rai setup all
./rai run app
```

Common checks:

```bash
./rai test
./rai check
```

See the documentation in `docs/` and the `rai` CLI for more development and deployment commands.

## Configuration

Copy `.env.example` to `.env` and replace placeholder values with credentials for your own environment. Do not commit real secrets.

## Contributing

Contributions are welcome. Please read `CONTRIBUTING.md` and `CODE_OF_CONDUCT.md` before opening issues or pull requests.

## Security

Please report vulnerabilities using the guidance in `SECURITY.md`. Do not open public issues for suspected security vulnerabilities.

## License

ReflectAI is licensed under the MIT License. See `LICENSE` for details.
