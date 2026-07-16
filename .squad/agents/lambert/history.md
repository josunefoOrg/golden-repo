# Project Context

- **Owner:** Jordi Sune
- **Project:** golden-repo — turn the `controlforge` repo (infra/, src/, docs/, tools/) into a reusable GitHub *template* repository, plus tooling to provision new agent/security-tooling repos (e.g. SOCBot, PostureIQ-style) securely and repeatably.
- **Stack:** GitHub Actions, Python (PyGithub / gh CLI), CodeQL, gitleaks/secret-scanning, Syft SBOM, Cosign signing, SLSA L3, GitHub App + OIDC auth.
- **Test org:** https://github.com/josunefoOrg
- **Created:** 2026-07-16

## Learnings

<!-- Append new learnings below. Each entry is something lasting about the project. -->


- 2026-07-16: Created governance baseline files for the template repository: README.md, CONTRIBUTING.md, SECURITY.md, CODE_OF_CONDUCT.md, LICENSE, CODEOWNERS, .github/ISSUE_TEMPLATE/bug_report.yml, .github/ISSUE_TEMPLATE/feature_request.yml, and .github/PULL_REQUEST_TEMPLATE.md.
- 2026-07-16: Introduced placeholder values <security-email> and <conduct-email>; CODEOWNERS teams are documented placeholders that must exist in josunefoOrg.
- 2026-07-16: Standards used: MIT License, Contributor Covenant v2.1, Conventional Commits, GitHub issue forms, GitHub CODEOWNERS, and the locked branch protection baseline with checks test, build, analyze, and gitleaks.
- 2026-07-16: **Phase 1 complete:** Delivered community standards and governance framework for a professional template repository.
- 2026-07-16: Documented the required `repo-provisioning` GitHub Environment approval gate and org Actions credentials for the self-service provisioning workflow.
