#!/usr/bin/env python3
"""
PII Scanner - Complex Regex-Based Security Scanner

Scans all files in the repository for potential personally identifiable information
and sensitive data leaks using comprehensive regex patterns.

Exit codes:
  0 - No findings (clean)
  1 - Findings detected (potential security issues)
"""

import re
import sys
from pathlib import Path

# Comprehensive PII and sensitive data patterns
PII_PATTERNS: dict[str, str] = {
    "AWS Account ID": r'\b\d{12}\b',
    "AWS Access Key": r'AKIA[0-9A-Z]{16}',
    "AWS Secret Key": r'(?i)aws_secret_access_key\s*=\s*\S+',
    "GitHub PAT": r'ghp_[a-zA-Z0-9]{36}',
    "GitHub OAuth": r'gho_[a-zA-Z0-9]{36}',
    "GitHub App Token": r'ghs_[a-zA-Z0-9]{36}',
    "GitHub Fine-grained PAT": r'github_pat_[a-zA-Z0-9]{82}',
    "Private Key": r'-----BEGIN (?:RSA |EC )?PRIVATE KEY-----',
    "Generic API Key": r'(?i)(?:api[_-]?key|apikey)\s*[:=]\s*["\']?\w{20,}',
    "Generic Secret": r'(?i)(?:secret|password|passwd|pwd)\s*[:=]\s*["\']?\S{8,}',
    "IP Address (Private)": r'\b(?:10\.\d{1,3}\.\d{1,3}\.\d{1,3}|172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}|192\.168\.\d{1,3}\.\d{1,3})\b',
    "Email Address": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
    "Slack Webhook": r'https://hooks\.slack\.com/services/T[A-Z0-9]+/B[A-Z0-9]+/[a-zA-Z0-9]+',
    "JWT Token": r'eyJ[A-Za-z0-9-_]+\.eyJ[A-Za-z0-9-_]+\.[A-Za-z0-9-_]+',
    "Connection String": r'(?i)(?:mongodb|postgres|mysql|redis|amqp)://\S+',
    "S3 Bucket (Specific)": r'(?i)(?:qh-|quantum|q-health)',  # Catches any remnant org references
    "Org Reference": r'(?i)(?:Q-Health|Quantum\.Health|quantum-health)',
    "Personal Path": r'(?i)(?:ellis\.pinaman|Ellis\.Pinaman|ellis_pinaman)',
}

# Additional patterns for common sensitive data
ADDITIONAL_PATTERNS: dict[str, str] = {
    "Credit Card": r'\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b',
    "SSN": r'\b\d{3}-\d{2}-\d{4}\b',
    "Phone Number": r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
    "Azure Key": r'(?i)azure[_-]?(?:key|secret|token)\s*[:=]\s*\S+',
    "GCP Key": r'(?i)gcp[_-]?(?:key|secret|token)\s*[:=]\s*\S+',
    "NPM Token": r'npm_[A-Za-z0-9]{36}',
    "PyPI Token": r'pypi-[A-Za-z0-9-_]{84}',
    "Docker Hub Token": r'dckr_pat_[a-zA-Z0-9_-]{60}',
}

# Combine all patterns
ALL_PATTERNS = {**PII_PATTERNS, **ADDITIONAL_PATTERNS}

# Directories to exclude from scanning
EXCLUDED_DIRS = [
    '.git',
    '__pycache__',
    'node_modules',
    '.terraform',
    'venv',
    'env',
    '.venv',
    'dist',
    'build',
    '.pytest_cache',
    '.mypy_cache',
    '.tox',
    'migration_logs',
]

# File extensions to exclude
EXCLUDED_EXTENSIONS = [
    '.pyc',
    '.pyo',
    '.pyd',
    '.so',
    '.dll',
    '.dylib',
    '.exe',
    '.bin',
    '.jpg',
    '.jpeg',
    '.png',
    '.gif',
    '.pdf',
    '.zip',
    '.tar',
    '.gz',
]

# Whitelist patterns (known safe matches)
WHITELIST_PATTERNS = [
    r'example@example\.com',  # Example email
    r'user@example\.com',
    r'test@test\.com',
    r'your-org',  # Generic placeholders
    r'acme-corp',
    r'your-username',
    r'your-email@example\.com',
    r'AKIA[X]{16}',  # Example AWS key
    r'AKIA\.\.\.',  # Redacted example
    r'ghp_[X]{36}',  # Example GitHub token
    r'192\.168\.1\.1',  # Common example IPs
    r'10\.0\.0\.1',
    r'123456789012',  # Example AWS account ID in docs
    r'aws_secret_access_key\s*=\s*"?\.\.\."?',  # Redacted examples in docs
    r'AWS_SECRET_ACCESS_KEY\s*=\s*"?\.\.\."?',  # Redacted examples in docs (uppercase)
    r'-----BEGIN.*PRIVATE KEY-----',  # Key format examples in docs (not actual keys)
]


class PIIScanner:
    """Scanner for PII and sensitive data in files."""

    def __init__(self, root_dir: str = "."):
        """Initialize scanner with root directory."""
        self.root_dir = Path(root_dir).resolve()
        self.findings: list[tuple[str, str, int, str, str]] = []
        self.files_scanned = 0
        self.compiled_patterns = {
            name: re.compile(pattern)
            for name, pattern in ALL_PATTERNS.items()
        }
        self.compiled_whitelist = [
            re.compile(pattern) for pattern in WHITELIST_PATTERNS
        ]

    def should_skip_file(self, file_path: Path) -> bool:
        """Check if file should be skipped."""
        # Check if in excluded directory
        for excluded_dir in EXCLUDED_DIRS:
            if excluded_dir in file_path.parts:
                return True

        # Check file extension
        if file_path.suffix in EXCLUDED_EXTENSIONS:
            return True

        # Skip binary files
        try:
            with open(file_path, encoding='utf-8') as f:
                f.read(1024)  # Test read
        except (UnicodeDecodeError, PermissionError):
            return True

        return False

    def is_whitelisted(self, match: str) -> bool:
        """Check if match is in whitelist (known safe pattern)."""
        return any(pattern.search(match) for pattern in self.compiled_whitelist)

    def scan_file(self, file_path: Path):
        """Scan a single file for PII patterns."""
        # Skip the PII scanner itself to avoid false positives from pattern definitions
        if file_path.name == "pii_scanner.py":
            return

        try:
            with open(file_path, encoding='utf-8', errors='ignore') as f:
                for line_num, line in enumerate(f, 1):
                    # Skip lines that are clearly pattern definitions or examples in docs
                    if any(marker in line for marker in [
                        'PII_PATTERNS', 'ADDITIONAL_PATTERNS', '(?i)', 'r\'', 'r"',
                        'Pattern definitions', 'Example:', 'e.g.,'
                    ]):
                        continue

                    for pattern_name, pattern_re in self.compiled_patterns.items():
                        for match in pattern_re.finditer(line):
                            matched_text = match.group(0)

                            # Skip if whitelisted
                            if self.is_whitelisted(matched_text):
                                continue

                            # Redact sensitive parts of the match
                            redacted = self.redact_match(matched_text)

                            # Store finding
                            rel_path = file_path.relative_to(self.root_dir)
                            self.findings.append((
                                str(rel_path),
                                pattern_name,
                                line_num,
                                matched_text,
                                redacted
                            ))

        except Exception as e:
            print(f"Error scanning {file_path}: {e}", file=sys.stderr)

    def redact_match(self, text: str) -> str:
        """Redact sensitive parts of matched text for display."""
        if len(text) <= 8:
            return "[REDACTED]"

        # Show first and last 4 characters
        return f"{text[:4]}...{text[-4:]}"

    def scan_directory(self):
        """Recursively scan directory for PII."""
        print(f"🔍 Scanning directory: {self.root_dir}")
        print(f"📋 Using {len(ALL_PATTERNS)} detection patterns")
        print("")

        for file_path in self.root_dir.rglob("*"):
            if not file_path.is_file():
                continue

            if self.should_skip_file(file_path):
                continue

            self.scan_file(file_path)
            self.files_scanned += 1

            # Progress indicator
            if self.files_scanned % 100 == 0:
                print(f"  Scanned {self.files_scanned} files...", end='\r')

        print(f"  Scanned {self.files_scanned} files.    ")

    def print_findings(self):
        """Print findings in a readable format."""
        if not self.findings:
            print("")
            print("✅ No PII or sensitive data detected!")
            print("")
            return

        print("")
        print(f"❌ Found {len(self.findings)} potential security issues:")
        print("")

        # Group findings by file
        findings_by_file: dict[str, list] = {}
        for file_path, pattern, line_num, match, redacted in self.findings:
            if file_path not in findings_by_file:
                findings_by_file[file_path] = []
            findings_by_file[file_path].append((pattern, line_num, match, redacted))

        # Print grouped findings
        for file_path, file_findings in sorted(findings_by_file.items()):
            print(f"📄 {file_path}")
            for pattern, line_num, match, redacted in file_findings:
                print(f"   Line {line_num:4d}: {pattern:25s} → {redacted}")
            print("")

        print("=" * 80)
        print(f"Total findings: {len(self.findings)}")
        print("=" * 80)
        print("")
        print("⚠️  Please review these findings and remove any actual sensitive data.")
        print("")

    def generate_summary(self) -> dict:
        """Generate summary statistics."""
        pattern_counts: dict[str, int] = {}
        for _, pattern, _, _, _ in self.findings:
            pattern_counts[pattern] = pattern_counts.get(pattern, 0) + 1

        return {
            "files_scanned": self.files_scanned,
            "total_findings": len(self.findings),
            "findings_by_pattern": pattern_counts,
            "clean": len(self.findings) == 0
        }


def main():
    """Main entry point."""
    print("=" * 80)
    print("  PII Scanner - Security Data Leak Detection")
    print("=" * 80)
    print("")

    # Get directory to scan (default: current directory)
    scan_dir = sys.argv[1] if len(sys.argv) > 1 else "."

    # Run scanner
    scanner = PIIScanner(scan_dir)
    scanner.scan_directory()

    # Print findings
    scanner.print_findings()

    # Generate summary
    summary = scanner.generate_summary()

    if not summary["clean"]:
        print("Summary by pattern:")
        for pattern, count in sorted(
            summary["findings_by_pattern"].items(),
            key=lambda x: x[1],
            reverse=True
        ):
            print(f"  {pattern:30s}: {count:3d} occurrences")
        print("")

    # Exit with appropriate code
    exit_code = 0 if summary["clean"] else 1

    if exit_code == 0:
        print("✅ Security scan passed - no issues detected")
    else:
        print("❌ Security scan failed - please review and remediate findings")

    print("")
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
