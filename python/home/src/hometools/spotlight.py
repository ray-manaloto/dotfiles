"""spotlight-check: check that Spotlight skips the tracked folders, and say how to add the ones it doesn't."""

# The global AGENTS.md rule "Bulky scratch and Spotlight" says Spotlight skips ~/dev (owner, 2026-11-17: ~/dev is in
# Search Privacy); this check is what keeps that rule true, failing while either folder is indexed.
#
# Probed on macOS 27.2.1 (2026-11-16, dotfiles-lead): Spotlight indexed a new file in ~/dev/tmp or ~/dev/github within
# about two minutes; it skipped every file under a folder named *.noindex, including one written through a symlink into
# it; a .metadata_never_index file in a folder changed nothing; and new files under a hidden folder such as
# ~/.cache were never indexed. The Search Privacy list lives in
# /System/Volumes/Data/.Spotlight-V100/VolumeConfiguration.plist, which even root can't read without Full Disk Access,
# so this never edits it (owner, 2026-11-16: the owner drags the folders
# into System Settings > Spotlight > Search Privacy once, and this task checks the result).
#
# Each run writes one uniquely named file into every tracked folder that exists and one into a control folder that
# Spotlight does index, polls `mdfind -name` until the control file shows up, and then reports each folder as excluded
# when its file is missing from the results. It deletes every file it wrote. Without the control file indexed in time,
# nothing is proved and it exits 3. Hidden folders aren't in the list: new files there are never indexed, so a probe
# would pass whatever the setting.

import os
import secrets
import subprocess
import sys
import time
from collections.abc import Sequence
from pathlib import Path

from .models import SpotlightCheck, SpotlightFolder

# The folders to keep out of Spotlight: clones and scratch that agents fill with many files. ~/Library/Caches is not
# here: like a hidden folder, its new files were never indexed (probed), so a probe there passes whatever the setting.
FOLDERS = ("~/dev/github", "~/dev/tmp")
# Indexed (probed): the control file must show up here before a missing probe file means anything. mise bootstrap
# creates ~/dev/tmp.noindex ([bootstrap.directories]); the control can't go there or in a listed folder.
CONTROL = "~/Documents"
SETTINGS = "x-apple.systempreferences:com.apple.Spotlight-Settings.extension"
SECONDS = 300  # how long to wait for the control file; SPOTLIGHT_SECONDS overrides it for one run
# After the control shows up, how long to keep looking for the probes: Spotlight can index the control (written last)
# before a probe, so a probe missing at that moment means nothing yet. Three minutes is past the slowest indexing seen
# in the probes (about 2.5 min); a probe still missing then reads as excluded, which is evidence, not proof (only the
# Search Privacy list, behind Full Disk Access, is proof). SPOTLIGHT_SETTLE overrides it for one run.
SETTLE = 180
POLL = 5


def found(name: str) -> set[Path]:
    """Every path Spotlight has indexed whose name contains name, symlinks resolved."""
    done = subprocess.run(["mdfind", "-name", name], capture_output=True, check=True, text=True)
    return {Path(line).resolve() for line in done.stdout.splitlines() if line}


def check(
    folders: Sequence[str] = FOLDERS,
    control: str = CONTROL,
    seconds: float = SECONDS,
    settle: float = SETTLE,
    poll: float = POLL,
) -> SpotlightCheck:
    token = f"spotlight-probe-{secrets.token_hex(8)}"
    # Resolved, as mdfind reports them: a folder reached through a symlink is matched by its real path.
    probes = {folder: Path(folder).expanduser().resolve() / f"{token}.txt" for folder in folders}
    probes = {folder: probe for folder, probe in probes.items() if probe.parent.is_dir()}
    witness = Path(control).expanduser().resolve() / f"{token}-control.txt"
    written = [*probes.values(), witness]  # the control last, so it is not indexed long before the probes
    indexed: set[Path] = set()
    try:
        for path in written:
            path.write_text("spotlight-check probe\n")
        deadline = time.monotonic() + seconds
        while witness not in (indexed := found(token)) and time.monotonic() < deadline:
            time.sleep(poll)
        settled = time.monotonic() + settle
        while witness in indexed and not set(probes.values()) <= indexed and time.monotonic() < settled:
            time.sleep(poll)
            indexed |= found(token)
    finally:
        for path in written:
            path.unlink(missing_ok=True)
    control_indexed = witness in indexed
    results = [
        SpotlightFolder(
            folder=folder,
            # null without a probe, or without the control indexed: then nothing was proved either way.
            excluded=probes[folder] not in indexed if folder in probes and control_indexed else None,
        )
        for folder in folders
    ]
    return SpotlightCheck(control_indexed=control_indexed, folders=results)


def run() -> None:
    seconds = float(os.environ.get("SPOTLIGHT_SECONDS") or SECONDS)
    result = check(FOLDERS, CONTROL, seconds, float(os.environ.get("SPOTLIGHT_SETTLE") or SETTLE))
    sys.stdout.write(result.model_dump_json() + "\n")
    if not result.control_indexed:
        sys.stderr.write(f"spotlight-check: the control file in {CONTROL} was not indexed in time; nothing proved\n")
        raise SystemExit(3)
    if missing := [entry.folder for entry in result.folders if entry.excluded is False]:
        sys.stderr.write(
            "spotlight-check: Spotlight still indexes "
            + ", ".join(missing)
            + ". The agent rules (AGENTS.md, Bulky scratch and Spotlight) say ~/dev is skipped: drag ~/dev into System"
            " Settings > Spotlight > Search Privacy and run this again, or change that rule.\n"
        )
        # The daily run (spotlight:daily, from launchd) sets SPOTLIGHT_NO_OPEN: it alerts instead of opening a window.
        if not os.environ.get("SPOTLIGHT_NO_OPEN"):
            subprocess.run(["open", SETTINGS], check=False)
        raise SystemExit(1)
