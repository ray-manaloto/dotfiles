"""Host↔image mise parity gates (#160 T12.5, decision 16).

Ray's parity principle, verbatim: "macOS local == CI/CD versions." Two
machine checks enforce the structure that keeps it true:

1. A tool used by BOTH host and image must live in the shared fragment
   (`.config/mise/conf.d/shared.toml`, exact-pinned, T5) — never declared
   twice. A duplicate declaration is exactly how version drift starts.
2. A `[settings]` key set in BOTH the host and image configs must carry
   the same value, unless the difference is intentionally allowlisted
   with a reason.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

_REPO_ROOT = Path(__file__).parent.parent

# Settings keys (flattened, dot-joined) that may legitimately differ
# between host and image, each with the reason. Empty today — add entries
# HERE (with a reason) rather than letting the parity test rot.
_INTENTIONAL_SETTINGS_DIFFS: dict[str, str] = {}


def _tools(path: str) -> set[str]:
    return set(tomllib.loads((_REPO_ROOT / path).read_text()).get("tools", {}))


def _flat_settings(path: str) -> dict[str, object]:
    def walk(prefix: str, table: dict) -> dict[str, object]:
        out: dict[str, object] = {}
        for key, value in table.items():
            dotted = f"{prefix}.{key}" if prefix else key
            if isinstance(value, dict):
                out.update(walk(dotted, value))
            else:
                out[dotted] = value
        return out

    return walk("", tomllib.loads((_REPO_ROOT / path).read_text()).get("settings", {}))


def test_no_tool_declared_in_both_host_and_image_configs() -> None:
    """Shared tools live ONLY in shared.toml.

    A tool declared in both the root config and an image config would
    drift the moment one side bumps.
    """
    host = _tools("mise.toml")
    image = (
        _tools(".devcontainer/mise-system.toml")
        | _tools(".devcontainer/mise-runtime.toml")
        | _tools("home/dot_config/mise/config.toml.tmpl")
    )
    shared = _tools(".config/mise/conf.d/shared.toml")
    duplicated = host & image
    assert duplicated == set(), (
        f"tools declared in BOTH host and image configs (move to shared.toml): "
        f"{sorted(duplicated)}"
    )
    shadowed = shared & (host | image)
    assert shadowed == set(), (
        f"shared.toml tools re-declared elsewhere (delete the shadow): "
        f"{sorted(shadowed)}"
    )


def test_settings_parity_host_vs_image() -> None:
    """[settings] keys present in BOTH host and image configs must agree.

    Intentional differences require an allowlist entry with a reason in
    _INTENTIONAL_SETTINGS_DIFFS.
    """
    host = _flat_settings("mise.toml")
    image = _flat_settings(".devcontainer/mise-system.toml")
    diverged = {
        key: (host[key], image[key])
        for key in host.keys() & image.keys()
        if host[key] != image[key] and key not in _INTENTIONAL_SETTINGS_DIFFS
    }
    assert diverged == {}, (
        f"host↔image [settings] divergence (fix, or allowlist with a reason): "
        f"{diverged}"
    )
