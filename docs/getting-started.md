---
title: Getting started
layout: default
nav_order: 2
---

# Getting started

This guide walks through creating a repository from the template and installing
the local tooling. For applying the secure baseline, continue to
[Provisioning](provisioning.md).

## Prerequisites

- A GitHub account with permission to create repositories in the target
  organization.
- The [GitHub CLI](https://cli.github.com/) (`gh`), authenticated with
  `gh auth login`.
- Python 3.11 or newer, for the provisioning tooling.
- For provisioning against an organization, an approved short-lived token source
  such as a GitHub App installation token. Do not use long-lived personal access
  tokens.

## Create a repository from the template

Use the GitHub CLI:

```bash
gh repo create <org>/<name> --template josunefoOrg/golden-repo
```

Or use the GitHub UI: open
[josunefoOrg/golden-repo](https://github.com/josunefoOrg/golden-repo), select
`Use this template`, and create a new repository.

## Clone and install tooling

```bash
git clone https://github.com/<org>/<name>.git
cd <name>
python -m pip install -r tools/requirements.txt
```

## Repository layout

```text
infra/           Infrastructure definitions and deployment assets.
src/             Application and agent source code.
docs/            Architecture, operations, and security documentation.
tests/           Test suite; runs in CI via pytest (the required test check).
tools/           Provisioning and repository automation scripts.
.github/agents/  Optional Copilot custom agents shipped with generated repos.
```

## Next steps

- [Provisioning](provisioning.md): apply the branch protection and security
  baseline.
- [Configuration](configuration.md): set up the org variables, secrets, and
  environment the self-service workflow needs.
