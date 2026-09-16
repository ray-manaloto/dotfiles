# codex-review-fb93d8a — verbatim report (2026-09-16)

Brief: cold review by ref of `fb93d8a` (wrapper review-fix round) against `67a6cad`, restricted to the two implementer agent files, diff only. Lane: `fable-orchestrator:codex-reviewer` (GPT-5.6 Sol, read-only). Report file copied verbatim below; the architect's refutation pass follows it.

---

# Cold review — fb93d8a vs 67a6cad (`.claude/agents/codex-{sol,astra}-implementer.md`)

Repository: `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles`
Branch: `fix/codex-implementer-wrapper-and-6c-p1`
Command reviewed: `git diff 67a6cad..fb93d8a -- .claude/agents/codex-sol-implementer.md .claude/agents/codex-astra-implementer.md`
Scope: diff-only, cold (no intent framing supplied). Other files in commit `fb93d8a` (verbatim report transcripts) are out of scope and were not read.

Both files are confirmed mechanically identical modulo the `codex-lane-mirror` substitution (`codex-sol-` → `codex-astra-`, `gpt-5.6-sol` → `gpt-6-astra`, plus the GENERATED banner) — verified live: `uv run --project python dotfiles-setup codex-lane-mirror --check` → `codex-lane-mirror OK: 12 generated file(s) match their sol source`, rc=0. Every finding below therefore applies identically to both files at a two-line offset (astra is +2 lines vs sol throughout the diff, due to the GENERATED comment).

## Findings

### 1. [HIGH] New step-3 code depends on `$PROMPT` surviving across Bash calls; the (unchanged) "what to re-assign" instruction never says to carry it — the budget/timeout mechanism silently collapses

- `codex-sol-implementer.md:205` (mirror: `codex-astra-implementer.md:207`): `remaining=$(( TIMEOUT - ( $(date +%s) - $(stat -f %m "$PROMPT") ) ))` — first use of `$PROMPT` inside the step-3 wait loop. This is new in this commit; the pre-diff step 3 used only `$LOG` and `$OUT`.
- `codex-sol-implementer.md:155` (mirror: `codex-astra-implementer.md:157`) — untouched by this diff: *"Shell variables do not survive between your Bash calls, so re-assign `LANE_ID`, `OUT` and `LOG` from the printed literals at the top of every later call."* `PROMPT` is not in that list, and the diff did not add it.

Each step-3 slice is its own Bash tool call (the file itself: *"One slice per Bash call"*, `codex-sol-implementer.md:198`), and per the file's own stated rule shell state does not carry over — so on the very first step-3 slice, `$PROMPT` is unset unless the executing agent independently infers (beyond what the doc tells it to do) that it must also re-assign `PROMPT`, not just `LANE_ID`/`OUT`/`LOG`.

**Empirically verified the failure cascade** (macOS default bash 3.2.57, `/bin/bash`, matching the repo's host environment):

```
$ bash -c 'unset PROMPT; stat -f %m "$PROMPT"'
stat: : stat: No such file or directory        # exit=1

$ bash -c '
  unset PROMPT; TIMEOUT=1800
  remaining=$(( TIMEOUT - ( $(date +%s) - $(stat -f %m "$PROMPT") ) ))
  echo "remaining=$remaining"'
stat: : stat: No such file or directory
bash: line 3: TIMEOUT - ( 1789578042 -  ) : syntax error: operand expected (error token is ") ")
remaining=                                      # empty — assignment silently failed, no `set -e` to halt it
```

Running the **full published snippet** verbatim with `$PROMPT` unset (`$OUT`/`$LOG` set to real paths):

```
stat: : stat: No such file or directory
bash: line 5: TIMEOUT - ( 1789578053 -  ) : syntax error: operand expected (error token is ") ")
bash: line 6: [: : integer expression expected
still running at 17:00:54Z; s of budget remained before this slice
```

Trace through the consequences, all confirmed by the above:
1. `remaining` ends up empty (assignment aborted mid-arithmetic-error, and the script has no `set -e`, so execution continues).
2. `[ "$remaining" -le 0 ]` itself errors (`integer expression expected`) and returns non-zero, so the `&&` **never fires** — the `budget exhausted` signal-3 path can never trigger while this bug is live. Not "fires early," but permanently disabled.
3. `slice=$(( remaining < 540 ? remaining : 540 ))` silently succeeds because bash's arithmetic context coerces the empty/unset `remaining` to `0` — no error is printed for this line. `slice` becomes `0`.
4. `deadline=$((SECONDS+0))` equals the current `$SECONDS`, so the `while [ $SECONDS -lt $deadline ]` loop performs **zero iterations** — no `sleep 15`, no actual wait.
5. The snippet falls straight through to the final `grep`, which (if codex hasn't finished yet) immediately prints `still running at <time>; s of budget remained before this slice` — note the literal empty interpolation (`; s of` with no number), which is itself a visible tell that `remaining` was blank.

Net effect: the entire point of this commit's step-3 rewrite (precise elapsed-time budget tracking, replacing the old fixed-count-of-540s-slices approach) does not work unless the calling agent independently carries `$PROMPT` forward despite the adjacent, unedited instruction telling it to re-assign only three of the four variables the snippet now needs. Symptoms in the failure mode: the wait collapses to a busy-poll (each "slice" call returns near-instantly instead of waiting up to 540s), and the `budget exhausted` / `STATUS: timeout` termination path becomes permanently unreachable, contradicting the file's own hard limit *"Never end your turn while the lane may be alive"* (nothing would ever force a reap on a runaway lane through this mechanism).

Fix shape: add `PROMPT` to the `codex-sol-implementer.md:155` re-assign sentence (and, since it's the mirror source, the astra copy follows automatically via `codex-lane-mirror`).

### 2. [MEDIUM] The `budget exhausted` fast-path never checks `$LOG` for a just-written `rc=` before declaring timeout — a real completion in the hand-off window can be reported as `STATUS: timeout` and its `$OUT` discarded

`codex-sol-implementer.md:206` (mirror: `codex-astra-implementer.md:208`):

```bash
[ "$remaining" -le 0 ] && { echo "budget exhausted"; exit 0; }
```

This exits immediately on a `remaining <= 0` computation, printing only the literal string `budget exhausted` — no log tail, no `rc=` check, nothing. Contrast with the file's own stated priority a few paragraphs earlier (`codex-sol-implementer.md:174`, unchanged by this diff): *"The `rc=` line in `$LOG` is the ONLY completion signal you trust."* If codex writes its final `rc=` line in the gap between the previous slice's last poll and this slice's invocation (a real, non-zero window — tool-call round-trip latency, or simply the agent's own "thinking" time before issuing the next Bash call), this fast path reports `STATUS: timeout` and routes straight to the reap commands, even though `$OUT` on disk already holds a real, completed result. The old (pre-diff) design didn't have this exact gap for the default `TIMEOUT=1800`: it always ran a full, unconditional `deadline=$((SECONDS+540))` wait-and-check per slice regardless of a remaining-budget computation, and `ceil(1800/540)=4` slices totalling 2160s (360s past nominal) meant the last slice's own post-loop check always re-verified the log near/at the true boundary rather than skipping it.

Note this can only manifest once finding 1 is fixed — while finding 1 is live, `[ "$remaining" -le 0 ]` always errors rather than evaluating true, so this fast-path is unreachable today. It becomes a live risk as soon as `$PROMPT` is correctly threaded through.

Fix shape: `[ "$remaining" -le 0 ] && { grep '^rc=' "$LOG" || { echo "budget exhausted"; exit 0; }; }` (or equivalent) so a just-arrived `rc=` still wins over the timeout classification.

### 3. [LOW] `stat -f %m` is BSD/macOS-specific; this is the first `stat` call step 3 has ever had

`codex-sol-implementer.md:205` / `codex-astra-implementer.md:207`. On GNU/Linux `coreutils` `stat`, `-f` means "display filesystem status" (not "use this format string") and `%m` means mount point in that mode — a different, non-numeric result, not a mtime. This is consistent with the rest of the file's implicit host-only execution model (it already references `~/.codex/config.toml`, "this host," "this machine" elsewhere, unchanged by this diff), so it is very likely fine in practice — but it is a new dependency this commit introduces (the pre-diff step 3 called no `stat` at all), so if this agent's Bash tool is ever invoked from inside the Linux devcontainer rather than the macOS host, this line breaks silently in a different way than finding 1. Flagging for completeness, not blocking.

### 4. [INFO — verified correct, not a defect] "Lane history" rewrite fixes a real dead link in the astra file; the sol file trades away filename precision for it

`codex-sol-implementer.md:38-42` / `codex-astra-implementer.md:40-44`. Before this diff, the astra file (via the mechanical `codex-sol-` → `codex-astra-` mirror substitution) cited `docs/research/kb/reports/agents/codex-astra-implementer-spawn-reconciliation-2026-09-16.md` — **confirmed this file does not exist** (`git ls-files` / `ls` of that directory show only a `codex-sol-implementer-spawn-reconciliation-2026-09-16.md`, no astra counterpart). The new generic wording ("the implementer lane's spawn-reconciliation report of 2026-09-16 under `docs/research/kb/reports/agents/`... the incident is the sol lane's, and the astra twin inherits the lesson, not a report of its own") is accurate and verified:
- `docs/research/kb/reports/agents/codex-sol-implementer-spawn-reconciliation-2026-09-16.md` exists and does document the described haiku-wrapper incident (grepped: references the haiku wrapper, cites `feedback_haiku_lane_wrapper_abandons_codex_and_self_implements`).
- `docs/research/kb/reports/agents/briefs/spawn-reconciliation-2026-09-16/` exists with 8 files (README.md, agent-prompts.md, codex-lane-preambles.md, live-settlement-request.json, live-settlement-review-spec.md, spec-v1-as-first-verified.md, spec-v5.md, spec-v7-respec.md, spec-v8-addendum.md).

Cost of the fix: the sol file's own paragraph is necessarily shared verbatim with astra (mirror-substitution constraint — confirmed via `codex_lane_mirror.py`'s `render_md`, which only replaces the literal strings `codex-sol-`/`gpt-5.6-sol`), so sol also lost its previously-exact filename citation in favor of the generic directory-level pointer. Not a defect — the old sol citation was correct but the shared-text constraint means keeping it exact for sol would have required either duplicating logic outside the mirror's narrow substitution rule or leaving astra with a dead link. The trade made here is reasonable and was verified consistent (`codex-lane-mirror --check` passes, rc=0).

### Also checked, no issue found

- The "mutate realistically" bullet reframing (`codex-sol-implementer.md:266-269` / `codex-astra-implementer.md:268-271`) changes address from imperative-to-the-supervisor ("Mutate realistically... Assert the mutation landed") to descriptive-of-codex ("Codex mutates realistically... you check that its report says the mutation landed"). This is a genuine fix, not a new defect: the old wording told a file whose entire premise is "you never edit / you never write the code yourself" (`codex-sol-implementer.md:15-16`, `23-28`) to itself perform mutation testing — a direct self-contradiction the new wording removes.
- The `complete` vs `dissent` clarification (`codex-sol-implementer.md:286-289` / `codex-astra-implementer.md:288-291`, "read `$OUT` for a refusal FIRST...") is consistent with the pre-existing "Refusing is a success, not a failure" section and does not introduce new inconsistency.
- The relaunch-on-signal-2 rewrite (`codex-sol-implementer.md:216-220` / `codex-astra-implementer.md:218-222`, `LANE_ID="${LANE_ID}-r1"`) fixes a real latent bug in the old text: the old instruction said "relaunch ONCE with the identical spec" without changing `LANE_ID`, which would collide with the `set -C` atomic claim on `$OUT` from the first (dead) attempt (`( set -C; : > "$OUT" ) ... || { echo "refusing: $OUT already claimed"; exit 1; }`, unchanged, line ~143). The `-r1` suffix avoids that collision. Good catch.
- Ternary arithmetic (`remaining < 540 ? remaining : 540`) and the general bash syntax are valid on macOS's default `/bin/bash` (GNU bash 3.2.57) — verified live, not a portability issue.

## Repos/paths touched during this review

- Local files only, in-repo: `.claude/agents/codex-sol-implementer.md`, `.claude/agents/codex-astra-implementer.md`, `python/src/dotfiles_setup/codex_lane_mirror.py`, `docs/research/kb/reports/agents/codex-sol-implementer-spawn-reconciliation-2026-09-16.md` (grep only), `docs/research/kb/reports/agents/briefs/spawn-reconciliation-2026-09-16/` (listing only). No external repos consulted.

---

## Architect refutation pass (2026-09-16)

| # | Sev | Verdict | Disposition |
|---|---|---|---|
| 1 | HIGH | **CONFIRMED** | `:155` re-assign list omitted `PROMPT` while the new slice snippet reads `stat -f %m "$PROMPT"`; with `$PROMPT` unset the arithmetic errors, `remaining` is empty, the budget check can never fire and the loop runs zero iterations. Fixed: `PROMPT` added to the re-assign sentence. |
| 2 | MED | **CONFIRMED** | the `budget exhausted` fast path exited before consulting `$LOG`; a run finishing between slices would be reported `timeout`. Fixed: the slice reads `rc=` FIRST, then the budget. |
| 3 | LOW | **CONFIRMED** | `stat -f %m` is BSD/macOS syntax. Fixed: inline comment naming the GNU form. |

This was the wrapper's SECOND cold round (first: `49d7af6`). Per the two-round
bound these fixes ship without a third cold read; the residual is stated in
the PR body.
