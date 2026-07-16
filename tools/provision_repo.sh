#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage: provision_repo.sh --name <repo> --org <org> [options]

Options:
  --name <repo>                    New repository name (required)
  --org <org>                      Target GitHub organization (required)
  --visibility <private|internal|public>
                                   Repository visibility (default: private)
  --team <slug>                    Team slug to grant; repeat for multiple teams
  --new-team <slug>                Dedicated team to create/reuse (default: <name>-admins)
  --new-team-permission <perm>     Dedicated team repo permission: pull, push, maintain, admin (default: maintain)
  --new-team-member <login>        Org member to add to dedicated team; repeat for multiple members
  --no-new-team                    Do not create the dedicated team
  --description <text>             Repository description
  --topics <csv>                   Comma-separated topics
  --template-owner <owner>         Template owner (default: josunefoOrg)
  --template-repo <repo>           Template repo (default: golden-repo)
  --codeowners-override <path>     CODEOWNERS override path to note in summary
  --token <token>                  GitHub token; otherwise GITHUB_TOKEN or gh auth token is used
  --dry-run                        Print planned API calls without mutating GitHub
  --help                           Show this help
USAGE
}

NAME=""
ORG=""
VISIBILITY="private"
DESCRIPTION=""
TOPICS=""
TEMPLATE_OWNER="josunefoOrg"
TEMPLATE_REPO="golden-repo"
CODEOWNERS_OVERRIDE=""
TOKEN_VALUE=""
DRY_RUN=0
TEAMS=()
NEW_TEAM=""
NEW_TEAM_PERMISSION="maintain"
NEW_TEAM_MEMBERS=()
NO_NEW_TEAM=0

require_value() {
  local flag="$1"
  local value="${2:-}"
  if [[ -z "$value" || "$value" == --* ]]; then
    echo "ERROR: $flag requires a value." >&2
    exit 2
  fi
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --name)
      require_value "$1" "${2:-}"
      NAME="$2"
      shift 2
      ;;
    --org)
      require_value "$1" "${2:-}"
      ORG="$2"
      shift 2
      ;;
    --visibility)
      require_value "$1" "${2:-}"
      VISIBILITY="$2"
      shift 2
      ;;
    --team)
      require_value "$1" "${2:-}"
      TEAMS+=("$2")
      shift 2
      ;;
    --new-team)
      require_value "$1" "${2:-}"
      NEW_TEAM="$2"
      shift 2
      ;;
    --new-team-permission)
      require_value "$1" "${2:-}"
      NEW_TEAM_PERMISSION="$2"
      shift 2
      ;;
    --new-team-member)
      require_value "$1" "${2:-}"
      NEW_TEAM_MEMBERS+=("$2")
      shift 2
      ;;
    --no-new-team)
      NO_NEW_TEAM=1
      shift
      ;;
    --description)
      require_value "$1" "${2:-}"
      DESCRIPTION="$2"
      shift 2
      ;;
    --topics)
      require_value "$1" "${2:-}"
      TOPICS="$2"
      shift 2
      ;;
    --template-owner)
      require_value "$1" "${2:-}"
      TEMPLATE_OWNER="$2"
      shift 2
      ;;
    --template-repo)
      require_value "$1" "${2:-}"
      TEMPLATE_REPO="$2"
      shift 2
      ;;
    --codeowners-override)
      require_value "$1" "${2:-}"
      CODEOWNERS_OVERRIDE="$2"
      shift 2
      ;;
    --token)
      require_value "$1" "${2:-}"
      TOKEN_VALUE="$2"
      shift 2
      ;;
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      echo "ERROR: Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ -z "$NAME" || -z "$ORG" ]]; then
  echo "ERROR: --name and --org are required." >&2
  usage >&2
  exit 2
fi

if [[ "$VISIBILITY" != "private" && "$VISIBILITY" != "internal" && "$VISIBILITY" != "public" ]]; then
  echo "ERROR: --visibility must be private, internal, or public." >&2
  exit 2
fi

if [[ "$NEW_TEAM_PERMISSION" != "pull" && "$NEW_TEAM_PERMISSION" != "push" && "$NEW_TEAM_PERMISSION" != "maintain" && "$NEW_TEAM_PERMISSION" != "admin" ]]; then
  echo "ERROR: --new-team-permission must be pull, push, maintain, or admin." >&2
  exit 2
fi

if [[ -z "$TOKEN_VALUE" && -n "${GITHUB_TOKEN:-}" ]]; then
  TOKEN_VALUE="$GITHUB_TOKEN"
fi

if [[ -z "$TOKEN_VALUE" ]] && command -v gh >/dev/null 2>&1; then
  if GH_TOKEN_OUTPUT="$(gh auth token 2>/dev/null)"; then
    TOKEN_VALUE="$(printf '%s' "$GH_TOKEN_OUTPUT" | tr -d '\r\n')"
  fi
fi

if [[ -z "$TOKEN_VALUE" ]]; then
  echo "ERROR: A GitHub token is required. Pass --token, set GITHUB_TOKEN, or sign in with the GitHub CLI so gh auth token succeeds." >&2
  exit 1
fi

if command -v python3 >/dev/null 2>&1; then
  PYTHON_CMD="python3"
elif command -v python >/dev/null 2>&1; then
  PYTHON_CMD="python"
else
  echo "ERROR: Python is required but was not found. Install Python and ensure python3 or python is on PATH." >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ENGINE_PATH="$SCRIPT_DIR/provision_repo.py"
REQUIREMENTS_PATH="$SCRIPT_DIR/requirements.txt"

if [[ ! -f "$ENGINE_PATH" ]]; then
  echo "ERROR: Provisioning engine not found: $ENGINE_PATH" >&2
  exit 1
fi

"$PYTHON_CMD" -m pip install --quiet -r "$REQUIREMENTS_PATH"

ARGS=(
  "$ENGINE_PATH"
  --name "$NAME"
  --org "$ORG"
  --visibility "$VISIBILITY"
  --template-owner "$TEMPLATE_OWNER"
  --template-repo "$TEMPLATE_REPO"
)

for team in "${TEAMS[@]}"; do
  ARGS+=(--team "$team")
done

if [[ -n "$NEW_TEAM" ]]; then
  ARGS+=(--new-team "$NEW_TEAM")
fi
ARGS+=(--new-team-permission "$NEW_TEAM_PERMISSION")
for member in "${NEW_TEAM_MEMBERS[@]}"; do
  ARGS+=(--new-team-member "$member")
done
if [[ "$NO_NEW_TEAM" -eq 1 ]]; then
  ARGS+=(--no-new-team)
fi

if [[ -n "$DESCRIPTION" ]]; then
  ARGS+=(--description "$DESCRIPTION")
fi
if [[ -n "$TOPICS" ]]; then
  ARGS+=(--topics "$TOPICS")
fi
if [[ -n "$CODEOWNERS_OVERRIDE" ]]; then
  ARGS+=(--codeowners-override "$CODEOWNERS_OVERRIDE")
fi
if [[ "$DRY_RUN" -eq 1 ]]; then
  ARGS+=(--dry-run)
fi

cd "$REPO_ROOT"
exec env GITHUB_TOKEN="$TOKEN_VALUE" "$PYTHON_CMD" "${ARGS[@]}"
