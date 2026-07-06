"""Lock-coverage gates (#160 T8): every committed lockfile must cover its config.

This is the deterministic, network-free half of the lock-staleness gate — it
runs in CI contract-preflight AND locally, and fails when a tool or feature is
added/removed without regenerating the matching lock.

Freshness of the *resolutions* (new upstream releases for `"latest"` pins)
is intentionally NOT checked here: that is the daily `lock-refresh` job's
purpose, and asserting it per-PR would false-fail whenever any upstream
tool released since the last refresh.
"""

from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path

from dotfiles_setup.lock_refresh import (
    merged_system_config_tools,
    runtime_config_tools,
)

_REPO_ROOT = Path(__file__).parent.parent
_FEATURE_KEY_RE = re.compile(r'"(ghcr\.io/[^"]+/features/[^"]+)"\s*:')


def _lock_tools(lock_path: Path) -> set[str]:
    return set(tomllib.loads(lock_path.read_text()).get("tools", {}))


def test_system_lock_covers_merged_config() -> None:
    """mise-system.lock must lock exactly the merged image config's tools.

    Merged config = mise-system.toml + shared.toml. `mise install --system
    --locked` silently skips unlocked tools, so a gap here means a tool
    missing from the image.
    """
    config = merged_system_config_tools(_REPO_ROOT)
    locked = _lock_tools(_REPO_ROOT / ".devcontainer" / "mise-system.lock")
    assert config - locked == set(), (
        f"tools missing from mise-system.lock (regenerate via lock-refresh): "
        f"{sorted(config - locked)}"
    )
    assert locked - config == set(), (
        f"stale mise-system.lock entries for removed tools: {sorted(locked - config)}"
    )


def test_runtime_lock_covers_runtime_config() -> None:
    """mise-runtime.lock must lock exactly the runtime tier's tools (#160 T9).

    The devcontainer-runtime stage installs them with
    `mise install --system --locked` under MISE_ENV=runtime.
    """
    config = runtime_config_tools(_REPO_ROOT)
    locked = _lock_tools(_REPO_ROOT / ".devcontainer" / "mise-runtime.lock")
    assert config - locked == set(), (
        f"tools missing from mise-runtime.lock (regenerate via lock-refresh): "
        f"{sorted(config - locked)}"
    )
    assert locked - config == set(), (
        f"stale mise-runtime.lock entries for removed tools: {sorted(locked - config)}"
    )


def test_image_locks_carry_no_provenance() -> None:
    """The image locks must not require provenance the image won't verify.

    mise-system.toml disables `github_attestations`/`slsa` (T7 decision
    16), and `mise install --system --locked` fail-closes when a lock
    entry requires provenance while verification is off (jdx/mise#10694
    — broke PR #169's base build). `mise lock` records provenance
    regardless of those settings, so lock-collect strips it
    (`strip_provenance`); this gate catches a hand-regenerated lock that
    bypassed collect. Host locks keep provenance — hosts verify.
    """
    for lock in ("mise-system.lock", "mise-runtime.lock"):
        text = (_REPO_ROOT / ".devcontainer" / lock).read_text()
        assert "provenance" not in text, (
            f"{lock} requires provenance the image build cannot verify — "
            f"collect via `dotfiles-setup lock-collect` (strips it), do not "
            f"copy stage locks by hand"
        )


def test_root_lock_covers_host_config() -> None:
    """mise.lock must lock exactly the root mise.toml tools.

    CI lint installs with MISE_LOCKED=1 from it. mise 2026.7.0 writes one lock
    PER CONFIG DIR (empirically re-verified at the T12 hk bump: `mise install`
    split the shared entries out of the root lock), so the shared fragment
    locks separately below.
    """
    config = set(tomllib.loads((_REPO_ROOT / "mise.toml").read_text()).get("tools", {}))
    locked = _lock_tools(_REPO_ROOT / "mise.lock")
    assert config - locked == set(), (
        f"tools missing from mise.lock (run `mise run lock`): {sorted(config - locked)}"
    )
    assert locked - config == set(), (
        f"stale mise.lock entries for removed tools: {sorted(locked - config)}"
    )


def test_shared_conf_d_lock_covers_shared_fragment() -> None:
    """.config/mise/mise.lock must lock exactly shared.toml's tools.

    This is the per-config-dir lock mise writes for the conf.d fragment.
    Without this file committed, CI's MISE_LOCKED=1 install cannot resolve the
    20 shared tools (hk, pkl, the linters) and lint fails.
    """
    shared = set(
        tomllib.loads(
            (_REPO_ROOT / ".config" / "mise" / "conf.d" / "shared.toml").read_text()
        ).get("tools", {})
    )
    locked = _lock_tools(_REPO_ROOT / ".config" / "mise" / "mise.lock")
    assert shared - locked == set(), (
        f"tools missing from .config/mise/mise.lock: {sorted(shared - locked)}"
    )
    assert locked - shared == set(), (
        f"stale .config/mise/mise.lock entries: {sorted(locked - shared)}"
    )


def test_devcontainer_lock_covers_features() -> None:
    """devcontainer-lock.json must pin every referenced devcontainer.json feature.

    Regenerate via `devcontainer upgrade`. Feature keys are extracted by
    pattern because devcontainer.json is JSONC.
    """
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
