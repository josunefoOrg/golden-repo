"""Tests for README.md replacement during provisioning."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add tools directory to path for imports
tools_dir = Path(__file__).parent.parent / "tools"
sys.path.insert(0, str(tools_dir))

import provision_repo


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
