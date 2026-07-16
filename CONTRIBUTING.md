# Contributing

Thank you for contributing to repositories generated from golden-repo. Keep changes small, reviewed, and aligned with the secure baseline.

## Local development setup

Use Python 3.11 for repository tooling.

```bash
python --version
python -m pip install -r tools/requirements.txt
```

Run project checks before opening a pull request. Generated repositories may add more checks, but the protected baseline checks are `test`, `build`, `analyze`, and `gitleaks`.

## Branch naming

Use one of these prefixes:

- `feat/` for new features.
- `fix/` for bug fixes.
- `chore/` for maintenance.
- `docs/` for documentation-only changes.
- `refactor/` for behavior-preserving code changes.

Examples:

```text
feat/add-slack-notifier
fix/token-refresh-error
docs/update-security-policy
```

## Commit messages

Use Conventional Commits.

Format:

```text
<type>(optional-scope): <description>
```

Common types:

- `feat` - introduces a new feature.
- `fix` - fixes a bug.
- `docs` - changes documentation only.
- `chore` - maintenance or tooling changes.
- `refactor` - changes code without changing behavior.
- `test` - adds or updates tests.
- `build` - changes build or dependency configuration.
- `ci` - changes continuous integration configuration.

Examples:

```text
feat(provisioning): enable CodeQL default setup
fix(auth): reject expired installation tokens
docs(security): clarify disclosure process
chore(deps): update tooling dependencies
```

Breaking changes must be marked with `!` or a `BREAKING CHANGE:` footer.

```text
feat(api)!: replace legacy repository options

BREAKING CHANGE: repository settings now require explicit team slugs.
```

## Pull request process

1. Create a branch using the naming rules above.
2. Make focused changes with Conventional Commits.
3. Sign all commits.
4. Open a pull request with a clear summary and linked issue when applicable.
5. Ensure required checks pass: `test`, `build`, `analyze`, and `gitleaks`.
6. Obtain at least 1 Code Owner approval.
7. Keep the branch up to date with the protected base branch.

Pull requests must not bypass required review, signed commits, or security checks.
