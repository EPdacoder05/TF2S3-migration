# TF2S3 Migration Tool

Universal Terraform Cloud to S3 Backend Migration Tool — automates state backend migration for 1,000+ repositories with parallel processing, dry-run mode, and comprehensive secret sanitization.

**Resume Highlight**: *Saved $126K annually by migrating 1,000+ repository Terraform backends from HCP Cloud to S3/DynamoDB, eliminating per-resource billing.*

## Overview

This tool automates the complete migration of Terraform state backends from HCP Terraform Cloud to AWS S3/DynamoDB. It handles everything from state copying to code updates to pull request creation, making it possible to migrate hundreds of repositories efficiently and safely.

### Key Features

- **12-Step Migration Pipeline**: Fully automated workflow from clone to PR creation
- **Parallel Processing**: Migrate multiple repositories concurrently with configurable batch sizes
- **Dry-Run Mode**: Preview all changes before executing
- **Secret Sanitization**: Automatically redact sensitive data from logs using regex patterns
- **Cross-Platform**: Works on Windows (PowerShell) and Linux/Mac (Bash)
- **Comprehensive Validation**: Pre-flight checks for environment, permissions, and configuration
- **Rollback Support**: Clear instructions for reverting changes if needed
- **Production Quality**: Type hints, docstrings, structured logging, and error handling throughout

## Quick Start

### Prerequisites

- Python 3.8+
- AWS CLI (authenticated)
- Terraform CLI
- GitHub CLI (`gh`, authenticated)
- Git

### Installation

```bash
# Clone the repository
git clone https://github.com/EPdacoder05/TF2S3-migration.git
cd TF2S3-migration

# Copy environment template
cp .env.example .env

# Edit configuration (or use CLI arguments)
nano .env
```

### Basic Usage

```bash
# Migrate a single repository
python S3_migration.py --repos my-repo --org your-org

# Migrate multiple repositories
python S3_migration.py --repos repo1,repo2,repo3 --org your-org --bucket your-tfstate-bucket

# Dry run to preview changes
python S3_migration.py --repos my-repo --org your-org --dry-run

# Parallel processing
python S3_migration.py --repos repo1,repo2,repo3 --batch-size 3
```

## Configuration

### Method 1: Update `migrationlib/config.py`

Edit the default values for your organization:

```python
DEFAULT_ORGANIZATION = "your-org"
DEFAULT_BUCKET_NAME = "your-org-tfstate-bucket"
DEFAULT_REGION = "us-east-1"
DEFAULT_AWS_PROFILE = "default"
```

### Method 2: Use CLI Arguments

All configuration can be provided via command-line arguments:

```bash
python S3_migration.py \
  --repos repo1,repo2 \
  --org your-org \
  --bucket your-org-tfstate-bucket \
  --region us-east-1 \
  --aws-profile default \
  --scripts-path /path/to/platform-scripts
```

### Method 3: Environment Variables

Set environment variables:

```bash
export PLATFORM_SCRIPTS_PATH="/path/to/platform-scripts"
export GITHUB_ORG="your-org"
export AWS_PROFILE="default"
```

## Team Setup Options

### Option 1: Environment Variable (Recommended)

```bash
# Linux/Mac
export PLATFORM_SCRIPTS_PATH="/home/your-username/repos/platform-scripts"

# Windows
setx PLATFORM_SCRIPTS_PATH "C:\repos\platform-scripts"
```

### Option 2: Standard Location

Place platform-scripts in one of these locations:
- `C:\repos\platform-scripts` (Windows)
- `~/repos/platform-scripts` (Linux/Mac)
- `~/source/repos/platform-scripts`
- `/opt/platform-scripts`

### Option 3: CLI Path

```bash
python S3_migration.py --scripts-path /path/to/platform-scripts --repos my-repo
```

## CLI Options Reference

| Option | Description | Default |
|--------|-------------|---------|
| `--repos` | Comma-separated list of repositories (required) | - |
| `--org` | GitHub organization name | `your-org` |
| `--bucket` | S3 bucket for state storage | `your-org-tfstate-bucket` |
| `--region` | AWS region | `us-east-1` |
| `--aws-profile` | AWS CLI profile to use | `default` |
| `--scripts-path` | Path to platform-scripts directory | Auto-detected |
| `--batch-size` | Number of concurrent migrations | `1` |
| `--dry-run` | Preview changes without executing | `false` |
| `--skip-validation` | Skip environment validation | `false` |
| `--skip-version-check` | Skip module version validation | `false` |
| `--auto-commit` | Auto-commit without prompts | `false` |
| `--work-dir` | Working directory for clones | `./migration_work` |
| `--branch` | Migration branch name | `migrate-to-s3-backend` |
| `--verbose` | Enable debug logging | `false` |

## Migration Pipeline

The tool executes a 12-step pipeline for each repository:

1. **Clone Repository** - Clone from GitHub using `gh` CLI
2. **Create Branch** - Create and checkout migration branch
3. **Validate Versions** - Check module version requirements (optional)
4. **Copy State** - Execute `copy_state.sh` to migrate state from TFC to S3
5. **Update Backend** - Replace `cloud {}` block with `backend "s3" {}` configuration
6. **Update Modules** - Convert TFC registry sources to Git-based sources
7. **Update Workflows** - Inject GitHub secrets into workflow files
8. **Commit Changes** - Stage and commit all modifications
9. **Push Branch** - Push migration branch to remote
10. **Create PR** - Create pull request via `gh pr create`
11. **Verify State** - Confirm state files exist in S3
12. **Log Completion** - Record results and generate summary

## Security Features

### Secret Sanitization

All log output is automatically sanitized to prevent sensitive data leakage:

- AWS Access Keys (AKIA...)
- AWS Secret Keys
- GitHub Personal Access Tokens
- OAuth Tokens
- API Keys
- Passwords
- Private Keys
- Email Addresses

### PII Scanner

Run the included PII scanner to detect any accidental data leaks:

```bash
python scripts/pii_scanner.py
```

The scanner checks for:
- AWS credentials
- GitHub tokens
- Private keys
- API keys
- Organization-specific references
- Personal paths
- Connection strings

## Troubleshooting

### Environment Validation Failed

**Issue**: One or more CLI tools not found

**Solution**:
```bash
# Install missing tools
aws --version  # Install AWS CLI
terraform --version  # Install Terraform
gh --version  # Install GitHub CLI
git --version  # Install Git

# Authenticate
gh auth login
aws configure --profile default
```

### Platform Scripts Not Found

**Issue**: `Platform scripts directory not found in standard locations`

**Solution**:
```bash
# Set environment variable
export PLATFORM_SCRIPTS_PATH="/path/to/platform-scripts"

# Or use CLI argument
python S3_migration.py --scripts-path /path/to/platform-scripts --repos my-repo
```

### State Copy Failed

**Issue**: `Failed to copy state to S3`

**Solution**:
- Verify Terraform Cloud token is configured: `echo $TF_TOKEN`
- Check AWS credentials: `aws sts get-caller-identity --profile default`
- Verify S3 bucket exists and is accessible
- Review `copy_state.sh` script in platform-scripts

### PR Creation Failed

**Issue**: `Failed to create pull request`

**Solution**:
- Verify GitHub CLI authentication: `gh auth status`
- Check repository permissions (must have write access)
- Ensure branch doesn't already have an open PR
- Try creating PR manually: `gh pr create`

## Rollback Instructions

If a migration needs to be rolled back:

### 1. Close the Pull Request

```bash
# Via GitHub CLI
gh pr close [PR-NUMBER] --repo your-org/repo-name

# Via Web UI
# Navigate to the PR and click "Close pull request"
```

### 2. Delete the Migration Branch

```bash
# Delete remote branch
git push origin --delete migrate-to-s3-backend

# Delete local branch
git branch -D migrate-to-s3-backend
```

### 3. Restore Original Backend (if changes were merged)

```bash
# Revert the backend configuration commit
git revert [COMMIT-SHA]

# Run terraform init to reconfigure
terraform init -reconfigure
```

### 4. Copy State Back to TFC (if needed)

If state was already migrated to S3, you may need to copy it back to Terraform Cloud:

```bash
# Pull state from S3
terraform state pull > backup.tfstate

# Reconfigure for TFC
terraform init -reconfigure

# Push state back to TFC
terraform state push backup.tfstate
```

## Cost Savings Analysis

See [docs/COST_SAVINGS.md](docs/COST_SAVINGS.md) for detailed cost analysis showing how this migration can save $126K+ annually for organizations managing 100K+ Terraform resources.

## Documentation

- [USAGE.md](USAGE.md) - Detailed usage guide with examples
- [SECURITY_CONFIG.md](SECURITY_CONFIG.md) - Security configuration best practices
- [SECURITY_SUMMARY.md](SECURITY_SUMMARY.md) - Security audit summary
- [ORG_CONFIGURATION.md](ORG_CONFIGURATION.md) - Organization setup guide
- [PRODUCTION_IMPROVEMENTS.md](PRODUCTION_IMPROVEMENTS.md) - Production hardening notes
- [docs/MIGRATION_GUIDE.md](docs/MIGRATION_GUIDE.md) - Step-by-step migration guide
- [docs/COST_SAVINGS.md](docs/COST_SAVINGS.md) - Cost analysis documentation

## Related Projects

This tool is part of a larger system design portfolio. For architectural patterns, infrastructure-as-code best practices, and system design references, see:

**[System-Design-Engineering-Universal-Reference](https://github.com/EPdacoder05/System-Design-Engineering-Universal-Reference)**

## Contributing

Contributions are welcome! This is a portfolio project, but improvements and bug fixes are appreciated.

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run the PII scanner: `python scripts/pii_scanner.py`
5. Submit a pull request

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Author

**EPdacoder05**

Portfolio project demonstrating production-ready infrastructure automation, Python engineering, and cloud cost optimization.

---

*This tool is organization-agnostic and contains zero PII or company-specific references. All values are configurable via CLI arguments, environment variables, or the config module.*
