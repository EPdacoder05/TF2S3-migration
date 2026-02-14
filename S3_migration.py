#!/usr/bin/env python3
"""
S3_migration.py - Terraform Cloud to S3 Backend Migration Tool

Production-ready CLI tool that orchestrates a 12-step migration pipeline
for migrating Terraform state backends from HCP Terraform Cloud to AWS S3/DynamoDB.

Usage:
    python S3_migration.py --repos repo1,repo2 --org your-org --bucket your-bucket

Author: EPdacoder05
License: MIT
"""

import argparse
import sys
import os
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import List, Dict, Optional, Any

# Add migrationlib to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from migrationlib import config, tf_ops, gh_ops, state_ops, utils, validation

logger = logging.getLogger(__name__)


def parse_arguments() -> argparse.Namespace:
    """
    Parse command line arguments.
    
    Returns:
        Parsed arguments namespace
    """
    parser = argparse.ArgumentParser(
        description="Terraform Cloud to S3 Backend Migration Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Migrate a single repository
  python S3_migration.py --repos my-repo --org your-org

  # Migrate multiple repositories with custom bucket
  python S3_migration.py --repos repo1,repo2,repo3 --org your-org --bucket my-tfstate-bucket

  # Dry run to preview changes
  python S3_migration.py --repos my-repo --org your-org --dry-run

  # Parallel processing with custom batch size
  python S3_migration.py --repos repo1,repo2,repo3 --batch-size 3

For more information, see README.md and USAGE.md
        """
    )
    
    # Required arguments
    parser.add_argument(
        '--repos',
        required=True,
        help='Comma-separated list of repository names to migrate'
    )
    
    parser.add_argument(
        '--org',
        default=config.DEFAULT_ORGANIZATION,
        help=f'GitHub organization name (default: {config.DEFAULT_ORGANIZATION})'
    )
    
    # AWS configuration
    parser.add_argument(
        '--bucket',
        default=config.DEFAULT_BUCKET_NAME,
        help=f'S3 bucket name for state storage (default: {config.DEFAULT_BUCKET_NAME})'
    )
    
    parser.add_argument(
        '--region',
        default=config.DEFAULT_REGION,
        help=f'AWS region (default: {config.DEFAULT_REGION})'
    )
    
    parser.add_argument(
        '--aws-profile',
        default=config.DEFAULT_AWS_PROFILE,
        help=f'AWS profile to use (default: {config.DEFAULT_AWS_PROFILE})'
    )
    
    # Platform scripts
    parser.add_argument(
        '--scripts-path',
        help='Path to platform-scripts directory (auto-detected if not provided)'
    )
    
    # Processing options
    parser.add_argument(
        '--batch-size',
        type=int,
        default=config.DEFAULT_BATCH_SIZE,
        help=f'Number of concurrent repository migrations (default: {config.DEFAULT_BATCH_SIZE})'
    )
    
    # Operational flags
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview changes without executing'
    )
    
    parser.add_argument(
        '--skip-validation',
        action='store_true',
        help='Skip environment validation checks'
    )
    
    parser.add_argument(
        '--skip-version-check',
        action='store_true',
        help='Skip module version validation'
    )
    
    parser.add_argument(
        '--auto-commit',
        action='store_true',
        help='Automatically commit and push changes without confirmation'
    )
    
    parser.add_argument(
        '--work-dir',
        default=os.path.join(os.getcwd(), 'migration_work'),
        help='Working directory for repository clones'
    )
    
    parser.add_argument(
        '--branch',
        default=config.DEFAULT_BRANCH_NAME,
        help=f'Branch name for migration (default: {config.DEFAULT_BRANCH_NAME})'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose debug logging'
    )
    
    return parser.parse_args()


def migrate_repository(
    repo_name: str,
    org: str,
    bucket: str,
    region: str,
    aws_profile: str,
    scripts_path: str,
    work_dir: str,
    branch_name: str,
    dry_run: bool,
    skip_version_check: bool,
    auto_commit: bool
) -> Dict[str, Any]:
    """
    Execute 12-step migration pipeline for a single repository.
    
    Steps:
    1. Clone repository
    2. Create migration branch
    3. Validate module versions (optional)
    4. Copy state from TFC to S3
    5. Update backend configuration
    6. Update module sources
    7. Update GitHub Actions workflows
    8. Commit changes
    9. Push branch
    10. Create pull request
    11. Verify state in S3
    12. Log completion
    
    Args:
        repo_name: Repository name
        org: GitHub organization
        bucket: S3 bucket name
        region: AWS region
        aws_profile: AWS profile
        scripts_path: Path to platform-scripts
        work_dir: Working directory
        branch_name: Migration branch name
        dry_run: Dry run mode
        skip_version_check: Skip version validation
        auto_commit: Auto-commit mode
        
    Returns:
        Dict with migration results
    """
    result = {
        'repo': repo_name,
        'success': False,
        'steps_completed': [],
        'errors': [],
        'warnings': []
    }
    
    logger.info(f"\n{'='*80}")
    logger.info(f"Starting migration for: {org}/{repo_name}")
    logger.info(f"{'='*80}\n")
    
    try:
        # Step 1: Clone repository
        logger.info("[1/12] Cloning repository...")
        repo_path = gh_ops.clone_repo(org, repo_name, work_dir, dry_run)
        if not repo_path and not dry_run:
            result['errors'].append("Failed to clone repository")
            return result
        result['steps_completed'].append("clone")
        
        # Step 2: Create migration branch
        logger.info("[2/12] Creating migration branch...")
        if not gh_ops.create_branch(repo_path, branch_name, dry_run):
            result['errors'].append("Failed to create branch")
            return result
        result['steps_completed'].append("branch")
        
        # Step 3: Validate module versions (optional)
        if not skip_version_check:
            logger.info("[3/12] Validating module versions...")
            version_errors = tf_ops.validate_module_versions(repo_path, config.REQUIRED_VERSIONS)
            if version_errors:
                result['warnings'].extend(version_errors)
                logger.warning(f"Found {len(version_errors)} version validation warnings")
        else:
            logger.info("[3/12] Skipping module version validation...")
        result['steps_completed'].append("validate")
        
        # Step 4: Copy state from TFC to S3
        logger.info("[4/12] Copying Terraform state from Cloud to S3...")
        if not state_ops.copy_state_to_s3(repo_path, scripts_path, aws_profile, dry_run):
            result['errors'].append("Failed to copy state to S3")
            return result
        result['steps_completed'].append("copy_state")
        
        # Step 5: Update backend configuration
        logger.info("[5/12] Updating backend configuration...")
        if not tf_ops.update_backend_config(repo_path, bucket, region, repo_name):
            result['errors'].append("Failed to update backend config")
            return result
        result['steps_completed'].append("backend")
        
        # Step 6: Update module sources
        logger.info("[6/12] Converting module sources to Git format...")
        module_count = tf_ops.update_module_sources(repo_path, org)
        logger.info(f"Updated {module_count} module sources")
        result['steps_completed'].append("modules")
        
        # Step 7: Update GitHub Actions workflows
        logger.info("[7/12] Updating GitHub Actions workflows...")
        workflow_count = gh_ops.update_workflow_secrets(repo_path, dry_run)
        logger.info(f"Updated {workflow_count} workflow files")
        result['steps_completed'].append("workflows")
        
        # Step 8: Commit changes
        logger.info("[8/12] Committing changes...")
        if not auto_commit and not dry_run:
            confirm = utils.confirm_action(f"Commit changes for {repo_name}?", default=True)
            if not confirm:
                result['warnings'].append("User skipped commit")
                logger.info("Skipping commit and remaining steps")
                return result
        
        if not gh_ops.commit_changes(repo_path, config.GIT_COMMIT_MESSAGE, dry_run):
            result['errors'].append("Failed to commit changes")
            return result
        result['steps_completed'].append("commit")
        
        # Step 9: Push branch
        logger.info("[9/12] Pushing migration branch...")
        if not gh_ops.push_changes(repo_path, branch_name, dry_run):
            result['errors'].append("Failed to push branch")
            return result
        result['steps_completed'].append("push")
        
        # Step 10: Create pull request
        logger.info("[10/12] Creating pull request...")
        
        # Check if PR already exists
        if not dry_run and gh_ops.check_pr_exists(repo_path, branch_name):
            logger.info("Pull request already exists, skipping creation")
            result['warnings'].append("PR already exists")
        else:
            if not gh_ops.create_pull_request(
                repo_path, org, repo_name, branch_name,
                config.PR_TITLE, config.PR_BODY_TEMPLATE, dry_run
            ):
                result['errors'].append("Failed to create pull request")
                return result
        result['steps_completed'].append("pr")
        
        # Step 11: Verify state in S3
        logger.info("[11/12] Verifying state in S3...")
        if not state_ops.verify_state_in_s3(bucket, repo_name, aws_profile, region, dry_run):
            result['warnings'].append("Could not verify state in S3")
        result['steps_completed'].append("verify")
        
        # Step 12: Log completion
        logger.info("[12/12] Migration complete!")
        result['steps_completed'].append("complete")
        result['success'] = True
        
        logger.info(f"\n✅ Successfully migrated {org}/{repo_name}")
        logger.info(f"Migration branch: {branch_name}")
        logger.info(f"PR: {gh_ops.get_repo_url(org, repo_name)}/pulls\n")
        
    except Exception as e:
        logger.error(f"Unexpected error during migration: {e}", exc_info=True)
        result['errors'].append(str(e))
    
    return result


def main():
    """Main entry point for the migration tool."""
    args = parse_arguments()
    
    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    utils.setup_logging(config.LOG_DIRECTORY)
    logger.setLevel(log_level)
    
    # Print banner
    logger.info("="*80)
    logger.info("  Terraform Cloud to S3 Backend Migration Tool  ")
    logger.info("  Version: 1.0.0")
    logger.info("="*80)
    logger.info("")
    
    # Display configuration
    logger.info("Configuration:")
    logger.info(f"  Organization: {args.org}")
    logger.info(f"  S3 Bucket: {args.bucket}")
    logger.info(f"  AWS Region: {args.region}")
    logger.info(f"  AWS Profile: {args.aws_profile}")
    logger.info(f"  Batch Size: {args.batch_size}")
    logger.info(f"  Dry Run: {args.dry_run}")
    logger.info("")
    
    # Parse repository list
    repo_list = utils.parse_list_argument(args.repos)
    if not repo_list:
        logger.error("No repositories specified")
        return 1
    
    logger.info(f"Repositories to migrate ({len(repo_list)}):")
    for repo in repo_list:
        logger.info(f"  - {repo}")
    logger.info("")
    
    # Validate repository names
    valid_repos = validation.validate_repo_list(repo_list)
    if len(valid_repos) < len(repo_list):
        logger.warning(f"Filtered out {len(repo_list) - len(valid_repos)} invalid repository names")
    
    if not valid_repos:
        logger.error("No valid repositories to migrate")
        return 1
    
    # Validate environment
    if not args.skip_validation:
        logger.info("Validating environment...")
        if not validation.validate_environment():
            logger.error("Environment validation failed")
            logger.info("Use --skip-validation to bypass (not recommended)")
            return 1
        logger.info("")
    
    # Find platform scripts
    scripts_path = args.scripts_path
    if not scripts_path:
        scripts_path = validation.find_platform_scripts()
        if not scripts_path:
            logger.error("Platform scripts not found")
            logger.info("Use --scripts-path to specify location")
            return 1
    elif not validation.validate_scripts_path(scripts_path):
        logger.error(f"Invalid platform scripts path: {scripts_path}")
        return 1
    
    logger.info(f"Using platform scripts: {scripts_path}")
    logger.info("")
    
    # Create working directory
    if not utils.ensure_directory(args.work_dir):
        logger.error(f"Failed to create working directory: {args.work_dir}")
        return 1
    
    # Confirm before starting
    if not args.dry_run and not args.auto_commit:
        logger.info(f"\nReady to migrate {len(valid_repos)} repositories")
        if not utils.confirm_action("Proceed with migration?", default=False):
            logger.info("Migration cancelled by user")
            return 0
        logger.info("")
    
    # Execute migrations
    start_time = datetime.now()
    results = []
    
    if args.batch_size == 1:
        # Sequential processing
        logger.info("Processing repositories sequentially...")
        for repo in valid_repos:
            result = migrate_repository(
                repo, args.org, args.bucket, args.region, args.aws_profile,
                scripts_path, args.work_dir, args.branch, args.dry_run,
                args.skip_version_check, args.auto_commit
            )
            results.append(result)
    else:
        # Parallel processing
        logger.info(f"Processing repositories in parallel (batch size: {args.batch_size})...")
        with ThreadPoolExecutor(max_workers=args.batch_size) as executor:
            futures = {
                executor.submit(
                    migrate_repository,
                    repo, args.org, args.bucket, args.region, args.aws_profile,
                    scripts_path, args.work_dir, args.branch, args.dry_run,
                    args.skip_version_check, args.auto_commit
                ): repo
                for repo in valid_repos
            }
            
            for future in as_completed(futures):
                repo = futures[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    logger.error(f"Unexpected error processing {repo}: {e}")
                    results.append({
                        'repo': repo,
                        'success': False,
                        'errors': [str(e)]
                    })
    
    # Print summary
    elapsed = (datetime.now() - start_time).total_seconds()
    logger.info("\n" + "="*80)
    logger.info("  MIGRATION SUMMARY")
    logger.info("="*80)
    
    successful = [r for r in results if r['success']]
    failed = [r for r in results if not r['success']]
    
    logger.info(f"\nTotal repositories: {len(results)}")
    logger.info(f"Successful: {len(successful)}")
    logger.info(f"Failed: {len(failed)}")
    logger.info(f"Duration: {utils.format_duration(elapsed)}")
    
    if successful:
        logger.info("\n✅ Successful migrations:")
        for r in successful:
            logger.info(f"  - {r['repo']}")
    
    if failed:
        logger.info("\n❌ Failed migrations:")
        for r in failed:
            logger.info(f"  - {r['repo']}")
            if r['errors']:
                for error in r['errors']:
                    logger.info(f"      Error: {error}")
    
    # Print rollback instructions if there were failures
    if failed and not args.dry_run:
        logger.info("\n" + "="*80)
        logger.info("  ROLLBACK INSTRUCTIONS")
        logger.info("="*80)
        logger.info("\nFor failed migrations, you may need to:")
        logger.info("1. Close the pull request")
        logger.info("2. Delete the migration branch: git push origin --delete " + args.branch)
        logger.info("3. Review logs in migration_logs/ directory")
        logger.info("4. Re-run migration after fixing issues")
    
    logger.info("\n" + "="*80)
    logger.info("")
    
    # Return appropriate exit code
    return 0 if len(failed) == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
