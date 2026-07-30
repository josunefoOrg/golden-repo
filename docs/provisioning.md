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

1. Create or reuse the repository from `<yourGitHubOrganization>/golden-repo`.
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

## Seeding a StartRight-created repository

In environments where repositories can only be created through 1ES StartRight
(for example EAG / the `mcaps-microsoft` organization), StartRight creates the new
GitHub repository and the golden-repo template is pushed into it as the initial
commit. StartRight repo creation is performed separately; this repository only
performs the content push.

- `tools/seed_repo.py`: exports this repository's tracked structure (without git
  history, via `git archive`) and pushes it to an already-created target
  repository as its initial commit. Provisioning-only files are excluded by
  default so the seeded repository does not carry the seeding tooling.
- `.github/workflows/seed-target-repo.yml`: self-service `workflow_dispatch`
  wrapper, gated behind the `repo-provisioning` environment.

The flow is:

1. StartRight creates the empty target repository in the same organization.
2. This workflow (or `tools/seed_repo.py` locally) pushes the golden-repo
   structure to the target as the `main` initial commit.

No GitHub App is required. The push is authenticated with a token supplied in the
`TARGET_REPO_TOKEN` environment variable (a fine-grained PAT with `Contents: write`
on the target repository), or by passing a ready-to-use `--target-url` such as an
SSH URL backed by a deploy key.

### One-time setup for the seeding workflow

Two setup steps gate `.github/workflows/seed-target-repo.yml`:

1. **The `repo-provisioning` environment** must exist on this repository (it is
   shared with `provision-new-repo.yml`). Create/update it with
   `tools/setup_environment.py` (see [Configuration](configuration.md)) rather
   than the UI; this step is fully automatable.
2. **The `TARGET_REPO_TOKEN` secret** must be set once the target repository
   exists. Minting the credential (a fine-grained PAT scoped to `Contents: write`
   on that specific repository, or an org/SSH deploy key) requires a human with
   the appropriate GitHub permissions and cannot be scripted end-to-end, because
   the token does not exist until an authorized person creates it. Storing the
   resulting value as a secret is scriptable:

   ```bash
   gh secret set TARGET_REPO_TOKEN --repo <org>/golden-repo --body "<token-value>"
   ```

### Command-line seeding

```bash
TARGET_REPO_TOKEN=<token> \
  python tools/seed_repo.py \
    --target-repo <org>/<name> \
    --target-branch main \
    --commit-message "Initial import from golden-repo template"
```

Useful options: `--exclude PATH` (repeatable) and `--exclude-file FILE` to drop
additional paths, `--no-default-excludes` to keep every tracked file, `--force` to
replace an existing seed commit, `--source-ref REF` to seed a ref other than
`HEAD`, and `--dry-run` to print the steps without pushing. Run
`python tools/seed_repo.py --help` for the full list.

If the target's `main` branch is already protected, push to a feature branch
(`--target-branch <branch>`) and open a pull request instead of pushing to `main`.

## Plan tier limitation

Branch protection on private repositories requires a paid GitHub plan (Team or
Enterprise). On the Free plan, GitHub returns HTTP 403 and the branch-protection
step fails. All other provisioning steps work on any plan. Provision into a
paid-plan organization or a public repository to exercise branch protection. See
[Troubleshooting](troubleshooting.md).
