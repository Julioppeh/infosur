"""Version and build information for Info Sur."""
import subprocess
from datetime import datetime, timezone


def get_version() -> str:
    """Get application version."""
    return "1.0.0"


def get_compile_id() -> str:
    """Get compile/build ID from git commit hash and timestamp."""
    try:
        # Try to get git commit hash
        commit_hash = subprocess.check_output(
            ['git', 'rev-parse', '--short', 'HEAD'],
            stderr=subprocess.DEVNULL,
            text=True
        ).strip()

        # Get commit timestamp
        commit_time = subprocess.check_output(
            ['git', 'log', '-1', '--format=%ct'],
            stderr=subprocess.DEVNULL,
            text=True
        ).strip()

        return f"build-{commit_hash}-{commit_time}"
    except (subprocess.CalledProcessError, FileNotFoundError):
        # Fallback to timestamp if git is not available
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        return f"build-{timestamp}"


def get_full_version() -> str:
    """Get full version string with compile ID."""
    return f"v{get_version()} ({get_compile_id()})"
