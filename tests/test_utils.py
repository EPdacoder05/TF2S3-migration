"""Tests for migrationlib.utils module."""
from migrationlib import utils


class TestSanitizeLogMessage:
    """Test log message sanitization."""

    def test_redacts_aws_access_key(self):
        msg = "Found key AKIAIOSFODNN7EXAMPLE in config"
        result = utils.sanitize_log_message(msg)
        assert "AKIAIOSFODNN7EXAMPLE" not in result
        assert "[REDACTED]" in result

    def test_redacts_github_pat(self):
        msg = "Token: ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefgh"
        result = utils.sanitize_log_message(msg)
        assert "ghp_" not in result

    def test_safe_message_unchanged(self):
        msg = "Migration completed successfully for repo-name"
        result = utils.sanitize_log_message(msg)
        assert result == msg


class TestParseListArgument:
    """Test comma-separated list parsing."""

    def test_single_item(self):
        result = utils.parse_list_argument("repo-a")
        assert result == ["repo-a"]

    def test_multiple_items(self):
        result = utils.parse_list_argument("repo-a,repo-b,repo-c")
        assert len(result) == 3

    def test_strips_whitespace(self):
        result = utils.parse_list_argument("repo-a , repo-b , repo-c")
        assert all(not r.startswith(" ") and not r.endswith(" ") for r in result)
