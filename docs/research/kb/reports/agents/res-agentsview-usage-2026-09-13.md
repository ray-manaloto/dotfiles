# Are we using agentsview correctly for the secret-findings problem? (2026-09-13)

**Lane:** read-only research (`res-agentsview`). No edits, no `--reveal`, no
`scan`/`sync`/`duckdb`/`prune`/`embeddings`/`daemon`/`serve`, no reads of
`~/.agentsview/config.toml` or other credential files. All commands below ran
against the local archive that already exists; nothing was uploaded or
persisted beyond what a prior `agentsview` sync already wrote.

Tool: `agentsview v0.42.0 (commit ff8fb4e8, built 2026-09-01T19:37:18Z)`, only
reachable at
`/Users/rmanaloto/.local/share/mise/installs/github-kenn-io-agentsview/0.42.0/agentsview`
— see finding 2.

## 1. The full `secrets` surface

```
agentsview secrets              # scan for and list detected secret leaks
agentsview secrets list [flags] # list stored findings (redacted by default)
agentsview secrets scan [flags] # full-ruleset scan; PERSISTS findings
```

Two confidence tiers, from `docs/session-api.md#secret-scanning` (fetched via
`https://agentsview.io/docs/session-api.md`):

| Tier | Rules | When scanned |
|---|---|---|
| **Definite** | Well-anchored vendor formats: AWS access keys, Anthropic `sk-ant-…`, OpenAI `sk-proj-`/`sk-svcacct-`/`sk-admin-`, GitHub `ghp_…`/`github_pat_…`, GitLab `glpat-…`, Slack `xox{b,a,p,r,s}`, Stripe `sk_live_…`/`rk_live_…`, Google `AIza…`, npm `npm_…`, PyPI `pypi-…`, Hugging Face `hf_…`, SendGrid `SG.…`, PEM private-key blocks | **Inline during sync** — every ordinary `agentsview` sync already stamps these |
| **Candidate** | FP-prone heuristics: basic-auth URLs, JWTs, high-entropy assignments | **Only when `secrets scan` runs explicitly** |

`secrets list --confidence definite` (the default) is a pure read against
whatever the last sync already found — it triggers no new scanning and is
always safe to run. `secrets scan` (forbidden in this lane) walks the whole
archive, re-runs the **full** ruleset (definite + candidate) and **writes new
rows to the `secret_findings` table** — that is a real mutation of the
archive, which is why the brief bans it; `--backfill` narrows it to sessions
not yet scanned at the current `secrets_rules_version`.

**Measured, safely:** `secrets list --confidence candidate --limit 500 --format
json` returns **0 findings** right now (control: the same call with
`--confidence all` returns the full 649, so the query itself discriminates).
That means **no candidate-tier scan has ever run** in this archive — the
649 definite findings are 100% inline-sync byproduct, and the FP-prone
heuristic tier (which would likely add noise, not signal, per its own "FP-prone"
label in the docs) has literally never executed. Running `secrets scan` would
add JWT/basic-auth/high-entropy findings on top, which is a plausible reason
to eventually run it (under `--backfill`) but not blindly — its own docs flag
that tier as false-positive prone, and it is machine-mutating.

**No allowlist / ignore / baseline / triage-marking mechanism exists.**
Grepped `secrets`/`secrets list`/`secrets scan --help` (all flags enumerated
below) and the full `commands.md` (1395 lines) and `session-api.md` (1076
lines) docs for `allowlist`, `baseline`, `ignore`, `dismiss`, `suppress`,
`whitelist`, `false-positive`: the only `allowlist`/`ignore` hits are for
**unrelated** features (`--allowed-subnet` on `serve`, `watch_exclude_patterns`
for directory watching, `--include-project`/`--all-projects` for project
filtering). There is no verb or flag that marks a `secret_findings` row as
triaged, reviewed, a known fixture, or false-positive. A finding, once
written, stays forever (or until the archive itself is pruned/reset — `prune`
deletes whole *sessions*, not individual findings, and is out of scope for this
lane anyway).

`secrets list` flags (verbatim from `--help`):
```
--agent string        Filter by agent
--confidence string   definite | candidate | all (default definite)
--cursor int          Pagination cursor
--date-from/--date-to string
--limit int           Max findings (default 50, max 500)
--project string      Filter by project
--reveal               Show full secret values (localhost-only; OPERATOR ONLY, never used here)
--rule string          Filter by rule name
```

## 2. Are we even running it?

**No — nothing in this repo invokes agentsview.** `git grep -n -i agentsview`
across the tracked tree (branch `feat/enable-research-plugins` @ `5f96509`)
returns hits only in:
- `.claude/settings.json` — two `Read()` **deny** rules on `~/.agentsview/config.toml{,.lock}` and a `Bash()` deny fragment (defensive, not usage)
- `.claude/rules/secrets-out-of-the-shell-env.md` — narrating the config.toml leak incident
- `docs/research/kb/reports/agents/2026-09-12-agentsview-field-research.md` and this lane's sibling reports — research artifacts, not wiring

There is **no** mise task, no hk step, no `doctor.toml` check, no CI job, no
git hook that calls `agentsview` anywhere. `doctor.toml` (repo root) has zero
`agentsview`/secret-scanning integration; its only `secret`-adjacent content
is the unrelated `env_true` credential-name list for the shell-env doctor
check.

⚠️ **It is not even reachable as a bare command on this branch.** `mise.toml:126`
(comment on the `firecrawl` pin) says explicitly: *"a bare `agentsview`...
resolved an ORPHAN mise shim and `agentsview --version` exited 'No version is
set for shim' — the same shape that blocks agentsview."* Confirmed by history:
commit `0085d99` ("chore(tools): pin agentsview 0.42.0 host-only") exists only
on **`fix/universal-subprocess-logging`** (`git branch -a --contains 0085d99`
names only that branch) — a branch `goalrev-agentsview-2026-09-13.md` already
found is 6 commits behind main and would delete ~9600 landed lines on a naive
merge. On `main` and on this branch, `agentsview` resolves to nothing without
the absolute installs-dir path used throughout this report.

**The finding is exactly what the brief anticipated: a scanner nobody runs,
whose own pin hasn't shipped.** The 649 findings that exist are a fossil of
whatever `agentsview sync` ran historically (against `~/.claude`/`~/.codex`
session trees across 11 projects), not evidence of an active gate.

## 3. The 15:1 ratio question

**No native de-duplication or grouping-by-value exists.** `secrets list` has
no `--group-by`, `--distinct`, or `--dedupe` flag, and `--format json` returns
a flat `{findings: [...], next_cursor: N}` array — one row per
(session, rule, match_index) tuple, not per distinct value. Confirmed against
both pages of `--confidence all --limit 500`: 649 raw findings, **44 distinct
`redacted_match` strings** (counted client-side from the JSON, no value ever
printed) — a ~14.75:1 ratio, consistent with the architect's ~15:1 figure.

The **only** supported paths to the deduplicated set are (a) what this lane
already did — pull the JSON via `--format json`, extract `redacted_match`
client-side, dedupe in a script/pipeline — or (b) the HTTP API's identical
`GET /api/v1/secrets` endpoint (same fields, same lack of grouping). Both are
"bring your own dedup," not an agentsview feature. **Practically: whoever
triages this should write a five-line script that reads `secrets list
--confidence all --format json` (paginating on `next_cursor`), groups by
`redacted_match` (or by `(rule_name, redacted_match)` if two rules ever
redact to the same shape), and reports 44 rows with a representative
`session_id`/`project` each — a distinct-value triage list, not 649
duplicates.** Rule 8 of this repo's zero-bash-logic policy says that script
belongs in `python/`, not a one-off shell pipeline (see §5).

## 4. What agentsview CANNOT tell us

Stated plainly, per the brief's instruction to name blind spots rather than guess:

- **It cannot tell a real credential from a fixture, doc example, or test
  string.** The rule set is purely format-based (regex-anchored on vendor
  prefixes); it has no concept of "this AWS key lives in a `tests/fixtures/`
  path" or "this is a well-known placeholder." Every one of the 649 findings
  needs a human (or a separate heuristic) to classify real-vs-fixture — the
  reason `--reveal` is operator-only and this lane never ran it.
- **It cannot tell you *where in the repo* a secret lives**, because it scans
  **agent session transcripts** (message/tool_input/tool_result content in
  `~/.claude`, `~/.codex`, etc.), not repository source files. A finding's
  `location_kind` is one of `message`/`tool_input`/`tool_result`/
  `tool_result_event` inside a session JSONL — 649/649 measured here skew to
  `tool_result` per the architect's note. That is a **different surface**
  than a source-code secret scanner (gitleaks, betterleaks, trufflehog):
  agentsview answers "did an agent ever see/paste this value in a
  conversation," not "is this value committed to the tree." Both questions
  matter here (`.claude/rules/secrets-out-of-the-shell-env.md` catalogues
  exactly the leak-into-transcript failure mode agentsview is suited to
  catch), but agentsview is not a substitute for a repo-scanning tool.
- **`rules_version` does mean what it looks like — but it hasn't drifted
  yet.** All 649 findings in this archive currently carry the **same**
  `rules_version` hash (`e4715ff2…`), confirmed by set-collecting the field
  across both JSON pages. So today there is no stale-ruleset problem to
  reconcile; `secrets_rules_version` (session-level) plus `--backfill` exist
  specifically so that a future ruleset bump can be re-applied incrementally
  without re-scanning everything — a mechanism this project has not yet had
  to use.
- **It cannot filter to "sessions from repo X's working tree" reliably beyond
  the `--project` label agentsview itself assigned at sync time** — that
  label is derived from `cwd` heuristics on ingest, and there is no
  cross-check offered here against whether that heuristic mapped a session to
  the right project.
- **A negative result from `secrets list` is not "no secrets exist"** — it is
  "no *definite-tier* pattern matched in *sessions agentsview has synced*."
  Sessions never synced (a different machine, a pruned/cleaned session, a
  harness agentsview doesn't support) are invisible. Control arm for this
  claim: `secrets list --rule "zzqqxx-nonexistent-rule-9f3k" --confidence all`
  returned `{"findings":[],"next_cursor":0}` — proving the query mechanism can
  return a genuine empty result — while the same call with `--rule
  aws-access-key` returned a real row, so absence-of-match is a meaningful
  signal *for rules that exist*, but says nothing about transcripts the tool
  never ingested.

## 5. Recommended usage for this project

Concrete, scoped to what agentsview actually offers (no invented capability):

1. **Ship the pin first.** `chore(tools): pin agentsview 0.42.0 host-only`
   (`0085d99`) sits unshipped on `fix/universal-subprocess-logging`. Land it
   (or cherry-pick it standalone — it is self-contained tooling metadata) so a
   bare `agentsview` resolves on `main` at all. Host-only is the right call
   per that commit's own rationale (the archive indexes `~/.claude`/`~/.codex`,
   which don't exist in the devcontainer image) — no change needed there.

2. **Add a read-only `doctor.toml` check, not a blocking gate.** Per this
   repo's own `zero-skip-policy.md`/`verify-before-advancing.md`, a raw
   secret-in-transcript finding is not something to auto-fail CI on (no
   reveal, no way to auto-classify fixture-vs-real) — it is exactly the shape
   of thing `doctor.toml` already handles for other "silent unless drift"
   signals (see the `env_true` check in the same file). A new doctor check
   that runs `secrets list --confidence definite --format json` (paginating),
   counts findings, and reports "N secret findings across M distinct values
   (was N₀/M₀ last session)" gives the operator a standing signal without
   auto-triaging anything. This matches `mise-tasks-only.md`'s canonical
   shape: **skill → mise task → python module**, no bash.

   - `python/src/dotfiles_setup/` module: wraps the JSON call + pagination +
     dedup-by-`redacted_match` (the fix for §3's 15:1 ratio) + the
     "same rules_version as last run?" drift check from §4.
   - `mise run agentsview-secrets-report` (or fold into an existing
     `plugin-health`/`dependency-currency`-style task) as the seam.
   - `doctor.toml` entry calling that task, silent when the finding count is
     unchanged, loud on new distinct values.

3. **Cadence: on-demand + doctor's existing SessionStart cadence**, not a
   cron/CI gate. Agentsview's own inline-sync-stamps-definite-tier design
   means the definite-tier count is already fresh whenever `agentsview`
   syncs (which happens on most read commands); a doctor check surfaces drift
   without agentsview needing a dedicated CI job. **Do not wire `secrets
   scan`** into any automated path — it is a mutating command whose
   candidate tier is explicitly FP-prone, and this repo's `real-integration-
   evidence.md`/`zero-skip-policy.md` posture argues against automating a
   step whose output nobody has a plan to act on yet (no triage-marking
   feature exists, per §1).

4. **What stays manual, by design:**
   - **Triage of the 44 distinct values** (real vs. fixture vs. doc example)
     — agentsview cannot do this (§4); it is an operator judgment call,
     ideally the same operator running `--reveal` under the existing
     "OPERATOR-ONLY" convention this repo already uses for attestation
     (`.claude/CLAUDE.md`'s plan-attest section is the closest analog: a
     human-only verb, deliberately unreachable from any model route).
   - **Rotation of anything confirmed real** — outside agentsview's scope
     entirely; per `project_session_2026-09-13-c.md` in memory, this exact
     project has an open, deliberately-deferred rotation decision from a
     prior credential-leak incident. This lane defers to that precedent and
     does not recommend a rotation action here.
   - **Running `secrets scan --backfill`** to pick up the never-yet-run
     candidate tier — worth doing once, by the operator, after triage
     tooling for the definite tier exists, so the FP-prone tier doesn't
     double the untriaged backlog before there's a process for it.

## GitHub repos touched

- [kenn-io/agentsview](https://github.com/kenn-io/agentsview) — the tool itself; read `--help` output for `secrets`/`secrets list`/`secrets scan` and the top-level command inventory, and its hosted docs (`agentsview.io/guide.md`, `agentsview.io/docs/commands.md`, `agentsview.io/docs/session-api.md`) for the secret-scanning design, storage shape, and HTTP API — no repo source cloned, docs fetched via `curl -L`.
