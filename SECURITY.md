# Security Policy

## Supported versions

| Version | Supported |
| --- | --- |
| `main` | Yes |
| Generated repositories | Maintained by the owning repository team |
| Archived or unmaintained forks | No |

## Reporting a vulnerability

Report suspected vulnerabilities by email to <security-email>.

Placeholder: replace <security-email> with the monitored security contact for the organization before using this template in production.

Do not open public issues for security vulnerabilities. Include as much detail as possible:

- Affected repository and version or commit.
- Vulnerability type and impact.
- Reproduction steps or proof of concept.
- Relevant logs, screenshots, or configuration details.
- Whether the issue is actively exploited or publicly disclosed.

## Response SLA

We aim to acknowledge reports within 3 business days.

Target fix timelines depend on severity:

| Severity | Target fix or mitigation |
| --- | --- |
| Critical | 7 calendar days |
| High | 14 calendar days |
| Medium | 30 calendar days |
| Low | Next planned maintenance cycle |

If a fix requires more time, maintainers should provide status updates and a mitigation plan.

## Security controls

Repositories generated from this template are expected to enforce:

- Secret scanning.
- Secret scanning push protection.
- CodeQL analysis.
- Dependabot alerts.
- Dependabot security updates.
- Required `gitleaks` status check for pull requests.

Never commit secrets, credentials, private keys, or production data to the repository.
