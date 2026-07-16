# Project Context

- **Owner:** Jordi Sune
- **Project:** golden-repo — turn the `controlforge` repo (infra/, src/, docs/, tools/) into a reusable GitHub *template* repository, plus tooling to provision new agent/security-tooling repos (e.g. SOCBot, PostureIQ-style) securely and repeatably.
- **Stack:** GitHub Actions, Python (PyGithub / gh CLI), CodeQL, gitleaks/secret-scanning, Syft SBOM, Cosign signing, SLSA L3, GitHub App + OIDC auth.
- **Test org:** https://github.com/josunefoOrg
- **Created:** 2026-07-16

## Learnings

<!-- Append new learnings below. Each entry is something lasting about the project. -->

### 2026-07-16 — CI, Dependabot, and self-service provisioning workflow

- Created `.github/workflows/ci.yml` with stable required status check job/context names `test` and `build`.
- Created `.github/dependabot.yml` for weekly `github-actions` (`/`), `pip` (`/tools`), `npm` (`/`), and `docker` (`/`) updates, grouped for minor/patch and labeled `dependencies`.
- Created `.github/workflows/provision-new-repo.yml` using a short-lived GitHub App token from `actions/create-github-app-token@v1`; no PATs are used.
- Assumed provisioning script CLI: `python tools/provision_repo.py --name "<repo_name>" --org "josunefoOrg" --visibility "<private|internal|public>" --team "<team-slug>" [--description "<description>"] [--topics "<comma-separated topics>"]`.
- Required org variable/secret: `PROVISIONER_APP_ID` and `PROVISIONER_APP_PRIVATE_KEY`.
- Manual setup remains required for the `repo-provisioning` environment with required reviewers.
- **Phase 1 complete:** Led provisioning workflow design and CI/CD automation for the template repository team effort.
