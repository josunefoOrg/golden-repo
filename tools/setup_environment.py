"""Create or update a GitHub Environment with required-reviewer protection rules.

Despite claims elsewhere that environment protection rules must be configured
manually in the UI, GitHub's REST API fully supports creating and updating them:

    PUT /repos/{owner}/{repo}/environments/{environment_name}

This script wraps that call so the ``repo-provisioning`` approval gate (or any
other environment) can be created/updated idempotently from the command line or
a workflow, instead of requiring a manual UI step. What genuinely cannot be
scripted is the *act of approving* a deployment: that always requires a human
reviewer to click approve when a protected job runs.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any
from urllib.parse import quote

import requests

API_BASE_URL = "https://api.github.com"
API_VERSION = "2022-11-28"
MAX_REVIEWERS = 6


class ProvisioningError(RuntimeError):
    """Raised when the environment cannot be created/updated safely."""


class ApiError(ProvisioningError):
    """Raised for an unexpected GitHub API response."""

    def __init__(self, method: str, url: str, status: int, body: str) -> None:
        super().__init__(
            f"{method} {url} failed with HTTP {status}: {body or '<empty body>'}"
        )


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Create or update a GitHub Environment with required-reviewer "
            "protection rules via the REST API."
        )
    )
    parser.add_argument("--org", required=True, help="Repository owner/org.")
    parser.add_argument("--repo", required=True, help="Repository name.")
    parser.add_argument(
        "--environment",
        default="repo-provisioning",
        help="Environment name. Default: repo-provisioning.",
    )
    parser.add_argument(
        "--reviewer-team",
        action="append",
        default=[],
        help="Team slug to add as a required reviewer. Repeat for multiple teams.",
    )
    parser.add_argument(
        "--reviewer-user",
        action="append",
        default=[],
        help="User login to add as a required reviewer. Repeat for multiple users.",
    )
    parser.add_argument(
        "--wait-timer",
        type=int,
        default=0,
        help="Minutes to delay a job after it is triggered (0-43200). Default: 0.",
    )
    parser.add_argument(
        "--prevent-self-review",
        action="store_true",
        help="Prevent the user who triggered the job from approving it.",
    )
    parser.add_argument(
        "--protected-branches-only",
        action="store_true",
        help="Restrict deploys to branches with branch protection rules.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the intended API call without mutating GitHub.",
    )
    args = parser.parse_args(argv)
    validate_args(args)
    return args


def validate_args(args: argparse.Namespace) -> None:
    if not (args.reviewer_team or args.reviewer_user):
        raise ProvisioningError(
            "At least one --reviewer-team or --reviewer-user is required."
        )
    total = len(args.reviewer_team) + len(args.reviewer_user)
    if total > MAX_REVIEWERS:
        raise ProvisioningError(
            f"GitHub allows at most {MAX_REVIEWERS} reviewers per environment; "
            f"got {total}."
        )
    if not 0 <= args.wait_timer <= 43200:
        raise ProvisioningError("--wait-timer must be between 0 and 43200 minutes.")


def resolve_team_id(
    session: requests.Session, org: str, slug: str, *, dry_run: bool
) -> int:
    if dry_run:
        return -1
    url = f"{API_BASE_URL}/orgs/{quote(org)}/teams/{quote(slug)}"
    response = session.get(url, timeout=30)
    if response.status_code != 200:
        raise ApiError("GET", url, response.status_code, response.text)
    return response.json()["id"]


def resolve_user_id(
    session: requests.Session, login: str, *, dry_run: bool
) -> int:
    if dry_run:
        return -1
    url = f"{API_BASE_URL}/users/{quote(login)}"
    response = session.get(url, timeout=30)
    if response.status_code != 200:
        raise ApiError("GET", url, response.status_code, response.text)
    return response.json()["id"]


def build_reviewers(
    session: requests.Session, args: argparse.Namespace
) -> list[dict[str, Any]]:
    reviewers: list[dict[str, Any]] = []
    for slug in args.reviewer_team:
        team_id = resolve_team_id(session, args.org, slug, dry_run=args.dry_run)
        reviewers.append({"type": "Team", "id": team_id})
    for login in args.reviewer_user:
        user_id = resolve_user_id(session, login, dry_run=args.dry_run)
        reviewers.append({"type": "User", "id": user_id})
    return reviewers


def build_body(
    args: argparse.Namespace, reviewers: list[dict[str, Any]]
) -> dict[str, Any]:
    return {
        "wait_timer": args.wait_timer,
        "prevent_self_review": args.prevent_self_review,
        "reviewers": reviewers,
        "deployment_branch_policy": {
            "protected_branches": args.protected_branches_only,
            "custom_branch_policies": not args.protected_branches_only,
        },
    }


def apply_environment(
    session: requests.Session,
    args: argparse.Namespace,
    body: dict[str, Any],
) -> dict[str, Any] | None:
    url = (
        f"{API_BASE_URL}/repos/{quote(args.org)}/{quote(args.repo)}/environments/"
        f"{quote(args.environment)}"
    )
    if args.dry_run:
        print(f"[dry-run] PUT {url}")
        print(json.dumps(body, indent=2))
        return None
    response = session.put(url, json=body, timeout=30)
    if response.status_code != 200:
        raise ApiError("PUT", url, response.status_code, response.text)
    return response.json()


def main(argv: list[str] | None = None) -> int:
    try:
        args = parse_args(argv or sys.argv[1:])
        token = os.environ.get("GITHUB_TOKEN")
        if not token and not args.dry_run:
            raise ProvisioningError(
                "GITHUB_TOKEN is required (a token with admin rights on the "
                "repository, for example an org-owner PAT or GitHub App token)."
            )

        session = requests.Session()
        session.headers.update(
            {
                "Accept": "application/vnd.github+json",
                "Authorization": "Bearer " + (token or "dry-run-placeholder"),
                "User-Agent": "golden-repo-environment-setup/1.0",
                "X-GitHub-Api-Version": API_VERSION,
            }
        )

        reviewers = build_reviewers(session, args)
        body = build_body(args, reviewers)
        print(
            f"Applying '{args.environment}' environment protection to "
            f"{args.org}/{args.repo} (reviewers: "
            f"{', '.join(args.reviewer_team + args.reviewer_user)})"
        )
        result = apply_environment(session, args, body)
        if result is not None:
            print(f"Environment '{args.environment}' is configured.")
        if args.dry_run:
            print("[dry-run] no mutations were executed.")
        return 0
    except ProvisioningError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except requests.RequestException as exc:
        print(f"ERROR: GitHub API request failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
