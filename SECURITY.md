# Security Policy

## Supported Versions

Security fixes are best-effort for the latest code on the default branch.

## Reporting a Vulnerability

Please do not open a public issue for suspected vulnerabilities.

Instead, send the report through a private maintainer contact channel or the hosting platform's private security reporting feature. Include:

- A short description of the issue
- The affected component or file path
- Reproduction steps or a proof of concept
- Any suggested mitigation if you already have one

We aim to acknowledge reports quickly, confirm impact, and coordinate a fix before public disclosure whenever possible.

## Sensitive Data Guidelines

- Never commit real credentials, service-account keys, session tokens, or production `.env` files.
- Treat scraped content and logs as potentially sensitive until reviewed and sanitized.
- Prefer placeholder data in committed fixtures and examples.
