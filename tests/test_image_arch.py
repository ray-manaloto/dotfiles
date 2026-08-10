# Copyright (c) 2026 Raymond Manaloto
"""The image's own architecture handling (#698).

#676 published an arm64 image; #698 is the discovery that the *contents* were
still amd64. Two independent causes, and this module pins both:

1. **mise resolved x86_64 tools** into whatever it was building, because
   ``mise-system.toml`` pinned ``arch``. Covered by ``test_platform_target.py``;
   what is covered here is the build-time consequence — the existing self-checks
   COUNT installed tools (``mise ls --installed | wc -l``), and a count cannot
   see a binary that will not run. Only executing one can.

2. **Two hand-downloaded ``.deb``s are single-architecture.** graphviz publishes
   no Linux arm64 build and ``gcc-latest`` publishes none by upstream policy
   ("only for x86_64"), so both downloads must be gated on ``TARGETARCH``.

The sharpest trap here is BuildKit's: ``TARGETARCH`` is an *automatic* build
arg, and an automatic arg that a stage does not declare expands to the **empty
string** rather than erroring. A stage that branches on an undeclared
``TARGETARCH`` therefore takes the else-branch on EVERY architecture — so the
amd64 image would silently lose the very packages this gating exists to keep,
and nothing in the build would say so.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "python" / "src"))

from dotfiles_setup import image, platform_target

REPO_ROOT = Path(__file__).parent.parent
DOCKERFILE = REPO_ROOT / ".devcontainer" / "Dockerfile"
SHARED_FRAGMENT = REPO_ROOT / ".config" / "mise" / "conf.d" / "shared.toml"

#: The build args whose payloads only exist for amd64.
_SINGLE_ARCH_DOWNLOADS = ("GRAPHVIZ_DEB", "GCC_LATEST_DEB")

_STAGE_RE = re.compile(r"^FROM\s+.*?\s+AS\s+(?P<name>\S+)", re.IGNORECASE)
_PROBES_RE = re.compile(r'^ARG\s+ARCH_EXEC_PROBES="(?P<names>[^"]+)"', re.MULTILINE)

# The OPERATOR is captured deliberately. Reading only the operand makes
# `= "amd64"` and `!= "amd64"` indistinguishable, so a sign inversion — install
# the x86_64-only deb on arm64, skip it on amd64 — would pass every assertion
# here. That is the realistic regression, and it is the one a bare operand
# check cannot see.
_TARGETARCH_TEST_RE = re.compile(
    r'\$\{TARGETARCH\}"?\s*(?P<op>!?=)\s*"(?P<arch>[^"]+)"'
)


def _dockerfile() -> str:
    return DOCKERFILE.read_text(encoding="utf-8")


def _stages(text: str) -> dict[str, str]:
    """The Dockerfile split into stage bodies, keyed by stage name.

    Build args do not cross a ``FROM``, which is exactly why an undeclared
    automatic arg is a live hazard rather than a style point — so the unit this
    module reasons about has to be the stage, not the file.
    """
    stages: dict[str, list[str]] = {}
    current: list[str] | None = None
    for line in text.splitlines():
        match = _STAGE_RE.match(line)
        if match is not None:
            current = stages.setdefault(match.group("name"), [])
            continue
        if current is not None:
            current.append(line)
    return {name: "\n".join(body) for name, body in stages.items()}


def _declared_tools() -> set[str]:
    """Tool names declared in the shared host↔image mise fragment."""
    text = SHARED_FRAGMENT.read_text(encoding="utf-8")
    body = text.split("[tools]", 1)[1]
    return {
        match.group(1).strip('"')
        for match in re.finditer(r'^([A-Za-z0-9_."\-:]+)\s*=', body, re.MULTILINE)
    }


# --------------------------------------------------------------------------- #
# The build-time check must EXECUTE, not count
# --------------------------------------------------------------------------- #


def test_the_dockerfile_declares_architecture_execution_probes() -> None:
    """A named, reviewable set — not an unbounded "run everything" sweep."""
    match = _PROBES_RE.search(_dockerfile())
    assert match is not None, (
        'no `ARG ARCH_EXEC_PROBES="..."` in the Dockerfile — the build has no '
        "check that a mise-installed binary can actually run on the target "
        "architecture, which is how #698 survived to smoke"
    )
    assert len(match.group("names").split()) >= 3


def test_every_execution_probe_is_a_tool_the_image_installs() -> None:
    """A probe naming an uninstalled tool can only fail — or become a no-op.

    Cross-checked against the shared fragment rather than against a second list
    here, so a tool rename breaks this test instead of the image build.
    """
    match = _PROBES_RE.search(_dockerfile())
    assert match is not None
    declared = _declared_tools()

    unknown = [name for name in match.group("names").split() if name not in declared]

    assert unknown == [], (
        f"execution probes name tools the shared fragment does not declare: "
        f"{unknown}. Declared: {sorted(declared)}"
    )


def test_the_probe_loop_runs_the_binary_rather_than_testing_for_it() -> None:
    """#698's whole lesson: presence is not capability.

    A wrong-architecture binary is present, is executable by its mode bits, and
    is counted by `mise ls --installed`. The only thing it cannot do is run.
    """
    text = _dockerfile()
    probe_block = text.split("ARCH_EXEC_PROBES", 1)[1]

    assert "--version" in probe_block.split("\nRUN ", 2)[1], (
        "the architecture probe block never invokes a probe binary — a check "
        "that only stats the file reproduces the defect it exists to catch"
    )


# --------------------------------------------------------------------------- #
# The single-architecture downloads must be gated — and the gate must be armed
# --------------------------------------------------------------------------- #


def test_each_single_architecture_download_is_gated_on_target_arch() -> None:
    """Graphviz ships no Linux arm64 deb; gcc-latest ships none by policy."""
    text = _dockerfile()
    for arg in _SINGLE_ARCH_DOWNLOADS:
        run_block = next(
            block
            for block in text.split("\nRUN ")[1:]
            if f"${{{arg}}}" in block and "curl" in block
        )
        assert "TARGETARCH" in run_block, (
            f"the {arg} download is not gated on TARGETARCH — it is an amd64-only "
            f"artifact, so an arm64 build fails on it (measured: graphviz "
            f"`exit code: 100`, job 93363618928)"
        )


def test_the_graphviz_fallback_installs_every_engine_the_smoke_exercises() -> None:
    """A per-architecture fallback must be CAPABILITY-equivalent, not just present.

    The amd64 branch installs graphviz's plugin dependencies by hand; Ubuntu
    splits the layout engines into separate packages and `graphviz` Depends on
    only the gd and pango plugins, so `--no-install-recommends` produces an
    install where `dot` works and `neato` reports "There is no layout engine
    support". The shared smoke below the branch renders with BOTH, so the
    fallback silently fails the whole RUN — measured on the arm64 base
    2026-08-10, and it is what reddened #703 after the gating itself was right.
    """
    graphviz_run = next(
        block
        for block in _dockerfile().split("\nRUN ")[1:]
        if "${GRAPHVIZ_DEB}" in block
    )
    fallback = graphviz_run.split("else", 1)[1]

    for engine in ("neato",):
        if f"| {engine} -T" not in graphviz_run:
            continue
        assert f"libgvplugin-{engine}-layout" in fallback, (
            f"the smoke renders with `{engine}`, but the apt fallback does not "
            f"install its layout plugin — `dot` would work and `{engine}` would "
            f"not, failing the RUN on every non-amd64 build"
        )


def test_every_stage_that_reads_targetarch_also_declares_it() -> None:
    """The trap that would make this whole change a silent no-op.

    ``TARGETARCH`` is an automatic build arg: BuildKit provides its VALUE, but
    only to stages that declare `ARG TARGETARCH`. Undeclared, it expands to the
    empty string — so `[ "${TARGETARCH}" = "amd64" ]` is false on amd64 too, and
    the amd64 image silently loses graphviz and GCC-17 while the build stays
    green. Nothing else in this repo would notice until smoke.
    """
    declares = re.compile(r"^ARG\s+TARGETARCH", re.MULTILINE)
    offenders = [
        name
        for name, body in _stages(_dockerfile()).items()
        if "${TARGETARCH}" in body and not declares.search(body)
    ]

    assert offenders == [], (
        f"stages read ${{TARGETARCH}} without declaring `ARG TARGETARCH`: "
        f"{offenders}. An undeclared automatic arg is EMPTY, so every "
        f"architecture takes the else-branch"
    )


def test_targetarch_is_only_compared_against_docker_architecture_names() -> None:
    """``TARGETARCH`` is ``amd64``/``arm64`` — never ``x86_64``/``aarch64``.

    Three spellings of one axis meet in this file: `uname -m` says x86_64,
    docker says amd64, mise says linux-x64. A comparison against the wrong
    spelling is always false, so the guarded branch never runs and the build
    stays green while silently doing the other thing — the same shape as the
    undeclared-ARG trap, reached by a different mistake.
    """
    compared = {m.group("arch") for m in _TARGETARCH_TEST_RE.finditer(_dockerfile())}

    assert compared, "no ${TARGETARCH} comparison found — the gating is gone"
    assert compared <= set(platform_target.PUBLISHED_ARCHES), (
        f"TARGETARCH compared against non-docker architecture name(s): "
        f"{sorted(compared - set(platform_target.PUBLISHED_ARCHES))}. "
        f"BuildKit sets TARGETARCH to {list(platform_target.PUBLISHED_ARCHES)}"
    )


# --------------------------------------------------------------------------- #
# The smoke must check what the image actually contains
# --------------------------------------------------------------------------- #


def test_the_dockerfile_gate_and_the_smoke_agree_on_who_ships_gcc_latest() -> None:
    """One fact stated in two languages must be bound, not trusted.

    The Dockerfile decides with a shell comparison on `TARGETARCH`; the smoke
    script decides from `GCC_LATEST_ARCHES`. Left unbound, they drift into the
    two failure modes that look nothing alike: an image carrying a compiler
    nothing verifies, or a smoke demanding one that was never installed.
    """
    gcc_run = next(
        block
        for block in _dockerfile().split("\nRUN ")[1:]
        if "${GCC_LATEST_DEB}" in block and "curl" in block
    )
    tests = [
        (m.group("op"), m.group("arch")) for m in _TARGETARCH_TEST_RE.finditer(gcc_run)
    ]

    assert tests, "the gcc-latest download is no longer gated on TARGETARCH"
    for op, arch_name in tests:
        # The branch installs on GCC_LATEST_ARCHES and skips elsewhere. Written
        # as `!= "amd64"` -> skip, so an `=` here is the sign inversion that
        # installs an x86_64-only deb on arm64 and drops it from amd64.
        assert op == "!=", (
            f'gcc-latest is gated `{op} "{arch_name}"`, which INVERTS the '
            f"branch: the x86_64-only deb would install on every OTHER "
            f"architecture and be skipped on the one that has it"
        )
        assert arch_name in platform_target.GCC_LATEST_ARCHES

    assert {arch for _, arch in tests} == set(platform_target.GCC_LATEST_ARCHES)


def test_the_smoke_skips_gcc_latest_where_the_image_omits_it() -> None:
    """An arm64 smoke must not fail on a compiler upstream never published."""
    script = image.build_tier3_script(
        expected_p2996_ref="a" * 40, emulated=False, gcc_latest=False
    )

    assert "GCC_LATEST_PRESENT=''\n" in script


def test_the_smoke_still_demands_gcc_latest_where_the_image_ships_it() -> None:
    """Control arm: the skip above is only safe if the check is real elsewhere.

    A gate that skips on every architecture is indistinguishable from a deleted
    gate, and this is exactly the arm that would not have been run.
    """
    script = image.build_tier3_script(
        expected_p2996_ref="a" * 40, emulated=False, gcc_latest=True
    )

    assert "GCC_LATEST_PRESENT=1\n" in script
    assert "/opt/gcc-latest/bin/g++" in script


def test_the_smoke_derives_gcc_latest_from_the_platform_it_is_given() -> None:
    """The caller states an architecture, not a boolean it had to work out.

    `build_smoke_docker_cmd` already resolves `emulated` this way; deciding
    `gcc_latest` anywhere else would put the asymmetry in a second place.
    """
    amd64 = image.build_smoke_docker_cmd("img", platform="linux/amd64/v2")
    arm64 = image.build_smoke_docker_cmd("img", platform="linux/arm64/v8")

    assert "GCC_LATEST_PRESENT=1\n" in amd64[-1]
    assert "GCC_LATEST_PRESENT=''\n" in arm64[-1]


@pytest.mark.parametrize(
    ("platform", "expected"),
    [
        ("linux/amd64/v2", "GCC_LATEST_PRESENT=1\n"),
        ("linux/arm64/v8", "GCC_LATEST_PRESENT=''\n"),
    ],
)
def test_the_devcontainer_smoke_cli_also_derives_gcc_latest(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    platform: str,
    expected: str,
) -> None:
    """The CI path and the devcontainer path must agree about the image.

    `build_smoke_docker_cmd` derives this from the platform; `smoke_script_main`
    is the OTHER caller — the one `scripts/devcontainer-smoke.sh` evaluates. Left
    at its default it would demand gcc-latest inside an arm64 container that
    deliberately omits it, failing `verify-container-latest` on an image that is
    correct by design.
    """
    monkeypatch.setenv(platform_target.PLATFORM_ENV_VAR, platform)

    assert image.smoke_script_main(3) == 0

    assert expected in capsys.readouterr().out


def test_the_stage_split_really_finds_the_image_stages() -> None:
    """Control arm: the check above is vacuous if no stage body is parsed.

    Every assertion here is a "no offenders found" shape, which an empty parse
    satisfies for free.
    """
    stages = _stages(_dockerfile())

    assert "devcontainer" in stages
    assert any("${TARGETARCH}" in body for body in stages.values()), (
        "no stage body mentions ${TARGETARCH} — either the gating is gone or "
        "the parser stopped seeing stage bodies"
    )
