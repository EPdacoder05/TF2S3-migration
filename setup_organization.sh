#!/bin/bash
###############################################################################
# Organization Setup Script for TF2S3 Migration Tool (Linux/Mac)
#
# This script helps you configure the migration tool for your organization
# by prompting for required values and creating a .env configuration file.
###############################################################################

set -e

echo "============================================================================"
echo "  TF2S3 Migration Tool - Organization Setup"
echo "============================================================================"
echo ""
echo "This script will help you configure the migration tool for your organization."
echo "All values will be saved to a .env file in the current directory."
echo ""

# Function to prompt for input with default value
prompt_with_default() {
    local prompt="$1"
    local default="$2"
    local value
    
    read -p "$prompt [$default]: " value
    echo "${value:-$default}"
}

# Function to prompt for input (required)
prompt_required() {
    local prompt="$1"
    local value
    
    while [ -z "$value" ]; do
        read -p "$prompt (required): " value
        if [ -z "$value" ]; then
            echo "  ❌ This value is required. Please enter a value."
        fi
    done
    
    echo "$value"
}

# Prompt for configuration values
echo "📋 Configuration Values"
echo "─────────────────────────────────────────────────────────────────────────"
echo ""

GITHUB_ORG=$(prompt_required "GitHub Organization Name")
echo "✅ GitHub Org: $GITHUB_ORG"
echo ""

S3_BUCKET=$(prompt_with_default "S3 Bucket Name for Terraform State" "${GITHUB_ORG}-tfstate-bucket")
echo "✅ S3 Bucket: $S3_BUCKET"
echo ""

AWS_REGION=$(prompt_with_default "AWS Region" "us-east-1")
echo "✅ AWS Region: $AWS_REGION"
echo ""

AWS_PROFILE=$(prompt_with_default "AWS CLI Profile Name" "default")
echo "✅ AWS Profile: $AWS_PROFILE"
echo ""

echo "Platform Scripts Path (where copy_state.sh is located)"
echo "Common locations:"
echo "  - ~/repos/platform-scripts"
echo "  - ~/source/repos/platform-scripts"
echo "  - /opt/platform-scripts"
PLATFORM_SCRIPTS_PATH=$(prompt_with_default "Platform Scripts Path" "~/repos/platform-scripts")
# Expand ~ to actual home directory
PLATFORM_SCRIPTS_PATH="${PLATFORM_SCRIPTS_PATH/#\~/$HOME}"
echo "✅ Platform Scripts: $PLATFORM_SCRIPTS_PATH"
echo ""

BATCH_SIZE=$(prompt_with_default "Batch Size (concurrent migrations)" "1")
echo "✅ Batch Size: $BATCH_SIZE"
echo ""

# Ask if user wants to enable auto-commit
read -p "Enable auto-commit (skip confirmation prompts)? [y/N]: " AUTO_COMMIT_INPUT
if [[ "$AUTO_COMMIT_INPUT" =~ ^[Yy]$ ]]; then
    AUTO_COMMIT="true"
else
    AUTO_COMMIT="false"
fi
echo "✅ Auto-commit: $AUTO_COMMIT"
echo ""

# Summary
echo ""
echo "============================================================================"
echo "  Configuration Summary"
echo "============================================================================"
echo ""
echo "GitHub Organization:   $GITHUB_ORG"
echo "S3 Bucket:             $S3_BUCKET"
echo "AWS Region:            $AWS_REGION"
echo "AWS Profile:           $AWS_PROFILE"
echo "Platform Scripts:      $PLATFORM_SCRIPTS_PATH"
echo "Batch Size:            $BATCH_SIZE"
echo "Auto-commit:           $AUTO_COMMIT"
echo ""

# Confirm before writing
read -p "Save this configuration to .env file? [Y/n]: " CONFIRM
if [[ "$CONFIRM" =~ ^[Nn]$ ]]; then
    echo "❌ Configuration cancelled. No changes made."
    exit 0
fi

# Create .env file
ENV_FILE=".env"

cat > "$ENV_FILE" << EOF
# TF2S3 Migration Tool Configuration
# Generated on $(date)

# GitHub Configuration
GITHUB_ORG=$GITHUB_ORG
GITHUB_TOKEN=

# AWS Configuration
AWS_PROFILE=$AWS_PROFILE
AWS_REGION=$AWS_REGION
S3_BUCKET=$S3_BUCKET

# Platform Scripts
PLATFORM_SCRIPTS_PATH=$PLATFORM_SCRIPTS_PATH

# Migration Settings
DRY_RUN=false
BATCH_SIZE=$BATCH_SIZE
AUTO_COMMIT=$AUTO_COMMIT
EOF

echo ""
echo "✅ Configuration saved to $ENV_FILE"
echo ""

# Check if platform scripts exist
if [ -f "$PLATFORM_SCRIPTS_PATH/copy_state.sh" ]; then
    echo "✅ Platform scripts found at: $PLATFORM_SCRIPTS_PATH"
else
    echo "⚠️  Warning: copy_state.sh not found at: $PLATFORM_SCRIPTS_PATH"
    echo "   Make sure to place your platform-scripts repository there before running migrations."
fi
echo ""

# Validation steps
echo "============================================================================"
echo "  Next Steps"
echo "============================================================================"
echo ""
echo "1. Verify your configuration:"
echo "   cat .env"
echo ""
echo "2. Set your GitHub token (if needed):"
echo "   echo 'GITHUB_TOKEN=ghp_your_token' >> .env"
echo ""
echo "3. Test your environment:"
echo "   python S3_migration.py --repos test-repo --dry-run"
echo ""
echo "4. Run your first migration:"
echo "   python S3_migration.py --repos your-repo-name"
echo ""
echo "For more information, see:"
echo "  - README.md - Quick start guide"
echo "  - USAGE.md - Detailed usage examples"
echo "  - ORG_CONFIGURATION.md - Organization setup guide"
echo ""
echo "============================================================================"

exit 0
