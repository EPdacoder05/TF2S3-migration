"""
Validation Module

Input validation and environment checks for security and correctness.
"""

import logging
import os
import re
import subprocess

from . import config

logger = logging.getLogger(__name__)


def validate_repo_name(name: str) -> bool:
    """
    Validate repository name for security.

    Rejects:
    - Path traversal attempts (../, ..\\)
    - Shell metacharacters
    - Control characters
    - Invalid formats

    Args:
        name: Repository name to validate

    Returns:
        True if valid, False otherwise
    """
    if not name:
        logger.error("Repository name cannot be empty")
        return False

    # Check for path traversal
    if '..' in name:
        logger.error(f"Invalid repository name (path traversal): {name}")
        return False

    # Check for invalid patterns
    for pattern in config.INVALID_REPO_PATTERNS:
        if re.search(pattern, name):
            logger.error(f"Invalid repository name (contains invalid characters): {name}")
            return False

    # Check against valid pattern
    if not re.match(config.VALID_REPO_NAME_PATTERN, name):
        logger.error(f"Invalid repository name format: {name}")
        return False

    return True


def validate_repo_list(repos: list[str]) -> list[str]:
    """
    Validate a list of repository names.

    Args:
        repos: List of repository names

    Returns:
        List of valid repository names (invalid ones filtered out)
    """
    valid_repos = []

    for repo in repos:
        if validate_repo_name(repo):
            valid_repos.append(repo)
        else:
            logger.warning(f"Skipping invalid repository name: {repo}")

    return valid_repos


def validate_environment() -> bool:
    """
    Validate that required CLI tools are installed and configured.

    Checks for:
    - AWS CLI
    - Terraform CLI
    - GitHub CLI (gh)
    - Git

    Returns:
        True if environment is valid, False otherwise
    """
    logger.info("Validating environment")

    required_tools = {
        "aws": ["aws", "--version"],
        "terraform": ["terraform", "--version"],
        "gh": ["gh", "--version"],
        "git": ["git", "--version"],
    }

    all_valid = True

    for tool_name, cmd in required_tools.items():
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode == 0:
                version = result.stdout.strip().split('\n')[0]
                logger.info(f"✅ {tool_name}: {version}")
            else:
                logger.error(f"❌ {tool_name}: command failed")
                all_valid = False

        except FileNotFoundError:
            logger.error(f"❌ {tool_name}: not found in PATH")
            all_valid = False
        except Exception as e:
            logger.error(f"❌ {tool_name}: error checking - {e}")
            all_valid = False

    # Check AWS authentication
    if all_valid:
        try:
            result = subprocess.run(
                ["aws", "sts", "get-caller-identity"],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                logger.info("✅ AWS credentials configured")
            else:
                logger.warning("⚠️  AWS credentials not configured or invalid")

        except Exception as e:
            logger.warning(f"⚠️  Could not verify AWS credentials: {e}")

    # Check GitHub authentication
    if all_valid:
        try:
            result = subprocess.run(
                ["gh", "auth", "status"],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                logger.info("✅ GitHub CLI authenticated")
            else:
                logger.warning("⚠️  GitHub CLI not authenticated")
                logger.info("Run 'gh auth login' to authenticate")

        except Exception as e:
            logger.warning(f"⚠️  Could not verify GitHub authentication: {e}")

    if all_valid:
        logger.info("✅ Environment validation passed")
    else:
        logger.error("❌ Environment validation failed")

    return all_valid


def validate_scripts_path(path: str) -> bool:
    """
    Verify platform-scripts directory exists and contains required scripts.

    Args:
        path: Path to platform-scripts directory

    Returns:
        True if valid, False otherwise
    """
    if not path:
        return False

    if not os.path.isdir(path):
        logger.error(f"Platform scripts directory not found: {path}")
        return False

    # Check for required scripts
    required_scripts = ["copy_state.sh"]

    for script in required_scripts:
        script_path = os.path.join(path, script)
        if not os.path.isfile(script_path):
            logger.error(f"Required script not found: {script_path}")
            return False

    logger.info(f"✅ Platform scripts validated: {path}")
    return True


def find_platform_scripts() -> str | None:
    """
    Auto-detect platform-scripts directory from environment or standard locations.

    Returns:
        Path to platform-scripts directory, or None if not found
    """
    logger.info("Searching for platform-scripts directory")

    for path in config.PLATFORM_SCRIPTS_PATHS:
        if path and os.path.isdir(path) and validate_scripts_path(path):
            logger.info(f"✅ Found platform-scripts at: {path}")
            return path

    logger.warning("Platform scripts directory not found in standard locations")
    logger.info("Set PLATFORM_SCRIPTS_PATH environment variable or use --scripts-path")

    return None


def validate_aws_profile(profile: str) -> bool:
    """
    Validate that AWS profile exists and is configured.

    Args:
        profile: AWS profile name

    Returns:
        True if valid, False otherwise
    """
    try:
        result = subprocess.run(
            ["aws", "configure", "list", "--profile", profile],
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode == 0:
            logger.info(f"✅ AWS profile validated: {profile}")
            return True
        else:
            logger.error(f"❌ AWS profile not found or invalid: {profile}")
            return False

    except Exception as e:
        logger.error(f"Error validating AWS profile: {e}")
        return False


def validate_s3_bucket(bucket: str, region: str, profile: str) -> bool:
    """
    Validate that S3 bucket exists and is accessible.

    Args:
        bucket: S3 bucket name
        region: AWS region
        profile: AWS profile name

    Returns:
        True if valid, False otherwise
    """
    try:
        result = subprocess.run(
            ["aws", "s3", "ls", f"s3://{bucket}/", "--profile", profile, "--region", region],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0:
            logger.info(f"✅ S3 bucket accessible: {bucket}")
            return True
        else:
            logger.error(f"❌ S3 bucket not accessible: {bucket}")
            return False

    except Exception as e:
        logger.error(f"Error validating S3 bucket: {e}")
        return False


def validate_github_org(org: str) -> bool:
    """
    Validate that GitHub organization exists and is accessible.

    Args:
        org: GitHub organization name

    Returns:
        True if valid, False otherwise
    """
    try:
        result = subprocess.run(
            ["gh", "api", f"/orgs/{org}"],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0:
            logger.info(f"✅ GitHub organization accessible: {org}")
            return True
        else:
            logger.error(f"❌ GitHub organization not accessible: {org}")
            return False

    except Exception as e:
        logger.error(f"Error validating GitHub organization: {e}")
        return False


def validate_region(region: str) -> bool:
    """
    Validate AWS region format.

    Args:
        region: AWS region name

    Returns:
        True if valid format, False otherwise
    """
    # Basic AWS region format validation
    region_pattern = r'^[a-z]{2}-[a-z]+-\d+$'

    if re.match(region_pattern, region):
        return True
    else:
        logger.error(f"Invalid AWS region format: {region}")
        return False


def check_disk_space(path: str, required_gb: float = 1.0) -> bool:
    """
    Check if sufficient disk space is available.

    Args:
        path: Path to check
        required_gb: Required space in GB

    Returns:
        True if sufficient space, False otherwise
    """
    try:
        import shutil
        stat = shutil.disk_usage(path)
        available_gb = stat.free / (1024 ** 3)

        if available_gb >= required_gb:
            logger.info(f"✅ Sufficient disk space: {available_gb:.1f} GB available")
            return True
        else:
            logger.warning(f"⚠️  Low disk space: {available_gb:.1f} GB available (need {required_gb} GB)")
            return False

    except Exception as e:
        logger.warning(f"Could not check disk space: {e}")
        return True  # Don't fail if we can't check


def validate_batch_size(batch_size: int, max_size: int = 10) -> bool:
    """
    Validate batch size parameter.

    Args:
        batch_size: Requested batch size
        max_size: Maximum allowed batch size

    Returns:
        True if valid, False otherwise
    """
    if batch_size < 1:
        logger.error(f"Batch size must be at least 1: {batch_size}")
        return False

    if batch_size > max_size:
        logger.warning(f"Batch size {batch_size} exceeds recommended maximum {max_size}")
        return True  # Warning only, not an error

    return True


def validate_path_safety(path: str) -> bool:
    """
    Validate that a path is safe (no path traversal, etc.).

    Args:
        path: Path to validate

    Returns:
        True if safe, False otherwise
    """
    # Normalize path
    normalized = os.path.normpath(path)

    # Check for path traversal
    if '..' in normalized.split(os.sep):
        logger.error(f"Unsafe path (path traversal): {path}")
        return False

    return True
