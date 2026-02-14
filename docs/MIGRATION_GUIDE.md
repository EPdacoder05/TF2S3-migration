# Terraform Cloud to S3 Backend Migration Guide

Complete step-by-step guide for migrating Terraform backends from HCP Terraform Cloud to AWS S3/DynamoDB.

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Pre-Migration Steps](#pre-migration-steps)
4. [Migration Steps](#migration-steps)
5. [Post-Migration Steps](#post-migration-steps)
6. [Troubleshooting](#troubleshooting)
7. [Rollback Procedures](#rollback-procedures)

## Overview

This guide walks through the complete migration process for moving Terraform state from HCP Terraform Cloud to AWS S3 with DynamoDB state locking.

**Migration Strategy:**
- Automated via TF2S3 Migration Tool
- Zero-downtime migration
- State verification at each step
- Rollback capability maintained

**Timeline:**
- Single repository: 5-10 minutes
- 100 repositories (parallel): 2-4 hours
- 1,000+ repositories (batched): 1-2 days

## Prerequisites

### Tools Required

- [x] Python 3.8+
- [x] AWS CLI (configured)
- [x] Terraform CLI
- [x] GitHub CLI (`gh`)
- [x] Git

### Access Required

- [x] GitHub: Write access to repositories
- [x] AWS: S3 and DynamoDB permissions
- [x] Terraform Cloud: Read access to workspaces
- [x] Platform Scripts: Access to `copy_state.sh` script

### Infrastructure Required

- [x] S3 bucket for state storage (encryption enabled, versioning enabled)
- [x] DynamoDB table for state locking
- [x] IAM permissions configured

## Pre-Migration Steps

### Step 1: Create S3 Bucket

```bash
# Create bucket
aws s3 mb s3://your-org-tfstate-bucket --region us-east-1

# Enable versioning (critical for state recovery)
aws s3api put-bucket-versioning \
  --bucket your-org-tfstate-bucket \
  --versioning-configuration Status=Enabled

# Enable encryption
aws s3api put-bucket-encryption \
  --bucket your-org-tfstate-bucket \
  --server-side-encryption-configuration '{
    "Rules": [{
      "ApplyServerSideEncryptionByDefault": {
        "SSEAlgorithm": "AES256"
      }
    }]
  }'

# Block public access
aws s3api put-public-access-block \
  --bucket your-org-tfstate-bucket \
  --public-access-block-configuration \
    BlockPublicAcls=true,\
    IgnorePublicAcls=true,\
    BlockPublicPolicy=true,\
    RestrictPublicBuckets=true
```

### Step 2: Create DynamoDB Lock Table

```bash
aws dynamodb create-table \
  --table-name terraform-state-lock \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region us-east-1

# Enable point-in-time recovery
aws dynamodb update-continuous-backups \
  --table-name terraform-state-lock \
  --point-in-time-recovery-specification PointInTimeRecoveryEnabled=true
```

### Step 3: Configure IAM Permissions

Create IAM policy for migration:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::your-org-tfstate-bucket",
        "arn:aws:s3:::your-org-tfstate-bucket/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:PutItem",
        "dynamodb:GetItem",
        "dynamodb:DeleteItem",
        "dynamodb:DescribeTable"
      ],
      "Resource": [
        "arn:aws:dynamodb:*:*:table/terraform-state-lock"
      ]
    }
  ]
}
```

### Step 4: Update Project Factory Module Versions

If your repositories use project factory modules, ensure they meet minimum version requirements:

```bash
# Example: Update to version 15.1.0+
# In your Terraform code:
module "github_project" {
  source = "git::https://github.com/your-org/terraform-github-project-factory?ref=v15.1.0"
  # ... config
}
```

**Minimum Versions** (customize for your org):
- GitHub Project Factory: >= 15.1.0
- AWS Project Factory: >= 5.5.2

### Step 5: Prepare Repository List

Create a list of repositories to migrate:

```bash
# Option 1: Manual list
cat > repos_to_migrate.txt << EOF
infrastructure-core
application-backend
application-frontend
networking-configs
EOF

# Option 2: Query GitHub API for all repos with Terraform
gh api -X GET /orgs/your-org/repos --paginate \
  | jq -r '.[] | select(.name | contains("terraform")) | .name' \
  > repos_to_migrate.txt

# Option 3: Filter by topic
gh api -X GET '/search/repositories?q=org:your-org+topic:terraform' \
  | jq -r '.items[].name' \
  > repos_to_migrate.txt
```

## Migration Steps

### Step 1: Install Migration Tool

```bash
git clone https://github.com/EPdacoder05/TF2S3-migration.git
cd TF2S3-migration
```

### Step 2: Configure Tool

```bash
# Copy environment template
cp .env.example .env

# Edit configuration
nano .env

# Set values:
GITHUB_ORG=your-org
S3_BUCKET=your-org-tfstate-bucket
AWS_PROFILE=default
AWS_REGION=us-east-1
PLATFORM_SCRIPTS_PATH=/path/to/platform-scripts
```

### Step 3: Test with Dry Run

Always test with a dry run first:

```bash
python S3_migration.py \
  --repos test-repo \
  --org your-org \
  --bucket your-org-tfstate-bucket \
  --dry-run
```

Review the output to ensure configuration is correct.

### Step 4: Migrate a Test Repository

Migrate a non-critical repository first:

```bash
python S3_migration.py \
  --repos test-infrastructure \
  --org your-org \
  --bucket your-org-tfstate-bucket \
  --region us-east-1 \
  --aws-profile default
```

**What this does:**
1. Clones repository
2. Creates migration branch
3. Copies state from TFC to S3
4. Updates backend configuration (cloud → s3)
5. Updates module sources (TFC registry → Git)
6. Updates GitHub Actions workflows
7. Commits and pushes changes
8. Creates pull request
9. Verifies state in S3

### Step 5: Verify Test Migration

```bash
# Clone the migrated repository
gh repo clone your-org/test-infrastructure
cd test-infrastructure

# Checkout migration branch
git checkout migrate-to-s3-backend

# Reinitialize Terraform
terraform init -reconfigure

# Verify state (should show no changes)
terraform plan

# Expected output:
# No changes. Your infrastructure matches the configuration.
```

### Step 6: Batch Migrate Repositories

After successful test migration, proceed with production repositories:

```bash
# Convert repo list to comma-separated
REPOS=$(cat repos_to_migrate.txt | tr '\n' ',' | sed 's/,$//')

# Migrate with parallel processing
python S3_migration.py \
  --repos "$REPOS" \
  --org your-org \
  --bucket your-org-tfstate-bucket \
  --batch-size 5 \
  --auto-commit \
  --verbose
```

**Batch Size Recommendations:**
- Small repositories (< 100 resources): 5-10
- Medium repositories (100-500 resources): 3-5
- Large repositories (> 500 resources): 1-2

### Step 7: Monitor Progress

```bash
# Watch logs in real-time
tail -f migration_logs/migration_*.log

# Check summary
cat migration_logs/migration_*.log | grep -A 20 "MIGRATION SUMMARY"
```

## Post-Migration Steps

### Step 1: Review Pull Requests

Each migrated repository will have a PR created. Review and merge them:

```bash
# List all migration PRs
gh pr list --search "Migrate Terraform backend" --json number,title,url

# Review a specific PR
gh pr view 123 --repo your-org/infrastructure-core

# If tests pass and changes look good, merge
gh pr merge 123 --repo your-org/infrastructure-core --merge
```

### Step 2: Update Team Documentation

Notify team members to update their local environments:

**Team Communication Template:**

```markdown
## Terraform Backend Migration Complete

We've migrated our Terraform backends from Terraform Cloud to AWS S3.

### Action Required:

For each repository you work with, run:

```bash
cd your-terraform-repo
git pull origin main
terraform init -reconfigure
```

### Changes:
- ✅ State now stored in S3 bucket: `your-org-tfstate-bucket`
- ✅ State locking via DynamoDB table: `terraform-state-lock`
- ✅ Module sources updated to use Git references
- ✅ GitHub Actions workflows updated

### Verify:
```bash
terraform plan  # Should show no changes
```

Questions? See #infrastructure-team or read the migration guide.
```

### Step 3: Update CI/CD Pipelines

If you have CI/CD pipelines outside GitHub Actions:

```yaml
# Example: Update Jenkins/GitLab/CircleCI to use AWS credentials
environment:
  AWS_PROFILE: default
  AWS_REGION: us-east-1

script:
  - terraform init -reconfigure
  - terraform plan
  - terraform apply -auto-approve
```

### Step 4: Archive Terraform Cloud Workspaces

After confirming migrations are successful, archive old TFC workspaces:

```bash
# List workspaces
terraform workspace list

# For each workspace in Terraform Cloud UI:
# 1. Go to workspace settings
# 2. Click "Archive Workspace"
# 3. Confirm archival

# Or via API:
curl \
  --header "Authorization: Bearer $TF_TOKEN" \
  --header "Content-Type: application/vnd.api+json" \
  --request PATCH \
  --data '{"data": {"type": "workspaces", "attributes": {"archived": true}}}' \
  https://app.terraform.io/api/v2/organizations/your-org/workspaces/workspace-name
```

### Step 5: Update Output Sharing (Optional)

If you share outputs between Terraform projects, update to use S3 objects:

**Before (Terraform Cloud):**
```hcl
data "terraform_remote_state" "networking" {
  backend = "remote"
  config = {
    organization = "your-org"
    workspaces = {
      name = "networking-prod"
    }
  }
}
```

**After (S3):**
```hcl
data "terraform_remote_state" "networking" {
  backend = "s3"
  config = {
    bucket = "your-org-tfstate-bucket"
    key    = "networking-prod/terraform.tfstate"
    region = "us-east-1"
  }
}
```

**Alternative (S3 Objects):**
```hcl
# In source project, export outputs to S3:
resource "aws_s3_object" "outputs" {
  bucket  = "your-org-shared-outputs"
  key     = "networking-prod/outputs.json"
  content = jsonencode({
    vpc_id     = aws_vpc.main.id
    subnet_ids = aws_subnet.private[*].id
  })
}

# In consuming project:
data "aws_s3_object" "networking_outputs" {
  bucket = "your-org-shared-outputs"
  key    = "networking-prod/outputs.json"
}

locals {
  networking = jsondecode(data.aws_s3_object.networking_outputs.body)
  vpc_id     = local.networking.vpc_id
}
```

## Troubleshooting

### Issue: State Copy Failed

**Symptoms:**
```
[4/12] Copying Terraform state from Cloud to S3...
❌ Failed to copy state to S3
```

**Diagnosis:**
```bash
# Check Terraform Cloud token
echo $TF_TOKEN

# Test TFC access
terraform login

# Check AWS access
aws s3 ls s3://your-org-tfstate-bucket/ --profile default

# Check platform scripts
ls -la /path/to/platform-scripts/copy_state.sh
```

**Solution:**
1. Ensure `TF_TOKEN` environment variable is set
2. Verify AWS credentials: `aws sts get-caller-identity`
3. Verify S3 bucket exists and is accessible
4. Check `copy_state.sh` script has execute permissions

### Issue: Module Version Validation Failed

**Symptoms:**
```
[3/12] Validating module versions...
⚠️  Module 'github_factory' version 14.5.0 is below minimum required 15.1.0
```

**Solution:**
```bash
# Skip version check (if acceptable)
python S3_migration.py --skip-version-check --repos my-repo

# Or update module versions first
cd infrastructure-repo
# Edit .tf files to update module versions
git commit -m "Update module versions"
git push
```

### Issue: PR Creation Failed

**Symptoms:**
```
[10/12] Creating pull request...
❌ Failed to create pull request
```

**Diagnosis:**
```bash
# Check GitHub CLI authentication
gh auth status

# Test repository access
gh repo view your-org/repo-name

# Check for existing PR
gh pr list --head migrate-to-s3-backend --repo your-org/repo-name
```

**Solution:**
1. Re-authenticate: `gh auth login`
2. Verify repository write access
3. If PR already exists, close it first or use different branch name

### Issue: Terraform Plan Shows Changes After Migration

**Symptoms:**
```bash
terraform plan
# Shows unexpected resource changes
```

**Diagnosis:**
This usually indicates state drift or module version differences.

**Solution:**
```bash
# 1. Check state file exists in S3
aws s3 ls s3://your-org-tfstate-bucket/repo-name/terraform.tfstate

# 2. Pull state and inspect
terraform state pull > current-state.json
cat current-state.json | jq '.resources | length'

# 3. Compare with Terraform Cloud state
# (if you have a backup)
diff current-state.json tfc-state-backup.json

# 4. If state is correct but plan shows changes, may need to:
terraform apply  # Apply the drift
# Or
terraform refresh  # Update state to match reality
```

## Rollback Procedures

### Scenario 1: Rollback Before Merging PR

If migration was unsuccessful and PR not yet merged:

```bash
# 1. Close the pull request
gh pr close [PR-NUMBER] --repo your-org/repo-name --delete-branch

# 2. Continue using Terraform Cloud backend
# (no changes required, original backend config still in main branch)
```

### Scenario 2: Rollback After Merging PR

If migration was merged but needs to be reverted:

```bash
# 1. Clone repository
gh repo clone your-org/repo-name
cd repo-name

# 2. Revert the migration commit
git revert [COMMIT-SHA]
git push origin main

# 3. Reconfigure Terraform for Cloud backend
terraform init -reconfigure

# 4. Optionally, copy state back to TFC
terraform state pull > backup.tfstate
# Reconfigure terraform block to use cloud backend
terraform init
terraform state push backup.tfstate
```

### Scenario 3: Emergency Rollback (Multiple Repos)

If many repositories need to be rolled back:

```bash
# Create rollback script
cat > rollback.sh << 'EOF'
#!/bin/bash
for repo in $(cat failed_repos.txt); do
  echo "Rolling back $repo..."
  gh pr close --repo your-org/$repo --delete-branch migrate-to-s3-backend
done
EOF

chmod +x rollback.sh
./rollback.sh
```

## Known Errors and Solutions

### Error: "LockID already exists"

**Cause:** Previous Terraform operation didn't release lock

**Solution:**
```bash
# Force unlock (use with caution)
terraform force-unlock [LOCK-ID]

# Or delete lock from DynamoDB
aws dynamodb delete-item \
  --table-name terraform-state-lock \
  --key '{"LockID": {"S": "your-org-tfstate-bucket/repo-name/terraform.tfstate"}}'
```

### Error: "Access Denied" on S3

**Cause:** Insufficient IAM permissions

**Solution:**
```bash
# Verify current IAM identity
aws sts get-caller-identity

# Test S3 access
aws s3 ls s3://your-org-tfstate-bucket/ --profile default

# Update IAM policy (see Pre-Migration Steps)
```

### Error: "Module not found" after migration

**Cause:** Module source URL incorrect or no access to private repo

**Solution:**
```bash
# Verify GitHub token has repo access
gh auth status

# Test module repository access
gh repo view your-org/terraform-module-name

# Update GitHub Actions secret if needed
gh secret set GH_READACCESS_PAT --repo your-org/repo-name
```

## Best Practices

1. **Always start with dry-run**
2. **Migrate test repos first**
3. **Use batch processing for scale**
4. **Monitor logs during migration**
5. **Verify state after migration**
6. **Keep backups of state files**
7. **Document any custom changes**
8. **Communicate with team**

## Success Criteria

Migration is successful when:

- [x] State file exists in S3
- [x] `terraform init` succeeds
- [x] `terraform plan` shows no changes
- [x] Team members can run Terraform locally
- [x] CI/CD pipelines work with new backend
- [x] State locking works (test with concurrent runs)
- [x] Module sources resolve correctly

## Additional Resources

- [Terraform S3 Backend Documentation](https://www.terraform.io/docs/language/settings/backends/s3.html)
- [AWS S3 Best Practices](https://docs.aws.amazon.com/AmazonS3/latest/userguide/best-practices.html)
- [Terraform State Management](https://www.terraform.io/docs/language/state/index.html)
- [Cost Savings Analysis](COST_SAVINGS.md)

---

**Questions or Issues?**

- Review tool documentation: [README.md](../README.md), [USAGE.md](../USAGE.md)
- Check troubleshooting section above
- Contact infrastructure team
