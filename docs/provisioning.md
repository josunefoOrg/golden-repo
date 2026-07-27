---
title: Provisioning
layout: default
nav_order: 3
---

# Provisioning

New repositories are provisioned in one of two ways:

- `tools/provision_repo.py`: command-line provisioning for repository settings,
  security features, branch protection, and team access.
- `.github/workflows/provision-new-repo.yml`: a self-service GitHub Actions
  workflow for creating and securing repositories from this template, gated
  behind a manual approval environment.

The provisioner is idempotent. It is safe to re-run and converges the target
repository toward the baseline.

## Command-line provisioning

```bash
GITHUB_TOKEN=<github-app-installation-token> \
  python tools/provision_repo.py \
    --org <org> \
    --name <name> \
    --visibility <private|internal|public> \
    --description "<description>" \
    --topics "agent,security"
```

Cross-platform wrappers are available: `tools/provision_repo.ps1` (PowerShell)
and `tools/provision_repo.sh` (bash). Both call the same Python engine.

### Common options

| Option | Purpose |
| ------ | ------- |
| `--visibility` | `private`, `internal`, or `public`. Controls GitHub Pages (see below). |
| `--team` | Team slug to grant access. Repeat for multiple teams. |
| `--new-team` | Dedicated team to create or reuse. Default: `<name>-admins`. |
| `--no-new-team` | Do not create the dedicated team; `--team` grants still apply. |
| `--topics` | Comma-separated repository topics. |
| `--dry-run` | Print the intended API calls without mutating GitHub. |

Run `python tools/provision_repo.py --help` for the full list.

## What provisioning does

The provisioning flow performs these steps in order:

1. Create or reuse the repository from `josunefoOrg/golden-repo`.
2. Wait for template population to stabilize.
3. Replace `README.md` with the placeholder template.
4. Remove `provision-new-repo.yml` from the generated repository. The
   provisioning workflow exists only in golden-repo and must not run inside a
   provisioned repo.
5. Enable GitHub Pages for non-private repositories (see below).
6. Update the repository description, visibility, and topics.
7. Create or reuse the team and grant repository access.
8. Apply the [branch protection baseline](branch-protection.md).
9. Enable [security features](security.md).

## GitHub Pages

For repositories that are not private (public and internal), the provisioner
enables GitHub Pages and publishes a single placeholder landing page. The site is
served from the `main` branch `/docs` folder.

- Private repositories skip Pages and record the skip in the provisioning
  summary.
- Provisioned repositories keep the placeholder page only. The golden-repo
  documentation site is not carried into provisioned repositories: the
  provisioner resets the generated repository's `docs/` folder to the placeholder
  landing page.

The Pages enablement runs before branch protection is applied. The placeholder
page is committed to `main` through the Contents API, and a protected `main`
would reject that direct commit.

## Self-service workflow

`.github/workflows/provision-new-repo.yml` is the controlled interface for
repository creation:

1. A developer starts the workflow with `workflow_dispatch` and supplies inputs.
2. The job targets the `repo-provisioning` GitHub Environment.
3. Required reviewers approve the deployment, which releases the provisioning job.
4. The workflow exchanges the stored GitHub App credentials for a short-lived
   installation token and runs the provisioner.

See [Configuration](configuration.md) for the one-time environment, variable, and
secret setup the workflow requires.

## Plan tier limitation

Branch protection on private repositories requires a paid GitHub plan (Team or
Enterprise). On the Free plan, GitHub returns HTTP 403 and the branch-protection
step fails. All other provisioning steps work on any plan. Provision into a
paid-plan organization or a public repository to exercise branch protection. See
[Troubleshooting](troubleshooting.md).
