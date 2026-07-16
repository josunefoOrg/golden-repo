# Branch protection baseline

This is the authoritative `main` branch-protection baseline for repositories generated from `josunefoOrg/golden-repo`.

## Required baseline for `main`

- Pull request reviews:
  - At least 1 approval.
  - Require Code Owner review.
  - Dismiss stale approvals when new commits are pushed.
- Required status checks:
  - Strict mode enabled, so branches must be up to date before merge.
  - Exact required check contexts:
    - `test`
    - `build`
    - `analyze`
    - `gitleaks`
- Require signed commits.
- No force pushes.
- No branch deletion.
- Enforce protection for administrators.
- Restrict push access to the `maintainers` team.

## Manual application with `gh api`

Set these variables first:

```powershell
$org = "josunefoOrg"
$repo = "REPLACE_WITH_REPO_NAME"
$branch = "main"
```

Apply branch protection:

```powershell
$body = @'
{
  "required_status_checks": {
    "strict": true,
    "contexts": [
      "test",
      "build",
      "analyze",
      "gitleaks"
    ]
  },
  "enforce_admins": true,
  "required_pull_request_reviews": {
    "dismiss_stale_reviews": true,
    "require_code_owner_reviews": true,
    "required_approving_review_count": 1
  },
  "restrictions": {
    "users": [],
    "teams": [
      "maintainers"
    ],
    "apps": []
  },
  "required_linear_history": false,
  "allow_force_pushes": false,
  "allow_deletions": false,
  "block_creations": false,
  "required_conversation_resolution": false,
  "lock_branch": false,
  "allow_fork_syncing": false
}
'@

$body | gh api `
  -X PUT `
  -H "Accept: application/vnd.github+json" `
  -H "X-GitHub-Api-Version: 2022-11-28" `
  "/repos/$org/$repo/branches/$branch/protection" `
  --input -
```

Require signed commits:

```powershell
gh api `
  -X POST `
  -H "Accept: application/vnd.github+json" `
  -H "X-GitHub-Api-Version: 2022-11-28" `
  "/repos/$org/$repo/branches/$branch/protection/required_signatures"
```

Verify the effective protection:

```powershell
gh api `
  -H "Accept: application/vnd.github+json" `
  -H "X-GitHub-Api-Version: 2022-11-28" `
  "/repos/$org/$repo/branches/$branch/protection"
```

## Equivalent JSON body for `PUT /repos/{org}/{repo}/branches/main/protection`

Signed commits are not part of the `PUT /branches/{branch}/protection` JSON body. They must be enabled with `POST /repos/{org}/{repo}/branches/main/protection/required_signatures` after the PUT request.

```json
{
  "required_status_checks": {
    "strict": true,
    "contexts": [
      "test",
      "build",
      "analyze",
      "gitleaks"
    ]
  },
  "enforce_admins": true,
  "required_pull_request_reviews": {
    "dismiss_stale_reviews": true,
    "require_code_owner_reviews": true,
    "required_approving_review_count": 1
  },
  "restrictions": {
    "users": [],
    "teams": [
      "maintainers"
    ],
    "apps": []
  },
  "required_linear_history": false,
  "allow_force_pushes": false,
  "allow_deletions": false,
  "block_creations": false,
  "required_conversation_resolution": false,
  "lock_branch": false,
  "allow_fork_syncing": false
}
```
