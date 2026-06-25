"""
ReflectAI Version Management

Centralized version management using pyproject.toml as single source of truth.
Provides consistent versioning across the entire application
with git information.

Version is read from pyproject.toml and can be
overridden by APP_VERSION env var.
Git commit and branch information is automatically included when available.
"""

import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


# Single source of truth: pyproject.toml
def _read_version_from_pyproject() -> str:
    """Read version from pyproject.toml."""
    try:
        # Find pyproject.toml in project root
        current_file = Path(__file__)
        project_root = current_file.parent.parent
        pyproject_path = project_root / "pyproject.toml"

        if pyproject_path.exists():
            with open(pyproject_path) as f:
                for line in f:
                    if line.startswith("version"):
                        # Extract version from: version = "0.1.2-alpha"
                        return line.split("=")[1].strip().strip('"').strip("'")

        # Fallback if pyproject.toml not found
        return "0.1.2-alpha"
    except Exception:
        return "0.1.2-alpha"


def get_git_commit() -> str:
    """Get current git commit hash (short form)."""
    try:
        # Try to get from environment first (useful for CI/CD)
        if "GIT_COMMIT" in os.environ:
            commit = os.environ["GIT_COMMIT"]
            return commit[:7] if len(commit) > 7 else commit

        # Get from git command
        result = subprocess.run(
            ["git", "rev-parse", "--short=7", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
            timeout=2,
            cwd=Path(__file__).parent.parent,
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        return "unknown"


def get_git_branch() -> str:
    """Get current git branch name."""
    try:
        # Try to get from environment first (useful for CI/CD)
        if "GIT_BRANCH" in os.environ:
            return os.environ["GIT_BRANCH"]

        # Get from git command
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True,
            text=True,
            check=True,
            timeout=2,
            cwd=Path(__file__).parent.parent,
        )
        branch = result.stdout.strip()
        return branch if branch else "detached"
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        return "unknown"


def get_git_dirty_status() -> bool:
    """Check if working directory has uncommitted changes."""
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            check=True,
            timeout=2,
            cwd=Path(__file__).parent.parent,
        )
        return bool(result.stdout.strip())
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        return False


def get_base_version() -> str:
    """
    Get base version from pyproject.toml or environment.

    Priority:
    1. APP_VERSION environment variable (for production builds)
    2. pyproject.toml [project] version
    3. Fallback: "0.1.2-alpha"
    """
    # Allow environment override for production builds
    if "APP_VERSION" in os.environ:
        return os.environ["APP_VERSION"]

    # Read from pyproject.toml (single source of truth)
    return _read_version_from_pyproject()


# Initialize version information at module load
__version__ = get_base_version()
__git_commit__ = get_git_commit()
__git_branch__ = get_git_branch()
__git_dirty__ = get_git_dirty_status()
__build_date__ = datetime.now(UTC).isoformat() + "Z"


def get_version_string() -> str:
    """
    Get formatted version string with git info.

    Format:
    - Clean: "0.1.2-alpha+a1b2c3d"
    - Dirty: "0.1.2-alpha+a1b2c3d.dirty"
    - No git: "0.1.2-alpha"
    """
    if __git_commit__ != "unknown":
        version = f"{__version__}+{__git_commit__}"
        if __git_dirty__:
            version += ".dirty"
        return version
    return __version__


def get_short_version() -> str:
    """Get short version without git commit info."""
    return __version__


def get_version_info() -> dict[str, Any]:
    """
    Get comprehensive version information for API responses and logging.

    Returns:
        Dictionary with version, git info, build metadata
    """
    return {
        "version": __version__,
        "version_full": get_version_string(),
        "git_commit": __git_commit__,
        "git_branch": __git_branch__,
        "git_dirty": __git_dirty__,
        "build_date": __build_date__,
        "environment": os.environ.get("ENVIRONMENT", "development"),
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
    }


# Legacy compatibility
def get_version() -> str:
    """
    Legacy function for compatibility.
    Returns full version string with git info.
    """
    return get_version_string()
