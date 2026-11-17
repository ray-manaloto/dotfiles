"""pc-doctor's gpu-cdi line: GPU containers get the GPU through NVIDIA's CDI refresh units, read over ssh (#732)."""

# Five things, each read with commands on the PC: the toolkit is installed (pacman -Q); nvidia-cdi-refresh.path is
# enabled and waiting and the oneshot nvidia-cdi-refresh.service's last run did not fail (systemctl show; inactive
# after a success is normal); nvidia-ctk cdi list, given the CDI folders Docker reads, resolves nvidia.com/gpu=all and
# logs no warning (it warns about a spec it could not load and still exits 0); every path the specs mount exists
# (find prints each spec, stat checks the paths); the loaded module's version (/proc/driver/nvidia/version) is
# nvidia-utils' version without its package release. Any failure fails the line, a mismatched driver with the reason
# driver-reboot-required beside the others; else anything unread is unknown; else it passes. It checks configuration;
# it does not prove that a GPU workload runs.
#
# The shapes are what the PC printed on 2026-11-16 (nvidia-container-toolkit 1.20.1, systemd, GNU find and coreutils
# stat under LC_ALL=C), with a malformed spec and a missing library qualified in a scratch CDI folder: nvidia-ctk exits
# 0 for both, warns only for the malformed spec and never notices the missing library.

import re
import shlex
import subprocess
from collections.abc import Callable

import yaml
from pydantic import TypeAdapter, ValidationError

from .models import CdiContainerEdits, CdiSpec, CdiSpecDirs, PcDoctorLine, Result

CHECK = "gpu-cdi"
TOOLKIT, UTILS = "nvidia-container-toolkit", "nvidia-utils"
PATH_UNIT, SERVICE = "nvidia-cdi-refresh.path", "nvidia-cdi-refresh.service"
PROPERTIES = "Id,LoadState,UnitFileState,ActiveState,SubState,Result"
# The PC's own daemon, never a Docker context or DOCKER_HOST the ssh session inherits.
DOCKER = ("docker", "--host", "unix:///var/run/docker.sock")
DEVICE = "nvidia.com/gpu=all"
MODULE = "/proc/driver/nvidia/version"
REBOOT = "driver-reboot-required"
# GNU tools' messages in English, so a missing path reads apart from an unreadable one.
C = ("env", "LC_ALL=C")
GONE = ": No such file or directory"
# logrus text lines: time="..." level=warning msg="..."
LOG = re.compile(r'level=(?P<level>\w+) msg="(?P<msg>(?:[^"\\]|\\.)*)"')
# NVRM version: NVIDIA UNIX Open Kernel Module for x86_64  615.78.08  Release Build ...
LOADED = re.compile(r"^NVRM version: .*?Kernel Module(?: for \S+)?\s+(?P<version>\d+(?:\.\d+)+)\s")
# stat: cannot statx '<path>': <reason>; the path as coreutils quotes it, which shlex reads back.
STAT_ERROR = re.compile(r"stat: cannot statx (?P<name>.+): (?P<why>[^:]+)")
NOT_FOUND = re.compile(r"error: package '[^']+' was not found")
DIRS = TypeAdapter[list[str]](CdiSpecDirs)

type Run = Callable[[tuple[str, ...]], subprocess.CompletedProcess[str] | str]


class Seen:
    """What the line saw: each failure (a sentence and its culprits) and each thing it could not read."""

    def __init__(self, run: Run) -> None:
        self.run = run
        self.failed: list[tuple[str, list[str]]] = []
        self.unread: list[str] = []
        # Once ssh itself failed or a call timed out, the PC is not answering: the rest is skipped, so an unreachable
        # PC costs one time limit, not one per call.
        self.cut = False

    def fail(self, why: str, *culprits: str) -> None:
        self.failed.append((why, list(culprits)))

    def call(
        self, argv: tuple[str, ...], codes: frozenset[int] = frozenset({0})
    ) -> subprocess.CompletedProcess[str] | None:
        """argv's answer on the PC when it exited with one of codes; otherwise None, and why is unread."""
        if self.cut:
            return None
        done = self.run(argv)
        if isinstance(done, str):
            self.unread.append(done)
            self.cut = True
            return None
        if done.returncode not in codes:
            words = argv[len(C) :] if argv[: len(C)] == C else argv
            self.unread.append(f"{words[0]} exited {done.returncode}")
            return None
        return done

    def line(self, passed: str) -> PcDoctorLine:
        """Any failure fails, with every failure and unread named; else anything unread is unknown; else a pass."""
        if self.failed:
            detail = "; ".join([why for why, _ in self.failed] + [f"could not read: {why}" for why in self.unread])
            culprits = [culprit for _, named in self.failed for culprit in named]
            return PcDoctorLine(check=CHECK, result=Result.fail, detail=detail, culprits=culprits)
        if self.unread:
            return PcDoctorLine(check=CHECK, result=Result.unknown, detail="; ".join(self.unread), culprits=[])
        return PcDoctorLine(check=CHECK, result=Result.pass_, detail=passed, culprits=[])


def packages(seen: Seen) -> str | None:
    """Fails a missing toolkit; nvidia-utils' version without its epoch and package release, or None if unread."""
    # pacman -Q exits 1 when a package is not installed and still prints the ones that are.
    done = seen.call(("pacman", "-Q", TOOLKIT, UTILS), frozenset({0, 1}))
    if done is None:
        return None
    installed = {}
    # Exit 1 is an answer only when each complaint is a package that is not installed (a locked or unreadable
    # database also exits 1).
    if done.returncode and not all(NOT_FOUND.fullmatch(row) for row in done.stderr.splitlines()):
        seen.unread.append(f"pacman -Q failed: {done.stderr.strip()[:120]!r}")
        return None
    for row in done.stdout.splitlines():
        name, _, version = row.partition(" ")
        if not version or " " in version:
            seen.unread.append(f"pacman -Q printed {row!r}")
            return None
        installed[name] = version
    if TOOLKIT not in installed:
        seen.fail(f"{TOOLKIT} is not installed", f"package:{TOOLKIT}")
    if UTILS not in installed:
        seen.unread.append(f"{UTILS} is not installed, so the driver's version is unknown")
        return None
    # [epoch:]version-release, as pacman prints it: 615.78.08-1 is driver 615.78.08.
    version = installed[UTILS].rpartition(":")[2]
    return version.rpartition("-")[0] or version


def units(seen: Seen) -> None:
    """Fails a refresh path unit that is not enabled and waiting, and a refresh service whose last run failed."""
    done = seen.call(("systemctl", "show", f"--property={PROPERTIES}", "--", PATH_UNIT, SERVICE))
    if done is None:
        return
    shown = {}
    for block in done.stdout.strip().split("\n\n"):
        values = dict(row.partition("=")[::2] for row in block.splitlines())
        shown[values.get("Id")] = values
    keys = set(PROPERTIES.split(","))
    if set(shown) != {PATH_UNIT, SERVICE} or any(set(values) != keys for values in shown.values()):
        seen.unread.append("systemctl show did not print both refresh units")
        return
    path, service = shown[PATH_UNIT], shown[SERVICE]
    if path["UnitFileState"] != "enabled" or (path["ActiveState"], path["SubState"]) != ("active", "waiting"):
        state = f"{path['UnitFileState']}, {path['ActiveState']} ({path['SubState']})"
        seen.fail(f"{PATH_UNIT} is {state}, not enabled and waiting", f"unit:{PATH_UNIT}")
    # A oneshot is inactive after a success; a failed run leaves it failed, Result naming why (exit-code,
    # start-limit-hit after Restart=on-failure gave up).
    if service["LoadState"] != "loaded" or service["ActiveState"] == "failed" or service["Result"] != "success":
        state = f"{service['LoadState']}, {service['ActiveState']}, last result {service['Result']}"
        seen.fail(f"{SERVICE}'s last generation did not succeed ({state})", f"unit:{SERVICE}")


def folders(seen: Seen) -> list[str] | None:
    """The CDI folders Docker reads, or None if unread."""
    done = seen.call((*DOCKER, "info", "--format", "{{json .CDISpecDirs}}"))
    if done is None:
        return None
    try:
        return DIRS.validate_json(done.stdout)
    except ValidationError:
        # null when Docker runs without CDI, or output that is not a list of folders.
        seen.unread.append(f"docker info printed no CDI folders: {done.stdout.strip()[:80]!r}")
        return None


def resolves(seen: Seen, dirs: list[str]) -> None:
    """Fails when nvidia-ctk cannot resolve the GPU in those folders, and for each warning it logs."""
    done = seen.call(("nvidia-ctk", "cdi", "list", *(arg for d in dirs for arg in ("--spec-dir", d))))
    if done is None:
        return
    if DEVICE not in done.stdout.splitlines():
        seen.fail(f"nvidia-ctk cdi list does not resolve {DEVICE}", f"cdi:{DEVICE}")
    warnings = [m["msg"] for m in LOG.finditer(done.stderr) if m["level"] in {"warning", "error", "fatal"}]
    if warnings:
        seen.fail(f"nvidia-ctk cdi list logged {len(warnings)} spec warnings", *(f"cdi-warning:{w}" for w in warnings))


def mounts(edits: CdiContainerEdits | None) -> list[str]:
    """The host side of each mount in edits."""
    return [mount.hostPath for mount in edits.mounts or []] if edits else []


def specs(seen: Seen, dirs: list[str]) -> list[str] | None:
    """Every host path the CDI specs in those folders mount, or None if a spec could not be read."""
    # The specs CDI reads (container-device-interface v1.1.1, the toolkit 1.20.1's, pkg/cdi/spec-dirs.go:74-103):
    # each folder one level deep (os.ReadDir follows a linked folder: -H), every entry but a directory (a link to a
    # spec counts; os.ReadFile follows it, as cat does), named *.yaml or *.json. One call prints each as NUL, its path,
    # NUL, its text, so a spec's text never has to be split by guessing.
    entries = (
        "-mindepth",
        "1",
        "-maxdepth",
        "1",
        "!",
        "-type",
        "d",
        "(",
        "-name",
        "*.yaml",
        "-o",
        "-name",
        "*.json",
        ")",
    )
    argv = (*C, "find", "-H", *dirs, *entries, "-printf", r"\0%p\0", "-exec", "cat", "{}", ";")
    done = seen.call(argv, frozenset({0, 1}))
    if done is None:
        return None
    # A folder Docker lists but that does not exist holds no spec; any other complaint is unread.
    absent = {f"find: '{d}'{GONE}" for d in dirs}
    if done.returncode and not set(done.stderr.splitlines()) <= absent:
        seen.unread.append("find could not list the CDI folders")
        return None
    parts = done.stdout.split("\0")
    if parts[0] or len(parts) % 2 == 0:
        seen.unread.append("find's listing of the CDI specs did not parse")
        return None
    paths = []
    for name, text in zip(parts[1::2], parts[2::2], strict=True):
        try:
            spec = CdiSpec.model_validate(yaml.safe_load(text))
        except (yaml.YAMLError, ValidationError) as failed:
            seen.unread.append(f"the CDI spec {name} did not parse: {type(failed).__name__}")
            return None
        paths += mounts(spec.containerEdits)
        for device in spec.devices or []:
            paths += mounts(device.containerEdits)
    return list(dict.fromkeys(paths))


def present(seen: Seen, paths: list[str]) -> None:
    """Fails each mounted path that does not exist on the PC."""
    if not paths:
        return
    done = seen.call((*C, "stat", "-L", "--printf", r"%n\0", "--", *paths), frozenset({0, 1}))
    if done is None:
        return
    found = set(done.stdout.split("\0"))
    # stat names each path it could not read, quoted as the shell would read it; only "No such file" confirms a path
    # is missing, any other reason leaves that path unread, and a path no message names is unread too.
    said = {}
    for row in done.stderr.splitlines():
        match = STAT_ERROR.fullmatch(row)
        if match is None:
            continue
        try:
            (name,) = shlex.split(match["name"])
        except ValueError:
            continue
        said[name] = match["why"]
    missing = [path for path in paths if path not in found and said.get(path) == GONE.removeprefix(": ")]
    unreadable = [path for path in paths if path not in found and path in said and path not in missing]
    seen.unread += [f"stat could not read {path}: {said[path]}" for path in unreadable]
    if unnamed := [path for path in paths if path not in found and path not in said]:
        seen.unread.append(f"stat said nothing about {len(unnamed)} paths it did not print")
    if missing:
        seen.fail(f"{len(missing)} paths the CDI specs mount are missing", *(f"file:{path}" for path in missing))


def driver(seen: Seen, installed: str | None) -> None:
    """Fails with driver-reboot-required when the loaded module is not the installed nvidia-utils."""
    done = seen.call(("cat", MODULE))
    if done is None:
        return
    match = LOADED.match(done.stdout)
    if match is None:
        seen.unread.append(f"{MODULE} did not name the module's version")
        return
    if installed is not None and match["version"] != installed:
        loaded = match["version"]
        seen.fail(f"the loaded module is {loaded} but nvidia-utils {installed} is installed: reboot", REBOOT)


def line(run: Run) -> PcDoctorLine:
    """The gpu-cdi line."""
    seen = Seen(run)
    installed = packages(seen)
    units(seen)
    dirs = folders(seen)
    if dirs is not None:
        if dirs:
            resolves(seen, dirs)
            paths = specs(seen, dirs)
            if paths is not None:
                present(seen, paths)
        else:
            seen.fail(f"Docker reads no CDI folder, so {DEVICE} cannot resolve", f"cdi:{DEVICE}")
    driver(seen, installed)
    return seen.line(f"{TOOLKIT} installed, refresh units set up, {DEVICE} resolves, its paths exist, driver loaded")
