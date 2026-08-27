# Copyright (c) 2026 Raymond Manaloto
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

# Tools that may legitimately be declared in BOTH host and image, each with the
# reason. The shared fragment is the normal answer; these are the cases it
# CANNOT serve. Add entries HERE (with a reason) rather than deleting the check.
_INTENTIONAL_HOST_IMAGE_DUPES: dict[str, str] = {
    # shared.toml merges into the SYSTEM tier, which sets minimum_release_age
    # = "7d" (.devcontainer/mise-system.toml) and carries tools ONLY — no
    # [settings], so no per-tool age exclusion is expressible there. An exact
    # pin of a fresh codex therefore fail-closes at image build; that is the
    # recorded PR #169 failure ("codex 0.142.5 at 5.7d", mise-runtime.toml).
    # So the host pins it exactly (locked, reproducible) while the image
    # resolves "latest" in the RUNTIME tier, which is where this repo puts
    # fast-moving AI CLIs and which carries the age exclusion. Approved by Ray
    # 2026-08-27; revisit if shared.toml ever gains a [settings] table.
    "npm:@openai/codex": "host pins exactly; image resolves latest (runtime tier)",
}


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
    duplicated = (host & image) - set(_INTENTIONAL_HOST_IMAGE_DUPES)
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
