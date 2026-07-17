"""Tests for README.md replacement during provisioning."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add tools directory to path for imports
tools_dir = Path(__file__).parent.parent / "tools"
sys.path.insert(0, str(tools_dir))

import provision_repo


class TestTemplateReadyWait:
    """Test that wait_for_template_ready handles async template population."""

    def test_wait_template_dry_run(self):
        """Test that dry-run skips polling."""
        client = MagicMock()
        client.dry_run = True
        
        args = MagicMock()
        args.name = "test-repo"
        args.org = "test-org"
        
        # Should not raise, should not call request
        provision_repo.wait_for_template_ready(client, args)
        
        assert client.request_allowing_statuses.call_count == 0

    def test_wait_template_empty_then_stable(self):
        """Test polling: empty repo (404), then stable HEAD across two polls."""
        client = MagicMock()
        client.dry_run = False
        
        # First call: 404 (repo empty)
        # Second call: 200 with commit sha abc123
        # Third call: 200 with same sha abc123 (stable)
        client.request_allowing_statuses.side_effect = [
            (404, None),
            (200, [{"sha": "abc123def"}]),
            (200, [{"sha": "abc123def"}]),
        ]
        
        args = MagicMock()
        args.name = "test-repo"
        args.org = "test-org"
        
        with patch("provision_repo.time.sleep"):  # Skip actual sleep
            provision_repo.wait_for_template_ready(client, args)
        
        # Should have made 3 calls
        assert client.request_allowing_statuses.call_count == 3

    def test_wait_template_409_then_stable(self):
        """Test polling: 409 (empty repo), then stable HEAD."""
        client = MagicMock()
        client.dry_run = False
        
        # First call: 409 (repo empty)
        # Second call: 200 with commit
        # Third call: 200 with same commit (stable)
        client.request_allowing_statuses.side_effect = [
            (409, {"message": "Git Repository is empty"}),
            (200, [{"sha": "xyz789abc"}]),
            (200, [{"sha": "xyz789abc"}]),
        ]
        
        args = MagicMock()
        args.name = "test-repo"
        args.org = "test-org"
        
        with patch("provision_repo.time.sleep"):  # Skip actual sleep
            provision_repo.wait_for_template_ready(client, args)
        
        assert client.request_allowing_statuses.call_count == 3

    def test_wait_template_changing_head_then_stable(self):
        """Test polling: HEAD changes, then stabilizes."""
        client = MagicMock()
        client.dry_run = False
        
        # Simulate HEAD changing then becoming stable
        client.request_allowing_statuses.side_effect = [
            (200, [{"sha": "commit1"}]),
            (200, [{"sha": "commit2"}]),  # HEAD changed
            (200, [{"sha": "commit2"}]),  # Now stable
        ]
        
        args = MagicMock()
        args.name = "test-repo"
        args.org = "test-org"
        
        with patch("provision_repo.time.sleep"):  # Skip actual sleep
            provision_repo.wait_for_template_ready(client, args)
        
        assert client.request_allowing_statuses.call_count == 3

    def test_wait_template_timeout_empty(self):
        """Test that timeout raises ProvisioningError when repo stays empty."""
        client = MagicMock()
        client.dry_run = False
        
        # Always return 404 (repo stays empty)
        client.request_allowing_statuses.return_value = (404, None)
        
        args = MagicMock()
        args.name = "test-repo"
        args.org = "test-org"
        
        with patch("provision_repo.time.sleep"):  # Skip actual sleep
            with pytest.raises(provision_repo.ProvisioningError, match="still empty"):
                provision_repo.wait_for_template_ready(client, args)

    def test_wait_template_timeout_unstable(self):
        """Test that timeout raises ProvisioningError when HEAD keeps changing."""
        client = MagicMock()
        client.dry_run = False
        
        # Simulate HEAD constantly changing (never stable)
        call_count = [0]
        def changing_head(*args, **kwargs):
            call_count[0] += 1
            return (200, [{"sha": f"commit{call_count[0]}"}])
        
        client.request_allowing_statuses.side_effect = changing_head
        
        args = MagicMock()
        args.name = "test-repo"
        args.org = "test-org"
        
        with patch("provision_repo.time.sleep"):  # Skip actual sleep
            with pytest.raises(provision_repo.ProvisioningError, match="still changing"):
                provision_repo.wait_for_template_ready(client, args)


class TestReadmePlaceholder:
    """Test that README.md is replaced with the placeholder template."""

    def test_template_file_exists(self):
        """Verify that the README template file exists at the expected path."""
        script_dir = Path(__file__).parent.parent / "tools"
        template_path = script_dir / "templates" / "README.template.md"
        assert template_path.exists(), f"Template not found at {template_path}"

    def test_template_contains_repo_name_token(self):
        """Verify that the template contains the {{REPO_NAME}} token."""
        script_dir = Path(__file__).parent.parent / "tools"
        template_path = script_dir / "templates" / "README.template.md"
        content = template_path.read_text(encoding="utf-8")
        assert "{{REPO_NAME}}" in content, "Template must contain {{REPO_NAME}} token"

    def test_replace_readme_dry_run(self):
        """Test README replacement in dry-run mode."""
        client = MagicMock()
        client.dry_run = True
        
        args = MagicMock()
        args.name = "test-repo"
        args.org = "test-org"
        
        summary = provision_repo.Summary()
        
        provision_repo.replace_readme_with_placeholder(client, args, summary)
        
        assert summary.readme_replaced is True
        assert client.request.call_count == 0  # No API calls in dry-run

    @patch("provision_repo.Path")
    def test_replace_readme_missing_template(self, mock_path):
        """Test that missing template raises ProvisioningError."""
        mock_template_path = MagicMock()
        mock_template_path.exists.return_value = False
        
        mock_path_obj = MagicMock()
        mock_path_obj.__truediv__ = lambda self, other: mock_template_path
        mock_path.return_value.parent.__truediv__ = lambda self, other: mock_path_obj
        
        client = MagicMock()
        client.dry_run = False
        
        args = MagicMock()
        args.name = "test-repo"
        args.org = "test-org"
        
        summary = provision_repo.Summary()
        
        with pytest.raises(provision_repo.ProvisioningError, match="README template not found"):
            provision_repo.replace_readme_with_placeholder(client, args, summary)

    def test_replace_readme_substitutes_repo_name(self):
        """Test that {{REPO_NAME}} is correctly substituted in the content."""
        client = MagicMock()
        client.dry_run = False
        client.request_allowing_statuses.return_value = (404, None)
        client.request.return_value = MagicMock()
        
        args = MagicMock()
        args.name = "my-awesome-repo"
        args.org = "test-org"
        
        summary = provision_repo.Summary()
        
        provision_repo.replace_readme_with_placeholder(client, args, summary)
        
        # Verify the PUT call was made
        assert client.request.call_count == 1
        call_args = client.request.call_args
        
        # Check that we're PUTting to the correct endpoint
        assert call_args[0][0] == "PUT"
        assert "/contents/README.md" in call_args[0][1]
        
        # Check that the body contains base64-encoded content
        body = call_args[1]["body"]
        assert "content" in body
        assert "message" in body
        
        # Decode and verify the content contains the substituted repo name
        import base64
        decoded_content = base64.b64decode(body["content"]).decode("utf-8")
        assert "my-awesome-repo" in decoded_content
        assert "{{REPO_NAME}}" not in decoded_content
        
        assert summary.readme_replaced is True

    def test_replace_readme_idempotent_with_existing_file(self):
        """Test that README replacement is idempotent by including sha when file exists."""
        client = MagicMock()
        client.dry_run = False
        client.request_allowing_statuses.return_value = (
            200,
            {"sha": "abc123existing"}
        )
        client.request.return_value = MagicMock()
        
        args = MagicMock()
        args.name = "test-repo"
        args.org = "test-org"
        
        summary = provision_repo.Summary()
        
        provision_repo.replace_readme_with_placeholder(client, args, summary)
        
        # Verify the PUT call includes the sha for idempotent update
        call_args = client.request.call_args
        body = call_args[1]["body"]
        assert "sha" in body
        assert body["sha"] == "abc123existing"
        
        assert summary.readme_replaced is True


class TestProvisionWorkflowRemoval:
    """Test that provision-new-repo.yml workflow is removed from generated repos."""

    def test_remove_workflow_dry_run(self):
        """Test workflow removal in dry-run mode."""
        client = MagicMock()
        client.dry_run = True
        
        args = MagicMock()
        args.name = "test-repo"
        args.org = "test-org"
        
        summary = provision_repo.Summary()
        
        provision_repo.remove_provision_workflow(client, args, summary)
        
        assert summary.provision_workflow_removed is True
        assert client.request_allowing_statuses.call_count == 0  # No API calls in dry-run
        assert client.request.call_count == 0

    def test_remove_workflow_file_present(self):
        """Test workflow removal when file exists (GET 200 returns sha)."""
        client = MagicMock()
        client.dry_run = False
        client.request_allowing_statuses.return_value = (
            200,
            {"sha": "workflow-file-sha-abc123"}
        )
        client.request.return_value = MagicMock()
        
        args = MagicMock()
        args.name = "test-repo"
        args.org = "test-org"
        
        summary = provision_repo.Summary()
        
        provision_repo.remove_provision_workflow(client, args, summary)
        
        # Verify GET was called to fetch the sha
        assert client.request_allowing_statuses.call_count == 1
        get_call = client.request_allowing_statuses.call_args
        assert get_call[0][0] == "GET"
        assert ".github/workflows/provision-new-repo.yml" in get_call[0][1]
        
        # Verify DELETE was called with the correct path and sha
        assert client.request.call_count == 1
        delete_call = client.request.call_args
        assert delete_call[0][0] == "DELETE"
        assert ".github/workflows/provision-new-repo.yml" in delete_call[0][1]
        
        body = delete_call[1]["body"]
        assert "sha" in body
        assert body["sha"] == "workflow-file-sha-abc123"
        assert "message" in body
        
        assert summary.provision_workflow_removed is True

    def test_remove_workflow_file_absent(self):
        """Test workflow removal when file is absent (GET 404) - idempotent."""
        client = MagicMock()
        client.dry_run = False
        client.request_allowing_statuses.return_value = (404, None)
        
        args = MagicMock()
        args.name = "test-repo"
        args.org = "test-org"
        
        summary = provision_repo.Summary()
        
        # Should not raise, should handle 404 gracefully
        provision_repo.remove_provision_workflow(client, args, summary)
        
        # Verify GET was called
        assert client.request_allowing_statuses.call_count == 1
        
        # Verify DELETE was NOT called (file doesn't exist)
        assert client.request.call_count == 0
        
        # Summary flag should not be set when file is absent
        assert summary.provision_workflow_removed is False

