"""PROTOTYPE (throwaway) — TUI shell over `policy.py`. Not for production.

Run:  mise run proto-432

Flip the four design toggles and watch the (caller x verb) matrix move. The line
that matters is REFERENCE-ONLY at the bottom: it must stay GREEN. Press `g` to
see it go red, which is the whole point of the prototype.
"""

from __future__ import annotations

import sys
from dataclasses import replace

from policy import (
    Caller,
    Design,
    Verb,
    decide,
    invariant_breaches,
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
    "e": ("exec_via_fnox_mcp", "delegate exec to `fnox mcp`"),
    "g": ("get_secret_denied", "deny mcp__fnox__get_secret consumer-side"),
    "d": ("writes_via_doppler_cli", "writes go through the `doppler` CLI"),
    "s": ("keep_shell_eval", "human keeps the zsh eval propagation"),
    "a": ("exec_command_allowlist", "constrain WHICH commands may be exec'd"),
}


def render(design: Design) -> str:
    out: list[str] = []
    out.append(f"{BOLD}PROTOTYPE #432 — what shape is the secrets CLI?{OFF}")
    out.append(
        f"{DIM}consumers: Claude Code plugin + Codex plugin · "
        f"invariant: reference-only (agent never receives a value){OFF}"
    )
    out.append("")

    out.append(f"{BOLD}Design{OFF}")
    for key, (attr, label) in TOGGLES.items():
        on = getattr(design, attr)
        mark = f"{GREEN}ON {OFF}" if on else f"{DIM}off{OFF}"
        out.append(f"  [{BOLD}{key}{OFF}] {mark} {label}")
    out.append("")

    out.append(f"{BOLD}Route matrix{OFF}  {DIM}(verb x caller){OFF}")
    header = f"  {'verb':<8}" + "".join(f"{c.value:<16}" for c in Caller)
    out.append(f"{DIM}{header}{OFF}")
    for verb in Verb:
        row = f"  {BOLD}{verb.value:<8}{OFF}"
        for caller in Caller:
            d = decide(caller, verb, design)
            plain = "LEAKS" if d.leaks else "ok"
            colour = RED if d.leaks else GREEN
            row += f"{colour}{plain}{OFF}" + " " * (16 - len(plain))
        out.append(row)
    out.append("")

    out.append(f"{BOLD}Call boundary{OFF}  {DIM}(claude-code column, verbatim){OFF}")
    for verb in Verb:
        d = decide(Caller.CLAUDE, verb, design)
        colour = RED if d.leaks else CYAN
        out.append(f"  {BOLD}{verb.value:<8}{OFF}{colour}{d.call}{OFF}")
        out.append(f"           {DIM}route: {d.route.value}{OFF}")
        real = d.layer_is_real
        flag = {True: "", False: f" {RED}(LAYER DOES NOT EXIST){OFF}", None: f" {YELLOW}(UNVERIFIED){OFF}"}[real]
        out.append(f"           {DIM}stopped by: {d.enforced_by.value}{OFF}{flag}")
        if d.note:
            out.append(f"           {DIM}{_wrap(d.note)}{OFF}")
    out.append("")

    breaches = invariant_breaches(design)
    if breaches:
        out.append(f"{RED}{BOLD}REFERENCE-ONLY: BROKEN{OFF}")
        for caller, verb, d in breaches:
            out.append(f"  {RED}{caller.value} / {verb.value} -> {d.call}{OFF}")
    else:
        out.append(f"{GREEN}{BOLD}REFERENCE-ONLY: holds for every agent caller{OFF}")

    unver = unverified_layers(design)
    if unver:
        seen = {(c, d.enforced_by) for c, _, d in unver}
        for caller, layer in sorted(seen):
            out.append(
                f"{YELLOW}UNVERIFIED{OFF} {DIM}can {caller.value} even express "
                f"'{layer.value}'? Not found on `codex mcp add --help` — a bound, "
                f"not an answer.{OFF}"
            )

    out.append("")
    keys = "  ".join(f"[{BOLD}{k}{OFF}]" for k in TOGGLES)
    out.append(f"{DIM}toggle: {keys}   [{BOLD}q{OFF}{DIM}] quit{OFF}")
    return "\n".join(out)


def _wrap(text: str, width: int = 88) -> str:
    words, lines, cur = text.split(), [], ""
    for w in words:
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
    # `--toggle eg` pre-flips toggles before the first frame. Exists so the
    # FAIL direction can be armed non-interactively: `--once --toggle g`.
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
