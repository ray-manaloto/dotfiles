"""PROTOTYPE (throwaway) — the secrets-CLI shape as a pure decision function.

THE QUESTION (wayfinder #432)
-----------------------------
What shape should the secrets CLI be, given that its consumers are the Claude
Code and Codex plugins?  Which verbs do the plugins actually need, what does the
plugin<->CLI call boundary look like, and where do hooks + agent documentation
have to take over if plugins alone cannot enforce use?

WHAT THE PROTOTYPE CHANGED
--------------------------
It was built to stress ONE invariant: the map's "reference-only -- the agent
causes a secret to be consumed, it never receives the value."  Building it
falsified that invariant (see PROBE, below).  So the model now measures BLAST
RADIUS -- how many secrets are readable at a given call -- instead of pretending
a boolean.  That reframing is the prototype's actual output.

The `Design` defaults below are the SETTLED shape (Ray, HITL, 2026-07-30).
Flip any of them to see the option that was rejected and why.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum

TOTAL_SECRETS = 49  # PROBED: what `fnox activate` puts in the login shell today


class Caller(StrEnum):
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
    ZSH_EVAL = "zsh fn -> mde-py (eval into current shell)"
    DOTFILES_CLI = "dotfiles-secrets (the CLI being designed)"
    FNOX_MCP_EXEC = "fnox mcp :: exec"
    FNOX_MCP_GET = "fnox mcp :: get_secret"
    DOPPLER_CLI = "doppler CLI (source-of-truth write)"
    BLOCKED = "-- no agent affordance --"


class Layer(StrEnum):
    STRUCTURAL = 'structural (env="exec": nothing in scope to read)'
    HOOK = "hook backstop (refuse when the mode is wiped)"
    PLUGIN = "plugin (only affordance offered)"
    MCP_DENY = "consumer-side MCP tool deny"
    DOCS = "AGENTS.md + skill prose"
    NONE = "nothing"


# ---------------------------------------------------------------------------
# Enforcement availability -- PROBED, 2026-07-30, this host
# ---------------------------------------------------------------------------

#: `None` == UNVERIFIED. Absence from `--help` is a search bound, not proof
#: (.claude/rules/probes-need-a-control-arm.md).
LAYER_AVAILABLE: dict[tuple[Caller, Layer], bool | None] = {
    (Caller.CLAUDE, Layer.STRUCTURAL): True,
    (Caller.CLAUDE, Layer.HOOK): True,  # hook_guard.py, already wired
    (Caller.CLAUDE, Layer.PLUGIN): True,
    (Caller.CLAUDE, Layer.MCP_DENY): True,
    (Caller.CLAUDE, Layer.DOCS): True,
    # Codex has hooks/skills/rules (`--dangerously-bypass-hook-trust`, and
    # ~/.codex/config.toml's own header names them) -- but that is a SECOND
    # implementation to write and keep in sync, which is this option's cost.
    (Caller.CODEX, Layer.STRUCTURAL): True,  # env is env; nothing to port
    (Caller.CODEX, Layer.HOOK): True,
    (Caller.CODEX, Layer.PLUGIN): True,
    (Caller.CODEX, Layer.MCP_DENY): None,
    (Caller.CODEX, Layer.DOCS): True,
}

#: PROBED: ~/.codex/config.toml sets approval_policy = "never" and
#: sandbox_mode = "danger-full-access". Codex will NOT stop to ask on this host,
#: so its approval prompt is not an available layer. Hooks are the only gate.
CODEX_CAVEAT = (
    ' [codex: approval_policy="never", sandbox_mode="danger-full-access" on this '
    "host -- no approval prompt fires, and this layer needs a second Codex port]"
)


@dataclass(frozen=True)
class Design:
    """Defaults are the SETTLED shape. Flip one to see the rejected option."""

    #: DECIDED: the agent cannot write at all. Origination is human-only --
    #: nobody can hand an agent a value it must not read, so `add`/`update`/
    #: `remove` simply have no agent affordance. No agent write path to secure.
    agent_may_write: bool = False

    #: DECIDED: least-privilege scoping. An fnox agent profile puts only that
    #: command's secrets in the environment. The agent CAN read what it was
    #: given; nothing else exists to read.
    #: DEPENDS ON #441 (fnox Composable Profiles), which is blocked on #435.
    scoped_agent_profile: bool = True

    #: REJECTED in favour of scoping: you cannot enumerate every command an
    #: agent legitimately runs, and the deny half fails open on novel shapes.
    exec_command_allowlist: bool = False

    #: DECIDED: structural first -- with `env = "exec"` the agent's shell holds
    #: nothing, so an exec verb is the only path that works at all.
    structural_empty_env: bool = True

    #: DECIDED: a hook backstop for the ONE known failure of the above -- the
    #: mode getting wiped (mde-py's bootstrap_config, macos-development-
    #: environment#82). It checks the MODE, it does not sniff commands.
    hook_backstop: bool = True

    #: DECIDED: plain CLI over Bash, register nothing. PROBED that MCP-vs-CLI is
    #: NOT a security axis (both leak identically), so the choice falls to cost,
    #: and research-doc-sources.md lane 2 says CLI.
    exec_via_fnox_mcp: bool = False

    #: Moot under the above, kept to show why: denying get_secret buys nothing
    #: while the caller still picks the command.
    get_secret_denied: bool = True

    #: The incumbent zsh `eval "$(...)"` propagation. PROBED: this is what
    #: re-exports all 49 into the login shell, and it is the wipe trigger.
    keep_shell_eval: bool = False


@dataclass(frozen=True)
class Decision:
    """What happens for one (caller, verb) under one Design."""

    route: Route
    call: str
    #: How many secrets the caller can READ at this call. The prototype's whole
    #: correction: this is a number, not a boolean.
    #:
    #: PROBED 2026-07-30 -- `exec` does not confine, in EITHER form:
    #:   fnox exec -- sh -c 'echo ${#EXA_API_KEY}'  -> 36
    #:   ... same name, not a secret                ->  0  (arm: discriminates)
    #:   ... same var, outside fnox                 ->  0  (arm: fnox injects)
    #: Not a workaround: `mcp__fnox__exec`'s own description says
    #: "To use shell expansion, pass ["sh","-c",...]".
    readable: int
    enforced_by: Layer
    note: str = ""
    _layer_real: bool | None = None

    @property
    def layer_is_real(self) -> bool | None:
        return self._layer_real


WRITE_VERBS = (Verb.ADD, Verb.UPDATE, Verb.REMOVE)


def decide(caller: Caller, verb: Verb, design: Design) -> Decision:
    """Resolve one cell of the (caller x verb) matrix under `design`."""
    d = _human(verb, design) if caller is Caller.HUMAN else _agent(verb, design)
    if caller is Caller.CODEX and d.enforced_by in (Layer.HOOK, Layer.MCP_DENY):
        d = replace(d, note=d.note + CODEX_CAVEAT)
    return replace(d, _layer_real=LAYER_AVAILABLE.get((caller, d.enforced_by), True))


def _human(verb: Verb, design: Design) -> Decision:
    """The human is allowed to read. The only question here is whether the
    incumbent shell-eval -- and with it the wipe trigger -- survives."""
    if verb in WRITE_VERBS:
        if design.keep_shell_eval:
            return Decision(
                route=Route.ZSH_EVAL,
                call=f"mde-secret-{verb.value} KEY",
                readable=TOTAL_SECRETS,
                enforced_by=Layer.NONE,
                note="WIPE TRIGGER: the eval of `export KEY=...` re-exports all "
                f"{TOTAL_SECRETS} into the login shell, and mde-py's "
                'bootstrap_config() drops env="exec" + every opt-in. '
                "macos-development-environment#82.",
            )
        return Decision(
            route=Route.DOPPLER_CLI,
            call=f"dotfiles-secrets {verb.value} KEY   # value via stdin/prompt",
            readable=1,
            enforced_by=Layer.NONE,
            note="No shell eval: the value never enters the interactive shell, so "
            "the wipe trigger and the __MISE_DIFF blob both go away. Writes land "
            "via the `doppler` CLI -- fnox's Doppler provider is read-only (#433).",
        )
    if verb is Verb.EXEC:
        return Decision(
            route=Route.DOTFILES_CLI,
            call="fnox exec -- <cmd>",
            readable=TOTAL_SECRETS,
            enforced_by=Layer.NONE,
            note="Already native, and the human is entitled to all of it.",
        )
    return Decision(
        route=Route.DOTFILES_CLI,
        call=f"dotfiles-secrets {verb.value}",
        readable=0,
        enforced_by=Layer.NONE,
    )


def _agent(verb: Verb, design: Design) -> Decision:
    if verb in WRITE_VERBS:
        if design.agent_may_write:
            return Decision(
                route=Route.DOPPLER_CLI,
                call=f"dotfiles-secrets {verb.value} KEY --value <...>",
                readable=1,
                enforced_by=Layer.NONE,
                note="REJECTED: an agent that must not read a value cannot supply "
                "one either, so this verb can only ever be theatre.",
            )
        return Decision(
            route=Route.BLOCKED,
            call=f"-- none. Ask the human: 'run `dotfiles-secrets {verb.value} KEY`' --",
            readable=0,
            enforced_by=Layer.PLUGIN,
            note="DECIDED: origination is human-only, so there is no agent write "
            "path left to secure at all.",
        )

    if verb is Verb.EXEC:
        route = Route.FNOX_MCP_EXEC if design.exec_via_fnox_mcp else Route.DOTFILES_CLI
        if design.exec_command_allowlist:
            return Decision(
                route=route,
                call="dotfiles-secrets exec -- <cmd>   # vs command allow-list",
                readable=0,
                enforced_by=Layer.HOOK,
                note="REJECTED: you cannot enumerate what an agent legitimately "
                "runs, and the deny half fails open on every novel shape.",
            )
        if design.scoped_agent_profile:
            return Decision(
                route=route,
                call="dotfiles-secrets exec -P agent -- gh api user",
                readable=1,
                enforced_by=Layer.STRUCTURAL if design.structural_empty_env else Layer.DOCS,
                note="DECIDED: the agent CAN read what is in scope -- `sh -c` is "
                "always available to it -- so cap what is in scope. One command's "
                "secrets, not 49. Needs #441 (fnox Composable Profiles), blocked "
                "on #435.",
            )
        return Decision(
            route=route,
            call="dotfiles-secrets exec -- sh -c 'echo $EXA_API_KEY'",
            readable=TOTAL_SECRETS,
            enforced_by=Layer.NONE,
            note="Unscoped exec is a read primitive for the WHOLE store. This is "
            "the state the prototype was built to expose.",
        )

    if verb is Verb.LIST:
        return Decision(
            route=Route.DOTFILES_CLI,
            call="dotfiles-secrets list          # names only; -V is human-only",
            readable=0,
            enforced_by=Layer.PLUGIN,
            note="PROBED: `fnox list` is already names-only by default; -V/--values "
            "opts in. The leak is a flag, not the verb.",
        )

    return Decision(
        route=Route.DOTFILES_CLI,
        call="dotfiles-secrets status        # mode, opt-ins, drift vs doctor.toml",
        readable=0,
        enforced_by=Layer.HOOK if design.hook_backstop else Layer.DOCS,
        note="Carries the hook backstop: it is `status` that knows the mode has "
        'been wiped. Subsumes mise run doctor\'s fnox-baseline check -- the thing '
        "that caught the wipe. Reads config, never a value.",
    )


def matrix(design: Design) -> dict[tuple[Caller, Verb], Decision]:
    return {(c, v): decide(c, v, design) for c in Caller for v in Verb}


def blast_radius(design: Design) -> tuple[int, list[tuple[Caller, Verb]]]:
    """Worst-case number of secrets an AGENT can read, and where."""
    cells = [
        ((c, v), d)
        for (c, v), d in matrix(design).items()
        if c is not Caller.HUMAN
    ]
    worst = max(d.readable for _, d in cells)
    return worst, [k for k, d in cells if d.readable == worst and worst > 0]


def unverified_layers(design: Design) -> list[tuple[Caller, Layer]]:
    return sorted(
        {
            (c, d.enforced_by)
            for (c, _), d in matrix(design).items()
            if d.layer_is_real is None
        }
    )
