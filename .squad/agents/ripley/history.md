# Project Context

- **Owner:** Jordi Sune
- **Project:** golden-repo — turn the `controlforge` repo (infra/, src/, docs/, tools/) into a reusable GitHub *template* repository, plus tooling to provision new agent/security-tooling repos (e.g. SOCBot, PostureIQ-style) securely and repeatably.
- **Stack:** GitHub Actions, Python (PyGithub / gh CLI), CodeQL, gitleaks/secret-scanning, Syft SBOM, Cosign signing, SLSA L3, GitHub App + OIDC auth.
- **Test org:** https://github.com/josunefoOrg
- **Created:** 2026-07-16

## Learnings

<!-- Append new learnings below. Each entry is something lasting about the project. -->

### 2026-07-16

- The architecture docs now define golden-repo as both the template source and the self-service provisioning control point for `josunefoOrg`.
- Signed commits require the separate GitHub REST endpoint `POST /repos/{org}/{repo}/branches/{branch}/protection/required_signatures`; they are not part of the branch protection PUT JSON body.
- The `repo-provisioning` environment is the manual approval gate before privileged App-token provisioning runs.
- **Phase 1 complete:** Ripley led a five-member team (Ripley, Parker, Dallas, Brett, Lambert) to build a secure GitHub template repo with provisioning tooling. Ready for live test.
