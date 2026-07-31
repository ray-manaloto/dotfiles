"""PROTOTYPE (throwaway) — TUI shell over `policy.py`. Not for production.

Run:  mise run proto-432

The defaults are the SETTLED shape (#432). Every toggle moves you to an option
that was considered and rejected — flip one and read why in the notes. The line
that matters is BLAST RADIUS at the bottom: how many secrets an agent can read.

Non-interactive:  mise run proto-432 --once [--toggle <keys>]
"""

from __future__ import annotations

import sys
from dataclasses import replace

from policy import (
    TOTAL_SECRETS,
    Caller,
    Design,
    Verb,
    blast_radius,
    decide,
    unverified_layers,
)

BOLD = "\x1b[1m"
DIM = "\x1b[2m"
RED = "\x1b[31m"
GREEN = "\x1b[32m"
YELLOW = "\x1b[33m"
CYAN = "\x1b[36m"
OFF = "\x1b[0m"

TOGGLES = {
    "w": ("agent_may_write", "agent may write secrets"),
    "p": ("scoped_agent_profile", "scope exec to an fnox agent profile"),
    "a": ("exec_command_allowlist", "allow-list WHICH commands may exec"),
    "n": ("structural_empty_env", 'structural: env="exec", nothing in scope'),
    "b": ("hook_backstop", "hook backstop when the mode is wiped"),
    "m": ("exec_via_fnox_mcp", "route exec through `fnox mcp` not the CLI"),
    "s": ("keep_shell_eval", "human keeps the zsh eval propagation"),
}

DECIDED = Design()


def _tint(readable: int) -> str:
    if readable == 0:
        return GREEN
    return RED if readable > 1 else YELLOW


def render(design: Design) -> str:
    out: list[str] = []
    out.append(f"{BOLD}PROTOTYPE #432 — what shape is the secrets CLI?{OFF}")
    out.append(
        f"{DIM}consumers: Claude Code plugin + Codex plugin · cells show how many "
        f"secrets that caller can READ at that call{OFF}"
    )
    out.append("")

    out.append(f"{BOLD}Design{OFF}   {DIM}(defaults = the settled shape){OFF}")
    for key, (attr, label) in TOGGLES.items():
        on = getattr(design, attr)
        decided = on == getattr(DECIDED, attr)
        mark = f"{GREEN}ON {OFF}" if on else f"{DIM}off{OFF}"
        tail = "" if decided else f"  {YELLOW}<- rejected option{OFF}"
        out.append(f"  [{BOLD}{key}{OFF}] {mark} {label}{tail}")
    out.append("")

    out.append(f"{BOLD}Readable-secret count{OFF}  {DIM}(verb x caller){OFF}")
    out.append(f"{DIM}  {'verb':<8}" + "".join(f"{c.value:<16}" for c in Caller) + OFF)
    for verb in Verb:
        row = f"  {BOLD}{verb.value:<8}{OFF}"
        for caller in Caller:
            d = decide(caller, verb, design)
            plain = "none" if d.readable == 0 else str(d.readable)
            row += f"{_tint(d.readable)}{plain}{OFF}" + " " * (16 - len(plain))
        out.append(row)
    out.append("")

    out.append(f"{BOLD}Call boundary{OFF}  {DIM}(claude-code column, verbatim){OFF}")
    for verb in Verb:
        d = decide(Caller.CLAUDE, verb, design)
        out.append(f"  {BOLD}{verb.value:<8}{OFF}{_tint(d.readable)}{d.call}{OFF}")
        out.append(f"           {DIM}route: {d.route.value}{OFF}")
        flag = {
            True: "",
            False: f" {RED}(LAYER DOES NOT EXIST){OFF}",
            None: f" {YELLOW}(UNVERIFIED){OFF}",
        }[d.layer_is_real]
        out.append(f"           {DIM}held by: {d.enforced_by.value}{OFF}{flag}")
        if d.note:
            out.append(f"           {DIM}{_wrap(d.note)}{OFF}")
    out.append("")

    worst, where = blast_radius(design)
    colour = _tint(worst)
    label = "none" if worst == 0 else f"{worst} of {TOTAL_SECRETS}"
    out.append(f"{colour}{BOLD}AGENT BLAST RADIUS: {label}{OFF}")
    for caller, verb in where:
        out.append(f"  {colour}via {caller.value} / {verb.value}{OFF}")
    if worst <= 1:
        out.append(
            f"{DIM}  reference-only was never achievable — `sh -c` is always "
            f"available to a caller that picks the command. Capping scope is.{OFF}"
        )

    for caller, layer in unverified_layers(design):
        out.append(
            f"{YELLOW}UNVERIFIED{OFF} {DIM}can {caller.value} even express "
            f"'{layer.value}'? Not on `codex mcp add --help` — a bound, not an "
            f"answer.{OFF}"
        )

    out.append("")
    keys = "  ".join(f"[{BOLD}{k}{OFF}]" for k in TOGGLES)
    out.append(f"{DIM}toggle: {keys}   [{BOLD}q{OFF}{DIM}] quit{OFF}")
    return "\n".join(out)


def _wrap(text: str, width: int = 88) -> str:
    lines, cur = [], ""
    for w in text.split():
        if len(cur) + len(w) + 1 > width:
            lines.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    lines.append(cur)
    return "\n           ".join(lines)


def main() -> int:
    design = Design()
    once = "--once" in sys.argv
    # `--toggle pa` pre-flips toggles before the first frame, so every arm can
    # be armed non-interactively.
    if "--toggle" in sys.argv:
        for key in sys.argv[sys.argv.index("--toggle") + 1]:
            if key in TOGGLES:
                attr = TOGGLES[key][0]
                design = replace(design, **{attr: not getattr(design, attr)})
    while True:
        print("\x1b[2J\x1b[H" + render(design))
        if once:
            return 0
        try:
            key = input("> ").strip().lower()
        except EOFError:
            return 0
        if key == "q":
            return 0
        if key in TOGGLES:
            attr = TOGGLES[key][0]
            design = replace(design, **{attr: not getattr(design, attr)})


if __name__ == "__main__":
    raise SystemExit(main())
