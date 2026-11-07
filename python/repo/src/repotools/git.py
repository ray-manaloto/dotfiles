"""The text output of a git command, raising on a non-zero exit."""

import subprocess


def git(*args: str) -> str:
    return subprocess.run(["git", *args], capture_output=True, check=True, text=True).stdout
