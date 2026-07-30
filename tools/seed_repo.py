"""Seed a target GitHub repository with this repository's structure.

This pushes the golden-repo content (the tracked working tree, without git
history) into a *separate*, already-created target repository as its initial
commit. It is the "first push" step in the flow:

    golden-repo (source)  ->  StartRight creates empty repo  ->  seed_repo.py push

StartRight (repo creation) is performed separately/manually. This script only
performs the content push, so it does not need a GitHub App: it authenticates the
push with whatever token is provided in the ``TARGET_REPO_TOKEN`` environment
variable (a fine-grained PAT with Contents: write on the target, or any token the
org allows), or you can pass a ready-to-use ``--target-url`` (for example an SSH
URL backed by a deploy key) and no token.

The source content is exported with ``git archive`` so only tracked files are
included and ``.gitignore``/``export-ignore`` rules are honored. Provisioning-only
files are excluded by default so the seeded repo does not carry the seeding
tooling itself.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path
from urllib.parse import quote

DEFAULT_HOST = "github.com"
DEFAULT_BRANCH = "main"
DEFAULT_SOURCE_REF = "HEAD"
DEFAULT_COMMIT_MESSAGE = "Initial import from golden-repo template"
DEFAULT_AUTHOR_NAME = "golden-repo-seeder"
DEFAULT_AUTHOR_EMAIL = "golden-repo-seeder@users.noreply.github.com"

# Provisioning/seeding-only files that should not be carried into a seeded repo.
DEFAULT_EXCLUDES = [
    ".github/workflows/provision-new-repo.yml",
    ".github/workflows/seed-target-repo.yml",
]

OWNER_REPO_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*/[A-Za-z0-9][A-Za-z0-9._-]*$")


class SeedError(RuntimeError):
    """Raised when seeding cannot continue safely."""


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Push this repository's structure into an already-created target "
            "repository as its initial commit."
        )
    )
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument(
        "--target-repo",
        help="Target repository as 'owner/name'. Combined with --host and the "
        "TARGET_REPO_TOKEN env var to build the push URL.",
    )
    target.add_argument(
        "--target-url",
        help="Fully-formed push URL (for example an SSH URL). Used as-is; no token "
        "is injected.",
    )
    parser.add_argument(
        "--host",
        default=DEFAULT_HOST,
        help=f"Git host for --target-repo. Default: {DEFAULT_HOST}.",
    )
    parser.add_argument(
        "--target-branch",
        default=DEFAULT_BRANCH,
        help=f"Branch to push on the target. Default: {DEFAULT_BRANCH}.",
    )
    parser.add_argument(
        "--source-ref",
        default=DEFAULT_SOURCE_REF,
        help=f"Source ref to export. Default: {DEFAULT_SOURCE_REF}.",
    )
    parser.add_argument(
        "--commit-message",
        default=DEFAULT_COMMIT_MESSAGE,
        help="Commit message for the seeded initial commit.",
    )
    parser.add_argument(
        "--exclude",
        action="append",
        default=[],
        help="Path to exclude from the seeded content. Repeat for multiple paths.",
    )
    parser.add_argument(
        "--exclude-file",
        help="File listing additional paths to exclude, one per line ('#' comments).",
    )
    parser.add_argument(
        "--no-default-excludes",
        action="store_true",
        help="Do not apply the built-in provisioning-file excludes.",
    )
    parser.add_argument(
        "--author-name",
        default=DEFAULT_AUTHOR_NAME,
        help="Commit author/committer name.",
    )
    parser.add_argument(
        "--author-email",
        default=DEFAULT_AUTHOR_EMAIL,
        help="Commit author/committer email.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force-push (use when the target already has a seed commit to replace).",
    )
    parser.add_argument(
        "--username",
        default="x-access-token",
        help="Username used in the HTTPS push URL. Default: x-access-token.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the steps without cloning, committing, or pushing.",
    )
    args = parser.parse_args(argv)
    validate_args(args)
    return args


def validate_args(args: argparse.Namespace) -> None:
    if args.target_repo and not OWNER_REPO_RE.match(args.target_repo):
        raise SeedError(
            f"--target-repo {args.target_repo!r} must be in 'owner/name' form."
        )


def resolve_excludes(args: argparse.Namespace) -> list[str]:
    excludes: list[str] = [] if args.no_default_excludes else list(DEFAULT_EXCLUDES)
    excludes.extend(args.exclude)
    if args.exclude_file:
        file_path = Path(args.exclude_file)
        if not file_path.exists():
            raise SeedError(f"--exclude-file not found: {args.exclude_file}")
        for raw in file_path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if line and not line.startswith("#"):
                excludes.append(line)
    # De-duplicate while preserving order.
    seen: set[str] = set()
    ordered: list[str] = []
    for item in excludes:
        normalized = item.replace("\\", "/").strip("/")
        if normalized and normalized not in seen:
            seen.add(normalized)
            ordered.append(normalized)
    return ordered


def build_remote_url(args: argparse.Namespace, token: str) -> str:
    """Return the push URL, injecting the token for HTTPS targets."""
    if args.target_url:
        return args.target_url
    if not token:
        raise SeedError(
            "TARGET_REPO_TOKEN is required when using --target-repo. Provide a token "
            "with Contents: write on the target, or pass --target-url instead."
        )
    user = quote(args.username, safe="")
    secret = quote(token, safe="")
    return f"https://{user}:{secret}@{args.host}/{args.target_repo}.git"


def redact_url(url: str) -> str:
    """Hide credentials in an HTTPS URL for logging."""
    return re.sub(r"://[^@/]+@", "://***@", url)


def run_git(
    args_list: list[str],
    *,
    cwd: Path | None = None,
    dry_run: bool = False,
) -> None:
    printable = " ".join(args_list)
    if dry_run:
        print(f"[dry-run] {printable}")
        return
    subprocess.run(args_list, cwd=cwd, check=True)


def export_source_tree(source_ref: str, dest: Path, *, dry_run: bool) -> None:
    """Export tracked files at source_ref into dest using git archive."""
    if dry_run:
        print(f"[dry-run] git archive {source_ref} -> {dest}")
        return
    archive_path = dest.parent / "source.tar"
    with archive_path.open("wb") as handle:
        subprocess.run(
            ["git", "archive", "--format=tar", source_ref],
            check=True,
            stdout=handle,
        )
    with tarfile.open(archive_path) as tar:
        tar.extractall(dest)
    archive_path.unlink()


def apply_excludes(root: Path, excludes: list[str], *, dry_run: bool) -> None:
    for rel in excludes:
        target = root / rel
        if dry_run:
            print(f"[dry-run] exclude {rel}")
            continue
        if target.is_dir():
            _remove_tree(target)
        elif target.exists():
            target.unlink()


def _remove_tree(path: Path) -> None:
    for child in path.iterdir():
        if child.is_dir():
            _remove_tree(child)
        else:
            child.unlink()
    path.rmdir()


def seed(args: argparse.Namespace, token: str) -> None:
    excludes = resolve_excludes(args)
    remote_url = build_remote_url(args, token)
    print(f"Seeding {redact_url(remote_url)} (branch {args.target_branch})")
    if excludes:
        print("Excluding: " + ", ".join(excludes))

    if args.dry_run:
        export_source_tree(args.source_ref, Path("<tmp>"), dry_run=True)
        apply_excludes(Path("<tmp>"), excludes, dry_run=True)
        run_git(["git", "init"], dry_run=True)
        run_git(["git", "add", "-A"], dry_run=True)
        run_git(
            ["git", "commit", "-m", args.commit_message], dry_run=True
        )
        push = ["git", "push", redact_url(remote_url), f"HEAD:{args.target_branch}"]
        if args.force:
            push.insert(2, "--force")
        run_git(push, dry_run=True)
        print("[dry-run] no changes were pushed.")
        return

    with tempfile.TemporaryDirectory(prefix="golden-seed-") as tmp:
        content = Path(tmp) / "content"
        content.mkdir(parents=True)
        export_source_tree(args.source_ref, content, dry_run=False)
        apply_excludes(content, excludes, dry_run=False)

        git_id = [
            "-c",
            f"user.name={args.author_name}",
            "-c",
            f"user.email={args.author_email}",
        ]
        run_git(["git", "init", "-q", "-b", args.target_branch], cwd=content)
        run_git(["git", *git_id, "add", "-A"], cwd=content)
        run_git(
            ["git", *git_id, "commit", "-q", "-m", args.commit_message],
            cwd=content,
        )
        push = ["git", "push"]
        if args.force:
            push.append("--force")
        push.extend([remote_url, f"HEAD:{args.target_branch}"])
        run_git(push, cwd=content)

    print(
        f"Pushed initial commit to {args.target_repo or args.target_url} "
        f"({args.target_branch})."
    )


def main(argv: list[str] | None = None) -> int:
    try:
        args = parse_args(argv or sys.argv[1:])
        token = os.environ.get("TARGET_REPO_TOKEN", "")
        seed(args, token)
        return 0
    except SeedError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except subprocess.CalledProcessError as exc:
        print(f"ERROR: git command failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
