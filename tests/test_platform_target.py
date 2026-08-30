# Copyright (c) 2026 Raymond Manaloto
"""Tests for the one platform parameter (dotfiles_setup.platform_target, #673).

Two layers, mirroring ``test_bash_budget.py``: isolated logic tests that pin the
host arch and the environment so both branches of every resolution rule are
exercised, and real-repo guards that the tree currently passes the gate, that a
planted literal FAILS it, and that the CLI wires end-to-end.

The FAIL arms matter more than the PASS arms here. A completeness gate verified
only on a clean tree is decoration (`.claude/rules/probes-need-a-control-arm.md`
rule 2), and the regression this gate exists to catch — a platform literal
re-appearing at a site nobody remembered — is invisible in a green run.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "python" / "src"))

from dotfiles_setup import platform_target
from dotfiles_setup.image import _is_emulated

REPO_ROOT = Path(__file__).parent.parent

AMD64_TRIPLE = "linux/amd64/v2"
ARM64_TRIPLE = "linux/arm64/v8"


class _FakeUname:
    """Just enough of ``os.uname_result`` for :func:`host_arch`."""

    def __init__(self, machine: str) -> None:
        self.machine = machine


@pytest.fixture
def _no_pin(monkeypatch: pytest.MonkeyPatch) -> None:
    """Run with the repo pin absent, so host fallback is reachable.

    Without this the ambient mise `[env]` supplies DOTFILES_PLATFORM and every
    fallback assertion would silently be testing the pin instead — a fixture
    that can only produce one answer (`probes-need-a-control-arm.md` rule 8).
    """
    monkeypatch.delenv(platform_target.PLATFORM_ENV_VAR, raising=False)


def _pin_host(monkeypatch: pytest.MonkeyPatch, machine: str) -> None:
    monkeypatch.setattr(platform_target.os, "uname", lambda: _FakeUname(machine))


# --------------------------------------------------------------------------
# Arch normalisation — uname and docker disagree on the spelling
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("token", "expected"),
    [
        ("x86_64", "amd64"),
        ("amd64", "amd64"),
        ("AMD64", "amd64"),
        ("  arm64 ", "arm64"),
        ("aarch64", "arm64"),
        ("riscv64", None),
        ("", None),
    ],
)
def test_normalize_arch(token: str, expected: str | None) -> None:
    assert platform_target.normalize_arch(token) == expected


@pytest.mark.parametrize(
    ("machine", "expected"),
    [("x86_64", AMD64_TRIPLE), ("arm64", ARM64_TRIPLE), ("aarch64", ARM64_TRIPLE)],
)
def test_host_platform_is_a_full_triple(
    monkeypatch: pytest.MonkeyPatch, machine: str, expected: str
) -> None:
    """The parameter carries a microarchitecture LEVEL, not an arch word."""
    _pin_host(monkeypatch, machine)
    assert platform_target.host_platform() == expected


def test_host_arch_refuses_an_unknown_machine(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Guessing a microarchitecture level would build an image nothing runs."""
    _pin_host(monkeypatch, "riscv64")
    with pytest.raises(ValueError, match="unsupported host architecture"):
        platform_target.host_arch()


# --------------------------------------------------------------------------
# Resolution order: override -> repo pin -> host native
# --------------------------------------------------------------------------


def test_override_beats_the_pin(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(platform_target.PLATFORM_ENV_VAR, AMD64_TRIPLE)
    assert platform_target.resolve_platform(ARM64_TRIPLE) == ARM64_TRIPLE


def test_pin_beats_the_host(monkeypatch: pytest.MonkeyPatch) -> None:
    """The repo pin is why #673 changes no behaviour on an arm64 Mac."""
    _pin_host(monkeypatch, "arm64")
    monkeypatch.setenv(platform_target.PLATFORM_ENV_VAR, AMD64_TRIPLE)
    assert platform_target.resolve_platform() == AMD64_TRIPLE


@pytest.mark.usefixtures("_no_pin")
def test_host_is_the_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    """Unpinned, the parameter really does default to the host architecture."""
    _pin_host(monkeypatch, "arm64")
    assert platform_target.resolve_platform() == ARM64_TRIPLE


@pytest.mark.usefixtures("_no_pin")
def test_blank_pin_is_not_a_pin(monkeypatch: pytest.MonkeyPatch) -> None:
    """An exported-but-empty var must fall through, not yield ``--platform=``."""
    _pin_host(monkeypatch, "x86_64")
    monkeypatch.setenv(platform_target.PLATFORM_ENV_VAR, "   ")
    assert platform_target.resolve_platform() == AMD64_TRIPLE


def test_explicit_env_mapping_is_honoured() -> None:
    assert (
        platform_target.resolve_platform(
            env={platform_target.PLATFORM_ENV_VAR: ARM64_TRIPLE}
        )
        == ARM64_TRIPLE
    )


# --------------------------------------------------------------------------
# Derived facts
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("triple", "arch", "os_arch", "machine"),
    [
        (AMD64_TRIPLE, "amd64", "linux/amd64", "x86_64"),
        (ARM64_TRIPLE, "arm64", "linux/arm64", "aarch64"),
        ("linux/amd64", "amd64", "linux/amd64", "x86_64"),
    ],
)
def test_derived_facts(triple: str, arch: str, os_arch: str, machine: str) -> None:
    assert platform_target.platform_arch(triple) == arch
    assert platform_target.os_arch(triple) == os_arch
    assert platform_target.expected_uname_machine(triple) == machine


def test_platform_arch_refuses_a_platform_with_no_arch() -> None:
    with pytest.raises(ValueError, match="no recognised architecture"):
        platform_target.platform_arch("linux/riscv64")


@pytest.mark.parametrize(
    ("host_machine", "triple", "emulated"),
    [
        ("x86_64", AMD64_TRIPLE, False),
        ("x86_64", ARM64_TRIPLE, True),
        ("arm64", AMD64_TRIPLE, True),
        ("arm64", ARM64_TRIPLE, False),
    ],
)
def test_is_emulated_both_arms(
    monkeypatch: pytest.MonkeyPatch,
    host_machine: str,
    triple: str,
    *,
    emulated: bool,
) -> None:
    """TSan aborts under emulation, so this must answer BOTH ways.

    ``image._is_emulated`` is asserted alongside because the mapping must exist
    once, not twice — a second copy is exactly how the two drift apart.
    """
    _pin_host(monkeypatch, host_machine)
    assert platform_target.is_emulated(triple) is emulated
    assert _is_emulated(triple) is emulated


@pytest.mark.parametrize(
    ("field", "expected"),
    [("triple", AMD64_TRIPLE), ("arch", "amd64"), ("machine", "x86_64")],
)
def test_platform_field(
    monkeypatch: pytest.MonkeyPatch, field: str, expected: str
) -> None:
    monkeypatch.setenv(platform_target.PLATFORM_ENV_VAR, AMD64_TRIPLE)
    assert platform_target.platform_field(field) == expected


def test_platform_field_rejects_an_unknown_name() -> None:
    with pytest.raises(ValueError, match="unknown platform field"):
        platform_target.platform_field("microarch")


# --------------------------------------------------------------------------
# The completeness gate — the tree, and a planted regression
# --------------------------------------------------------------------------


def test_repo_tree_has_no_stray_literals() -> None:
    violations = platform_target.find_violations(REPO_ROOT)
    assert violations == [], [v.render() for v in violations]


def test_repo_defaults_agree() -> None:
    assert platform_target.find_default_drift(REPO_ROOT) is None


def test_planted_literal_is_caught(tmp_path: Path) -> None:
    """FAIL arm: the regression is a literal at a site nobody remembered.

    Mutating a REAL consumer (a python module under the scanned tree) rather
    than a synthetic name, because a mutation that is not the real failure
    proves nothing.
    """
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    target = tmp_path / "python" / "src" / "dotfiles_setup" / "docker.py"
    target.parent.mkdir(parents=True)
    target.write_text('CMD = ["docker", "pull", "--platform", "linux/amd64/v2"]\n')
    subprocess.run(["git", "-C", str(tmp_path), "add", "-A"], check=True)

    violations = platform_target.find_violations(tmp_path)

    assert [v.literal for v in violations] == ["linux/amd64/v2"]
    assert violations[0].path == "python/src/dotfiles_setup/docker.py"
    assert violations[0].line == 1
    assert platform_target.PLATFORM_ENV_VAR in violations[0].render()


def test_untracked_literal_is_invisible_by_design(tmp_path: Path) -> None:
    """Control arm for the scan's bound: it enumerates the TRACKED tree.

    Stated rather than assumed, because "no findings" from a bounded search is
    not the same answer as "no literals".
    """
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    (tmp_path / "stray.py").write_text('P = "linux/amd64/v2"\n')

    assert platform_target.find_violations(tmp_path) == []


@pytest.mark.parametrize("excluded", ["tests/t.py", "docs/d.toml", "plugins/p.py"])
def test_excluded_trees_may_name_a_platform(tmp_path: Path, excluded: str) -> None:
    """Fixtures and archived evidence legitimately carry concrete platforms."""
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    target = tmp_path / excluded
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text('P = "linux/arm64/v8"\n')
    subprocess.run(["git", "-C", str(tmp_path), "add", "-A"], check=True)

    assert platform_target.find_violations(tmp_path) == []


def test_default_drift_between_the_two_permitted_sites(tmp_path: Path) -> None:
    """FAIL arm: bake and mise disagreeing is the split-brain, restated."""
    (tmp_path / "mise.toml").write_text(
        "[env]\n"
        f"{platform_target.PLATFORM_ENV_VAR} = "
        "\"{{ env.DOTFILES_PLATFORM | default(value='linux/amd64/v2') }}\"\n"
    )
    (tmp_path / "docker-bake.hcl").write_text(
        'variable "PLATFORM" {\n  default = "linux/arm64/v8"\n}\n'
    )

    drift = platform_target.find_default_drift(tmp_path)

    assert drift is not None
    assert "linux/amd64/v2" in drift
    assert "linux/arm64/v8" in drift


def test_a_deleted_default_is_a_failure_not_a_pass(tmp_path: Path) -> None:
    """A missing declaration must not read as 'the two agree'."""
    (tmp_path / "docker-bake.hcl").write_text(
        'variable "PLATFORM" {\n  default = "linux/amd64/v2"\n}\n'
    )

    drift = platform_target.find_default_drift(tmp_path)

    assert drift is not None
    assert platform_target.PLATFORM_ENV_VAR in drift


# --------------------------------------------------------------------------
# CLI wiring — a library nothing calls is not a gate
# --------------------------------------------------------------------------


def _cli(*args: str, platform: str | None = None) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    if platform is not None:
        env[platform_target.PLATFORM_ENV_VAR] = platform
    return subprocess.run(
        ["uv", "run", "--project", "python", "dotfiles-setup", *args],
        capture_output=True,
        text=True,
        check=False,
        cwd=REPO_ROOT,
        env=env,
    )


def test_platform_literals_cli_passes_on_the_real_tree() -> None:
    assert _cli("platform-literals").returncode == 0


@pytest.mark.parametrize(
    ("triple", "field", "expected"),
    [
        (AMD64_TRIPLE, "triple", AMD64_TRIPLE),
        (AMD64_TRIPLE, "machine", "x86_64"),
        (ARM64_TRIPLE, "machine", "aarch64"),
    ],
)
def test_platform_cli_prints_the_resolved_fact(
    triple: str, field: str, expected: str
) -> None:
    """`verify-arch` and the benchmark script read these; they must be exact.

    The pin is passed explicitly rather than inherited: a test that reads the
    ambient value would pass on whatever the shell happened to export, which is
    the one thing it must not certify.
    """
    result = _cli("platform", field, platform=triple)
    assert result.returncode == 0
    assert result.stdout.strip() == expected


# ──────────────────────────────────────────────────────────────────────
# #676 — the set of architectures the image PUBLISHES.
#
# The matrix cannot live in `.github/workflows/*.yml`: those files are scanned
# by `no_platform_literals`, so a triple written there fails the gate. Declaring
# it here and feeding it to the workflow through `fromJSON` is what that gate
# pushes you toward, and it means "which architectures do we ship" has exactly
# one answer in the tree.
# ──────────────────────────────────────────────────────────────────────


def test_published_targets_cover_every_declared_architecture() -> None:
    """Each published architecture yields one fully-resolved build target."""
    targets = platform_target.published_targets()
    assert [t.arch for t in targets] == list(platform_target.PUBLISHED_ARCHES)
    for target in targets:
        assert target.platform.startswith("linux/")
        assert platform_target.platform_arch(target.platform) == target.arch
        assert target.runner


def test_published_targets_are_natively_built_never_emulated() -> None:
    """No two architectures may share a runner label.

    Ray's ruling for #676 was a NATIVE runner matrix over one bake with two
    platforms, because the arm64 half would otherwise compile GCC 16.2 and
    clang-p2996 under QEMU — the ~2h build `docker-bake.hcl` already calls out.
    Two architectures pointing at one label is that rejected topology arriving
    by accident, and it would look like a normal green build.
    """
    runners = [t.runner for t in platform_target.published_targets()]
    assert len(set(runners)) == len(runners), f"shared runner label: {runners}"


def test_published_targets_carry_distinct_tags() -> None:
    """AC2: a per-architecture tag exists for each, and they cannot collide."""
    suffixes = [t.tag_suffix for t in platform_target.published_targets()]
    assert len(set(suffixes)) == len(suffixes)
    assert all(suffixes)


def test_the_repo_pin_is_one_of_the_published_architectures() -> None:
    """The devcontainer must be able to pull what CI publishes.

    `DOTFILES_PLATFORM` selects what `mise run up` asks the registry for. If the
    pin ever named an architecture the publish matrix omits, every local pull
    would fail against a manifest that genuinely lists two other architectures —
    a failure that reads as a registry problem, not a config one.
    """
    assert platform_target.find_unpublished_pin(REPO_ROOT) is None


def test_a_pin_outside_the_publish_matrix_is_reported(tmp_path: Path) -> None:
    """FAIL arm: the gate above is decoration unless the drift really fails.

    The fixture writes the same declaration shape `mise.toml` uses, naming an
    architecture no `PUBLISHED_ARCHES` entry ships.
    """
    (tmp_path / "mise.toml").write_text(
        "[env]\n"
        'DOTFILES_PLATFORM = "{{ env.DOTFILES_PLATFORM | '
        "default(value='linux/riscv64/v1') }}\"\n",
        encoding="utf-8",
    )
    message = platform_target.find_unpublished_pin(tmp_path)
    assert message is not None
    assert "riscv64" in message


def test_a_missing_pin_is_left_to_the_drift_check(tmp_path: Path) -> None:
    """One edit must not be reported as two problems.

    A deleted pin is `find_default_drift`'s finding; reporting it here as well
    would put two failures on screen for one cause, and the second names the
    publish matrix — which is not what broke.
    """
    (tmp_path / "mise.toml").write_text("[env]\n", encoding="utf-8")
    assert platform_target.find_unpublished_pin(tmp_path) is None
    assert platform_target.find_default_drift(tmp_path) is not None


def test_publish_matrix_json_is_parseable_and_complete() -> None:
    """The exact shape `fromJSON` consumes in the workflow — now 3 legs (#840)."""
    entries = json.loads(platform_target.publish_matrix_json())
    assert isinstance(entries, list)
    assert {key for entry in entries for key in entry} == {
        "platform",
        "arch",
        "runner",
        "tag_suffix",
        "role",
        "cache_eligible",
        "blocking",
    }
    assert len(entries) == len(platform_target.ci_matrix_targets())


def test_publish_matrix_cli_emits_one_line() -> None:
    """`>> $GITHUB_OUTPUT` is line-oriented: a wrapped payload breaks it."""
    proc = subprocess.run(
        [sys.executable, "-m", "dotfiles_setup.main", "platform-matrix"],
        capture_output=True,
        text=True,
        check=True,
        cwd=REPO_ROOT,
    )
    assert proc.stdout.count("\n") == 1
    assert len(json.loads(proc.stdout)) == len(platform_target.ci_matrix_targets())


# ──────────────────────────────────────────────────────────────────────
# #840: the non-blocking arm64/ubuntu-26.04-arm validation leg.
# ──────────────────────────────────────────────────────────────────────


def test_ci_matrix_adds_exactly_one_validation_leg() -> None:
    """The CI matrix is the publish matrix plus one explicit extra row."""
    ci_targets = platform_target.ci_matrix_targets()
    assert len(ci_targets) == len(platform_target.published_targets()) + 1
    assert ci_targets[: len(platform_target.published_targets())] == (
        platform_target.published_targets()
    )


def test_validation_leg_fields() -> None:
    """The validation leg's role/cache_eligible/blocking match the ticket."""
    validation = [
        t for t in platform_target.ci_matrix_targets() if t.role == "validate"
    ]
    assert len(validation) == 1
    leg = validation[0]
    assert leg.arch == "arm64"
    assert leg.runner == "ubuntu-26.04-arm"
    assert leg.cache_eligible is False
    assert leg.blocking is platform_target.UBUNTU_26_04_ARM_RUNNER_BLOCKING
    assert leg.blocking is False


def test_publish_legs_default_to_publish_role_and_are_unaffected() -> None:
    """#840 must not change the two existing legs' behavior at all."""
    for target in platform_target.published_targets():
        assert target.role == "publish"
        assert target.cache_eligible is True
        assert target.blocking is True


def test_manifest_membership_is_derived_from_role() -> None:
    """The manifest job filters `role == "publish"` — exactly the old set."""
    publish_only = [
        t for t in platform_target.ci_matrix_targets() if t.role == "publish"
    ]
    assert tuple(publish_only) == platform_target.published_targets()


def test_validation_leg_tag_namespace_never_collides_with_arm64_publish() -> None:
    """Same architecture, distinct tag/cache namespace — no shared marker."""
    ci_targets = platform_target.ci_matrix_targets()
    suffixes = [t.tag_suffix for t in ci_targets]
    assert len(set(suffixes)) == len(suffixes)
    arm64_publish = next(
        t for t in ci_targets if t.role == "publish" and t.arch == "arm64"
    )
    arm64_validate = next(t for t in ci_targets if t.role == "validate")
    assert arm64_publish.arch == arm64_validate.arch
    assert arm64_publish.tag_suffix != arm64_validate.tag_suffix
    assert not arm64_validate.tag_suffix.startswith("ubuntu")
    assert "26.04" not in arm64_validate.tag_suffix


def test_published_arch_without_a_runner_label_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """FAIL arm: adding an architecture without wiring its runner must not pass.

    Silently omitting the label would emit a matrix entry whose `runs-on` is
    empty — GitHub then queues the job against no runner and it hangs until the
    job timeout, which reads as a capacity problem rather than a config one.

    Declared through `PUBLISHED_ARCHES`, which is the edit a person actually
    makes; reaching for the private resolver would test a path no caller uses.
    """
    monkeypatch.setattr(platform_target, "PUBLISHED_ARCHES", ("amd64", "riscv64"))
    with pytest.raises(ValueError, match="riscv64"):
        platform_target.published_targets()


# --------------------------------------------------------------------------
# The image's OWN architecture (#698) — publishing an arch is not building it
# --------------------------------------------------------------------------


def test_every_published_arch_has_a_mise_lock_platform() -> None:
    """Mise spells the same axis a third way, and the locks are keyed by it.

    `PUBLISHED_ARCHES` says what CI builds, docker says `amd64`/`arm64`, and
    mise's lockfiles say `linux-x64`/`linux-arm64`. An architecture published
    without a lock-platform name resolves its tools for somebody else's CPU.
    """
    platforms = platform_target.mise_lock_platforms()
    assert len(platforms) == len(platform_target.PUBLISHED_ARCHES)
    assert len(set(platforms)) == len(platforms)


def test_a_published_arch_without_a_lock_platform_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """FAIL arm: an unmapped architecture must not silently resolve to nothing.

    Declared through `PUBLISHED_ARCHES` — the edit a person actually makes.
    """
    monkeypatch.setattr(platform_target, "PUBLISHED_ARCHES", ("amd64", "riscv64"))
    with pytest.raises(ValueError, match="riscv64"):
        platform_target.mise_lock_platforms()


def test_the_image_config_locks_every_published_architecture() -> None:
    """#698: the image resolved x86_64 tools while CI published two arches.

    `lockfile_platforms` scopes what `mise lock` writes, so an architecture
    missing from it gets **no lock entries at all** — and `mise install
    --locked` then resolves that architecture's tools from somebody else's
    platform. It survives the build (the self-checks counted tools rather than
    running them), so nothing fails until a binary is executed.
    """
    assert platform_target.find_lock_platform_drift(REPO_ROOT) is None


def test_an_uncovered_architecture_is_reported(tmp_path: Path) -> None:
    """FAIL arm: the gate above is decoration unless a narrow list really fails."""
    config = tmp_path / ".devcontainer" / "mise-system.toml"
    config.parent.mkdir(parents=True)
    config.write_text(
        '[settings]\nlockfile_platforms = ["linux-x64"]\n', encoding="utf-8"
    )

    message = platform_target.find_lock_platform_drift(tmp_path)

    assert message is not None
    assert "linux-arm64" in message


def test_a_deleted_lockfile_platforms_declaration_is_reported(tmp_path: Path) -> None:
    """A missing declaration must not read as 'every architecture is covered'.

    mise's own default is every platform it knows, so a reader could argue the
    absence is harmless. It is not: the declaration is what `image_lock.py`
    reads to decide which platforms to regenerate, so deleting it silently
    narrows the refresh instead of widening it.
    """
    config = tmp_path / ".devcontainer" / "mise-system.toml"
    config.parent.mkdir(parents=True)
    config.write_text("[settings]\nexperimental = true\n", encoding="utf-8")

    message = platform_target.find_lock_platform_drift(tmp_path)

    assert message is not None
    assert "lockfile_platforms" in message


def test_the_image_config_does_not_pin_a_literal_architecture() -> None:
    """#698 AC1: `arch` is derived from the build target, never a literal.

    Each matrix leg builds in a container OF its target architecture, so mise's
    own detection is already the target. A literal `arch` overrides that
    detection with whatever was true when the line was written.
    """
    assert platform_target.find_pinned_image_arch(REPO_ROOT) is None


@pytest.mark.parametrize(
    ("rel_path", "body"),
    [
        # The exact line #698 was filed for.
        (".devcontainer/mise-system.toml", '[settings]\narch = "x86_64"\n'),
        # The SAME setting under its environment spelling. Probed 2026-08-10:
        # `MISE_ARCH=x86_64 mise settings get arch` -> x86_64; unset -> "not
        # set". A gate that knew only the first spelling let this survive the
        # commit that claimed to remove the pin.
        (".devcontainer/mise-system.toml", '[env]\nMISE_ARCH = "x86_64"\n'),
        (".devcontainer/mise-system.toml", '[env]\nCONDA_SUBDIR = "linux-64"\n'),
        # And the same pins in the runtime spec, which the gate did not read
        # at all — `containerEnv` puts them in EVERY process in the container,
        # so a runtime `mise install` resolves the pinned architecture.
        # Written the way the real file is written — one key per line. A
        # single-line fixture would miss, because the scan anchors at line start
        # so that a COMMENTED pin does not re-trip the gate that removed it, and
        # a fixture the real format cannot produce proves nothing either way.
        (
            ".devcontainer/devcontainer.json",
            '{\n  "containerEnv": {\n    "MISE_ARCH": "x86_64"\n  }\n}\n',
        ),
        (
            ".devcontainer/devcontainer.json",
            '{\n  "containerEnv": {\n    "CONDA_SUBDIR": "linux-64"\n  }\n}\n',
        ),
    ],
)
def test_an_architecture_pin_is_reported_whatever_it_is_spelled(
    tmp_path: Path, rel_path: str, body: str
) -> None:
    """FAIL arms: one axis, three spellings, two files — all of them pin it.

    Enumerated rather than asserted (`feedback_enumerate_dont_assert_the_list`):
    the first version of this gate knew exactly the one spelling that had
    already been fixed, so it was armed only against the regression least
    likely to recur.
    """
    config = tmp_path / rel_path
    config.parent.mkdir(parents=True, exist_ok=True)
    config.write_text(body, encoding="utf-8")

    message = platform_target.find_pinned_image_arch(tmp_path)

    assert message is not None
    assert rel_path in message


def test_the_pin_scan_reads_every_file_that_can_carry_one() -> None:
    """Control arm: the real-tree PASS above is free if no file is read.

    Both checks are "no violation found" shaped, which an empty file list
    satisfies for nothing.
    """
    for rel_path in platform_target.IMAGE_ARCH_CONFIGS:
        assert (REPO_ROOT / rel_path).is_file(), f"{rel_path} is not on disk"


def test_a_commented_out_arch_pin_is_not_a_violation(tmp_path: Path) -> None:
    """A comment explaining why the pin was removed must not re-trip the gate.

    Without this the honest fix — deleting the line and saying why — fails the
    check that motivated it, and the next author deletes the explanation.
    """
    config = tmp_path / ".devcontainer" / "mise-system.toml"
    config.parent.mkdir(parents=True)
    config.write_text(
        '[settings]\n# arch = "x86_64" was removed by #698\nexperimental = true\n',
        encoding="utf-8",
    )

    assert platform_target.find_pinned_image_arch(tmp_path) is None
