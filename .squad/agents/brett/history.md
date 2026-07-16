# Project Context

- **Owner:** Jordi Sune
- **Project:** golden-repo — turn the `controlforge` repo (infra/, src/, docs/, tools/) into a reusable GitHub *template* repository, plus tooling to provision new agent/security-tooling repos (e.g. SOCBot, PostureIQ-style) securely and repeatably.
- **Stack:** GitHub Actions, Python (PyGithub / gh CLI), CodeQL, gitleaks/secret-scanning, Syft SBOM, Cosign signing, SLSA L3, GitHub App + OIDC auth.
- **Test org:** https://github.com/josunefoOrg
- **Created:** 2026-07-16

## Learnings

<!-- Append new learnings below. Each entry is something lasting about the project. -->

### 2026-07-16: Implemented `tools/provision_repo.py`

- Exact CLI contract implemented:
  `python tools/provision_repo.py --name <repo> --org <org> --visibility <private|internal|public> --team <team-slug> [--team <another>] [--description <text>] [--topics <csv>] [--template-owner josunefoOrg] [--template-repo golden-repo] [--codeowners-override <path>] [--dry-run]`.
- REST endpoints used: `POST /repos/{template_owner}/{template_repo}/generate`, `GET/PATCH /repos/{org}/{repo}`, `PUT /repos/{org}/{repo}/topics`, `GET /repos/{org}/{repo}/branches/main`, `PUT /repos/{org}/{repo}/branches/main/protection`, `POST /repos/{org}/{repo}/branches/main/protection/required_signatures`, `PUT /repos/{org}/{repo}/vulnerability-alerts`, `PUT /repos/{org}/{repo}/automated-security-fixes`, `PATCH /repos/{org}/{repo}/code-scanning/default-setup`, and `PUT /orgs/{org}/teams/{team_slug}/repos/{org}/{repo}`.
- Idempotency approach: treat template generation `422` "already exists" as non-fatal, then continue with `PATCH`/`PUT` settings, security, branch protection, and team permissions. All unexpected API responses abort with status and body.
- GHAS-sensitive features: secret scanning, secret scanning push protection, and CodeQL default setup may require GitHub Advanced Security for private/internal repositories.
- **Phase 1 complete:** Delivered production-ready provisioning script with idempotent template generation and security feature enablement.
