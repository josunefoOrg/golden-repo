"""Seed a target GitHub repository with this repository's structure.

This overlays the golden-repo content (the tracked working tree, without git
history) onto an *already-created* target repository, as an additional commit on
top of whatever the target already contains. It is the "first push" step in the
flow:

    golden-repo (source)  ->  StartRight creates the repo  ->  seed_repo.py push

StartRight (repo creation) is performed separately/manually, and StartRight-
provisioned repositories are commonly *not* empty: they may already carry
scaffolding such as a placeholder README or compliance/policy files (for example
``.github/policies/*.yml``). This script clones the target repository, copies
golden-repo's tracked files on top of it, and commits normally. It never deletes
pre-existing target files and never force-pushes by default, so anything
StartRight (or a prior run) already committed survives.

This script does not need a GitHub App: it authenticates the push with whatever
token is provided in the ``TARGET_REPO_TOKEN`` environment variable (a
fine-grained PAT with Contents: write on the target, or any token the org
allows), or you can pass a ready-to-use ``--target-url`` (for example an SSH URL
backed by a deploy key) and no token.

The source content is exported with ``git archive`` so only tracked files are
included and ``.gitignore``/``export-ignore`` rules are honored. Provisioning-only
files are excluded by default so the seeded repo does not carry the seeding
tooling itself.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path
from urllib.parse import quote

DEFAULT_HOST = "github.com"
DEFAULT_BRANCH = "main"
DEFAULT_SOURCE_REF = "HEAD"
DEFAULT_COMMIT_MESSAGE = "Import golden-repo template structure"
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
            "Overlay this repository's structure onto an already-created target "
            "repository as a new commit, preserving any content the target "
            "already has (for example StartRight compliance scaffolding)."
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
        help="Fully-formed clone/push URL (for example an SSH URL). Used as-is; "
        "no token is injected.",
    )
    parser.add_argument(
        "--host",
        default=DEFAULT_HOST,
        help=f"Git host for --target-repo. Default: {DEFAULT_HOST}.",
    )
    parser.add_argument(
        "--target-branch",
        default=DEFAULT_BRANCH,
        help=f"Branch to clone from and push on the target. Default: {DEFAULT_BRANCH}.",
    )
    parser.add_argument(
        "--source-ref",
        default=DEFAULT_SOURCE_REF,
        help=f"Source ref to export. Default: {DEFAULT_SOURCE_REF}.",
    )
    parser.add_argument(
        "--commit-message",
        default=DEFAULT_COMMIT_MESSAGE,
        help="Commit message for the overlay commit.",
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
        help=(
            "Force-push instead of a normal (fast-forward) push. Not needed for "
            "the default overlay flow; only use it to knowingly rewrite the "
            "target branch."
        ),
    )
    parser.add_argument(
        "--username",
        default="x-access-token",
        help="Username used in the HTTPS clone/push URL. Default: x-access-token.",
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
    """Return the clone/push URL, injecting the token for HTTPS targets."""
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
    check: bool = True,
) -> subprocess.CompletedProcess | None:
    printable = " ".join(args_list)
    if dry_run:
        print(f"[dry-run] {printable}")
        return None
    return subprocess.run(args_list, cwd=cwd, check=check)


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
    """Drop excluded paths from the exported source content (not the target)."""
    for rel in excludes:
        target = root / rel
        if dry_run:
            print(f"[dry-run] exclude {rel}")
            continue
        if target.is_dir():
            shutil.rmtree(target)
        elif target.exists():
            target.unlink()


def overlay_content(source: Path, target: Path, *, dry_run: bool) -> None:
    """Copy every file under source into target, overwriting on conflict.

    Files that already exist in target but are absent from source are left
    untouched. This is what preserves target-only content such as StartRight
    compliance scaffolding.
    """
    if dry_run:
        print(f"[dry-run] overlay {source} onto {target} (no deletions)")
        return
    for src_path in source.rglob("*"):
        if src_path.is_dir():
            continue
        rel = src_path.relative_to(source)
        dest_path = target / rel
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_path, dest_path)


def clone_target(remote_url: str, branch: str, dest: Path, *, dry_run: bool) -> None:
    if dry_run:
        print(f"[dry-run] git clone --branch {branch} {redact_url(remote_url)} {dest}")
        return
    result = subprocess.run(
        ["git", "clone", "--branch", branch, "--single-branch", remote_url, str(dest)],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        return
    # A brand-new repository with zero commits has no branch to clone; clone the
    # (empty) default state instead and let the first commit create the branch.
    if "Remote branch" in result.stderr and "not found" in result.stderr:
        subprocess.run(["git", "clone", remote_url, str(dest)], check=True)
        return
    raise SeedError(f"git clone failed: {result.stderr.strip()}")


def seed(args: argparse.Namespace, token: str) -> None:
    excludes = resolve_excludes(args)
    remote_url = build_remote_url(args, token)
    print(
        f"Seeding {redact_url(remote_url)} (branch {args.target_branch}) "
        "by overlaying onto the target's existing content"
    )
    if excludes:
        print("Excluding from golden-repo content: " + ", ".join(excludes))

    if args.dry_run:
        clone_target(remote_url, args.target_branch, Path("<tmp>/target"), dry_run=True)
        export_source_tree(args.source_ref, Path("<tmp>/source"), dry_run=True)
        apply_excludes(Path("<tmp>/source"), excludes, dry_run=True)
        overlay_content(Path("<tmp>/source"), Path("<tmp>/target"), dry_run=True)
        run_git(["git", "add", "-A"], dry_run=True)
        run_git(["git", "commit", "-m", args.commit_message], dry_run=True)
        push = ["git", "push", redact_url(remote_url), f"HEAD:{args.target_branch}"]
        if args.force:
            push.insert(2, "--force")
        run_git(push, dry_run=True)
        print("[dry-run] no changes were pushed.")
        return

    with tempfile.TemporaryDirectory(prefix="golden-seed-") as tmp:
        target_dir = Path(tmp) / "target"
        source_dir = Path(tmp) / "source"
        source_dir.mkdir(parents=True)

        clone_target(remote_url, args.target_branch, target_dir, dry_run=False)
        export_source_tree(args.source_ref, source_dir, dry_run=False)
        apply_excludes(source_dir, excludes, dry_run=False)
        overlay_content(source_dir, target_dir, dry_run=False)

        git_id = [
            "-c",
            f"user.name={args.author_name}",
            "-c",
            f"user.email={args.author_email}",
        ]
        run_git(["git", *git_id, "add", "-A"], cwd=target_dir)
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=target_dir,
            capture_output=True,
            text=True,
            check=True,
        )
        if not status.stdout.strip():
            print("Target already matches golden-repo content; nothing to commit.")
            return

        run_git(
            ["git", *git_id, "commit", "-q", "-m", args.commit_message],
            cwd=target_dir,
        )
        push = ["git", "push"]
        if args.force:
            push.append("--force")
        push.extend(["origin", f"HEAD:{args.target_branch}"])
        run_git(push, cwd=target_dir)

    print(
        f"Pushed overlay commit to {args.target_repo or args.target_url} "
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
