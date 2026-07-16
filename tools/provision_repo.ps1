<#
.SYNOPSIS
Provision a GitHub repository locally using tools/provision_repo.py.

.DESCRIPTION
Resolves a GitHub token from -Token, GITHUB_TOKEN, or gh auth token; installs
the Python requirements; and forwards arguments to the provisioning engine.

.EXAMPLE
.\tools\provision_repo.ps1 -Name socbot -Org josunefoOrg -Visibility private -Team maintainers,socbot-developers -Description "SOC automation bot" -Topics "security,agent,python" -DryRun

.EXAMPLE
.\tools\provision_repo.ps1 -Name postureiq -Org josunefoOrg -Visibility private -Team maintainers -Description "Posture management automation" -Topics "security,posture,automation" -Token $env:GITHUB_TOKEN
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [string]$Name,

    [Parameter(Mandatory)]
    [string]$Org,

    [ValidateSet('private','internal','public')]
    [string]$Visibility = 'private',

    [string[]]$Team,

    [string]$NewTeam,

    [ValidateSet('pull','push','maintain','admin')]
    [string]$NewTeamPermission = 'maintain',

    [string[]]$NewTeamMember,

    [switch]$NoNewTeam,

    [string]$Description,

    [string]$Topics,

    [string]$TemplateOwner = 'josunefoOrg',

    [string]$TemplateRepo = 'golden-repo',

    [string]$CodeownersOverride,

    [string]$Token,

    [switch]$DryRun
)

$ErrorActionPreference = 'Stop'

function Resolve-PythonCommand {
    if (Get-Command python -ErrorAction SilentlyContinue) {
        return 'python'
    }
    if (Get-Command py -ErrorAction SilentlyContinue) {
        return 'py'
    }
    Write-Error 'Python is required but was not found. Install Python and ensure python or py is on PATH.'
}

function Resolve-GitHubToken {
    param([string]$ExplicitToken)

    if ($ExplicitToken) {
        return $ExplicitToken
    }
    if ($env:GITHUB_TOKEN) {
        return $env:GITHUB_TOKEN
    }
    if (Get-Command gh -ErrorAction SilentlyContinue) {
        $ghToken = & gh auth token 2>$null
        if ($LASTEXITCODE -eq 0 -and $ghToken) {
            $joinedToken = ($ghToken -join '').Trim()
            if ($joinedToken) {
                return $joinedToken
            }
        }
    }
    Write-Error 'A GitHub token is required. Pass -Token, set GITHUB_TOKEN, or sign in with the GitHub CLI so gh auth token succeeds.'
}

$scriptDir = $PSScriptRoot
if (-not $scriptDir) {
    $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
}
$repoRoot = Split-Path -Parent $scriptDir
$enginePath = Join-Path $scriptDir 'provision_repo.py'
$requirementsPath = Join-Path $scriptDir 'requirements.txt'

if (-not (Test-Path -LiteralPath $enginePath -PathType Leaf)) {
    Write-Error "Provisioning engine not found: $enginePath"
}

$pythonCommand = Resolve-PythonCommand
$resolvedToken = Resolve-GitHubToken -ExplicitToken $Token

& $pythonCommand -m pip install --quiet -r $requirementsPath
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

$arguments = @(
    $enginePath,
    '--name', $Name,
    '--org', $Org,
    '--visibility', $Visibility,
    '--template-owner', $TemplateOwner,
    '--template-repo', $TemplateRepo
)

if ($Team) {
    foreach ($teamSlug in $Team) {
        if ($teamSlug) {
            $arguments += @('--team', $teamSlug)
        }
    }
}
if ($NewTeam) {
    $arguments += @('--new-team', $NewTeam)
}
if ($NewTeamPermission) {
    $arguments += @('--new-team-permission', $NewTeamPermission)
}
if ($NewTeamMember) {
    foreach ($memberLogin in $NewTeamMember) {
        if ($memberLogin) {
            $arguments += @('--new-team-member', $memberLogin)
        }
    }
}
if ($NoNewTeam) {
    $arguments += '--no-new-team'
}
if ($Description) {
    $arguments += @('--description', $Description)
}
if ($Topics) {
    $arguments += @('--topics', $Topics)
}
if ($CodeownersOverride) {
    $arguments += @('--codeowners-override', $CodeownersOverride)
}
if ($DryRun) {
    $arguments += '--dry-run'
}

$previousToken = $env:GITHUB_TOKEN
$hadPreviousToken = Test-Path Env:\GITHUB_TOKEN
$previousLocation = (Get-Location).Path
$exitCode = 0

try {
    $env:GITHUB_TOKEN = $resolvedToken
    Set-Location -LiteralPath $repoRoot
    & $pythonCommand @arguments
    $exitCode = $LASTEXITCODE
}
finally {
    Set-Location -LiteralPath $previousLocation
    if ($hadPreviousToken) {
        $env:GITHUB_TOKEN = $previousToken
    }
    else {
        Remove-Item Env:\GITHUB_TOKEN -ErrorAction SilentlyContinue
    }
}

exit $exitCode
