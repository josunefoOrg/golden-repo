---
title: Workflows
layout: default
nav_order: 6
---

# Workflows

The template ships GitHub Actions workflows that automate testing, security
scanning, supply-chain integrity, and repository provisioning. The status checks
`test`, `build`, `analyze`, and `gitleaks` are required for merge on protected
branches.

## CI

`.github/workflows/ci.yml` runs on every pull request and push to `main`. It
installs dependencies from `tools/requirements.txt`, runs pytest, and lints. It
produces the required `test` status check and the `build` check.

## CodeQL

`.github/workflows/codeql.yml` performs advanced static analysis (SAST). It runs
on pull requests, push to `main`, and weekly. It scans Python and
JavaScript/TypeScript code and skips languages absent from the repository. It
produces the required `analyze` status check.

This template uses an advanced CodeQL workflow configuration. Do not enable CodeQL
default setup in the UI: default setup conflicts with the advanced workflow and
produces a configuration error. See [Troubleshooting](troubleshooting.md).

## Secret scanning

`.github/workflows/secret-scan.yml` runs Gitleaks on pull requests and push to
`main`, scanning the full git history. It produces the required `gitleaks` status
check and complements GitHub-native secret scanning and push protection, which the
provisioner enables.

## SBOM and signing

`.github/workflows/sbom-signing.yml` is an SLSA L3-aligned supply-chain workflow.
It is triggered on release publication, a tag push matching `v*`, or manual
dispatch. It generates Syft SPDX SBOMs, signs them keylessly with Cosign using
OIDC, and pairs release artifacts with SLSA provenance.

## Framework compliance review

`.github/workflows/framework-compliance-review.yml` runs on pull requests. It
invokes the framework-compliance-reviewer Copilot custom agent to review the
repository against the AI Agent Risk Management framework, posts the review as a
PR comment, and adds a `compliance reviewed` label. It skips pull requests that
already carry the label; remove the label to force a re-review. It requires an
organization-level Actions secret `COPILOT_CLI_TOKEN` and consumes Copilot usage
quota.

## Provision new repository

`.github/workflows/provision-new-repo.yml` is the self-service workflow for
creating and securing new repositories from the template. It is triggered by
manual dispatch and gated behind the `repo-provisioning` environment approval.
This workflow exists only in golden-repo and is removed from every generated
repository. See [Provisioning](provisioning.md).

## Dependabot

`.github/dependabot.yml` is configuration, not a workflow. It schedules weekly
version updates for GitHub Actions and pip dependencies under `tools/`, grouped
and labeled `dependencies`. Additional ecosystems such as npm and docker are
present but commented out and can be enabled once their manifest files exist.

## Required status checks

The following checks are required for merge on protected branches:

- `test`
- `build`
- `analyze`
- `gitleaks`

See [Branch protection](branch-protection.md) for the full baseline.
