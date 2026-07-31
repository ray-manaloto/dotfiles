"""PROTOTYPE (throwaway) — the secrets-CLI shape as a pure decision function.

THE QUESTION (wayfinder #432)
-----------------------------
What shape should the secrets CLI be, given that its consumers are the Claude
Code and Codex plugins?  Specifically: which verbs do the plugins actually need,
what does the plugin<->CLI call boundary look like, and where do hooks + agent
documentation have to take over if plugins alone cannot enforce use?

THE INVARIANT BEING STRESSED
----------------------------
The map locks the exposure model as **reference-only**: an agent causes a secret
to be consumed, it never receives the value.  So for every agent caller and every
verb, `Decision.leaks` must be False.  The whole point of this module is that it
is easy to make that go True -- flip `Design.get_secret_denied` off and watch.

WHAT IS MEASURED VS ASSUMED
---------------------------
Facts marked PROBED were measured on this host on 2026-07-30 (fnox 1.31.1).
Everything else is a design position to react to, not a finding.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum

# ---------------------------------------------------------------------------
# Domain
# ---------------------------------------------------------------------------


class Caller(StrEnum):
    """Who is making the call."""

    HUMAN = "human"
    CLAUDE = "claude-code"
    CODEX = "codex"


class Verb(StrEnum):
    """The candidate verb set, straight from the ticket body."""

    ADD = "add"
    UPDATE = "update"
    REMOVE = "remove"
    LIST = "list"
    EXEC = "exec"
    STATUS = "status"


class Route(StrEnum):
    """Where the call physically lands."""

    ZSH_EVAL = "zsh fn -> mde-py (eval into current shell)"
    DOTFILES_CLI = "dotfiles-secrets (the CLI being designed)"
    FNOX_MCP_EXEC = "fnox mcp :: exec"
    FNOX_MCP_GET = "fnox mcp :: get_secret"
    DOPPLER_CLI = "doppler CLI (source-of-truth write)"
    BLOCKED = "-- no affordance --"


class Layer(StrEnum):
    """What stops the caller from taking a route it should not take."""

    PLUGIN = "plugin (only affordance offered)"
    MCP_DENY = "consumer-side MCP tool deny"
    HOOK = "PreToolUse / codex hook"
    DOCS = "AGENTS.md + skill prose"
    NONE = "nothing"


# ---------------------------------------------------------------------------
# Enforcement availability -- PROBED, 2026-07-30, this host
# ---------------------------------------------------------------------------

#: Is a given enforcement layer actually real for a given caller?
#: `None` means UNVERIFIED -- absence from `--help` is a search bound, not proof
#: (.claude/rules/probes-need-a-control-arm.md).
LAYER_AVAILABLE: dict[tuple[Caller, Layer], bool | None] = {
    # Claude Code: all four layers exist and this repo already uses three.
    (Caller.CLAUDE, Layer.PLUGIN): True,
    (Caller.CLAUDE, Layer.MCP_DENY): True,  # permissions deny mcp__fnox__get_secret
    (Caller.CLAUDE, Layer.HOOK): True,  # hook_guard.py, already wired
    (Caller.CLAUDE, Layer.DOCS): True,
    # Codex: hooks are real (`--dangerously-bypass-hook-trust`, and ~/.codex/
    # config.toml's own header names "hooks, and rules"). Per-tool MCP deny was
    # NOT found on `codex mcp add --help` -- but that is a bound, not an answer.
    (Caller.CODEX, Layer.PLUGIN): True,
    (Caller.CODEX, Layer.MCP_DENY): None,
    (Caller.CODEX, Layer.HOOK): True,
    (Caller.CODEX, Layer.DOCS): True,
}

#: PROBED: on this Mac ~/.codex/config.toml sets approval_policy = "never" and
#: sandbox_mode = "danger-full-access". Codex's approval prompt is therefore NOT
#: an available layer here -- it will not ask. Hooks are the only live gate.
CODEX_APPROVALS_DISABLED_ON_THIS_HOST = True


@dataclass(frozen=True)
class Design:
    """The four open design choices. Flip these and watch the matrix move."""

    #: Delegate `exec` to fnox's own MCP server rather than owning it.
    #: PROBED: `fnox mcp` exposes exactly two tools, `exec` and `get_secret`.
    exec_via_fnox_mcp: bool = True
    #: Deny the leaking `get_secret` tool consumer-side. Without this,
    #: adopting fnox mcp hands raw values to the agent.
    get_secret_denied: bool = True
    #: Writes go through the `doppler` CLI (locked: Doppler's fnox provider is
    #: read-only, so the write path is the CLI) rather than editing fnox config.
    writes_via_doppler_cli: bool = True
    #: Keep the incumbent zsh `eval "$(...)"` propagation for the human.
    #: PROBED: this is what re-exports every credential into the login shell --
    #: it is the mechanism `env = "exec"` exists to defeat.
    keep_shell_eval: bool = False


@dataclass(frozen=True)
class Decision:
    """What happens for one (caller, verb) under one Design."""

    route: Route
    call: str
    leaks: bool
    enforced_by: Layer
    note: str = ""

    @property
    def layer_is_real(self) -> bool | None:
        """Whether `enforced_by` actually exists for the caller. See caller-aware
        `decide`, which resolves this; `None` == unverified."""
        return self._layer_real

    _layer_real: bool | None = None


# ---------------------------------------------------------------------------
# The decision function -- the bit worth lifting into the real codebase
# ---------------------------------------------------------------------------

WRITE_VERBS = (Verb.ADD, Verb.UPDATE, Verb.REMOVE)


def decide(caller: Caller, verb: Verb, design: Design) -> Decision:
    """Resolve one cell of the (caller x verb) matrix under `design`."""
    d = _route(caller, verb, design)
    real = LAYER_AVAILABLE.get((caller, d.enforced_by), True)
    return replace(d, _layer_real=real)


#: PROBED: appended to any Codex cell that leans on a runtime gate, because on
#: this host Codex will not stop to ask.
CODEX_CAVEAT = (
    " [codex: approval_policy=\"never\", sandbox_mode=\"danger-full-access\" on "
    "this host -- no approval prompt will fire, so the hook is the only gate]"
)


def _route(caller: Caller, verb: Verb, design: Design) -> Decision:
    if caller is Caller.HUMAN:
        return _human(verb, design)
    d = _agent(verb, design)
    if caller is Caller.CODEX and d.enforced_by in (Layer.HOOK, Layer.MCP_DENY):
        d = replace(d, note=d.note + CODEX_CAVEAT)
    return d


def _human(verb: Verb, design: Design) -> Decision:
    """The human is allowed to see values. Nothing here is an invariant breach --
    the only question is whether the shell-eval wipe trigger survives."""
    if verb in WRITE_VERBS:
        if design.keep_shell_eval:
            return Decision(
                route=Route.ZSH_EVAL,
                call=f"mde-secret-{verb.value}  KEY",
                leaks=False,
                enforced_by=Layer.NONE,
                note="WIPE TRIGGER: eval of `export KEY=...` re-exports all 49 "
                "creds into the login shell, and mde-py's bootstrap_config() "
                "drops env=\"exec\" + every opt-in. macos-development-environment#82.",
            )
        return Decision(
            route=Route.DOPPLER_CLI if design.writes_via_doppler_cli else Route.DOTFILES_CLI,
            call=f"dotfiles-secrets {verb.value} KEY   # value via stdin/prompt",
            leaks=False,
            enforced_by=Layer.NONE,
            note="No shell eval: the value never enters the interactive shell, "
            "so the wipe trigger and the __MISE_DIFF blob both go away.",
        )
    if verb is Verb.EXEC:
        return Decision(
            route=Route.DOTFILES_CLI,
            call="fnox exec -- <cmd>",
            leaks=False,
            enforced_by=Layer.NONE,
            note="Already native. Nothing to build.",
        )
    return Decision(
        route=Route.DOTFILES_CLI,
        call=f"dotfiles-secrets {verb.value}",
        leaks=False,
        enforced_by=Layer.NONE,
    )


def _agent(verb: Verb, design: Design) -> Decision:
    """Agent callers. Every cell here must have leaks=False or the map's
    reference-only constraint is broken."""
    if verb is Verb.EXEC:
        if design.exec_via_fnox_mcp:
            if not design.get_secret_denied:
                return Decision(
                    route=Route.FNOX_MCP_GET,
                    call="mcp__fnox__get_secret(name=...)  ->  RAW VALUE",
                    leaks=True,
                    enforced_by=Layer.NONE,
                    note="Registering `fnox mcp` ships get_secret ALONGSIDE exec. "
                    "There is no server-side flag to disable it -- the deny has "
                    "to come from the consumer, or the whole server is unusable.",
                )
            return Decision(
                route=Route.FNOX_MCP_EXEC,
                call='mcp__fnox__exec(command=["gh","api","user"])',
                leaks=False,
                enforced_by=Layer.MCP_DENY,
                note="Reference-only by construction: no shell, secrets injected "
                "as env, only stdout/stderr returned. get_secret denied alongside.",
            )
        return Decision(
            route=Route.DOTFILES_CLI,
            call="dotfiles-secrets exec -- <cmd>",
            leaks=False,
            enforced_by=Layer.HOOK,
            note="Owning exec ourselves means re-implementing what `fnox mcp exec` "
            "already does -- a use-tool-builtins.md debt.",
        )

    if verb in WRITE_VERBS:
        return Decision(
            route=Route.DOPPLER_CLI if design.writes_via_doppler_cli else Route.DOTFILES_CLI,
            call=f"dotfiles-secrets {verb.value} KEY --from-op/--prompt-human",
            leaks=False,
            enforced_by=Layer.PLUGIN,
            note="THE ACTUAL GAP: `fnox mcp` has NO write path at all. If the "
            "agent must never see the value, the agent cannot supply it either -- "
            "so a write verb is really 'ask the human for a value I never read'.",
        )

    if verb is Verb.LIST:
        return Decision(
            route=Route.DOTFILES_CLI,
            call="dotfiles-secrets list          # names only; -V is human-only",
            leaks=False,
            enforced_by=Layer.PLUGIN,
            note="PROBED: `fnox list` is already names-only by default; -V/--values "
            "opts in. The leak is a flag, not the verb.",
        )

    return Decision(
        route=Route.DOTFILES_CLI,
        call="dotfiles-secrets status        # mode, opt-ins, drift vs doctor.toml",
        leaks=False,
        enforced_by=Layer.PLUGIN,
        note="Subsumes mise run doctor's fnox-baseline check -- the thing that "
        "caught the wipe. Reads config, never a value.",
    )


# ---------------------------------------------------------------------------
# Whole-matrix view + the invariant
# ---------------------------------------------------------------------------


def matrix(design: Design) -> dict[tuple[Caller, Verb], Decision]:
    return {(c, v): decide(c, v, design) for c in Caller for v in Verb}


def invariant_breaches(design: Design) -> list[tuple[Caller, Verb, Decision]]:
    """Reference-only: no agent caller may receive a raw value."""
    return [
        (c, v, d)
        for (c, v), d in matrix(design).items()
        if c is not Caller.HUMAN and d.leaks
    ]


def unverified_layers(design: Design) -> list[tuple[Caller, Verb, Decision]]:
    """Cells whose enforcement layer has not been proven to exist."""
    return [
        (c, v, d)
        for (c, v), d in matrix(design).items()
        if d.layer_is_real is None
    ]
