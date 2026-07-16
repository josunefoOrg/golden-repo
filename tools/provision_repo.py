"""Provision a GitHub repository from the golden-repo template.

The script is intentionally defensive: every required provisioning step logs
what it is doing, aborts on unexpected API errors, and can be safely re-run to
re-apply settings to an existing repository.
"""

from __future__ import annotations

import argparse
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
    teams_granted: list[str] = field(default_factory=list)
    branch_protection_applied: bool = False
    security_features_enabled: list[str] = field(default_factory=list)
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
        required=True,
        help=(
            "Team slug to grant. Repeat for multiple teams. Slugs containing "
            "'maintain' receive maintain; all others receive push."
        ),
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
    if not args.team:
        raise ProvisioningError("At least one --team value is required.")
    for team_slug in args.team:
        validate_slug(team_slug, "--team")
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
        "visibility": args.visibility,
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


def wait_for_main_branch(client: GitHubClient, org: str, repo: str) -> None:
    progress("Waiting for main branch to be available")
    if client.dry_run:
        client.request("GET", f"/repos/{org}/{repo}/branches/main")
        return

    for attempt in range(1, 11):
        status, _ = client.request_allowing_statuses(
            "GET",
            f"/repos/{org}/{repo}/branches/main",
            allowed=(200, 404),
        )
        if status == 200:
            return
        if attempt < 10:
            print(f"main branch not ready yet; retrying ({attempt}/10)")
            time.sleep(2)
    raise ProvisioningError(
        f"Branch 'main' did not appear for {org}/{repo} after waiting."
    )


def select_branch_restriction_teams(team_slugs: list[str]) -> list[str]:
    maintainers = [slug for slug in team_slugs if "maintain" in slug.lower()]
    if maintainers:
        return maintainers
    print(
        "No maintainers-like team slug supplied; using the first --team value "
        "for main-branch push restrictions."
    )
    return [team_slugs[0]]


def apply_branch_protection(
    client: GitHubClient,
    args: argparse.Namespace,
    summary: Summary,
) -> None:
    wait_for_main_branch(client, args.org, args.name)
    restricted_teams = select_branch_restriction_teams(args.team)
    progress(
        "Applying branch protection to main "
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
        f"/repos/{args.org}/{args.name}/branches/main/protection",
        body=body,
        expected=(200,),
    )

    progress("Requiring signed commits on main")
    client.request(
        "POST",
        f"/repos/{args.org}/{args.name}/branches/main/protection/required_signatures",
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

    # CodeQL default setup for private/internal repositories may require GitHub
    # Advanced Security and code scanning permissions.
    progress("Configuring CodeQL default setup")
    client.request(
        "PATCH",
        f"/repos/{args.org}/{args.name}/code-scanning/default-setup",
        body={"state": "configured"},
        expected=(200, 201, 202, 204),
    )
    summary.security_features_enabled.append("CodeQL default setup")


def grant_team_access(
    client: GitHubClient,
    args: argparse.Namespace,
    summary: Summary,
) -> None:
    for team_slug in args.team:
        permission = "maintain" if "maintain" in team_slug.lower() else "push"
        progress(f"Granting team {team_slug} {permission} access")
        client.request(
            "PUT",
            f"/orgs/{args.org}/teams/{team_slug}/repos/{args.org}/{args.name}",
            body={"permission": permission},
            expected=(204,),
        )
        summary.teams_granted.append(f"{team_slug}:{permission}")


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
            "teams_granted": summary.teams_granted,
            "branch_protection": {
                "applied": summary.branch_protection_applied,
                "required_checks": REQUIRED_CHECKS,
            },
            "security_features_enabled": summary.security_features_enabled,
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
        update_repo_settings(client, args)
        grant_team_access(client, args, summary)
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
