"""
Configuration module for TF2S3 Migration Tool

All values are generic placeholders — configure for YOUR organization.
Update these values or provide via CLI arguments/environment variables.
"""

import os
from typing import Dict, Optional

# Organization defaults - CUSTOMIZE THESE FOR YOUR ORG
DEFAULT_ORGANIZATION = "your-org"
DEFAULT_BUCKET_NAME = "your-org-tfstate-bucket"
DEFAULT_REGION = "us-east-1"
DEFAULT_AWS_PROFILE = "default"
DEFAULT_BRANCH_NAME = "migrate-to-s3-backend"

# Platform scripts paths (auto-detected or manually configured)
# The tool will search these locations for your platform-scripts repository
PLATFORM_SCRIPTS_PATHS = [
    os.environ.get("PLATFORM_SCRIPTS_PATH", ""),
    os.path.join("C:\\repos", "platform-scripts"),
    os.path.join("C:\\", "repos", "platform-scripts"),
    os.path.join(os.path.expanduser("~"), "repos", "platform-scripts"),
    os.path.join(os.path.expanduser("~"), "source", "repos", "platform-scripts"),
    "/opt/platform-scripts",
    "/usr/local/platform-scripts",
]

# Module version requirements — customize for your org's modules
# Format: "module-name": {"min": "X.Y.Z", "max": "X.Y.Z" or None}
REQUIRED_VERSIONS: Dict[str, Dict[str, Optional[str]]] = {
    "your-github-project-factory": {"min": "15.1.0", "max": None},
    "your-aws-project-factory": {"min": "5.5.2", "max": None},
}

# Sensitive patterns to redact from logs
# These regex patterns identify sensitive data that should never appear in logs
SENSITIVE_PATTERNS = [
    r'AKIA[0-9A-Z]{16}',                      # AWS Access Key
    r'(?i)aws_secret_access_key\s*=\s*\S+',  # AWS Secret Key
    r'ghp_[a-zA-Z0-9]{36}',                   # GitHub PAT
    r'gho_[a-zA-Z0-9]{36}',                   # GitHub OAuth
    r'ghs_[a-zA-Z0-9]{36}',                   # GitHub App Token
    r'github_pat_[a-zA-Z0-9]{82}',            # GitHub Fine-grained PAT
    r'(?i)token\s*[:=]\s*["\']?\S{20,}',     # Generic token
    r'(?i)password\s*[:=]\s*["\']?\S{8,}',   # Generic password
    r'(?i)secret\s*[:=]\s*["\']?\S{8,}',     # Generic secret
    r'-----BEGIN (?:RSA |EC )?PRIVATE KEY-----',  # Private keys
    r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # Email addresses
]

# Migration settings
DEFAULT_BATCH_SIZE = 1  # Number of concurrent repository migrations
DEFAULT_TIMEOUT = 300   # Command timeout in seconds (5 minutes)
MAX_RETRIES = 3         # Maximum retry attempts for failed operations

# Logging configuration
LOG_DIRECTORY = "migration_logs"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Backend configuration template for S3
BACKEND_TEMPLATE = '''
  backend "s3" {{
    bucket         = "{bucket}"
    key            = "{key}"
    region         = "{region}"
    dynamodb_table = "{dynamodb_table}"
    encrypt        = true
  }}
'''

# DynamoDB table naming convention
DYNAMODB_TABLE_NAME = "terraform-state-lock"

# Git configuration
GIT_COMMIT_MESSAGE = "Migrate Terraform backend from Cloud to S3"
PR_TITLE = "Migrate Terraform backend from Cloud to S3"
PR_BODY_TEMPLATE = """
## Migration Summary

This PR migrates the Terraform backend from HCP Terraform Cloud to AWS S3/DynamoDB.

### Changes Made:
- ✅ Terraform state copied from Cloud to S3
- ✅ Backend configuration updated to use S3
- ✅ Module sources converted from TFC registry to Git
- ✅ GitHub Actions workflows updated with required secrets

### Testing:
- [ ] Run `terraform init` to verify backend configuration
- [ ] Run `terraform plan` to verify state integrity
- [ ] Verify no resource changes are detected (state should match)

### Post-Merge:
1. Merge this PR
2. Run `terraform init -reconfigure` in your local environment
3. Verify state is accessible
4. Archive the old TFC workspace

Related documentation: [MIGRATION_GUIDE.md](docs/MIGRATION_GUIDE.md)
"""

# File patterns for Terraform operations
TF_FILE_PATTERNS = ["*.tf", "**/*.tf"]
WORKFLOW_FILE_PATTERNS = [".github/workflows/*.yml", ".github/workflows/*.yaml"]

# Validation patterns
VALID_REPO_NAME_PATTERN = r'^[a-zA-Z0-9_.-]+$'
INVALID_REPO_PATTERNS = [
    r'\.\.',      # Path traversal
    r'[;&|`$]',   # Shell metacharacters
    r'[\x00-\x1f]',  # Control characters
]
