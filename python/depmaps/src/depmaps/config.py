"""Where depmaps reads and writes: each path from its DEP_MAPS_* variable, else its default."""

import os
from pathlib import Path

from .models import Config


def load() -> Config:
    home = Path.home()
    # mise's link to the globally pinned cbm, which the tools phase of `mise bootstrap` makes before the
    # post-tools hook runs depmaps; cbm's own launcher, which points at it, comes only with //cbm:install
    # (docs/research/codebase-memory-mcp/install.md).
    defaults = {
        "registry": home / ".config/dep-maps/deps.json",
        "store": home / ".local/share/dep-maps",
        "lock": home / ".config/mise/mise.lock",
        "cbm": home / ".local/share/mise/installs/github-deus-data-codebase-memory-mcp/global/codebase-memory-mcp",
    }
    return Config.model_validate(
        {key: os.environ.get(f"DEP_MAPS_{key.upper()}") or str(value) for key, value in defaults.items()}
    )
