# Repository provisioning tool

`tools/provision_repo.py` creates a repository from `josunefoOrg/golden-repo`
and reapplies the required settings every time it runs. It is idempotent: if the
repository already exists, template generation is skipped and settings,
security controls, branch protection, and team grants are updated in place. It
fails loudly: any unexpected GitHub API response exits non-zero with the HTTP
status and response body.

## Install

```powershell
cd C:\GIT\golden-repo
python -m pip install -r tools\requirements.txt
```

## Authentication

The script reads `GITHUB_TOKEN` from the environment. Use a GitHub App
installation token or an OIDC-derived token. For local testing with the GitHub
CLI, you can use:

```powershell
cd C:\GIT\golden-repo
$env:GITHUB_TOKEN = gh auth token
python tools\provision_repo.py --help
```

Required GitHub App/token permissions:

- Repository **Administration: read/write** — create from template, update
  settings, branch protection, vulnerability alerts, and team repo permissions.
- Repository **Contents: read/write** — read the template and support generated
  repository contents.
- Repository **Metadata: read** — required by GitHub Apps.
- Repository **Code scanning alerts: read/write** — configure CodeQL default
  setup.
- Repository **Secret scanning alerts: read/write** — enable secret scanning and
  push protection where available.
- Repository **Dependabot alerts: read/write** — enable Dependabot alerts and
  automated security updates.
- Organization **Members: read** — resolve teams by slug for least-privilege
  team grants.

Secret scanning, push protection, and CodeQL default setup may require GitHub
Advanced Security for private or internal repositories.

## Examples

Dry run:

```powershell
cd C:\GIT\golden-repo
$env:GITHUB_TOKEN = gh auth token
python tools\provision_repo.py `
  --name socbot `
  --org josunefoOrg `
  --visibility private `
  --team maintainers `
  --team socbot-developers `
  --description "SOC automation bot" `
  --topics "security,agent,python" `
  --dry-run
```

Provision for real:

```powershell
cd C:\GIT\golden-repo
$env:GITHUB_TOKEN = gh auth token
python tools\provision_repo.py `
  --name postureiq `
  --org josunefoOrg `
  --visibility private `
  --team maintainers `
  --description "Posture management automation" `
  --topics "security,posture,automation"
```

With explicit template and a CODEOWNERS override note:

```powershell
cd C:\GIT\golden-repo
$env:GITHUB_TOKEN = gh auth token
python tools\provision_repo.py `
  --name agent-tooling `
  --org josunefoOrg `
  --visibility internal `
  --team maintainers `
  --template-owner josunefoOrg `
  --template-repo golden-repo `
  --codeowners-override .\CODEOWNERS `
  --description "Agent tooling repository" `
  --topics "agent,tooling"
```

`--codeowners-override` is reported in the summary only. Apply CODEOWNERS
changes through a normal commit or pull request; the provisioner never rewrites
history.
