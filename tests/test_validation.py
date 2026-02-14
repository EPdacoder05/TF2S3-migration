"""Tests for migrationlib.validation module."""
from migrationlib import validation


class TestRepoNameValidation:
    """Test repository name validation."""

    def test_valid_repo_name(self):
        assert validation.validate_repo_name("my-terraform-repo") is True

    def test_valid_repo_with_numbers(self):
        assert validation.validate_repo_name("repo-123") is True

    def test_empty_repo_name(self):
        assert validation.validate_repo_name("") is False

    def test_path_traversal_rejected(self):
        assert validation.validate_repo_name("../etc/passwd") is False

    def test_path_traversal_backslash(self):
        assert validation.validate_repo_name("..\\windows\\system32") is False


class TestRepoListValidation:
    """Test repository list validation."""

    def test_all_valid(self):
        repos = ["repo-a", "repo-b", "repo-c"]
        result = validation.validate_repo_list(repos)
        assert len(result) == 3

    def test_filters_invalid(self):
        repos = ["valid-repo", "../bad-repo", "another-valid"]
        result = validation.validate_repo_list(repos)
        assert len(result) == 2
        assert "../bad-repo" not in result
