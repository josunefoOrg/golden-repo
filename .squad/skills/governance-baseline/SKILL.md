---
name: "governance-baseline"
description: "Create standards-aligned OSS governance files for golden-repo template repositories"
domain: "docs-governance"
confidence: "high"
source: "lambert"
---

## Pattern

When creating governance files for golden-repo, keep content template-generic and align it to the locked project contract in `.squad/decisions.md`.

Use these defaults unless a later decision overrides them:

- Organization: `josunefoOrg`.
- License: MIT, marked as swappable where summarized.
- Branch protection checks: `test`, `build`, `analyze`, `gitleaks`.
- Branch protection: at least 1 approval, stale approval dismissal, Code Owner review, strict required checks, signed commits, no force-push, no branch deletion, admins enforced, push restricted to maintainers.
- Security placeholders: `<security-email>` and `<conduct-email>`.

## Style

- Use concise governance language.
- Use plain hyphens.
- Do not use emojis or em dashes.
- Mark unknown production values with angle-bracket placeholders.

## Files owned by docs and governance

- `README.md`
- `CONTRIBUTING.md`
- `SECURITY.md`
- `CODE_OF_CONDUCT.md`
- `LICENSE`
- `CODEOWNERS`
- `.github/ISSUE_TEMPLATE/*.yml`
- `.github/PULL_REQUEST_TEMPLATE.md`
