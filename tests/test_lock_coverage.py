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
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping

from dotfiles_setup.lock_refresh import (
    merged_system_config,
    merged_system_config_tools,
    runtime_config_tools,
)

_REPO_ROOT = Path(__file__).parent.parent
_FEATURE_KEY_RE = re.compile(r'"(ghcr\.io/[^"]+/features/[^"]+)"\s*:')
_EXTRAS_RE = re.compile(r"\[.*\]$")
# A fully-specified pin (X.Y.Z, optional suffix). ONLY these are version-checked
# against the lock: "latest", partial ("1.52"), and range ("^1.2") pins resolve
# to a version mise picks and legitimately drifts between refreshes — asserting
# those per-PR would false-fail, which is the daily lock-refresh job's domain.
_EXACT_VERSION_RE = re.compile(r"^\d+\.\d+\.\d+[\w.\-+]*$")


def _strip_extras(tool: str) -> str:
    """Drop a pipx `[extras]` suffix so config keys compare to lock keys.

    mise records a pipx tool's lock key WITHOUT its extras suffix (extras
    affect the install, not the locked identity), so `pipx:graphifyy[all]`
    in mise.toml is locked as `pipx:graphifyy`. Normalize the config side to
    match. A genuinely unlocked tool still fails: its normalized name is
    absent from the lock either way.
    """
    return _EXTRAS_RE.sub("", tool)


def _lock_tools(lock_path: Path) -> set[str]:
    return set(tomllib.loads(lock_path.read_text()).get("tools", {}))


def _normalize_version(version: str) -> str:
    """Strip a leading `v` so a pin (`v0.2.40`) matches a lock version (`0.2.40`)."""
    return version.removeprefix("v")


def _config_pin(value: object) -> str | None:
    """Extract the pin from a mise tool value (a string or a `{version=...}` table)."""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        pin = value.get("version")
        return pin if isinstance(pin, str) else None
    return None


def _exact_config_pins(tools: Mapping[str, object]) -> dict[str, str]:
    """Map each EXACTLY-pinned tool to its normalized version (name extras-stripped).

    Only fully-specified pins (X.Y.Z) are returned; see `_EXACT_VERSION_RE`.
    """
    pins: dict[str, str] = {}
    for name, value in tools.items():
        pin = _config_pin(value)
        if pin is None:
            continue
        normalized = _normalize_version(pin)
        if _EXACT_VERSION_RE.match(normalized):
            pins[_strip_extras(name)] = normalized
    return pins


def _lock_versions(lock_path: Path) -> dict[str, str]:
    """Map each locked tool to its normalized version.

    mise writes each tool as an array-of-tables (`[[tools.NAME]]`), so the
    version lives at `tools[name][0]["version"]`.
    """
    tools = tomllib.loads(lock_path.read_text()).get("tools", {})
    versions: dict[str, str] = {}
    for name, entries in tools.items():
        if isinstance(entries, list) and entries and isinstance(entries[0], dict):
            version = entries[0].get("version")
            if isinstance(version, str):
                versions[name] = _normalize_version(version)
    return versions


def _version_drift(
    tools: Mapping[str, object], lock_path: Path
) -> dict[str, tuple[str, str]]:
    """Return {tool: (config_pin, lock_version)} for exact pins that disagree.

    Only tools present in BOTH the config pins and the lock are compared — name
    coverage is the other tests' job; this one is purely about version match.
    """
    pins = _exact_config_pins(tools)
    locked = _lock_versions(lock_path)
    return {
        name: (pins[name], locked[name])
        for name in pins
        if name in locked and pins[name] != locked[name]
    }


def _assert_no_version_drift(tools: dict[str, object], lock_path: Path) -> None:
    drift = _version_drift(tools, lock_path)
    assert not drift, (
        f"{lock_path.name}: exact config pin != lock version — a tool was "
        f"bumped in config without regenerating the lock (root/shared: "
        f"`mise run lock`; image: lock-refresh on linux-x64). Drift: "
        + "; ".join(
            f"{name}: config {cfg} vs lock {lock}"
            for name, (cfg, lock) in sorted(drift.items())
        )
    )


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
    config = {
        _strip_extras(t)
        for t in tomllib.loads((_REPO_ROOT / "mise.toml").read_text()).get("tools", {})
    }
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


# --- Version-drift gates (config exact pin must equal the locked version) ------
# The coverage tests above check a tool NAME is present in its lock; these check
# its exact-pinned VERSION matches. Version drift was the invisible gap that let
# a manual tool bump (hk 1.50.0 -> 1.52.0) ship with a stale lock: name coverage
# stayed green because hk was still present (at the old version), and CI's
# `mise install --locked` only failed downstream in the base build. These gates
# move that failure per-PR, where the fix (`mise run lock` / lock-refresh) is
# cheap. "latest"/partial/range pins are excluded by design (see _EXACT_VERSION_RE).


def _root_config_tools() -> dict[str, object]:
    return tomllib.loads((_REPO_ROOT / "mise.toml").read_text()).get("tools", {})


def _shared_config_tools() -> dict[str, object]:
    return tomllib.loads(
        (_REPO_ROOT / ".config" / "mise" / "conf.d" / "shared.toml").read_text()
    ).get("tools", {})


def _runtime_config_tools_table() -> dict[str, object]:
    return tomllib.loads(
        (_REPO_ROOT / ".devcontainer" / "mise-runtime.toml").read_text()
    ).get("tools", {})


def test_root_lock_versions_match_pins() -> None:
    """mise.lock's versions must equal root mise.toml's exact pins (`mise run lock`)."""
    _assert_no_version_drift(_root_config_tools(), _REPO_ROOT / "mise.lock")


def test_shared_lock_versions_match_pins() -> None:
    """.config/mise/mise.lock's versions must equal shared.toml's exact pins."""
    _assert_no_version_drift(
        _shared_config_tools(), _REPO_ROOT / ".config" / "mise" / "mise.lock"
    )


def test_system_lock_versions_match_pins() -> None:
    """mise-system.lock's versions must equal the merged image config's exact pins.

    This is the gate that would have caught the stale image lock: a shared.toml
    bump that skipped the linux-x64 lock-refresh leaves mise-system.lock behind,
    and the base build's `mise install --system --locked` rejects it.
    """
    _assert_no_version_drift(
        merged_system_config(_REPO_ROOT),
        _REPO_ROOT / ".devcontainer" / "mise-system.lock",
    )


def test_runtime_lock_versions_match_pins() -> None:
    """mise-runtime.lock's versions must equal the runtime tier's exact pins."""
    _assert_no_version_drift(
        _runtime_config_tools_table(),
        _REPO_ROOT / ".devcontainer" / "mise-runtime.lock",
    )


def test_version_drift_gate_discriminates(tmp_path: Path) -> None:
    """Control arm: the gate must flag a stale lock AND pass a matching one.

    A gate verified only on the (currently clean) real locks is a check that
    can only pass. Reproduce the exact stale-lock failure realistically — an
    exact config pin ahead of its lock entry — and confirm it is caught; then
    align them and confirm it clears. See probes-need-a-control-arm.md.
    """
    config = {"hk": "1.52.0", "pixi": {"version": "0.73.0", "os": ["macos"]}}
    stale_lock = tmp_path / "stale.lock"
    stale_lock.write_text(
        '[[tools.hk]]\nversion = "1.50.0"\nbackend = "aqua:jdx/hk"\n\n'
        '[[tools.pixi]]\nversion = "0.73.0"\nbackend = "github:prefix-dev/pixi"\n'
    )
    drift = _version_drift(config, stale_lock)
    assert drift == {"hk": ("1.52.0", "1.50.0")}, (
        f"gate failed to flag the stale hk pin (or over-reported): {drift}"
    )

    fresh_lock = tmp_path / "fresh.lock"
    fresh_lock.write_text('[[tools.hk]]\nversion = "1.52.0"\nbackend = "aqua:jdx/hk"\n')
    assert _version_drift({"hk": "1.52.0"}, fresh_lock) == {}, (
        "gate false-positived on a matching pin/lock pair"
    )


def test_version_drift_gate_skips_non_exact_pins(tmp_path: Path) -> None:
    """`latest`/partial/range pins are not version-checked (they legitimately drift)."""
    config = {"conda:cmake": "latest", "foo": "1.52", "bar": "^1.2.0"}
    lock = tmp_path / "x.lock"
    lock.write_text(
        '[[tools."conda:cmake"]]\nversion = "3.31.0"\n\n'
        '[[tools.foo]]\nversion = "1.52.9"\n\n'
        '[[tools.bar]]\nversion = "1.5.0"\n'
    )
    assert _version_drift(config, lock) == {}, (
        "gate must not check non-exact pins — those are the daily refresh's domain"
    )
