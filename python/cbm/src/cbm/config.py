"""The generated Config, loaded from the environment, and the paths it implies."""

import os
from collections.abc import Mapping
from pathlib import Path

from pydantic import ValidationError

from .models import Client, Config

# The checks read ~/.claude.json, ~/.claude, ~/.codex and ~/.config/opencode, so a moved config is refused.
# OPENCODE_CONFIG moves the file CBM writes OpenCode's MCP entry to (src/cli/cli.c:2953-2958).
MOVED = ("CLAUDE_CONFIG_DIR", "CODEX_HOME", "OPENCODE_CONFIG")
# CBM_CACHE_DIR and CBM_RUNTIME_DIR select another cache or daemon namespace: never passed on.
PRIVATE = ("CBM_CACHE_DIR", "CBM_RUNTIME_DIR")


class SettingError(Exception):
    """A setting the package cannot work with; the CLI prints it and exits 2."""


def load(environ: Mapping[str, str] = os.environ) -> Config:
    if moved := [name for name in MOVED if environ.get(name)]:
        msg = f"cbm: unset {', '.join(moved)}; this package only handles the default folders"
        raise SettingError(msg)
    home = Path(environ["HOME"])
    requested = environ.get("CBM_CLIENTS", ",".join(Client))
    clients = [name.strip() for name in requested.split(",") if name.strip()]
    mise_data_dir = Path(environ.get("MISE_DATA_DIR", home / ".local/share/mise"))
    fields: dict[str, object] = {"home": home, "mise_data_dir": mise_data_dir, "clients": clients}
    if (seconds := environ.get("CBM_PROBE_TIMEOUT_SECONDS")) is not None:
        fields["probe_timeout"] = seconds
    try:
        return Config.model_validate(fields)
    except ValidationError as error:
        if any(detail["loc"][0] == "probe_timeout" for detail in error.errors()):
            msg = f"cbm: CBM_PROBE_TIMEOUT_SECONDS must be greater than 0 and at most 60: {seconds}"
            raise SettingError(msg) from None
        reasons = "; ".join(detail["msg"] for detail in error.errors())
        msg = f"cbm: CBM_CLIENTS must name one or more of {','.join(Client)}, each once ({reasons}): {requested}"
        raise SettingError(msg) from None


def link(cfg: Config) -> Path:
    """The mise global runtime link: it follows the global config only, so no project pin moves it."""
    return cfg.mise_data_dir / "installs/github-deus-data-codebase-memory-mcp/global/codebase-memory-mcp"


def launcher(cfg: Config) -> Path:
    """The one path every agent config names: a symlink to the global link."""
    return cfg.home / ".local/share/codebase-memory-mcp/bin/codebase-memory-mcp"


def child_env(environ: Mapping[str, str] = os.environ) -> dict[str, str]:
    return {name: value for name, value in environ.items() if name not in PRIVATE}
