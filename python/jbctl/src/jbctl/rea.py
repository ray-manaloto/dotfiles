"""rea (rea-agents): window maps and declarative AX scenarios, plus jbctl's patch to its native helper."""

import json
import subprocess
import time
from importlib.resources import as_file, files
from pathlib import Path
from typing import Any

from . import reainstall
from .ide import IdeError, tool
from .models import PatchState, ReaHealth, ReaIdentity, ReaPin

MARKER = "jbctl patch (dotfiles#502)"


def native_ui(command: str, app: str, ide: int, window: int, *args: str) -> dict[str, Any]:
    """One rea native-UI command against a window, without screenshots, as JSON."""
    return tool("rea", command, app, "--pid", str(ide), "--window-id", str(window),
                "--max-nodes", "3000", "--screenshot=false", *args, "--format", "json")  # fmt: skip


def observe(app: str, ide: int, window: int) -> dict[str, Any]:
    """rea's map of a layer-0 window: every node's path, role, label, value and actions."""
    return native_ui("observe-native-ui", app, ide, window)["normalized_result"]["initial"]


def top_level(snapshot: dict[str, Any], role: str) -> list[dict[str, Any]]:
    return [n for n in snapshot["nodes"] if len(n["path"]) == 1 and n["role"] == role]


def breadcrumb(snapshot: dict[str, Any]) -> list[str]:
    """The Settings page header (e.g. AI > MCP Server > Exposed Tools): labelled top-level buttons with no actions.

    A banner's link (e.g. Dismiss) matches too and comes first, so the page is always the last entry.
    """
    return [n["title"] for n in top_level(snapshot, "AXButton") if n["title"] and not n["actions"]]


def goto(app: str, ide: int, window: int, page: str) -> list[str]:
    """Type the page name into the Settings search field, then clear it; works with the IDE in the background."""
    # The dialog's own search field comes first; a page such as Exposed Tools adds another "Search" field.
    search = [n["path"] for n in top_level(observe(app, ide, window), "AXTextField") if n["title"] == "Search"]
    if not search:
        msg = "the Settings search field is missing"
        raise IdeError(msg)
    steps = [
        {"kind": "key-entry", "path": search[0], "text": page},
        {"kind": "wait", "milliseconds": 1500},
        {"kind": "key-entry", "path": search[0], "text": ""},
    ]
    native_ui("capture-native-ui-scenario", app, ide, window, "--steps", json.dumps(steps))
    # The page swap lands asynchronously.
    crumbs: list[str] = []
    for _ in range(4):
        crumbs = breadcrumb(observe(app, ide, window))
        if crumbs and crumbs[-1] == page:
            return crumbs
        time.sleep(0.5)
    msg = f"Settings did not reach {page}: the breadcrumb reads {crumbs}"
    raise IdeError(msg)


def installed_helper() -> Path:
    """The helper in jbctl's rea folder (mise run //jbctl:rea-install), not the global rea-agents install."""
    return reainstall.folder() / reainstall.HELPER


def patch(helper: Path) -> PatchState:
    """Apply the patch once; refuse a helper the patch no longer fits (an upstream change)."""
    if MARKER in helper.read_text():
        return PatchState.already
    # Every hunk must fit before any is written: a partial apply would leave the marker and read as already.
    with as_file(files("jbctl").joinpath("rea-native-ui.patch")) as diff:
        for mode in ("--dry-run", "--silent"):
            done = subprocess.run(["patch", "--forward", mode, "-i", str(diff), str(helper)],
                                  capture_output=True, text=True, check=False)  # fmt: skip
            if done.returncode != 0:
                msg = f"the rea helper changed upstream; refresh rea-native-ui.patch ({done.stdout.strip()})"
                raise IdeError(msg)
    return PatchState.applied


def installed_version(root: Path) -> str | None:
    """rea --version from the folder's bin, run with the node on PATH (the global one); None when it does not run."""
    rea = root / "node_modules/.bin/rea"
    if not rea.is_file():
        return None
    done = subprocess.run([str(rea), "--version"], capture_output=True, text=True, check=False)
    return done.stdout.strip() if done.returncode == 0 else None


def stray_global() -> bool:
    """npm's global prefix still holds a rea-agents: the hand install this folder replaces."""
    prefix = subprocess.run(["npm", "prefix", "-g"], capture_output=True, text=True, check=True).stdout.strip()
    return (Path(prefix) / "lib/node_modules/rea-agents").exists()


def health(root: Path, want: ReaPin) -> ReaHealth:
    """The folder against the pin: source commit, package sha256, patch marker and rea's own version."""
    written = root / reainstall.IDENTITY
    recorded = ReaIdentity.model_validate_json(written.read_text()) if written.is_file() else None
    archive = root / reainstall.ARCHIVE
    helper = root / reainstall.HELPER
    version = installed_version(root)
    source = recorded.source_sha if recorded else None
    package = archive.is_file() and reainstall.sha256(archive) == want.package_sha256
    marker = helper.is_file() and MARKER in helper.read_text()
    return ReaHealth(
        ok=source == want.source_sha and package and marker and version == want.package_version,
        pinned_source_sha=want.source_sha,
        installed_source_sha=source,
        package_sha_match=package,
        patch_marker=marker,
        version=version,
        version_match=version == want.package_version,
        stray_global=stray_global(),
    )
