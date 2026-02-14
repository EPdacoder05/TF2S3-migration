###############################################################################
# Organization Setup Script for TF2S3 Migration Tool (Windows PowerShell)
#
# This script helps you configure the migration tool for your organization
# by prompting for required values and creating a .env configuration file.
###############################################################################

# Set error action preference
$ErrorActionPreference = "Stop"

Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host "  TF2S3 Migration Tool - Organization Setup" -ForegroundColor Cyan
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "This script will help you configure the migration tool for your organization."
Write-Host "All values will be saved to a .env file in the current directory."
Write-Host ""

# Function to prompt for input with default value
function Prompt-WithDefault {
    param(
        [string]$Prompt,
        [string]$Default
    )
    
    $value = Read-Host "$Prompt [$Default]"
    if ([string]::IsNullOrWhiteSpace($value)) {
        return $Default
    }
    return $value
}

# Function to prompt for required input
function Prompt-Required {
    param(
        [string]$Prompt
    )
    
    $value = ""
    while ([string]::IsNullOrWhiteSpace($value)) {
        $value = Read-Host "$Prompt (required)"
        if ([string]::IsNullOrWhiteSpace($value)) {
            Write-Host "  ❌ This value is required. Please enter a value." -ForegroundColor Red
        }
    }
    return $value
}

# Prompt for configuration values
Write-Host "📋 Configuration Values" -ForegroundColor Yellow
Write-Host "─────────────────────────────────────────────────────────────────────────"
Write-Host ""

$githubOrg = Prompt-Required "GitHub Organization Name"
Write-Host "✅ GitHub Org: $githubOrg" -ForegroundColor Green
Write-Host ""

$s3Bucket = Prompt-WithDefault "S3 Bucket Name for Terraform State" "$githubOrg-tfstate-bucket"
Write-Host "✅ S3 Bucket: $s3Bucket" -ForegroundColor Green
Write-Host ""

$awsRegion = Prompt-WithDefault "AWS Region" "us-east-1"
Write-Host "✅ AWS Region: $awsRegion" -ForegroundColor Green
Write-Host ""

$awsProfile = Prompt-WithDefault "AWS CLI Profile Name" "default"
Write-Host "✅ AWS Profile: $awsProfile" -ForegroundColor Green
Write-Host ""

Write-Host "Platform Scripts Path (where copy_state.sh is located)"
Write-Host "Common locations:"
Write-Host "  - C:\repos\platform-scripts"
Write-Host "  - $HOME\repos\platform-scripts"
$platformScriptsPath = Prompt-WithDefault "Platform Scripts Path" "C:\repos\platform-scripts"
Write-Host "✅ Platform Scripts: $platformScriptsPath" -ForegroundColor Green
Write-Host ""

$batchSize = Prompt-WithDefault "Batch Size (concurrent migrations)" "1"
Write-Host "✅ Batch Size: $batchSize" -ForegroundColor Green
Write-Host ""

# Ask if user wants to enable auto-commit
$autoCommitInput = Read-Host "Enable auto-commit (skip confirmation prompts)? [y/N]"
if ($autoCommitInput -match "^[Yy]$") {
    $autoCommit = "true"
} else {
    $autoCommit = "false"
}
Write-Host "✅ Auto-commit: $autoCommit" -ForegroundColor Green
Write-Host ""

# Summary
Write-Host ""
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host "  Configuration Summary" -ForegroundColor Cyan
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "GitHub Organization:   $githubOrg"
Write-Host "S3 Bucket:             $s3Bucket"
Write-Host "AWS Region:            $awsRegion"
Write-Host "AWS Profile:           $awsProfile"
Write-Host "Platform Scripts:      $platformScriptsPath"
Write-Host "Batch Size:            $batchSize"
Write-Host "Auto-commit:           $autoCommit"
Write-Host ""

# Confirm before writing
$confirm = Read-Host "Save this configuration to .env file? [Y/n]"
if ($confirm -match "^[Nn]$") {
    Write-Host "❌ Configuration cancelled. No changes made." -ForegroundColor Red
    exit 0
}

# Create .env file
$envFile = ".env"
$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"

$envContent = @"
# TF2S3 Migration Tool Configuration
# Generated on $timestamp

# GitHub Configuration
GITHUB_ORG=$githubOrg
GITHUB_TOKEN=

# AWS Configuration
AWS_PROFILE=$awsProfile
AWS_REGION=$awsRegion
S3_BUCKET=$s3Bucket

# Platform Scripts
PLATFORM_SCRIPTS_PATH=$platformScriptsPath

# Migration Settings
DRY_RUN=false
BATCH_SIZE=$batchSize
AUTO_COMMIT=$autoCommit
"@

Set-Content -Path $envFile -Value $envContent -Encoding UTF8

Write-Host ""
Write-Host "✅ Configuration saved to $envFile" -ForegroundColor Green
Write-Host ""

# Check if platform scripts exist
$copyStateScript = Join-Path $platformScriptsPath "copy_state.sh"
if (Test-Path $copyStateScript) {
    Write-Host "✅ Platform scripts found at: $platformScriptsPath" -ForegroundColor Green
} else {
    Write-Host "⚠️  Warning: copy_state.sh not found at: $platformScriptsPath" -ForegroundColor Yellow
    Write-Host "   Make sure to place your platform-scripts repository there before running migrations."
}
Write-Host ""

# Validation steps
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host "  Next Steps" -ForegroundColor Cyan
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. Verify your configuration:"
Write-Host "   Get-Content .env"
Write-Host ""
Write-Host "2. Set your GitHub token (if needed):"
Write-Host "   Add-Content .env 'GITHUB_TOKEN=ghp_your_token'"
Write-Host ""
Write-Host "3. Test your environment:"
Write-Host "   python S3_migration.py --repos test-repo --dry-run"
Write-Host ""
Write-Host "4. Run your first migration:"
Write-Host "   python S3_migration.py --repos your-repo-name"
Write-Host ""
Write-Host "For more information, see:"
Write-Host "  - README.md - Quick start guide"
Write-Host "  - USAGE.md - Detailed usage examples"
Write-Host "  - ORG_CONFIGURATION.md - Organization setup guide"
Write-Host ""
Write-Host "============================================================================" -ForegroundColor Cyan

exit 0
