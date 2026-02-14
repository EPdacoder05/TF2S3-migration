"""Tests for migrationlib.config module."""
from migrationlib import config


class TestConfigDefaults:
    """Test configuration default values."""

    def test_default_organization_is_generic(self):
        """Ensure no real org name is hardcoded."""
        assert config.DEFAULT_ORGANIZATION == "your-org"

    def test_default_bucket_is_generic(self):
        """Ensure no real bucket name is hardcoded."""
        assert "your-org" in config.DEFAULT_BUCKET_NAME

    def test_default_region_is_set(self):
        """Ensure a valid AWS region is set."""
        assert config.DEFAULT_REGION.startswith("us-") or config.DEFAULT_REGION.startswith("eu-")

    def test_default_branch_name(self):
        """Ensure migration branch name is set."""
        assert config.DEFAULT_BRANCH_NAME == "migrate-to-s3-backend"

    def test_batch_size_is_positive(self):
        """Ensure batch size is a positive integer."""
        assert isinstance(config.DEFAULT_BATCH_SIZE, int)
        assert config.DEFAULT_BATCH_SIZE >= 1

    def test_timeout_is_reasonable(self):
        """Ensure timeout is between 30s and 1800s."""
        assert 30 <= config.DEFAULT_TIMEOUT <= 1800

    def test_sensitive_patterns_exist(self):
        """Ensure sensitive patterns are defined for log redaction."""
        assert len(config.SENSITIVE_PATTERNS) > 0
        assert any("AKIA" in p for p in config.SENSITIVE_PATTERNS)  # AWS key pattern

    def test_backend_template_has_placeholders(self):
        """Ensure S3 backend template has format placeholders."""
        assert "{bucket}" in config.BACKEND_TEMPLATE
