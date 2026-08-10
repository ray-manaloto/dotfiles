# Copyright (c) 2026 Raymond Manaloto
"""The one platform parameter (#673).

The target platform used to be a literal — ``linux/amd64/v2`` — repeated across
``docker-bake.hcl``, three ``mise.toml`` task envs, ``devcontainer.json``, five
Python modules, ``scripts/benchmark-docker.sh`` and two verification contracts.
Changing the target meant editing every one of them, and **missing two produces
a container that runs one architecture while a probe asserts another** — not a
crash, a false pass.

This module is the single resolver every one of those sites now goes through.

Resolution order
----------------

1. an explicit ``override`` argument (the caller asked for a specific arch),
2. the ``DOTFILES_PLATFORM`` environment variable — **the repo's pin**,
3. the host's own native triple.

Step 3 is why the parameter "defaults to the host architecture" (#673 AC1) while
behaviour stays unchanged (#673 AC4): the repo pins step 2 to ``linux/amd64/v2``
in ``mise.toml``'s global ``[env]``, so every flow that runs under mise resolves
to exactly what it resolved to before. When #676 publishes both architectures
and #678 brings up a native arm64 container, deleting that pin is what flips the
default to native — no other site changes.

A platform is a **triple**, not an arch word
--------------------------------------------

``linux/amd64/v2`` carries a *microarchitecture level*; arm64's analogue is
``linux/arm64/v8``. Every function here takes and returns the full triple, and
:func:`os_arch` is the explicit way to drop the level when a consumer (docker's
``--platform`` for an apt probe) only cares about the architecture.

Where the literal is still allowed
----------------------------------

Two files, listed in :data:`DEFAULT_LITERAL_SITES`. ``mise.toml`` is the pin
every mise-run flow reads. ``docker-bake.hcl`` must repeat it because CI's
``docker/bake-action`` jobs do not run under mise and HCL cannot read a TOML
file — see :func:`find_violations`, which forbids the literal everywhere else,
and :func:`find_default_drift`, which fails if the two ever disagree.
Collapsing them into one generated value is #680's codegen job, not this
ticket's.
"""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger(__name__)

__all__ = [
    "DEFAULT_LITERAL_SITES",
    "GCC_LATEST_ARCHES",
    "PLATFORM_ENV_VAR",
    "PLATFORM_FIELDS",
    "PUBLISHED_ARCHES",
    "PlatformLiteral",
    "PublishTarget",
    "expected_uname_machine",
    "find_default_drift",
    "find_lock_platform_drift",
    "find_pinned_image_arch",
    "find_unpublished_pin",
    "find_violations",
    "host_arch",
    "host_platform",
    "is_emulated",
    "mise_lock_platforms",
    "normalize_arch",
    "os_arch",
    "platform_arch",
    "platform_field",
    "platform_literals_main",
    "platform_main",
    "publish_matrix_json",
    "publish_matrix_main",
    "published_targets",
    "resolve_platform",
    "ships_gcc_latest",
]

PLATFORM_ENV_VAR = "DOTFILES_PLATFORM"

# Docker's architecture names, keyed by every spelling a host or a platform
# string may use for them. `uname -m` says x86_64/aarch64; docker says
# amd64/arm64; the two are not interchangeable and conflating them is how a
# probe ends up asserting the wrong machine.
_ARCH_ALIASES = {
    "x86_64": "amd64",
    "amd64": "amd64",
    "arm64": "arm64",
    "aarch64": "arm64",
}

# The microarchitecture level this project targets per architecture. amd64/v2 is
# the baseline the image is built for; arm64/v8 is its analogue.
_MICROARCH_LEVEL = {"amd64": "v2", "arm64": "v8"}

# What `uname -m` reports inside a container of each architecture — the value
# `mise run verify-arch` (R3) compares against.
_UNAME_MACHINE = {"amd64": "x86_64", "arm64": "aarch64"}

# The two files permitted to carry the literal; see the module docstring.
DEFAULT_LITERAL_SITES = ("mise.toml", "docker-bake.hcl")

# `linux/<arch>` with an optional microarchitecture level. Deliberately matches
# the arch words too (`linux/amd64` without a level), because a site that drops
# the level is exactly the split-brain this gate exists to catch.
_LITERAL_RE = re.compile(r"linux/(?:amd64|arm64|x86_64|aarch64)(?:/v\d+)?")

# Files scanned for a re-appearing literal. Prose and archived evidence are out
# of scope — a research report records what was true when it was written, and
# rewriting it would falsify the record (`agent-artifact-conventions.md`).
_SCANNED_SUFFIXES = (".py", ".toml", ".hcl", ".json", ".sh", ".yml", ".yaml")

# Tests legitimately name concrete platforms: a fixture asserting that another
# architecture bumps a content hash cannot express itself through the resolver
# it is testing without becoming tautological (`tests/AGENTS.md`).
_SCAN_EXCLUDED_PREFIXES = (
    "docs/",
    "missions/",
    "plugins/",
    "tests/",
)

# This module is the definition site: it composes every triple from
# `_MICROARCH_LEVEL` and never hard-codes one, but it must be able to NAME them
# — in its docstring, in the scan pattern, and in the explanation of why a
# triple is not an arch word. Documentation that cannot use the example is
# worse documentation, and this is the one file a reader comes to for the
# answer. Nothing here issues a `--platform`, so the exemption costs no
# coverage.
_SCAN_EXCLUDED_PATHS = ("python/src/dotfiles_setup/platform_target.py",)


# The architectures the published image ships as one manifest (#676), in the
# order the CI matrix runs them.
PUBLISHED_ARCHES = ("amd64", "arm64")

# The GitHub-hosted runner label that executes each architecture NATIVELY.
# Native is the whole ruling: a single bake emitting both platforms would build
# the arm64 half under QEMU, and that half compiles GCC 16.2 and clang-p2996 —
# the "~2h compiler" rebuild `docker-bake.hcl` already names, paid on emulated
# CPU. Availability of the arm label is measured, not assumed: a control-armed
# probe scheduled on it and asserted `uname -m` = aarch64 (#676).
_RUNNER_LABELS = {"amd64": "ubuntu-latest", "arm64": "ubuntu-24.04-arm"}

# The architectures whose image carries the kayari `gcc-latest` trunk snapshot.
#
# NOT a subset waiting to be widened: upstream states the policy on its index
# page — "Only the C and C++ compilers are included, and only for x86_64, in a
# single large package" — so there is nothing to wait for. arm64's modern-GCC
# slot is conda-forge's `gcc` instead, which does publish linux-aarch64.
#
# The published image is therefore NOT architecture-symmetric, and pretending
# otherwise is what a smoke check would do if it asserted this compiler
# unconditionally: it would fail an arm64 build over an artifact that does not
# exist. clang-p2996 is unaffected — it is built from source (#698).
GCC_LATEST_ARCHES = ("amd64",)

# mise's own spelling of each architecture — a THIRD name for the same axis,
# and the one both image lockfiles are keyed by. `uname -m` says x86_64, docker
# says amd64, mise says linux-x64; treating any two as interchangeable is how
# #698 shipped an arm64 image holding 131 x86_64 tool resolutions.
_MISE_LOCK_PLATFORM = {"amd64": "linux-x64", "arm64": "linux-arm64"}

# The image's system-wide mise config. Its `[settings]` decide what the IMAGE
# resolves, which is a different question from what CI publishes — #698 is
# precisely the two answers disagreeing.
IMAGE_MISE_CONFIG = ".devcontainer/mise-system.toml"

_LOCKFILE_PLATFORMS_RE = re.compile(
    r"^\s*lockfile_platforms\s*=\s*\[(?P<body>[^\]]*)\]", re.MULTILINE
)

# Anchored at line start so a COMMENTED pin (the honest record of why the line
# went away) does not re-trip the gate that removed it.
_PINNED_ARCH_RE = re.compile(
    r"^\s*arch\s*=\s*[\"'](?P<arch>[^\"']+)[\"']", re.MULTILINE
)


@dataclass(frozen=True)
class PublishTarget:
    """One architecture of the published image, fully resolved for CI.

    ``tag_suffix`` is what turns the moving tag into a per-architecture one
    (``:<sha>`` → ``:<sha>-arm64``). Every matrix leg must push a DISTINCT tag:
    they run concurrently against one registry, so two legs sharing a tag do not
    merge, they overwrite — and the loser's smoke result silently describes an
    image nobody can pull any more.
    """

    platform: str
    arch: str
    runner: str
    tag_suffix: str


def _publish_target(arch: str) -> PublishTarget:
    """Resolve one architecture, or raise naming what is unwired.

    Raises ``ValueError`` rather than defaulting a missing runner label to
    something plausible: an empty ``runs-on`` queues the job against no runner
    at all, so it hangs to the job timeout and reads as GitHub capacity rather
    than as this table being incomplete.
    """
    level = _MICROARCH_LEVEL.get(arch)
    runner = _RUNNER_LABELS.get(arch)
    if level is None or runner is None:
        missing = "microarchitecture level" if level is None else "runner label"
        msg = (
            f"architecture {arch!r} is declared in PUBLISHED_ARCHES but has no "
            f"{missing} — publishing it would emit an unbuildable matrix entry"
        )
        raise ValueError(msg)
    return PublishTarget(
        platform=f"linux/{arch}/{level}",
        arch=arch,
        runner=runner,
        tag_suffix=arch,
    )


def published_targets() -> tuple[PublishTarget, ...]:
    """Every architecture the image publishes, in matrix order."""
    return tuple(_publish_target(arch) for arch in PUBLISHED_ARCHES)


def publish_matrix_json() -> str:
    """The publish matrix as one line of JSON, for a workflow ``fromJSON``.

    One line because ``>> "$GITHUB_OUTPUT"`` is line-oriented — a pretty-printed
    payload is read as a truncated first line and the matrix silently loses
    every architecture after the first.
    """
    return json.dumps([asdict(target) for target in published_targets()])


def publish_matrix_main() -> int:
    """CLI entry: print the publish matrix for the CI job that fans out."""
    sys.stdout.write(f"{publish_matrix_json()}\n")
    return 0


def ships_gcc_latest(platform: str) -> bool:
    """Does an image built for ``platform`` carry the kayari gcc-latest deb?

    Asked of the platform rather than answered by a boolean the caller worked
    out, so the asymmetry in :data:`GCC_LATEST_ARCHES` is stated once.
    """
    return platform_arch(platform) in GCC_LATEST_ARCHES


def normalize_arch(token: str) -> str | None:
    """Docker's architecture name for ``token``, or ``None`` if unrecognised."""
    return _ARCH_ALIASES.get(token.strip().lower())


def host_arch() -> str:
    """This host's docker architecture name (``amd64`` / ``arm64``).

    Raises ``ValueError`` on an architecture this project has no
    microarchitecture level for, rather than guessing one — a wrong level
    silently builds an image the host cannot run.
    """
    machine = os.uname().machine
    arch = normalize_arch(machine)
    if arch is None:
        msg = (
            f"unsupported host architecture {machine!r}: this project targets "
            f"{sorted(_MICROARCH_LEVEL)} only"
        )
        raise ValueError(msg)
    return arch


def host_platform() -> str:
    """This host's native triple (``linux/arm64/v8`` on an M-series Mac)."""
    arch = host_arch()
    return f"linux/{arch}/{_MICROARCH_LEVEL[arch]}"


def resolve_platform(
    override: str | None = None,
    *,
    env: dict[str, str] | None = None,
) -> str:
    """The platform triple to target: ``override`` → repo pin → host native.

    ``env`` defaults to the ambient process environment and exists so callers
    (and tests) can resolve against an explicit mapping.
    """
    if override:
        return override
    environ = os.environ if env is None else env
    pinned = environ.get(PLATFORM_ENV_VAR, "").strip()
    if pinned:
        return pinned
    return host_platform()


def platform_arch(platform: str) -> str:
    """The docker architecture name inside a platform triple.

    Raises ``ValueError`` rather than defaulting, because every caller uses the
    answer to assert something — an assertion built on a guess cannot fail
    honestly.
    """
    for part in platform.split("/"):
        arch = normalize_arch(part)
        if arch is not None:
            return arch
    msg = f"no recognised architecture in platform {platform!r}"
    raise ValueError(msg)


def os_arch(platform: str) -> str:
    """``platform`` with its microarchitecture level dropped (``linux/amd64``).

    Used where a consumer resolves per-architecture artifacts and the level is
    meaningless — apt package pins are published per architecture, not per
    microarchitecture level.
    """
    return f"linux/{platform_arch(platform)}"


def expected_uname_machine(platform: str) -> str:
    """What ``uname -m`` reports inside a container of ``platform`` (R3)."""
    return _UNAME_MACHINE[platform_arch(platform)]


def is_emulated(platform: str) -> bool:
    """True when this host's CPU cannot *natively* execute ``platform``.

    ThreadSanitizer's shadow-memory layout requires a native x86_64 process;
    under Rosetta/QEMU emulation (arm64 host running an amd64 image) the TSan
    RUN aborts with an ASLR/"unexpected memory mapping" fatal. The host↔target
    mismatch is detected here — Python knows the host arch via ``os.uname()`` —
    rather than by probing ``binfmt_misc`` in-container, because the emulator
    marker is not reliably visible inside the container.
    """
    try:
        target = platform_arch(platform)
    except ValueError:
        return False
    try:
        return target != host_arch()
    except ValueError:
        return False


@dataclass(frozen=True)
class PlatformLiteral:
    """One re-appearing platform literal found by :func:`find_violations`."""

    path: str
    line: int
    literal: str

    def render(self) -> str:
        """One reviewer-facing line naming the site and the fix."""
        return (
            f"{self.path}:{self.line}: hard-coded platform literal "
            f"{self.literal!r} — resolve it from {PLATFORM_ENV_VAR} "
            f"(config) or dotfiles_setup.platform_target.resolve_platform() "
            f"(Python) instead"
        )


def _tracked_files(repo_root: Path) -> list[str]:
    proc = subprocess.run(
        ["git", "-C", str(repo_root), "ls-files", "-z"],
        capture_output=True,
        text=True,
        check=True,
    )
    return [entry for entry in proc.stdout.split("\0") if entry]


def _in_scope(rel_path: str) -> bool:
    if not rel_path.endswith(_SCANNED_SUFFIXES):
        return False
    if rel_path.startswith(_SCAN_EXCLUDED_PREFIXES):
        return False
    if rel_path in _SCAN_EXCLUDED_PATHS:
        return False
    return rel_path not in DEFAULT_LITERAL_SITES


def find_violations(repo_root: Path) -> list[PlatformLiteral]:
    """Every platform literal outside the two permitted default sites.

    Machine-enforced completeness (#673 AC3): careful editing threads the
    parameter through the sites you remembered, and this finds the ones you did
    not. It scans the *tracked* tree so a literal cannot arrive via a file the
    author forgot to add.
    """
    violations: list[PlatformLiteral] = []
    for rel_path in _tracked_files(repo_root):
        if not _in_scope(rel_path):
            continue
        target = repo_root / rel_path
        try:
            text = target.read_text(encoding="utf-8")
        except OSError, UnicodeDecodeError:
            continue
        violations.extend(
            PlatformLiteral(path=rel_path, line=lineno, literal=match.group(0))
            for lineno, line in enumerate(text.splitlines(), start=1)
            for match in _LITERAL_RE.finditer(line)
        )
    return violations


# The declaration each permitted site must carry the default in. mise.toml's
# is templated so a per-clone mise.local.toml override still works; bake's is a
# plain HCL variable default.
_MISE_DEFAULT_RE = re.compile(
    rf"^{PLATFORM_ENV_VAR}\s*=.*default\(value='([^']+)'\)", re.MULTILINE
)
_BAKE_DEFAULT_RE = re.compile(
    r'variable\s+"PLATFORM"\s*\{[^}]*default\s*=\s*"([^"]+)"', re.DOTALL
)


def _read_default(
    repo_root: Path, rel_path: str, pattern: re.Pattern[str]
) -> str | None:
    try:
        text = (repo_root / rel_path).read_text(encoding="utf-8")
    except OSError:
        return None
    match = pattern.search(text)
    return match.group(1) if match else None


def find_default_drift(repo_root: Path) -> str | None:
    """A message when the two permitted defaults disagree, else ``None``.

    ``docker-bake.hcl`` repeats the literal because CI's bake jobs do not run
    under mise and HCL cannot read a TOML file. That duplication is only safe
    while the two are equal, so it is checked rather than trusted — a retarget
    that edits one and forgets the other would publish an image of one
    architecture for a devcontainer that asks for the other.
    """
    mise_default = _read_default(repo_root, "mise.toml", _MISE_DEFAULT_RE)
    bake_default = _read_default(repo_root, "docker-bake.hcl", _BAKE_DEFAULT_RE)
    if mise_default is None:
        return (
            f"mise.toml no longer declares a {PLATFORM_ENV_VAR} default — it is "
            f"the one place the platform is chosen"
        )
    if bake_default is None:
        return 'docker-bake.hcl no longer declares a `variable "PLATFORM"` default'
    if mise_default != bake_default:
        return (
            f"platform default drift: mise.toml says {mise_default!r} but "
            f"docker-bake.hcl says {bake_default!r} — CI would build one "
            f"architecture while the devcontainer asks for the other"
        )
    return None


def find_unpublished_pin(repo_root: Path) -> str | None:
    """A message when the repo's pin names an architecture CI does not publish.

    ``DOTFILES_PLATFORM`` decides what ``mise run up`` asks the registry for,
    and :data:`PUBLISHED_ARCHES` decides what CI puts there. Nothing else ties
    the two together, so they can drift apart in a one-line edit — and the
    result is a devcontainer that cannot start, reporting a manifest error
    against a tag that genuinely exists and genuinely lists two other
    architectures. That reads as a registry problem for as long as it takes
    someone to compare these two declarations by hand.

    Returns ``None`` when they agree, so it composes with the literal scan in
    :func:`platform_literals_main`.
    """
    pinned = _read_default(repo_root, "mise.toml", _MISE_DEFAULT_RE)
    if pinned is None:
        # `find_default_drift` already reports a missing pin, and reporting it
        # twice would make one edit look like two problems.
        return None
    published = {target.platform for target in published_targets()}
    if pinned not in published:
        return (
            f"the repo pins {pinned!r} but the publish matrix ships "
            f"{sorted(published)} — `mise run up` would ask the registry for an "
            f"architecture no build produces"
        )
    return None


def mise_lock_platforms() -> tuple[str, ...]:
    """Mise's lock-platform name for every published architecture.

    Raises ``ValueError`` naming the architecture rather than skipping it: a
    silently-dropped platform produces a lockfile that is complete by its own
    definition and wrong by the build's, which is the #698 failure exactly.
    """
    platforms: list[str] = []
    for arch in PUBLISHED_ARCHES:
        platform = _MISE_LOCK_PLATFORM.get(arch)
        if platform is None:
            msg = (
                f"architecture {arch!r} is declared in PUBLISHED_ARCHES but has "
                f"no mise lock-platform name — its tools would be resolved for "
                f"another architecture"
            )
            raise ValueError(msg)
        platforms.append(platform)
    return tuple(platforms)


def _image_mise_config(repo_root: Path) -> str | None:
    try:
        return (repo_root / IMAGE_MISE_CONFIG).read_text(encoding="utf-8")
    except OSError:
        return None


def find_lock_platform_drift(repo_root: Path) -> str | None:
    """A message when the image locks fewer architectures than CI publishes.

    ``lockfile_platforms`` scopes what ``mise lock`` writes, so an architecture
    absent from it gets **no lock entries at all** — and ``mise install
    --locked`` then resolves that architecture's tools from whatever platform is
    present. The build survives it, because the build-time self-checks count
    installed tools rather than executing them, so the first honest failure is a
    binary that will not run, hours later at smoke.

    ``image_lock.py`` also reads this declaration to decide which platforms to
    regenerate, which is why a *missing* declaration is reported rather than
    read as "all platforms": deleting it narrows the refresh silently.
    """
    text = _image_mise_config(repo_root)
    if text is None:
        return None
    match = _LOCKFILE_PLATFORMS_RE.search(text)
    if match is None:
        return (
            f"{IMAGE_MISE_CONFIG} declares no `lockfile_platforms` — "
            f"`mise run lock-image` reads it to decide which platforms to "
            f"regenerate, so its absence narrows the locks instead of widening "
            f"them. Expected {list(mise_lock_platforms())}"
        )
    declared = {token.strip().strip("\"'") for token in match.group("body").split(",")}
    missing = [p for p in mise_lock_platforms() if p not in declared]
    if missing:
        return (
            f"{IMAGE_MISE_CONFIG} locks {sorted(declared - {''})} but the publish "
            f"matrix ships {list(PUBLISHED_ARCHES)} — {missing} would get no lock "
            f"entries, so those architectures resolve another platform's tools"
        )
    return None


def find_pinned_image_arch(repo_root: Path) -> str | None:
    """A message when the image config pins ``arch`` to a literal (#698 AC1).

    Every matrix leg builds inside a container OF its target architecture, so
    mise's own detection already *is* the build target. A literal overrides that
    detection with whatever was true the day the line was written — and unlike a
    wrong ``--platform``, nothing downstream contradicts it: the image is built
    for one architecture and filled with another's binaries.
    """
    text = _image_mise_config(repo_root)
    if text is None:
        return None
    match = _PINNED_ARCH_RE.search(text)
    if match is None:
        return None
    return (
        f'{IMAGE_MISE_CONFIG} pins `arch = "{match.group("arch")}"` — the image '
        f"would resolve that architecture's tools whatever it is being built for. "
        f"Delete the line: each matrix leg builds in a container of its own "
        f"architecture, so mise's detection is already the build target"
    )


#: What ``dotfiles-setup platform <field>`` can print. Shell callers (the
#: `verify-arch` task) read these instead of re-implementing the triple→arch
#: and triple→uname mappings in bash ([[zero-bash-logic]]).
PLATFORM_FIELDS = ("triple", "arch", "machine")


def platform_field(field: str, *, platform: str | None = None) -> str:
    """One resolved platform fact, addressed by name.

    ``triple`` is the platform itself, ``arch`` docker's architecture name and
    ``machine`` what ``uname -m`` reports inside a container of it.
    """
    resolved = resolve_platform(platform)
    if field == "triple":
        return resolved
    if field == "arch":
        return platform_arch(resolved)
    if field == "machine":
        return expected_uname_machine(resolved)
    msg = f"unknown platform field {field!r}: expected one of {PLATFORM_FIELDS}"
    raise ValueError(msg)


def platform_main(field: str) -> int:
    """CLI entry: print one resolved platform fact on stdout."""
    sys.stdout.write(f"{platform_field(field)}\n")
    return 0


def platform_literals_main(repo_root: Path) -> int:
    """CLI entry: report re-appearing literals and default drift; exit 1 if any."""
    failed = False
    checks = (
        find_default_drift(repo_root),
        find_unpublished_pin(repo_root),
        find_lock_platform_drift(repo_root),
        find_pinned_image_arch(repo_root),
    )
    for message in checks:
        if message is not None:
            failed = True
            logger.error("platform-literals FAIL: %s", message)
    violations = find_violations(repo_root)
    if violations:
        failed = True
        logger.error(
            "platform-literals FAIL: %d hard-coded literal(s) outside the "
            "permitted defaults (%s). The platform is ONE parameter (#673): "
            "config resolves it from %s, Python from "
            "dotfiles_setup.platform_target.resolve_platform()",
            len(violations),
            ", ".join(DEFAULT_LITERAL_SITES),
            PLATFORM_ENV_VAR,
        )
        for violation in violations:
            logger.error("platform-literals %s", violation.render())
    if failed:
        return 1
    logger.info(
        "platform-literals OK: the only platform defaults are %s, and they agree",
        ", ".join(DEFAULT_LITERAL_SITES),
    )
    return 0
