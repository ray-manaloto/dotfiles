from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


class DevContainerManager:
    """Manages the lifecycle of the devcontainer for local validation."""

    DEFAULT_IMAGE_NAME = "dotfiles-dev-local"
    CONTAINER_NAME = "dotfiles-dev-container"

    def __init__(self, project_root: Path, image_name: str | None = None):
        self.project_root = project_root
        self.dockerfile = project_root / ".devcontainer" / "Dockerfile"
        # image_name priority: arg > env > default
        import os
        self.image_name = image_name or os.environ.get("DOTFILES_IMAGE") or self.DEFAULT_IMAGE_NAME

    def build(self) -> None:
        """Build the AMD64 image locally."""
        logger.info("Building AMD64 devcontainer image...")
        cmd = [
            "docker", "build",
            "--platform", "linux/amd64",
            "-t", self.image_name,
            "-f", str(self.dockerfile),
            str(self.project_root)
        ]
        subprocess.run(cmd, check=True)

    def run(self) -> None:
        """Start the devcontainer in the background."""
        logger.info("Starting devcontainer...")
        # Remove old instance if exists
        subprocess.run(["docker", "rm", "-f", self.CONTAINER_NAME], capture_output=True)
        
        cmd = [
            "docker", "run", "-d",
            "--name", self.CONTAINER_NAME,
            "--platform", "linux/amd64",
            "-v", f"{self.project_root}:/home/vscode/.local/share/chezmoi",
            self.image_name,
            "tail", "-f", "/dev/null"
        ]
        subprocess.run(cmd, check=True)

    def test(self) -> None:
        """Run functional tests inside the container."""
        logger.info("Running functional tests inside container...")
        cmd = [
            "docker", "exec",
            "-u", "vscode",
            "-w", "/home/vscode/.local/share/chezmoi",
            self.CONTAINER_NAME,
            "bash", "-c", "/home/vscode/.local/share/mise/shims/uv run --with pytest pytest tests/test_bootstrap.py"
        ]
        subprocess.run(cmd, check=True)

    def stop(self) -> None:
        """Stop and remove the container."""
        logger.info("Stopping devcontainer...")
        subprocess.run(["docker", "stop", self.CONTAINER_NAME], check=True)
        subprocess.run(["docker", "rm", self.CONTAINER_NAME], check=True)
