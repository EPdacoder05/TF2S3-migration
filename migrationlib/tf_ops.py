"""
Terraform Operations Module

Handles all Terraform-specific operations including backend configuration updates,
module source transformations, and version validation.
"""

import os
import re
import logging
from typing import List, Dict, Optional, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)


def update_backend_config(repo_path: str, bucket: str, region: str, repo_name: str) -> bool:
    """
    Update Terraform backend configuration from cloud to S3.
    
    Replaces cloud {} block with backend "s3" {} configuration in main.tf or providers.tf.
    
    Args:
        repo_path: Path to the repository
        bucket: S3 bucket name for state storage
        region: AWS region
        repo_name: Repository name (used for S3 key path)
        
    Returns:
        True if backend was updated, False otherwise
    """
    logger.info(f"Updating backend configuration for {repo_name}")
    
    # Look for terraform configuration files
    tf_files = [
        os.path.join(repo_path, "main.tf"),
        os.path.join(repo_path, "providers.tf"),
        os.path.join(repo_path, "backend.tf"),
    ]
    
    backend_updated = False
    
    for tf_file in tf_files:
        if not os.path.exists(tf_file):
            continue
            
        try:
            with open(tf_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check if this file contains a cloud block
            if not re.search(r'cloud\s*\{', content):
                continue
            
            logger.info(f"Found cloud backend in {tf_file}")
            
            # Replace cloud block with S3 backend
            # Match terraform { ... cloud { ... } ... } block
            pattern = r'(terraform\s*\{[^}]*)(cloud\s*\{[^}]*\})'
            
            # S3 backend configuration
            s3_backend = f'''backend "s3" {{
    bucket         = "{bucket}"
    key            = "{repo_name}/terraform.tfstate"
    region         = "{region}"
    dynamodb_table = "terraform-state-lock"
    encrypt        = true
  }}'''
            
            # Replace cloud block with S3 backend
            new_content = re.sub(pattern, rf'\1{s3_backend}', content, flags=re.DOTALL)
            
            if new_content != content:
                with open(tf_file, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                logger.info(f"✅ Updated backend configuration in {tf_file}")
                backend_updated = True
            
        except Exception as e:
            logger.error(f"Error updating backend in {tf_file}: {e}")
            
    if not backend_updated:
        logger.warning("No cloud backend found to update")
        
    return backend_updated


def update_module_sources(repo_path: str, org: str) -> int:
    """
    Convert Terraform Cloud module sources to Git-based sources.
    
    Transforms sources from:
      app.terraform.io/ORG/module-name/provider
    To:
      git::https://github.com/ORG/terraform-PROVIDER-module-name?ref=vX.Y.Z
    
    Also removes standalone version = "X.Y.Z" statements that followed module blocks.
    
    Args:
        repo_path: Path to the repository
        org: GitHub organization name
        
    Returns:
        Number of module sources updated
    """
    logger.info(f"Updating module sources to Git format for org: {org}")
    
    update_count = 0
    tf_files = list(Path(repo_path).rglob("*.tf"))
    
    for tf_file in tf_files:
        try:
            with open(tf_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            
            # Pattern 1: Match TFC registry sources
            # Example: app.terraform.io/your-org/project-factory/aws
            tfc_pattern = r'source\s*=\s*"app\.terraform\.io/([^/]+)/([^/]+)/([^"]+)"'
            
            def replace_source(match):
                nonlocal update_count
                tfc_org = match.group(1)
                module_name = match.group(2)
                provider = match.group(3)
                
                # Look for version in the surrounding context
                # Search for version = "X.Y.Z" within the next 200 characters
                start_pos = match.end()
                context = content[start_pos:start_pos + 200]
                version_match = re.search(r'version\s*=\s*"([^"]+)"', context)
                
                version = version_match.group(1) if version_match else "main"
                ref = f"v{version}" if not version.startswith("v") and version != "main" else version
                
                # Construct Git source URL
                git_source = f'source = "git::https://github.com/{org}/terraform-{provider}-{module_name}?ref={ref}"'
                
                update_count += 1
                logger.debug(f"Converting module source: {module_name} -> Git ref {ref}")
                
                return git_source
            
            # Replace TFC sources with Git sources
            content = re.sub(tfc_pattern, replace_source, content)
            
            # Pattern 2: Remove standalone version statements after module blocks
            # This removes version = "X.Y.Z" lines that appear after module { ... source = ... }
            # We need to be careful to only remove versions related to modules, not provider versions
            
            # First, let's identify module blocks and remove their version statements
            module_pattern = r'(module\s+"[^"]+"\s*\{[^}]*source\s*=\s*"git::[^"]+[^}]*?)(\s*version\s*=\s*"[^"]+"\s*)'
            content = re.sub(module_pattern, r'\1', content, flags=re.DOTALL)
            
            # Write back if changed
            if content != original_content:
                with open(tf_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                logger.info(f"✅ Updated {tf_file.name}")
                
        except Exception as e:
            logger.error(f"Error updating module sources in {tf_file}: {e}")
    
    logger.info(f"Updated {update_count} module sources")
    return update_count


def validate_module_versions(repo_path: str, required_versions: Dict[str, Dict[str, Optional[str]]]) -> List[str]:
    """
    Validate that Terraform modules meet minimum version requirements.
    
    Args:
        repo_path: Path to the repository
        required_versions: Dict of module names to version requirements
                          Format: {"module-name": {"min": "1.0.0", "max": "2.0.0"}}
        
    Returns:
        List of validation error messages (empty if all valid)
    """
    logger.info("Validating module versions")
    
    errors = []
    tf_files = list(Path(repo_path).rglob("*.tf"))
    
    for tf_file in tf_files:
        try:
            with open(tf_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract module declarations with sources
            module_pattern = r'module\s+"([^"]+)"\s*\{[^}]*source\s*=\s*"[^"]*?/([^/?]+)(?:\?ref=v?([^"]+))?[^}]*\}'
            
            for match in re.finditer(module_pattern, content, re.DOTALL):
                module_instance = match.group(1)
                module_name = match.group(2)
                version = match.group(3) if match.group(3) else None
                
                # Check if this module has version requirements
                if module_name in required_versions:
                    req = required_versions[module_name]
                    min_version = req.get("min")
                    max_version = req.get("max")
                    
                    if not version:
                        errors.append(
                            f"Module '{module_instance}' ({module_name}) in {tf_file.name} "
                            f"has no version specified, but requires minimum version {min_version}"
                        )
                        continue
                    
                    # Parse versions for comparison
                    try:
                        current = parse_version(version)
                        
                        if min_version and parse_version(min_version) > current:
                            errors.append(
                                f"Module '{module_instance}' ({module_name}) in {tf_file.name} "
                                f"version {version} is below minimum required {min_version}"
                            )
                        
                        if max_version and parse_version(max_version) < current:
                            errors.append(
                                f"Module '{module_instance}' ({module_name}) in {tf_file.name} "
                                f"version {version} exceeds maximum allowed {max_version}"
                            )
                    except ValueError as e:
                        errors.append(f"Invalid version format for module '{module_instance}': {e}")
                        
        except Exception as e:
            logger.error(f"Error validating versions in {tf_file}: {e}")
    
    if errors:
        logger.warning(f"Found {len(errors)} version validation errors")
        for error in errors:
            logger.warning(f"  - {error}")
    else:
        logger.info("✅ All module versions validated successfully")
    
    return errors


def parse_version(version_str: str) -> Tuple[int, ...]:
    """
    Parse a semantic version string into a tuple for comparison.
    
    Args:
        version_str: Version string (e.g., "1.2.3", "v1.2.3")
        
    Returns:
        Tuple of version components (e.g., (1, 2, 3))
    """
    # Remove 'v' prefix if present
    version_str = version_str.lstrip('v')
    
    # Split on dots and convert to integers
    try:
        parts = [int(x) for x in version_str.split('.')]
        return tuple(parts)
    except ValueError:
        raise ValueError(f"Invalid version format: {version_str}")


def list_terraform_files(repo_path: str) -> List[str]:
    """
    List all Terraform files in the repository.
    
    Args:
        repo_path: Path to the repository
        
    Returns:
        List of Terraform file paths
    """
    tf_files = []
    for root, dirs, files in os.walk(repo_path):
        # Skip .terraform directories
        dirs[:] = [d for d in dirs if d != '.terraform']
        
        for file in files:
            if file.endswith('.tf'):
                tf_files.append(os.path.join(root, file))
    
    return tf_files


def validate_terraform_syntax(repo_path: str) -> bool:
    """
    Validate Terraform configuration syntax.
    
    Args:
        repo_path: Path to the repository
        
    Returns:
        True if syntax is valid, False otherwise
    """
    logger.info("Validating Terraform syntax")
    
    try:
        import subprocess
        result = subprocess.run(
            ["terraform", "validate", "-no-color"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            logger.info("✅ Terraform syntax is valid")
            return True
        else:
            logger.error(f"Terraform validation failed: {result.stderr}")
            return False
            
    except FileNotFoundError:
        logger.warning("Terraform CLI not found, skipping syntax validation")
        return True  # Don't fail if terraform not installed
    except Exception as e:
        logger.error(f"Error validating Terraform syntax: {e}")
        return False
