# SDLC roster recovery and team consistency repair — 2026-10-05

This report records the narrow repair in `fix/sdlc-team-commit-mode` as work
proceeded. The ratified specification is the local
`.agent/plans/sdlc-roster-repair-spec.md`. Commit ownership is the caller;
implementation changes remain unstaged. The pre-existing untracked
`sdlc-team-commit-mode-2026-10-05.md` remains untracked and was not written
by the dispatcher or specialists. No initial hash was recorded, so preservation
is an ownership/action record rather than measured before/after byte equality.

Final scoped implementation result: 131 tests passed (exit 0); Ruff,
format-check, ty, and diff checks exited 0. Three real source mutations each
produced green 0 / red 1 / restored green 0. All five direct specialist
results are complete. Changes are unstaged and uncommitted. Full gates,
installed schema currency/native loading, and fresh actual five-role CLI
review, implementation, hook-replacement, and control rehearsals were not run.
The strict-five research retry passes PROVISIONAL after credit fallback.

## Observations and scope

The motivating historical run emitted a substantive partial-failure final, then
a research receipt replaced the captured output. Root inspection found the
source final at one-based native record ordinal 528, the receipt final at 536,
and `task_complete` at 539. Canonical turn metadata uses
`internal_chat_message_metadata_passthrough.turn_id`. These historical reads
explain the repair; they are not a fresh CLI rehearsal or delivery proof.

The root reported `mise run graphify-health` exit 3: the worktree graph is
missing (`graphify-out/graph.json`, runtime 0.9.76). Source fallback is in use;
no graph rebuild was requested or performed. Configuration inspection found
parallel-only routing, extra agents/retries, unconditional full gates, and a
duplicated `tests/ tests/` arguments. The installed `codex --version` exited 0 and
reported 0.160.1. These observations were supplied by the root dispatcher;
specialist command evidence is recorded below.

Documentation inspection confirmed the skill's generated prompt description
already says `COMMIT: caller`, while its seven-part contract calls `lane` the
default. The opening six-agent description also leaves the root/direct-child
topology implicit. The canonical skill now states one root dispatcher and five
direct specialists, caller commit ownership, mode-aware checks, and the exact
closing roster. It also bounds the architect fallback chain so it cannot
authorize replacement children within the team. The documentation specialist
owns only the canonical skill, its generated mirror, and this report.

The public `skills_mirror.render(source_text, skill)` interface generated only
`.agents/skills/codex-sdlc-team/SKILL.md`; the generator's bulk writer was not
used because it traverses all skills and reference files. The scoped generation
command `uv run --project python python` with that interface exited 0. The
generated sibling skill links use `.agents/skills/`, while `.claude/rules/`
citations remain the real shared paths.

## Validation and limitations

Scoped mirror parity through `skills_mirror.render` exited 0; an in-memory
stale-commit-default control was detected. This is a documentation check, not
the runtime recovery mutation test. Scoped `git diff --check` exited 0.

The initial direct-file agnix invocation across the two skills and report
exited 1: `Agent file must have YAML frontmatter` for the report path. The
repository's existing `.agnix.toml` explicitly excludes `docs/research/kb/**`
because an `agents/` report directory is misclassified as agent definitions;
the direct-file invocation exposed that classification. No frontmatter or new
suppression was added to the prose report. Corrected scoped skill validation
`agnix .claude/skills/codex-sdlc-team/SKILL.md
.agents/skills/codex-sdlc-team/SKILL.md --strict` exited 0 with zero errors and
zero warnings (one informational client-specific `user-invocable` field).
The report's first `mise exec -- markdownlint-cli2` check exited 1 on MD013
line length; that line was wrapped and its scoped recheck exited 0.

Configuration specialist results supplied by the root: `mise run
codex-agent-validate` exited 0 (six definitions valid), `mise exec -- taplo check`
on those six files exited 0, and their scoped `git diff --check` exited 0.
`mise run codex-schema-check` exited 1: `Schema not found at
.../schemas/codex_app_server_protocol.schemas.json`. No schema was generated
outside the allowlist. Installed schema currency and native loading proof
remain unverified; these scoped checks do not establish rehearsal proof.

The image specialist inspected the revised image role definition (lines
20–37 and 49–51): it preserves direct-child/no-delegation topology, caller
commits, review mode without writes/gates, authorized scoped implementation
checks, and coordinator ownership of full/container gates. Image requirements
remain stated, and inspection is expressly not R1/R2/R3 or persistence proof.
No image consumer defect requiring respec was identified. The image specialist
made no source edits and ran no image gate, container lifecycle/build, or
current-pin audit. Its combined source query exited 2 with
`rg: .codex/config.toml: No such file or directory (os error 2)`.
The absent worktree config does not prove a runtime loading failure or absence
of global configuration. Image runtime and fresh rehearsal proof remain pending.

Python implemented a private `sdlc_final_report.py` selector
without public schema changes. Its strict standalone-heading scanner excludes
fenced, blockquoted, and inline examples and checks all native declarations
within a completed bounded root turn. Per the root's ruling, a valid directly
captured final retains the existing no-native compatibility path; prior-final
recovery refuses missing native evidence. The new `roster-provenance.md`
sidecar records run/parent/turn/path metadata, ordinals/timestamps,
normalization, SHA256, reason, and outcome without raw output or secrets.
It lives beside the canonical per-run `settlement.json`, independent of custom
output overrides. Raw captured output and transcripts are preserved. Earlier
interim checks are retained below; final validation follows them.

The root supplied the Python specialist's interim command:
`uv run --project python pytest tests/test_sdlc_final_report.py
tests/test_sdlc_team.py tests/test_lane_result.py -n 0 -x -q` exited 0 with
108 passed. Scoped Ruff and ty checks also exited 0; their exact arguments
were pending at that point; the final arguments are recorded below. Initial
syntax, codec, and zip errors were corrected before these results.

The next scoped run exited 0 with 114 passed through public
`dispatch`/`read_status` interfaces using an isolated synthetic Codex executable.
This latest interim result supersedes the earlier 108-test count. Refusal
controls for zero/missing children, later unclaimed child, recorded role
mismatch, and path mismatch passed. Raw captured output stayed unchanged;
the provenance sidecar remains metadata-only. Scoped Ruff and ty exited 0
after a typing correction; final arguments are recorded below.
These are unit integration fixtures, not fresh CLI rehearsals. Additional
native-eligibility axes and source mutation controls were then added as
recorded below.
The root's integration inspection was read-only, with no out-of-allowlist
edits, extra agents, or full gates.

The next scoped suite exited 0 with 123 passed before the final fixture
durability repair. Python then found the historical replay depended on
ignored `.agent/plans/` records that would be unavailable in a clean clone.
The specialist embedded minimal exact historical native records into
the allowed `tests/test_sdlc_final_report.py`, with independently pinned
hashes, IDs, timestamps, and the original source citation. Both actual final
message texts are retained; no additional fixture files are created.
Historical regression replay still does not establish a fresh native CLI
or actual hook-replacement rehearsal.

The first real source mutation disabled prior-final fallback: its control
failed with exit 1, and restoring the source made that control pass with
exit 0. This is mutation evidence for fallback behavior, not rehearsal proof.
The second source mutation removed the full-turn agreement guard: its
conflicting path control incorrectly accepted `/root/python` versus
`/root/other`, failed with exit 1, and passed with exit 0 after restoration.
Both mutation harnesses exited 0 and restored the source byte-identically
in their `finally` paths. The root held source inspection during mutations.

Exact mutation commands reported by Python:

```bash
uv run --project python pytest \
tests/test_sdlc_final_report.py::test_historical_hook_replacement_\
regression_preserves_actual_report \
'tests/test_sdlc_team.py::test_public_dispatch_native_recovery_'\
'reconciles_every_child[none]' \
-n 0 -x -q
uv run --project python pytest \
tests/test_sdlc_final_report.py::test_any_invalid_or_conflicting_\
declaration_refuses_fallback \
-n 0 -x -q
```

The first command passed 2 controls before mutation (exit 0), failed after
restricting prior-final selection to latest-only (exit 1), and passed the
same 2 controls after restoration (exit 0). The second command passed 8
controls before removing the agreement guard (exit 0), failed with that
mutation (exit 1), and passed the same 8 controls after restoration (exit 0).

The embedded historical fixture retains both actual message texts and the
turn/phase metadata, identifiers, and hashes. The substantive message SHA256 is
`55402bf41e77bc178098cd1c43ee9894dd04f49217adad750cac803aed7f3faf`.
It no longer depends on ignored plan files and has not been committed.

Python then found and fixed an interaction with the old collector: quoted,
fenced, or inline heading examples after an actual roster could be reselected.
The strict scanner now passes only the initial roster-list body to the legacy
collector while continuing to check all actual standalone declarations.
Prefix and suffix controls were added. At that point, a focused third mutation
and post-change suite were pending. The prior 123-test result is interim;
completed third mutation and final validation are recorded below.

The next interim scoped suite exited 0 with 130 passed. Scoped lint, type,
format, and diff checks also exited 0. That result predates two subsequent
edge changes: a blank-terminal refusal test, and moving
`roster-provenance.md` beside the canonical per-run settlement so custom or
shared output overrides cannot collide. The synthetic public dispatch pass
arm now pins a custom shared-output override and the sidecar placement.
The 130-test result predates these final edge changes; it is retained as
interim history, with authoritative post-change results below.

## Authoritative Python validation

Frozen final source and tests passed the following commands:

```bash
uv run --project python pytest \
tests/test_sdlc_final_report.py tests/test_sdlc_team.py \
tests/test_lane_result.py -n 0 -x -q
uv run --project python ruff check \
python/src/dotfiles_setup/sdlc_final_report.py \
python/src/dotfiles_setup/sdlc_team.py \
tests/test_sdlc_final_report.py tests/test_sdlc_team.py
uv run --project python ruff format --check \
python/src/dotfiles_setup/sdlc_final_report.py \
python/src/dotfiles_setup/sdlc_team.py \
tests/test_sdlc_final_report.py tests/test_sdlc_team.py
uv run --project python ty check --project python \
python/src/dotfiles_setup/sdlc_final_report.py \
python/src/dotfiles_setup/sdlc_team.py \
tests/test_sdlc_final_report.py tests/test_sdlc_team.py
git diff --check -- \
python/src/dotfiles_setup/sdlc_final_report.py \
python/src/dotfiles_setup/sdlc_team.py \
python/src/dotfiles_setup/lane_result.py \
tests/test_sdlc_final_report.py tests/test_sdlc_team.py \
tests/test_lane_result.py
```

Each command exited 0. Pytest reported 131 passed in 7.67 seconds; Ruff
format-check reported four formatted files. Changed Python paths are
`sdlc_team.py`, new `sdlc_final_report.py`, `test_sdlc_team.py`, and new
`test_sdlc_final_report.py`. `lane_result.py` and `test_lane_result.py`
remain unchanged. Public schemas remain unchanged.

The third mutation command was:

```bash
uv run --project python pytest \
tests/test_sdlc_final_report.py::test_examples_are_absence_not_declarations \
-n 0 -x -q
```

Before mutation, eight cases passed (exit 0). Removing the roster body
boundary produced exit 1 (one failed, four passed) because suffix inline
prose made the collector misread a malformed declaration. Restoration
passed all eight cases (exit 0). The first historical mutation was repeated
after embedding the durable fixture: two cases passed before mutation (0),
latest-only selection failed (1) on the expected substantive message hash
versus terminal receipt hash, then both passed after restoration (0).
Each mutation restored the source byte-identically.

Final controls refuse a blank terminal message. Normalization is limited
to CRLF/CR-to-LF conversion and trailing whitespace; controls reject changes
to interior VT, FF, and U+2028. The public dispatch pass arm pins the
metadata-only sidecar beside canonical settlement even with a custom shared
output path. These are scoped regression and synthetic process-boundary
fixtures, including actual historical messages; they are not fresh CLI or
actual hook-replacement rehearsal proof.

## Remaining validation

Scoped specialist checks are authorized; full lint, pytest, verify, and
lint-docs gates remain pending the coordinator's serialized SLOT GO. The
documentation role's ordinary
`mise run lint-docs` success criterion therefore remains pending, rather than
being represented by a scoped check.

Fresh CLI review, bounded implementation/control rehearsals requiring all five
expected roles, and actual hook replacement remain coordinator work. Unit
fixtures and historical replay cannot satisfy those rehearsal requirements.
Participation reconciliation must not upgrade partial implementation, licensed
dissent, or failed research to delivered work.

## Research coverage

The root owns the hook-specific strict-five research receipt for request
`01a10e91-1219-7320-90af-0222515b7430`. The first attempt used native
`fnox --config ~/.config/fnox/config.toml --profile codex_research --no-defaults
--no-daemon --non-interactive exec` with `mise -C
/Users/rmanaloto/.codex/tools/dotfiles-research-gate run research-fanout`,
`--strict-five`, an explicit Last30Days plan, and the hook output directory.
It exited 1. Manifest:
`~/.codex/research-coverage/01a10e91-0d7d-7833-b61d-b3d164b29f61/01a10e91-1219-7320-90af-0222515b7430/manifest.json`.

RESEARCH INCOMPLETE: the GitHub releases route failed with exact reason
`exited 1: stream error: stream ID 1; CANCEL; received from peer |`.
The root retried that transient failure once with the full hook-specific receipt.
Other first-attempt routes: GitHub issues ok, discussions `empty_verified`
(control 10), Exa ok (10), Context7 ok (5), Firecrawl developer ok (10),
Last30Days ok (3). Firecrawl search returned primary HTTP 402 and was recorded
`skipped: credits-exhausted`; its Serper substitute returned HTTP 200 with seven
results and is PROVISIONAL. Those routes are root-reported CLI evidence;
the documentation specialist ran no independent research apps or MCP routes.

The root's additional GitHub code probe exited 0 with HTTP 200:
`final_answer` 59, `task_complete` 18, known-absent control 0. Its local primary
Codex corpus read at `app-server.md:1238` confirmed `commentary` and
`final_answer` phases. No secret values or raw tool messages are copied here.

The root's full retry exited 0; its strict-five receipt passes PROVISIONAL
because Firecrawl search used Serper after primary HTTP 402 credit exhaustion.
Latest manifest counts: GitHub issues 1, discussions `empty_verified` with a
control, releases `empty_verified`, Exa 10, Context7 5, Firecrawl developer 10,
Firecrawl search via Serper 10, Last30Days 3. The first attempt's failed releases
route remains recorded above; the retry supersedes its incomplete overall
status while retaining the provisional provider substitution.

Actual research execution used native fnox, mise, uv/Python fanout, gh for
GitHub REST/GraphQL, Exa HTTPS API, Context7 `ctx7 library`/`ctx7 docs`,
Firecrawl developer HTTPS GET, Firecrawl search CLI, the Last30Days
`last30days.py` script, and Serper HTTPS fallback. The documentation specialist
confirmed those transport declarations in the exact fanout checkout's
`python/src/dotfiles_setup/research_fanout.py`. No connector apps or separate
Exa/Firecrawl/Last30Days plugin skills were invoked. Root skills used were
`codex-sdlc-team`, `graphify`, and `research-sweep`; configuration used
`codex-schema`; documentation used `codex-sdlc-team` and `writing-for-agents`.

The root verified the latest manifest's request ID, strict-five-v2 contract,
and raw hashes (`raw_hash_matches=True` for all). Its primary-source reads at
the installed release's [message model] and [turn completion protocol]
confirmed `commentary`/`final_answer` phases, `TurnCompleteEvent.turn_id`,
`last_agent_message`, and optional `root_turn_id`. Source checks exited 0;
this establishes native format evidence, not parser or rehearsal success.

[message model]: https://github.com/openai/codex/blob/rust-v0.160.1/codex-rs/protocol/src/models.rs#L1027
[turn completion protocol]: https://github.com/openai/codex/blob/rust-v0.160.1/codex-rs/protocol/src/protocol.rs#L2153

## Workflows specialist outcome

No repair-specific contradiction or consumer defect requiring respec was
identified. The workflows specialist made no writes and ran no syntax or
pin-actions gate. Its revised role definition (lines 15–25) preserves direct
child/no-delegation topology, caller commits, read-only review without gates,
only spec-authorized scoped implementation checks, and coordinator ownership
of pin-actions. Line 28 retains SHA-pin review responsibility.

The source inspection command
`rg -n 'sdlc|lane.result|lane_result|sdlc_final_report|roster-provenance' .github`
exited 1 with no matches; that bounded search is not full absence proof.
The generic CI consumer at `.github/workflows/ci.yml:235–245` runs
`uv run --project python pytest tests/ -q`, and its comments at 241–242 state
that `image_exec` and `codex_exec` tests are deselected. Neither this source
read nor unit CI proves actual native rehearsal. The external-reference
inspection `rg -n 'uses:' .github/workflows` exited 0 and found SHA-pinned
references; it did not run the pin-actions gate. Other reads/diff checks exited
0 as reported by the specialist.

A preliminary exploratory query incorrectly assumed `lint.yml` and
`claude.yml` existed and exited 2 with `No such file or directory (os error 2)`
for both. The specialist corrected the query using the actual file inventory
and the whole `.github` scan. No repository defect is inferred from those
incorrect paths. Fresh rehearsal, schema currency, and native loading evidence
remain pending.

## Specialists spawned

The root dispatcher reported all five direct children successfully spawned,
with no dispatcher child or additional agents:

- `sdlc-python-specialist` — `/root/python`
- `sdlc-config-specialist` — `/root/config`
- `sdlc-documentation-specialist` — `/root/documentation`
- `sdlc-image-specialist` — `/root/image`
- `sdlc-workflows-specialist` — `/root/workflows`

No others were spawned. This is the root's reported participation roster;
it does not substitute for settlement reconciliation or fresh rehearsal proof.

## Live-proof addendum and fresh implementation scope — 2026-10-05

This append-only addendum promotes later observed evidence without rewriting
the earlier report's pending claims. The documentation specialist read the
fresh `.agent/plans/sdlc-live-implementation-rehearsal.md` and owns only this
addendum and `.claude/rules/codex-sdlc-team.md`. The eager rule now agrees with
the canonical skill: the CLI root directly dispatches five specialists,
parallel spawning respects capacity, sequential spawning is allowed, and no
dispatcher child or additional agent belongs to this team. The existing role
names, specialist gate table, typed invocation, and schema/guard limitations
are preserved. Review permits no writes or gates; implementation permits only
spec-authorized scoped checks, with full gates and commits owned by the caller.

### Actual prior native review and Stop-hook recovery

The specialist inspected these artifacts under
`.agent/sdlc-runs/9c7a9314650841019d634666117c4ccf/`:

- `settlement.json`: `status=completed`, `codex_returncode=0`, no errors, and
  matching claimed/observed sets of the five expected specialist roles.
- `independent-control.json`: independent inspection returned 0 and recorded
  exactly five direct children, substantive and replacement final ordinals
  145/153, and the genuine blocking Stop-hook record at ordinal 148.
- `roster-provenance.md`: `selection reason: prior-final-absence`,
  `selection outcome: selected`, and `participation outcome: consistent`.

The native parent is `01a10ea8-13d3-7a72-93bc-5bb46b36d327`; its completed
turn is `01a10ea8-1972-79a1-a7bf-7de51c7f8291`. The source is the native
`rollout-2026-10-05T19-40-59-01a10ea8-13d3-7a72-93bc-5bb46b36d327.jsonl`,
with independent source SHA256
`568db129d57383c785fa04625c6b234c9bb94c010d2d4d2fadc6d304c216a45a`.
Provenance bounds selection to the completed supervised turn; selected ordinal
145 predates replacement ordinal 153 and terminal ordinal 156. The selected
message SHA256 is
`e09c03e49b3662ff0a1e79cc15087ff3675551a6e67d5708137024a4149e549b`.
The latest and terminal messages share SHA256
`1adc9f3ca9e16094392fccf56b2195799b3f7cc1484bc1d39b3f328252ee119d`;
the independent control confirms latest/terminal/captured equality and absence
of a roster in captured output. Recovery therefore selected the earlier
substantive final while preserving the replacement and raw artifacts.

This genuine missing-receipt Stop block/replacement passed participation
recovery through the actual prior CLI run. It was a review/control rehearsal,
not a synthetic fixture. Intentionally incomplete research remains its
negative-control input; the successful reconciliation does not make that
research successful. Earlier historical replay and unit mutation evidence
remain separate from this live proof.

### Exact child instruction loading and root boundary

The specialist also inspected `independent-instruction-loading.json` beside
those artifacts. Its return code is 0. It records exact edited instruction
loading for all five children, including native source paths, developer record
ordinals 12–16, current definition paths, instruction hashes, and a true
`old_main_definition_mismatch` for each child. The receipt also records
`local_config_required_for_this_load=false`. Thus prior child loading has
evidence beyond role metadata; an absent worktree config alone did not prove
failure. This addendum cites that independent comparison and does not claim
the documentation specialist reran it.

The CLI root's dispatcher contract remains its generated prompt, rather than
proof that the root loaded the dispatcher TOML. The prior child-loading receipt
does not independently attest fresh implementation-mode child loading. The
coordinator must reconcile this fresh run's native metadata, completed root
turn, observed expected roles, final/captured agreement, and provenance.

### Documentation ownership and remaining checks

Before appending, the report contained 19,731 bytes with SHA256
`ced4a6c92eb6289e5e4821a1e517cbea682a5c810857657f0ca5fcea63d3decc`.
The earlier report stays an exact byte prefix; prefix verification and the
authorized focused checks are recorded below as they complete. No preexisting
commit-mode report, source module, test, native definition, hook, or setting
was edited by this specialist. Branch HEAD at the start was
`deb5c54e45d736e0a320fb64b4164814bc9df9df`.

Only focused `markdownlint-cli2` on the two allowed files and
`git diff --check` are authorized for documentation. Full lint, pytest,
verify, lint-docs, container gates, reviews, and commits remain coordinator
obligations under its serialized authorization. No staging, commit, push,
ship, land, container lifecycle, or heavy gate was performed. No contradiction
requiring licensed dissent was found in the assigned documentation correction.
Implementation, full gates, research coverage, and delivery remain separate
obligations; a consistent participation roster alone cannot complete them.
The root owns this turn's research receipt; this specialist ran no research
provider, connector app, or additional agent.

The provenance sidecar retains a distinct compatibility limit: native terminal
and latest hashes are unavailable on the direct captured compatibility route.
That general route limit does not erase the explicit native hashes recorded
for this prior recovery run.

The root supplied the fresh Python consumer result: the authorized
`uv run --project python pytest tests/test_sdlc_final_report.py
tests/test_sdlc_team.py tests/test_lane_result.py -n 2 -x -q` returned 0 with
131 passed in 1.97 seconds. Those isolated public-interface recovery controls
have fail arms; private-supervisor fixture coverage remains limited evidence.
This scoped test result does not independently establish fresh native
instruction loading or implementation delivery.

### Incremental scoped checks and current research receipt

The documentation specialist ran:

```bash
mise exec -- markdownlint-cli2 .claude/rules/codex-sdlc-team.md \
docs/research/kb/reports/agents/sdlc-roster-recovery-2026-10-05.md
git diff --check -- .claude/rules/codex-sdlc-team.md \
docs/research/kb/reports/agents/sdlc-roster-recovery-2026-10-05.md
```

Markdownlint returned 1: ten issues, all in the eager rule. Its preexisting
table separator produced six MD060 spacing findings; the image/documentation
rows were 95/99 characters, and two prose lines were 84/88 characters (MD013).
The report had no Markdown diagnostics. Diff check returned 0. A read-only
byte-prefix inspection through `uv run --project python python -c` returned 0
and confirmed the first 19,731 report bytes still have the original SHA256.
The specialist reported the long table rows to the root under licensed dissent
because the spec requires preserving the table. Resolution is recorded below;
no suppressions or configuration changes are authorized.

Two exploratory config queries used a nonexistent `.markdown*` glob and
returned 1 with `zsh:1: no matches found: .markdown*`; a corrected bounded
`rg` query returned 2 because `package.json` does not exist in this worktree.
The corrected file inventory returned 0. These are query errors, not evidence
of a repository or tool-loading defect.

The root supplied current configuration consumer checks: native
`mise run codex-agent-validate` returned 0 for six definitions (the dispatcher
plus five specialists); `mise run skills-mirror -- --check` returned 0.
Configuration made no edits. These scoped results do not attest this fresh
run's native instruction loading or delivery.

The root's mandated native fnox research-fanout command and independent
strict-five-v2 identity/hash verdict each returned 0. The current receipt is
PROVISIONAL: `provisional: firecrawl-search via serper (credits-exhausted)`.
Its external manifest is at
`~/.codex/research-coverage/01a10eb3-4652-7622-b6ae-210a2f4632c5/01a10eb3-4d53-7820-a59a-76b7aa051d9b/manifest.json`.
The recorded routes were GitHub issues ok (9), discussions/releases
`empty_verified` (0), Exa ok (10), Context7 ok (5), Firecrawl developer ok
(10), Firecrawl search substituted through Serper ok (7), and Last30Days
with the explicit factual plan ok (6). The documentation specialist did not
rerun these providers. This current provisional pass does not rewrite the
prior live control's intentional research-negative input.

The root subsequently verified Firecrawl's failed primary route: its raw
record returned 1 with exact redacted error
`Error: Request failed with status code 402`. Serper is the recorded
credit-exhaustion substitute, not evidence that the primary Firecrawl route
succeeded. Root image/workflows inspections returned 0 with empty staged and
unstaged consumer diffs; no image lifecycle, CI scope, or gates changed.

### Documentation check boundary and baseline control

The root directed the specialist to preserve all gate-table contents and retain
the explicit scoped failure rather than restructure table links or suppress
diagnostics. The specialist then used the public linter's stdin interface with
the original rule from `HEAD`, held entirely in memory:

```python
original = subprocess.run(
    ["git", "show", "HEAD:.claude/rules/codex-sdlc-team.md"],
    capture_output=True, text=True,
)
lint = subprocess.run(
    ["mise", "exec", "--", "markdownlint-cli2", "-"],
    input=original.stdout, capture_output=True, text=True,
)
```

This read-only control ran via `uv run --project python python -c`.
`git show` returned 0; the original-rule linter returned 1 with the same ten
diagnostics: MD060 at original line 11 and MD013 at original lines
16/17/45/47. No baseline file was written. The implementation therefore did
not introduce those diagnostics. The CLI help read returned 2 while documenting
stdin support; no check result was inferred from that help exit code.

The specialist corrected separator spacing and wrapped prose without changing
literal table values, guard limits, or authority. The intermediate two-file
Markdown recheck returned 1 with three MD013 findings, including one remaining
prose wrap; that prose was then wrapped. The image/documentation table rows
retain their required contents and exceed 80 characters. Those rows stay a
licensed-dissent boundary reported to the root, with focused Markdown failure
and partial verification retained. No full gate or delivery claim follows from
the documentation edits. Final scoped results follow.

The final two-file Markdown command above returned 1 with exactly two retained
MD013 findings at `.claude/rules/codex-sdlc-team.md:19:81` (95 characters) and
`:20:81` (99 characters). The report is Markdown-clean. The final scoped
`git diff --check --` command above returned 0. The byte-prefix inspection
returned 0 with `original_prefix_preserved=true` and the recorded 19,731-byte
SHA256 unchanged. `git rev-parse HEAD` returned 0 and still reports
`deb5c54e45d736e0a320fb64b4164814bc9df9df`. These results were rechecked after
appending this outcome. Both authored files remain unstaged; no caller commit
was performed. The prescribed content correction is implemented, with scoped
documentation verification partial because the required preexisting table
rows remain over the linter limit. Full coordinator gates and fresh native
rehearsal reconciliation remain pending; delivery is not established.

## Native citation-boundary correction — sequential restart receipt

This incremental addendum records the ratified same-ID rendered/citation
correction from `.agent/plans/sdlc-citation-boundary-correction.md`.
The coordinator's typed IMPLEMENT dispatch explicitly starts this work.
The dispatcher consumes each specialist's actual final/completed status and
inspects `list_agents` before spawning the next of the same five direct roles.
Python and config have completed in this restart; image and workflows have
not yet spawned at the documentation append boundary. This is not completed
five-role reconciliation or fresh implementation settlement.

The previous report is preserved as an exact 31,107-byte prefix with SHA256
`589647fa2b7644e655ae930398ce5ca91a035dfecbee684715d774f55ea0827e`.
The documentation specialist's pre-append `uv run --project python python -c`
byte/hash inspection returned 0 and matched that coordinator-supplied value.
Only this report is assigned to documentation, append-only and unstaged.
The historical licensed dissent, failed checks, partial implementations,
research failures, and provisional receipts above remain unaltered.

### Ratified source and display boundary

Captured and terminal normalized text must first agree exactly. A citation
transform requires a genuine current-turn native `item_completed` AgentMessage
with the same nonempty message ID as the raw final, matching parent/thread,
turn, final-answer phase, supervised interval, and exactly one attestation.
The rendered visible text must match captured/terminal. A single standalone,
complete trailing `oai-mem-citation` block is permitted only when its parsed
entries and rollout IDs exactly match native `item.memory_citation` metadata.
Each earlier eligible citation-bearing final binds its own visible prefix to
its own same-ID rendered event and metadata; only the latest final must match
the latest terminal/capture. Missing, conflicting, duplicate, malformed,
nested, multiple, mid-answer, unterminated, or unsupported evidence refuses.

Declaration inspection uses that attested visible boundary. Raw citation text
cannot declare or conceal a roster, and parsing failures do not become
provenance. Selected report text and selected/latest hashes retain raw-native
normalized values; captured/terminal hashes retain their actual values.
The provenance uses a fixed transform name and raw message hashes, without
citation contents or a public selector/settlement/lane-result schema change.
Direct captured compatibility cannot authorize missing-native transform
recovery. Existing exact equality and whitespace normalization remain controls.

The spec preserves failed run0d4c's four-role settlement and workflows spawn
capacity error, partial Python edits, prior7101's zero-evidence failed
settlement, and run0d5's original refusal. Historical recovery is replay;
no original settlement, transcript, or research receipt is rewritten.
No hook/config/settings/capacity change, extra role, substitute, dispatcher
child, commit, staging, push, ship, or lifecycle gate is authorized here.

### Python implementation and scoped evidence supplied by the root

The completed Python specialist resumed preserved partial edits in the two
allowed source/test files. It implemented the attested visible boundary,
strict citation grammar/metadata agreement, earlier-final binding, and durable
embedded native projections without changing the public schema. The root
consumed its actual final/completed status before routing the next role.
These are Python-reported commands and actual return codes; documentation
did not rerun this test or source-check bundle:

```bash
uv run --project python pytest tests/test_sdlc_final_report.py \
tests/test_sdlc_team.py tests/test_lane_result.py -x -q
uv run --project python ruff check \
python/src/dotfiles_setup/sdlc_final_report.py \
tests/test_sdlc_final_report.py
uv run --project python ruff format --check \
python/src/dotfiles_setup/sdlc_final_report.py \
tests/test_sdlc_final_report.py
uv run --project python ty check --project python \
python/src/dotfiles_setup/sdlc_final_report.py \
tests/test_sdlc_final_report.py
git diff --check -- python/src/dotfiles_setup/sdlc_final_report.py \
tests/test_sdlc_final_report.py
uv run --project python pytest \
tests/test_sdlc_final_report.py::\
test_retained_real_0d5_projection_replays_five_roles_without_delivery_claim \
-n 0 -x -q
```

Each command returned 0. The three-file bundle reported 232 passed; the
retained-real0d5 control reported one passed. Initial Ruff and ty probes each
returned 1, and an initial pytest probe returned 2; Python corrected those
issues before the final bundle. Their complete initial command/error text was
not supplied to documentation, so no fabricated arguments or error details
are added here. Those failed probes remain part of the work record.

Python's isolated in-memory revert executed the following exact command:

```bash
uv run --project python python - <<'PY'
from pathlib import Path
from types import ModuleType
import sys
sys.path.insert(0, str(Path('python/src').resolve()))
import dotfiles_setup
from dotfiles_setup import sdlc_final_report
import pytest
source = Path('python/src/dotfiles_setup/sdlc_final_report.py').read_text()
old = 'visible = tuple(_visible_final(turn, final) for final in turn.finals)'
assert source.count(old) == 1
reverted = ModuleType(sdlc_final_report.__name__)
sys.modules[reverted.__name__] = reverted
exec(
    compile(
        source.replace(old, 'visible = tuple(final.text for final in turn.finals)'),
        'isolated_reverted_sdlc_final_report.py', 'exec',
    ),
    reverted.__dict__,
)
dotfiles_setup.sdlc_final_report = reverted
raise SystemExit(pytest.main([
    'tests/test_sdlc_final_report.py::'
    'test_retained_real_0d5_projection_replays_five_roles_without_delivery_claim',
    '-n', '0', '-x', '-q',
]))
PY
```

That revert returned 1, rejecting the observed citation arm when raw equality
was restored. The unchanged on-disk implementation subsequently passed the
focused retained0d5 command above, return code 0. This is an isolated realistic
fail arm through the public selector; no shared source file was mutated.

Python reported read-only embedded-artifact checks returning 0: both newly
embedded projections exactly match retained artifact bytes; decoded historical
native records2,528,536,539 match the original session, and record1 retains
only permitted projected session metadata. The original raw historical report
hash is `55402bf41e77bc178098cd1c43ee9894dd04f49217adad750cac803aed7f3faf`.
The complete commands for those checks were not printed in its final and
were not rerun by documentation; these outcomes are attributed to Python.

A compact historical encoded-byte comparison initially returned 1. The
existing literal's actual hash is
`7e32342fe5ccda59d1f2563e9f9b221664703c8fbd7bde2a05ba7a4f89719d6f`,
which differs from the retained-artifact comment beginning `44b99`.
Decoded original-native record equality resolved the comparison, return code
0, without altering the original compact fixture literal. Serialization-byte
inequality is retained as a failed probe and is not recast as source drift.

The real0d5 replay selects the existing five-role roster. Its raw/latest hash
is `378b05369e31ee7b8fb2a378177779b56b50bbcdba33615d2eb99d80bc8f8b81`;
terminal/captured hash is
`0fba34198d98f1a17d52e71bdcff934e6998aca0bc51c7cdb9cd00b7963a01cd`.
The replay remains task partial and research PROVISIONAL; it does not rewrite
the original refusal or establish fresh implementation delivery.

Frozen final Python source SHA256 is
`0e442eea49301b145e919f999458c494ef0626a5d597149bfc01b0159747af05`.
Frozen final test SHA256 is
`5918de314e4afc144e8af576c693d5e2892127f9ce1031500b166a767d0461ca`.

### Configuration consumer findings supplied by the root

The completed config specialist found no consumer/schema contradiction or
repair requiring respec. The private citation transform/provenance remains
separate from public settlement/lane-result schema; hook/schema consumers
require no configuration change. Config made no edits and ran no full gate.
Its exact final command was:

```bash
shasum -a 256 python/src/dotfiles_setup/sdlc_final_report.py \
tests/test_sdlc_final_report.py
```

It returned 0 with the same frozen source/test hashes above. Discovery probes
returned 2 for the absent `.claude/hooks` directory and guessed
`codex_agent_schema.py` path. Corrected inventory/read routes returned 0.
Their exact command strings were not supplied in config's final; these are
attributed results, not independently rerun documentation checks. A guessed
missing path is not evidence of a broken installed schema or native loading.

### Same-turn strict-five-v2 research receipt

The root ran the required native fnox command below, actual return code 0.
Documentation consumes this same-turn root receipt rather than launching
another provider run or claiming a child-owned research sweep:

```bash
fnox --config ~/.config/fnox/config.toml --profile codex_research \
--no-defaults --no-daemon --non-interactive exec -- \
mise -C /Users/rmanaloto/.codex/tools/dotfiles-research-gate \
run research-fanout -- \
'OpenAI Codex native item_completed AgentMessage memory_citation '\
'final_answer rendered citation same message ID' \
--repo openai/codex --strict-five \
--request-id 01a10ecd-d456-7741-9220-c51883b6d7dc \
--last30days-plan /Users/rmanaloto/.codex/research-coverage/\
01a10ecd-ccd2-7421-a269-0210d2c6f32d/\
last30days-plan-01a10ecd-d456-7741-9220-c51883b6d7dc.json \
--out /Users/rmanaloto/.codex/research-coverage/\
01a10ecd-ccd2-7421-a269-0210d2c6f32d/01a10ecd-d456-7741-9220-c51883b6d7dc
```

The root verified the manifest/request identity and primary sources. This
specialist independently read the same manifest, then checked its request ID,
`strict-five-v2`, strict flag, positive controls for empty routes, every source
raw hash and both Firecrawl attempt hashes through read-only
`uv run --project python python -` inspection; each returned 0.
The manifest is at the command's output directory, `manifest.json`.

The receipt passes PROVISIONAL. GitHub issues/discussions/releases are each
`empty_verified`, with control counts10/10/1. Exa is ok with10 results,
Context7 ok with5, Firecrawl developer ok with10, Last30Days ok with10.
Firecrawl search uses Serper, ok with7 results, provisional true.

RESEARCH INCOMPLETE: the primary Firecrawl search route is recorded skipped,
credits-exhausted, exact blocker `Error: Request failed with status code 402`.
Its Serper substitute returned HTTP200. The provisional receipt passes with
that substitution; it does not assert primary Firecrawl success. Previous
research failures remain unchanged above.

The root reported actual execution through fnox, mise, uv/Python, gh GitHub
issues/discussions/releases, Exa HTTPS, Context7 `ctx7 library`/`ctx7 docs`,
Firecrawl developer HTTP, Firecrawl search CLI with Serper HTTPS fallback,
and the Last30Days plugin's `last30days.py` script via python3 with an explicit
plan. No connector app or MCP research server ran. Root applied
`codex-sdlc-team`; the Last30Days plugin script ran through its CLI, without
invoking the Last30Days skill. This documentation specialist applied no
additional skill, invoked no provider, and spawned no agent.

The root's primary web reads of the [current stream-parser README] and
[current memory citation instructions] provide display context. The retained
same-ID native evidence independently binds this observed transform at
CLI0.160.1; current docs do not establish universal0.160.1 renderer behavior.
Those primary-source checks are root-reported evidence, not a documentation
rerun of the web reads.

[current stream-parser README]: https://github.com/openai/codex/blob/main/codex-rs/utils/stream-parser/README.md
[current memory citation instructions]: https://github.com/openai/codex/blob/main/codex-rs/ext/memories/templates/memories/read_path.md

### Documentation scope and remaining coordinator work

No licensed contradiction was found in this assigned append. Source/test
implementation and its scoped checks are Python evidence; schema/consumer
inspection is config evidence; provider execution and primary reads belong
to the root. Documentation validates only report content and append
preservation. No full lint, pytest, verify, lint-docs/agnix, container,
pin-actions, lifecycle, review, staging, or commit gate ran in this child.

Image and workflows inspection remains pending at this addendum's boundary.
The caller owns serialized full gates, reviews, commit, and fresh post-final
native reconciliation/new-instruction evidence. Historical replay, scoped
unit controls, and participation success do not establish delivery or erase
licensed dissent, partial implementation, failed providers, or PROVISIONAL
research. Final append/content inspections follow as they complete.

The first attempt to append this evidence failed at shell parsing, return code
1, exact error `zsh:196: unmatched` followed by a backtick. The outer heredoc
collided with the verbatim inner Python command's delimiter. No append occurred:
the corrected command asserted the prior 34,208-byte hash before writing.
A distinct outer delimiter resolved the collision; the original report and
first incremental addendum were preserved byte for byte.

### Final documentation content and append inspections

The documentation specialist ran the following exact scoped commands:

```bash
git diff --check -- docs/research/kb/reports/agents/sdlc-roster-recovery-2026-10-05.md
uv run --project python python - <<'DOC_VERIFY'
from pathlib import Path
import hashlib
p = Path('docs/research/kb/reports/agents/sdlc-roster-recovery-2026-10-05.md')
b = p.read_bytes()
assert hashlib.sha256(b[:31107]).hexdigest() == '589647fa2b7644e655ae930398ce5ca91a035dfecbee684715d774f55ea0827e'
text = b[31107:].decode()
assert sum(line.startswith('```') for line in text.splitlines()) == 8
for term in [
    '232 passed', 'RESEARCH INCOMPLETE:', 'PROVISIONAL',
    'Image and workflows inspection remains pending',
    'No licensed contradiction', 'same nonempty message ID',
]:
    assert term in text, term
for name, expected in [
    ('python/src/dotfiles_setup/sdlc_final_report.py',
     '0e442eea49301b145e919f999458c494ef0626a5d597149bfc01b0159747af05'),
    ('tests/test_sdlc_final_report.py',
     '5918de314e4afc144e8af576c693d5e2892127f9ce1031500b166a767d0461ca'),
]:
    assert hashlib.sha256(Path(name).read_bytes()).hexdigest() == expected
print(
    'original_prefix_preserved=true evidence_content_present=true '
    'code_fences_balanced=true source_test_hashes_unchanged=true '
    f'bytes={len(b)} sha256={hashlib.sha256(b).hexdigest()}'
)
DOC_VERIFY
git diff --cached --name-only -- docs/research/kb/reports/agents/sdlc-roster-recovery-2026-10-05.md
```

All three returned 0. Diff check had no diagnostics; the staged-path query
was empty. The content inspection confirmed the original 31,107-byte prefix,
required evidence terms, balanced addendum code fences, and unchanged frozen
Python source/test hashes. At that inspection boundary the report contained
44,448 bytes, SHA256
`03391a596b221890ff5e497426e2b422dfdba47827a4bb409101688538cbfc84`.
The fence count belongs to that pre-final-outcome snapshot; this appended
verbatim command receipt adds its own enclosing code fence afterward.
These are content/preservation inspections, not a Markdown linter, full gate,
native rehearsal, or delivery proof. Results are recorded once; no broader
documentation gate was run. This final append preserves the previously
inspected report byte prefix. Image/workflows remain pending at handoff.

## Final-runtime rehearsal — 2026-10-05

Prior actual implementation: `0d5e7e1a16f248509914f7931e538701`
(native parent `01a10eb3-4652-7622-b6ae-210a2f4632c5`); original FAIL retained.
Scoped final references: `/root/python` pytest bundle `-n 0 -x -q`,
rc=0, 232 passed; `/root/config` `codex-agent-validate`/`skills-mirror` rc=0.
`/root/image` consumer diff rc=0; `/root/workflows` diff rc=0, rg rc=1.
Failed inspections retained: config/image rg rc=2 (missing config).
`/root/documentation`: report Markdown/diff/prefix rc=0; scoped checks only.
Native ordering/Stop/same-ID renderer/settlement are coordinator-owned;
missing proof = FAIL. No providers/full gates/delivery; caller commits.
