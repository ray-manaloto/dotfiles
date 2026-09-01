# Copyright (c) 2026 Raymond Manaloto
"""Docker and devcontainer runtime management for dotfiles setup.

R2 outbound SSH agent forwarding now relies on Docker Desktop's native
``/run/host-services/ssh-auth.sock`` magic socket (bind-mounted in
``.devcontainer/devcontainer.json``). The custom Python TCP/unix-socket
proxy that previously implemented R2 was deleted in issue #77 stage 2.

The only host-side runtime preparation that remains is staging
``authorized_keys`` for the container's R1 inbound sshd login. See
``.devcontainer/AGENTS.md`` SSH section for the full picture.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path

from dotfiles_setup.config import (
    DotfilesConfig,
    host_state_dir,
)
from dotfiles_setup.devcontainer_names import (
    DevcontainerNames,
    doppler_env_filename,
    resolve_names,
    teardown_container_ids,
)
from dotfiles_setup.platform_target import resolve_platform

logger = logging.getLogger(__name__)

HOST_AUTHORIZED_KEYS_FILE = "authorized_keys"

#: Doppler defaults, matching the values ``initializeCommand`` used inline
#: before #893 moved the download here. A clone overrides either through
#: ``mise.local.toml`` — which is exactly why the output path must be scoped.
DEFAULT_DOPPLER_PROJECT = "dotfiles"
DEFAULT_DOPPLER_CONFIG = "dev_personal"

#: How long the secrets download may take before it is treated as a failure.
_DOPPLER_TIMEOUT_S = 120.0


class SecretsDownloadError(RuntimeError):
    """The Doppler download did not produce a usable env file.

    The message is built here rather than at the raise sites so the two
    failure modes read the same way in a bring-up log, and so a caller never
    has to compose one.
    """

    def __init__(self, project: str, config: str, reason: str) -> None:
        """Build the message from the project, config, and failure reason."""
        super().__init__(
            f"doppler secrets download for {project}/{config} failed: {reason}"
        )


def doppler_env_file(names: DevcontainerNames, state_dir: Path) -> Path:
    """This workspace+architecture's secrets env file (#893).

    Before #893 every clone wrote ``<state_dir>/doppler.env`` — one literal
    path under ``$HOME``, with no workspace or architecture in it. Two
    concurrent ``mise run up`` runs therefore raced between the write and
    ``runArgs --env-file`` reading it, and ``DOPPLER_PROJECT`` /
    ``DOPPLER_CONFIG`` are documented PER-CLONE overrides — so the loser
    started with the winner's secrets, silently and with no error.

    Scoping by architecture as well as workspace is deliberate even though a
    clone's Doppler project does not vary by arch: bringing both
    architectures of ONE workspace up concurrently is a supported flow
    (#677), and giving each its own path makes that race structurally
    impossible rather than merely atomic. It also matches how the home
    volume is already named.
    """
    return state_dir / doppler_env_filename(names)


def stage_host_secrets() -> Path:
    """Write this workspace's secrets env file, and return its path.

    #893 moved the Doppler download out of the ``initializeCommand`` shell
    chain in ``devcontainer.json``. It was an unlocked ``>``-truncate to one
    host-wide path, so it needed both a per-workspace path and an atomic
    write — more logic than belongs in a JSON string
    (``.claude/rules/zero-bash-logic.md``).

    Raises :class:`SecretsDownloadError` if the secrets are unusable, which
    fails the bring-up exactly as the old ``&& [ -s ... ] &&`` guard did.
    """
    state_dir = host_state_dir()
    state_dir.mkdir(parents=True, exist_ok=True)
    return download_doppler_env(resolve_names(), state_dir)


def download_doppler_env(
    names: DevcontainerNames, state_dir: Path, env: dict[str, str] | None = None
) -> Path:
    """Write this workspace's secrets env file atomically, and return it.

    Raises :class:`SecretsDownloadError` when the download fails or produces
    an empty file. Before #893 the ``initializeCommand`` shell chain guarded
    this with ``&& [ -s ... ] &&``, so an empty download aborted the bring-up;
    that guard is reproduced here rather than dropped — an empty env file
    reaching ``--env-file`` is a container with no secrets and no complaint.
    """
    source = os.environ if env is None else env
    project = source.get("DOPPLER_PROJECT") or DEFAULT_DOPPLER_PROJECT
    config = source.get("DOPPLER_CONFIG") or DEFAULT_DOPPLER_CONFIG
    result = subprocess.run(
        [
            "doppler",
            "secrets",
            "download",
            "--format",
            "docker",
            "--no-file",
            "--project",
            project,
            "--config",
            config,
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=_DOPPLER_TIMEOUT_S,
    )
    if result.returncode != 0:
        raise SecretsDownloadError(
            project, config, f"rc={result.returncode}: {result.stderr.strip()}"
        )
    if not result.stdout.strip():
        raise SecretsDownloadError(project, config, "it returned no secrets")

    path = doppler_env_file(names, state_dir)
    # Write-then-rename: the state directory is shared by every clone, and a
    # reader must see a whole file or the previous one, never a partial write.
    tmp = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    try:
        # Born 0o600: create-then-chmod leaves a umask-mode window where
        # another local reader could open the secrets before chmod runs.
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w") as handle:
            handle.write(result.stdout)
        tmp.replace(path)
    finally:
        tmp.unlink(missing_ok=True)
    return path


def _agent_public_keys(env: dict[str, str]) -> list[str]:
    """Collect public keys from the SSH agent selected by ``env``."""
    result = subprocess.run(
        ["ssh-add", "-L"],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    if result.returncode != 0:
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def _ssh_agent_environment() -> dict[str, str]:
    """Resolve an environment with a working agent, including macOS launchd."""
    env = os.environ.copy()
    if _agent_public_keys(env):
        return env
    if sys.platform != "darwin":
        msg = "No SSH agent public keys available"
        raise RuntimeError(msg)

    result = subprocess.run(
        ["/bin/launchctl", "getenv", "SSH_AUTH_SOCK"],
        capture_output=True,
        text=True,
        check=False,
    )
    socket_lines = result.stdout.splitlines()
    if result.returncode != 0 or len(socket_lines) != 1:
        msg = "No SSH agent public keys available"
        raise RuntimeError(msg)
    socket_path = socket_lines[0].strip()
    if not socket_path or not Path(socket_path).is_absolute():
        msg = "No SSH agent public keys available"
        raise RuntimeError(msg)

    launchd_env = env.copy()
    launchd_env["SSH_AUTH_SOCK"] = socket_path
    if not _agent_public_keys(launchd_env):
        msg = "No SSH agent public keys available"
        raise RuntimeError(msg)
    return launchd_env


def _write_host_authorized_keys(state_dir: Path, public_keys: list[str]) -> None:
    """Persist authorized keys for the container to consume."""
    unique_keys = list(dict.fromkeys(public_keys))
    auth_keys_path = state_dir / HOST_AUTHORIZED_KEYS_FILE
    content = "\n".join(unique_keys)
    if content:
        content += "\n"
    auth_keys_path.write_text(content, encoding="utf-8")
    auth_keys_path.chmod(0o600)


def initialize_host_ssh_runtime() -> dict[str, str]:
    """Stage host-side authorized_keys for the container's R1 sshd login.

    Docker Desktop's native ``/run/host-services/ssh-auth.sock`` handles
    R2 outbound agent forwarding directly via the bind mount in
    ``devcontainer.json``; no host-side proxy is required. The only
    remaining host-side preparation is delivering the user's public keys
    for sshd's ``authorized_keys`` check.

    Secrets staging is deliberately NOT here — see
    :func:`stage_host_secrets`. The two are independent, and folding them
    together would make every SSH test stub a Doppler call it does not care
    about.
    """
    state_dir = host_state_dir()
    state_dir.mkdir(parents=True, exist_ok=True)
    public_keys = _agent_public_keys(_ssh_agent_environment())
    _write_host_authorized_keys(state_dir, public_keys)
    return {
        "state_dir": str(state_dir),
        "authorized_keys": str(len(public_keys)),
    }


def host_authorized_keys() -> list[str]:
    """Read the host-provided authorized keys file."""
    auth_keys_path = host_state_dir() / HOST_AUTHORIZED_KEYS_FILE
    if not auth_keys_path.exists():
        return []
    return [
        line.strip()
        for line in auth_keys_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def verify_host_ssh_inbound(port: int, user: str) -> str:
    """Verify R1 through the same resolved agent used to stage its public key."""
    result = subprocess.run(
        [
            "ssh",
            "-o",
            "BatchMode=yes",
            "-o",
            "StrictHostKeyChecking=accept-new",
            "-o",
            "UserKnownHostsFile=/dev/null",
            "-o",
            "LogLevel=ERROR",
            "-o",
            "ConnectTimeout=10",
            "-p",
            str(port),
            f"{user}@localhost",
            "hostname && whoami",
        ],
        capture_output=True,
        text=True,
        check=False,
        env=_ssh_agent_environment(),
    )
    lines = result.stdout.splitlines()
    if result.returncode != 0 or not lines or lines[-1] != user:
        msg = f"Inbound SSH verification failed on localhost:{port}"
        raise RuntimeError(msg)
    return result.stdout


class DevContainerManager:
    """Manage the local devcontainer lifecycle."""

    DEFAULT_IMAGE_NAME = "dotfiles-dev-local"
    DEFAULT_BASE_IMAGE = "ghcr.io/ray-manaloto/dotfiles-devcontainer:dev"

    def __init__(
        self,
        project_root: Path,
        image_name: str | None = None,
        config: DotfilesConfig | None = None,
    ) -> None:
        """Initialize the devcontainer manager.

        Args:
            project_root: The project root path.
            image_name: Optional image name override.
            config: Optional config; defaults to a fresh DotfilesConfig.
        """
        self.project_root = project_root
        self.config = config if config is not None else DotfilesConfig()
        self.image_name = image_name or self.config.container.image
        self.base_image = self.config.container.base_image

    def _get_bin(self, name: str) -> str:
        path = shutil.which(name)
        if not path:
            msg = f"Required binary '{name}' not found in PATH"
            raise RuntimeError(msg)
        return path

    def _run_cli(
        self,
        args: list[str],
        *,
        capture: bool = False,
    ) -> subprocess.CompletedProcess[str]:
        bin_path = self._get_bin("devcontainer")
        cmd = [bin_path, *args]
        env = os.environ.copy()

        if not capture:
            return subprocess.run(cmd, check=True, env=env, text=True)

        return subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True,
            env=env,
        )

    def build(self) -> None:
        """Build the thin host-user overlay image."""
        logger.info("Pulling published base image %s...", self.base_image)
        docker = self._get_bin("docker")
        platform = resolve_platform()
        subprocess.run(
            [docker, "pull", "--platform", platform, self.base_image],
            check=True,
            text=True,
            env=os.environ.copy(),
        )
        logger.info("Building thin local host-user overlay...")
        self._run_cli(
            [
                "build",
                "--workspace-folder",
                str(self.project_root),
                "--image-name",
                self.image_name,
                "--platform",
                platform,
            ]
        )

    def up(self) -> None:
        """Start the local devcontainer."""
        self.build()
        logger.info("Bringing devcontainer up...")
        self._run_cli(
            [
                "up",
                "--workspace-folder",
                str(self.project_root),
                "--remove-existing-container",
            ]
        )

    def down(self) -> None:
        """Stop and remove the local devcontainer (#800 F3).

        Looks up ids via ``devcontainer_names.teardown_container_ids`` — this
        workspace+architecture's #677 id labels plus pre-#677
        ``devcontainer.local_folder`` leftovers — the same lookup
        ``mise run stop`` uses, rather than a bare folder-label filter.
        Post-#677 containers carry no ``devcontainer.local_folder`` label
        (``--id-label`` REPLACES the CLI's inferred label set), so that
        filter alone stopped matching anything this verb was meant to find.
        """
        logger.info("Bringing devcontainer down...")
        docker = self._get_bin("docker")
        # Ensure project_root is absolute for label matching
        abs_root = str(Path(self.project_root).resolve())
        lookup_error = None
        try:
            container_ids = teardown_container_ids(resolve_names(workspace=abs_root))
        except subprocess.CalledProcessError as exc:
            lookup_error = exc
        if lookup_error is not None:
            logger.error("could not list devcontainers: %s", lookup_error)
            # A failed lookup is a failed teardown — exit non-zero so a
            # chained `dotfiles-setup docker down && …` does not proceed.
            raise SystemExit(1)

        if not container_ids:
            logger.info("No active or exited devcontainers found for this project.")
            return

        for container_id in container_ids:
            logger.info("Stopping and removing container %s...", container_id)
            subprocess.run([docker, "stop", container_id], check=False)
            subprocess.run([docker, "rm", "-f", container_id], check=False)

    def test(self) -> None:
        """Run the functional verification suite inside the container."""
        logger.info("Running functional tests inside container...")
        ssh_port = str(self.config.container.ssh_port)
        test_cmd = (
            "bash -lc '"
            f"export DOTFILES_SSH_PORT={ssh_port} && "
            "cd /workspaces/dotfiles/python && uv run dotfiles-setup audit --all && "
            "cd /workspaces/dotfiles && "
            "uv run --with pytest pytest tests/test_bootstrap.py && "
            "bats tests/infra/*.bats'"
        )

        self._run_cli(
            [
                "exec",
                "--workspace-folder",
                str(self.project_root),
                "bash",
                "-c",
                test_cmd,
            ]
        )

    def initialize_host(self) -> None:
        """Stage host-side authorized_keys and the scoped secrets env file."""
        result = initialize_host_ssh_runtime()
        env_file = stage_host_secrets()
        logger.info(
            "Prepared devcontainer host runtime at %s (keys: %s, env file: %s)",
            result["state_dir"],
            result["authorized_keys"],
            env_file,
        )

    def verify_ssh_inbound(self, port: int, user: str) -> None:
        """Verify host-to-container SSH using the resolved host agent."""
        output = verify_host_ssh_inbound(port, user)
        logger.info("Inbound SSH succeeded on localhost:%d:\n%s", port, output)
