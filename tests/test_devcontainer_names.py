# Copyright (c) 2026 Raymond Manaloto
"""Architecture-scoped devcontainer resource names (#677).

The failure this whole module exists to prevent is *silent*: docker creates a
named volume on first mount, so two architectures sharing one home volume do
not collide loudly — they interleave ``~/.local/share/mise/installs``,
``~/.cargo`` and ``~/.rustup`` until a binary of the wrong architecture is on
the path. Every assertion below therefore checks that the arch word is
genuinely *in* the name, not merely that two calls returned something.
"""

from __future__ import annotations

import hashlib
import re
import tomllib
from pathlib import Path

import pytest
from dotfiles_setup.devcontainer_names import (
    MIGRATION_MARKER,
    NAME_FIELDS,
    REFUSED_ACTIONS,
    SSH_PORT_BASE,
    SSH_PORT_ENV_VAR,
    SSH_PORT_SPAN,
    DevcontainerNames,
    HomeVolumeMigration,
    migration_platform_refusal,
    name_field,
    names_env,
    plan_home_volume_migration,
    resolve_names,
    ssh_port,
    teardown_container_ids,
    workspace_hash,
)

WORKSPACE = "/workspaces/dotfiles"
OTHER_WORKSPACE = "/Users/dev/dotfiles"
USER = "rmanaloto"
AMD64 = "linux/amd64/v2"
ARM64 = "linux/arm64/v8"


def _names(
    workspace: str = WORKSPACE,
    platform: str = AMD64,
    port_override: str | int | None = None,
    env: dict[str, str] | None = None,
) -> DevcontainerNames:
    """Resolve names against an EXPLICIT empty environment by default.

    `env={}` rather than `env=None`, because `None` means "read `os.environ`"
    and these tests then depend on the shell they run in. That is not
    hypothetical: `mise run ship` runs pytest under mise, which exports
    `DEVCONTAINER_SSH_PORT=4444` from this clone's `mise.local.toml` pin — so
    both architectures resolved to port 4444 and
    `test_both_architectures_collide_on_nothing` failed in `ship` after passing
    in a bare `uv run`. The test was right and the harness was leaky.
    """
    return resolve_names(
        workspace=workspace,
        user=USER,
        platform=platform,
        port_override=port_override,
        env={} if env is None else env,
    )


# ---------------------------------------------------------------- the hash


def test_workspace_hash_is_the_deployed_shell_scheme() -> None:
    """The python port must reproduce ``sha256sum | cut -c1-8`` exactly.

    A different digest renames every existing volume on the next `mise run up`,
    which presents as an empty home rather than as an error.
    """
    expected = hashlib.sha256(WORKSPACE.encode()).hexdigest()[:8]
    assert workspace_hash(WORKSPACE) == expected


def test_workspace_hash_golden_values() -> None:
    """Frozen goldens: an independent re-derivation cannot drift silently."""
    assert workspace_hash(WORKSPACE) == "be636185"
    assert workspace_hash(OTHER_WORKSPACE) == "01f20a06"


def test_workspace_hash_is_absolute_path_based() -> None:
    """A relative path resolves, so `mise run up` from a symlink is stable."""
    assert workspace_hash(WORKSPACE + "/") == workspace_hash(WORKSPACE)


# ------------------------------------------------------- the arch is in it


@pytest.mark.parametrize(
    ("platform", "arch"),
    [(AMD64, "amd64"), (ARM64, "arm64")],
)
def test_container_and_volume_carry_the_architecture(platform: str, arch: str) -> None:
    names = _names(platform=platform)
    assert names.arch == arch
    # The arch must be its own dash-delimited segment, not an accidental
    # substring of the hash — `-amd64-` cannot be produced by a hex digest.
    assert f"-{arch}-" in names.container
    assert names.home_volume.endswith(f"-{arch}-home")


def test_both_architectures_collide_on_nothing() -> None:
    """AC: both architectures up simultaneously, no name/volume/port collision."""
    amd = _names(platform=AMD64)
    arm = _names(platform=ARM64)
    assert amd.container != arm.container
    assert amd.home_volume != arm.home_volume
    assert amd.ssh_port != arm.ssh_port


def test_volume_name_excludes_the_port() -> None:
    """AC: changing a port must not orphan a home directory (C10/C11/C12)."""
    default = _names()
    moved = _names(port_override=45123)
    assert moved.ssh_port == 45123
    assert moved.home_volume == default.home_volume
    assert str(moved.ssh_port) not in moved.home_volume


def test_container_name_includes_the_port() -> None:
    """Two ports in one workspace+arch are two containers, not one."""
    assert _names(port_override=45123).container.endswith("-45123")


def test_legacy_volume_is_the_pre_677_name() -> None:
    """The migration source. If this drifts, the migration copies nothing."""
    names = _names()
    assert names.legacy_home_volume == f"dotfiles-dotfiles-{USER}-be636185-home"
    assert names.arch not in names.legacy_home_volume
    assert names.legacy_home_volume != names.home_volume


# --------------------------------------------------------------- the port


def test_second_working_directory_gets_a_distinct_port() -> None:
    """AC: without manual configuration."""
    here = _names(workspace=WORKSPACE)
    there = _names(workspace=OTHER_WORKSPACE)
    assert here.ssh_port != there.ssh_port


def test_derived_port_is_deterministic_and_in_range() -> None:
    for workspace in (WORKSPACE, OTHER_WORKSPACE):
        for arch in ("amd64", "arm64"):
            port = ssh_port(workspace, arch)
            assert port == ssh_port(workspace, arch)
            assert SSH_PORT_BASE <= port < SSH_PORT_BASE + SSH_PORT_SPAN


def test_derived_port_golden_values() -> None:
    """Frozen: a change here silently moves every clone's SSH port."""
    assert ssh_port(WORKSPACE, "amd64") == 21281
    assert ssh_port(WORKSPACE, "arm64") == 28455


def test_derived_port_avoids_the_macos_ephemeral_range() -> None:
    """The host hands out 49152-65535 to anonymous binds; a clash is a flaky R1."""
    assert SSH_PORT_BASE + SSH_PORT_SPAN <= 49152
    assert SSH_PORT_BASE > 1024


def test_explicit_override_wins_over_derivation() -> None:
    assert ssh_port(WORKSPACE, "amd64", override="4444") == 4444
    assert _names(env={SSH_PORT_ENV_VAR: "4444"}).ssh_port == 4444


def test_blank_override_falls_through_to_derivation() -> None:
    """An unset var reaches us from mise as the empty string, not as absence."""
    assert _names(env={SSH_PORT_ENV_VAR: "  "}).ssh_port == 21281


def test_resolution_is_hermetic_against_an_ambient_pin(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An ambient DEVCONTAINER_SSH_PORT must not reach an explicit-env resolve.

    The control arm for the leak that broke `ship`: with the variable really set
    in the process environment, an `env={}` resolve still derives, and an
    `env=None` resolve picks the ambient value up. If the first assertion ever
    starts matching 4444, the test harness has gone porous again.
    """
    monkeypatch.setenv(SSH_PORT_ENV_VAR, "4444")
    assert _names().ssh_port == 21281
    ambient = resolve_names(workspace=WORKSPACE, user=USER, platform=AMD64)
    assert ambient.ssh_port == 4444


def test_unparsable_override_fails_loud() -> None:
    """A typo'd port must not silently become a derived one."""
    with pytest.raises(ValueError, match="DEVCONTAINER_SSH_PORT"):
        ssh_port(WORKSPACE, "amd64", override="forty-four-forty-four")


# ------------------------------------------------------------- the exports


def test_names_env_covers_every_substitution_devcontainer_json_makes() -> None:
    env = names_env(_names())
    names = _names()
    assert set(env) == {
        "DEVCONTAINER_WORKSPACE_HASH",
        "DEVCONTAINER_ARCH",
        "DEVCONTAINER_NAME",
        "DEVCONTAINER_HOME_VOLUME",
        "DEVCONTAINER_WORKSPACE_LABEL",
        "DEVCONTAINER_ARCH_LABEL",
        "DEVCONTAINER_ID_FLAGS",
        SSH_PORT_ENV_VAR,
    }
    assert env["DEVCONTAINER_NAME"] == names.container
    assert env["DEVCONTAINER_HOME_VOLUME"] == names.home_volume
    # The id-label exports are what makes `up` arch-aware at all; a name-only
    # export set is exactly the state this ticket shipped and had to fix.
    assert env["DEVCONTAINER_ID_FLAGS"] == names.id_flags


def test_name_field_addresses_every_field() -> None:
    names = _names()
    for field in NAME_FIELDS:
        assert name_field(field, names)
    assert name_field("port", names) == str(names.ssh_port)


def test_name_field_rejects_an_unknown_field() -> None:
    with pytest.raises(ValueError, match="unknown devcontainer name field"):
        name_field("hostname", _names())


# ------------------------------------------------------------ the id labels
#
# These exist because the container NAME turned out to be decorative: in
# @devcontainers/cli 0.88.0 an existing container is looked up by *id labels*,
# and with none supplied they are inferred from the workspace folder alone. So
# an arm64 `up` in a directory that already has an amd64 container found and
# reused it. The tests below pin the two properties that fix makes load-bearing.


def test_id_labels_carry_both_workspace_and_arch() -> None:
    """Either one alone is wrong.

    Arch alone collides across clones (`--id-label` REPLACES the inferred
    folder label rather than extending it); workspace alone is what the CLI
    already inferred, i.e. no change at all.
    """
    names = _names()
    assert names.id_labels == (
        f"dotfiles.workspace={names.hash}",
        f"dotfiles.arch={names.arch}",
    )


def test_id_labels_differ_across_architectures_and_clones() -> None:
    here_amd = _names(platform=AMD64)
    here_arm = _names(platform=ARM64)
    there_amd = _names(workspace=OTHER_WORKSPACE, platform=AMD64)
    assert here_amd.id_labels != here_arm.id_labels
    assert here_amd.id_labels != there_amd.id_labels


def test_id_labels_are_whitespace_free() -> None:
    """`$DEVCONTAINER_ID_FLAGS` is used UNQUOTED in mise task bodies.

    That is only safe while every value is a hex digest or an arch word. If a
    component ever gains a space, word splitting silently truncates the flags
    and container lookup falls back to matching fewer labels than intended.
    """
    for names in (_names(), _names(platform=ARM64), _names(workspace=OTHER_WORKSPACE)):
        for label in names.id_labels:
            assert label.split() == [label]
        assert names.id_flags.split() == [
            "--id-label",
            names.workspace_label,
            "--id-label",
            names.arch_label,
        ]


def test_id_labels_match_the_cli_name_value_format() -> None:
    """The CLI rejects an id-label that does not match `.+=.+`."""
    for label in _names().id_labels:
        name, sep, value = label.partition("=")
        assert name
        assert sep
        assert value


def test_every_devcontainer_invocation_in_mise_toml_is_arch_scoped() -> None:
    """ENUMERATE the call sites; do not assert the one you remember.

    This is the gate that would have caught the original defect. The contracts
    written alongside the first implementation asserted that the *name* carries
    the architecture — true, and useless, because nothing looked a container up
    by name. Container identity is decided by ``--id-label``, so every `up` and
    every `exec` has to carry them; one that does not silently resolves by
    workspace folder and can reach the other architecture.

    Written against the file rather than a remembered list, because the count
    changes (8 `exec` sites today) and a hard-coded one rots into a no-op.
    """
    repo_root = Path(__file__).resolve().parent.parent
    text = (repo_root / "mise.toml").read_text(encoding="utf-8")
    # Join backslash continuations so a flag on the next line still counts.
    joined = text.replace("\\\n", " ")
    # Match a COMMAND, not prose: a `description = "... devcontainer up ..."`
    # line is documentation and caught this matcher out on its first run.
    invocation = re.compile(r"""^(?:run\s*=\s*["']+)?devcontainer\s+(?:up|exec)\s""")
    sites = [
        stripped
        for line in joined.splitlines()
        if (stripped := line.strip()) and invocation.match(stripped)
    ]
    # A floor, not an exact count: an exact one rots on the next task edit, but
    # without any floor a matcher that goes blind reports "all clear" (there
    # are 9 sites today — 1 `up`, 8 `exec`, plus dev-rebuild's `up`).
    assert len(sites) >= 5, f"matcher went blind — only found {sites}"
    unscoped = [
        line
        for line in sites
        if "--id-label" not in line and "$DEVCONTAINER_ID_FLAGS" not in line
    ]
    assert not unscoped, (
        "these devcontainer invocations resolve the container by WORKSPACE "
        f"FOLDER and can reach the other architecture: {unscoped}"
    )


_FNOX_DEVCONTAINER_UP = "fnox exec --non-interactive -- devcontainer up "


def _devcontainer_up_sites(mise_text: str) -> list[tuple[str, str]]:
    """Enumerate executable up commands from every declared mise task."""
    tasks = tomllib.loads(mise_text)["tasks"]
    sites: list[tuple[str, str]] = []
    for name, task in tasks.items():
        if not isinstance(task, dict) or not isinstance(task.get("run"), str):
            continue
        for line in task["run"].splitlines():
            command = line.strip()
            if command.startswith("#"):
                continue
            if re.search(r"\bdevcontainer\s+up(?:\s|$)", command):
                sites.append((name, command))
    return sites


def _assert_devcontainer_up_sites_are_fnox_scoped(mise_text: str) -> None:
    sites = _devcontainer_up_sites(mise_text)
    assert len(sites) >= 2, f"devcontainer up enumeration went blind: {sites}"
    unscoped = []
    for name, command in sites:
        if not command.startswith(_FNOX_DEVCONTAINER_UP):
            unscoped.append(name)
    assert not unscoped, f"unscoped devcontainer up tasks: {unscoped}"


def _remove_fnox_scope_from_task(mise_text: str, task_name: str) -> str:
    header = f"[tasks.{task_name}]"
    start = mise_text.index(header)
    end = mise_text.find("\n[tasks.", start + len(header))
    section = mise_text[start:] if end == -1 else mise_text[start:end]
    assert section.count(_FNOX_DEVCONTAINER_UP) == 1
    mutated = section.replace(_FNOX_DEVCONTAINER_UP, "devcontainer up ", 1)
    return (
        mise_text[:start] + mutated
        if end == -1
        else mise_text[:start] + mutated + mise_text[end:]
    )


def test_every_executable_devcontainer_up_site_is_fnox_scoped() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    _assert_devcontainer_up_sites_are_fnox_scoped(
        (repo_root / "mise.toml").read_text(encoding="utf-8")
    )


@pytest.mark.parametrize(
    ("mutated_task", "protected_task"),
    [("up", "dev-rebuild"), ("dev-rebuild", "up")],
)
def test_each_public_up_route_independently_requires_fnox_scope(
    mutated_task: str,
    protected_task: str,
) -> None:
    repo_root = Path(__file__).resolve().parent.parent
    original = (repo_root / "mise.toml").read_text(encoding="utf-8")
    mutated = _remove_fnox_scope_from_task(original, mutated_task)
    with pytest.raises(AssertionError, match=mutated_task):
        _assert_devcontainer_up_sites_are_fnox_scoped(mutated)
    sites = dict(_devcontainer_up_sites(mutated))
    assert sites[protected_task].startswith(_FNOX_DEVCONTAINER_UP)


def test_every_task_resolves_the_env_before_its_first_devcontainer_call() -> None:
    """The flags are useless if they are resolved after they are used.

    Caught for real: `persistence` had the resolver placed after its first two
    `devcontainer exec` calls, and died with `DEVCONTAINER_ID_FLAGS: unbound
    variable` on the first `verify-local` run. That is the GOOD failure — `set
    -u` turned it into a hard stop rather than an empty expansion that silently
    resolves the container by workspace folder.
    """
    repo_root = Path(__file__).resolve().parent.parent
    config = tomllib.loads((repo_root / "mise.toml").read_text(encoding="utf-8"))
    tasks = config["tasks"]
    late = []
    for name, task in tasks.items():
        body = task.get("run", "")
        if not isinstance(body, str) or "$DEVCONTAINER_ID_FLAGS" not in body:
            continue
        lines = [ln for ln in body.splitlines() if not ln.lstrip().startswith("#")]
        resolved = next(
            (i for i, ln in enumerate(lines) if ln.startswith("eval ")), None
        )
        used = next(
            (i for i, ln in enumerate(lines) if "$DEVCONTAINER_ID_FLAGS" in ln), None
        )
        if resolved is None or used is None or resolved > used:
            late.append(name)
    assert not late, f"these tasks use the id flags before resolving them: {late}"


# ------------------------------------------------------------- the teardown


def test_teardown_takes_this_arch_and_pre_677_leftovers() -> None:
    names = _names()
    ids = teardown_container_ids(
        names,
        this_arch=["mine"],
        legacy=["mine", "old"],
        legacy_labelled=["mine"],
    )
    assert ids == ["mine", "old"]


def test_teardown_leaves_the_other_architecture_alone() -> None:
    """The whole reason this is not a per-folder docker filter.

    `other` is the sibling architecture's container: it carries one of our
    workspace labels, so it is NOT a pre-#677 leftover and must survive a stop
    that was asked about this architecture.
    """
    names = _names()
    ids = teardown_container_ids(
        names,
        this_arch=["mine"],
        legacy=["mine", "other"],
        legacy_labelled=["mine", "other"],
    )
    assert ids == ["mine"]
    assert "other" not in ids


def test_teardown_is_empty_when_nothing_is_up() -> None:
    ids = teardown_container_ids(_names(), this_arch=[], legacy=[], legacy_labelled=[])
    assert ids == []


# ---------------------------------------------------------- the migration


def test_migration_is_skipped_when_the_legacy_volume_is_gone() -> None:
    plan = plan_home_volume_migration(_names(), existing_volumes=())
    assert plan.action == "nothing-to-migrate"
    assert plan.commands == ()


def test_completed_migration_is_recognised_by_its_marker() -> None:
    """Re-running after a completed migration must not copy over live state."""
    names = _names()
    plan = plan_home_volume_migration(
        names,
        existing_volumes=(names.legacy_home_volume, names.home_volume),
        target_populated=True,
        target_marked=True,
    )
    assert plan.action == "already-migrated"
    assert plan.commands == ()


def test_populated_but_unmarked_target_refuses_rather_than_guessing() -> None:
    """The interrupted-copy hole: non-empty is NOT the same as complete.

    A copy that dies partway through a 3.5 GB home leaves a target that is
    neither empty nor finished. Reading "non-empty" as "done" reported
    already-migrated and would have sent the user into a truncated home. It is
    also genuinely ambiguous — the same state is what `mise run up` leaves after
    real work — so the plan refuses and names both possibilities.
    """
    names = _names()
    plan = plan_home_volume_migration(
        names,
        existing_volumes=(names.legacy_home_volume, names.home_volume),
        target_populated=True,
        target_marked=False,
    )
    assert plan.action == "target-unverified"
    assert plan.commands == ()
    assert "docker volume rm" in plan.reason


def test_the_copy_writes_its_marker_last_and_in_one_shell() -> None:
    """Two docker runs could die between them and mark an incomplete copy."""
    names = _names()
    plan = plan_home_volume_migration(
        names, existing_volumes=(names.legacy_home_volume,)
    )
    copy = next(" ".join(c) for c in plan.commands if "cp -a" in " ".join(c))
    assert copy.index("cp -a") < copy.index(MIGRATION_MARKER)
    assert "set -e" in copy


def test_migration_resumes_over_an_interrupted_first_attempt() -> None:
    """AC: an interrupted first creation leaves a recoverable state.

    An empty-but-existing target is exactly what an interrupted copy leaves
    behind, so it must be treated as work to redo, never as work already done.
    """
    names = _names()
    plan = plan_home_volume_migration(
        names,
        existing_volumes=(names.legacy_home_volume, names.home_volume),
        target_populated=False,
    )
    assert plan.action == "copy"
    assert plan.commands


def test_migration_copies_from_legacy_into_the_arch_scoped_volume() -> None:
    names = _names()
    plan = plan_home_volume_migration(
        names, existing_volumes=(names.legacy_home_volume,)
    )
    assert isinstance(plan, HomeVolumeMigration)
    assert plan.action == "copy"
    joined = [" ".join(cmd) for cmd in plan.commands]
    copy = next(line for line in joined if "cp" in line)
    # Direction matters: reversing these two overwrites the surviving home.
    assert f"{names.legacy_home_volume}:/from:ro" in copy
    assert f"{names.home_volume}:/to" in copy
    assert copy.index(":/from") < copy.index(":/to")


def test_migration_refuses_to_guess_an_architecture() -> None:
    """Measured hazard, not theory.

    ``dotfiles-setup devcontainer env`` resolves ``amd64`` under ``mise run``
    (which supplies the repo pin) and ``arm64`` from a bare shell on this
    M-series Mac. The pre-#677 volume name records no architecture, so an
    unpinned copy would name its target for whichever machine happened to ask.
    """
    refusal = migration_platform_refusal(None, env={})
    assert refusal is not None
    assert "DOTFILES_PLATFORM" in refusal


def test_migration_proceeds_when_the_platform_is_pinned() -> None:
    assert migration_platform_refusal(None, env={"DOTFILES_PLATFORM": AMD64}) is None


def test_migration_proceeds_when_the_platform_is_explicit() -> None:
    """An explicit --platform beats an unset environment."""
    assert migration_platform_refusal(ARM64, env={}) is None


def test_blank_platform_pin_is_not_a_pin() -> None:
    """An unset variable renders as '', which must not read as an answer."""
    blank = migration_platform_refusal(None, env={"DOTFILES_PLATFORM": "  "})
    assert blank is not None


def test_migration_refuses_while_a_container_still_holds_the_source() -> None:
    """A live home is being WRITTEN to; `cp -a` would capture a torn record.

    Measured on the real host: the pre-#677 volume was 3.5 GB and mounted
    read-write by a running container. A torn home starts fine and misbehaves
    later, which is the worst shape of all — so refuse and say `mise run stop`.
    """
    names = _names()
    plan = plan_home_volume_migration(
        names,
        existing_volumes=(names.legacy_home_volume,),
        source_in_use=True,
    )
    assert plan.action == "source-in-use"
    assert plan.commands == ()
    assert "mise run stop" in plan.reason


def test_in_use_refusal_outranks_nothing_to_do() -> None:
    """Both arms of the in-use flag, on both source states.

    The refusal must not be reachable only when there is work, and a plain
    absent source must stay a no-op rather than becoming an error.
    """
    names = _names()
    idle = plan_home_volume_migration(
        names, existing_volumes=(names.legacy_home_volume,), source_in_use=False
    )
    assert idle.action == "copy"
    absent = plan_home_volume_migration(names, existing_volumes=(), source_in_use=True)
    assert absent.action == "nothing-to-migrate"


def test_refused_actions_are_distinguishable_from_nothing_to_do() -> None:
    """`--apply` exits non-zero on a refusal and zero on a genuine no-op.

    Both produce an empty command list, so without this split a refusal under
    `--apply` would look exactly like success to any caller reading the rc.
    """
    assert "source-in-use" in REFUSED_ACTIONS
    assert "nothing-to-migrate" not in REFUSED_ACTIONS
    assert "already-migrated" not in REFUSED_ACTIONS


def test_migration_never_deletes_the_legacy_volume() -> None:
    """The source is the only copy until the user is satisfied; `prune` removes it."""
    names = _names()
    plan = plan_home_volume_migration(
        names, existing_volumes=(names.legacy_home_volume,)
    )
    assert not any("rm" in " ".join(cmd).split() for cmd in plan.commands)
