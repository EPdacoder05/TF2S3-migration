# Usage Guide

Comprehensive guide for using the TF2S3 Migration Tool to migrate Terraform state backends from HCP Terraform Cloud to AWS S3/DynamoDB.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Initial Setup](#initial-setup)
- [Basic Workflows](#basic-workflows)
- [Advanced Usage](#advanced-usage)
- [Common Scenarios](#common-scenarios)
- [Troubleshooting](#troubleshooting)

## Prerequisites

### Required Tools

1. **Python 3.8+**
   ```bash
   python --version  # Should be 3.8 or higher
   ```

2. **AWS CLI** (configured and authenticated)
   ```bash
   aws --version
   aws configure --profile default
   aws sts get-caller-identity --profile default
   ```

3. **Terraform CLI**
   ```bash
   terraform --version
   ```

4. **GitHub CLI** (authenticated)
   ```bash
   gh --version
   gh auth login
   gh auth status
   ```

5. **Git**
   ```bash
   git --version
   ```

### Required Permissions

- **AWS**: S3 read/write access to your tfstate bucket
- **GitHub**: Write access to repositories being migrated
- **Terraform Cloud**: Read access to workspaces (via TF_TOKEN)

### Platform Scripts Repository

You need a `platform-scripts` repository containing the `copy_state.sh` script that handles Terraform Cloud to S3 state copying.

## Initial Setup

### 1. Clone the Migration Tool

```bash
git clone https://github.com/EPdacoder05/TF2S3-migration.git
cd TF2S3-migration
```

### 2. Configure for Your Organization

Choose one of three methods:

#### Method A: Edit config.py (Recommended for teams)

```bash
nano migrationlib/config.py
```

Update these values:
```python
DEFAULT_ORGANIZATION = "your-org"
DEFAULT_BUCKET_NAME = "your-org-tfstate-bucket"
DEFAULT_REGION = "us-east-1"
DEFAULT_AWS_PROFILE = "default"
```

#### Method B: Use .env file

```bash
cp .env.example .env
nano .env
```

Set your values:
```
GITHUB_ORG=your-org
AWS_PROFILE=default
AWS_REGION=us-east-1
S3_BUCKET=your-org-tfstate-bucket
PLATFORM_SCRIPTS_PATH=C:\Users\your-username\repos\platform-scripts
```

#### Method C: Use CLI arguments (most flexible)

Pass all configuration via command line:
```bash
python S3_migration.py \
  --org your-org \
  --bucket your-org-tfstate-bucket \
  --region us-east-1 \
  --aws-profile default \
  --repos repo1,repo2
```

### 3. Set Up Platform Scripts Path

The tool needs to find your `platform-scripts` repository. Choose one option:

**Option 1: Environment Variable (Recommended)**
```bash
# Linux/Mac
export PLATFORM_SCRIPTS_PATH="/home/your-username/repos/platform-scripts"

# Windows Command Prompt
setx PLATFORM_SCRIPTS_PATH "C:\repos\platform-scripts"

# Windows PowerShell
$env:PLATFORM_SCRIPTS_PATH = "C:\repos\platform-scripts"
```

**Option 2: Standard Location**

Place platform-scripts in one of these auto-detected locations:
- Windows: `C:\repos\platform-scripts`
- Linux/Mac: `~/repos/platform-scripts` or `~/source/repos/platform-scripts`

**Option 3: CLI Argument**
```bash
python S3_migration.py --scripts-path /path/to/platform-scripts --repos my-repo
```

## Basic Workflows

### Single Repository Migration

Migrate one repository with dry-run first:

```bash
# 1. Preview changes (dry-run)
python S3_migration.py --repos my-terraform-repo --org your-org --dry-run

# 2. Review the output, then execute for real
python S3_migration.py --repos my-terraform-repo --org your-org
```

### Multiple Repositories (Sequential)

Migrate several repositories one at a time:

```bash
python S3_migration.py \
  --repos repo1,repo2,repo3 \
  --org your-org \
  --bucket your-org-tfstate-bucket
```

### Parallel Processing

Migrate multiple repositories concurrently:

```bash
# Migrate 5 repositories with batch size of 3 (3 at a time)
python S3_migration.py \
  --repos repo1,repo2,repo3,repo4,repo5 \
  --batch-size 3 \
  --org your-org
```

**Recommended batch sizes:**
- Small repos (< 100 resources): batch-size 5-10
- Medium repos (100-500 resources): batch-size 3-5
- Large repos (500+ resources): batch-size 1-2

### Fully Automated Migration

Skip all confirmations with auto-commit:

```bash
python S3_migration.py \
  --repos repo1,repo2,repo3 \
  --org your-org \
  --auto-commit \
  --batch-size 3
```

## Advanced Usage

### Custom Branch Name

Use a different branch name for migration:

```bash
python S3_migration.py \
  --repos my-repo \
  --org your-org \
  --branch feature/migrate-backend-to-s3
```

### Skip Version Validation

Skip module version checks (faster, but less safe):

```bash
python S3_migration.py \
  --repos my-repo \
  --org your-org \
  --skip-version-check
```

### Skip Environment Validation

Bypass pre-flight environment checks (not recommended):

```bash
python S3_migration.py \
  --repos my-repo \
  --org your-org \
  --skip-validation
```

### Custom Working Directory

Specify where repositories should be cloned:

```bash
python S3_migration.py \
  --repos my-repo \
  --org your-org \
  --work-dir /tmp/migration-work
```

### Verbose Logging

Enable detailed debug output:

```bash
python S3_migration.py \
  --repos my-repo \
  --org your-org \
  --verbose
```

## Common Scenarios

### Scenario 1: Testing the Tool (Dry Run)

Before migrating production repos, test with dry-run mode:

```bash
# Test on one repository
python S3_migration.py --repos test-repo --org your-org --dry-run

# Review the log output
cat migration_logs/migration_*.log
```

**What dry-run does:**
- ✅ Validates environment
- ✅ Checks repository access
- ✅ Shows what changes would be made
- ❌ Does NOT clone repositories
- ❌ Does NOT modify code
- ❌ Does NOT create PRs

### Scenario 2: Large-Scale Migration (100+ Repos)

For large migrations, use a systematic approach:

```bash
# 1. Create a list of repositories
cat > repos.txt << EOF
repo1
repo2
repo3
... (100+ repos)
EOF

# 2. Convert to comma-separated list
REPOS=$(cat repos.txt | tr '\n' ',' | sed 's/,$//')

# 3. Run migration in batches
python S3_migration.py \
  --repos "$REPOS" \
  --org your-org \
  --batch-size 5 \
  --auto-commit \
  --verbose
```

### Scenario 3: Partial Failure Recovery

If some repositories fail, re-run with only failed repos:

```bash
# 1. Check the summary in logs
cat migration_logs/migration_*.log | grep "Failed migrations"

# 2. Re-run with only failed repositories
python S3_migration.py \
  --repos failed-repo1,failed-repo2 \
  --org your-org \
  --verbose
```

### Scenario 4: Different AWS Profiles per Environment

Migrate different repos with different AWS profiles:

```bash
# Development repositories
python S3_migration.py \
  --repos dev-repo1,dev-repo2 \
  --org your-org \
  --aws-profile dev \
  --bucket your-org-dev-tfstate

# Production repositories
python S3_migration.py \
  --repos prod-repo1,prod-repo2 \
  --org your-org \
  --aws-profile prod \
  --bucket your-org-prod-tfstate
```

### Scenario 5: Multi-Region Migration

Migrate repos using different AWS regions:

```bash
# US East repositories
python S3_migration.py \
  --repos us-east-repo1,us-east-repo2 \
  --org your-org \
  --region us-east-1 \
  --bucket your-org-us-east-1-tfstate

# EU West repositories
python S3_migration.py \
  --repos eu-west-repo1,eu-west-repo2 \
  --org your-org \
  --region eu-west-1 \
  --bucket your-org-eu-west-1-tfstate
```

## Understanding the Migration Pipeline

Each repository goes through 12 steps:

### Step 1: Clone Repository
```
[1/12] Cloning repository...
✅ Successfully cloned your-org/my-repo
```

### Step 2: Create Branch
```
[2/12] Creating migration branch...
✅ Successfully created branch migrate-to-s3-backend
```

### Step 3: Validate Versions
```
[3/12] Validating module versions...
✅ All module versions validated successfully
```

### Step 4: Copy State
```
[4/12] Copying Terraform state from Cloud to S3...
✅ Successfully copied state to S3
```

### Step 5: Update Backend
```
[5/12] Updating backend configuration...
✅ Updated backend configuration in main.tf
```

### Step 6: Convert Modules
```
[6/12] Converting module sources to Git format...
Updated 5 module sources
```

### Step 7: Update Workflows
```
[7/12] Updating GitHub Actions workflows...
Updated 2 workflow files
```

### Step 8: Commit
```
[8/12] Committing changes...
✅ Successfully committed changes
```

### Step 9: Push
```
[9/12] Pushing migration branch...
✅ Successfully pushed branch migrate-to-s3-backend
```

### Step 10: Create PR
```
[10/12] Creating pull request...
✅ Successfully created pull request
PR URL: https://github.com/your-org/my-repo/pull/123
```

### Step 11: Verify
```
[11/12] Verifying state in S3...
✅ State file verified in S3: my-repo/terraform.tfstate
```

### Step 12: Complete
```
[12/12] Migration complete!
✅ Successfully migrated your-org/my-repo
```

## Troubleshooting

### Issue: "Platform scripts directory not found"

**Solution:**
```bash
# Set the path explicitly
export PLATFORM_SCRIPTS_PATH="/path/to/platform-scripts"

# Or use CLI argument
python S3_migration.py --scripts-path /path/to/platform-scripts --repos my-repo
```

### Issue: "AWS credentials not configured"

**Solution:**
```bash
# Configure AWS CLI
aws configure --profile default

# Test authentication
aws sts get-caller-identity --profile default
```

### Issue: "GitHub CLI not authenticated"

**Solution:**
```bash
# Login to GitHub
gh auth login

# Verify authentication
gh auth status
```

### Issue: "Failed to clone repository"

**Possible causes:**
1. Repository doesn't exist
2. No read access
3. Network issues

**Solution:**
```bash
# Test repository access manually
gh repo view your-org/repo-name

# Clone manually to test
gh repo clone your-org/repo-name
```

### Issue: "Failed to copy state to S3"

**Possible causes:**
1. Terraform Cloud token not configured
2. AWS credentials insufficient
3. S3 bucket doesn't exist

**Solution:**
```bash
# Check Terraform Cloud token
echo $TF_TOKEN

# Test S3 bucket access
aws s3 ls s3://your-org-tfstate-bucket/ --profile default

# Verify S3 bucket exists
aws s3 mb s3://your-org-tfstate-bucket --profile default --region us-east-1
```

### Issue: "Module version validation failed"

**Solution:**
```bash
# Skip version validation (if acceptable)
python S3_migration.py --repos my-repo --skip-version-check

# Or update modules to required versions first
```

### Issue: Multiple repos failed with same error

**Solution:**
```bash
# Enable verbose logging
python S3_migration.py --repos failed-repos --verbose

# Check detailed logs
tail -f migration_logs/migration_*.log
```

## Best Practices

### 1. Always Start with Dry Run

```bash
python S3_migration.py --repos test-repo --dry-run
```

### 2. Test on Non-Critical Repos First

Validate the process on test/dev repositories before production.

### 3. Use Appropriate Batch Sizes

Don't overwhelm your system or GitHub rate limits:
- Start with `--batch-size 1`
- Gradually increase to 3-5 for smaller repos
- Monitor system resources

### 4. Review Logs

```bash
# Check logs after each run
tail -n 100 migration_logs/migration_*.log
```

### 5. Verify State After Migration

For each migrated repo:
```bash
cd migration_work/repo-name
terraform init -reconfigure
terraform plan  # Should show no changes
```

### 6. Keep Backups

The tool creates logs, but you may want additional backups:
```bash
# Backup Terraform Cloud workspace before migration
terraform state pull > backup-$(date +%Y%m%d).tfstate
```

## Next Steps

After running migrations:

1. **Review Pull Requests** - Each repo will have a PR created
2. **Test Changes** - Run `terraform plan` in each repo
3. **Merge PRs** - Once validated, merge the pull requests
4. **Update Local Environments** - Team members run `terraform init -reconfigure`
5. **Archive TFC Workspaces** - Clean up old Terraform Cloud workspaces

See [MIGRATION_GUIDE.md](docs/MIGRATION_GUIDE.md) for detailed post-migration steps.
