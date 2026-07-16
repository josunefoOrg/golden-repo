# Squad Decisions

## Active Decisions

### 2026-07-16: Provisioning contract & filled-in placeholders (by Squad/Ripley)

These resolve the "fill in" items in the request. Assumptions stated because the user was unavailable to confirm; all are documented and easy to change.

- **Platform:** GitHub.com (the test org is on github.com). GHES differences noted where relevant.
- **Org name:** `josunefoOrg` (the user's test org). Template repo = `josunefoOrg/golden-repo`. golden-repo also acts as the central "platform" repo hosting the self-service workflow.
- **License:** MIT (generic, permissive template default; clearly flagged as swappable).
- **Team access:** passed as INPUT to script + workflow (reusable), with documented defaults. No individual admin grants — team-based only.
- **Template source dirs:** `infra/`, `src/`, `docs/`, `tools/` are scaffolded as coherent placeholders (README/.gitkeep) since upstream controlforge code is out of scope ("ignore repo-only files").

**Auth model (no long-lived PATs):**
- Workflows: GitHub App installation token via `actions/create-github-app-token`.
- Script `tools/provision_repo.py`: reads token from `GITHUB_TOKEN` env (produced by App token / OIDC exchange). Never hardcodes a PAT.
- Manual one-time setup (cannot be scripted): register org-level GitHub App with permissions — Repository administration (RW), Contents (RW), Metadata (R), Actions (RW), Code scanning alerts (RW), Secret scanning alerts (RW), Dependabot alerts (RW), Members/Org (R for teams). Install on the org; store App ID + private key as org secrets/variables.

**Branch-protection baseline for `main` (single source of truth):**
- PR reviews: ≥1 approval, dismiss stale approvals, require Code Owner review.
- Required status checks (strict / up-to-date), exact contexts: `test`, `build`, `analyze`, `gitleaks`.
- Require signed commits. No force-push. No branch deletion. Enforce for admins.
- Restrict push to the maintainers team (least-privilege).

**Standard workflow job/context names (all agents must match exactly):**
- `ci.yml` -> jobs `test`, `build`
- `codeql.yml` -> job `analyze`
- `secret-scan.yml` -> job `gitleaks`
- `sbom-signing.yml` -> job `sbom` (release/tag-triggered; Syft SBOM + Cosign keyless signing, SLSA L3 aligned)

**Security features enabled by provisioning:** Dependabot alerts + security updates, secret scanning, secret scanning push protection, CodeQL default setup.

### 2026-07-16: Ripley decision — provisioning documentation refinements

- Treat signed commits as a separate branch-protection API operation from `PUT /branches/{branch}/protection`; GitHub exposes signed commits through `POST /branches/{branch}/protection/required_signatures`.
- Document `repo-provisioning` as the approval gate for privileged provisioning and require a team reviewer, preferably `maintainers` or `platform-team`.
- Keep GHAS enablement explicitly manual because licensing and org policy determine whether private repo CodeQL and secret scanning features are available.

**Rationale:** These refinements preserve the locked branch-protection contract while making the runbook copy-pasteable against GitHub's actual REST API shape. They also keep one-time trust-anchor and licensing steps visible instead of hiding them inside automation that cannot reliably or safely complete them.

### 2026-07-16: Parker decision — provisioning CLI contract

The self-service workflow `.github/workflows/provision-new-repo.yml` invokes Brett's provisioning script as:

```bash
python tools/provision_repo.py \
  --name "<repo_name>" \
  --org "josunefoOrg" \
  --visibility "<private|internal|public>" \
  --team "<team-slug>" \
  --description "<optional description>" \
  --topics "<optional comma-separated topics>"
```

The script reads its short-lived GitHub App installation token from `GITHUB_TOKEN`. `--team` is repeatable by script contract; `--description` and `--topics` are only passed when non-empty. The workflow creates the token with `actions/create-github-app-token@v1` using org variable `PROVISIONER_APP_ID` and org secret `PROVISIONER_APP_PRIVATE_KEY`. The workflow runs behind the manually configured `repo-provisioning` environment approval gate.

### 2026-07-16: Dallas decision — fail-closed security workflow baseline

- Required status-check job ids remain stable: `analyze` for CodeQL, `gitleaks` for secret scanning, and `sbom` for release/tag SBOM signing.
- Security scanners are configured fail-closed: CodeQL and Gitleaks failures fail their workflow jobs rather than warning only.
- Release SBOM signing uses GitHub OIDC with Cosign keyless signatures and certificates; no stored signing keys are introduced.
- SBOM generation emits both SPDX JSON and CycloneDX JSON so template consumers can satisfy sibling-repo SLSA L3-aligned evidence expectations.

### 2026-07-16: Brett decision — repository provisioner implementation

- Implemented provisioning with direct GitHub REST calls via `requests` for explicit control over template generation, security settings, branch protection, and CodeQL default setup.
- The provisioner reads only `GITHUB_TOKEN`; no PAT or token value is stored in code or docs.
- Team access remains least-privilege: slugs containing `maintain` receive `maintain`, all others receive `push`; branch push restrictions use maintainers-like slugs, or the first supplied team if no maintainers-like slug is present.
- CODEOWNERS overrides are summary-only because changing CODEOWNERS should happen through a normal commit or PR, not silent history rewrites during provisioning.

## Governance

- All meaningful changes require team consensus
- Document architectural decisions here
- Keep history focused on work, decisions focused on direction
