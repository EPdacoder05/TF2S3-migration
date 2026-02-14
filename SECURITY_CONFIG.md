# Security Configuration

Security guidelines and best practices for the TF2S3 Migration Tool.

## Overview

This tool handles sensitive infrastructure data including:
- Terraform state files (may contain secrets)
- AWS credentials
- GitHub tokens
- Terraform Cloud tokens

Proper security configuration is critical to prevent data leaks and unauthorized access.

## Security Features

### 1. Automatic Secret Sanitization

All log output is automatically sanitized to remove sensitive data before writing to files or console.

**Patterns Redacted:**
- AWS Access Keys (`AKIA...`)
- AWS Secret Keys
- GitHub Personal Access Tokens (`ghp_...`, `gho_...`, `ghs_...`)
- Fine-grained GitHub PATs (`github_pat_...`)
- Generic API keys and tokens
- Passwords and secrets
- Private keys (PEM format)
- Email addresses

### 2. Input Validation

All user inputs are validated to prevent:
- **Path Traversal**: Rejects `../` and similar patterns
- **Command Injection**: Filters shell metacharacters
- **Control Characters**: Blocks invisible/control characters
- **Invalid Formats**: Validates repository names, regions, etc.

### 3. Secure Defaults

- No credentials stored in code
- Credentials loaded from environment or AWS CLI config
- Subprocess execution with timeouts
- Error messages sanitized

## Required Credentials

### AWS Credentials

**Recommended Method: AWS CLI Profiles**

```bash
# Configure default profile
aws configure --profile default

# Or configure named profile
aws configure --profile production
```

**Alternative: Environment Variables (Less Secure)**

```bash
export AWS_ACCESS_KEY_ID="AKIA..."
export AWS_SECRET_ACCESS_KEY="..."
export AWS_REGION="us-east-1"
```

**Do NOT:**
- ❌ Store credentials in code
- ❌ Commit credentials to Git
- ❌ Use root account credentials
- ❌ Share credentials across teams

**Do:**
- ✅ Use IAM roles when possible
- ✅ Use temporary credentials (STS)
- ✅ Rotate credentials regularly
- ✅ Use separate profiles for different environments

### GitHub Token

**Recommended Method: GitHub CLI**

```bash
# Login via GitHub CLI (most secure)
gh auth login

# Verify authentication
gh auth status
```

**Alternative: Personal Access Token**

If using PAT directly:

```bash
export GITHUB_TOKEN="ghp_..."
```

**Required Scopes:**
- `repo` - Full repository access
- `workflow` - Update GitHub Actions workflows
- `read:org` - Read organization data

**Do NOT:**
- ❌ Use tokens with broader permissions than needed
- ❌ Commit tokens to repository
- ❌ Share tokens between users

**Do:**
- ✅ Use fine-grained tokens when possible
- ✅ Set token expiration
- ✅ Rotate tokens regularly
- ✅ Revoke tokens when no longer needed

### Terraform Cloud Token

**Configuration:**

```bash
# Set via environment variable
export TF_TOKEN="..."

# Or configure in ~/.terraform.d/credentials.tfrc.json
{
  "credentials": {
    "app.terraform.io": {
      "token": "..."
    }
  }
}
```

**Do NOT:**
- ❌ Share tokens between users
- ❌ Use organization tokens for individual operations

**Do:**
- ✅ Use user-specific tokens
- ✅ Set appropriate permissions (read access to workspaces)
- ✅ Rotate tokens periodically

## AWS IAM Permissions

### Minimum Required Permissions

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
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

### Recommended: Use IAM Roles

For production environments, use IAM roles instead of long-lived credentials:

```bash
# Assume role via AWS CLI
aws sts assume-role \
  --role-arn arn:aws:iam::123456789012:role/TerraformMigrationRole \
  --role-session-name migration-session

# Or use instance/container roles in AWS environments
```

## S3 Bucket Security

### Bucket Configuration

**Enable Encryption:**
```bash
aws s3api put-bucket-encryption \
  --bucket your-org-tfstate-bucket \
  --server-side-encryption-configuration '{
    "Rules": [{
      "ApplyServerSideEncryptionByDefault": {
        "SSEAlgorithm": "AES256"
      }
    }]
  }'
```

**Enable Versioning:**
```bash
aws s3api put-bucket-versioning \
  --bucket your-org-tfstate-bucket \
  --versioning-configuration Status=Enabled
```

**Block Public Access:**
```bash
aws s3api put-public-access-block \
  --bucket your-org-tfstate-bucket \
  --public-access-block-configuration \
    BlockPublicAcls=true,\
    IgnorePublicAcls=true,\
    BlockPublicPolicy=true,\
    RestrictPublicBuckets=true
```

**Enable Logging:**
```bash
aws s3api put-bucket-logging \
  --bucket your-org-tfstate-bucket \
  --bucket-logging-status '{
    "LoggingEnabled": {
      "TargetBucket": "your-org-logs-bucket",
      "TargetPrefix": "s3-access-logs/tfstate/"
    }
  }'
```

### Bucket Policy

Restrict access to specific IAM roles/users:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Deny",
      "Principal": "*",
      "Action": "s3:*",
      "Resource": [
        "arn:aws:s3:::your-org-tfstate-bucket",
        "arn:aws:s3:::your-org-tfstate-bucket/*"
      ],
      "Condition": {
        "Bool": {
          "aws:SecureTransport": "false"
        }
      }
    }
  ]
}
```

## DynamoDB Lock Table Security

### Table Configuration

**Enable Point-in-Time Recovery:**
```bash
aws dynamodb update-continuous-backups \
  --table-name terraform-state-lock \
  --point-in-time-recovery-specification PointInTimeRecoveryEnabled=true
```

**Enable Encryption:**
```bash
aws dynamodb update-table \
  --table-name terraform-state-lock \
  --sse-specification Enabled=true,SSEType=KMS
```

## Secure Execution Environment

### File System Permissions

```bash
# Restrict access to working directory
chmod 700 migration_work/

# Restrict access to log directory
chmod 700 migration_logs/

# Protect configuration files
chmod 600 .env
```

### Network Security

**Firewall Rules:**
- Allow HTTPS (443) to github.com, app.terraform.io, AWS endpoints
- Block all other outbound traffic (if possible)

**Use VPN:**
- Run migrations from within corporate VPN when possible
- Avoid public Wi-Fi networks

### Log Security

**Log Rotation:**
```bash
# Logs are written to migration_logs/ with timestamps
# Implement log rotation if running frequently

# Example: Keep only last 30 days of logs
find migration_logs/ -name "*.log" -mtime +30 -delete
```

**Log Sanitization:**
- Logs are automatically sanitized
- Verify no credentials in logs: `grep -i "AKIA\|ghp_\|password" migration_logs/*.log`

## Security Scanning

### Pre-Commit Scanning

Run PII scanner before committing changes:

```bash
# Scan entire repository
python scripts/pii_scanner.py

# Exit code 1 if findings detected
echo $?
```

### Continuous Scanning

GitHub Actions workflow automatically scans on every push:

```yaml
# .github/workflows/pii-scan.yml
name: PII Scanner
on: [push, pull_request]
jobs:
  scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run PII Scanner
        run: python scripts/pii_scanner.py
```

### Manual Security Audit

Periodically review:

```bash
# Check for accidentally committed secrets
git log -p | grep -i "AKIA\|ghp_\|password"

# Check for organization-specific references
grep -ri "company-name\|org-name" .

# Check for personal paths
grep -ri "ellis\|c:\\\\users\\\\specific-user" .
```

## Incident Response

### If Credentials Are Leaked

**Immediate Actions:**

1. **Rotate Credentials**
   ```bash
   # AWS: Rotate access keys immediately
   aws iam create-access-key --user-name your-user
   aws iam delete-access-key --access-key-id OLD_KEY_ID --user-name your-user
   
   # GitHub: Revoke and regenerate token
   gh auth refresh -h github.com -s repo,workflow
   ```

2. **Revoke S3 Bucket Access**
   ```bash
   # Temporarily block all access
   aws s3api put-public-access-block --bucket your-org-tfstate-bucket \
     --public-access-block-configuration BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
   ```

3. **Review Access Logs**
   ```bash
   # Check S3 access logs for unauthorized access
   aws s3 ls s3://your-org-logs-bucket/s3-access-logs/tfstate/
   ```

4. **Clean Git History (if committed)**
   ```bash
   # Use BFG Repo Cleaner to remove secrets from history
   git clone --mirror https://github.com/your-org/repository.git
   java -jar bfg.jar --replace-text passwords.txt repository.git
   cd repository.git
   git reflog expire --expire=now --all
   git gc --prune=now --aggressive
   git push --force
   ```

### If State Files Are Compromised

1. **Rotate Any Secrets in State**
   - Database passwords
   - API keys
   - Certificates

2. **Review State Access Logs**
   ```bash
   aws s3api get-bucket-logging --bucket your-org-tfstate-bucket
   ```

3. **Update Bucket Policies**
   - Restrict access further
   - Require MFA for access

## Compliance Considerations

### Data Residency

If you have data residency requirements:

```bash
# Specify region for state storage
python S3_migration.py \
  --repos repo-name \
  --region eu-west-1 \
  --bucket your-org-eu-tfstate
```

### Audit Trail

Maintain audit trail of migrations:

```bash
# Logs include:
# - Timestamp of migration
# - User executing migration (from Git config)
# - Repositories migrated
# - Changes made
# - PR URLs created

# Review audit trail
cat migration_logs/migration_*.log | grep "Successfully migrated"
```

### Access Reviews

Regularly review:
- Who has access to S3 bucket
- Who has access to DynamoDB table
- Who has access to GitHub repositories
- Token expiration dates

## Security Checklist

Before running migrations:

- [ ] AWS credentials configured securely (IAM roles preferred)
- [ ] GitHub CLI authenticated
- [ ] Terraform Cloud token configured
- [ ] S3 bucket encryption enabled
- [ ] S3 bucket versioning enabled
- [ ] S3 public access blocked
- [ ] DynamoDB encryption enabled
- [ ] IAM permissions follow least privilege
- [ ] Network security configured (VPN, firewall)
- [ ] PII scanner executed successfully
- [ ] No credentials in code or configuration files
- [ ] Logs will be stored securely
- [ ] Backup strategy in place

After migration:

- [ ] Verify no credentials in logs
- [ ] Rotate temporary credentials used
- [ ] Review S3 access logs
- [ ] Update documentation with any security notes
- [ ] Archive old Terraform Cloud workspaces

## Resources

- [AWS Security Best Practices](https://docs.aws.amazon.com/security/)
- [GitHub Security Best Practices](https://docs.github.com/en/security)
- [Terraform Security](https://www.terraform.io/docs/language/state/security.html)
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)

## Contact

For security concerns or to report vulnerabilities, please contact the repository owner.
