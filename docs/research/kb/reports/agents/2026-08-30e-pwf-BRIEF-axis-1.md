## Your axis — HOOKS AND GUARD-CHAIN INTERACTION

The single highest-risk surface. This repo's PreToolUse guard DENIES tool calls;
a plugin hook that fires alongside it can weaken, duplicate, or deadlock it.

Answer, each cited:

1. **What hooks does the plugin actually register for Claude Code?** Read
   `hooks/hooks.json`, `claude-hook.sh`, and any hook wiring in
   `.claude-plugin/plugin.json` or the `.claude/` tree. For EACH hook: which
   event, which matcher, what command, and what it does on stdout/exit code.
2. **Does any of them return a permission decision** (deny/allow) or a non-zero
   exit that blocks a tool call? A `Stop` gate is named `gate-stop.sh` — read it
   and say exactly when it blocks.
3. **How would they compose with this repo's existing hooks?** The repo already
   wires PreToolUse (deny-capable), SessionStart, and SessionEnd. State whether
   the plugin's hooks ADD to those or could SHADOW them, and whether hook
   ordering is defined or undefined between a plugin and project settings.
4. **Can any plugin hook make the repo's guard fail open?** The guard already
   has a recorded fail-open incident (a non-zero non-2 PreToolUse exit is a
   non-blocking error that lets the call proceed). Say whether the plugin's
   hooks can produce that condition.
5. **What does `inject-plan.sh` inject, into what, and when?** It sounds like
   context injection on every turn — quantify the token cost per invocation if
   the file lets you.

Write incrementally to:
/private/tmp/claude-501/-Users-rmanaloto-dev-github-ray-manaloto-dotfiles/84f08a9b-5231-4071-8759-b2d32945c99e/scratchpad/pwf-A-hooks.md
