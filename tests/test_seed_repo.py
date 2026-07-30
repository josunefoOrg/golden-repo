"""Tests for seed_repo.py (repo-to-repo seeding)."""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

tools_dir = Path(__file__).parent.parent / "tools"
sys.path.insert(0, str(tools_dir))

import seed_repo


def make_args(**overrides):
    args = MagicMock()
    args.target_repo = "mcaps-microsoft/new-repo"
    args.target_url = ""
    args.host = "github.com"
    args.target_branch = "main"
    args.source_ref = "HEAD"
    args.commit_message = "Initial import from golden-repo template"
    args.exclude = []
    args.exclude_file = None
    args.no_default_excludes = False
    args.author_name = "seeder"
    args.author_email = "seeder@example.com"
    args.force = False
    args.username = "x-access-token"
    args.dry_run = False
    for key, value in overrides.items():
        setattr(args, key, value)
    return args


class TestValidateArgs:
    def test_valid_owner_repo(self):
        seed_repo.validate_args(make_args(target_repo="org/name"))

    def test_invalid_owner_repo(self):
        with pytest.raises(seed_repo.SeedError, match="owner/name"):
            seed_repo.validate_args(make_args(target_repo="not-a-repo", target_url=""))

    def test_target_url_skips_owner_check(self):
        # target_url present, target_repo None -> no owner/name validation
        seed_repo.validate_args(
            make_args(target_repo=None, target_url="git@github.com:org/name.git")
        )


class TestResolveExcludes:
    def test_defaults_applied(self):
        result = seed_repo.resolve_excludes(make_args())
        assert ".github/workflows/provision-new-repo.yml" in result
        assert ".github/workflows/seed-target-repo.yml" in result

    def test_no_default_excludes(self):
        result = seed_repo.resolve_excludes(make_args(no_default_excludes=True))
        assert result == []

    def test_extra_excludes_deduped_and_normalized(self):
        result = seed_repo.resolve_excludes(
            make_args(
                no_default_excludes=True,
                exclude=["docs\\secret.md", "docs/secret.md", "tools/"],
            )
        )
        assert result == ["docs/secret.md", "tools"]

    def test_exclude_file(self, tmp_path):
        f = tmp_path / "excludes.txt"
        f.write_text("# comment\nfoo/bar\n\nbaz.txt\n", encoding="utf-8")
        result = seed_repo.resolve_excludes(
            make_args(no_default_excludes=True, exclude_file=str(f))
        )
        assert result == ["foo/bar", "baz.txt"]

    def test_missing_exclude_file(self):
        with pytest.raises(seed_repo.SeedError, match="exclude-file not found"):
            seed_repo.resolve_excludes(
                make_args(exclude_file="/no/such/file.txt")
            )


class TestBuildRemoteUrl:
    def test_https_url_with_token(self):
        url = seed_repo.build_remote_url(make_args(), "sekret")
        assert url == (
            "https://x-access-token:sekret@github.com/mcaps-microsoft/new-repo.git"
        )

    def test_token_is_url_encoded(self):
        url = seed_repo.build_remote_url(make_args(), "a/b+c")
        assert "a%2Fb%2Bc" in url

    def test_target_url_used_verbatim(self):
        args = make_args(target_repo=None, target_url="git@github.com:org/name.git")
        assert seed_repo.build_remote_url(args, "") == "git@github.com:org/name.git"

    def test_missing_token_raises(self):
        with pytest.raises(seed_repo.SeedError, match="TARGET_REPO_TOKEN is required"):
            seed_repo.build_remote_url(make_args(), "")


class TestRedactUrl:
    def test_credentials_redacted(self):
        url = "https://x-access-token:sekret@github.com/org/name.git"
        assert seed_repo.redact_url(url) == "https://***@github.com/org/name.git"

    def test_ssh_url_unchanged(self):
        url = "git@github.com:org/name.git"
        assert seed_repo.redact_url(url) == url


class TestApplyExcludes:
    def test_removes_files_and_dirs(self, tmp_path):
        (tmp_path / "keep.txt").write_text("keep", encoding="utf-8")
        (tmp_path / "drop.txt").write_text("drop", encoding="utf-8")
        nested = tmp_path / "sub" / "dir"
        nested.mkdir(parents=True)
        (nested / "file.txt").write_text("x", encoding="utf-8")

        seed_repo.apply_excludes(tmp_path, ["drop.txt", "sub"], dry_run=False)

        assert (tmp_path / "keep.txt").exists()
        assert not (tmp_path / "drop.txt").exists()
        assert not (tmp_path / "sub").exists()

    def test_missing_exclude_is_noop(self, tmp_path):
        # Should not raise if the excluded path is absent.
        seed_repo.apply_excludes(tmp_path, ["nope.txt"], dry_run=False)


class TestMainDryRun:
    def test_dry_run_pushes_nothing(self, monkeypatch, capsys):
        monkeypatch.setenv("TARGET_REPO_TOKEN", "tok")
        called = []
        monkeypatch.setattr(
            seed_repo.subprocess, "run", lambda *a, **k: called.append(a)
        )
        rc = seed_repo.main(
            ["--target-repo", "org/name", "--dry-run"]
        )
        assert rc == 0
        assert called == []  # no subprocess calls in dry-run
        out = capsys.readouterr().out
        assert "no changes were pushed" in out


class TestOverlayContent:
    def test_copies_files_without_deleting_target_only_files(self, tmp_path):
        source = tmp_path / "source"
        target = tmp_path / "target"
        (source / "sub").mkdir(parents=True)
        (source / "README.md").write_text("golden content", encoding="utf-8")
        (source / "sub" / "new.txt").write_text("new", encoding="utf-8")

        target.mkdir()
        (target / "README.md").write_text("placeholder", encoding="utf-8")
        (target / ".github").mkdir()
        (target / ".github" / "policies").mkdir()
        (target / ".github" / "policies" / "jit.yml").write_text(
            "policy: strict", encoding="utf-8"
        )

        seed_repo.overlay_content(source, target, dry_run=False)

        # Golden content overwrites the placeholder README.
        assert (target / "README.md").read_text(encoding="utf-8") == "golden content"
        # New golden files are added.
        assert (target / "sub" / "new.txt").read_text(encoding="utf-8") == "new"
        # Target-only content (e.g. StartRight compliance scaffolding) survives.
        assert (target / ".github" / "policies" / "jit.yml").read_text(
            encoding="utf-8"
        ) == "policy: strict"

    def test_dry_run_makes_no_changes(self, tmp_path):
        source = tmp_path / "source"
        target = tmp_path / "target"
        source.mkdir()
        target.mkdir()
        (source / "file.txt").write_text("x", encoding="utf-8")

        seed_repo.overlay_content(source, target, dry_run=True)

        assert not (target / "file.txt").exists()


def _init_bare_repo(path):
    import subprocess

    subprocess.run(["git", "init", "--bare", "-b", "main", str(path)], check=True)


def _clone_and_commit(bare_path, work_path, files, message):
    import subprocess

    subprocess.run(["git", "clone", str(bare_path), str(work_path)], check=True)
    for rel, content in files.items():
        full = work_path / rel
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_text(content, encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=work_path, check=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=tester",
            "-c",
            "user.email=tester@example.com",
            "commit",
            "-q",
            "-m",
            message,
        ],
        cwd=work_path,
        check=True,
    )
    subprocess.run(["git", "push", "-q", "origin", "main"], cwd=work_path, check=True)


class TestEndToEndSeeding:
    """Exercises the full clone -> overlay -> commit -> push flow against real
    local bare repositories, proving pre-existing target content survives."""

    def test_seed_preserves_existing_target_content(self, tmp_path, monkeypatch):
        import subprocess

        # Source "golden-repo" bare repo with a couple of tracked files.
        source_bare = tmp_path / "source.git"
        _init_bare_repo(source_bare)
        source_work = tmp_path / "source-work"
        _clone_and_commit(
            source_bare,
            source_work,
            {
                "README.md": "golden readme",
                "docs/guide.md": "guide",
                ".github/workflows/provision-new-repo.yml": "should-be-excluded",
            },
            "seed source commit",
        )

        # Target bare repo pre-seeded with StartRight-style scaffolding.
        target_bare = tmp_path / "target.git"
        _init_bare_repo(target_bare)
        target_seed_work = tmp_path / "target-seed-work"
        _clone_and_commit(
            target_bare,
            target_seed_work,
            {
                "README.md": "placeholder readme",
                ".github/policies/jit.yml": "policy: strict",
            },
            "startright scaffolding commit",
        )

        monkeypatch.chdir(source_work)
        args = seed_repo.parse_args(
            [
                "--target-url",
                str(target_bare),
                "--commit-message",
                "Import golden-repo template structure",
            ]
        )
        seed_repo.seed(args, token="")

        # Verify by cloning the target bare repo fresh.
        verify_dir = tmp_path / "verify"
        subprocess.run(["git", "clone", str(target_bare), str(verify_dir)], check=True)

        assert (verify_dir / "README.md").read_text(encoding="utf-8") == "golden readme"
        assert (verify_dir / "docs" / "guide.md").read_text(encoding="utf-8") == "guide"
        assert (verify_dir / ".github" / "policies" / "jit.yml").read_text(
            encoding="utf-8"
        ) == "policy: strict"
        assert not (
            verify_dir / ".github" / "workflows" / "provision-new-repo.yml"
        ).exists()

        # History from the StartRight scaffolding commit is preserved.
        log = subprocess.run(
            ["git", "log", "--oneline"],
            cwd=verify_dir,
            capture_output=True,
            text=True,
            check=True,
        )
        assert "startright scaffolding commit" in log.stdout
        assert log.stdout.count("\n") == 2  # two commits total

    def test_seed_is_idempotent_noop_on_second_run(self, tmp_path, monkeypatch, capsys):
        import subprocess

        source_bare = tmp_path / "source2.git"
        _init_bare_repo(source_bare)
        source_work = tmp_path / "source2-work"
        _clone_and_commit(
            source_bare, source_work, {"a.txt": "hello"}, "seed source commit"
        )

        target_bare = tmp_path / "target2.git"
        _init_bare_repo(target_bare)

        monkeypatch.chdir(source_work)
        args = seed_repo.parse_args(["--target-url", str(target_bare)])
        seed_repo.seed(args, token="")
        seed_repo.seed(args, token="")  # second run should be a no-op

        out = capsys.readouterr().out
        assert "nothing to commit" in out

        verify_dir = tmp_path / "verify2"
        subprocess.run(["git", "clone", str(target_bare), str(verify_dir)], check=True)
        log = subprocess.run(
            ["git", "log", "--oneline"],
            cwd=verify_dir,
            capture_output=True,
            text=True,
            check=True,
        )
        assert log.stdout.count("\n") == 1  # only one commit was ever pushed

    def test_seed_into_empty_target(self, tmp_path, monkeypatch):
        import subprocess

        source_bare = tmp_path / "source3.git"
        _init_bare_repo(source_bare)
        source_work = tmp_path / "source3-work"
        _clone_and_commit(
            source_bare, source_work, {"a.txt": "hello"}, "seed source commit"
        )

        target_bare = tmp_path / "target3.git"
        _init_bare_repo(target_bare)  # remains fully empty (no commits)

        monkeypatch.chdir(source_work)
        args = seed_repo.parse_args(["--target-url", str(target_bare)])
        seed_repo.seed(args, token="")

        verify_dir = tmp_path / "verify3"
        subprocess.run(["git", "clone", str(target_bare), str(verify_dir)], check=True)
        assert (verify_dir / "a.txt").read_text(encoding="utf-8") == "hello"
