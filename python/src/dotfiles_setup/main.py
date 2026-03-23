from __future__ import annotations

import argparse
import logging
import platform
import subprocess
import sys
from pathlib import Path
from typing import ClassVar

# Configure logging to stderr so stdout remains clean for command output
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s",
    stream=sys.stderr
)
logger = logging.getLogger(__name__)


class EnvironmentValidator:
    """Validates the execution environment."""

    SUPPORTED_OS: ClassVar[list[str]] = ["Linux", "Darwin"]
    SUPPORTED_ARCH: ClassVar[list[str]] = ["x86_64", "arm64", "aarch64"]

    @classmethod
    def validate(cls) -> None:
        """Validate the operating system and architecture.

        Raises:
            SystemExit: If the environment is unsupported.
        """
        current_os = platform.system()
        current_arch = platform.machine()

        if current_os not in cls.SUPPORTED_OS:
            raise SystemExit(f"Unsupported OS: {current_os}")

        if current_arch not in cls.SUPPORTED_ARCH:
            raise SystemExit(f"Unsupported Architecture: {current_arch}")


class ToolManager:
    """Manages tool installation and version querying."""

    @staticmethod
    def run_command(cmd: list[str], capture: bool = True) -> subprocess.CompletedProcess[str]:
        """Run a shell command and return the result.

        Args:
            cmd: The command and its arguments.
            capture: Whether to capture stdout/stderr.

        Returns:
            The completed process object.

        Raises:
            SystemExit: If the command fails.
        """
        try:
            return subprocess.run(
                cmd,
                check=True,
                capture_output=capture,
                text=True
            )
        except subprocess.CalledProcessError as e:
            if capture:
                logger.error("Error executing command %s: %s\n%s", " ".join(cmd), e.stdout or "", e.stderr or "")
            else:
                logger.error("Error executing command %s", " ".join(cmd))
            raise SystemExit(e.returncode) from e
        except FileNotFoundError:
            logger.error("Command not found: %s", cmd[0])
            raise SystemExit(1) from None

    def query_latest(self, tool: str) -> str:
        """Query the latest stable version of a tool using mise.

        Args:
            tool: The tool name.

        Returns:
            The latest version string.
        """
        result = self.run_command(["mise", "latest", tool])
        return result.stdout.strip()

    def install(self) -> None:
        """Execute mise install and pixi install."""
        logger.info("Installing tools with mise...")
        self.run_command(["mise", "install"], capture=False)

        logger.info("Installing tools with pixi...")
        self.run_command(["pixi", "install"], capture=False)


def main() -> None:
    """Main entry point for the dotfiles-setup CLI."""
    parser = argparse.ArgumentParser(
        description="Dotfiles setup orchestration library"
    )
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # query-latest command
    query_parser = subparsers.add_parser(
        "query-latest",
        help="Query latest stable version of a tool"
    )
    query_parser.add_argument("tool", help="Tool name (e.g., python, node, go)")

    # install command
    subparsers.add_parser(
        "install",
        help="Install all tools using mise and pixi"
    )

    # validate command
    subparsers.add_parser(
        "validate",
        help="Validate the current environment"
    )

    # docker subcommands
    docker_parser = subparsers.add_parser("docker", help="Manage devcontainer for validation")
    docker_subparsers = docker_parser.add_subparsers(dest="docker_command", help="Docker commands")
    docker_subparsers.add_parser("build", help="Build local AMD64 image")
    docker_subparsers.add_parser("up", help="Start the devcontainer")
    docker_subparsers.add_parser("test", help="Run tests inside the container")
    docker_subparsers.add_parser("down", help="Stop and remove the container")

    # version command
    subparsers.add_parser(
        "version",
        help="Show the version of the library"
    )

    args = parser.parse_args()

    manager = ToolManager()
    project_root = Path(__file__).parent.parent.parent.parent
    docker_manager = None # Lazy load

    if args.command == "validate":
        EnvironmentValidator.validate()
        logger.info("Environment is valid.")
    elif args.command == "docker":
        from dotfiles_setup.docker import DevContainerManager
        docker_manager = DevContainerManager(project_root)
        if args.docker_command == "build":
            docker_manager.build()
        elif args.docker_command == "up":
            docker_manager.run()
        elif args.docker_command == "test":
            docker_manager.test()
        elif args.docker_command == "down":
            docker_manager.stop()
    elif args.command == "version":
        sys.stdout.write("0.1.0\n")
    elif args.command == "query-latest":
        EnvironmentValidator.validate()
        latest = manager.query_latest(args.tool)
        sys.stdout.write(f"{latest}\n")
    elif args.command == "install":
        EnvironmentValidator.validate()
        manager.install()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
