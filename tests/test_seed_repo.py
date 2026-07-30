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
