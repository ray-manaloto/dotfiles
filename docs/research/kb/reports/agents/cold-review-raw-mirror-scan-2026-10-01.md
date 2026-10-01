# Cold review — raw-mirror scan exemptions (`3a861923..12e58433`)

- Reviewer: cold-reviewer (Opus), diff-only, by ref.
- Subject: `git diff 3a861923efe6..12e58433d069`
  (2 commits: `ef049b5e`, `12e58433`; full SHAs omitted — a 40-hex SHA in a file that says "sourcegraph" trips gitleaks' legacy `sourcegraph-access-token` form, measured on this very report; branch `fix/raw-mirror-scan-exemptions`).
- Memory: consulted (`mutation_harness.md`, `vendored_tree_and_workflow_order_review.md`, `repo_gate_locations.md`).
- Status: COMPLETE (2026-10-01).

## Brief domain (bounded)

1. Every new `.gitleaks.toml` `[[allowlists]]` entry (4 entries) — can it suppress a real secret?
2. The stub/pairs exemption regex (2 scripts, 3 call sites) — does it exempt anything outside `docs/research/kb/raw/`?
3. `claudeMdExcludes` (1 pattern) — can it exclude a memory file we want loaded?
4. `tests/test_gitleaks_raw_mirror_allowlist.py` — red for the right reason; free of matchable literals?

## Findings

| # | Severity | Claim | file:line | Evidence |
|---|---|---|---|---|
| F1 | MEDIUM | Entry 1 (`regexTarget = "line"`) suppresses EVERY `sourcegraph-access-token` finding on any `docs/research/kb/raw/` line that also carries a github.com commit/tree/blob URL — including `sgp_`-prefixed real-format tokens (both formats), which can never be a git SHA. In a minified/one-line file the "line" is the whole file. Both scanners. Fix (armed): `regexes = ['''^[0-9a-f]{40}$''']` with the default secret target. | `.gitleaks.toml:94-100` | E1, E2, E5 |
| F2 | LOW | For betterleaks 1.9.0, entry 1 has NO false-positive benefit at all (betterleaks never flags the bare 40-hex SHA), so its only effect there is suppressing prefixed `sgp_` tokens. | `.gitleaks.toml:92-100` | E1 (`c1_ctl_sgp_different_line`: betterleaks reports line 3 only) |
| F3 | MEDIUM | The new pytest only plants a `github-pat`, a rule no raw-mirror entry targets, so it catches the "made global" trap but is blind to every WITHIN-rule widening: dropping entry 2's `regexes` or its `condition = "AND"` (default is OR), dropping entry 1's `regexes`, or dropping entry 3's `condition` all stay 6/6 green while both scanners go blind to `generic-api-key` / `sourcegraph-access-token` across the raw tree. | `tests/test_gitleaks_raw_mirror_allowlist.py:127-139` | E3, E4 |
| F4 | LOW | The section header says the content allowlists are "scoped to the mirror tree"; entry 4 has no `paths`, so it is repo-wide — betterleaks now suppresses a `my_password` generic-password finding in `python/src/` (HEAD rc=0, parent rc=1). Impact is nil (exact placeholder value, and `paths` would trigger the gitleaks trap), but the clause is false: narrow it to "entries 1-3". | `.gitleaks.toml:81-83`, `:127-129` | E1 (`c4` rows) |
| F5 | LOW | Test docstring claims "Each test plants a real-shaped token"; 2 of 6 do (`:127`, `:134`). Entry 4 — the only entry betterleaks needs on its own — has no automated coverage at all: gitleaks has no `generic-password` rule (E1 ctl row: random password in `python/src` → gitleaks rc=0 under defaults) and betterleaks is host-only (`mise.toml:16-21`), so deleting entry 4 keeps pytest green; only the host hk `betterleaks_verbatim_trees` step would notice. | `tests/test_gitleaks_raw_mirror_allowlist.py:8-14` | E1, `mise.toml:16-21`, `hk.pkl:348-350` |
| F6 | INFO (pre-existing; ticket, not this diff) | Both stub/pairs scripts silently SKIP any CLAUDE.md/AGENTS.md whose path has a non-ASCII byte: `git ls-files` quotes it (`core.quotePath` unset → default true), so the line ends in `"` and `(^|/)CLAUDE\.md$` never matches. Identical in parent and HEAD. | `scripts/check-claude-md-stub.sh:55`, `scripts/check-claude-agents-md-pairs.sh:39,43` | E4 |

## Evidence log

### E1 — scanner arms, HEAD / parent / defaults configs (runtime-built random tokens, scratch only, `--redact`)

Harness: `<scratchpad>/arms/build_and_scan.py`; every row ran `mise exec -- <tool> dir --no-banner --redact -c <cfg> -f json -r <out> <tree>` with cwd = repo root; rc captured from the subprocess. gitleaks 8.30.1, betterleaks 1.9.0 (`mise exec -- … version`). Fixture layout `docs/research/kb/raw/zz-arm/...`; the sourcegraph keyword line is present in every c1 case.

| Case | HEAD gitleaks | HEAD betterleaks | parent `3a861923` gitleaks / betterleaks | defaults gitleaks / betterleaks |
|---|---|---|---|---|
| c0 judged FPs (test's own fixture shape) | rc=0, 0 | rc=0, 0 | 1 / 1 (4 findings each) | 1 / 1 |
| c1 `sgp_`+40hex on SAME line as a commit URL, in raw | **rc=0, 0** | **rc=0, 0** | 1 / 1 (`sourcegraph-access-token` L2) | 1 / 1 |
| c1 new-format `sgp_<16hex>_<40hex>` same line, in raw | **rc=0** | **rc=0** | 1 / 1 | 1 / 1 |
| c1 one-line JSON, URL ~4 KB before the token, in raw | **rc=0** | **rc=0** | 1 / 1 | 1 / 1 |
| ctl: token on a DIFFERENT line from the URL, in raw | rc=1 (L3) | rc=1 (L3) | 1 (L2,L3) / 1 (L3) | same |
| ctl: same line, OUTSIDE raw (`docs/research/kb/reports/`) | rc=1 | rc=1 | 1 / 1 | 1 / 1 |
| ctl: token alone in raw | rc=1 | rc=1 | 1 / 1 | 1 / 1 |
| PAT on same line as commit URL, in raw | rc=1 `github-pat` | rc=1 `github-pat` | 1 / 1 | 1 / 1 |
| generic api key on the SAME line as the minisign key | rc=1 | rc=1 | 1 / 1 | 1 / 1 |
| generic api key on a non-`"key"` line of a showreel capture | rc=1 (L3) | rc=1 (L3) | 1 (L2,L3) | 1 (L2,L3) |
| `my_password` in `python/src/x.py` (outside raw) | rc=0 | **rc=0** | 0 / 1 (`generic-password`) | 0 / 1 |
| ctl: random password in `python/src/x.py` | rc=0 | rc=1 | 0 / 1 | 0 / 1 |

The controls discriminate: the only variable between the suppressed c1 row and its rc=1 controls is the URL sharing the token's line (or the path being inside raw). So F1 is entry 1, not a broken probe.

### E2 — config mutations and the candidate fix, same harness (gitleaks / betterleaks rc)

| Config | c0 FPs | sgp same-line raw | sgp alone raw | sgp same-line outside raw | PAT in raw | generic in raw | generic in capture (non-key line) |
|---|---|---|---|---|---|---|---|
| HEAD | 0 / 0 | **0 / 0** | 1 / 1 | 1 / 1 | 1 / 1 | 1 / 1 | 1 / 1 |
| m1: entry 1 `targetRules` deleted (GLOBAL + paths + AND) | 0 / 0 | 0 / 0 | **0** / 1 | 1 / 1 | **0** / 1 | **0** / 1 | **0** / 1 |
| m2: entry 2 `regexes` deleted | 0 / 0 | 0 / 0 | 1 / 1 | 1 / 1 | 1 / 1 | **0 / 0** | **0 / 0** |
| m3: entry 2 `condition = "AND"` deleted (default OR) | 0 / 0 | 0 / 0 | 1 / 1 | 1 / 1 | 1 / 1 | **0 / 0** | **0 / 0** |
| m4: entry 1 `regexTarget`+`regexes` deleted | 0 / 0 | 0 / 0 | **0 / 0** | 1 / 1 | 1 / 1 | 1 / 1 | 1 / 1 |
| m5: entry 3 `condition` deleted | 0 / 0 | 0 / 0 | 1 / 1 | 1 / 1 | 1 / 1 | 1 / 1 | **0 / 0** |
| m6: entry 1 `condition` deleted | 0 / 0 | 0 / 0 | **0 / 0** | **0 / 0** | 1 / 1 | 1 / 1 | 1 / 1 |
| **f1 (candidate fix): entry 1 → `regexes = ['''^[0-9a-f]{40}$''']`, default secret target** | **0 / 0** | **1 / 1** | 1 / 1 | 1 / 1 | 1 / 1 | 1 / 1 | 1 / 1 |

- m1 re-derives the caller's trap claim for gitleaks 8.30.1 (whole raw path blinded). **betterleaks 1.9.0 is NOT blinded by m1** — it honours AND on a global entry — so the trap is gitleaks-specific; the comment at `.gitleaks.toml:85-89` scopes it to gitleaks correctly.
- f1 keeps every judged FP suppressed in both scanners and re-exposes both `sgp_` formats on a URL line, including the one-line JSON. Residual of f1 (stated, not hidden): a bare lowercase 40-hex legacy-format Sourcegraph token anywhere in raw is suppressed — that form is byte-indistinguishable from a git SHA, which is the FP class the entry exists for.

### E3 — the new pytest against each mutation (scratch `git worktree` at `12e58433`, `.gitleaks.toml` replaced, restored with `git -C wt checkout --`)

Command: `uv run --project python pytest <wt>/tests/test_gitleaks_raw_mirror_allowlist.py -q -p no:cacheprovider`; each mutation's application asserted with `git diff --quiet` (non-empty) and the pristine row asserted empty.

| Config | rc | Result | Red tests |
|---|---|---|---|
| pristine (control) | 0 | 6 passed | — |
| m1 entry 1 made global | 1 | 3 failed | planted-in-mirror, planted-in-capture, structural |
| m2 entry 2 `regexes` deleted | **0** | **6 passed** | none — scanners blind to generic-api-key in raw (E2) |
| m3 entry 2 `condition` deleted | **0** | **6 passed** | none — same blindness |
| m4 entry 1 `regexes` deleted | **0** | **6 passed** | none — scanners blind to sourcegraph in raw |
| m5 entry 3 `condition` deleted | **0** | **6 passed** | none — blind to generic-api-key in captures |
| m6 entry 1 `condition` deleted | 1 | 1 failed | commit-sha-outside-raw |
| f1 candidate fix | 0 | 6 passed | — (the fix is compatible with the shipped test) |

So the test fails for the right reason on the "made global" class (question 4a: yes), but 4 of 6 realistic within-rule widenings are invisible to it (F3). A planted `generic-api-key`-shaped value and a planted `sgp_` token on a commit-URL line (both built at runtime) would close m2/m3/m4/m5 and F1's regression direction.

### E4 — stub/pairs exemption regex (question 2), real scripts from each ref in a scratch `git init` repo

Paths staged (each CLAUDE.md non-stub, no sibling): `docs/research/kb/raw/m/`, `docs/research/kb/raw/` (root), `docs/research/kb/raw/.claude/`, `docs/research/kb/raw/sp ace/`, `docs/research/kb/raw/é/`, `docs/research/kb/rawx/`, `xdocs/research/kb/raw/`, `a/docs/research/kb/raw/`, `.claude/x/`; AGENTS.md-only at `docs/research/kb/raw/agentsonly/` and `docs/research/kb/rawy/`.

| Script | parent `3a861923` | HEAD `12e58433` | Difference |
|---|---|---|---|
| `check-claude-md-stub.sh` | rc=1, 7 flagged | rc=1, 3 flagged (`a/docs/...raw`, `rawx`, `xdocs/...`) | exactly the 4 paths beginning `docs/research/kb/raw/` |
| `check-claude-agents-md-pairs.sh` | rc=1, 9 flagged | rc=1, 4 flagged (+ `rawy/AGENTS.md`) | exactly the 5 paths beginning `docs/research/kb/raw/` |

Answer to question 2: **no** — the exemption drops only paths whose first segments are `docs/research/kb/raw/`; a prefix-sibling (`rawx`, `rawy`), a nested non-root occurrence (`a/docs/...`) and a leading-substring (`xdocs/...`) are all still checked. The case variant `docs/research/kb/Raw/` collapsed onto `raw/` on this case-insensitive APFS volume, so it could not be staged; the grep is case-sensitive, so on Linux it stays checked (regex semantics, not run — UNVERIFIED by execution). The `é` path is invisible to BOTH refs (F6).

### E5 — `claudeMdExcludes` (question 3)

- Matcher, read from the installed binary (`~/.local/share/claude/versions/2.1.286`, mmap search): schema text "Patterns are matched against absolute file paths using picomatch. Only applies to User, Project, and Local memory types"; code `Not.default(n,{dot:!0})` gated on `g==="User"||g==="Project"||g==="Local"`. So `**` DOES cross dot segments (`.claude/worktrees/...`).
- picomatch arm (`{dot:true}`, the openspec-vendored picomatch — a different copy from CC's bundle, same library) over 73 paths: every tracked `CLAUDE.md`/`CLAUDE.local.md`/`AGENTS.md`/`.claude/rules/**/*.md` in dotfiles AND knowledge-base (absolute), plus user-level files, plus 7 synthetic controls. **Excluded: 4, all synthetic raw-tree paths** (`raw/CLAUDE.md`, `raw/m/.claude/CLAUDE.md`, the held packslip path, a worktree-embedded `raw/m/.claude/rules/r.md`). Not excluded: synthetic `docs/research/kb/rawx/CLAUDE.md`, `docs/research/kb/CLAUDE.md`, `.claude/worktrees/agent-x/CLAUDE.md`, and all 66 real files.
- No tracked instruction file `@`-imports anything under `docs/research/kb/raw` (`git grep '@[^ ]*docs/research/kb/raw'` → 0; control `^@AGENTS\.md` in CLAUDE.md files → 6). knowledge-base has no `docs/research/kb/raw/` (0 tracked files).
- Answer to question 3: **no** wanted memory file is excluded today. The implementer's live two-arm session test (report `implement-raw-mirror-scan-2026-10-01.md` § Round b) is consistent with the binary's matcher; I did not re-run a live session (UNVERIFIED by me, inherited).

### E6 — literal hygiene (question 4b)

Single-file scans, both tools × {repo `.gitleaks.toml`, defaults-only}: the new test file, a renamed copy of `.gitleaks.toml`, and the implementer report → all rc=0, 0 findings (12 runs). Control: a runtime-built PAT in a scratch `.py` scanned the same way → gitleaks rc=1, betterleaks rc=1 `github-pat`. `.gitleaks.toml` scanned in place reports "scanned ~0 bytes" for both (the default allowlist skips the config path). Answer: the test is free of matchable literals.

### E7 — `(^|/)docs/research/kb/raw/` unanchored path regex on the real working tree

`find . -type d -path '*/docs/research/kb/raw'` → the repo raw dir (control), two `.claude/worktrees/agent-*/docs/research/kb/raw`, and `.agent/kb/raw/held-2026-09-30/docs/research/kb/raw`. The extra three are under the pre-existing GLOBAL path allowlist (`.gitleaks.toml:17-23`), so the `(^|/)` alternative blinds nothing new today.

## Required questions

- **Q-FRESH:** N/A — the diff adds static config, a grep filter and a test; no decision→action pair reads state that can change between the decision and the action.
- **Q-SCOPE:** F1-F5 are introduced by this diff (in scope). F6 is pre-existing in both scripts → ticket. Scope note bearing on F1's severity: `docs/research/kb/raw/` is NOT only vendored mirrors — `research-sweep-run.js:117` writes fetched GitHub/web pages to `docs/research/kb/raw/<slug>/links/`, and `session-2026-09-22d/skilloverrides-probe/*.out` is agent probe output. So entry 1's line suppression covers fetched GitHub pages (dense with commit URLs) and probe output, the exact tree `.gitleaks.toml:35-44` says a leak is "most likely to land".
- **Q-CLAIM** (operator-facing strings this diff adds):

| Clause | Enforcing line | Outcome |
|---|---|---|
| entry 1 description "40-hex git SHAs inside github.com commit/tree/blob URLs" | none — the entry suppresses ANY sourcegraph finding on such a line | F1 |
| header "scoped to the mirror tree" | entries 1-3 `paths`; entry 4 has none | F4 |
| TRAP "Rule-scoped entries honour AND in both gitleaks and betterleaks" | E2 m2-m6 (AND changes outcomes in both tools) | holds |
| TRAP "the pytest … plants a token to catch exactly that" | test `:127-139`, `:150-158`; E3 m1 red | holds |
| entry 2 "Exact match only" | `^…$` anchors, secret target; E1 generic-on-minisign-line rc=1 | holds |
| entry 4 "no `paths` (the P1 trap needs `paths`)" | `.gitleaks.toml:127-129` | holds; "P1" is an undefined spec label in this file (cosmetic) |
| test docstring "Each test plants a real-shaped token" | 2 of 6 tests | F5 |
| `.claude/CLAUDE.md:7-8`, `hk.pkl:768-781`, script headers: "`docs/research/kb/raw/**` is exempt" | `scripts/check-claude-md-stub.sh:55`, `scripts/check-claude-agents-md-pairs.sh:39,43` | holds (E4) |

## Answers to the four brief questions

1. **Allowlist entries.** Entry 1 CAN suppress a real secret: a real-format `sgp_` Sourcegraph token on any raw-tree line that also carries a github.com commit/tree/blob URL (whole file if minified) — both scanners (F1, MEDIUM). Entries 2 and 3 cannot beyond their exact/anchored values (E1). Entry 4 is repo-wide but suppresses only the literal placeholder (F4, LOW). No new entry is global-with-`paths`; the trap is real for gitleaks 8.30.1 and absent in betterleaks 1.9.0 (E2 m1).
2. **Stub/pairs regex.** Exempts nothing outside `docs/research/kb/raw/` (E4).
3. **`claudeMdExcludes`.** Excludes no wanted memory file; `dot:true` means it also covers worktree-embedded raw paths (E5).
4. **New pytest.** Goes red when an entry is made global (E3 m1: 3 failures, for the right reason) and is literal-clean (E6), but is blind to within-rule widening (F3) and has no coverage of entry 4 (F5).

## Verdict

**SHIP-WITH-FIXES.** Nothing weakens scanning outside `docs/research/kb/raw/`, and the stub/pairs/`claudeMdExcludes` scopes are exact. Inside the raw tree, F1 suppresses more than the SHA false positive it was written for. The fix is one line, armed in E2 (f1 column) and compatible with the shipped test (E3 f1 row: 6 passed):

```toml
# entry 1: drop `regexTarget = "line"` and the URL regex; keep condition/targetRules/paths
regexes = ['''^[0-9a-f]{40}$''']
```

Pair it with F3's two planted cases (a runtime-built `generic-api-key`-shaped value in the mirror; a runtime-built `sgp_` token on a commit-URL line), which would turn m2/m3/m4/m5 and an F1 regression red. F4/F5 are comment edits. F6 → ticket.

## GitHub repos touched

_None._ (All evidence is local: the installed gitleaks 8.30.1 / betterleaks 1.9.0 / Claude Code 2.1.286 binaries and the offline `$CC` corpus.)
