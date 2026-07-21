---
title: Home
layout: default
nav_order: 1
---

# golden-repo

golden-repo is a GitHub template repository for creating secure agent and
security-tooling repositories. It provides a reusable, opinionated baseline with
standard directories for `infra/`, `src/`, `docs/`, and `tools/`, plus automated
workflows for testing, static analysis, secret scanning, and supply-chain
integrity.

This documentation site is published from the `main` branch `/docs` folder and is
meant to be consumed by anyone creating, provisioning, or maintaining a repository
from this template.

## What you get

- A consistent repository layout for agent and security tooling projects.
- Branch protection and required status checks applied automatically at
  provisioning time.
- Security features enabled out of the box: Dependabot alerts and updates, secret
  scanning and push protection, and CodeQL analysis via an advanced workflow.
- Supply-chain integrity with SBOM generation and keyless signing on release.
- Optional Copilot custom agents for infrastructure, security, and compliance
  review.
- Self-service provisioning through a script or a gated GitHub Actions workflow.

## Start here

| Guide | What it covers |
| ----- | -------------- |
| [Getting started](getting-started.md) | Create a repository from the template and install tooling. |
| [Provisioning](provisioning.md) | Apply the secure baseline with the script or the self-service workflow. |
| [Configuration](configuration.md) | Required org variables, secrets, environments, and one-time setup. |
| [GitHub App setup](SETUP.md) | The full one-time GitHub App registration and installation steps. |
| [Workflows](workflows.md) | CI, CodeQL, secret scanning, SBOM, and compliance review workflows. |
| [Security baseline](security.md) | The security controls enabled and enforced by the template. |
| [Branch protection](branch-protection.md) | The authoritative `main` protection baseline. |
| [Architecture](architecture.md) | Template architecture and the provisioning flow. |
| [Copilot agents](agents.md) | The custom agents shipped with the template. |
| [Troubleshooting](troubleshooting.md) | Common provisioning and Pages issues and fixes. |

## Quick reference

Create a repository from this template:

```bash
gh repo create <org>/<name> --template josunefoOrg/golden-repo
```

Provision the secure baseline:

```bash
GITHUB_TOKEN=<github-app-installation-token> \
  python tools/provision_repo.py --org <org> --repo <name>
```

Use a GitHub App installation token or another approved short-lived token source.
Do not use long-lived personal access tokens.

## GitHub Pages behavior

- golden-repo itself publishes this full documentation site from `main` `/docs`.
- Repositories provisioned from the template get GitHub Pages enabled only when
  they are not private (public and internal), served with a single placeholder
  landing page. Private repositories skip Pages. See
  [Provisioning](provisioning.md#github-pages) for details.
