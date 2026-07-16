# Repository provisioning tool

`tools/provision_repo.py` creates a repository from `josunefoOrg/golden-repo`
and reapplies the required settings every time it runs. It is idempotent: if the
repository already exists, template generation is skipped and settings,
security controls, branch protection, and team grants are updated in place. It
fails loudly: any unexpected GitHub API response exits non-zero with the HTTP
status and response body.

By default, each run also creates or reuses a dedicated repository team named
`<name>-admins` and grants it `maintain` access. Use `--new-team` to choose a
custom slug, `--new-team-permission` to set `pull`, `push`, `maintain`, or
`admin`, `--new-team-member` to seed org members, or `--no-new-team` to opt out.
Existing `--team` grants are also create-if-missing, so the tool can run against
orgs where teams have not been pre-created.

Dedicated-team flags:

- `--new-team <slug>` — create/reuse this dedicated team instead of the default
  `<name>-admins`.
- `--new-team-permission <pull|push|maintain|admin>` — permission granted to the
  dedicated team; default `maintain`.
- `--new-team-member <login>` — add an org member to the dedicated team; repeat
  for multiple members.
- `--no-new-team` — skip dedicated-team creation while still honoring `--team`
  grants.

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
- Organization **Members: read/write** — create/reuse teams, grant team repo
  permissions, and optionally add org members to the dedicated team.

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
  --new-team-member josunefon `
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

With a custom dedicated team and seeded members:

```powershell
cd C:\GIT\golden-repo
$env:GITHUB_TOKEN = gh auth token
python tools\provision_repo.py `
  --name demo-svc `
  --org josunefoOrg `
  --visibility private `
  --new-team demo-platform-admins `
  --new-team-permission maintain `
  --new-team-member josunefon `
  --new-team-member another-member `
  --team maintainers `
  --description "Demo service"
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

## Standalone local provisioning

Use the standalone wrappers when you want to provision or test a repository from
your own machine instead of the self-service pipeline. Both wrappers are
idempotent and fail loudly with clear errors if prerequisites, authentication,
or GitHub API calls fail. They install `tools/requirements.txt`, resolve paths
from the wrapper location, and forward to `tools/provision_repo.py`.

Token resolution order is:

1. Explicit wrapper token (`-Token` in PowerShell or `--token` in Bash).
2. `GITHUB_TOKEN` from the environment. Use a GitHub App installation token or
   an OIDC-derived token for production-like runs.
3. `gh auth token` for local testing when you are signed in with GitHub CLI.

PowerShell dry run:

```powershell
cd C:\GIT\golden-repo
.\tools\provision_repo.ps1 `
  -Name socbot `
  -Org josunefoOrg `
  -Visibility private `
  -Team maintainers,socbot-developers `
  -NewTeamMember josunefon `
  -Description "SOC automation bot" `
  -Topics "security,agent,python" `
  -DryRun
```

PowerShell real run:

```powershell
cd C:\GIT\golden-repo
.\tools\provision_repo.ps1 `
  -Name postureiq `
  -Org josunefoOrg `
  -Visibility private `
  -Team maintainers `
  -Description "Posture management automation" `
  -Topics "security,posture,automation"
```

Bash dry run:

```bash
cd /path/to/golden-repo
./tools/provision_repo.sh \
  --name socbot \
  --org josunefoOrg \
  --visibility private \
  --team maintainers \
  --team socbot-developers \
  --new-team-member josunefon \
  --description "SOC automation bot" \
  --topics "security,agent,python" \
  --dry-run
```

Bash real run:

```bash
cd /path/to/golden-repo
./tools/provision_repo.sh \
  --name postureiq \
  --org josunefoOrg \
  --visibility private \
  --team maintainers \
  --description "Posture management automation" \
  --topics "security,posture,automation"
```

## Running from the pipeline

The self-service pipeline is `.github/workflows/provision-new-repo.yml`. Its
setup is documented in the repository README and `docs/SETUP.md`.
