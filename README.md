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

## Required environment configuration

The self-service workflow `.github/workflows/provision-new-repo.yml` uses `environment: repo-provisioning` as a manual approval gate before privileged repository provisioning runs. Provisioning is therefore not fully unattended.

IMPORTANT: Create the GitHub Environment and its required reviewers manually in the GitHub UI. Environment protection rules and required reviewers CANNOT be created via API/script and must be configured manually before provisioning is treated as ready.

Create the environment in the repository that hosts the workflow:

1. Open repository or organization settings for `josunefoOrg/golden-repo`.
2. Go to `Settings` -> `Environments`.
3. Select `New environment`.
4. Name it `repo-provisioning`.
5. Enable `Required reviewers`.
6. Add the approver team or users, preferably `maintainers` or `platform-team`.
7. Save the protection rules.

The workflow also needs these organization-level Actions credentials from the provisioning GitHub App:

- Variable: `PROVISIONER_APP_ID`
- Secret: `PROVISIONER_APP_PRIVATE_KEY`

Set them with `gh`:

```bash
gh variable set PROVISIONER_APP_ID --org josunefoOrg --body "<app-id>"
gh secret set PROVISIONER_APP_PRIVATE_KEY --org josunefoOrg < path/to/private-key.pem
```

Visibility flags may be required by org policy, for example `--visibility all` or selected repository access. See [docs/SETUP.md](docs/SETUP.md) for the full one-time GitHub App registration and installation steps.

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
infra/           Infrastructure definitions and deployment assets.
src/             Application and agent source code.
docs/            Architecture, operations, and security documentation.
tests/           Test suite; runs in CI via pytest (the required `test` status check).
tools/           Provisioning and repository automation scripts.
.github/agents/  Optional Copilot custom agents shipped with generated repos.
```

## Optional Copilot agents

This template can ship reusable Copilot custom agents under `.github/agents/` so every repository generated from it starts with domain expertise built in. Agents are Markdown files with a YAML front matter header (`name`, `description`, `tools`, `model`) followed by the agent instructions.

Recommended agents to support new agent/security-tooling projects:

- **IaC agent** - reviews and authors infrastructure-as-code in `infra/` (Bicep/Terraform), enforces tagging, network, and least-privilege conventions.
- **Security agent** - reviews changes for security issues, validates the security baseline (secret scanning, CodeQL, signed commits), and flags risky patterns.
- **AI Risk & Security Advisor** (`.github/agents/risk-security-advisor.md`) - included in this template. Advises on risk tier classification, Zero Trust architecture, threat detection, incident response, and compliance for enterprise AI agents on Microsoft Foundry.

To add another agent, drop a new `.github/agents/<name>.md` file following the same front matter format. To remove one, delete its file. Agents are inert until invoked, so they add no runtime cost to a generated repo.

## License

This template is distributed under the MIT License. The license holder and license choice are template defaults and can be replaced for generated repositories when needed.
