---
title: Troubleshooting
layout: default
nav_order: 11
---

# Troubleshooting

Common issues seen during provisioning and GitHub Pages setup, with fixes.

## Branch protection fails with HTTP 403 on the Free plan

Branch protection on private repositories requires a paid GitHub plan (Team or
Enterprise). On the Free plan, GitHub returns HTTP 403 with a message to upgrade
or make the repository public, and the branch-protection step fails. This is a
GitHub platform limitation, not a provisioner defect. Provision into a paid-plan
organization or a public repository to exercise branch protection. All other
provisioning steps work on any plan.

## Team creation fails with HTTP 403

The provisioning GitHub App or token needs the organization Members permission set
to read and write. Members read-only causes a 403 when the provisioner creates the
per-repository admin team. Update the App permission and reinstall if needed. See
[Configuration](configuration.md).

## CodeQL reports a configuration error

The template uses an advanced CodeQL workflow (`.github/workflows/codeql.yml` with
the `analyze` job). Do not enable CodeQL default setup in the repository UI:
default setup conflicts with the advanced workflow and produces a configuration
error. Keep default setup disabled and rely on the workflow.

## Pages placeholder commit fails with HTTP 409

If GitHub Pages enablement runs after branch protection is applied, committing the
placeholder page to `main` is rejected with HTTP 409 because the protected branch
requires signed commits and a pull request. The provisioner enables Pages before
applying branch protection to avoid this. If you customize the provisioning order,
keep any direct commit to `main` ahead of branch protection.

## GitHub Pages is not enabled on a provisioned repository

Pages is enabled only for repositories that are not private. Private repositories
skip Pages by design, and the provisioning summary records the skip. To publish
Pages, provision the repository as public or internal.

## Provisioned repository shows the golden-repo documentation site

It should not. The provisioner resets a provisioned repository's `docs/` folder to
a single placeholder landing page, so the full golden-repo documentation site is
not carried over. If you see the full site, re-run the provisioner to converge the
repository to the baseline.

## The docs site did not update after a merge

GitHub Pages builds asynchronously. After merging to `main`, allow a short time
for the Pages build to complete. Check the latest Pages build status in the
repository settings or through the Pages API.
