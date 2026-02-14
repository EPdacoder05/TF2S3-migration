"""
GitHub Operations Module

Handles all GitHub-related operations including repository cloning, branch management,
PR creation, and workflow updates.
"""

import os
import logging
import subprocess
from typing import Optional, List

from . import utils

logger = logging.getLogger(__name__)


def clone_repo(org: str, repo_name: str, work_dir: str, dry_run: bool = False) -> Optional[str]:
    """
    Clone a GitHub repository using GitHub CLI.
    
    Args:
        org: GitHub organization name
        repo_name: Repository name
        work_dir: Working directory for cloning
        dry_run: If True, simulate the operation
        
    Returns:
        Path to cloned repository, or None on failure
    """
    logger.info(f"Cloning repository: {org}/{repo_name}")
    
    repo_path = os.path.join(work_dir, repo_name)
    
    if dry_run:
        logger.info(f"[DRY RUN] Would clone {org}/{repo_name} to {repo_path}")
        return repo_path
    
    # Remove existing directory if present
    if os.path.exists(repo_path):
        logger.warning(f"Repository directory already exists: {repo_path}")
        return repo_path
    
    try:
        cmd = ["gh", "repo", "clone", f"{org}/{repo_name}", repo_path]
        result = utils.run_command(cmd, cwd=work_dir, dry_run=dry_run)
        
        if result and result.returncode == 0:
            logger.info(f"✅ Successfully cloned {org}/{repo_name}")
            return repo_path
        else:
            logger.error(f"Failed to clone {org}/{repo_name}")
            return None
            
    except Exception as e:
        logger.error(f"Error cloning repository: {e}")
        return None


def create_branch(repo_path: str, branch_name: str, dry_run: bool = False) -> bool:
    """
    Create and checkout a new Git branch.
    
    Args:
        repo_path: Path to the repository
        branch_name: Name of the branch to create
        dry_run: If True, simulate the operation
        
    Returns:
        True if successful, False otherwise
    """
    logger.info(f"Creating branch: {branch_name}")
    
    if dry_run:
        logger.info(f"[DRY RUN] Would create branch {branch_name} in {repo_path}")
        return True
    
    try:
        # Create and checkout new branch
        cmd = ["git", "checkout", "-b", branch_name]
        result = utils.run_command(cmd, cwd=repo_path, dry_run=dry_run)
        
        if result and result.returncode == 0:
            logger.info(f"✅ Successfully created branch {branch_name}")
            return True
        else:
            logger.error(f"Failed to create branch {branch_name}")
            return False
            
    except Exception as e:
        logger.error(f"Error creating branch: {e}")
        return False


def commit_changes(repo_path: str, message: str, dry_run: bool = False) -> bool:
    """
    Stage and commit all changes in the repository.
    
    Args:
        repo_path: Path to the repository
        message: Commit message
        dry_run: If True, simulate the operation
        
    Returns:
        True if successful, False otherwise
    """
    logger.info(f"Committing changes with message: {message}")
    
    if dry_run:
        logger.info(f"[DRY RUN] Would commit changes in {repo_path}")
        return True
    
    try:
        # Stage all changes
        cmd_add = ["git", "add", "."]
        result = utils.run_command(cmd_add, cwd=repo_path, dry_run=dry_run)
        
        if not result or result.returncode != 0:
            logger.error("Failed to stage changes")
            return False
        
        # Check if there are changes to commit
        cmd_status = ["git", "status", "--porcelain"]
        result = utils.run_command(cmd_status, cwd=repo_path, dry_run=dry_run)
        
        if not result or not result.stdout.strip():
            logger.info("No changes to commit")
            return True
        
        # Commit changes
        cmd_commit = ["git", "commit", "-m", message]
        result = utils.run_command(cmd_commit, cwd=repo_path, dry_run=dry_run)
        
        if result and result.returncode == 0:
            logger.info("✅ Successfully committed changes")
            return True
        else:
            logger.error("Failed to commit changes")
            return False
            
    except Exception as e:
        logger.error(f"Error committing changes: {e}")
        return False


def push_changes(repo_path: str, branch_name: str, dry_run: bool = False) -> bool:
    """
    Push changes to remote repository.
    
    Args:
        repo_path: Path to the repository
        branch_name: Name of the branch to push
        dry_run: If True, simulate the operation
        
    Returns:
        True if successful, False otherwise
    """
    logger.info(f"Pushing branch: {branch_name}")
    
    if dry_run:
        logger.info(f"[DRY RUN] Would push branch {branch_name} from {repo_path}")
        return True
    
    try:
        cmd = ["git", "push", "-u", "origin", branch_name]
        result = utils.run_command(cmd, cwd=repo_path, dry_run=dry_run)
        
        if result and result.returncode == 0:
            logger.info(f"✅ Successfully pushed branch {branch_name}")
            return True
        else:
            logger.error(f"Failed to push branch {branch_name}")
            return False
            
    except Exception as e:
        logger.error(f"Error pushing changes: {e}")
        return False


def create_pull_request(
    repo_path: str,
    org: str,
    repo_name: str,
    branch_name: str,
    title: str,
    body: str,
    dry_run: bool = False
) -> bool:
    """
    Create a pull request using GitHub CLI.
    
    Args:
        repo_path: Path to the repository
        org: GitHub organization name
        repo_name: Repository name
        branch_name: Source branch for the PR
        title: PR title
        body: PR description
        dry_run: If True, simulate the operation
        
    Returns:
        True if successful, False otherwise
    """
    logger.info(f"Creating pull request: {title}")
    
    if dry_run:
        logger.info(f"[DRY RUN] Would create PR for {org}/{repo_name}")
        logger.info(f"[DRY RUN] Title: {title}")
        logger.info(f"[DRY RUN] Branch: {branch_name}")
        return True
    
    try:
        cmd = [
            "gh", "pr", "create",
            "--title", title,
            "--body", body,
            "--base", "main",
            "--head", branch_name
        ]
        
        result = utils.run_command(cmd, cwd=repo_path, dry_run=dry_run)
        
        if result and result.returncode == 0:
            logger.info(f"✅ Successfully created pull request")
            if result.stdout:
                logger.info(f"PR URL: {result.stdout.strip()}")
            return True
        else:
            logger.error("Failed to create pull request")
            return False
            
    except Exception as e:
        logger.error(f"Error creating pull request: {e}")
        return False


def update_workflow_secrets(repo_path: str, dry_run: bool = False) -> int:
    """
    Update GitHub Actions workflow files to inject required secrets.
    
    Adds gh-readaccess-pat secret reference to workflow files that need it.
    
    Args:
        repo_path: Path to the repository
        dry_run: If True, simulate the operation
        
    Returns:
        Number of workflow files updated
    """
    logger.info("Updating GitHub Actions workflow files")
    
    workflow_dir = os.path.join(repo_path, ".github", "workflows")
    
    if not os.path.exists(workflow_dir):
        logger.info("No GitHub Actions workflows found")
        return 0
    
    if dry_run:
        logger.info(f"[DRY RUN] Would update workflows in {workflow_dir}")
        return 0
    
    update_count = 0
    
    try:
        for filename in os.listdir(workflow_dir):
            if not (filename.endswith(".yml") or filename.endswith(".yaml")):
                continue
            
            filepath = os.path.join(workflow_dir, filename)
            
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check if workflow needs secret injection
            # Look for terraform commands that might need private module access
            if "terraform" in content.lower() and "gh-readaccess-pat" not in content:
                # Add secret to env section or create one
                if "env:" in content:
                    # Add to existing env section
                    env_pattern = r'(env:)'
                    replacement = r'\1\n  GITHUB_TOKEN: ${{ secrets.gh-readaccess-pat }}'
                    new_content = content.replace(env_pattern, replacement, 1)
                else:
                    # Create env section after jobs
                    jobs_pattern = r'(jobs:\s+\w+:)'
                    replacement = r'\1\n    env:\n      GITHUB_TOKEN: ${{ secrets.gh-readaccess-pat }}'
                    new_content = content.replace(jobs_pattern, replacement, 1)
                
                if new_content != content:
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                    logger.info(f"✅ Updated workflow: {filename}")
                    update_count += 1
        
        if update_count > 0:
            logger.info(f"Updated {update_count} workflow files")
        else:
            logger.info("No workflow updates needed")
            
    except Exception as e:
        logger.error(f"Error updating workflows: {e}")
    
    return update_count


def get_repo_url(org: str, repo_name: str) -> str:
    """
    Get the full GitHub repository URL.
    
    Args:
        org: GitHub organization name
        repo_name: Repository name
        
    Returns:
        Full repository URL
    """
    return f"https://github.com/{org}/{repo_name}"


def check_pr_exists(repo_path: str, branch_name: str, dry_run: bool = False) -> bool:
    """
    Check if a pull request already exists for the given branch.
    
    Args:
        repo_path: Path to the repository
        branch_name: Branch name to check
        dry_run: If True, simulate the operation
        
    Returns:
        True if PR exists, False otherwise
    """
    if dry_run:
        return False
    
    try:
        cmd = ["gh", "pr", "list", "--head", branch_name, "--json", "number"]
        result = utils.run_command(cmd, cwd=repo_path, dry_run=dry_run)
        
        if result and result.returncode == 0:
            import json
            prs = json.loads(result.stdout)
            return len(prs) > 0
            
    except Exception as e:
        logger.warning(f"Error checking for existing PR: {e}")
    
    return False


def list_branches(repo_path: str) -> List[str]:
    """
    List all branches in the repository.
    
    Args:
        repo_path: Path to the repository
        
    Returns:
        List of branch names
    """
    try:
        cmd = ["git", "branch", "-a"]
        result = utils.run_command(cmd, cwd=repo_path, dry_run=False)
        
        if result and result.returncode == 0:
            branches = []
            for line in result.stdout.splitlines():
                branch = line.strip().lstrip('* ').strip()
                if branch:
                    branches.append(branch)
            return branches
            
    except Exception as e:
        logger.error(f"Error listing branches: {e}")
    
    return []
