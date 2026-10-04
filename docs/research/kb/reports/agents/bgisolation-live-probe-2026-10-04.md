# Live probe: does `claude --bg --settings` honour `worktree.bgIsolation: "none"`? (2026-10-04)

Closes cold review R12 / spec P7 ("UNVERIFIED: live launch"). Claude Code v2.1.289, launched from the
dotfiles MAIN checkout (`/Users/rmanaloto/dev/github/ray-manaloto/dotfiles`), coordinator
`dotfiles-20261004T104413.238236000-05.coordinator`.

| Arm | Launch | Prompt | Result |
|---|---|---|---|
| treatment | `claude --bg -n probe-bgiso-none-k7q2 --settings '{"worktree":{"bgIsolation":"none"}}' "<prompt>"` (job 76020d9f) | Use the Write tool to create `.agent/state/bgiso-probe-none-k7q2.txt` in the main checkout; do not call EnterWorktree | **Written** (file present, 2 bytes, 11:37 CDT). Session: "The Write wasn't refused." |
| control | same, without `--settings` (job 6324ef28) | same, file `bgiso-probe-default-k7q2.txt` | **Refused**; file absent. Refusal: "This background session hasn't isolated its changes yet. Call EnterWorktree … (or set `"worktree": {"bgIsolation": "none"}` in .claude/settings.json.)" — fired even though `.agent/` is git-ignored. |

The probe discriminates: the only difference between arms is the `--settings` JSON, and the outcomes differ.
The successor argv in `coordinator_handoff.py` passes exactly this nested key (plus
`crossSessionInbound`) through `--settings`, so the PR's launch mechanism is live-verified.

Third arm, the successor's EXACT JSON: `claude --bg -n probe-bgiso-combined-m3x9 --settings
'{"crossSessionInbound":"accept","worktree":{"bgIsolation":"none"}}' "<same prompt>"` (job 55a994af)
→ **Written** (`bgiso-probe-combined-m3x9.txt` appeared; `mise run bounded-wait --file` rc 0).
All probe sessions stopped and probe files deleted afterwards.

## GitHub repos touched

_None._
