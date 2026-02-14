"""
Utilities Module

Common utilities for logging, command execution, and file operations.
"""

import os
import re
import logging
import subprocess
from typing import Optional, List, Pattern
from datetime import datetime
from pathlib import Path

from . import config


def setup_logging(log_dir: str = config.LOG_DIRECTORY) -> logging.Logger:
    """
    Configure structured logging with timestamps to file and console.
    
    Args:
        log_dir: Directory for log files
        
    Returns:
        Configured logger instance
    """
    # Create log directory if it doesn't exist
    ensure_directory(log_dir)
    
    # Generate log filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(log_dir, f"migration_{timestamp}.log")
    
    # Configure root logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # Remove existing handlers
    logger.handlers.clear()
    
    # File handler with detailed format
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        config.LOG_FORMAT,
        datefmt=config.LOG_DATE_FORMAT
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    
    # Console handler with simpler format
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter(
        '%(levelname)s - %(message)s'
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    logger.info(f"Logging initialized. Log file: {log_file}")
    
    return logger


def sanitize_log_message(message: str, patterns: Optional[List[str]] = None) -> str:
    """
    Redact sensitive values from log output using regex patterns.
    
    Args:
        message: Log message to sanitize
        patterns: List of regex patterns to redact (uses config.SENSITIVE_PATTERNS if None)
        
    Returns:
        Sanitized message with sensitive data redacted
    """
    if patterns is None:
        patterns = config.SENSITIVE_PATTERNS
    
    sanitized = message
    
    for pattern in patterns:
        try:
            # Replace matches with redacted placeholder
            sanitized = re.sub(pattern, '[REDACTED]', sanitized)
        except re.error as e:
            logging.warning(f"Invalid regex pattern: {pattern} - {e}")
    
    return sanitized


def run_command(
    cmd: List[str],
    cwd: Optional[str] = None,
    dry_run: bool = False,
    timeout: int = config.DEFAULT_TIMEOUT,
    env: Optional[dict] = None
) -> Optional[subprocess.CompletedProcess]:
    """
    Execute a subprocess command with timeout and error handling.
    
    Automatically sanitizes sensitive data from output.
    
    Args:
        cmd: Command and arguments as list
        cwd: Working directory for command execution
        dry_run: If True, log command but don't execute
        timeout: Command timeout in seconds
        env: Environment variables (uses os.environ if None)
        
    Returns:
        CompletedProcess instance, or None on error
    """
    logger = logging.getLogger(__name__)
    
    cmd_str = ' '.join(cmd)
    logger.debug(f"Running command: {cmd_str}")
    
    if dry_run:
        logger.info(f"[DRY RUN] Would execute: {cmd_str}")
        return None
    
    try:
        if env is None:
            env = os.environ.copy()
        
        result = subprocess.run(
            cmd,
            cwd=cwd,
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        
        # Sanitize output before logging
        if result.stdout:
            sanitized_stdout = sanitize_log_message(result.stdout)
            if sanitized_stdout.strip():
                logger.debug(f"Command output: {sanitized_stdout}")
        
        if result.stderr:
            sanitized_stderr = sanitize_log_message(result.stderr)
            if sanitized_stderr.strip():
                if result.returncode != 0:
                    logger.error(f"Command error: {sanitized_stderr}")
                else:
                    logger.debug(f"Command stderr: {sanitized_stderr}")
        
        if result.returncode != 0:
            logger.warning(f"Command failed with exit code {result.returncode}")
        
        return result
        
    except subprocess.TimeoutExpired:
        logger.error(f"Command timed out after {timeout} seconds: {cmd_str}")
        return None
    except FileNotFoundError:
        logger.error(f"Command not found: {cmd[0]}")
        return None
    except Exception as e:
        logger.error(f"Error executing command: {e}")
        return None


def ensure_directory(path: str) -> bool:
    """
    Create directory if it doesn't exist.
    
    Args:
        path: Directory path to create
        
    Returns:
        True if directory exists or was created, False on error
    """
    try:
        os.makedirs(path, exist_ok=True)
        return True
    except Exception as e:
        logging.error(f"Error creating directory {path}: {e}")
        return False


def read_file(filepath: str) -> Optional[str]:
    """
    Read file contents safely.
    
    Args:
        filepath: Path to file
        
    Returns:
        File contents as string, or None on error
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        logging.error(f"Error reading file {filepath}: {e}")
        return None


def write_file(filepath: str, content: str) -> bool:
    """
    Write content to file safely.
    
    Args:
        filepath: Path to file
        content: Content to write
        
    Returns:
        True if successful, False on error
    """
    try:
        # Ensure parent directory exists
        parent_dir = os.path.dirname(filepath)
        if parent_dir:
            ensure_directory(parent_dir)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    except Exception as e:
        logging.error(f"Error writing file {filepath}: {e}")
        return False


def copy_file(src: str, dst: str) -> bool:
    """
    Copy file from source to destination.
    
    Args:
        src: Source file path
        dst: Destination file path
        
    Returns:
        True if successful, False on error
    """
    try:
        import shutil
        shutil.copy2(src, dst)
        return True
    except Exception as e:
        logging.error(f"Error copying file from {src} to {dst}: {e}")
        return False


def find_files(directory: str, pattern: str) -> List[str]:
    """
    Find files matching a glob pattern.
    
    Args:
        directory: Directory to search
        pattern: Glob pattern (e.g., "*.tf")
        
    Returns:
        List of matching file paths
    """
    try:
        path = Path(directory)
        return [str(f) for f in path.rglob(pattern)]
    except Exception as e:
        logging.error(f"Error finding files in {directory}: {e}")
        return []


def format_duration(seconds: float) -> str:
    """
    Format duration in seconds to human-readable string.
    
    Args:
        seconds: Duration in seconds
        
    Returns:
        Formatted duration string (e.g., "2m 30s")
    """
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}m {secs}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}h {minutes}m"


def confirm_action(prompt: str, default: bool = False) -> bool:
    """
    Prompt user for confirmation.
    
    Args:
        prompt: Confirmation prompt
        default: Default value if user just presses Enter
        
    Returns:
        True if user confirms, False otherwise
    """
    default_str = "Y/n" if default else "y/N"
    response = input(f"{prompt} [{default_str}]: ").strip().lower()
    
    if not response:
        return default
    
    return response in ['y', 'yes']


def parse_list_argument(arg: str) -> List[str]:
    """
    Parse comma-separated list argument.
    
    Args:
        arg: Comma-separated string
        
    Returns:
        List of trimmed items
    """
    if not arg:
        return []
    
    return [item.strip() for item in arg.split(',') if item.strip()]


def get_repo_name_from_path(path: str) -> str:
    """
    Extract repository name from path.
    
    Args:
        path: Repository path
        
    Returns:
        Repository name (last path component)
    """
    return os.path.basename(os.path.normpath(path))


def is_git_repository(path: str) -> bool:
    """
    Check if path is a Git repository.
    
    Args:
        path: Path to check
        
    Returns:
        True if path is a Git repository, False otherwise
    """
    git_dir = os.path.join(path, '.git')
    return os.path.isdir(git_dir)


def get_file_size(filepath: str) -> int:
    """
    Get file size in bytes.
    
    Args:
        filepath: Path to file
        
    Returns:
        File size in bytes, or 0 if file doesn't exist
    """
    try:
        return os.path.getsize(filepath)
    except:
        return 0


def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human-readable format.
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        Formatted size string (e.g., "1.5 MB")
    """
    size = float(size_bytes)
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} PB"


class ProgressTracker:
    """Track progress of multi-step operations."""
    
    def __init__(self, total_steps: int):
        """
        Initialize progress tracker.
        
        Args:
            total_steps: Total number of steps
        """
        self.total_steps = total_steps
        self.current_step = 0
        self.start_time = datetime.now()
        self.logger = logging.getLogger(__name__)
    
    def step(self, message: str):
        """
        Advance to next step.
        
        Args:
            message: Description of current step
        """
        self.current_step += 1
        elapsed = (datetime.now() - self.start_time).total_seconds()
        self.logger.info(
            f"[{self.current_step}/{self.total_steps}] {message} "
            f"(elapsed: {format_duration(elapsed)})"
        )
    
    def complete(self):
        """Mark progress as complete."""
        elapsed = (datetime.now() - self.start_time).total_seconds()
        self.logger.info(
            f"✅ Completed all {self.total_steps} steps in {format_duration(elapsed)}"
        )
