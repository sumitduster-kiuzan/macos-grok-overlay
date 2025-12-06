import subprocess
import sys
from pathlib import Path

from .constants import APP_TITLE


TASK_NAME = f"macos_{APP_TITLE.lower()}_overlay"


def _build_command() -> str:
    """
    Build the command that launches the overlay. This mirrors the macOS launcher
    so packaged executables and pip installations behave the same.
    """
    if getattr(sys, "frozen", False):
        executable = Path(sys.argv[0]).resolve()
        return f'"{executable}"'
    python = Path(sys.executable).resolve()
    module = f"macos_{APP_TITLE.lower()}_overlay"
    return f'"{python}" -m {module}'


def install_startup() -> bool:
    """
    Create (or replace) a Task Scheduler entry that launches the overlay when
    the current user logs in.
    """
    command = _build_command()
    result = subprocess.run(
        [
            "schtasks",
            "/Create",
            "/TN",
            TASK_NAME,
            "/TR",
            command,
            "/SC",
            "ONLOGON",
            "/RL",
            "LIMITED",
            "/F",
        ],
        capture_output=True,
        text=True,
        shell=False,
    )
    if result.returncode != 0:
        print("Failed to register startup task.")
        if result.stderr:
            print(result.stderr.strip())
        return False
    print(f"Installed Windows startup task '{TASK_NAME}'.")
    return True


def uninstall_startup() -> bool:
    """
    Remove the scheduled task that auto-starts the overlay.
    """
    result = subprocess.run(
        ["schtasks", "/Delete", "/TN", TASK_NAME, "/F"],
        capture_output=True,
        text=True,
        shell=False,
    )
    if result.returncode != 0:
        stderr = result.stderr or ""
        if "ERROR: The system cannot find the file specified." in stderr:
            print("Startup task not found. Nothing to remove.")
            return False
        print("Failed to delete startup task.")
        if stderr:
            print(stderr.strip())
        return False
    print(f"Removed Windows startup task '{TASK_NAME}'.")
    return True
