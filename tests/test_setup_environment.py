"""Tests for setup_environment.py (environment protection-rule automation)."""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

tools_dir = Path(__file__).parent.parent / "tools"
sys.path.insert(0, str(tools_dir))

import setup_environment as se


def make_args(**overrides):
    args = MagicMock()
    args.org = "josunefoOrg"
    args.repo = "golden-repo"
    args.environment = "repo-provisioning"
    args.reviewer_team = ["maintainers"]
    args.reviewer_user = []
    args.wait_timer = 0
    args.prevent_self_review = False
    args.protected_branches_only = False
    args.dry_run = False
    for key, value in overrides.items():
        setattr(args, key, value)
    return args


class TestValidateArgs:
    def test_requires_at_least_one_reviewer(self):
        args = make_args(reviewer_team=[], reviewer_user=[])
        with pytest.raises(se.ProvisioningError, match="At least one"):
            se.validate_args(args)

    def test_rejects_too_many_reviewers(self):
        args = make_args(
            reviewer_team=["a", "b", "c", "d"], reviewer_user=["e", "f", "g"]
        )
        with pytest.raises(se.ProvisioningError, match="at most 6"):
            se.validate_args(args)

    def test_rejects_invalid_wait_timer(self):
        args = make_args(wait_timer=-1)
        with pytest.raises(se.ProvisioningError, match="wait-timer"):
            se.validate_args(args)

    def test_valid_args_pass(self):
        se.validate_args(make_args())


class TestBuildReviewers:
    def test_resolves_team_and_user_ids(self):
        session = MagicMock()
        team_response = MagicMock(status_code=200)
        team_response.json.return_value = {"id": 111}
        user_response = MagicMock(status_code=200)
        user_response.json.return_value = {"id": 222}
        session.get.side_effect = [team_response, user_response]

        args = make_args(reviewer_team=["maintainers"], reviewer_user=["octocat"])
        reviewers = se.build_reviewers(session, args)

        assert reviewers == [
            {"type": "Team", "id": 111},
            {"type": "User", "id": 222},
        ]

    def test_dry_run_skips_lookup(self):
        session = MagicMock()
        args = make_args(dry_run=True, reviewer_team=["maintainers"])
        reviewers = se.build_reviewers(session, args)
        assert reviewers == [{"type": "Team", "id": -1}]
        assert session.get.call_count == 0

    def test_team_lookup_failure_raises(self):
        session = MagicMock()
        response = MagicMock(status_code=404, text="Not Found")
        session.get.return_value = response
        args = make_args(reviewer_team=["missing-team"], reviewer_user=[])
        with pytest.raises(se.ApiError, match="HTTP 404"):
            se.build_reviewers(session, args)


class TestBuildBody:
    def test_body_shape(self):
        args = make_args(wait_timer=15, prevent_self_review=True)
        body = se.build_body(args, [{"type": "Team", "id": 1}])
        assert body == {
            "wait_timer": 15,
            "prevent_self_review": True,
            "reviewers": [{"type": "Team", "id": 1}],
            "deployment_branch_policy": {
                "protected_branches": False,
                "custom_branch_policies": True,
            },
        }

    def test_protected_branches_only_flips_policy(self):
        args = make_args(protected_branches_only=True)
        body = se.build_body(args, [])
        assert body["deployment_branch_policy"] == {
            "protected_branches": True,
            "custom_branch_policies": False,
        }


class TestApplyEnvironment:
    def test_dry_run_does_not_call_api(self):
        session = MagicMock()
        args = make_args(dry_run=True)
        result = se.apply_environment(session, args, {"reviewers": []})
        assert result is None
        assert session.put.call_count == 0

    def test_success_returns_json(self):
        session = MagicMock()
        response = MagicMock(status_code=200)
        response.json.return_value = {"name": "repo-provisioning"}
        session.put.return_value = response
        args = make_args()
        result = se.apply_environment(session, args, {"reviewers": []})
        assert result == {"name": "repo-provisioning"}

    def test_error_status_raises(self):
        session = MagicMock()
        response = MagicMock(status_code=422, text="bad request")
        session.put.return_value = response
        args = make_args()
        with pytest.raises(se.ApiError, match="HTTP 422"):
            se.apply_environment(session, args, {"reviewers": []})


class TestMain:
    def test_missing_token_fails(self, monkeypatch):
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        argv = [
            "--org", "o", "--repo", "r", "--reviewer-team", "maintainers",
        ]
        assert se.main(argv) == 1

    def test_dry_run_without_token_succeeds(self, monkeypatch):
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        argv = [
            "--org", "o", "--repo", "r",
            "--reviewer-team", "maintainers", "--dry-run",
        ]
        assert se.main(argv) == 0

    def test_no_reviewers_fails_argparse_validation(self, monkeypatch):
        monkeypatch.setenv("GITHUB_TOKEN", "token")
        argv = ["--org", "o", "--repo", "r"]
        assert se.main(argv) == 1
