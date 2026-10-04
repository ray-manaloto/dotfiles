# Premise report: credit-fallback spec rev 2

This is the premise-verifier subagent's report for coordinator f9467b, written on 2026-10-03 and saved here when it arrived. The coordinator applied fixes A, B and C, plus the D–J residuals, as rev 2.1, an addendum at the end of the spec.

---

PREMISE REPORT: credit-fallback spec rev 2 (`/Users/rmanaloto/.claude/jobs/1854b55f/tmp/spec-credit-fallback.md`)

**Verdict: CORRECT-SPEC-FIRST.** All four rev-1 blockers are closed. Three new problems must be fixed before dispatch:
- **A:** a webclaw mirror would never count as mirrored.
- **B:** the replacement text for `AGENTS.md:9-10` leaves a broken sentence.
- **C:** the "no URL anywhere" rule contradicts the real fixtures.

ROWS: 49 checked: 40 CONFIRMED (1 provenance corrected), 0 REFUTED, 0 UNVERIFIABLE, 9 ASSUMED (2 checkable).

## Rev-1 blockers: are they closed?

| Blocker | Closed? | What I read |
|---|---|---|
| **P18 token units** | Yes | `~/.codex/hooks.json:7-9`, `:19-20` match. KB `sources/agent-harness-docs/docs/codex/hooks.md:453` says "approximate token threshold" and `:464` says "default `2500`-token threshold". §3.6 is reworded to match. |
| **Pin-parity claim** | Yes | The §5.2 claim is dropped and §4.2 forbids editing `pin-parity.toml`. P49 checks out: `pin_parity.py:94-106` reads only `project_root / path`, and `pin-parity.toml` has headers only at `:43,46,61,72,84,123`, none for webclaw. The manual cross-check targets also check out: KB `mise.toml:123` and `~/.config/mise/config.toml:226` both say `0.6.23`. |
| **402 rc** | Yes | `fc402/rc.txt:1-2` says "search rc=1" and "scrape rc=1", and `:3` gives the two capture commands. Both `.out` files are empty and both `.err` files contain `Insufficient credits`. The rc==0 `success:false` defensive branch is needed. Today a `{"success":false}` scrape payload goes through `_scrape_payload` (`:1881-1890`), yields reason "" and markdown "", and reaches "rc=0, 0 bytes" at `:1862` without the classifier ever seeing it. |
| **Planner provisional rows** | Yes, with residual G | `--fanout-manifest` is `action="append"` (`research_fanout.py:1238`), so one probe can take several manifests. `common` is at `:734` and reaches the result through `...common` at `:842`. `:322` is the retrospect `facts` map, as the spec says. |

## Premise rows

| Row | Verdict | Evidence |
|---|---|---|
| P1-P17, P19, P21, P29, P30, P32-P38 | CONFIRMED | Unchanged from rev 1. I re-read the anchors cited in the new text: `research_fanout.py:93-100`, `:199-203`, `:527-565`, `:724-743`, `:801-827`, `:1080-1159`, `:1296-1301`, `:1356-1533`, `:1758-1890`, `:2133-2191`; gate `:14-19`, `:75-120`; JS `:129`, `:179-222`, `:458`, `:488-501`, `:580-620`, `:726`, `:734`, `:834-842`. All match. |
| P18 | CONFIRMED | As in the blocker table. The hooks run the clone's own `.venv` python (`hooks.json:7`). |
| P20, P23, P24, P39 | ASSUMED (accepted on record) | KB `docs_mirror.py:219-243` matches P20's description. |
| P22 | CONFIRMED | KB `mise.toml:123`; user-global `config.toml:226`. Dotfiles `mise.toml:117-128` has the firecrawl pin and no webclaw. |
| P25 | CONFIRMED | Fixtures `search.err:1`, `scrape.err:1`; RATIFICATION section. |
| P26 | CONFIRMED | `search.out` and `scrape.out` are both empty. |
| P27 | CONFIRMED | Carried over from rev 1. I did not re-read the credential file, to avoid touching it again. |
| P28 | CONFIRMED (verified half) / ASSUMED (assumed half) | This checkout's `doctor.toml` has `:91` SCRAPECREATORS and `:92` SKILLSMP, with no SERP key (control: FIRECRAWL at `:54`). The worktree `.claude/worktrees/serp-api-key-doctor/doctor.toml:92-93` does carry SERPER_API_KEY and SERP_API_KEY. This lane has no git access, so I could not check commit 1ba74fab or whether it is merged. |
| P31 | CONFIRMED | `~/.codex/AGENTS.md:16-17` "A failed arm is a recorded blocker". O2's `:11` "This profile injects Exa and Firecrawl" also checks out. |
| P40 | CONFIRMED | KB `hooks.md:185-187`: Codex "saves the full text to disk and sends a shorter preview". |
| P41 | CONFIRMED | Still holds. The `sdlc-webclaw-20261003` worktree has 0 webclaw hits outside `docs/`; the same grep for `firecrawl` gets 5+ hits (control). |
| P42 | CONFIRMED | Byte-identical to `search.err:1`, apart from the spec's `…` abbreviation. |
| P43 | CONFIRMED (provenance corrected) | The text matches `scrape.err:1`, which has no numeric 402. The row's statement "There is no rc file in `fc402/`" is stale: `rc.txt:1-2` records rc=1 for both commands. Re-cite P43 to `rc.txt`. |
| P44 | ASSUMED | firecrawl-developer's key is optional (`:783-787`). Low risk. |
| P45 | ASSUMED (checkable) | The capture argv (`rc.txt:3`) does differ from the fan-out argv (`:808-820`, `:1836-1844`), as stated. Whether the extra flags change the error output cannot be settled now. |
| P46 | CONFIRMED | JS `:615-616` lists only `empty_unverified` or `error`. |
| P47 | CONFIRMED | JS `:580-585`. |
| P48 | CONFIRMED | `test_research_fanout_probe.py:446-449` uses substring matches. The README header string appears only in `research_fanout.py:1952`; no test pins it. |
| P49 | CONFIRMED | As in the blocker table. |

## MISSING

### Must fix before dispatch

**A. The `rc` of a webclaw mirror row is never specified.**
- `_mirror_probe:1862` writes the reason `rc=<n>, <size> bytes` whenever `rc != 0`.
- Both the JS mapper (`research-sweep-run.js:497`) and `mirrored()` (`:499`) require `m.rc === 0`.
- If the row keeps firecrawl's rc=1, a successful webclaw mirror becomes a MIRROR GAP. That breaks §3.7 ("a provisional mirror is still a mirror") and test 10 (`reason: ""`).
- Fix: state that when webclaw succeeds, `rc` is webclaw's rc (0), and say what the README rc cell shows.

**B. The §4.3 replacement for `AGENTS.md:9-10` breaks a sentence.**
- `:10` reads "keys from that profile. Fnox resolves its Doppler token internally with", and that sentence ends at `:11` with "`env = false`."
- Replacing only `:9-10` leaves the fragment "`env = false`." at `:11`.
- Fix: replace `:9-11` and keep the Doppler sentence.

**C. The rule "no URL in any reason, exception message, raw file or stdout" (§3.3) contradicts the fixtures.**
- Both `.err` fixtures contain `https://firecrawl.dev/pricing`.
- The CLI envelope's `stderr_redacted` is a raw file, and `_subprocess_error` already puts this text into reasons today.
- A literal sentinel test would therefore fail, or the lane would strip URLs and lose evidence.
- Fix: scope the rule to the request URL and to any key-bearing string.

### Non-blocking residuals (accept on record)

- **D. Nothing carries the CLI envelope data.**
  - `_Attempt` (`:199-203`) gains only `http_status`.
  - `_run_json` (`:527-541`) returns only the truncated error string, with no rc and no untruncated redacted stderr.
  - The lane must add both. That is easy to discover, and the file is on the allowlist.
- **E. P43 needs a new citation:** `fc402/rc.txt:1-3`. Item 15's test-constant comment can cite `rc.txt:3` for the two capture commands.
- **F. The deep-read paths still call a bare `firecrawl scrape` with no fallback:** `research-sweep/SKILL.md:156-158` and the workflow `FETCH` at `:175` and `:645`. While Firecrawl stays un-topped-up, reader fetches will hit the 402. This is not in §4.6; name it there.
- **G. Early exits never get the `provisional` status.**
  - `withStatuses` (`:364-366`) is used by the plan-null (`:584`), no-manifests (`:586`), triage-null (`:624`) and synth-null (`:735`) exits.
  - Every early exit already has a degraded status, so nothing passes silently.
  - Name it as a residual.
- **H. The README `route` default can mislabel rows.** "No `route` field renders as `firecrawl`" also labels stale or unreadable rows (`:1914-1923`, `:1938`) as firecrawl. A blank cell is the honest value.
- **I. Test 15 has an unverified dependency.**
  - A copied `codex-research-gate.py` computes `REPO_ROOT/python/src` from its new location, and that path does not exist.
  - Its import (`:17-19`) then relies on the venv-installed `dotfiles_setup` (`pyproject.toml:47` has a build-system).
  - The lane must confirm this, or mirror `python/src` beside the copy.
- **J. The new planner node will break existing workflow tests.**
  - It needs a `ROUTE` key (`ROUTE.mirrorIndex = {model: 'haiku'}`, `:203`) and a `_SWEEP_ROUTING` row (`test_workflows_js.py:648`).
  - Existing mocks that do not handle the new label will add a `fanoutGaps` entry.
  - The test file is on the allowlist, and item 18 partly covers this.

Accepted on record, as already ratified: P20, P23, P24, P39, P44, P45.

VERDICT: CORRECT-SPEC-FIRST. A (webclaw-success `rc`), B (`AGENTS.md :9-11`) and C (URL scope) are three one-line spec edits, and D-J each need one line in the residual list. After those edits the spec is ready to dispatch. No further verification round is needed unless new premise rows are added.

Files read:
- `fc402/{search,scrape}.{out,err}`, `rc.txt`.
- Dotfiles:
  - `python/src/dotfiles_setup/{research_fanout.py,pin_parity.py,AGENTS.md}`, `python/pyproject.toml`
  - `pin-parity.toml`, `doctor.toml`, `mise.toml`, `scripts/codex-research-gate.py`
  - `tests/{test_research_fanout.py,test_research_fanout_probe.py,test_codex_research_gate.py,test_workflows_js.py}` (grep)
  - `.claude/workflows/research-sweep-run.js`, `.claude/skills/{research-sweep,codex-team-research}/SKILL.md`
- Worktrees: `serp-api-key-doctor/doctor.toml` and `sdlc-webclaw-20261003` (grep).
- KB: `python/src/kb_setup/docs_mirror.py`, `mise.toml`, `sources/agent-harness-docs/docs/codex/hooks.md`.
- User-global: `~/.codex/hooks.json` (key grep), `~/.codex/AGENTS.md`, `~/.config/mise/config.toml` (grep).

No credential file was read and no secret value was printed.

## GitHub repos touched

_None._ (local files only)
