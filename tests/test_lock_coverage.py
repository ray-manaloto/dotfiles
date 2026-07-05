"""Lock-coverage gates (#160 T8): every committed lockfile must cover its
config. This is the deterministic, network-free half of the lock-staleness
gate — it runs in CI contract-preflight AND locally, and fails when a tool
or feature is added/removed without regenerating the matching lock.

Freshness of the *resolutions* (new upstream releases for `"latest"` pins)
is intentionally NOT checked here: that is the daily `lock-refresh` job's
purpose, and asserting it per-PR would false-fail whenever any upstream
tool released since the last refresh.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

from dotfiles_setup.lock_refresh import merged_system_config_tools

_REPO_ROOT = Path(__file__).parent.parent
_FEATURE_KEY_RE = re.compile(r'"(ghcr\.io/[^"]+/features/[^"]+)"\s*:')


def _lock_tools(lock_path: Path) -> set[str]:
    return set(tomllib.loads(lock_path.read_text()).get("tools", {}))


def test_system_lock_covers_merged_config() -> None:
    """mise-system.lock must lock exactly the merged image config's tools
    (mise-system.toml + shared.toml) — `mise install --system --locked`
    silently skips unlocked tools, so a gap here means a tool missing from
    the image."""
    config = merged_system_config_tools(_REPO_ROOT)
    locked = _lock_tools(_REPO_ROOT / ".devcontainer" / "mise-system.lock")
    assert config - locked == set(), (
        f"tools missing from mise-system.lock (regenerate via lock-refresh): "
        f"{sorted(config - locked)}"
    )
    assert locked - config == set(), (
        f"stale mise-system.lock entries for removed tools: {sorted(locked - config)}"
    )


def test_root_lock_covers_host_config() -> None:
    """mise.lock must lock exactly the host config's tools (mise.toml +
    shared.toml) — CI lint installs with MISE_LOCKED=1 from it."""
    config_toml = tomllib.loads((_REPO_ROOT / "mise.toml").read_text())
    shared_toml = tomllib.loads(
        (_REPO_ROOT / ".config" / "mise" / "conf.d" / "shared.toml").read_text()
    )
    config = set(config_toml.get("tools", {})) | set(shared_toml.get("tools", {}))
    locked = _lock_tools(_REPO_ROOT / "mise.lock")
    assert config - locked == set(), (
        f"tools missing from mise.lock (run `mise run lock`): {sorted(config - locked)}"
    )
    assert locked - config == set(), (
        f"stale mise.lock entries for removed tools: {sorted(locked - config)}"
    )


def test_devcontainer_lock_covers_features() -> None:
    """devcontainer-lock.json must pin every feature referenced by
    devcontainer.json (regenerate via `devcontainer upgrade`). Feature keys
    are extracted by pattern because devcontainer.json is JSONC."""
    import json

    devcontainer_json = (_REPO_ROOT / ".devcontainer" / "devcontainer.json").read_text()
    referenced = set(_FEATURE_KEY_RE.findall(devcontainer_json))
    assert referenced, "no feature refs found — extraction pattern went stale"
    lock = json.loads(
        (_REPO_ROOT / ".devcontainer" / "devcontainer-lock.json").read_text()
    )
    locked = set(lock.get("features", {}))
    assert referenced - locked == set(), (
        f"features missing from devcontainer-lock.json "
        f"(run `devcontainer upgrade`): {sorted(referenced - locked)}"
    )
