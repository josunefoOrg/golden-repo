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

    def test_public_repo_publishes_placeholder_and_enables_pages(self):
        client = MagicMock()
        client.dry_run = False
        # GET placeholder (404 = new file), then POST /pages (201 = created).
        client.request_allowing_statuses.side_effect = [
            (404, None),
            (201, {"html_url": "https://test-org.github.io/test-repo/"}),
        ]
        client.request.return_value = MagicMock()
        summary = provision_repo.Summary()

        provision_repo.enable_github_pages(client, _args(visibility="public"), summary)

        # The placeholder page was committed via PUT contents.
        put_call = client.request.call_args
        assert put_call[0][0] == "PUT"
        assert "/contents/docs/index.md" in put_call[0][1]
        decoded = base64.b64decode(put_call[1]["body"]["content"]).decode("utf-8")
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
        # GET placeholder existing (200 w/ sha), then POST /pages 409 (already exists).
        client.request_allowing_statuses.side_effect = [
            (200, {"sha": "existing-sha"}),
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

