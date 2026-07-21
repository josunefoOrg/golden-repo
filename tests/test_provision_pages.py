"""Tests for GitHub Pages enablement during provisioning."""

import base64
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

# Add tools directory to path for imports
tools_dir = Path(__file__).parent.parent / "tools"
sys.path.insert(0, str(tools_dir))

import provision_repo


def _args(name="test-repo", org="test-org", visibility="public"):
    return SimpleNamespace(name=name, org=org, visibility=visibility)


class TestPagesTemplate:
    """The Pages placeholder template must exist and carry the repo-name token."""

    def test_template_file_exists(self):
        template_path = (
            Path(__file__).parent.parent
            / "tools"
            / "templates"
            / "pages-index.template.md"
        )
        assert template_path.exists(), f"Template not found at {template_path}"

    def test_template_contains_repo_name_token(self):
        template_path = (
            Path(__file__).parent.parent
            / "tools"
            / "templates"
            / "pages-index.template.md"
        )
        assert "{{REPO_NAME}}" in template_path.read_text(encoding="utf-8")


class TestEnablePages:
    """enable_github_pages behavior across visibilities and modes."""

    def test_private_repo_is_skipped(self):
        client = MagicMock()
        client.dry_run = False
        summary = provision_repo.Summary()

        provision_repo.enable_github_pages(client, _args(visibility="private"), summary)

        assert summary.pages_enabled is False
        assert client.request.call_count == 0
        assert client.request_allowing_statuses.call_count == 0
        assert any("private" in item for item in summary.skipped)

    def test_dry_run_marks_enabled_without_api_calls(self):
        client = MagicMock()
        client.dry_run = True
        summary = provision_repo.Summary()

        provision_repo.enable_github_pages(client, _args(visibility="public"), summary)

        assert summary.pages_enabled is True
        assert summary.pages_url == "https://test-org.github.io/test-repo/"
        assert client.request.call_count == 0

    def test_public_repo_resets_docs_and_enables_pages(self):
        client = MagicMock()
        client.dry_run = False
        # 1) list docs/ (index + a stray page + a dir), 2) list docs/images,
        # 3) POST /pages -> 201 created.
        client.request_allowing_statuses.side_effect = [
            (200, [
                {"type": "file", "path": "docs/index.md", "sha": "idx-sha"},
                {"type": "file", "path": "docs/architecture.md", "sha": "arch-sha"},
                {"type": "dir", "path": "docs/images", "sha": "dir-sha"},
            ]),
            (200, [
                {"type": "file", "path": "docs/images/a.png", "sha": "img-sha"},
            ]),
            (201, {"html_url": "https://test-org.github.io/test-repo/"}),
        ]
        client.request.return_value = MagicMock()
        summary = provision_repo.Summary()

        provision_repo.enable_github_pages(client, _args(visibility="public"), summary)

        methods = [c[0][0] for c in client.request.call_args_list]
        paths = [c[0][1] for c in client.request.call_args_list]

        # The golden-repo docs are cleared: stray file and nested image deleted.
        assert "DELETE" in methods
        assert any(p.endswith("/contents/docs/architecture.md") for p in paths)
        assert any(p.endswith("/contents/docs/images/a.png") for p in paths)

        # The placeholder index.md is (re)written with the existing sha.
        put_calls = [c for c in client.request.call_args_list if c[0][0] == "PUT"]
        index_put = [c for c in put_calls if c[0][1].endswith("/contents/docs/index.md")]
        assert len(index_put) == 1
        body = index_put[0][1]["body"]
        assert body["sha"] == "idx-sha"
        decoded = base64.b64decode(body["content"]).decode("utf-8")
        assert "test-repo" in decoded
        assert "{{REPO_NAME}}" not in decoded

        # Pages was enabled from main /docs.
        post_call = client.request_allowing_statuses.call_args
        assert post_call[0][0] == "POST"
        assert post_call[0][1].endswith("/pages")
        assert post_call[1]["body"] == {"source": {"branch": "main", "path": "/docs"}}

        assert summary.pages_enabled is True
        assert summary.pages_url == "https://test-org.github.io/test-repo/"

    def test_existing_pages_is_updated_idempotently(self):
        client = MagicMock()
        client.dry_run = False
        # docs/ already reset to just index.md; POST /pages -> 409 (already exists).
        client.request_allowing_statuses.side_effect = [
            (200, [
                {"type": "file", "path": "docs/index.md", "sha": "existing-sha"},
            ]),
            (409, {"message": "Pages already exists"}),
        ]
        client.request.return_value = MagicMock()
        summary = provision_repo.Summary()

        provision_repo.enable_github_pages(client, _args(visibility="public"), summary)

        # Two PUTs: placeholder content (with sha) and the pages source update.
        methods = [c[0][0] for c in client.request.call_args_list]
        paths = [c[0][1] for c in client.request.call_args_list]
        assert methods == ["PUT", "PUT"]
        assert any(p.endswith("/pages") for p in paths)
        assert summary.pages_enabled is True

    def test_missing_template_raises(self, monkeypatch):
        client = MagicMock()
        client.dry_run = False
        summary = provision_repo.Summary()

        real_read_text = Path.read_text

        def fake_exists(self):
            if self.name == "pages-index.template.md":
                return False
            return True

        monkeypatch.setattr(Path, "exists", fake_exists)

        with pytest.raises(provision_repo.ProvisioningError, match="Pages placeholder template"):
            provision_repo.enable_github_pages(client, _args(visibility="public"), summary)


class TestProvisionStepOrdering:
    """Pages must be enabled before branch protection.

    The placeholder page is committed to main via the Contents API. A protected
    main branch rejects direct commits (HTTP 409), so enable_github_pages must
    run before apply_branch_protection.
    """

    def test_pages_runs_before_branch_protection(self, monkeypatch):
        calls: list[str] = []

        def recorder(name):
            def _fn(*args, **kwargs):
                calls.append(name)
            return _fn

        for step in (
            "create_or_get_repo",
            "wait_for_template_ready",
            "replace_readme_with_placeholder",
            "remove_provision_workflow",
            "enable_github_pages",
            "update_repo_settings",
            "provision_team_access",
            "apply_branch_protection",
            "enable_security_features",
            "note_codeowners_override",
            "print_summary",
        ):
            monkeypatch.setattr(provision_repo, step, recorder(step))

        rc = provision_repo.main(
            ["--org", "o", "--name", "n", "--visibility", "public", "--dry-run"]
        )

        assert rc == 0
        assert "enable_github_pages" in calls
        assert "apply_branch_protection" in calls
        assert calls.index("enable_github_pages") < calls.index("apply_branch_protection")

