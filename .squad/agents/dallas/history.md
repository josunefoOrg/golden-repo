# Project Context

- **Owner:** Jordi Sune
- **Project:** golden-repo — turn the `controlforge` repo (infra/, src/, docs/, tools/) into a reusable GitHub *template* repository, plus tooling to provision new agent/security-tooling repos (e.g. SOCBot, PostureIQ-style) securely and repeatably.
- **Stack:** GitHub Actions, Python (PyGithub / gh CLI), CodeQL, gitleaks/secret-scanning, Syft SBOM, Cosign signing, SLSA L3, GitHub App + OIDC auth.
- **Test org:** https://github.com/josunefoOrg
- **Created:** 2026-07-16

## Learnings

<!-- Append new learnings below. Each entry is something lasting about the project. -->

### 2026-07-16 — Security workflow baseline

- Created `.github\workflows\codeql.yml` with required job/check id `analyze`; CodeQL advanced setup scans Python and JavaScript/TypeScript when those language files are present.
- Created `.github\workflows\secret-scan.yml` with required job/check id `gitleaks`; Gitleaks runs fail-closed and complements repo-level GitHub secret scanning plus push protection.
- Created `.github\workflows\sbom-signing.yml` with required job/check id `sbom`; Syft generates SPDX JSON and CycloneDX SBOMs, and Cosign signs SBOMs plus `dist` and `build` artifacts keylessly through GitHub OIDC.
- Added `.gitleaks.toml` extending the Gitleaks default rule set without sensitive allowlists.
- **Phase 1 complete:** Delivered fail-closed security scanning and SLSA L3-aligned artifact signing for the template team.
