# golden-repo

[![CI](https://github.com/josunefoOrg/golden-repo/actions/workflows/ci.yml/badge.svg)](https://github.com/josunefoOrg/golden-repo/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/josunefoOrg/golden-repo/blob/main/LICENSE)
[![CodeQL](https://github.com/josunefoOrg/golden-repo/actions/workflows/codeql.yml/badge.svg)](https://github.com/josunefoOrg/golden-repo/actions/workflows/codeql.yml)
[![Security Scan](https://github.com/josunefoOrg/golden-repo/actions/workflows/secret-scan.yml/badge.svg)](https://github.com/josunefoOrg/golden-repo/actions/workflows/secret-scan.yml)

golden-repo is a GitHub template repository for creating secure agent and security-tooling repositories. It provides a reusable baseline for repositories similar to SOCBot and PostureIQ-style projects, with standard directories for `infra/`, `src/`, `docs/`, and `tools/`.

## Quickstart

Create a new repository from this template:

```bash
gh repo create <org>/<name> --template josunefoOrg/golden-repo
```

Clone the generated repository and install the local tooling dependencies:

```bash
git clone https://github.com/<org>/<name>.git
cd <name>
python -m pip install -r tools/requirements.txt
```

Provision the repository baseline:

```bash
GITHUB_TOKEN=<github-app-installation-token> python tools/provision_repo.py --org <org> --repo <name>
```

Use a GitHub App installation token or another approved short-lived token source. Do not use long-lived personal access tokens.

## Architecture

See [docs/architecture.md](docs/architecture.md) for the template architecture, repository layout, provisioning flow, and security baseline.

## Provisioning a new repo

New repositories are provisioned through:

- `tools/provision_repo.py` - command-line provisioning for repository settings, security features, branch protection, and team access.
- `.github/workflows/provision-new-repo.yml` - self-service GitHub Actions workflow for creating and securing repositories from this template.

The provisioning flow is expected to enable Dependabot alerts and security updates, secret scanning, secret scanning push protection, CodeQL default setup, and the branch protection baseline below.

## Branch protection baseline

The `main` branch must use this baseline:

- Pull request reviews require at least 1 approval.
- Stale approvals are dismissed when new commits are pushed.
- Code Owner review is required.
- Required status checks are strict and must be up to date before merge.
- Required status check contexts are exactly `test`, `build`, `analyze`, and `gitleaks`.
- Signed commits are required.
- Force-push is disabled.
- Branch deletion is disabled.
- Branch protection is enforced for administrators.
- Push access is restricted to the `maintainers` team.

## Repository layout

```text
infra/   Infrastructure definitions and deployment assets.
src/     Application and agent source code.
docs/    Architecture, operations, and security documentation.
tools/   Provisioning and repository automation scripts.
```

## License

This template is distributed under the MIT License. The license holder and license choice are template defaults and can be replaced for generated repositories when needed.
