# /code-review medium — item 2 graphify nudge `3c727496` (2026-09-28)

Verbatim fork report. Coordinator disposition: both CONFIRMED against graphify 0.9.65 `graphify/cli.py:18-66` (`_READ_NUDGE_STALE`, `_READ_DENY` with `permissionDecision`, no `additionalContext`). Fixed in the follow-up commit: `_general_nudge` dedups only the two `MANDATORY:` payloads, keyed per session+agent; the stale nudge and any `permissionDecision` payload always pass through (tests `test_hook_guard_main_never_dedups_stale_or_deny`, incl. a deny that also carries a MANDATORY context so the exclusion itself is armed).

---

I found two real issues in this diff; both come from how the new once-per-session dedup behaves. Neither shows up in the tests.

**Findings:**

1. `python/src/dotfiles_setup/graphify.py:931` (medium): the dedup key is only `graphify-{kind}-{session_id}` (plus agent). It never looks at what graphify actually printed, so the file-specific stale-for-target nudge and the general graph nudge use up the same single slot.
   - **Scenario:** an agent Reads `a.py` and gets the general `_GRAPH_NUDGE`. It then edits `b.py`, whose mtime is now newer than `graph.json`, and Reads it. graphify prints `_READ_NUDGE_STALE`, which says the graph may be stale for this file and to run `graphify update`. The marker already exists, so that output is dropped.
   - **Reverse case:** if the first `read` of the session is a stale-for-target read, the stale message is the only nudge the session ever gets, and the general `graphify-query`/`graphify-health` sentence never appears.
   - **Effect:** the only notice that the graph is stale for a file is lost whenever it is not the first read-kind event.
   - **Fix:** include the payload variant in the key, or dedup only the replaced `MANDATORY:` payload.

2. `python/src/dotfiles_setup/graphify.py:931` (low, latent): the dedup also swallows graphify's strict-mode `permissionDecision: "deny"` payload.
   - **Scenario:** strict mode is turned on through `GRAPHIFY_HOOK_STRICT=1` in the settings env, which the `scripts/graphify-hook-guard.sh` header documents as a supported switch. The session does a Glob or a stale Read first, and that soft nudge sets the `read` marker. Later, the first qualifying Read makes graphify atomically claim its once-per-session block (`_mark_session_denied`) and print `_READ_DENY`.
   - **Effect:** `hook_guard_main` sees the existing marker and returns 0 with no output. The Read goes through and the one-time block is used up with nothing delivered, so strict mode is silently disabled.
   - **Fix:** never suppress output that carries a `permissionDecision`.

No other correctness issues turned up:
- Forwarding stdin via `input=raw` preserves the payload graphify reads from `sys.stdin.buffer`.
- The marker is written only when there is output.
- A missing `session_id` fails toward emitting the nudge.

I couldn't load a ReportFindings tool in this session, so the two findings above are the whole report and the caller will need to persist them. I made no file writes.

## GitHub repos touched

_None._
