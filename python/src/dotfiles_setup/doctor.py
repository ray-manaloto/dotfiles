# Copyright (c) 2026 Raymond Manaloto
"""Project doctor: does this repo's DECLARED setup match reality on this host?

Every gate this repo has looks *inside the working tree*. ``mise run lint``,
``pytest``, ``mise run verify`` and ``mise run lint-docs`` are all blind to the
seam between the repo, the host's credential store, and Claude Code's plugin
config — and session 2026-07-29 found three live defects living in exactly that
seam (#418):

1. **Context7 MCP running anonymous.** The plugin's ``.mcp.json`` interpolates
   ``${CONTEXT7_API_KEY:-}``; the variable is exec-only in fnox, so the header
   resolved to an EMPTY STRING. The server reported ``connected`` throughout —
   the failure mode is a silent tier downgrade, not an error.
2. **The fnox env-mode settings were one ``bootstrap-config`` run from a wipe.**
   The generator emitted ``provider`` + ``value`` only, so ``env = "exec"``, the
   opt-ins, and every ``sync`` block vanished on regeneration.
   ✅ **Fixed upstream 2026-08-03** — ``macos-development-environment#82``
   CLOSED, #83 merged as ``716b17d``: declarations are reconciled through
   ``fnox`` itself and the file is written only when it does not exist, so
   there is no template left to drop a field from. Two reasons this check still
   earns its place: every add/remove still churns all 49 ``sync`` ciphertexts,
   and one stale local branch still carries the pre-fix code. Since 2026-08-02
   the mode is ``env = true`` by decision (all 50 in every shell), so item 1's
   "exec-only" is history too — what ``fnox-baseline`` now pins is that mode
   plus the full 50-name set.
3. **The filesystem MCP server's real scope was not its declared scope.**
   ``.mcp.json`` names one directory; the session had two, because MCP Roots
   *replace* the server's own arguments.

All three are "the environment is not what the config says" faults. This module
is the project-specific complement to the built-in ``/doctor``: it reads the
declared baseline in ``doctor.toml`` and compares it with what is actually true
on this host.

Shape and constraints (all from #418):

- **SessionStart, not Stop** — fires once per session and cannot block.
- **Silent when healthy.** No news is good news; ``--verbose`` prints the
  per-check PASS lines when you want to see it did something.
- **Fails open.** A crashed check is recorded to :data:`ERROR_LOG` and surfaced
  on stdout, never raised — a broken doctor must not be able to disrupt a
  session. Exit is 0 even with findings unless ``--strict`` is passed.
- **Host-only by nature.** It reads ``~/.config/fnox`` and ``~/.claude``, so it
  is a hook and never a CI job; a runner has none of that state.
- **Both arms, and the live one knows what it cannot see.** See
  :func:`check_live_servers`.

Reading the credential store: :func:`read_fnox` parses ``~/.config/fnox`` for
the ``env`` FIELDS ONLY and never retains or reports a value. The config holds
no plaintext secrets (provider references plus age-encrypted sync blobs), and
findings name variables, never contents.
"""

from __future__ import annotations

import datetime as dt
import importlib.util
import json
import logging
import os
import platform
import plistlib
import re
import shutil
import subprocess
import sys
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from dotfiles_setup import (
    child_env,
    codex_schema,
    devcontainer_names,
    hk_hooks,
    install_doctor,
    removed_plugins,
)
from dotfiles_setup.dependency_currency import (
    check_dependency_currency as dependency_currency_findings,
)
from dotfiles_setup.graphify_currency import check as graphify_currency_check
from dotfiles_setup.listing_budget import (
    SKILL_DESCRIPTION_MAX,
    ListingEntry,
    collect_listing,
    over_cap,
    total_chars,
)
from dotfiles_setup.path_drift import (
    BLIND_ADVICE,
    DEFAULT_GATE_TOOLS,
    NATIVE_ONLY_BLIND_ADVICE,
    NativeTool,
    Provenance,
    drift_advice,
)

# Deliberately NOT imported as ``check_*``: ``test_every_check_function_is_
# actually_registered`` enumerates this module's ``check_*`` names and requires
# each to be in CHECKS, so an imported one would be an unregistrable false
# positive — the guard caught this import on its first run.
from dotfiles_setup.path_drift import check_native_only as shell_native_only
from dotfiles_setup.path_drift import check_path_drift as shell_path_drift
from dotfiles_setup.platform_target import (
    PLATFORM_ENV_VAR,
    platform_arch,
    published_platform,
)
from dotfiles_setup.plugin_health import check_plugin_health as plugin_health_findings

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping

logger = logging.getLogger(__name__)

#: The reviewed baseline this module checks reality against.
BASELINE_FILE = "doctor.toml"

#: Crashes are recorded next to the PreToolUse guard's fail-open log, for the
#: same reason (#343): a fail-open nobody records is indistinguishable from
#: enforcement.
ERROR_LOG = Path.home() / ".local" / "state" / "dotfiles" / "doctor-error.log"

_PROBE_TIMEOUT_S = 180.0
_FNOX_LIVE_TIMEOUT_S = 25.0

# `${VAR}` / `${VAR:-default}` — the interpolation Claude Code performs on an
# MCP server's env and headers before spawning it.
_INTERPOLATION_RE = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)(?::-[^}]*)?\}")

# Placeholders Claude Code SUBSTITUTES ITSELF before spawning an MCP server, so
# this process's environment says nothing about them. They are documented as
# "path placeholders" (`$CC/mcp.md:481`), and `$CC/mcp.md:941` scopes the first
# one explicitly: "the plugin's root directory. Set only when a plugin provides
# the server". A plugin server therefore gets a resolved absolute path while a
# `mise run doctor` child — which no plugin provides — sees nothing.
#
# Without this exemption `check_mcp_env_opt_in` reports permanent drift for
# EVERY plugin that uses the documented placeholder (measured: enabling
# context7, whose `.mcp.json` headersHelper is
# `node "${CLAUDE_PLUGIN_ROOT}/scripts/headers.mjs"`). That is the check's own
# failure mode turned inward — a finding about the prober's environment, not the
# server's. The credential axis it exists for is untouched: these three names
# are paths, never secrets, so exempting them cannot hide an anonymous-tier
# fallback.
_HARNESS_SUBSTITUTED = frozenset(
    {"CLAUDE_PLUGIN_ROOT", "CLAUDE_PLUGIN_DATA", "CLAUDE_PROJECT_DIR"}
)

# Package-runner commands whose first non-flag argument is an npm spec. `npx -y
# <pkg>` resolves the CURRENT dist-tag on every spawn, so an unpinned server can
# change its tool set between two sessions without any diff in this repo.
_PACKAGE_RUNNERS = frozenset({"npx", "bunx", "pnpx", "dlx"})

# The module whose offline drift check the SessionStart hook runs. Check 7
# delegates version comparison to it rather than re-implementing it.
_CURRENCY_MODULE = "kb_setup.currency"
_CURRENCY_TASK = "tool-currency-check"


def _str_keys(raw: object) -> dict[str, object]:
    """A JSON/TOML mapping narrowed to string keys; ``{}`` when it is not one.

    Every input here is externally-authored config, so each access has to cope
    with the wrong shape rather than assume it. Funnelling that through one
    helper keeps the checks readable instead of isinstance-laddered.
    """
    if not isinstance(raw, dict):
        return {}
    return {str(key): value for key, value in raw.items()}


def _str_list(raw: object) -> list[str]:
    """The string members of a list value; ``[]`` when it is not a list."""
    if not isinstance(raw, list):
        return []
    return [item for item in raw if isinstance(item, str)]


@dataclass(frozen=True)
class FnoxState:
    """The ``env``-visibility facts of a fnox config. Never holds a value.

    ``env`` is tri-state per fnox >= 1.30.0: ``true`` (shell + exec + get),
    ``"exec"`` (exec + get, NOT the interactive shell), ``false`` (get only).
    A per-secret field overrides the global one; absent means inherit.
    """

    exists: bool
    env_mode: object = True
    per_secret: dict[str, object] = field(default_factory=dict)
    profile_secrets: dict[str, frozenset[str]] = field(default_factory=dict)
    sync_blocks: int = 0
    error: str | None = None

    def shell_visible(self, name: str) -> bool:
        """True when ``name`` reaches the interactive shell — and thus every child.

        This is the *documented* semantics; :func:`check_mcp_env_opt_in` does not
        rely on it, because the doctor's own environment is a direct oracle for
        the same question. It is used to EXPLAIN an absence, which is what makes
        a finding actionable rather than merely true.
        """
        # `read_fnox` stores ``fields.get("env")``, so a declaration with NO
        # ``env`` field lands here as an explicit ``None`` — the key EXISTS, and
        # a ``dict.get(name, default)`` would never reach its default. Inherit on
        # ``None``, not on absence, or "absent means inherit" is a lie for every
        # declared secret. Invisible under ``env = "exec"`` (both paths returned
        # False); wrong under ``env = true``, where it would report all 50 as
        # shell-invisible after a `bootstrap_config()` regeneration — i.e. a
        # false alarm on precisely the event this tripwire exists to catch.
        mode = self.per_secret.get(name)
        if mode is None:
            mode = self.env_mode
        return mode is True

    def declares(self, name: str) -> bool:
        """True when the config has a ``[secrets]`` entry for ``name``."""
        return name in self.per_secret


@dataclass(frozen=True)
class Server:
    """A registered MCP server, with the provenance that decides who owns it."""

    name: str
    origin: str
    config: dict[str, object]

    @property
    def repo_owned(self) -> bool:
        """True when THIS repo declares the server, so a finding is actionable here.

        The split that keeps the doctor's output worth reading. A check saying
        "fix this repo's declaration" (scope, pin, tool coverage) must only run on
        what the repo declares — ``.mcp.json`` or an enabled plugin. A check
        saying "your setup is broken" (duplicate, health, an interpolation that
        resolves empty) runs on everything, because a broken server is broken
        whoever registered it.

        Without this the ``MCP_DOCKER`` gateway alone contributed **32** findings
        about undeclared mutating tools in a user-global server the repo neither
        owns nor can fix — noise that trains you to skim past the real ones.
        """
        return self.origin == "project" or self.origin.startswith("plugin:")


@dataclass(frozen=True)
class Setup:
    """Everything the doctor reads, resolved once.

    Checks are pure functions of this object, so a test drives a fixture without
    touching the real ``$HOME`` — which matters more than usual here: half the
    inputs are the operator's live credential config.
    """

    repo_root: Path
    baseline: dict[str, object]
    servers: tuple[Server, ...]
    settings: dict[str, object]
    local_settings: dict[str, object]
    fnox: FnoxState
    environ: Mapping[str, str]
    listing: tuple[ListingEntry, ...] = ()
    #: `~/.claude/settings.json`. Held so checks can reproduce the
    #: user-then-project precedence `enabled_plugin_ids` applies.
    user_settings: dict[str, object] = field(default_factory=dict)
    #: The home directory the Claude/codex user state was read from. ``None`` in
    #: fixtures that never touch user state; checks that need it skip then.
    home: Path | None = None

    def fnox_baseline(self) -> dict[str, object]:
        """The ``[fnox]`` section of the baseline; ``{}`` when it is absent."""
        return _str_keys(self.baseline.get("fnox"))

    def mcp_baseline(self) -> dict[str, object]:
        """The ``[mcp]`` section of the baseline; ``{}`` when it is absent."""
        return _str_keys(self.baseline.get("mcp"))

    def listing_baseline(self) -> dict[str, object]:
        """The ``[listing]`` section of the baseline; ``{}`` when it is absent."""
        return _str_keys(self.baseline.get("listing"))

    def server_names(self) -> set[str]:
        """Names of every registered MCP server, whatever its provenance."""
        return {server.name for server in self.servers}


# --------------------------------------------------------------------------- #
# Collection
# --------------------------------------------------------------------------- #


def load_json(path: Path) -> dict[str, object]:
    """Parse a JSON file; an unreadable or malformed one yields ``{}``."""
    try:
        return _str_keys(json.loads(path.read_text()))
    except (OSError, json.JSONDecodeError) as exc:
        logger.debug("doctor: could not read %s: %s", path, exc)
        return {}


def read_fnox(config_path: Path) -> FnoxState:
    """Parse a fnox config for its ``env`` fields and its ``sync`` coverage."""
    if not config_path.exists():
        return FnoxState(exists=False, error=f"{config_path} does not exist")
    try:
        data = tomllib.loads(config_path.read_text())
    except (OSError, tomllib.TOMLDecodeError) as exc:
        return FnoxState(exists=True, error=f"could not parse {config_path}: {exc}")
    per_secret: dict[str, object] = {}
    sync_blocks = 0
    for name, entry in _str_keys(data.get("secrets")).items():
        fields = _str_keys(entry)
        per_secret[name] = fields.get("env")
        if isinstance(fields.get("sync"), dict):
            sync_blocks += 1
    profiles = {
        name: frozenset(_str_keys(_str_keys(entry).get("secrets")))
        for name, entry in _str_keys(data.get("profiles")).items()
    }
    return FnoxState(
        exists=True,
        env_mode=data.get("env", True),
        per_secret=per_secret,
        profile_secrets=profiles,
        sync_blocks=sync_blocks,
    )


def enabled_plugin_ids(*settings: Mapping[str, object]) -> list[str]:
    """``<plugin>@<marketplace>`` ids enabled by any of the given settings files.

    Later mappings win, so a project setting overrides the user one — the same
    precedence Claude Code applies.
    """
    enabled: dict[str, bool] = {}
    for source in settings:
        enabled.update(
            {
                name: on
                for name, on in _str_keys(source.get("enabledPlugins")).items()
                if isinstance(on, bool)
            }
        )
    return sorted(name for name, on in enabled.items() if on)


def plugin_mcp_path(home: Path, plugin_id: str) -> Path | None:
    """The ``.mcp.json`` an enabled plugin contributes, if it has one.

    A marketplace clone holds EVERY plugin it publishes plus, often, variants
    for other agents (the context7 clone carries ``plugins/claude/context7``,
    ``plugins/codex/context7`` and ``plugins/copilot/context7``). Only the one
    the manifest names as the enabled plugin's source is loaded, so resolving
    through ``marketplace.json`` rather than globbing is what keeps this from
    reporting on configs Claude Code never reads.
    """
    plugin_name, _, marketplace = plugin_id.partition("@")
    if not marketplace:
        return None
    root = home / ".claude" / "plugins" / "marketplaces" / marketplace
    manifest = load_json(root / ".claude-plugin" / "marketplace.json")
    entries = manifest.get("plugins")
    for entry in entries if isinstance(entries, list) else []:
        fields = _str_keys(entry)
        source = fields.get("source")
        if fields.get("name") != plugin_name or not isinstance(source, str):
            continue
        candidate = (root / source).resolve() / ".mcp.json"
        if candidate.is_file():
            return candidate
    fallback = root / ".mcp.json"
    return fallback if fallback.is_file() else None


def servers_from(config: Mapping[str, object], origin: str) -> list[Server]:
    """The MCP servers one config file registers, sorted by name."""
    block = _str_keys(config.get("mcpServers"))
    return [
        Server(name=name, origin=origin, config=_str_keys(block[name]))
        for name in sorted(block)
        if isinstance(block[name], dict)
    ]


def claude_json_servers(home: Path, repo_root: Path) -> list[Server]:
    """MCP servers registered in ``~/.claude.json`` — user-global and per-project.

    **The surface the first version of this module missed**, and the miss cost it
    the very defect class it was written for: ``check_mcp_duplicate`` reported
    PASS while ``context7`` and ``filesystem`` were each registered twice — once
    here as a stale ``mde-mcp-*`` wrapper and once by the plugin / ``.mcp.json``.
    Reading only ``.mcp.json`` plus the plugin configs made a check that
    *compares registrations* blind to half of them.

    It is not a cosmetic duplicate. A same-name user-global entry **shadows** the
    project one, so the broken wrapper won and ``claude mcp list`` stopped showing
    the project's ``filesystem`` server at all.
    """
    data = load_json(home / ".claude.json")
    servers = servers_from(data, "user")
    projects = _str_keys(data.get("projects"))
    entry = _str_keys(projects.get(str(repo_root.resolve())))
    servers.extend(servers_from(entry, "project-local"))
    return servers


def collect_servers(
    repo_root: Path,
    home: Path,
    *settings: Mapping[str, object],
) -> tuple[Server, ...]:
    """Every MCP server Claude Code loads here, from all four sources.

    ``.mcp.json`` (project), each enabled plugin's own config, and
    ``~/.claude.json``'s user-global and per-project blocks. Registering a server
    in more than one of them is legal and silent, which is why the whole set has
    to be collected before any check compares them.
    """
    servers = servers_from(load_json(repo_root / ".mcp.json"), "project")
    for plugin_id in enabled_plugin_ids(*settings):
        path = plugin_mcp_path(home, plugin_id)
        if path is not None:
            servers.extend(servers_from(load_json(path), f"plugin:{plugin_id}"))
    servers.extend(claude_json_servers(home, repo_root))
    return tuple(servers)


def collect(
    repo_root: Path,
    *,
    home: Path | None = None,
    environ: Mapping[str, str] | None = None,
) -> Setup:
    """Resolve every input the checks read."""
    home = home or Path.home()
    environ = environ if environ is not None else os.environ
    baseline_path = repo_root / BASELINE_FILE
    try:
        baseline = _str_keys(tomllib.loads(baseline_path.read_text()))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        logger.debug("doctor: could not read %s: %s", baseline_path, exc)
        baseline = {}
    settings = load_json(repo_root / ".claude" / "settings.json")
    user_settings = load_json(home / ".claude" / "settings.json")
    return Setup(
        repo_root=repo_root,
        baseline=baseline,
        servers=collect_servers(repo_root, home, user_settings, settings),
        settings=settings,
        user_settings=user_settings,
        local_settings=load_json(repo_root / ".claude" / "settings.local.json"),
        fnox=read_fnox(home / ".config" / "fnox" / "config.toml"),
        environ=environ,
        listing=collect_listing(
            repo_root, home, enabled_plugin_ids(user_settings, settings)
        ),
        home=home,
    )


# --------------------------------------------------------------------------- #
# Shared readers
# --------------------------------------------------------------------------- #


def hook_commands(source: Mapping[str, object], event: str) -> list[str]:
    """Every hook command wired for a settings.json event."""
    entries = _str_keys(source.get("hooks")).get(event)
    commands: list[str] = []
    for entry in entries if isinstance(entries, list) else []:
        inner = _str_keys(entry).get("hooks")
        for hook in inner if isinstance(inner, list) else []:
            command = _str_keys(hook).get("command")
            if isinstance(command, str):
                commands.append(command)
    return commands


def hook_matchers(source: Mapping[str, object], event: str) -> list[str]:
    """The matcher regexes wired for a settings.json event."""
    entries = _str_keys(source.get("hooks")).get(event)
    matchers: list[str] = []
    for entry in entries if isinstance(entries, list) else []:
        matcher = _str_keys(entry).get("matcher")
        if isinstance(matcher, str):
            matchers.append(matcher)
    return matchers


def permission_rules(source: Mapping[str, object]) -> set[str]:
    """Every permission rule string in a settings file, across all decisions."""
    permissions = _str_keys(source.get("permissions"))
    rules: set[str] = set()
    for decision in ("allow", "ask", "deny"):
        rules.update(_str_list(permissions.get(decision)))
    return rules


# --------------------------------------------------------------------------- #
# Checks
# --------------------------------------------------------------------------- #


def interpolations(config: Mapping[str, object]) -> set[str]:
    """Variable names an MCP server config interpolates at spawn time."""
    return set(_INTERPOLATION_RE.findall(json.dumps(config)))


def check_mcp_env_opt_in(setup: Setup) -> list[str]:
    """Every ``${VAR}`` an MCP config interpolates must be set in this process.

    The oracle is **the doctor's own environment**, not a reading of fnox's
    semantics, and that is the whole point: the doctor runs as a child of the
    same Claude Code process that spawns the servers, so a variable this process
    cannot see is a variable the server will not get. fnox is then consulted
    only to EXPLAIN the absence.

    Control arms on the live host, 2026-07-29: ``EXA_API_KEY`` PRESENT (it is
    ``env = true``), ``CONTEXT7_API_KEY`` absent and ``AWS_SECRET_ACCESS_KEY``
    absent (both exec-only). So the probe discriminates — it is not a check that
    can only pass.

    ``${VAR:-}`` is why this is invisible without a doctor: the default makes an
    absent variable a legal empty string, so the server starts, reports
    connected, and silently serves an anonymous tier.

    **WHOSE environment, exactly.** The wired path is ``mise run doctor``, and
    mise recomputes the fnox env per invocation — so this answers "would a
    server spawned NOW get the variable", not "does the server already running in
    this session have it". Measured 2026-07-30, right after opting
    ``CONTEXT7_API_KEY`` back in: under ``mise run`` PRESENT and the check
    passes, under a bare ``uv run`` in the same shell absent and it reports
    drift, because that shell predates the fnox edit. Both answers are correct
    about different processes. At SessionStart the two agree (the harness was
    just launched from that shell); a mid-session credential change needs a
    harness restart before the running server picks it up, and the third branch
    of :func:`_explain_absence` is what says so.
    """
    findings: list[str] = []
    for server in setup.servers:
        for var in sorted(interpolations(server.config)):
            if var in _HARNESS_SUBSTITUTED:
                continue
            if setup.environ.get(var):
                continue
            findings.append(
                f"MCP server {server.name!r} ({server.origin}) interpolates "
                f"${{{var}}}, which is not set in this process — the server "
                f"will start with an EMPTY value and report healthy. "
                f"{_explain_absence(var, setup.fnox)}"
            )
    return findings


def _explain_absence(var: str, fnox: FnoxState) -> str:
    """Why a variable is missing — the half that makes the finding actionable."""
    if not fnox.exists:
        return "No fnox config on this host, so nothing declares it."
    if not fnox.declares(var):
        return f"fnox does not declare {var} at all: add it, or stop interpolating it."
    if not fnox.shell_visible(var):
        return (
            f"fnox declares {var} but it is exec-only (global env="
            f"{fnox.env_mode!r}, no per-secret `env = true`), so it never "
            f"reaches the shell Claude Code inherits. Opt it back in with "
            f"`env = true` and record it in {BASELINE_FILE}."
        )
    return (
        f"fnox marks {var} shell-visible, so the shell that launched this "
        f"session predates that change — restart the shell."
    )


def effective_roots(setup: Setup) -> list[str]:
    """The directories Claude Code will send as MCP Roots: cwd + additional dirs."""
    roots = {str(setup.repo_root.resolve())}
    for source in (setup.settings, setup.local_settings):
        extra = _str_keys(source.get("permissions")).get("additionalDirectories")
        roots.update(str(Path(d).resolve()) for d in _str_list(extra))
    return sorted(roots)


def declared_scope(server: Server) -> list[str]:
    """The absolute-path arguments a server declares as its scope."""
    return sorted(
        str(Path(arg).resolve())
        for arg in _str_list(server.config.get("args"))
        if arg.startswith("/")
    )


def check_mcp_scope(setup: Setup) -> list[str]:
    """A scope-bearing server's declared directories must equal the root set.

    MCP Roots REPLACE the server's own arguments, so when the harness supports
    roots the argument is inert and the real scope is whatever the harness sends.
    Straight from the server's startup line when nothing negotiates roots:
    "Client does not support MCP Roots, using allowed directories set from server
    args". A declaration that differs from the effective set is a fiction — it
    reads like a restriction and enforces nothing.
    """
    scope_servers = _str_list(setup.mcp_baseline().get("scope_servers"))
    roots = effective_roots(setup)
    registered = setup.server_names()
    findings = [
        f"{BASELINE_FILE} declares scope server {name!r}, which is not "
        f"registered — the entry is stale"
        for name in scope_servers
        if name not in registered
    ]
    for server in setup.servers:
        if server.name not in scope_servers or not server.repo_owned:
            continue
        declared = declared_scope(server)
        if declared == roots:
            continue
        if not declared:
            # A wrapper that takes no path argument (the `mde-mcp-*` shape)
            # decides its own scope internally. Saying it "declares []" would
            # read as a bug in the wrapper; the true statement is that nothing
            # in the config bounds it.
            findings.append(
                f"MCP server {server.name!r} ({server.origin}) declares no scope "
                f"at all, so it takes whatever the harness sends: {roots}. "
                f"Nothing in the config bounds it."
            )
            continue
        findings.append(
            f"MCP server {server.name!r} declares scope {declared} but the "
            f"harness sends roots {roots} (this workspace plus "
            f"permissions.additionalDirectories), and roots REPLACE the "
            f"server's arguments — the declared scope restricts nothing. "
            f"Declare the same set, or drop the extra working directory."
        )
    return findings


def check_fnox_baseline(setup: Setup) -> list[str]:
    """The env mode and opt-in set must match the reviewed baseline.

    This is the ``bootstrap-config`` tripwire. That generator emits ``provider``
    + ``value`` only, so a regeneration drops the global ``env``, every
    per-secret override, and every ``sync`` block in one go. Checking the NAME
    SET rather than a count is deliberate: a swap keeps the count and is exactly
    the change worth catching.

    .. note::
       The posture this guarded was **reversed on 2026-08-02**: the baseline is
       now ``env = true`` with the full 49-name set, because all credentials are
       deliberately available to every terminal and agent. The check is unchanged
       and still discriminates in both directions — what moved is the sanctioned
       state, not the mechanism. See
       ``.claude/rules/secrets-out-of-the-shell-env.md``.
    """
    expected = setup.fnox_baseline()
    if not expected:
        return [f"{BASELINE_FILE} has no [fnox] section to check against"]
    fnox = setup.fnox
    if fnox.error is not None:
        return [f"fnox config unreadable: {fnox.error}"]
    findings: list[str] = []
    want_mode = expected.get("env")
    if want_mode is not None and fnox.env_mode != want_mode:
        findings.append(
            f"fnox global env mode is {fnox.env_mode!r}, baseline expects "
            f"{want_mode!r} — a regeneration by `mde-py secrets "
            f"bootstrap-config` looks exactly like this"
        )
    if (want_opt_in := expected.get("env_true")) is not None:
        findings.extend(_opt_in_findings(fnox, set(_str_list(want_opt_in))))
    if fnox.per_secret and fnox.sync_blocks == 0:
        findings.append(
            f"fnox declares {len(fnox.per_secret)} secrets and not one `sync` "
            f"block — the signature of a regenerated config, which drops sync, "
            f"the env mode and every opt-in together"
        )
    return findings


def _fnox_workflows(setup: Setup) -> dict[str, dict[str, object]]:
    """Reviewed consumer scopes; contract fields contain names, never values."""
    return {
        name: _str_keys(value)
        for name, value in _str_keys(setup.fnox_baseline().get("workflows")).items()
    }


def _workflow_names(setup: Setup, spec: dict[str, object]) -> set[str]:
    required = spec.get("required")
    if required == "env_true":
        return set(_str_list(setup.fnox_baseline().get("env_true")))
    return set(_str_list(required))


def _workflow_declarations(setup: Setup, spec: dict[str, object]) -> set[str]:
    return _workflow_names(setup, spec) | set(_str_list(spec.get("bootstrap")))


def _workflow_scope(setup: Setup, spec: dict[str, object]) -> set[str] | None:
    profile = spec.get("profile")
    if not isinstance(profile, str):
        return None
    if profile == "default":
        return set(setup.fnox.per_secret)
    profile_names = setup.fnox.profile_secrets.get(profile)
    if profile_names is None:
        return None
    names = set(profile_names)
    if spec.get("no_defaults") is not True:
        names.update(setup.fnox.per_secret)
    return names


def check_fnox_workflows(setup: Setup) -> list[str]:
    """Every named consumer must see its required declarations in its scope.

    This catches the OpenRouter failure class: a top-level secret exists, but
    ``--profile codex_research --no-defaults`` excludes it. Resolution is a
    separate opt-in live check because provider calls can block or prompt.
    """
    workflows = _fnox_workflows(setup)
    if not workflows:
        return [f"{BASELINE_FILE} has no [fnox.workflows] contracts"]
    if setup.fnox.error is not None:
        return ["fnox workflow scopes unverifiable: fnox config unreadable"]
    findings: list[str] = []
    for consumer, spec in sorted(workflows.items()):
        required = _workflow_declarations(setup, spec)
        profile = spec.get("profile")
        if not required or not isinstance(profile, str):
            findings.append(f"fnox workflow {consumer} has an invalid contract")
            continue
        scope = _workflow_scope(setup, spec)
        if scope is None:
            findings.append(f"fnox workflow {consumer} profile {profile} is absent")
            continue
        if missing := sorted(required - scope):
            findings.append(
                f"fnox workflow {consumer} profile {profile} cannot expose {missing}"
            )
        if spec.get("no_defaults") is True and (extra := sorted(scope - required)):
            findings.append(
                f"fnox workflow {consumer} profile {profile} "
                f"unexpectedly exposes {extra}"
            )
    return findings


def check_fnox_services(setup: Setup) -> list[str]:
    """A LaunchAgent must start under its declared scoped fnox profile.

    Profile resolution in a fresh child does not prove the already-running
    daemon received those variables. Inspect only launch structure and key
    names; plist values may themselves be credentials and are never reported.
    """
    if setup.home is None:
        return []
    services = _str_keys(setup.fnox_baseline().get("services"))
    if not services:
        return [f"{BASELINE_FILE} has no [fnox.services] contracts"]
    findings: list[str] = []
    for service, raw in sorted(services.items()):
        spec = _str_keys(raw)
        plist_name = spec.get("launch_agent")
        profile = spec.get("profile")
        required = set(_str_list(spec.get("required")))
        if (
            not isinstance(plist_name, str)
            or Path(plist_name).name != plist_name
            or not isinstance(profile, str)
            or not required
        ):
            findings.append(f"fnox service {service} has an invalid contract")
            continue
        path = setup.home / "Library" / "LaunchAgents" / plist_name
        try:
            data = plistlib.loads(path.read_bytes())
        except OSError, ValueError, plistlib.InvalidFileException:
            findings.append(f"fnox service {service} launch declaration is unreadable")
            continue
        if not isinstance(data, dict):
            findings.append(f"fnox service {service} launch declaration is invalid")
            continue
        env_names = set(_str_keys(data.get("EnvironmentVariables")))
        if embedded := sorted(required & env_names):
            findings.append(
                f"fnox service {service} puts {embedded} directly in its plist"
            )
        raw_args = data.get("ProgramArguments")
        args = raw_args if isinstance(raw_args, list) else []
        exec_at = args.index("exec") if "exec" in args else 0
        fnox_args = args[:exec_at]
        if (
            not args
            or not isinstance(args[0], str)
            or Path(args[0]).name != "fnox"
            or "--no-defaults" not in fnox_args
            or not any(
                fnox_args[index : index + 2] == ["--profile", profile]
                for index in range(len(fnox_args) - 1)
            )
        ):
            findings.append(
                f"fnox service {service} launcher does not select "
                f"profile {profile} with --no-defaults"
            )
    return findings


_FNOX_CHILD_PROBE = (
    "import json,os,sys;"
    "names=json.loads(sys.argv[1]);"
    "print(json.dumps([name for name in names if not os.environ.get(name)]))"
)


def _fnox_presence_probe(
    setup: Setup,
    consumer: str,
    spec: dict[str, object],
    config_path: Path,
    parent_env: dict[str, str],
) -> str | None:
    required = sorted(_workflow_names(setup, spec))
    command = [
        "fnox",
        "--config",
        str(config_path),
        "--profile",
        str(spec["profile"]),
        "--no-daemon",
        "--non-interactive",
        "--if-missing",
        "error",
    ]
    if spec.get("no_defaults") is True:
        command.append("--no-defaults")
    command.extend(
        ["exec", "--", sys.executable, "-c", _FNOX_CHILD_PROBE, json.dumps(required)]
    )
    try:
        result = subprocess.run(
            command,
            cwd=setup.repo_root,
            env=parent_env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=_FNOX_LIVE_TIMEOUT_S,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return f"fnox workflow {consumer} resolution timed out"
    except OSError:
        return f"fnox workflow {consumer} could not start fnox"
    if result.returncode != 0:
        return (
            f"fnox workflow {consumer} resolution failed "
            f"(exit {result.returncode}); provider details suppressed"
        )
    try:
        missing = json.loads(result.stdout)
    except json.JSONDecodeError:
        missing = None
    if not isinstance(missing, list) or any(
        not isinstance(name, str) or name not in required for name in missing
    ):
        return f"fnox workflow {consumer} produced an invalid presence receipt"
    if missing:
        return f"fnox workflow {consumer} injected no value for {missing}"
    return None


def check_fnox_resolution(setup: Setup) -> list[str]:
    """Ask native fnox to inject each consumer's names into a bounded child.

    The parent drops inherited secret variables so a stale shell cannot make a
    broken fnox profile pass. Neither provider diagnostics nor values are echoed.
    """
    findings = check_fnox_workflows(setup)
    if findings:
        return findings
    config_path = (setup.home or Path.home()) / ".config" / "fnox" / "config.toml"
    all_names = set(setup.fnox.per_secret)
    for names in setup.fnox.profile_secrets.values():
        all_names.update(names)
    parent_env = {
        key: value for key, value in setup.environ.items() if key not in all_names
    }
    for consumer, spec in sorted(_fnox_workflows(setup).items()):
        finding = _fnox_presence_probe(setup, consumer, spec, config_path, parent_env)
        if finding:
            findings.append(finding)
    return findings


def check_exec_only_not_leaked(setup: Setup) -> list[str]:
    """An ``env = "exec"`` secret must never reach the interactive shell.

    2026-08-29c: ``CLAUDE_CODE_OAUTH_TOKEN`` leaked into an ambient shell
    despite ``env = "exec"`` being correctly configured — the mechanism (fnox's
    live hook unsetting it every prompt) was never broken; a `claude` process
    forked from a shell that predates the carve-out just keeps whatever it
    inherited at launch, since process environments are copied at fork, not
    live-linked to the parent shell's later `unset`. This check can't fix
    that (nothing running can rewrite its own inherited environment), but it
    surfaces the recurrence immediately instead of waiting for a `/login`
    warning. See memory ``reference_claude_code_oauth_token.md``.
    """
    fnox = setup.fnox
    if not fnox.exists:
        return []
    findings: list[str] = []
    for name, mode in fnox.per_secret.items():
        if mode != "exec":
            continue
        if setup.environ.get(name):
            findings.append(
                f'{name} is declared `env = "exec"` (must never reach the '
                f"interactive shell) but IS set in this process's environment "
                f"— likely a shell that predates the carve-out. Fully quit "
                f"and reopen the terminal application; a running process "
                f"keeps whatever it inherited at fork regardless of what "
                f"fnox's hook does afterward."
            )
    return findings


def _opt_in_findings(fnox: FnoxState, wanted: set[str]) -> list[str]:
    """Drift between the shell-visible set and the sanctioned one, both ways."""
    actual = {name for name in fnox.per_secret if fnox.shell_visible(name)}
    findings: list[str] = []
    if extra := sorted(actual - wanted):
        findings.append(
            f"fnox opts {extra} into the interactive shell, which "
            f"{BASELINE_FILE} does not sanction — every child process, agent "
            f"and MCP server now inherits them"
        )
    if missing := sorted(wanted - actual):
        findings.append(
            f"fnox no longer opts {missing} into the shell, but "
            f"{BASELINE_FILE} says something reads them from the environment "
            f"— expect a SILENT degradation, not an error"
        )
    return findings


def _pinned(spec: str) -> bool:
    """True when an npm spec names a version (``pkg@1.2.3``, ``@scope/pkg@1.2.3``)."""
    return "@" in spec.removeprefix("@")


def check_mcp_pin(setup: Setup) -> list[str]:
    """No MCP server may be launched from an unpinned package spec.

    ``npx -y <pkg>`` resolves the current dist-tag on every spawn, so the tool
    set can change between two sessions with no diff anywhere in this repo — and
    a tool that appears is a tool no permission rule covers yet. It also makes
    :func:`check_mcp_guard_coverage`'s declared list unfalsifiable, which is why
    this check is load-bearing rather than hygiene.
    """
    findings: list[str] = []
    for server in setup.servers:
        command = server.config.get("command")
        if (
            not server.repo_owned
            or not isinstance(command, str)
            or Path(command).name not in _PACKAGE_RUNNERS
        ):
            continue
        findings.extend(
            f"MCP server {server.name!r} ({server.origin}) launches unpinned "
            f"{spec!r} via {command} — the resolved version, and therefore its "
            f"tool set, can change between sessions. Pin it as {spec}@<version>."
            for spec in _str_list(server.config.get("args"))
            if not spec.startswith(("-", "/")) and not _pinned(spec)
        )
    return findings


def _matched_by_hook(tool: str, matchers: list[str]) -> bool:
    """True when any PreToolUse matcher regex reaches this tool name."""
    for matcher in matchers:
        try:
            if re.search(matcher, tool):
                return True
        except re.error:
            logger.debug("doctor: un-compilable PreToolUse matcher %r", matcher)
    return False


def _covered_by_rules(tool: str, server: str, rules: set[str]) -> bool:
    """A rule covers a tool exactly, or covers its whole server."""
    return tool in rules or f"mcp__{server}" in rules


def check_mcp_guard_coverage(setup: Setup) -> list[str]:
    """Every declared mutating MCP tool needs a reviewed decision.

    "Reviewed" means a permission rule in the TRACKED ``.claude/settings.json``
    or a PreToolUse matcher that reaches the tool. A rule that exists only in
    ``.claude/settings.local.json`` does not count and gets its own wording:
    that file is gitignored, so an ad-hoc "yes" clicked during one session
    becomes standing policy nobody ever reviews.
    """
    declared = _str_keys(setup.mcp_baseline().get("mutating_tools"))
    registered = setup.server_names()
    tracked = permission_rules(setup.settings)
    local = permission_rules(setup.local_settings)
    matchers = hook_matchers(setup.settings, "PreToolUse")
    findings: list[str] = []
    for server in sorted(declared):
        if server not in registered:
            findings.append(
                f"{BASELINE_FILE} declares mutating tools for {server!r}, which "
                f"is not a registered MCP server — the entry is stale"
            )
            continue
        for short in sorted(_str_list(declared[server])):
            tool = f"mcp__{server}__{short}"
            if _covered_by_rules(tool, server, tracked) or _matched_by_hook(
                tool, matchers
            ):
                continue
            where = (
                "it is allowed only by the gitignored .claude/settings.local.json"
                if _covered_by_rules(tool, server, local)
                else "no permission rule or PreToolUse matcher mentions it"
            )
            findings.append(
                f"mutating MCP tool {tool} has no reviewed decision — {where}. "
                f"Add an explicit allow/ask/deny to the tracked "
                f".claude/settings.json."
            )
    return findings


def check_mcp_duplicate(setup: Setup) -> list[str]:
    """No server name may be registered by both the project and a plugin.

    Two registrations of one name is not a merge: one wins, silently, and which
    one wins decides whether the server is authenticated. That is how the
    context7 double-registration hid an anonymous tier.
    """
    by_name: dict[str, list[str]] = {}
    for server in setup.servers:
        by_name.setdefault(server.name, []).append(server.origin)
    return [
        f"MCP server {name!r} is registered {len(origins)} times "
        f"({', '.join(origins)}) — one silently wins, and they do not carry "
        f"the same auth"
        for name, origins in sorted(by_name.items())
        if len(origins) > 1
    ]


def check_pin_currency_wired(setup: Setup) -> list[str]:
    """Pin-vs-installed drift is DELEGATED — assert the delegate actually runs.

    ``kb-setup currency check`` (the shared engine, one implementation across
    dotfiles and knowledge-base) already answers "does the install match the
    pin", and the SessionStart hook runs it every session. Re-implementing
    version comparison here would be a second answer to drift from — so this
    check verifies the delegation instead, in the one way the existing
    ``workflow.tool-currency-wiring`` contract cannot: that contract greps
    settings.json for the task name, which proves the hook is *written*, not
    that it can *run*. A missing ``kb_setup`` dep leaves the wiring intact and
    the check silently absent.
    """
    findings: list[str] = []
    wired = "\n".join(hook_commands(setup.settings, "SessionStart"))
    if _CURRENCY_TASK not in wired:
        findings.append(
            f"no SessionStart hook runs `{_CURRENCY_TASK}`, so pin-vs-installed "
            f"drift is not checked at all"
        )
    if importlib.util.find_spec(_CURRENCY_MODULE) is None:
        findings.append(
            f"`{_CURRENCY_MODULE}` is not importable, so the wired "
            f"`{_CURRENCY_TASK}` hook fails without checking anything — the "
            f"wiring looks intact either way"
        )
    return findings


# --------------------------------------------------------------------------- #
# The live arm
# --------------------------------------------------------------------------- #

# Verb prefixes that mutate. Matched on the tool NAME, so a server we have never
# seen is covered as long as it follows the MCP naming convention — the same
# name-shaped heuristic child_env.py uses for credential variables.
_MUTATING_PREFIXES = (
    "write_",
    "edit_",
    "create_",
    "delete_",
    "move_",
    "remove_",
    "update_",
    "add_",
    "set_",
    "put_",
    "patch_",
)


def looks_mutating(tool: str) -> bool:
    """True when a tool name's verb says it changes state."""
    return tool.startswith(_MUTATING_PREFIXES)


def stdio_command(server: Server) -> str | None:
    """The stdio command line ``mcp2cli`` can spawn for a server, if any.

    ``None`` for an HTTP server (``type = "http"``, no ``command``) — those
    cannot be spawned locally, so the live arm skips them.
    """
    command = server.config.get("command")
    if not isinstance(command, str):
        return None
    return " ".join([command, *_str_list(server.config.get("args"))])


def probe_tools(command: str) -> tuple[set[str], str | None]:
    """``mcp2cli --list`` against a stdio server -> its real tool names.

    ``mcp2cli`` rather than a hand-rolled JSON-RPC handshake: it is already
    pinned in ``mise.toml`` and already the repo's sanctioned way to reach an
    MCP server without registering it (``use-tool-builtins.md``).

    Names come back hyphenated (argparse normalises ``_`` -> ``-`` at the CLI
    layer), so they are converted back before comparison.
    """
    if shutil.which("mcp2cli") is None:
        return set(), "mcp2cli is not on PATH"
    try:
        result = subprocess.run(
            ["mcp2cli", "--mcp-stdio", command, "--list"],
            capture_output=True,
            text=True,
            check=False,
            timeout=_PROBE_TIMEOUT_S,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return set(), f"probe failed: {exc}"
    if result.returncode != 0:
        return set(), f"probe exited {result.returncode}: {result.stderr.strip()[:200]}"
    return parse_tool_list(result.stdout), None


def parse_tool_list(stdout: str) -> set[str]:
    """The tool names in an ``mcp2cli --list`` report, un-hyphenated."""
    tools: set[str] = set()
    in_list = False
    for line in stdout.splitlines():
        if line.startswith("Available tools:"):
            in_list = True
            continue
        if in_list and line.startswith("  ") and (parts := line.split()):
            tools.add(parts[0].replace("-", "_"))
    return tools


def check_live_servers(setup: Setup) -> list[str]:
    """Spawn each stdio server and compare its REAL tool set to the baseline.

    **What this arm cannot see, stated so nobody mistakes it for the scope
    check.** A standalone spawn negotiates no MCP Roots, so the server falls back
    to its command-line arguments and reports those — measured: the filesystem
    server printed "Client does not support MCP Roots, using allowed directories
    set from server args" and ``list_allowed_directories`` returned the single
    declared path, while the session it was probed from had two. So the live arm
    answers "what does the server itself offer", and :func:`check_mcp_scope`
    answers "what scope will it actually get". Reading a one-directory answer
    here as confirmation of the session's scope is precisely the false negative
    #418 was filed over.

    Off the SessionStart path by design (Ray, 2026-07-29): a subprocess spawn per
    server every session is real latency for drift that changes rarely. Run it
    on demand with ``mise run doctor -- --live``.
    """
    declared = _str_keys(setup.mcp_baseline().get("mutating_tools"))
    findings: list[str] = []
    for server in setup.servers:
        command = stdio_command(server)
        if command is None or not server.repo_owned:
            continue
        tools, error = probe_tools(command)
        if error is not None:
            findings.append(f"live probe of MCP server {server.name!r}: {error}")
            continue
        known = set(_str_list(declared.get(server.name)))
        if stale := sorted(known - tools):
            findings.append(
                f"MCP server {server.name!r} no longer offers {stale}, which "
                f"{BASELINE_FILE} declares as mutating tools — the entry is stale"
            )
        if undeclared := sorted(t for t in tools - known if looks_mutating(t)):
            findings.append(
                f"MCP server {server.name!r} offers mutating tools "
                f"{undeclared} that {BASELINE_FILE} does not declare, so "
                f"nothing checks they have a reviewed permission decision"
            )
    return findings


# `<name>: <target> - <glyph> <status>`, the shape `claude mcp list` prints.
#
# Anchored on the GLYPH, and the name is GREEDY. Both are load-bearing, and the
# fixture caught the version that was not: a name can itself contain colons
# (`plugin:context7:context7`), so `[^:]+` stopped at the first one and the row
# was silently DROPPED — and a dropped row is a server reported healthy. Greedy
# `.+` plus the required glyph makes the engine backtrack to the right split even
# when the status also contains `: ` (`— -32000: MCP error -32000: …`).
_MCP_LIST_RE = re.compile(
    r"^(?P<name>.+): (?P<target>.*) - (?P<glyph>[✔✘⏸!]) (?P<status>.+)$"
)

#: The one glyph that means the server actually answered.
_HEALTHY_GLYPH = "✔"


@dataclass(frozen=True)
class ServerHealth:
    """One row of ``claude mcp list``."""

    name: str
    target: str
    status: str
    healthy: bool


def parse_mcp_list(stdout: str) -> list[ServerHealth]:
    """Rows of a ``claude mcp list`` report.

    Text-parsed because the command has **no ``--json``** (probed: ``unknown
    option '--json'``). The format is pinned by a test against real captured
    output, so a change upstream fails loudly instead of silently reporting every
    server healthy — the failure mode a lenient parser would have.
    """
    rows: list[ServerHealth] = []
    for line in stdout.splitlines():
        match = _MCP_LIST_RE.match(line.strip())
        if match is None:
            continue
        rows.append(
            ServerHealth(
                name=match.group("name"),
                target=match.group("target").strip(),
                status=match.group("status").strip(),
                healthy=match.group("glyph") == _HEALTHY_GLYPH,
            )
        )
    return rows


def check_mcp_health(setup: Setup) -> list[str]:
    """Every registered MCP server must actually connect.

    Delegated to ``claude mcp list`` rather than a hand-rolled handshake per
    server: it is the harness's own view, it already covers sources this module
    reads statically *and* ones it cannot (the claude.ai cloud connectors), and it
    reports authentication state — three things a spawn probe cannot tell us
    (``use-tool-builtins.md``).

    It is a LIVE check because it health-checks every server, including cloud
    ones over the network. Measured on this host: six stale ``mde-mcp-*``
    wrappers failing on a ``mde-secrets.sh`` their removal left behind, two
    project servers ``Pending approval`` after a ``.mcp.json`` edit, and one
    cloud connector needing authentication — none of which any static check here
    can see, and all of which a session would otherwise carry silently.

    ``Pending approval`` is reported but named as such: it is a consent state
    resolved by ``/mcp``, not a defect.
    """
    if shutil.which("claude") is None:
        return ["`claude` is not on PATH, so server health cannot be checked"]
    try:
        result = subprocess.run(
            ["claude", "mcp", "list"],
            capture_output=True,
            text=True,
            check=False,
            timeout=_PROBE_TIMEOUT_S,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return [f"`claude mcp list` failed: {exc}"]
    rows = parse_mcp_list(result.stdout)
    if not rows:
        return [
            (
                "`claude mcp list` returned no parseable rows — the output format "
                "changed, and until the parser is updated this check reports nothing "
                f"rather than health (rc={result.returncode})"
            )
        ]
    owned = {server.name for server in setup.servers if server.repo_owned}
    return [
        health_finding(row, owned=row.name in owned) for row in rows if not row.healthy
    ]


#: A status that is a consent state, not a defect — resolved by approving in `/mcp`.
_CONSENT_STATES = ("Pending approval", "Needs authentication")


def health_finding(row: ServerHealth, *, owned: bool) -> str:
    """One health finding, worded by KIND — consent states are not failures.

    Reporting "not connected" for a server merely awaiting your approval reads as
    a defect and sends you debugging something that only needs a click. The
    distinction is the difference between a doctor and an alarm.
    """
    scope = " This repo registers it." if owned else ""
    if row.status.startswith(_CONSENT_STATES):
        return (
            f"MCP server {row.name!r} is waiting on you, not broken: "
            f"{row.status}. Approve it in `/mcp`.{scope}"
        )
    return (
        f"MCP server {row.name!r} is registered but does not connect: "
        f"{row.status}.{scope}"
    )


def check_listing_budget(setup: Setup) -> list[str]:
    """The skill/agent listing is standing context, and nothing else measures it.

    Two independent findings, deliberately in one check because they share the
    one collection pass:

    * an over-cap description, which TRUNCATES silently — the only hard failure
      in the instruction system, and it degrades behaviour rather than costing
      bytes;
    * total standing characters against the reviewed ceiling, so this class
      cannot grow unnoticed the way it already did (~29,874 B before anything
      looked).

    Host state, so it is a doctor check and not an hk step: a CI runner has no
    ``~/.claude/plugins`` and could only ever report zero.
    """
    listing_baseline = setup.listing_baseline()
    description_cap = listing_baseline.get("max_description_chars")
    if type(description_cap) is not int or description_cap <= 0:
        description_cap = SKILL_DESCRIPTION_MAX
    findings: list[str] = []
    if description_cap > SKILL_DESCRIPTION_MAX:
        # An override above the harness-true truncation cap cannot loosen
        # reporting: the harness truncates at SKILL_DESCRIPTION_MAX regardless
        # of what this repo configures, so honouring a higher cap here would
        # make the check pass while real truncation kept happening (the exact
        # shape `.claude/rules/probes-need-a-control-arm.md` rule 9 forbids).
        # Report the misconfiguration and clamp for the reporting pass below.
        findings.append(
            f"doctor.toml sets max_description_chars={description_cap}, above "
            f"the harness-true truncation cap of {SKILL_DESCRIPTION_MAX} — the "
            f"override cannot loosen reporting; entries over "
            f"{SKILL_DESCRIPTION_MAX} chars are still reported below"
        )
        description_cap = SKILL_DESCRIPTION_MAX
    findings.extend(
        f"{entry.kind} {entry.name!r} ({entry.source}) has a "
        f"{entry.desc_chars}-char description over the HARD {description_cap} "
        f"cap — the tail is TRUNCATED SILENTLY, taking the keywords it is matched "
        f"on with it: {entry.path}"
        for entry in over_cap(setup.listing, description_cap)
    )
    ceiling = listing_baseline.get("max_chars")
    if isinstance(ceiling, int):
        total = total_chars(setup.listing)
        if total > ceiling:
            findings.append(
                f"the skill + agent listing is {total} chars of STANDING context "
                f"(> {ceiling} declared in {BASELINE_FILE}) across "
                f"{len(setup.listing)} entries — every one is carried every turn. "
                f"Disable a plugin, or raise the ceiling in a reviewed diff"
            )
    return findings


def check_graphify_skill_surface(setup: Setup) -> list[str]:
    """The graphify skill surface stays in its reviewed, DELIBERATE shape.

    The commit-time twin is hk's ``graphify_skill_surface`` step, which
    asserts the identical facts. Both exist because hk only ever runs
    at commit time, while this runs every SessionStart — a session that
    never commits would otherwise carry a broken surface silently for its
    whole duration.

    Assertions, all read straight off the working tree rather than the
    baseline's usual host-external state, because that is exactly what this
    surface *is*:

    * every ``required_skill_files`` entry must exist — losing one is a
      regression for whichever platform reads it;
    * the ``stub_file`` must still carry ``stub_marker`` — its absence means
      either the deliberate-stub note was deleted by accident, or the file was
      silently replaced by real ``graphify agents install`` output (update
      ``doctor.toml`` in that case, rather than restoring the marker);
    * ``forbidden_agents_md_marker`` must not appear in the root
      ``AGENTS.md`` — that literal line is what a codex-platform
      ``graphify install`` (the VENDOR installer) appends there, so its
      presence means the banned vendor installer ran. ``AGENTS.md`` IS
      tracked, so `git diff` would also show it, but only at the next
      commit — this still needs to say so every session.

    Package, lock, receipt, ambient-PATH binary, stamp, and managed-byte
    comparisons delegate to :func:`dotfiles_setup.graphify_currency.check` in
    offline mode. SessionStart therefore never reaches the network or graph
    health while retaining every local currency gate.
    """
    baseline = _str_keys(setup.baseline.get("graphify"))
    findings: list[str] = [
        f"{rel} is missing — the graphify skill surface for that platform is gone"
        for rel in _str_list(baseline.get("required_skill_files"))
        if not (setup.repo_root / rel).is_file()
    ]
    findings.extend(
        drift.detail for drift in graphify_currency_check(setup.repo_root, offline=True)
    )
    stub_file = baseline.get("stub_file")
    stub_marker = baseline.get("stub_marker")
    if isinstance(stub_file, str) and isinstance(stub_marker, str):
        stub_path = setup.repo_root / stub_file
        if stub_path.is_file() and stub_marker not in stub_path.read_text(
            encoding="utf-8"
        ):
            findings.append(
                f"{stub_file} no longer carries the {stub_marker!r} marker — "
                f"either the deliberate-stub note was removed by accident "
                f"(restore it), or the file is now real installer output "
                f"(update {BASELINE_FILE} to match)"
            )
    agents_md_marker = baseline.get("forbidden_agents_md_marker")
    if isinstance(agents_md_marker, str):
        agents_md_path = setup.repo_root / "AGENTS.md"
        if agents_md_path.is_file() and agents_md_marker in agents_md_path.read_text(
            encoding="utf-8"
        ):
            findings.append(
                f"AGENTS.md contains {agents_md_marker!r} — do-not.md #8 "
                f"forbids running a codex-platform `graphify install` here, "
                f"and that append is exactly what it leaves behind. Revert it."
            )
    return findings


def check_path_drift(setup: Setup) -> list[str]:
    """Does THIS shell resolve the tools mise currently pins? (#596).

    Sibling of ``pin-currency-wired`` and deliberately not a duplicate of it:
    that one asks whether the *installed* version matches the *pin*, which
    ``kb-setup currency check`` answers from the config. This one asks whether
    the **shell that is about to run the gates** resolves to that install — a
    question about a cached activation, invisible to every config-reading check.
    A shell can be perfectly current by the pin and still execute a binary two
    versions old, which is how hk 1.52.0 produced two spurious red test runs.

    Host state, so a doctor check and never an hk step: the answer is a property
    of one operator's shell session, and a CI runner's shell is always fresh.

    ⚠️ The doctor is invoked as ``mise ... run doctor``, and mise repairs ``PATH``
    before the task starts — so this check is BLIND unless the hook captured the
    ambient ``PATH`` first. It reports that blindness as a finding rather than as
    a pass; see :mod:`dotfiles_setup.path_drift` for the measurements.
    """
    baseline = _str_keys(setup.baseline.get("path_drift"))
    declared = _str_list(baseline.get("gate_tools"))
    gate_tools = tuple(declared) if declared else DEFAULT_GATE_TOOLS
    report = shell_path_drift(environ=setup.environ)
    if report.provenance is Provenance.BLIND:
        return [BLIND_ADVICE]
    if report.error is not None:
        return [f"could not compare this shell's PATH with mise: {report.error}"]
    if not report.drifts:
        return []
    return [drift_advice(report.drifts, gate=report.gate_drifts(gate_tools))]


def check_native_only(setup: Setup) -> list[str]:
    """Do ``agy``, ``codex`` and ``claude`` come ONLY from their native installers?

    Ray's ruling (2026-10-01): on the Mac host these three come from the vendor
    installer, never mise. The first ``PATH`` hit must resolve under the native
    location ``[path_drift.native_only.<binary>].native`` declares; a mise,
    Homebrew, npm- or bun-global copy first fails, as does no native copy at
    all. A mise copy later on ``PATH`` or an existing mise install directory
    warns, because each is one ``PATH`` reorder from failing.

    Silent off macOS: the devcontainer runs these CLIs from mise by design and
    has its own check. Same ambient ``PATH`` as :func:`check_path_drift`, and
    BLIND for the same reason unless the SessionStart hook captured it —
    reported, never passed.
    """
    if host_system() != _HOST_SYSTEM:
        return []
    baseline = _str_keys(_str_keys(setup.baseline.get("path_drift")).get("native_only"))
    declared: dict[str, NativeTool] = {}
    for binary, raw in baseline.items():
        entry = _str_keys(raw)
        native = tuple(_str_list(entry.get("native")))
        if not native:
            return [
                (
                    f"native-only: doctor.toml [path_drift.native_only.{binary}] "
                    f"has no `native` locations, so nothing could count as native."
                )
            ]
        declared[binary] = NativeTool(
            native=native, specs=tuple(_str_list(entry.get("specs")))
        )
    report = shell_native_only(declared or None, environ=setup.environ, home=setup.home)
    if report.provenance is Provenance.BLIND:
        return [NATIVE_ONLY_BLIND_ADVICE]
    return [*report.failures, *report.warnings]


def check_install_doctor(setup: Setup) -> list[str]:
    """Is the `claude` this shell runs the newest one, and does it report clean?

    Host state, so a doctor check rather than an hk step: the answer is a
    property of one operator's machine, and a CI runner installs afresh.

    Every verdict's findings are advisory here; the ``classic.PreToolUse`` half
    of the ``install-doctor`` plugin owns enforcement. It denies an ``INVALID``
    report or one that explicitly sets ``enforcement_eligible`` and clears an
    established deny only after a positive OK, DRIFT, or disabled answer.

    ⚠️ Blind unless the SessionStart hook captured ``PATH`` first, exactly as
    :func:`check_path_drift` is: ``uv run`` executes under mise's activated
    environment, so an uncaptured ``PATH`` resolves mise's pinned ``claude``
    rather than the operator's own install.
    :func:`install_doctor.evaluate` reports that blindness rather than passing.
    """
    baseline = _str_keys(setup.baseline.get("claude"))
    if baseline.get("enabled") is False:
        return []
    expected = baseline.get("expected_install_method")
    verdict = install_doctor.evaluate(
        expected_method=expected
        if isinstance(expected, str)
        else install_doctor.NATIVE_METHOD,
    )
    return list(verdict.findings)


# --------------------------------------------------------------------------- #
# Entry point
# --------------------------------------------------------------------------- #


def check_plugin_health(setup: Setup) -> list[str]:
    """LIVE: reconcile declared plugins against what `claude plugin list` reports.

    Thin adapter. The reconciliation lives in ``plugin_health`` so it is
    testable without a doctor fixture; the precedence pair is resolved here
    because ``enabled_plugin_ids`` is this module's, and ``plugin_health``
    importing it back would be circular.
    """
    return plugin_health_findings(
        setup, enabled_plugin_ids(setup.user_settings, setup.settings)
    )


def check_dependency_currency(setup: Setup) -> list[str]:
    """LIVE: first-level mise and Python pins that are behind.

    Imported under a non-`check_*` alias for the same reason as plugin-health:
    an imported `check_*` lands in this module's namespace and
    `test_every_check_function_is_actually_registered` then demands that exact
    object be registered, which a wrapper cannot satisfy.
    """
    return dependency_currency_findings(setup)


#: Check name -> implementation. The name tags every finding, so it is part of
#: the interface: keep it stable.


def check_codex_schema(setup: Setup) -> list[str]:
    """Codex app-server JSON schema exists and valid for installed version.

    The schema is version-specific and regenerates on codex upgrade.
    """
    findings: list[str] = []

    # `Setup` exposes `repo_root: Path` — there is no `.config.project_root`, and
    # reaching for one crashed this check on every run until item 5's fail arm
    # exercised it (`AttributeError: 'Setup' object has no attribute 'config'`).
    # `repo_root` is non-optional, so no guard clause is needed.
    is_current, message = codex_schema.check_schema_currency(
        setup.repo_root, codex_schema.get_installed_codex_version()
    )

    if not is_current:
        findings.append(f"codex schema: {message}")

    return findings


#: Reported when the baseline names no removed plugin at all.
_REMOVED_PLUGINS_UNWATCHED = (
    "removed-plugins: `doctor.toml` has no [removed_plugins].names, so no "
    "removed plugin is being watched"
)


def check_removed_plugins(setup: Setup) -> list[str]:
    """Report a removed plugin that reappears on the Claude or codex side."""
    if setup.home is None:
        return []
    section = _str_keys(setup.baseline.get("removed_plugins"))
    names = section.get("names")
    if not isinstance(names, list) or not names:
        return [_REMOVED_PLUGINS_UNWATCHED]
    found = removed_plugins.find_reappearances(
        [str(name) for name in names],
        home=setup.home,
        settings_sources={
            "~/.claude/settings.json": setup.user_settings,
            ".claude/settings.json": setup.settings,
            ".claude/settings.local.json": setup.local_settings,
        },
    )
    findings: list[str] = []
    for line in found:
        if " is unreadable (" in line:
            findings.append(f"removed plugin could not check: {line}")
        else:
            findings.append(
                f"removed plugin reappeared: {line} — remove it, or take it out of "
                "`doctor.toml` [removed_plugins] in a reviewed diff"
            )
    return findings


def check_hk_hooks(setup: Setup) -> list[str]:
    """Every required hk hook event is installed for this checkout, any scope.

    The repo stopped installing hooks from mise's postinstall (jdx/hk#1376), so
    a fresh clone has none until `hk install --global --mise` runs once per
    machine — and `do-not.md` #9 counts hk's pre-commit as an enforcement layer.
    """
    section = _str_keys(setup.baseline.get("hk_hooks"))
    required = section.get("required")
    if not isinstance(required, list) or not required:
        return [
            (
                "hk-hooks: `doctor.toml` has no [hk_hooks].required, so no hook "
                "event is being checked"
            )
        ]
    try:
        missing = hk_hooks.missing_events(
            setup.repo_root, [str(event) for event in required]
        )
    except hk_hooks.HookConfigUnreadableError as exc:
        return [f"hk-hooks: could not read git hook config: {exc}"]
    if not missing:
        return []
    return [
        (
            f"hk-hooks: no hk git hook for {', '.join(missing)} — run "
            "`hk install --global --mise` from this checkout (upstream's "
            "recommended setup, jdx/hk#1376); until then these hooks do not run "
            "on commit/push"
        )
    ]


#: One `docker ps` per architecture; a hung daemon must not hold the session.
_DOCKER_PS_TIMEOUT_S = 10.0
#: The columns :func:`docker_container_rows` asks for, tab-separated, in order.
_DOCKER_PS_FIELDS = ("{{.ID}}", "{{.State}}", "{{.Names}}")
#: One output line each; they differ only in a linked worktree.
_GIT_DIR_FLAGS = ("--git-dir", "--git-common-dir")
_GIT_TIMEOUT_S = 10.0
#: `mise env --json` measured at 0.07 s on this host (2026-09-30); the bound
#: only stops a wedged mise (a hung credential child) from holding the session.
_MISE_ENV_TIMEOUT_S = 20.0
_MISE_STDERR_LINES = 3
#: Dropped from the `mise env` child so it answers from CONFIG alone.
#: ``mise.toml`` templates DOTFILES_PLATFORM from the ambient value, so a parent
#: running under ``MISE_ENV=arm64`` would otherwise make arm64 the "default".
#: ``MISE_PROFILE``/``MISE_ENVIRONMENT`` are aliases mise 2026.9.18 honours for
#: ``MISE_ENV`` (measured: ``MISE_PROFILE=arm64`` resolved the arm64 triple).
_MISE_AMBIENT_VARS = (
    "MISE_ENV",
    "MISE_PROFILE",
    "MISE_ENVIRONMENT",
    PLATFORM_ENV_VAR,
    devcontainer_names.SSH_PORT_ENV_VAR,
)
_PORT_ENV_VAR = devcontainer_names.SSH_PORT_ENV_VAR
_PLATFORM_ENV_VAR = PLATFORM_ENV_VAR
#: Devcontainers are brought up from the macOS host (AGENTS.md, "Two Build Types").
_HOST_SYSTEM = "Darwin"


class DockerUnavailableError(RuntimeError):
    """``docker ps`` did not answer, so no container state can be concluded."""


class MiseEnvError(RuntimeError):
    """``mise env`` did not answer, so the arch a profile selects is unknown."""


def host_system() -> str:
    """``platform.system()`` — a seam, so tests choose the host they model."""
    return platform.system()


def docker_container_rows(
    names: devcontainer_names.DevcontainerNames,
    *,
    timeout_s: float = _DOCKER_PS_TIMEOUT_S,
) -> list[tuple[str, str, str]]:
    """``(id, state, name)`` of every container this clone owns for one arch.

    ``sync.container_state`` derives its state from it too (#1478), so a down
    daemon can never read as ``absent`` there either — the conflation this
    helper exists to refuse. Every failure raises
    :class:`DockerUnavailableError` whose message names the cause.
    ``timeout_s`` is the caller's bound: the session doctor wants a fast
    answer, while sync must tolerate a daemon that is busy but alive.
    """
    try:
        proc = subprocess.run(
            [
                "docker",
                "ps",
                "-a",
                "--filter",
                f"label={names.workspace_label}",
                "--filter",
                f"label={names.arch_label}",
                "--format",
                "\t".join(_DOCKER_PS_FIELDS),
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout_s,
            env=child_env.without_git_context(),
        )
    except subprocess.TimeoutExpired as exc:
        msg = f"docker ps did not answer within {timeout_s:g} s"
        raise DockerUnavailableError(msg) from exc
    except FileNotFoundError as exc:
        msg = "docker CLI not found on PATH"
        raise DockerUnavailableError(msg) from exc
    except OSError as exc:
        msg = f"docker could not run: {exc}"
        raise DockerUnavailableError(msg) from exc
    if proc.returncode != 0:
        said = (proc.stderr.strip() or proc.stdout.strip()).splitlines()
        first = said[0] if said else f"exit {proc.returncode}"
        msg = (
            f"docker ps failed: {first}; is Docker Desktop running and the "
            "context right?"
        )
        raise DockerUnavailableError(msg)
    rows: list[tuple[str, str, str]] = []
    for line in proc.stdout.splitlines():
        if not line.strip():
            continue
        fields = line.split("\t")
        if len(fields) != len(_DOCKER_PS_FIELDS):
            msg = f"unparsable docker ps line: {line}"
            raise DockerUnavailableError(msg)
        rows.append((fields[0], fields[1], fields[2]))
    return rows


@dataclass(frozen=True)
class MiseResolution:
    """What one mise profile resolves the two devcontainer selectors to."""

    platform: str
    arch: str
    ssh_port: str


def mise_env_resolution(
    repo_root: Path,
    environ: Mapping[str, str],
    mise_env: str | None = None,
) -> MiseResolution:
    """``DOTFILES_PLATFORM`` / ``DEVCONTAINER_SSH_PORT`` as mise resolves them.

    ``mise_env`` ``None`` is the default profile; otherwise ``mise -E <name>``,
    exactly what ``MISE_ENV=<name> mise run up`` selects. Resolving through mise
    itself (not this process's environment) is the point: outside mise the
    process env falls back to the host's arm64, and mise's own precedence
    between ``mise.local.toml`` and ``mise.<env>.toml`` contradicts its docs
    (measured 2026-09-30), so only the resolved value is evidence. Every failure
    raises :class:`MiseEnvError`.
    """
    argv = ["mise", *(("-E", mise_env) if mise_env else ()), "env", "--json"]
    label = " ".join(argv[:-2])
    child_env = {k: v for k, v in environ.items() if k not in _MISE_AMBIENT_VARS}
    # mise's env cache is keyed without the caller's env values, so a parent run
    # that saw an ambient DOTFILES_PLATFORM could serve it to this stripped child
    # (cold review of 4ccb98a5, measured on a clone without a local pin).
    child_env["MISE_ENV_CACHE"] = "0"
    try:
        proc = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            check=False,
            cwd=repo_root,
            env=child_env,
            stdin=subprocess.DEVNULL,
            timeout=_MISE_ENV_TIMEOUT_S,
        )
    except subprocess.TimeoutExpired as exc:
        msg = f"`{label} env` did not answer within {_MISE_ENV_TIMEOUT_S:g} s"
        raise MiseEnvError(msg) from exc
    except FileNotFoundError as exc:
        msg = "mise not found on PATH"
        raise MiseEnvError(msg) from exc
    except OSError as exc:
        msg = f"`{label} env` could not run: {exc}"
        raise MiseEnvError(msg) from exc
    if proc.returncode != 0:
        said = [line.strip() for line in proc.stderr.splitlines() if line.strip()]
        # Up to three lines: mise puts the cause ("not trusted") on line 2.
        detail = " | ".join(said[:_MISE_STDERR_LINES]) if said else "no stderr"
        msg = f"`{label} env` exited {proc.returncode}: {detail}"
        raise MiseEnvError(msg)
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        msg = f"`{label} env` printed unparsable JSON ({exc.msg})"
        raise MiseEnvError(msg) from exc
    if not isinstance(data, dict):
        msg = f"`{label} env` printed JSON that is not an object"
        raise MiseEnvError(msg)
    platform_value = str(data.get(_PLATFORM_ENV_VAR, ""))
    try:
        arch = platform_arch(platform_value)
    except ValueError as exc:
        msg = f"`{label} env` resolves {_PLATFORM_ENV_VAR}={platform_value!r}: {exc}"
        raise MiseEnvError(msg) from exc
    return MiseResolution(
        platform=platform_value,
        arch=arch,
        ssh_port=str(data.get(_PORT_ENV_VAR, "")).strip(),
    )


def is_linked_worktree(repo_root: Path) -> bool:
    """Whether ``repo_root`` is a linked git worktree rather than the main checkout.

    Git that cannot answer (missing, hung past the bound, not a repository) is
    treated as "not a linked worktree", so the check still runs — failing open
    to checking, not to silence.
    """
    try:
        proc = subprocess.run(
            [
                "git",
                "-C",
                str(repo_root),
                "rev-parse",
                "--path-format=absolute",
                *_GIT_DIR_FLAGS,
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=_GIT_TIMEOUT_S,
            # An inherited GIT_DIR overrides `-C` and makes a linked worktree
            # read as the main checkout, silencing ship's #1481 refusal.
            env=child_env.without_git_context(),
        )
    except OSError, subprocess.TimeoutExpired:
        return False
    lines = proc.stdout.splitlines()
    if proc.returncode != 0 or len(lines) != len(_GIT_DIR_FLAGS):
        return False
    return Path(lines[0]).resolve() != Path(lines[1]).resolve()


def _configured_arches(section: dict[str, object]) -> tuple[list[str], str | None]:
    """The normalized ``[devcontainers].arches``, or a config finding."""
    entries = section.get("arches")
    if not isinstance(entries, list) or not entries:
        return [], (
            "devcontainers: doctor.toml has no [devcontainers].arches, so no "
            "container is being checked"
        )
    arches: list[str] = []
    bad: list[str] = []
    for entry in entries:
        try:
            arch = platform_arch(entry) if isinstance(entry, str) else None
        except ValueError:
            arch = None
        if arch is None or arch in arches:
            bad.append(repr(entry))
        else:
            arches.append(arch)
    if bad:
        return [], (
            f"devcontainers: doctor.toml [devcontainers].arches has unusable "
            f"entries {', '.join(bad)} — each must be a distinct arch word "
            "(amd64, arm64); no container is being checked"
        )
    return arches, None


def _profile_findings(
    arch: str, profile: MiseResolution, default: MiseResolution
) -> list[str]:
    """Does ``MISE_ENV=<arch>`` really select ``arch``, on its own port?"""
    findings: list[str] = []
    published = published_platform(arch)
    if profile.platform != published:
        findings.append(
            f"devcontainers: `MISE_ENV={arch}` resolves "
            f"{_PLATFORM_ENV_VAR}={profile.platform}, not the published "
            f"{published}, so `MISE_ENV={arch} mise run up` would bring up "
            f"{profile.arch or 'an unpublished platform'}; check mise.{arch}.toml"
        )
    if profile.ssh_port and profile.ssh_port == default.ssh_port:
        findings.append(
            f"devcontainers: `MISE_ENV={arch}` resolves {_PORT_ENV_VAR}="
            f"{profile.ssh_port}, the same port the default {default.arch} "
            f"container uses, so the two collide; blank it in mise.{arch}.toml"
        )
    return findings


def _profile_phase(
    setup: Setup, arches: list[str], default: MiseResolution
) -> tuple[list[str], list[str], list[str]]:
    """Assert each non-default arch's profile; return findings, arches, failures.

    An arch whose ``mise -E`` run fails is left out of the container query: its
    restore command is unknown, so a container finding would name a guess.
    """
    findings: list[str] = []
    queryable: list[str] = []
    failures: list[str] = []
    for arch in arches:
        if arch != default.arch:
            try:
                profile = mise_env_resolution(setup.repo_root, setup.environ, arch)
            except MiseEnvError as exc:
                failures.append(str(exc))
                continue
            findings.extend(_profile_findings(arch, profile, default))
        queryable.append(arch)
    return findings, queryable, failures


def _container_phase(setup: Setup, arches: list[str], default_arch: str) -> list[str]:
    """One finding per arch without a running container.

    A docker failure appends ONE unverifiable finding and stops querying, but
    the definite findings already made for earlier arches are kept.
    """
    findings: list[str] = []
    env = dict(setup.environ)
    for arch in arches:
        names = devcontainer_names.resolve_names(
            workspace=setup.repo_root, platform=arch, env=env
        )
        restore = (
            "mise run up" if arch == default_arch else f"MISE_ENV={arch} mise run up"
        )
        try:
            rows = docker_container_rows(names)
        except DockerUnavailableError as exc:
            findings.append(f"devcontainers: UNVERIFIABLE — {exc}")
            break
        if not rows:
            findings.append(
                f"devcontainers: no {arch} container for this clone — run `{restore}`"
            )
        elif not any(state == "running" for _, state, _ in rows):
            _, state, name = rows[0]
            findings.append(
                f"devcontainers: {arch} container {name} is {state} — run `{restore}`"
            )
    return findings


def check_devcontainers_running(setup: Setup) -> list[str]:
    """Every architecture in ``[devcontainers].arches`` has a RUNNING container.

    Docker Desktop quitting stops every workspace container, and nothing
    restarts them by itself: `land`/`sync` bring back only the default
    architecture, so on 2026-09-29 the arm64 container sat exited for ~24 h
    unreported. Each finding names the command that restores that architecture,
    and that command is itself checked: each non-default arch's ``MISE_ENV``
    profile must resolve (through mise) to that arch on a port of its own.

    Silent where it cannot apply. Devcontainers are brought up from the macOS
    host (AGENTS.md "Two Build Types"): inside the container there is no docker
    CLI or socket, and on a Linux CI host the concept does not exist. A linked
    git worktree is silent too: the devcontainers belong to the main checkout,
    whose path is what their workspace label hashes.
    """
    if host_system() != _HOST_SYSTEM:
        return []
    arches, config_finding = _configured_arches(
        _str_keys(setup.baseline.get("devcontainers"))
    )
    if config_finding is not None:
        return [config_finding]
    if is_linked_worktree(setup.repo_root):
        return []
    try:
        default = mise_env_resolution(setup.repo_root, setup.environ)
    except MiseEnvError as exc:
        return [f"devcontainers: UNVERIFIABLE — mise env failed ({exc})"]
    findings, queryable, mise_failures = _profile_phase(setup, arches, default)
    findings.extend(_container_phase(setup, queryable, default.arch))
    if mise_failures:
        findings.append(
            "devcontainers: UNVERIFIABLE — mise env failed "
            f"({'; '.join(mise_failures)})"
        )
    return findings


CHECKS: tuple[tuple[str, Callable[[Setup], list[str]]], ...] = (
    ("mcp-env-opt-in", check_mcp_env_opt_in),
    ("mcp-scope", check_mcp_scope),
    ("fnox-baseline", check_fnox_baseline),
    ("fnox-workflows", check_fnox_workflows),
    ("fnox-services", check_fnox_services),
    ("fnox-exec-leak", check_exec_only_not_leaked),
    ("mcp-pin", check_mcp_pin),
    ("mcp-guard-coverage", check_mcp_guard_coverage),
    ("mcp-duplicate", check_mcp_duplicate),
    ("pin-currency-wired", check_pin_currency_wired),
    ("listing-budget", check_listing_budget),
    ("path-drift", check_path_drift),
    ("native-only", check_native_only),
    ("graphify-skill-surface", check_graphify_skill_surface),
    ("install-doctor", check_install_doctor),
    ("codex-schema", check_codex_schema),
    ("removed-plugins", check_removed_plugins),
    ("hk-hooks", check_hk_hooks),
    ("devcontainers", check_devcontainers_running),
)

#: Only run with ``--live``: each entry spawns subprocesses.
LIVE_CHECKS: tuple[tuple[str, Callable[[Setup], list[str]]], ...] = (
    ("mcp-live-tools", check_live_servers),
    ("mcp-health", check_mcp_health),
    # Declared-vs-actual plugin reconciliation. LIVE because it runs
    # `claude plugin list --json`. `declared` is computed HERE so the
    # user-then-project precedence has exactly one implementation
    # (`enabled_plugin_ids`) and plugin_health.py needs no import of this
    # module, which would be circular.
    ("plugin-health", check_plugin_health),
    ("dependency-currency", check_dependency_currency),
)

FNOX_LIVE_CHECKS: tuple[tuple[str, Callable[[Setup], list[str]]], ...] = (
    ("fnox-resolution", check_fnox_resolution),
)


@dataclass(frozen=True)
class DoctorSelection:
    """Choose optional live probes and a focused fnox-only view."""

    live: bool = False
    fnox_live: bool = False
    fnox_only: bool = False


def _record_crash(name: str, exc: BaseException, log_path: Path) -> None:
    """Append a crashed check to the error log; never raise while doing it."""
    stamp = dt.datetime.now(dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a") as handle:
            handle.write(f"{stamp}\t{name}\t{type(exc).__name__}: {exc}\n")
    except OSError:
        logger.debug("doctor: could not record crash of %s", name, exc_info=True)


def run_checks(
    setup: Setup,
    *,
    live: bool = False,
    fnox_live: bool = False,
    fnox_only: bool = False,
    log_path: Path | None = None,
) -> list[tuple[str, list[str]]]:
    """Run every applicable check, containing a crash as a finding of its own.

    A crashed check must neither disrupt the session nor pass silently: it is
    recorded to the error log AND surfaced, because a doctor that quietly stops
    checking is worse than no doctor — #343's lesson, one layer up.
    """
    log_path = log_path or ERROR_LOG
    results: list[tuple[str, list[str]]] = []
    base_checks = (
        tuple(
            item
            for item in CHECKS
            if item[0].startswith("fnox-") or item[0] == "mcp-env-opt-in"
        )
        if fnox_only
        else CHECKS
    )
    checks = (
        base_checks
        + (LIVE_CHECKS if live and not fnox_only else ())
        + (FNOX_LIVE_CHECKS if fnox_live else ())
    )
    for name, check in checks:
        try:
            results.append((name, check(setup)))
        except Exception as exc:
            # Blind by design: ANY defect in a check must be contained, since the
            # alternative is a doctor that can disrupt a session. Logged with the
            # traceback (stderr) as well as recorded and surfaced, so a crash is
            # never cheaper to ignore than to fix.
            logger.exception("doctor: check %s crashed", name)
            _record_crash(name, exc, log_path)
            results.append(
                (
                    name,
                    [f"check crashed ({type(exc).__name__}: {exc}) — see {log_path}"],
                )
            )
    return results


def render(results: list[tuple[str, list[str]]], *, verbose: bool = False) -> list[str]:
    """The lines to print: drift always, PASS lines only when asked."""
    lines: list[str] = []
    findings = 0
    for name, check_findings in results:
        if not check_findings:
            if verbose:
                lines.append(f"PASS  doctor[{name}]")
            continue
        findings += len(check_findings)
        lines.extend(f"DRIFT doctor[{name}]: {finding}" for finding in check_findings)
    if findings:
        lines.append(
            f"doctor: {findings} finding(s) — each is a place where this host "
            f"stopped matching {BASELINE_FILE}. Fix the host, or change the "
            f"baseline in a reviewed diff. `--live` adds MCP probes; "
            f"`mise run doctor-fnox` resolves fnox workflow scopes."
        )
    elif verbose:
        lines.append("doctor: OK — the declared setup matches this host")
    return lines


def doctor_main(
    repo_root: Path,
    *,
    selection: DoctorSelection | None = None,
    strict: bool = False,
    verbose: bool = False,
) -> int:
    """Print drift and nothing else; 0 unless ``--strict`` and drift was found."""
    selection = selection or DoctorSelection()
    results = run_checks(
        collect(repo_root),
        live=selection.live,
        fnox_live=selection.fnox_live,
        fnox_only=selection.fnox_only,
    )
    for line in render(results, verbose=verbose):
        sys.stdout.write(f"{line}\n")
    drifted = any(findings for _, findings in results)
    return 1 if (drifted and strict) else 0
