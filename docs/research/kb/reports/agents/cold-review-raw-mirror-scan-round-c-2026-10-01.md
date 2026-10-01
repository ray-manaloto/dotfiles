# Cold review round c — raw-mirror scan exemptions (`12e58433..61a96253`)

- Reviewer: cold-reviewer (Opus), diff-only, by ref. NARROW, bounded round.
- Subject: `git diff 12e58433..61a96253` (one commit; full SHAs omitted — a 40-hex SHA in a file that says "sourcegraph" trips gitleaks' legacy form). Branch `fix/raw-mirror-scan-exemptions`; working tree `.gitleaks.toml` and the test file are byte-identical to the subject (`git diff --quiet 61a96253 -- …` rc=0).
- Prior round: `docs/research/kb/reports/agents/cold-review-raw-mirror-scan-2026-10-01.md` (F1-F6).
- Memory: consulted (`gitleaks_allowlist_review.md`, `mutation_harness.md`).
- Tools: gitleaks 8.30.1, betterleaks 1.9.0 (`mise exec -- … version`).
- Status: COMPLETE (2026-10-01).

## Domain (bounded — three questions, nothing else)

1. F1 closed? planted `sgp_` (both gitleaks shapes) on a commit-URL line + minified JSON, both scanners, new config; held/known FPs still clear.
2. F3 closed? the four previously-green mutations (m2, m3, m4, m5) now red; any NEW in-rule widening of entries 1-3 that stays green.
3. Any new defect in the round-c diff.

## Findings

| # | Severity | Claim | file:line | Evidence |
|---|---|---|---|---|
| R1 | LOW | 8 of 13 new in-rule widenings of entries 1-3 keep the pytest green while each hides a real-shaped value (both scanners where the rule exists): entry 3 losing `\s*$` (the F1 co-located-secret class returns), entry 3 `paths` deleted (repo-wide) or widened to the raw tree, entry 3 value class widened, entry 2 DocSearch regex generalised to 32-hex, entry 1 `(?i)`, entry 1 path without trailing `/`, entry 2 `paths` deleted (nil impact). No planted case varies path scope or sits on an entry-3 `"key"` line. Ticket: plant (a) a `"key": "<64hex>"` line outside raw and (b) in a non-capture raw file, (c) a non-hex value on a capture `"key"` line, (d) a second credential on a capture key line, (e) a 32-hex generic value in raw. | `tests/test_gitleaks_raw_mirror_allowlist.py:178-209`; `.gitleaks.toml:101-128` | E2 widening table |
| R2 | LOW | Config comment says the pytest catches "an entry widened within its own rule"; true only for the enumerated deletions (regexes/condition/line target), false for R1's 8. Narrow the clause. | `.gitleaks.toml:91-92` | E2, E3 |
| R3 | LOW | Test docstring (and the commit message and the implementer report) says gitleaks 8.30.1's rule has two `sgp_` shapes; the shipped regex has three (`sgp_local_<40hex>`), and the parametrize covers two. No hole: entry 1 does not suppress the third shape (E1). | `tests/test_gitleaks_raw_mirror_allowlist.py:70-71`, `:178-180` | gitleaks binary rule text (E1); E1 `sgp_local_` row |
| R4 | INFO | Entry 1 comment says the bare form fires in files mentioning the vendor name; the rule's keywords also include `sgp_`. Behaviour unaffected. | `.gitleaks.toml:94-95` | rule `keywords` (E1) |

## Evidence log

### E1 — Q1: F1 closure, scanner arms (gitleaks 8.30.1 / betterleaks 1.9.0)

Harness: `<scratchpad>/arms-c/scan_c.py` (round-b harness re-cut). Every token is random and built at runtime under the
scratchpad; every run is `mise exec -- <tool> dir --no-banner --redact -c <cfg> -f json -r <out> <tree>` from the repo root,
rc read from the subprocess. Configs: `head` = `git show 61a96253:.gitleaks.toml`, `prev` = `git show 12e58433:.gitleaks.toml`
(the F1 config, control), `defaults` = `useDefault` only. Betterleaks validation is opt-in (`--validation`, from
`betterleaks dir --help`), so no planted value left the host. Keyword line (`source`+`graph`) present in every case.

Rule shapes, read from the binaries (`strings`): gitleaks `sourcegraph-access-token` is
`(?i)\b(\b(sgp_(?:[a-fA-F0-9]{16}|local)_[a-fA-F0-9]{40}|sgp_[a-fA-F0-9]{40}|[a-fA-F0-9]{40})\b)…`, `entropy = 3`, keywords
`sgp_` + the vendor name — so THREE prefixed shapes (`<16hex>_`, `local_`, none) plus the bare legacy form. betterleaks'
rule has the three prefixed shapes and NO bare form.

| Case (all under `docs/research/kb/raw/` unless noted) | head gl | head bl | prev gl / bl | defaults gl / bl |
|---|---|---|---|---|
| judged FPs (round-b fixture shape) | rc=0, 0 | rc=0, 0 | 0 / 0 | 1 (4) / 1 (4) |
| `sgp_<40hex>` on the SAME line as a commit URL | **rc=1**, 1 (L2) | **rc=1**, 1 (L2) | 0 / 0 | 1 (2) / 1 (1) |
| `sgp_<16hex>_<40hex>`, same line | **rc=1**, 1 | **rc=1**, 1 | 0 / 0 | 1 / 1 |
| `sgp_local_<40hex>`, same line (third shape) | **rc=1**, 1 | **rc=1**, 1 | 0 / 0 | 1 / 1 |
| uppercased `SGP_<40HEX>`, same line | **rc=1**, 1 | **rc=1**, 1 | 0 / 0 | 1 / 1 |
| minified one-line JSON, URL ~4 KB before `sgp_<40hex>` | **rc=1**, 1 (L1) | **rc=1**, 1 | 0 / 0 | 1 (2) / 1 |
| minified JSON, `sgp_<16hex>_<40hex>` | **rc=1**, 1 | **rc=1**, 1 | 0 / 0 | 1 / 1 |
| minified JSON, token followed by an escaped `\n` | **rc=1**, 1 | **rc=1**, 1 | 0 / 0 | 1 / 1 |
| ctl: `sgp_` alone in raw | rc=1 | rc=1 | 1 / 1 | 1 / 1 |
| ctl: `sgp_` on URL line, OUTSIDE raw | rc=1 (2) | rc=1 | 1 / 1 | 1 / 1 |
| stated trade-off: bare LOWERCASE 40-hex in raw | rc=0 | rc=0 | 1 / 0 | 1 / 0 |
| trade-off control: same, outside raw | rc=1 | rc=0 | 1 / 0 | 1 / 0 |
| bare UPPERCASE 40-hex in raw | rc=1 | rc=0 | 1 / 0 | 1 / 0 |
| 8 held files (`.agent/kb/raw/held-2026-09-30`, link-4.md at `raw/cbm-link4/`) | rc=0, 0 | rc=0, 0 | 0 / 0 | 1 (44) / 1 (5) |
| held tree + `sgp_<16hex>_<40hex>` appended on a commit-URL line of link-4.md | **rc=1**, 1 (L1182 only) | **rc=1**, 1 | 0 / 0 | 1 (46) / 1 (6) |

Real tree, `head` config: `gitleaks dir .` rc=0 (44.58 MB); `betterleaks dir docs/research/kb` rc=0; `… docs/research/runs` rc=0.
Control: `defaults` over the tracked `docs/research/kb/raw` → gitleaks rc=1 (curl-auth-header 1, generic-api-key 2),
betterleaks rc=1 (curl-auth-header 1, generic-api-key 1, generic-password 1), so the clean head runs are not a blind probe.

Reading: every planted prefixed token that `prev` hid (rc=0 in both tools) is reported under `head` in both tools, with the
commit-URL SHA on the same line still suppressed (head n=1 vs defaults n=2). The judged and held FPs still clear. The
residual is exactly the stated trade-off (`.gitleaks.toml:99-100`): lowercase bare 40-hex in raw, gitleaks only — betterleaks
never reports that form, so entry 1 is now inert in betterleaks (round-b F2 is moot, not a hole). **F1: CLOSED.**

### E2 — Q2: F3 closure, the subject's pytest under each mutation

Harness: scratch `git worktree add --detach <scratchpad>/arms-c/wt 61a96253`; per row the mutated config is copied over
`wt/.gitleaks.toml`, application asserted with `git -C wt diff --quiet` (must be rc=1), then
`uv run --project python pytest wt/tests/test_gitleaks_raw_mirror_allowlist.py -q -p no:cacheprovider -rf` from the repo
root, rc read from the subprocess, then `git -C wt checkout -- .gitleaks.toml` and a clean-tree assert. Driver:
`<scratchpad>/arms-c/mutate_pytest.py`. PRISTINE rows first and last: **10 passed, rc=0** both times (non-zero count, so the
harness is live).

**The four previously-green mutations (round-b E3) — all RED now:**

| Mutation | round b | round c rc | Red tests |
|---|---|---|---|
| m2 entry 2 `regexes` deleted | 6 passed | **1** | generic-api-key[mirror], [showreel-capture] |
| m3 entry 2 `condition` deleted | 6 passed | **1** | generic-api-key[mirror], [showreel-capture] |
| m4 entry 1 `regexes` deleted | 6 passed | **1** | sgp[40hex], sgp[16hex-40hex] |
| m5 entry 3 `condition` deleted | 6 passed | **1** | generic-api-key[showreel-capture] |

Controls / claimed rows: m6 entry 1 `condition` deleted → rc=1 (sgp ×2, commit-sha-outside); m8 entry 3 `regexes` deleted →
rc=1 (generic[showreel-capture]); entry 3 `targetRules` deleted (global trap) → rc=1 (PAT-in-capture, generic[capture],
structural) — matches the implementer's table; w15 entry 3 `regexTarget` deleted (a NARROWING) → rc=1, judged-FP test red
(the capture SHA is then reported). **F3: CLOSED** for every mutation it named, plus the F1 revert (w7 below).

**New in-rule widenings of entries 1-3 (targetRules kept) — 13 mutations, enumerated before running:**

| # | Entry | Widening | pytest | Scanner arm under the mutation (head reports it; mutation hides it) |
|---|---|---|---|---|
| w1 | 1 | regex unanchored `[0-9a-f]{40}` | **red** (sgp ×2) | — |
| w2 | 1 | `^` dropped | **red** (sgp ×2) | — |
| w3 | 1 | `(?i)` added | green | bare UPPERCASE 40-hex in raw: gitleaks 1 → **0** (betterleaks never reports the bare form) |
| w4 | 1 | `paths` deleted | **red** (commit-sha-outside) | — |
| w5 | 1 | path `…/kb/raw` (no trailing `/`) | green | bare 40-hex in `docs/research/kb/rawx/`: gitleaks 1 → **0** (no such dir today) |
| w6 | 1 | path widened to `(^|/)docs/research/` | **red** (commit-sha-outside) | — |
| w7 | 1 | F1 reverted (line target + URL regex) | **red** (sgp ×2) | — |
| w9 | 2 | `paths` deleted | green | the exact minisign value in `python/src/`: 1 → **0** both tools (public value: nil impact) |
| w10 | 2 | DocSearch regex generalised to `^[0-9a-f]{32}$` | green | a random 32-hex `client_<secret-word>` value in raw: 1 → **0** both tools |
| w11 | 3 | `paths` deleted | green | `"key": "<random 64-hex>"` line in `python/src/conf.json`: 1 → **0** both tools (repo-wide) |
| w12 | 3 | path widened to `(^|/)docs/research/kb/raw/` | green | same line in a NON-capture raw file: 1 → **0** both tools |
| w13 | 3 | value class `[0-9a-f]{64}` → `[^"]+` | green | `"key": "<random 32 alnum>"` in a capture: 1 → **0** both tools |
| w14 | 3 | trailing `\s*$` dropped | green | `"key": "<sha256>", "client_<secret-word>": "<random>"` on ONE capture line: 1 → **0** both tools — **the F1 class (line target hides a co-located secret) returns in entry 3** |

Result: **5 of 13 red, 8 of 13 green.** None of the 8 is an equivalent mutant — each has a scanner arm in which a value the
subject reports goes unreported (harness `<scratchpad>/arms-c/scan_c2.py`, `head` and `defaults` columns are the controls;
every case's `head` row is rc=1). The green set is path-scope and value-class widening, a class no planted test varies: the
only out-of-scope probe is entry 1's (`test_commit_sha_outside_raw_mirrors_is_still_reported`), and no planted value sits
on an entry-3 `"key"` line or is pure hex.

Also re-derived this round (claim at `.gitleaks.toml:89-90`): entry 1 made global (`targetRules` deleted, `paths` + AND kept),
planted PAT in raw → gitleaks rc=0, betterleaks rc=1 `github-pat`. Holds.

### E3 — Q3: new defects in the round-c diff

Literal hygiene: the subject's test file and the implementer report, each scanned alone (scratch copies) by both tools under
the repo config and defaults-only → 8 runs, all rc=0 / 0 findings; control (a runtime-built PAT in a scratch `.py`, same
command shape) → rc=1 in all 4 runs. Clean.

Q-CLAIM over the strings this diff adds or changes:

| Clause | Enforcing evidence | Outcome |
|---|---|---|
| `.gitleaks.toml:83-84` "Entries 1-3 are scoped … by `paths`; entry 4 is … REPO-WIDE by design" | `:106`, `:119`, `:128` paths; `:134-136` none | holds (round-b F4 closed) |
| `:89-90` "betterleaks 1.9.0 is not blinded by the global form" | E2 re-derivation | holds |
| `:91-92` the test plants tokens "to catch an entry widened within its own rule" | E2: 8 of 13 within-rule widenings green | **R2 — overclaims** |
| `:94-95` bare form fires "in any file mentioning" the vendor name | rule `keywords` = `sgp_` + vendor name (binary) | holds but incomplete (`sgp_` also triggers) — R4 INFO |
| `:99-100` lowercase bare 40-hex suppressed; "Prefixed `sgp_` tokens stay reported" | E1 rows (lowercase 0, uppercase 1, all three prefixed shapes 1, both tools) | holds |
| test `:5-14` planted tests catch "dropping an entry's `regexes` or `condition`, or matching the line instead of the secret" | E2 m2-m6, m8, w7 all red | holds as enumerated |
| test `:16-22` roles of the other tests; entry 4 has no coverage | test bodies `:144-228`; gitleaks has no `generic-password` | holds (round-b F5 closed) |
| test `:70-71` "Shapes per gitleaks 8.30.1's rule regex: `sgp_<40 hex>` or `sgp_<16 hex>_<40 hex>`" (also the commit message and the implementer report: "both … shapes") | gitleaks regex has a THIRD, `sgp_local_<40hex>` | **R3 — false "both"**; no hole (E1: the third shape is reported) |
| test `:82-84` consecutive-letter run "is NOT reported" | not re-measured | UNVERIFIED (rationale only; no behaviour depends on it) |

No new defect in executable behaviour: every `.gitleaks.toml` change is either the F1 fix (E1) or a comment, and every test
added is red for the right reason on the mutations it names (E2).

## Round-b finding dispositions

| Round-b | Status | Evidence |
|---|---|---|
| F1 (MEDIUM) entry 1 line target hid `sgp_` tokens | **CLOSED** | E1 (all 4 shape/case variants + 3 minified variants: prev rc=0 → head rc=1, both tools) |
| F2 (LOW) entry 1 had no betterleaks benefit | moot | entry 1 now matches only the bare form, which betterleaks never reports (E1 bare rows) |
| F3 (MEDIUM) pytest blind to within-rule widening | **CLOSED** for m2/m3/m4/m5 | E2 |
| F4 (LOW) header "scoped to the mirror tree" | **CLOSED** | `:83-84` |
| F5 (LOW) docstring overclaimed planted tokens | **CLOSED** | test `:5-22` |
| F6 (INFO) stub/pairs skip non-ASCII paths | out of scope; the commit message says ticketed | ticket number UNVERIFIED |

## Required questions

- **Q-FRESH:** N/A — static config, comments and a test; no decision→action pair over mutable inputs.
- **Q-SCOPE:** R1-R4 are test-hardening and comment accuracy inside this diff's files, none a live suppression in the shipped
  config. R1 is a further class beyond what round b named, so it is a TICKET recommendation, not a blocker.
- **Q-CLAIM:** E3 table.

## Stop condition

This round was BOUNDED (three enumerated questions; Q2's widening set fixed at 13 before running). All three are answered.
Findings are LOW/INFO; disposition is ticket or comment edits. A further round is warranted only if dispositioning R1 changes
the enumeration (e.g. new planted cases), and then only over that delta.

## Verdict

**SHIP.** F1 is closed in both scanners for all three prefixed `sgp_` shapes on a commit-URL line, for minified JSON, and on
the held mirror. The held, tracked and fixture false positives still clear. F3 is closed: m2, m3, m4 and m5 are all red, and
so is the F1 revert. This round found only LOW/INFO items. They should be ticketed rather than block the change:

- R1: harden the planted cases against path-scope and value-class widening of entries 1-3 (five cases listed in the table).
- R2: narrow `.gitleaks.toml:91-92` to the widenings the test actually catches.
- R3: "two shapes" becomes three (`sgp_local_`) in the test docstring, and optionally a third param id.
- R4: the keyword clause.

Housekeeping: the scratch worktree was removed after the runs (`git worktree list` checked below), and no tracked file was edited.

## GitHub repos touched

_None._ (All evidence is local: the installed gitleaks 8.30.1 / betterleaks 1.9.0 binaries, read with `strings` for rule text.)
