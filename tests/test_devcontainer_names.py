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

import pytest
from dotfiles_setup.devcontainer_names import (
    NAME_FIELDS,
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
    return resolve_names(
        workspace=workspace,
        user=USER,
        platform=platform,
        port_override=port_override,
        env=env,
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


def test_unparsable_override_fails_loud() -> None:
    """A typo'd port must not silently become a derived one."""
    with pytest.raises(ValueError, match="DEVCONTAINER_SSH_PORT"):
        ssh_port(WORKSPACE, "amd64", override="forty-four-forty-four")


# ------------------------------------------------------------- the exports


def test_names_env_covers_every_substitution_devcontainer_json_makes() -> None:
    env = names_env(_names())
    assert set(env) == {
        "DEVCONTAINER_WORKSPACE_HASH",
        "DEVCONTAINER_ARCH",
        "DEVCONTAINER_NAME",
        "DEVCONTAINER_HOME_VOLUME",
        SSH_PORT_ENV_VAR,
    }
    assert env["DEVCONTAINER_NAME"] == _names().container
    assert env["DEVCONTAINER_HOME_VOLUME"] == _names().home_volume


def test_name_field_addresses_every_field() -> None:
    names = _names()
    for field in NAME_FIELDS:
        assert name_field(field, names)
    assert name_field("port", names) == str(names.ssh_port)


def test_name_field_rejects_an_unknown_field() -> None:
    with pytest.raises(ValueError, match="unknown devcontainer name field"):
        name_field("hostname", _names())


# ---------------------------------------------------------- the migration


def test_migration_is_skipped_when_the_legacy_volume_is_gone() -> None:
    plan = plan_home_volume_migration(_names(), existing_volumes=())
    assert plan.action == "nothing-to-migrate"
    assert plan.commands == ()


def test_migration_is_skipped_when_the_target_already_has_content() -> None:
    """Re-running after a completed migration must not copy over live state."""
    names = _names()
    plan = plan_home_volume_migration(
        names,
        existing_volumes=(names.legacy_home_volume, names.home_volume),
        target_populated=True,
    )
    assert plan.action == "already-migrated"
    assert plan.commands == ()


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


def test_migration_never_deletes_the_legacy_volume() -> None:
    """The source is the only copy until the user is satisfied; `prune` removes it."""
    names = _names()
    plan = plan_home_volume_migration(
        names, existing_volumes=(names.legacy_home_volume,)
    )
    assert not any("rm" in " ".join(cmd).split() for cmd in plan.commands)
