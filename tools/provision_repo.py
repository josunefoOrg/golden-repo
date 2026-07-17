"""Provision a GitHub repository from the golden-repo template.

The script is intentionally defensive: every required provisioning step logs
what it is doing, aborts on unexpected API errors, and can be safely re-run to
re-apply settings to an existing repository.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import requests


API_BASE_URL = "https://api.github.com"
API_VERSION = "2022-11-28"
DEFAULT_TEMPLATE_OWNER = "josunefoOrg"
DEFAULT_TEMPLATE_REPO = "golden-repo"
REQUIRED_CHECKS = ["test", "build", "analyze", "gitleaks"]
REPO_NAME_RE = re.compile(r"^[A-Za-z0-9_.-]{1,100}$")
ORG_OR_TEAM_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9-]{0,99}$")
TOPIC_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,49}$")


class ProvisioningError(RuntimeError):
    """Raised when provisioning cannot continue safely."""


class ApiError(ProvisioningError):
    """Raised for an unexpected GitHub API response."""

    def __init__(self, method: str, url: str, status: int, body: str) -> None:
        super().__init__(
            f"{method} {url} failed with HTTP {status}: {body or '<empty body>'}"
        )
        self.method = method
        self.url = url
        self.status = status
        self.body = body


@dataclass
class Summary:
    """Human-readable provisioning result emitted at the end."""

    repo_url: str = ""
    visibility: str = ""
    teams_created: list[str] = field(default_factory=list)
    teams_reused: list[str] = field(default_factory=list)
    teams_granted: list[str] = field(default_factory=list)
    team_members_added: list[str] = field(default_factory=list)
    team_member_warnings: list[str] = field(default_factory=list)
    branch_protection_applied: bool = False
    security_features_enabled: list[str] = field(default_factory=list)
    readme_replaced: bool = False
    provision_workflow_removed: bool = False
    skipped: list[str] = field(default_factory=list)


class GitHubClient:
    """Small REST client with dry-run support and clear API failures."""

    def __init__(self, token: str, dry_run: bool = False) -> None:
        self.dry_run = dry_run
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Accept": "application/vnd.github+json",
                "Authorization": "Bearer " + token,
                "User-Agent": "golden-repo-provisioner/1.0",
                "X-GitHub-Api-Version": API_VERSION,
            }
        )

    def request(
        self,
        method: str,
        path: str,
        *,
        body: dict[str, Any] | None = None,
        expected: tuple[int, ...] = (200,),
        accept: str | None = None,
    ) -> requests.Response | None:
        """Execute one API request or print it in dry-run mode."""

        url = f"{API_BASE_URL}{path}"
        body_summary = self._summarize_body(body)
        if self.dry_run:
            print(f"[dry-run] {method} {url} body={body_summary}")
            return None

        headers = {"Accept": accept} if accept else None
        response = self.session.request(
            method,
            url,
            json=body,
            headers=headers,
            timeout=30,
        )
        if response.status_code not in expected:
            raise ApiError(method, url, response.status_code, response.text)
        return response

    def request_allowing_statuses(
        self,
        method: str,
        path: str,
        *,
        body: dict[str, Any] | None = None,
        allowed: tuple[int, ...],
        accept: str | None = None,
    ) -> tuple[int, dict[str, Any] | str | None]:
        """Execute an API request where the caller handles selected statuses."""

        url = f"{API_BASE_URL}{path}"
        body_summary = self._summarize_body(body)
        if self.dry_run:
            print(f"[dry-run] {method} {url} body={body_summary}")
            return 200, None

        headers = {"Accept": accept} if accept else None
        response = self.session.request(
            method,
            url,
            json=body,
            headers=headers,
            timeout=30,
        )
        if response.status_code not in allowed:
            raise ApiError(method, url, response.status_code, response.text)
        return response.status_code, self._decode_response(response)

    @staticmethod
    def _decode_response(response: requests.Response) -> dict[str, Any] | str | None:
        if not response.text:
            return None
        try:
            return response.json()
        except ValueError:
            return response.text

    @staticmethod
    def _summarize_body(body: dict[str, Any] | None) -> str:
        if body is None:
            return "<none>"
        text = json.dumps(body, sort_keys=True)
        return text if len(text) <= 500 else f"{text[:497]}..."


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Provision a GitHub repository from the golden-repo template, "
            "then apply repo settings, security features, branch protection, "
            "and team grants idempotently."
        )
    )
    parser.add_argument("--name", required=True, help="New repository name.")
    parser.add_argument("--org", required=True, help="Target GitHub org.")
    parser.add_argument(
        "--visibility",
        required=True,
        choices=("private", "internal", "public"),
        help="Target repository visibility.",
    )
    parser.add_argument(
        "--team",
        action="append",
        default=[],
        help=(
            "Team slug to grant. Repeat for multiple teams. Slugs containing "
            "'maintain' receive maintain; all others receive push."
        ),
    )
    parser.add_argument(
        "--new-team",
        help=(
            "Dedicated team slug to create/reuse for this repo. Default: "
            "<name>-admins, sanitized to lowercase hyphenated slug."
        ),
    )
    parser.add_argument(
        "--new-team-permission",
        choices=("pull", "push", "maintain", "admin"),
        default="maintain",
        help="Repository permission for --new-team. Default: maintain.",
    )
    parser.add_argument(
        "--new-team-member",
        action="append",
        default=[],
        help="Org member login to add to --new-team. Repeat for multiple members.",
    )
    parser.add_argument(
        "--no-new-team",
        action="store_true",
        help="Opt out of creating the dedicated repo team; --team grants still apply.",
    )
    parser.add_argument("--description", default="", help="Repository description.")
    parser.add_argument(
        "--topics",
        default="",
        help="Comma-separated GitHub topics, for example: agent,security,python.",
    )
    parser.add_argument(
        "--template-owner",
        default=DEFAULT_TEMPLATE_OWNER,
        help=f"Template owner. Default: {DEFAULT_TEMPLATE_OWNER}.",
    )
    parser.add_argument(
        "--template-repo",
        default=DEFAULT_TEMPLATE_REPO,
        help=f"Template repo. Default: {DEFAULT_TEMPLATE_REPO}.",
    )
    parser.add_argument(
        "--codeowners-override",
        help=(
            "Path to a CODEOWNERS override to note in the summary. The script "
            "does not commit this file; apply it through a normal commit or PR."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print intended API calls without executing mutations.",
    )
    args = parser.parse_args(argv)
    args.topics_list = parse_topics(args.topics)
    validate_args(args)
    return args


def parse_topics(raw_topics: str) -> list[str]:
    if not raw_topics.strip():
        return []
    topics = [topic.strip().lower() for topic in raw_topics.split(",")]
    return [topic for topic in topics if topic]


def validate_args(args: argparse.Namespace) -> None:
    validate_repo_name(args.name, "--name")
    validate_slug(args.org, "--org")
    validate_slug(args.template_owner, "--template-owner")
    validate_repo_name(args.template_repo, "--template-repo")
    if args.no_new_team and not args.team:
        raise ProvisioningError("At least one --team value is required with --no-new-team.")
    if not args.no_new_team:
        args.new_team = (
            validate_new_team_slug(args.new_team, "--new-team")
            if args.new_team
            else sanitize_team_slug(f"{args.name}-admins")
        )
    for team_slug in args.team:
        validate_slug(team_slug, "--team")
    for member_login in args.new_team_member:
        validate_slug(member_login, "--new-team-member")
    for topic in args.topics_list:
        if not TOPIC_RE.fullmatch(topic):
            raise ProvisioningError(
                f"Invalid topic '{topic}'. Topics must be lowercase letters, "
                "numbers, or hyphens and be 1-50 characters."
            )
    if args.codeowners_override:
        path = Path(args.codeowners_override)
        if not path.exists() or not path.is_file():
            raise ProvisioningError(
                f"--codeowners-override path does not exist or is not a file: {path}"
            )


def validate_repo_name(value: str, flag: str) -> None:
    if not REPO_NAME_RE.fullmatch(value) or value in {".", ".."}:
        raise ProvisioningError(
            f"Invalid {flag} '{value}'. Use 1-100 letters, numbers, '.', '_', or '-'."
        )


def validate_slug(value: str, flag: str) -> None:
    if not ORG_OR_TEAM_RE.fullmatch(value):
        raise ProvisioningError(
            f"Invalid {flag} '{value}'. Use a GitHub slug with letters, numbers, "
            "and hyphens."
        )


def validate_new_team_slug(value: str, flag: str) -> str:
    validate_slug(value, flag)
    return value.lower()


def sanitize_team_slug(value: str) -> str:
    slug = value.strip().lower()
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"[^a-z0-9-]+", "-", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")
    if not slug:
        raise ProvisioningError(
            "Could not derive a valid --new-team slug from --name; pass --new-team."
        )
    validate_slug(slug, "--new-team")
    return slug


def progress(message: str) -> None:
    print(f"==> {message}")


def create_or_get_repo(
    client: GitHubClient,
    args: argparse.Namespace,
    summary: Summary,
) -> None:
    progress(
        f"Creating repository {args.org}/{args.name} from "
        f"{args.template_owner}/{args.template_repo}"
    )
    body = {
        "owner": args.org,
        "name": args.name,
        "description": args.description,
        "private": args.visibility != "public",
        "include_all_branches": False,
    }
    status, payload = client.request_allowing_statuses(
        "POST",
        f"/repos/{args.template_owner}/{args.template_repo}/generate",
        body=body,
        allowed=(201, 422),
    )

    if client.dry_run:
        summary.repo_url = f"https://github.com/{args.org}/{args.name}"
        return

    if status == 201:
        if not isinstance(payload, dict):
            raise ProvisioningError("Template generation returned no repository JSON.")
        summary.repo_url = str(
            payload.get("html_url", f"https://github.com/{args.org}/{args.name}")
        )
        return

    if status == 422 and is_repo_already_exists(payload):
        progress("Repository already exists; continuing idempotently.")
        summary.skipped.append("template generation: repository already exists")
        response = client.request("GET", f"/repos/{args.org}/{args.name}")
        repo = response.json() if response is not None else {}
        summary.repo_url = str(
            repo.get("html_url", f"https://github.com/{args.org}/{args.name}")
        )
        return

    raise ProvisioningError(
        "Template generation failed with 422 for a reason other than an existing "
        f"repository: {payload}"
    )


def is_repo_already_exists(payload: dict[str, Any] | str | None) -> bool:
    text = (
        json.dumps(payload).lower()
        if isinstance(payload, dict)
        else str(payload).lower()
    )
    return (
        "already_exists" in text
        or "already exists" in text
        or "name already exists" in text
    )


def wait_for_template_ready(
    client: GitHubClient,
    args: argparse.Namespace,
) -> None:
    """Wait for GitHub's async template population to complete.
    
    GitHub's template generation (POST /repos/.../generate) returns 201 immediately
    but populates files asynchronously with an "Initial commit" a few seconds later.
    Poll until the repository has commits AND the HEAD sha is stable across two
    consecutive polls (indicating the Initial commit has landed and no further
    template commits are pending).
    """
    progress("Waiting for template population to complete")
    
    if client.dry_run:
        progress("Dry-run: skipping template-ready poll")
        return
    
    max_attempts = 30  # 30 attempts * 2s = 60s timeout
    poll_interval = 2  # seconds
    previous_sha: str | None = None
    
    for attempt in range(1, max_attempts + 1):
        status, payload = client.request_allowing_statuses(
            "GET",
            f"/repos/{args.org}/{args.name}/commits?per_page=1",
            allowed=(200, 404, 409),
        )
        
        # 404/409 means repo is empty (template not populated yet)
        if status in (404, 409):
            if attempt < max_attempts:
                time.sleep(poll_interval)
                continue
            raise ProvisioningError(
                f"Template population did not complete after {max_attempts * poll_interval}s. "
                f"Repository {args.org}/{args.name} is still empty."
            )
        
        # Extract HEAD commit sha
        if status == 200 and isinstance(payload, list) and len(payload) > 0:
            current_sha = payload[0].get("sha")
            if current_sha:
                if previous_sha == current_sha:
                    # Stable HEAD across two consecutive polls - template is ready
                    progress(f"Template population complete (HEAD stable at {current_sha[:7]})")
                    return
                previous_sha = current_sha
        
        if attempt < max_attempts:
            time.sleep(poll_interval)
    
    raise ProvisioningError(
        f"Template population did not stabilize after {max_attempts * poll_interval}s. "
        f"Repository {args.org}/{args.name} HEAD commit is still changing."
    )


def replace_readme_with_placeholder(
    client: GitHubClient,
    args: argparse.Namespace,
    summary: Summary,
) -> None:
    """Replace the generated repo's README.md with the placeholder template."""
    progress("Replacing README.md with placeholder template")
    
    # Load and substitute the template
    script_dir = Path(__file__).parent
    template_path = script_dir / "templates" / "README.template.md"
    
    if not template_path.exists():
        raise ProvisioningError(
            f"README template not found at {template_path}. "
            "Ensure tools/templates/README.template.md exists."
        )
    
    template_content = template_path.read_text(encoding="utf-8")
    readme_content = template_content.replace("{{REPO_NAME}}", args.name)
    
    if client.dry_run:
        progress(
            f"Would replace README.md in {args.org}/{args.name} "
            f"({len(readme_content)} bytes)"
        )
        summary.readme_replaced = True
        return
    
    # Get existing README.md to obtain its sha (for idempotent updates)
    sha: str | None = None
    status, payload = client.request_allowing_statuses(
        "GET",
        f"/repos/{args.org}/{args.name}/contents/README.md",
        allowed=(200, 404),
    )
    
    if status == 200 and isinstance(payload, dict):
        sha = payload.get("sha")
    
    # PUT the new README content
    readme_b64 = base64.b64encode(readme_content.encode("utf-8")).decode("ascii")
    body: dict[str, Any] = {
        "message": "Replace README.md with placeholder template",
        "content": readme_b64,
    }
    if sha:
        body["sha"] = sha
    
    client.request(
        "PUT",
        f"/repos/{args.org}/{args.name}/contents/README.md",
        body=body,
        expected=(200, 201),
    )
    summary.readme_replaced = True


def remove_provision_workflow(
    client: GitHubClient,
    args: argparse.Namespace,
    summary: Summary,
) -> None:
    """Remove provision-new-repo.yml workflow from the generated repo."""
    progress("Removing provision-new-repo.yml workflow from generated repo")
    
    workflow_path = ".github/workflows/provision-new-repo.yml"
    
    if client.dry_run:
        progress(f"Would remove {workflow_path} from {args.org}/{args.name}")
        summary.provision_workflow_removed = True
        return
    
    # Get the workflow file to obtain its sha (404 if not present = idempotent)
    status, payload = client.request_allowing_statuses(
        "GET",
        f"/repos/{args.org}/{args.name}/contents/{workflow_path}",
        allowed=(200, 404),
    )
    
    if status == 404:
        progress(f"{workflow_path} not present, nothing to remove")
        return
    
    # File exists, extract sha and delete it
    if status == 200 and isinstance(payload, dict):
        sha = payload.get("sha")
        if not sha:
            raise ProvisioningError(
                f"GET {workflow_path} returned 200 but no sha in response"
            )
        
        client.request(
            "DELETE",
            f"/repos/{args.org}/{args.name}/contents/{workflow_path}",
            body={
                "message": "Remove provisioning workflow from generated repo",
                "sha": sha,
            },
            expected=(200,),
        )
        summary.provision_workflow_removed = True


def update_repo_settings(client: GitHubClient, args: argparse.Namespace) -> None:
    progress("Updating repository description and visibility")
    client.request(
        "PATCH",
        f"/repos/{args.org}/{args.name}",
        body={"description": args.description, "visibility": args.visibility},
        expected=(200,),
    )

    progress("Updating repository topics")
    client.request(
        "PUT",
        f"/repos/{args.org}/{args.name}/topics",
        body={"names": args.topics_list},
        expected=(200,),
    )


def get_default_branch(client: GitHubClient, org: str, repo: str) -> str:
    if client.dry_run:
        return "main"
    response = client.request("GET", f"/repos/{org}/{repo}")
    data = response.json() if response is not None else {}
    return str(data.get("default_branch") or "main")


def wait_for_main_branch(
    client: GitHubClient, org: str, repo: str, branch: str
) -> None:
    progress(f"Waiting for {branch} branch to be available")
    if client.dry_run:
        client.request("GET", f"/repos/{org}/{repo}/branches/{branch}")
        return

    for attempt in range(1, 11):
        status, _ = client.request_allowing_statuses(
            "GET",
            f"/repos/{org}/{repo}/branches/{branch}",
            allowed=(200, 404),
        )
        if status == 200:
            return
        if attempt < 10:
            print(f"{branch} branch not ready yet; retrying ({attempt}/10)")
            time.sleep(2)
    raise ProvisioningError(
        f"Branch '{branch}' did not appear for {org}/{repo} after waiting."
    )


def select_branch_restriction_teams(team_slugs: list[str]) -> list[str]:
    maintainers = [slug for slug in team_slugs if "maintain" in slug.lower()]
    if maintainers:
        return maintainers
    print(
        "No maintainers-like team slug supplied; using the first granted team "
        "for main-branch push restrictions."
    )
    return [team_slugs[0]]


def branch_restriction_team_candidates(args: argparse.Namespace) -> list[str]:
    candidates: list[str] = []
    if not args.no_new_team:
        candidates.append(args.new_team)
    candidates.extend(args.team)
    return list(dict.fromkeys(candidates))


def apply_branch_protection(
    client: GitHubClient,
    args: argparse.Namespace,
    summary: Summary,
) -> None:
    branch = get_default_branch(client, args.org, args.name)
    wait_for_main_branch(client, args.org, args.name, branch)
    restricted_teams = select_branch_restriction_teams(
        branch_restriction_team_candidates(args)
    )
    progress(
        f"Applying branch protection to {branch} "
        f"(restricted teams: {', '.join(restricted_teams)})"
    )
    body = {
        "required_status_checks": {
            "strict": True,
            "contexts": REQUIRED_CHECKS,
        },
        "enforce_admins": True,
        "required_pull_request_reviews": {
            "dismiss_stale_reviews": True,
            "require_code_owner_reviews": True,
            "required_approving_review_count": 1,
        },
        "restrictions": {
            "users": [],
            "teams": restricted_teams,
            "apps": [],
        },
        "allow_force_pushes": False,
        "allow_deletions": False,
    }
    client.request(
        "PUT",
        f"/repos/{args.org}/{args.name}/branches/{branch}/protection",
        body=body,
        expected=(200,),
    )

    progress(f"Requiring signed commits on {branch}")
    client.request(
        "POST",
        f"/repos/{args.org}/{args.name}/branches/{branch}/protection/required_signatures",
        expected=(200, 204),
        accept="application/vnd.github.zzzax-preview+json",
    )
    summary.branch_protection_applied = True


def enable_security_features(
    client: GitHubClient,
    args: argparse.Namespace,
    summary: Summary,
) -> None:
    progress("Enabling Dependabot vulnerability alerts")
    client.request(
        "PUT",
        f"/repos/{args.org}/{args.name}/vulnerability-alerts",
        expected=(204,),
    )
    summary.security_features_enabled.append("Dependabot vulnerability alerts")

    progress("Enabling Dependabot automated security updates")
    client.request(
        "PUT",
        f"/repos/{args.org}/{args.name}/automated-security-fixes",
        expected=(204,),
    )
    summary.security_features_enabled.append("Dependabot automated security updates")

    # Secret scanning and push protection for private/internal repositories require
    # GitHub Advanced Security to be available to the organization/repository.
    progress("Enabling secret scanning and push protection")
    client.request(
        "PATCH",
        f"/repos/{args.org}/{args.name}",
        body={
            "security_and_analysis": {
                "secret_scanning": {"status": "enabled"},
                "secret_scanning_push_protection": {"status": "enabled"},
            }
        },
        expected=(200,),
    )
    summary.security_features_enabled.extend(
        ["secret scanning", "secret scanning push protection"]
    )

    # CodeQL analysis is provided by the advanced workflow shipped in the
    # template (.github/workflows/codeql.yml), which produces the required
    # "analyze" status check. Enabling CodeQL *default setup* here would
    # conflict with that workflow ("configuration error"), so it is
    # intentionally left to the workflow instead.
    summary.security_features_enabled.append("CodeQL analysis (advanced workflow)")


def ensure_team_exists(
    client: GitHubClient,
    org: str,
    team_slug: str,
    summary: Summary,
) -> None:
    progress(f"Ensuring team {team_slug} exists")
    if client.dry_run:
        client.request_allowing_statuses(
            "GET",
            f"/orgs/{org}/teams/{team_slug}",
            allowed=(200, 404),
        )
        client.request(
            "POST",
            f"/orgs/{org}/teams",
            body={"name": team_slug, "privacy": "closed"},
            expected=(201,),
        )
        summary.teams_created.append(team_slug)
        return

    status, _ = client.request_allowing_statuses(
        "GET",
        f"/orgs/{org}/teams/{team_slug}",
        allowed=(200, 404),
    )
    if status == 200:
        summary.teams_reused.append(team_slug)
        return
    client.request(
        "POST",
        f"/orgs/{org}/teams",
        body={"name": team_slug, "privacy": "closed"},
        expected=(201,),
    )
    summary.teams_created.append(team_slug)


def add_new_team_members(
    client: GitHubClient,
    args: argparse.Namespace,
    summary: Summary,
) -> None:
    for member_login in args.new_team_member:
        progress(f"Adding {member_login} to team {args.new_team}")
        try:
            client.request(
                "PUT",
                f"/orgs/{args.org}/teams/{args.new_team}/memberships/{member_login}",
                body={"role": "member"},
                expected=(200, 201),
            )
            summary.team_members_added.append(f"{args.new_team}:{member_login}")
        except (ApiError, requests.RequestException) as exc:
            warning = (
                f"Could not add {member_login} to {args.new_team}: {exc}"
            )
            print(f"WARNING: {warning}")
            summary.team_member_warnings.append(warning)


def grant_team_repo_access(
    client: GitHubClient,
    args: argparse.Namespace,
    summary: Summary,
    team_slug: str,
    permission: str,
) -> None:
    progress(f"Granting team {team_slug} {permission} access")
    client.request(
        "PUT",
        f"/orgs/{args.org}/teams/{team_slug}/repos/{args.org}/{args.name}",
        body={"permission": permission},
        expected=(204,),
    )
    summary.teams_granted.append(f"{team_slug}:{permission}")


def provision_team_access(
    client: GitHubClient,
    args: argparse.Namespace,
    summary: Summary,
) -> None:
    granted_team_slugs: set[str] = set()
    if not args.no_new_team:
        ensure_team_exists(client, args.org, args.new_team, summary)
        add_new_team_members(client, args, summary)
        grant_team_repo_access(
            client,
            args,
            summary,
            args.new_team,
            args.new_team_permission,
        )
        granted_team_slugs.add(args.new_team)

    for team_slug in args.team:
        if team_slug in granted_team_slugs:
            summary.skipped.append(
                f"team grant skipped: {team_slug} already granted as --new-team"
            )
            continue
        ensure_team_exists(client, args.org, team_slug, summary)
        permission = "maintain" if "maintain" in team_slug.lower() else "push"
        grant_team_repo_access(client, args, summary, team_slug, permission)
        granted_team_slugs.add(team_slug)


def note_codeowners_override(args: argparse.Namespace, summary: Summary) -> None:
    if args.codeowners_override:
        summary.skipped.append(
            "CODEOWNERS override not applied: commit the override through a normal "
            f"commit or PR ({args.codeowners_override})"
        )


def print_summary(summary: Summary) -> None:
    print("\nSUMMARY")
    print(json.dumps(
        {
            "repo_url": summary.repo_url,
            "visibility": summary.visibility,
            "teams_created": summary.teams_created,
            "teams_reused": summary.teams_reused,
            "teams_granted": summary.teams_granted,
            "team_members_added": summary.team_members_added,
            "team_member_warnings": summary.team_member_warnings,
            "branch_protection": {
                "applied": summary.branch_protection_applied,
                "required_checks": REQUIRED_CHECKS,
            },
            "security_features_enabled": summary.security_features_enabled,
            "readme_replaced": summary.readme_replaced,
            "provision_workflow_removed": summary.provision_workflow_removed,
            "skipped": summary.skipped,
        },
        indent=2,
        sort_keys=True,
    ))


def main(argv: list[str] | None = None) -> int:
    try:
        args = parse_args(argv or sys.argv[1:])
        token = os.environ.get("GITHUB_TOKEN")
        if not token:
            if args.dry_run:
                token = "dry-run-placeholder"
            else:
                raise ProvisioningError(
                    "GITHUB_TOKEN is required. Provide a GitHub App installation "
                    "token or OIDC-derived token in the environment."
                )

        summary = Summary(
            repo_url=f"https://github.com/{args.org}/{args.name}",
            visibility=args.visibility,
        )
        client = GitHubClient(token=token, dry_run=args.dry_run)

        create_or_get_repo(client, args, summary)
        wait_for_template_ready(client, args)
        replace_readme_with_placeholder(client, args, summary)
        remove_provision_workflow(client, args, summary)
        update_repo_settings(client, args)
        provision_team_access(client, args, summary)
        apply_branch_protection(client, args, summary)
        enable_security_features(client, args, summary)
        note_codeowners_override(args, summary)
        if args.dry_run:
            summary.skipped.append("dry-run: no mutations were executed")
        print_summary(summary)
        return 0
    except ProvisioningError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except requests.RequestException as exc:
        print(f"ERROR: GitHub API request failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
