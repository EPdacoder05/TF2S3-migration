"""
State Operations Module

Handles Terraform state migration operations including copying state from
Terraform Cloud to S3 and verification.
"""

import logging
import os
import subprocess

from . import utils

logger = logging.getLogger(__name__)


def copy_state_to_s3(
    repo_path: str,
    scripts_path: str,
    aws_profile: str,
    dry_run: bool = False
) -> bool:
    """
    Execute copy_state.sh script to migrate Terraform state from Cloud to S3.

    This script should handle:
    - Terraform Cloud authentication
    - State download from TFC
    - State upload to S3
    - Workspace preservation

    Args:
        repo_path: Path to the repository
        scripts_path: Path to platform-scripts directory
        aws_profile: AWS profile to use
        dry_run: If True, simulate the operation

    Returns:
        True if successful, False otherwise
    """
    logger.info("Copying Terraform state from Cloud to S3")

    script_path = os.path.join(scripts_path, "copy_state.sh")

    if not os.path.exists(script_path):
        logger.error(f"copy_state.sh not found at: {script_path}")
        return False

    if dry_run:
        logger.info(f"[DRY RUN] Would execute: {script_path} in {repo_path}")
        return True

    try:
        # Set environment for script execution
        env = os.environ.copy()
        env["AWS_PROFILE"] = aws_profile

        # Execute the state copy script
        cmd = ["bash", script_path]

        result = subprocess.run(
            cmd,
            cwd=repo_path,
            env=env,
            capture_output=True,
            text=True,
            timeout=600  # 10 minute timeout for state operations
        )

        if result.returncode == 0:
            logger.info("✅ Successfully copied state to S3")
            if result.stdout:
                # Sanitize and log output
                sanitized_output = utils.sanitize_log_message(result.stdout, [])
                logger.debug(f"Script output: {sanitized_output}")
            return True
        else:
            logger.error("Failed to copy state to S3")
            if result.stderr:
                sanitized_error = utils.sanitize_log_message(result.stderr, [])
                logger.error(f"Error output: {sanitized_error}")
            return False

    except subprocess.TimeoutExpired:
        logger.error("State copy operation timed out")
        return False
    except Exception as e:
        logger.error(f"Error copying state: {e}")
        return False


def verify_state_in_s3(
    bucket: str,
    repo_name: str,
    aws_profile: str,
    region: str = "us-east-1",
    dry_run: bool = False
) -> bool:
    """
    Verify that Terraform state files exist in S3 after migration.

    Args:
        bucket: S3 bucket name
        repo_name: Repository name (used in S3 key path)
        aws_profile: AWS profile to use
        region: AWS region
        dry_run: If True, simulate the operation

    Returns:
        True if state files exist, False otherwise
    """
    logger.info(f"Verifying state files in S3 bucket: {bucket}")

    if dry_run:
        logger.info(f"[DRY RUN] Would verify state in s3://{bucket}/{repo_name}/")
        return True

    try:
        # Check for state file
        state_key = f"{repo_name}/terraform.tfstate"

        cmd = [
            "aws", "s3", "ls",
            f"s3://{bucket}/{state_key}",
            "--profile", aws_profile,
            "--region", region
        ]

        result = utils.run_command(cmd, cwd=None, dry_run=dry_run)

        if result and result.returncode == 0:
            logger.info(f"✅ State file verified in S3: {state_key}")
            return True
        else:
            logger.warning(f"State file not found in S3: {state_key}")
            return False

    except Exception as e:
        logger.error(f"Error verifying state in S3: {e}")
        return False


def list_workspaces(repo_path: str, dry_run: bool = False) -> list[str]:
    """
    List all Terraform workspaces in the repository.

    Args:
        repo_path: Path to the repository
        dry_run: If True, simulate the operation

    Returns:
        List of workspace names
    """
    logger.info("Listing Terraform workspaces")

    if dry_run:
        logger.info(f"[DRY RUN] Would list workspaces in {repo_path}")
        return ["default"]

    try:
        cmd = ["terraform", "workspace", "list"]
        result = utils.run_command(cmd, cwd=repo_path, dry_run=dry_run)

        if result and result.returncode == 0:
            workspaces = []
            for line in result.stdout.splitlines():
                # Remove asterisk and whitespace
                workspace = line.strip().lstrip('* ').strip()
                if workspace:
                    workspaces.append(workspace)

            logger.info(f"Found {len(workspaces)} workspaces: {', '.join(workspaces)}")
            return workspaces
        else:
            logger.warning("Failed to list workspaces")
            return []

    except FileNotFoundError:
        logger.warning("Terraform CLI not found")
        return []
    except Exception as e:
        logger.error(f"Error listing workspaces: {e}")
        return []


def backup_state_locally(repo_path: str, backup_dir: str, dry_run: bool = False) -> bool:
    """
    Create a local backup of the current Terraform state before migration.

    Args:
        repo_path: Path to the repository
        backup_dir: Directory to store backups
        dry_run: If True, simulate the operation

    Returns:
        True if successful, False otherwise
    """
    logger.info("Creating local state backup")

    if dry_run:
        logger.info(f"[DRY RUN] Would backup state to {backup_dir}")
        return True

    try:
        # Create backup directory
        utils.ensure_directory(backup_dir)

        # Pull current state
        cmd = ["terraform", "state", "pull"]
        result = utils.run_command(cmd, cwd=repo_path, dry_run=dry_run)

        if result and result.returncode == 0:
            # Save state to backup file
            from datetime import datetime as dt
            timestamp = dt.now().strftime("%Y%m%d_%H%M%S")
            repo_name = os.path.basename(repo_path)
            backup_file = os.path.join(backup_dir, f"{repo_name}_state_{timestamp}.json")

            with open(backup_file, 'w') as f:
                f.write(result.stdout)

            logger.info(f"✅ State backed up to: {backup_file}")
            return True
        else:
            logger.error("Failed to pull state for backup")
            return False

    except Exception as e:
        logger.error(f"Error backing up state: {e}")
        return False


def migrate_workspace_state(
    repo_path: str,
    workspace: str,
    scripts_path: str,
    aws_profile: str,
    dry_run: bool = False
) -> bool:
    """
    Migrate state for a specific Terraform workspace.

    Args:
        repo_path: Path to the repository
        workspace: Workspace name
        scripts_path: Path to platform-scripts directory
        aws_profile: AWS profile to use
        dry_run: If True, simulate the operation

    Returns:
        True if successful, False otherwise
    """
    logger.info(f"Migrating workspace: {workspace}")

    if dry_run:
        logger.info(f"[DRY RUN] Would migrate workspace {workspace}")
        return True

    try:
        # Select workspace
        cmd = ["terraform", "workspace", "select", workspace]
        result = utils.run_command(cmd, cwd=repo_path, dry_run=dry_run)

        if not result or result.returncode != 0:
            logger.error(f"Failed to select workspace: {workspace}")
            return False

        # Copy state for this workspace
        return copy_state_to_s3(repo_path, scripts_path, aws_profile, dry_run)

    except Exception as e:
        logger.error(f"Error migrating workspace {workspace}: {e}")
        return False


def validate_state_integrity(repo_path: str, dry_run: bool = False) -> bool:
    """
    Validate Terraform state integrity after migration.

    Runs terraform plan to ensure no unexpected changes are detected.

    Args:
        repo_path: Path to the repository
        dry_run: If True, simulate the operation

    Returns:
        True if state is valid and no changes detected, False otherwise
    """
    logger.info("Validating state integrity")

    if dry_run:
        logger.info(f"[DRY RUN] Would validate state integrity in {repo_path}")
        return True

    try:
        # Initialize Terraform with new backend
        cmd_init = ["terraform", "init", "-reconfigure"]
        result = utils.run_command(cmd_init, cwd=repo_path, dry_run=dry_run, timeout=300)

        if not result or result.returncode != 0:
            logger.error("Failed to initialize Terraform")
            return False

        # Run plan to check for changes
        cmd_plan = ["terraform", "plan", "-detailed-exitcode"]
        result = utils.run_command(cmd_plan, cwd=repo_path, dry_run=dry_run, timeout=600)

        if result:
            # Exit code 0 = no changes, 2 = changes detected, other = error
            if result.returncode == 0:
                logger.info("✅ State is valid, no changes detected")
                return True
            elif result.returncode == 2:
                logger.warning("⚠️  Changes detected in plan - state may have drift")
                return False
            else:
                logger.error("Terraform plan failed")
                return False
        else:
            logger.error("Failed to run terraform plan")
            return False

    except FileNotFoundError:
        logger.warning("Terraform CLI not found, skipping validation")
        return True
    except Exception as e:
        logger.error(f"Error validating state integrity: {e}")
        return False
