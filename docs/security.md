---
title: Security baseline
layout: default
nav_order: 7
---

# Security baseline

The template enforces a security baseline through a combination of provisioning
actions and workflows. This page summarizes the controls and where they are
applied.

## Enabled by the provisioner

When a repository is provisioned, the following are enabled automatically:

- Dependabot vulnerability alerts.
- Dependabot automated security updates.
- Secret scanning.
- Secret scanning push protection.

CodeQL analysis is provided by the advanced workflow shipped in the template
rather than by CodeQL default setup, to avoid a configuration conflict. See
[Workflows](workflows.md).

Some features on private and internal repositories require GitHub Advanced
Security to be available to the organization. See [GitHub App setup](SETUP.md).

## Enforced by branch protection

The `main` branch protection baseline enforces:

- Pull request review with at least one approval.
- Code Owner review.
- Dismissal of stale approvals when new commits are pushed.
- Strict, up-to-date required status checks: `test`, `build`, `analyze`,
  `gitleaks`.
- Signed commits.
- No force pushes and no branch deletion.
- Protection enforced for administrators.
- Push access restricted to the `maintainers` team.

See [Branch protection](branch-protection.md) for the authoritative baseline and
the exact API calls.

## Supply-chain integrity

On release, the SBOM and signing workflow generates SPDX SBOMs, signs them
keylessly with Cosign using OIDC, and pairs release artifacts with SLSA
provenance. This aligns with SLSA L3 build integrity expectations. See
[Workflows](workflows.md).

## Credentials and tokens

- Provisioning uses only the token supplied in `GITHUB_TOKEN`, which should be a
  short-lived GitHub App installation token or an OIDC-derived token.
- Do not use long-lived personal access tokens for provisioning.
- Do not commit private keys or secrets. Store the provisioning App private key
  as an organization Actions secret and delete local copies.

## Secret scanning in depth

Two layers protect against committed secrets:

- GitHub-native secret scanning and push protection, enabled by the provisioner.
- The Gitleaks workflow, which scans the full git history on pull requests and
  push to `main` and produces the required `gitleaks` check.
