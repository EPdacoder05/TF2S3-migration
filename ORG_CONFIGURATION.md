# Organization Configuration Guide

How to configure the TF2S3 Migration Tool for your specific organization.

## Overview

This tool is designed to be completely organization-agnostic. All organization-specific values are configurable and must be customized for your environment.

## Quick Start

### Option 1: Run Setup Script (Recommended)

**Linux/Mac:**
```bash
chmod +x setup_organization.sh
./setup_organization.sh
```

**Windows:**
```powershell
.\setup_organization.ps1
```

The setup script will prompt you for:
- GitHub organization name
- S3 bucket name
- AWS region
- AWS profile
- Platform scripts path

It will then create a `.env` file with your configuration.

### Option 2: Manual Configuration

#### Step 1: Edit `migrationlib/config.py`

```python
# Organization Configuration
DEFAULT_ORGANIZATION = "acme-corp"  # Your GitHub org
DEFAULT_BUCKET_NAME = "acme-corp-tfstate-bucket"  # Your S3 bucket
DEFAULT_REGION = "us-east-1"  # Your AWS region
DEFAULT_AWS_PROFILE = "default"  # Your AWS profile
```

#### Step 2: Update Module Version Requirements

If your organization has specific Terraform module version requirements:

```python
REQUIRED_VERSIONS: Dict[str, Dict[str, Optional[str]]] = {
    "acme-github-project-factory": {"min": "15.1.0", "max": None},
    "acme-aws-project-factory": {"min": "5.5.2", "max": None},
    "acme-networking-module": {"min": "2.0.0", "max": "3.0.0"},
}
```

#### Step 3: Configure Platform Scripts Path

Add your organization's platform-scripts path to the search list:

```python
PLATFORM_SCRIPTS_PATHS = [
    os.environ.get("PLATFORM_SCRIPTS_PATH", ""),
    "/path/to/your/org/platform-scripts",  # Add your path here
    "C:\\your-org\\platform-scripts",       # Windows path
    # ... existing paths
]
```

### Option 3: Environment Variables

Create `.env` file from template:

```bash
cp .env.example .env
nano .env
```

Configure your values:

```env
# GitHub Configuration
GITHUB_ORG=acme-corp
GITHUB_TOKEN=ghp_your_token_here

# AWS Configuration
AWS_PROFILE=acme-prod
AWS_REGION=us-east-1
S3_BUCKET=acme-corp-tfstate-bucket

# Platform Scripts
PLATFORM_SCRIPTS_PATH=/opt/acme-platform-scripts

# Migration Settings
DRY_RUN=false
BATCH_SIZE=3
AUTO_COMMIT=false
```

Then load the environment:

```bash
# Linux/Mac
source .env

# Or export individual variables
export GITHUB_ORG=acme-corp
export S3_BUCKET=acme-corp-tfstate-bucket
```

## Detailed Configuration Options

### 1. GitHub Organization

**What it is:** Your GitHub organization name (not user account).

**Where used:**
- Repository cloning: `gh repo clone ${ORG}/${REPO}`
- PR creation: PRs opened in `${ORG}/${REPO}`
- Module sources: Converted to `git::https://github.com/${ORG}/...`

**How to configure:**

```python
# config.py
DEFAULT_ORGANIZATION = "acme-corp"
```

```bash
# CLI
python S3_migration.py --org acme-corp --repos my-repo
```

```bash
# Environment
export GITHUB_ORG=acme-corp
```

### 2. S3 Bucket

**What it is:** S3 bucket where Terraform state files will be stored.

**Requirements:**
- Bucket must already exist
- Versioning should be enabled
- Encryption should be enabled
- You must have read/write access

**Naming convention:** `${ORG}-tfstate-bucket` or `${ORG}-${ENV}-tfstate`

**How to configure:**

```python
# config.py
DEFAULT_BUCKET_NAME = "acme-corp-prod-tfstate"
```

```bash
# CLI
python S3_migration.py --bucket acme-corp-prod-tfstate --repos my-repo
```

```bash
# Environment
export S3_BUCKET=acme-corp-prod-tfstate
```

**Create bucket if needed:**

```bash
# Create bucket
aws s3 mb s3://acme-corp-tfstate-bucket --region us-east-1

# Enable versioning
aws s3api put-bucket-versioning \
  --bucket acme-corp-tfstate-bucket \
  --versioning-configuration Status=Enabled

# Enable encryption
aws s3api put-bucket-encryption \
  --bucket acme-corp-tfstate-bucket \
  --server-side-encryption-configuration '{
    "Rules": [{
      "ApplyServerSideEncryptionByDefault": {
        "SSEAlgorithm": "AES256"
      }
    }]
  }'
```

### 3. AWS Region

**What it is:** AWS region where S3 bucket is located.

**How to configure:**

```python
# config.py
DEFAULT_REGION = "us-west-2"
```

```bash
# CLI
python S3_migration.py --region us-west-2 --repos my-repo
```

```bash
# Environment
export AWS_REGION=us-west-2
```

### 4. AWS Profile

**What it is:** AWS CLI profile name with credentials for S3 access.

**How to configure:**

```python
# config.py
DEFAULT_AWS_PROFILE = "acme-prod"
```

```bash
# CLI
python S3_migration.py --aws-profile acme-prod --repos my-repo
```

```bash
# Environment
export AWS_PROFILE=acme-prod
```

**Create profile if needed:**

```bash
aws configure --profile acme-prod
# Enter: Access Key, Secret Key, Region, Output format
```

### 5. Platform Scripts Path

**What it is:** Path to your organization's platform-scripts repository containing `copy_state.sh`.

**How to configure:**

```python
# config.py - Add to PLATFORM_SCRIPTS_PATHS list
PLATFORM_SCRIPTS_PATHS = [
    os.environ.get("PLATFORM_SCRIPTS_PATH", ""),
    "/opt/acme-scripts",  # Your path here
    "C:\\acme\\scripts",  # Windows path
]
```

```bash
# CLI
python S3_migration.py --scripts-path /opt/acme-scripts --repos my-repo
```

```bash
# Environment
export PLATFORM_SCRIPTS_PATH=/opt/acme-scripts
```

### 6. Module Version Requirements

**What it is:** Minimum/maximum versions for your organization's Terraform modules.

**How to configure:**

```python
# config.py
REQUIRED_VERSIONS: Dict[str, Dict[str, Optional[str]]] = {
    # Format: "module-name": {"min": "X.Y.Z", "max": "X.Y.Z" or None}
    "acme-github-factory": {"min": "15.1.0", "max": None},
    "acme-aws-factory": {"min": "5.5.2", "max": "6.0.0"},
    "acme-networking": {"min": "2.0.0", "max": None},
}
```

**Skip validation:**

```bash
python S3_migration.py --skip-version-check --repos my-repo
```

### 7. DynamoDB Table

**What it is:** DynamoDB table for Terraform state locking.

**Default:** `terraform-state-lock`

**How to configure:**

```python
# config.py
DYNAMODB_TABLE_NAME = "acme-terraform-locks"
```

**Create table if needed:**

```bash
aws dynamodb create-table \
  --table-name terraform-state-lock \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region us-east-1
```

### 8. Branch Name

**What it is:** Git branch name for migration PRs.

**Default:** `migrate-to-s3-backend`

**How to configure:**

```python
# config.py
DEFAULT_BRANCH_NAME = "feature/migrate-backend-to-s3"
```

```bash
# CLI
python S3_migration.py --branch feature/s3-migration --repos my-repo
```

## Multi-Environment Configuration

For organizations with multiple environments (dev, staging, prod):

### Approach 1: Separate Config Files

```bash
# Copy config for each environment
cp migrationlib/config.py migrationlib/config_prod.py
cp migrationlib/config.py migrationlib/config_dev.py

# Edit each config file
nano migrationlib/config_prod.py  # Set prod bucket, profile
nano migrationlib/config_dev.py   # Set dev bucket, profile

# Import appropriate config
# S3_migration.py
if args.env == "prod":
    from migrationlib import config_prod as config
else:
    from migrationlib import config_dev as config
```

### Approach 2: CLI Arguments

```bash
# Production
python S3_migration.py \
  --repos prod-app1,prod-app2 \
  --bucket acme-prod-tfstate \
  --aws-profile acme-prod \
  --region us-east-1

# Development
python S3_migration.py \
  --repos dev-app1,dev-app2 \
  --bucket acme-dev-tfstate \
  --aws-profile acme-dev \
  --region us-west-2
```

### Approach 3: Environment-Specific .env Files

```bash
# .env.prod
GITHUB_ORG=acme-corp
S3_BUCKET=acme-prod-tfstate
AWS_PROFILE=acme-prod
AWS_REGION=us-east-1

# .env.dev
GITHUB_ORG=acme-corp
S3_BUCKET=acme-dev-tfstate
AWS_PROFILE=acme-dev
AWS_REGION=us-west-2

# Load appropriate environment
source .env.prod  # For production
source .env.dev   # For development
```

## Multi-Region Configuration

For organizations with resources in multiple AWS regions:

```bash
# US East
python S3_migration.py \
  --repos us-east-repos \
  --bucket acme-us-east-1-tfstate \
  --region us-east-1

# EU West
python S3_migration.py \
  --repos eu-west-repos \
  --bucket acme-eu-west-1-tfstate \
  --region eu-west-1

# Asia Pacific
python S3_migration.py \
  --repos ap-southeast-repos \
  --bucket acme-ap-southeast-1-tfstate \
  --region ap-southeast-1
```

## Team Configuration Best Practices

### 1. Centralized Config Repository

Maintain organization-specific configuration in a separate repository:

```bash
# acme-corp/tf-migration-config
config/
├── config.py           # Base configuration
├── prod.env            # Production environment
├── dev.env             # Development environment
└── repos/
    ├── prod_repos.txt  # List of production repos
    └── dev_repos.txt   # List of development repos
```

### 2. CI/CD Integration

Automate migrations via CI/CD:

```yaml
# .github/workflows/migrate-repos.yml
name: Terraform Migration
on:
  workflow_dispatch:
    inputs:
      environment:
        description: 'Environment to migrate'
        required: true
        type: choice
        options:
          - dev
          - staging
          - prod

jobs:
  migrate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Configure AWS
        uses: aws-actions/configure-aws-credentials@v2
        with:
          role-to-assume: ${{ secrets.AWS_ROLE_ARN }}
          aws-region: us-east-1
      
      - name: Run Migration
        env:
          GITHUB_ORG: acme-corp
          S3_BUCKET: acme-${{ inputs.environment }}-tfstate
        run: |
          python S3_migration.py \
            --repos $(cat repos/${{ inputs.environment }}.txt | tr '\n' ',') \
            --org $GITHUB_ORG \
            --bucket $S3_BUCKET \
            --batch-size 5 \
            --auto-commit
```

### 3. Documentation

Document your organization's configuration:

```markdown
# ACME Corp Terraform Migration Configuration

## Environments

| Environment | S3 Bucket | Region | AWS Profile |
|-------------|-----------|--------|-------------|
| Production  | acme-prod-tfstate | us-east-1 | acme-prod |
| Staging     | acme-staging-tfstate | us-east-1 | acme-staging |
| Development | acme-dev-tfstate | us-west-2 | acme-dev |

## Module Versions

- acme-github-factory: >= 15.1.0
- acme-aws-factory: >= 5.5.2, < 6.0.0

## Contact

- Team: infrastructure@acme-corp.com
- Slack: #infrastructure-team
```

## Validation Checklist

Before running migrations, validate your configuration:

```bash
# 1. Test AWS access
aws s3 ls s3://acme-corp-tfstate-bucket/ --profile acme-prod

# 2. Test GitHub access
gh repo view acme-corp/test-repo

# 3. Verify platform scripts
ls -la /opt/acme-scripts/copy_state.sh

# 4. Test Terraform Cloud access
export TF_TOKEN="your-token"
terraform login

# 5. Dry-run test
python S3_migration.py \
  --repos test-repo \
  --org acme-corp \
  --bucket acme-corp-tfstate-bucket \
  --dry-run
```

## Troubleshooting

### Configuration Not Found

**Issue:** "Platform scripts directory not found"

**Solution:** Check `PLATFORM_SCRIPTS_PATHS` in config.py or set environment variable:
```bash
export PLATFORM_SCRIPTS_PATH=/path/to/your/scripts
```

### Wrong Organization

**Issue:** Repositories not found

**Solution:** Verify organization name:
```bash
gh api /orgs/acme-corp  # Should return org details
```

### S3 Access Denied

**Issue:** "Failed to verify state in S3"

**Solution:** Check IAM permissions:
```bash
aws sts get-caller-identity --profile acme-prod
aws s3 ls s3://acme-corp-tfstate-bucket/ --profile acme-prod
```

## Support

For configuration assistance:
1. Review [USAGE.md](USAGE.md) for usage examples
2. Check [SECURITY_CONFIG.md](SECURITY_CONFIG.md) for security setup
3. See [README.md](README.md) for quick start

## Next Steps

After configuration:
1. Test with `--dry-run` on a single repository
2. Migrate a non-critical repository
3. Validate the migration (terraform init, plan)
4. Scale up to batch migrations
5. Document any organization-specific customizations
