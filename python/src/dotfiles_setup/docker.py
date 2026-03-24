"""Docker management module for dotfiles setup."""

from __future__ import annotations

import logging
import os
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


class DevContainerManager:
    """Manages the lifecycle of the devcontainer for local validation."""

    DEFAULT_IMAGE_NAME = "dotfiles-dev-local"
    CONTAINER_NAME = "dotfiles-dev-container"

    def __init__(self, project_root: Path, image_name: str | None = None) -> None:
        """Initialize the DevContainerManager.

        Args:
            project_root: The project root path.
            image_name: Optional image name.
        """
        self.project_root = project_root
        self.dockerfile = project_root / ".devcontainer" / "Dockerfile"
        # image_name priority: arg > env > default
        self.image_name = (
            image_name
            or os.environ.get("DOTFILES_IMAGE")
            or self.DEFAULT_IMAGE_NAME
        )

    def build(self) -> None:
        """Build the devcontainer using the official CLI."""
        logger.info("Building devcontainer image...")
        cmd = [
            "devcontainer", "build",
            "--workspace-folder", str(self.project_root),
            "--image-name", self.image_name
        ]
        subprocess.run(cmd, check=True)  # noqa: S603

    def run(self) -> None:
        """Start the devcontainer using the official CLI."""
        logger.info("Starting devcontainer...")
        # Ensure any old instances are gone
        subprocess.run(
            ["docker", "rm", "-f", self.CONTAINER_NAME],
            capture_output=True,
            check=False,
        )
        
        cmd = [
            "devcontainer", "up",
            "--workspace-folder", str(self.project_root),
            "--remove-existing-container"
        ]
        subprocess.run(cmd, check=True)  # noqa: S603

    def test(self) -> None:
        """Run functional tests inside the container using the official CLI."""
        logger.info("Running functional tests inside container...")
        user = os.environ.get("USER") or Path.home().name
        test_cmd = (
            f"/home/{user}/.local/share/mise/shims/uv run "
            "--with pytest pytest tests/test_bootstrap.py"
        )
        cmd = [
            "devcontainer", "exec",
            "--workspace-folder", str(self.project_root),
            "bash", "-c", test_cmd,
        ]
        subprocess.run(cmd, check=True)  # noqa: S603

    def stop(self) -> None:
        """Stop and remove the container."""
        logger.info("Stopping devcontainer...")
        subprocess.run(
            ["docker", "stop", self.CONTAINER_NAME],
            check=False,
        )  # noqa: S603
        subprocess.run(
            ["docker", "rm", self.CONTAINER_NAME],
            check=False,
        )  # noqa: S603
