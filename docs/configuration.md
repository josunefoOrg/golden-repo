---
title: Configuration
layout: default
nav_order: 4
---

# Configuration

The self-service provisioning workflow requires one-time organization and
repository configuration. This page summarizes what to set. For the full,
step-by-step GitHub App registration and installation flow, see
[GitHub App setup](SETUP.md).

## Required organization credentials

The workflow authenticates as a GitHub App and needs these organization-level
Actions credentials:

| Kind | Name | Value |
| ---- | ---- | ----- |
| Variable | `PROVISIONER_APP_ID` | The provisioning GitHub App ID. |
| Secret | `PROVISIONER_APP_PRIVATE_KEY` | The App private key, including the BEGIN and END lines. |

Set them with `gh`:

```bash
gh variable set PROVISIONER_APP_ID --org josunefoOrg --body "<app-id>"
gh secret set PROVISIONER_APP_PRIVATE_KEY --org josunefoOrg < path/to/private-key.pem
```

Organization policy may require visibility flags, for example `--visibility all`
or selected repository access.

## Required GitHub App permissions

The provisioning GitHub App needs these repository permissions: Administration
read and write, Contents read and write, Metadata read, Actions read and write,
Code scanning alerts read and write, Secret scanning alerts read and write, and
Dependabot alerts read and write. It also needs the organization Members
permission read and write, which is required so provisioning can create the
per-repository admin team. Members read-only causes a 403 on team creation.

## The repo-provisioning environment

The self-service workflow uses `environment: repo-provisioning` as a manual
approval gate before privileged provisioning runs.

Environment protection rules and required reviewers cannot be created through the
API and must be configured manually in the GitHub UI:

1. Open repository or organization settings for `josunefoOrg/golden-repo`.
2. Go to Settings, then Environments.
3. Select New environment and name it `repo-provisioning`.
4. Enable Required reviewers.
5. Add the approver team or users, preferably `maintainers` or `platform-team`.
6. Save the protection rules.

## Optional: framework compliance review

The framework compliance review workflow runs a Copilot custom agent on each pull
request. To enable it, store a fine-grained personal access token from a
Copilot-enabled account as an Actions secret named `COPILOT_CLI_TOKEN`, preferably
at the organization level so every provisioned repository inherits it. Classic
personal access tokens are not supported by the Copilot CLI. See
[Workflows](workflows.md) and [GitHub App setup](SETUP.md) for details.

## Configuration checklist

- [ ] `PROVISIONER_APP_ID` organization variable is set.
- [ ] `PROVISIONER_APP_PRIVATE_KEY` organization secret is set.
- [ ] The provisioning GitHub App is installed on the organization.
- [ ] The `repo-provisioning` environment exists with required reviewers.
- [ ] `golden-repo` is marked as a template repository.
- [ ] GitHub Advanced Security is enabled where private repositories need it.
- [ ] Optional: `COPILOT_CLI_TOKEN` is set for compliance review.
