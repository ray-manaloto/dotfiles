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
import re
import shutil
import subprocess
import sys
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

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
    Provenance,
    drift_advice,
)

# Deliberately NOT imported as ``check_*``: ``test_every_check_function_is_
# actually_registered`` enumerates this module's ``check_*`` names and requires
# each to be in CHECKS, so an imported one would be an unregistrable false
# positive — the guard caught this import on its first run.
from dotfiles_setup.path_drift import check_path_drift as shell_path_drift

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

# `${VAR}` / `${VAR:-default}` — the interpolation Claude Code performs on an
# MCP server's env and headers before spawning it.
_INTERPOLATION_RE = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)(?::-[^}]*)?\}")

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
    return FnoxState(
        exists=True,
        env_mode=data.get("env", True),
        per_secret=per_secret,
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
        local_settings=load_json(repo_root / ".claude" / "settings.local.json"),
        fnox=read_fnox(home / ".config" / "fnox" / "config.toml"),
        environ=environ,
        listing=collect_listing(
            repo_root, home, enabled_plugin_ids(user_settings, settings)
        ),
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
    findings = [
        f"{entry.kind} {entry.name!r} ({entry.source}) has a "
        f"{entry.desc_chars}-char description over the HARD {SKILL_DESCRIPTION_MAX} "
        f"cap — the tail is TRUNCATED SILENTLY, taking the keywords it is matched "
        f"on with it: {entry.path}"
        for entry in over_cap(setup.listing)
    ]
    ceiling = setup.listing_baseline().get("max_chars")
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


# --------------------------------------------------------------------------- #
# Entry point
# --------------------------------------------------------------------------- #

#: Check name -> implementation. The name tags every finding, so it is part of
#: the interface: keep it stable.
CHECKS: tuple[tuple[str, Callable[[Setup], list[str]]], ...] = (
    ("mcp-env-opt-in", check_mcp_env_opt_in),
    ("mcp-scope", check_mcp_scope),
    ("fnox-baseline", check_fnox_baseline),
    ("mcp-pin", check_mcp_pin),
    ("mcp-guard-coverage", check_mcp_guard_coverage),
    ("mcp-duplicate", check_mcp_duplicate),
    ("pin-currency-wired", check_pin_currency_wired),
    ("listing-budget", check_listing_budget),
    ("path-drift", check_path_drift),
)

#: Only run with ``--live``: each entry spawns subprocesses.
LIVE_CHECKS: tuple[tuple[str, Callable[[Setup], list[str]]], ...] = (
    ("mcp-live-tools", check_live_servers),
    ("mcp-health", check_mcp_health),
)


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
    log_path: Path | None = None,
) -> list[tuple[str, list[str]]]:
    """Run every applicable check, containing a crash as a finding of its own.

    A crashed check must neither disrupt the session nor pass silently: it is
    recorded to the error log AND surfaced, because a doctor that quietly stops
    checking is worse than no doctor — #343's lesson, one layer up.
    """
    log_path = log_path or ERROR_LOG
    results: list[tuple[str, list[str]]] = []
    for name, check in CHECKS + (LIVE_CHECKS if live else ()):
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
            f"baseline in a reviewed diff. `mise run doctor -- --live` adds "
            f"the live MCP probes."
        )
    elif verbose:
        lines.append("doctor: OK — the declared setup matches this host")
    return lines


def doctor_main(
    repo_root: Path,
    *,
    live: bool = False,
    strict: bool = False,
    verbose: bool = False,
) -> int:
    """Print drift and nothing else; 0 unless ``--strict`` and drift was found."""
    results = run_checks(collect(repo_root), live=live)
    for line in render(results, verbose=verbose):
        sys.stdout.write(f"{line}\n")
    drifted = any(findings for _, findings in results)
    return 1 if (drifted and strict) else 0
