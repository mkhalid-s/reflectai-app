# Security Policy

## Supported Versions

ReflectAI is currently pre-1.0. Security fixes are applied to the `main` branch and future tagged releases where practical.

## Reporting a Vulnerability

Please do not report security vulnerabilities through public GitHub issues.

Instead, contact the repository maintainer privately through GitHub. Include:

- A clear description of the issue
- Steps to reproduce or proof-of-concept details
- Affected components or versions
- Any known mitigations

## Secrets and Sensitive Data

Do not commit real API keys, OAuth credentials, Slack tokens, database passwords, private certificates, or internal service URLs. Use `.env.example` placeholders and local untracked `.env` files for configuration.

## Responsible Disclosure

Please give maintainers reasonable time to investigate and release a fix before public disclosure.
