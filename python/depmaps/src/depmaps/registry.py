"""The registry of dependencies, and the version this machine pins for each."""

import re
import subprocess
import tomllib
from pathlib import Path

from pydantic import ValidationError

from .events import DepmapsError
from .models import CommandSource, Config, Dep, ErrorCode, Registry
from .process import run

# A version names a folder and a cbm project, so it is one path segment, and never .repo.git, the bare
# clone's folder beside the versions (store.bare).
VERSION = re.compile(r"[0-9A-Za-z][0-9A-Za-z.+_-]*")
COMMAND_TIMEOUT = 30


def load(cfg: Config) -> Registry:
    try:
        return Registry.model_validate_json(cfg.registry.read_bytes())
    except (OSError, ValidationError) as error:
        raise DepmapsError(ErrorCode.invalid_registry, f"depmaps: registry {cfg.registry}: {error}") from None


def dep(registry: Registry, name: str) -> Dep:
    if name not in registry.deps:
        raise DepmapsError(ErrorCode.unknown_dep, f"depmaps: {name} is not in the registry")
    return registry.deps[name]


def checked(version: str, source: str) -> str:
    if not VERSION.fullmatch(version):
        raise DepmapsError(ErrorCode.version_unavailable, f"depmaps: {source} gave {version!r}, not a version")
    return version


def pinned(cfg: Config, name: str, entry: Dep) -> str:
    """The version from the global lockfile itself, or from the tool's own version command."""
    if isinstance(entry.version, CommandSource):
        return from_command(name, entry.version.command)
    tool = entry.version.lock
    try:
        tools = tomllib.loads(cfg.lock.read_text()).get("tools", {})
    except (OSError, tomllib.TOMLDecodeError) as error:
        raise DepmapsError(ErrorCode.version_unavailable, f"depmaps: {name}: lockfile {cfg.lock}: {error}") from None
    versions = {str(each.get("version")) for each in tools.get(tool, []) if "version" in each}
    if len(versions) != 1:
        found = ", ".join(sorted(versions)) or "none"
        message = f"depmaps: {name}: {cfg.lock} needs one version of {tool}, found {found}"
        raise DepmapsError(ErrorCode.version_unavailable, message)
    return checked(versions.pop(), f"{cfg.lock} for {tool}")


def from_command(name: str, command: list[str]) -> str:
    shown = " ".join(command)
    try:
        # From HOME, so the caller's folder (and any mise config in it) cannot change what runs.
        done = run(*command, cwd=Path.home(), timeout=COMMAND_TIMEOUT)
    except (OSError, subprocess.TimeoutExpired) as error:
        raise DepmapsError(ErrorCode.version_unavailable, f"depmaps: {name}: {shown}: {error}") from None
    fields = done.stdout.split()
    if done.returncode or not fields:
        message = f"depmaps: {name}: {shown} exited {done.returncode} with {done.stdout.strip()!r}"
        raise DepmapsError(ErrorCode.version_unavailable, message)
    return checked(fields[0], shown)
