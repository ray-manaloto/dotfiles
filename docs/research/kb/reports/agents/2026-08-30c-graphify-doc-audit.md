# Staleness audit — graphify instruction prose (2026-08-30)

Status: IN PROGRESS (appended as each finding is settled)

Audit ref: branch `fix/graphify-health-links-schema` @ `325271c` (the links/edges
fix is ALREADY COMMITTED on this branch — so findings are stated against HEAD,
with the pre-fix state noted where the prose describes it).

## Ground truth measured this session (not inherited from the brief)

| Fact | Probe | Result |
|---|---|---|
| `graphify-out/graph.json` top-level keys | `python3 -c "import json;print(sorted(json.load(open('graphify-out/graph.json')).keys()))"` | `['built_at_commit','directed','graph','hyperedges','links','multigraph','nodes']` — **no `edges`**; `links` = 18,785; `hyperedges` = `[]` (0) |
| control arm for the above | same probe asking `'edges' in d, 'links' in d, 'zqwvbn_notakey' in d` | `False True False` — the probe discriminates |
| installed runtime | `uv run --project python python -c "from importlib.metadata import version; print(version('graphifyy'))"` | `0.9.42` (matches the pin at `python/pyproject.toml:9`) |
| **`mise run graphify-health` verdict RIGHT NOW** | `dotfiles-setup graphify health --json` | `{"detail":"build receipt missing","ok":false,"runtime_version":"0.9.42","status":"stale"}` rc=3 |
| **`mise run graphify-query` verdict RIGHT NOW** | `dotfiles-setup graphify query "…"` | rc=3, stderr `graphify: incomplete: graph health is stale: build receipt missing` |
| who writes `build-receipt.json` | `grep -rn "build-receipt\|GraphifyBuildReceipt"` across dotfiles | **only `tests/test_graphify.py`** — zero production writers in this repo. Control arm: same grep shape for `GraphifyStatus` → 2 files, so the grep is not blind |
| the only real writer | `grep -rn` in the knowledge-base clone | `knowledge-base/python/src/kb_setup/graph.py:3061` — part of the **KB's** build pipeline, which dotfiles never runs |
| what graphify actually writes into `graphify-out/` | `ls -la graphify-out/` | `graph.json`, `manifest.json`, `GRAPH_REPORT.md`, `graph.html`, `.graphify_labels.json`, `cache/` — **no `build-receipt.json`** |

---

## FINDING 1 — CONFIRMED-STALE / load-bearing P0: `graphify-first.md`'s whole read path is dead, and the `links` fix does not revive it

**Anchor:** `.claude/rules/graphify-first.md:3-9`

> Before broad source search, run `mise run graphify-health`.
> - `fresh`: use `mise run graphify-query -- "<question>"` and cite returned source paths.
> - `missing`, `stale`, `corrupt`, version drift, warnings, or truncation: say the graph is unavailable and fall back to source.

**Falsifier:** if `graphify_health` can return `FRESH` in this repo, the rule's
`fresh` branch is reachable and the rule is fine.

**Probe (route 1):** `dotfiles-setup graphify health --json` → `status: "stale"`,
`detail: "build receipt missing"`, rc=3.
**Probe (route 2, independent):** `dotfiles-setup graphify query "…"` → rc=3,
`graphify: incomplete: graph health is stale: build receipt missing`.
**Probe (route 3, source):** `graphify.py:159-161` returns `STALE` when
`graphify-out/build-receipt.json` is absent; `ls graphify-out/` shows it absent;
grep shows **no production writer of that file exists in dotfiles** (control-armed).

**Why the caller's framing understates it.** The brief says the `edges`/`links`
schema bug made health report `corrupt`. That was true, and the fix at `325271c`
does remove that verdict — but the checker then falls straight through to
`_receipt_problem` and returns `stale` instead. **Fixing the schema check does not
make the graph usable.** `graphify.py:209` runs unconditionally after the schema
gate, so under `graphify-first.md`'s own doctrine the graph remains "unavailable"
and every session must still fall back to source.

**Load-bearing:** yes, maximally. This rule instructs every session's search
strategy, and `query()` at `graphify.py:297-300` hard-gates on `health.ok`, so
`mise run graphify-query` is **unusable in this repository by construction**, not
by accident of a stale build.

**Correction (two parts, and part 2 is not a doc edit):**
1. The rule is not wrong about the vocabulary — it is describing a path nothing
   can reach. Either dotfiles must gain a receipt writer (port the KB's
   `kb_setup/graph.py:3061` path, or have `graphify update` wrapped by a task that
   writes the receipt), or `_receipt_problem` must be relaxed for a repo that
   builds with plain `graphify update`.
2. Until then `graphify-first.md` must say so out loud, e.g.:
   > `mise run graphify-health` currently reports **`stale` ("build receipt
   > missing")** in this repo — nothing here writes `graphify-out/build-receipt.json`
   > (the only writer is the knowledge-base's `kb_setup.graph` pipeline, #TBD).
   > So `mise run graphify-query` cannot run. Use the raw `graphify query` CLI, or
   > fall back to source, until the receipt gap is closed.

**Second route for the P0:** two independent commands (health, query) plus the
source read plus the directory listing all agree. No disagreement to resolve.

---

## FINDING 2 — INCOHERENT / load-bearing: the `--strict` PreToolUse hook orders sessions to run a command the repo's own doctrine forbids and the repo's own task cannot execute

**Anchor:** the live hook output, observed on every Bash/Read call in this session:

> `MANDATORY: graphify-out/graph.json exists. You MUST run `graphify query "<question>"` before grepping raw files.`

vs `.claude/rules/graphify-first.md:10-12`:

> Never run a global Graphify binary or installer as a substitute for the project
> tasks. The generated skill is reference material; repository tasks and receipts
> are authoritative.

**Why incoherent:** the hook mandates the **raw `graphify query` binary**; the rule
forbids exactly that in favour of `mise run graphify-query`; and `mise run
graphify-query` returns rc=3 (Finding 1). An agent cannot satisfy all three. The
hook wins in practice because it is injected into every tool result while the rule
is one paragraph of eager prose.

**Load-bearing:** yes — it is a PreToolUse injection that changes what every agent
does before every grep, in this repo and in every subagent (the Read-hook variant
explicitly says "This rule applies to subagents too").

**I believe the hook, not the rule**, on the narrow question of what works: raw
`graphify query` is the only invocation with a chance of succeeding today. The rule's
"repository tasks are authoritative" sentence is aspirational until Finding 1 is
closed.

_Further findings appended below as they are settled._

---

## FINDING 3 — REFUTES THE BRIEF: `graphify <platform> install` subcommands DO exist at 0.9.42, so `do-not.md` #8's codex sentence stands

**Brief claim (ground truth #3):** "There is no `graphify <platform> install` subcommand at this version."

**Probe:** `graphify --help` (v0.9.42, `graphify --version` → `graphify 0.9.42`):

```
120:  hook install            install post-commit/post-checkout git hooks (all platforms)
127:  claude install          write graphify section to CLAUDE.md + PreToolUse hook (Claude Code)
131:  codex install           write graphify section to AGENTS.md (Codex)
133:  opencode install        write graphify section to AGENTS.md + tool.execute.before plugin
151:  antigravity install     write .agents/rules + .agents/workflows + skill (Google Antigravity)
```
(20+ platform pairs; full list in the probe output.)

**Verdict:** the brief is REFUTED. `do-not.md:41` — *"`graphify codex install` appends
to the root `AGENTS.md`"* — is corroborated verbatim by the tool's own help line 131.
**Do not weaken that sentence.** The `install --platform P` form and the
`<platform> install` form both exist; they are alternatives, not a replacement.

## FINDING 4 — CONFIRMED-STALE (minor, but it is a ban that can only pass): `do-not.md:38` bans a flag spelling that does not exist

**Anchor:** `.claude/rules/do-not.md:38` — "Never run `graphify hook install` or **`graphify --watch`**."

- `graphify hook install` — REAL (`--help:120`, installs post-commit/post-checkout **git** hooks). Ban justified.
- `graphify --watch` — **no such flag.** `--help:31` shows `watch <path>` as a *subcommand*.

**Why it matters:** a prohibition naming a non-existent spelling is unenforceable
and unfalsifiable — the actually-dangerous invocation, `graphify watch .`, is not
covered by the words as written.
**Correction:** `Never run `graphify hook install` or `graphify watch <path>`.`

## FINDING 5 — FALSE (brief + prose): the "MANDATORY … you MUST run graphify query" nudge is NOT graphify's `--strict` hook and does NOT block anything here

**Brief claim (ground truth #3):** "`--strict` installs a Claude Code project hook
that blocks the first raw file read per session … that is the origin of the
'MANDATORY: run graphify query' PreToolUse message appearing in sessions."

**Probe:** `.claude/settings.json:56,66` wires **`scripts/graphify-hook-guard.sh`**,
a repo-authored wrapper — not graphify's installed hook. Its own header says:

> `scripts/graphify-hook-guard.sh:14-15` — "The nudge is advisory (**soft mode, no
> `--strict`**): it prints a 'query the graph first' reminder that Claude Code
> surfaces as context; **it never blocks a call**."

It shells `mise exec -- graphify hook-guard "$kind"` and `exit 0` unconditionally.

**Control arm:** every Bash/Read call in this audit produced the MANDATORY banner
**and then executed normally** — a blocking hook would have denied at least one.

**Verdict:** the banner's own word "MANDATORY" is graphify's nudge *copy*; the
mechanism is advisory. Anyone editing `do-not.md` or `graphify-first.md` on the
strength of "`--strict` is installed here" would be editing against a false premise.
`--strict` is real (`graphify install --help` documents it) — it is simply **not what
this repo runs**.

## FINDING 6 — INCOHERENT / this is Finding 1's root cause: `currency.toml` says the build stamp is the KB's concern; `graphify.py` hard-requires the KB's build stamp

**Anchor A:** `currency.toml:49-52`
> "No `manifest`/`artifact`/`stamp`: **unlike the knowledge-base, this repo does not
> build a committed graphify corpus** — graphify graphs the dotfiles source on demand
> and `graphify-out/` is gitignored. So step 1 checks the pin, the resolution, and the
> extras here; **the build-stamp checks are the KB's concern.**"

**Anchor B:** `python/src/dotfiles_setup/graphify.py:159-161, 209`
```python
receipt_path = graph_path.with_name(_BUILD_RECEIPT)   # graphify-out/build-receipt.json
if not receipt_path.is_file():
    return HealthResult(GraphifyStatus.STALE, runtime, "build receipt missing")
```

**Which I believe:** `currency.toml` describes the intended design correctly, and
`graphify.py` is the defect. The receipt is written only by
`knowledge-base/python/src/kb_setup/graph.py:3061`, inside the KB's committed-corpus
build — a pipeline dotfiles deliberately does not run. So dotfiles imported the KB's
*type* (`from kb_setup.graph import GraphifyBuildReceipt`) and the KB's *gate*, without
the KB's *writer*.

**Control that proves the graph itself is fine:** the raw binary answers correctly —
`graphify query "what does graphify_health do" --budget 300` → **rc=0**, 60 nodes,
correct `src=python/src/dotfiles_setup/graphify.py` citations. So `stale` is a false
negative about a healthy graph, exactly as `corrupt` was before `325271c`.

## FINDING 7 — CONFIRMED-STALE: the SessionStart currency check tells this repo to run a task that does not exist here

**Probe:** `kb-setup currency check` (the SessionStart hook's step) →
```
[currency] NOT CHECKED against upstream (this is not a pass):
[currency]   graphify: no upstream version has ever been recorded — run `mise run kb-currency` so the offline check can tell whether this pin is behind
rc=0
```
**Probe:** `mise tasks | grep -i currency` → `tool-currency`, `tool-currency-check`.
**No `kb-currency` task exists in dotfiles.** The message is the shared
knowledge-base engine's copy, unadapted for this repo.

**Correction:** the engine should name the caller's own task (`mise run tool-currency`
here), or dotfiles should alias it. As written the remediation is a dead pointer, and
rc=0 means nothing ever escalates it.

**Related, measured:** pin `graphifyy[all]==0.9.42` (`python/pyproject.toml:9`,
released 2026-08-13); latest on PyPI **0.9.53**. Control arm:
`curl pypi.org/pypi/zqwvbn-notapackage-8831/json` → 404, so the fetch discriminates.

## FINDING 8 — CONFIRMED-STALE / load-bearing: **two different graphify versions run in this repo**, and `graphify-hook-guard.sh`'s own comment names the wrong pin source

**Anchor:** `scripts/graphify-hook-guard.sh:9-10`
> "This wrapper resolves graphify at runtime via mise (**host-pinned in `mise.toml`**)"

**Falsifier:** if `mise.toml` declares a graphify tool, the comment is right.

**Probe:**
```
$ grep -rn "graphifyy" mise.toml .config/mise/conf.d/*.toml ~/.config/mise/config.toml
/Users/rmanaloto/.config/mise/config.toml:288:"pipx:graphifyy" = { version = "0.9.53", extras = ["all"], minimum_release_age = "0s" }
mise.toml:55:# extract audio before transcription — it is NOT a pip dep, so `graphifyy[all]`   <- a COMMENT
```
`mise.toml` does **not** pin graphify. The pin is in the **user-global**
`~/.config/mise/config.toml`, which is outside the repo and outside review.

**The measured consequence — the two invocation paths disagree:**
```
$ mise exec -- graphify --version                 -> graphify 0.9.53   # hook-guard's path
$ uv run --project python graphify --version      -> graphify 0.9.42   # mise run graphify-query's path
$ mise ls | grep graphif
pipx:graphifyy   0.9.53   ~/.config/mise/config.toml   0.9.53
```

**Load-bearing:** yes. `graphify-hook-guard.sh:25` runs `mise exec -- graphify
hook-guard "$kind"` — so the nudge injected into **every** tool call in this session
came from **0.9.53**, while `graphify.py:207` demands exactly `"0.9.42"` and would
report `version_drift` for anything else. The script's own header records this exact
class of drift happening once before ("a stale 0.9.23 install dir sat ahead of the
shims under a 0.9.25 pin"); it has recurred in the opposite direction and the comment
was not updated.

**Correction:** `scripts/graphify-hook-guard.sh:9-10` should read "...via mise (pinned
in the **user-global** `~/.config/mise/config.toml`, NOT in this repo — so the hook
can run a different version than `mise run graphify-query`)", and the divergence
should be closed rather than only documented.

## FINDING 9 — CONFIRMED-STALE / a gate that cannot see the thing it asserts: the single-owner dependency contract reads only `mise.toml`

**Anchor:** `python/src/dotfiles_setup/dependency_ownership.py:82`
```python
mise_values = tomllib.loads((repo_root / "mise.toml").read_text())
```
plus `currency.toml:33-34`: *"Graphify is a Python runtime dependency **owned only by
`python/pyproject.toml`**"*.

**Falsifier:** if the audit reads the merged mise configuration, the claim is safe.

**Probe:** the grep above — the module names exactly one config file. Control arm:
`grep -c "def "` on the same file → 7, so the grep is not blind.

**Verdict:** the contract asserts single ownership while reading a single file that
graphify was never going to appear in. The real duplicate owner
(`~/.config/mise/config.toml:288`, at a *different version*) is invisible to it, and
it is the one that wins for every bare `graphify` invocation. The gate is not wrong,
it is **narrower than the sentence in `currency.toml`** — and Finding 8 is the defect
it exists to catch, uncaught.

## FINDING 10 — REFUTED (the brief's #4): the tracked/ignored `.graphify_version` split is deliberate and test-gated, not an inconsistency

**Brief claim (#4):** "`.claude/skills/graphify/.graphify_version` is gitignored on
purpose while `.agents/skills/graphify/.graphify_version` IS tracked — an
inconsistency in the repo's own stated policy."

**Probe:** `tests/test_graphify.py:42-66`,
`test_graphify_runtime_and_skill_stamps_match_project_pin`, binds **three** copies of
the pin:
```python
assert dependency == "graphifyy[all]==0.9.42"                       # python/pyproject.toml
stamp = repo / ".agents/skills/graphify/.graphify_version"
assert stamp.read_text(encoding="utf-8").strip() == version         # the TRACKED stamp
assert f'if runtime != "{version}":' in health_source               # graphify.py:207
```
**Probe:** `ls -la .claude/skills/graphify/` → the ignored path **does not exist on
disk at all**; the tracked one contains `0.9.42`.

**Verdict:** the tracked stamp is a *pin assertion under test*, not per-install state.
The split is coherent. What IS worth fixing is the `.gitignore:67` comment — *"graphify
per-install state (generated by `graphify install`/runs; not source)"* — which invites
exactly this misreading. Suggested addition: `# (the .agents/ sibling is deliberately
TRACKED — it is a pin stamp asserted by tests/test_graphify.py:42.)`

**Hazard worth flagging anyway:** `graphify --help:151` shows `antigravity install`
writes "`.agents/rules` + `.agents/workflows` + skill" — so a future
`graphify antigravity install` run in this repo could **overwrite** the hand-authored
`.agents/skills/graphify/SKILL.md` and its tracked stamp. `do-not.md` #8's
"throwaway directory outside this repo" ban already covers it; it is worth naming
`.agents/` explicitly there.

## FINDING 11 — REFUTED (I suspected staleness, the memory is right): `--graph=<path>` is still ignored at 0.9.53

**Anchor:** memory `feedback_graphify_attached_graph_flag` — probed at graphify
**0.9.25**, i.e. an inherited measurement 28 releases old.

**Re-probe, both arms, from a scratch dir with no `graphify-out/`:**
```
ARM A  graphify query "graphify_health" --graph=/abs/.../graph.json --budget 100  -> rc=1  (no output)
ARM B  graphify query "graphify_health" --graph  /abs/.../graph.json --budget 100  -> rc=0
       Graph: /Users/.../graphify-out/graph.json (13344 nodes) | BFS depth=2 | 89 nodes found
```
The memory's claim **holds at 0.9.53**. Report it as still-current rather than
re-verifying it again next session.

## FINDING 12 — INCOHERENT: `.claude/CLAUDE.md` tells you to run the raw binary; `graphify-first.md` forbids it

**Anchor A:** `.claude/CLAUDE.md` § graphify —
> "Codebase questions: run `graphify query "<question>"` first when
> `graphify-out/graph.json` exists"

**Anchor B:** `.claude/rules/graphify-first.md:10-12` —
> "Never run a global Graphify binary or installer as a substitute for the project
> tasks. … repository tasks and receipts are authoritative."

Both are eager-loaded every session. **They give opposite instructions**, and the
PreToolUse nudge sides with Anchor A. This is Finding 2's conflict at its source.

**Which I believe:** Anchor A describes what works today (Finding 1 makes Anchor B's
route return rc=3); Anchor B describes the intended posture. One of the two must be
edited, and the choice depends on whether the receipt gap (Finding 1) is closed.

**Also in that section, verified CORRECT — do not "fix":**
- "After changing code: `graphify update .` (AST-only, no API cost)" — `graphify
  --help:31`: *"update `<path>` re-extract code files and update the graph (**no LLM
  needed**)"*. CONFIRMED.
- "`graphify-out/` is gitignored" — true but imprecise: `.gitignore:65` un-ignores
  `!graphify-out/wiki/`. Cosmetic.

## FINDING 13 — NEEDS-VERIFICATION (out of my scope to settle): the generated graphify SKILL.md is 714 lines / 41,300 bytes against a documented 500-line / 32,000-byte `skill` budget

`wc -lc .claude/skills/graphify/SKILL.md` → `714  41300`, vs
`.claude/rules/md-size-budgets.md` § The budgets, `skill` class = **500 lines /
32,000 bytes**. Yet `uv run --project python kb-setup md-budget` exits **rc=0**
("62 instruction files checked"). Either the shared engine excludes generated
skills, or the rule's table over-states what is enforced.
**Probe that would settle it:** have the engine print its file list (it has no
`--json`; `kb-setup md-budget --json` fails to parse), or read
`kb_setup/md_budget.py`'s glob in the knowledge-base clone.

---

## Sentences that must change once the `graphify install` containment probe lands

The sibling probe (`docs/research/kb/reports/agents/2026-08-30c-graphify-install-probe.md`)
owns the measurement. `do-not.md:34-42` is the text; the mechanical edit per outcome:

| Probe outcome | Sentences to change |
|---|---|
| Bare `graphify install` still mutates `~/.claude` (~43 KB + `# graphify` H1) | **none** — `do-not.md:34-37` stands as written |
| It no longer writes `~/.claude/CLAUDE.md` | rewrite `do-not.md:35-36` ("~43 KB of skill files and a `# graphify` H1 appended to `~/.claude/CLAUDE.md`") to the measured artifact set, and re-date the claim |
| `CLAUDE_CONFIG_DIR` now DOES contain the write | delete `do-not.md:36-37` ("`CLAUDE_CONFIG_DIR` is NOT containment … that write is hardcoded") and replace with the measured containment recipe |
| `--project` alone now contains everything | delete the ⚠️ paragraph `do-not.md:40-43` **except** the `graphify codex install` sentence, which Finding 3 independently confirms via `graphify --help:131` |
| `graphify codex install` no longer touches root `AGENTS.md` | edit `do-not.md:41` only; help line 131 currently says otherwise, so require a real invocation, not a help read |

Independent of the probe, `do-not.md:38` needs the Finding 4 fix
(`graphify --watch` → `graphify watch <path>`).

---

## Re-verified before reporting

Re-read at write-up time; HEAD unchanged at `325271c` on
`fix/graphify-health-links-schema`; `graphify health` re-run gave the identical
`stale / build receipt missing` JSON. SHA-1 of every audited artifact, recorded so a
later reader can tell whether it moved:

```
ef89effb70ab8d1149c3dcab1df8403721919170  .claude/rules/graphify-first.md
dbcab5b5d20b3f7fd309c2c167e487d595908ca7  .claude/rules/do-not.md
68362d54712379c4a538a7498183085f8d7c13f9  .claude/CLAUDE.md
53a9d1662a95ea0346eaca76074500235ef3ab6e  python/src/dotfiles_setup/graphify.py
f1a9dbe4a93ed015224e87bb304b03d860b79ada  .claude/settings.json
c51de00abb0e50d94045c43f89e7091bdbdf892e  scripts/graphify-hook-guard.sh
1d22443a24d7016af135fb0fb1144f37d72e02fb  currency.toml
562691bf7b611ef02caab4f4a8d52c2573efe2d4  .gitignore
```
Nothing had moved. **Caveat the caller must apply:** the lane fixing the schema
checker may push onto this branch after this timestamp; Findings 1 and 6 are about
`_receipt_problem`, which that fix does not touch, so they survive — but re-read
`graphify.py` before acting on any anchor line number.

**Correction to my own Finding 2 heading:** it says "the `--strict` PreToolUse hook".
Finding 5 refutes that — the hook is `scripts/graphify-hook-guard.sh` in soft mode.
Read Finding 2's heading as "the graphify nudge hook".

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the audited repo
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) — located the only real `build-receipt.json` writer (`kb_setup/graph.py:3061`) and the shared `kb-setup currency` / `md-budget` engines
- [Graphify-Labs/graphify](https://github.com/Graphify-Labs/graphify) — upstream named in `currency.toml:37`; version/latest checked via PyPI `graphifyy`, CLI surface read from the installed `--help`
