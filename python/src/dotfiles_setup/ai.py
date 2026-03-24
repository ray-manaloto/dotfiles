"""AI toolchain orchestration module."""

from __future__ import annotations

import logging
import subprocess
from typing import Protocol

from dotfiles_setup.audit import ToolManager

logger = logging.getLogger(__name__)


class AIOrchestratorInterface(Protocol):
    """Interface for AI toolchain orchestration."""

    def setup_claude(self) -> None:
        """Install Claude Code using the official installer.

        This method executes the official curl-based installation script
        in a non-interactive manner.
        """
        ...

    def setup_extensions(self) -> None:
        """Install AI-related extensions.

        This method handles the installation of GitHub extensions
        and other AI-related tools.
        """
        ...

    def run_all(self) -> None:
        """Run all AI setup steps.

        This method orchestrates the full AI toolchain setup process.
        """
        ...


class AIOrchestrator:
    """Orchestrates the setup of AI tools and extensions.

    This class implements the AIOrchestratorInterface and provides
    concrete logic for installing Claude Code and other AI extensions.
    """

    def __init__(self) -> None:
        """Initialize the AIOrchestrator."""
        self.tool_manager = ToolManager()

    def setup_claude(self) -> None:
        """Install Claude Code using the official installer.

        Executes: curl -fsSL https://claude.ai/install.sh | bash
        """
        logger.info("Installing Claude Code...")
        # We use bash -c to pipe curl to bash, following the Zero-Bash rule
        # by encapsulating it within Python's subprocess logic.
        cmd = ["bash", "-c", "curl -fsSL https://claude.ai/install.sh | bash"]
        self.tool_manager.run_command(cmd, capture=False)

    def setup_extensions(self) -> None:
        """Install AI-related extensions.

        Currently handles gh-copilot if needed in the future.
        """
        logger.info("Setting up AI extensions...")
        # Placeholder for future extensions like gh-copilot
        # self.tool_manager.run_command(["gh", "extension", "install", "github/gh-copilot"], capture=False)
        pass

    def run_all(self) -> None:
        """Run all AI setup steps."""
        self.setup_claude()
        self.setup_extensions()
        logger.info("AI toolchain setup complete.")
