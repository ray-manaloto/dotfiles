# Staleness audit — secrets-prose (2026-08-03)

> Persisted verbatim at receipt per `.claude/rules/agent-report-persistence.md`.
> Producer: `staleness-auditor` agent (`model: opus`), first run — a smoke test of
> `.claude/agents/staleness-auditor.md` (PR #512). The agent delivered by message
> and did **not** write this file itself; the caller persisted it. See the
> "Caller's verification" section appended at the end.

**Ground truth used** (measured this host, no values printed): fnox **1.32.0**; `fnox config-files` → only `~/.config/fnox/config.toml`; `fnox list` = **50** secrets (49 doppler + 1 keychain); config line 2 = bare global `env = true` plus **50** inline per-secret `env = true`; **49** `sync = {` blocks; `AGE_PRIVATE_KEY` declared, doppler-primary, **no** sync block; `doctor.toml` `[fnox] env = true` + `env_true = [50 names]` incl. `AGE_PRIVATE_KEY`.

⚠️ **Read finding 2 first — it changes what you think is already fixed.**

| # | Verdict | Anchor | Claim | Probe + control arm |
|---|---|---|---|---|
| 1 | **CONFIRMED-STALE (P0)** | `.claude/rules/secrets-out-of-the-shell-env.md:43` | "Both entries were deleted … `gh:github.com` / `doppler-cli`" | `security find-generic-password -s 'gh:github.com'` → **rc=0 PRESENT**, cdat=mdat=`20260717`; `-s doppler-cli` → rc=44; control `-s krendlo-absent-9931` → rc=44 same error |
| 2 | **CONFIRMED-STALE** | `.claude/rules/…:123-125` | gate #4 is "`clean_env()` … strips `__MISE_DIFF`" | `clean_env` → 0 production call sites; control `without_env_diff` → `graphify.py:18,52`, `graph_bakeoff.py:60,152`; control `ZANDRUP_KEEVIL_4471` → 0 |
| 3 | **CONFIRMED-STALE** | `docs/secrets-doppler-fnox-keychain.md:28-61` | "Since 2026-07-27 this config is globally `env = "exec"`" + "**Four are**" | config line 2 = `env = true`; 50 inline `env = true`; 0 occurrences of `env = "exec"` |
| 4 | **CONFIRMED-STALE** | `docs/…keychain.md:204` | step-3 comment "`present here + absent in step 4 == env="exec"`" | contradicted by the file's own rewritten table 14 lines later (`:224-229`) |
| 5 | **CONFIRMED-STALE** | `docs/…keychain.md:21`, `:90` | "49 secrets"; table "per-secret `env = true` \| **3**" | `fnox list` → 50 rows; 50 inline `env = true`. `:90` also contradicts `:43` ("Four are") |
| 6 | **REFUTED** | `docs/…keychain.md:72`, `:110`, `:91`, `:320` | mde-py off PATH · 3 `FNOX_*` vars · 49 sync blocks · `fnox scan` unused | `which mde-py` rc=1 (control `which fnox` rc=0); `env \| grep -c '^FNOX_'` → 3; 49 `sync = {`; `fnox scan` → 0 wiring (control `gitleaks` → 14) |

## 1 — `gh:github.com` was never deleted (P0, two routes)

> `.claude/rules/secrets-out-of-the-shell-env.md:43` — "Both entries were deleted (`security delete-generic-password -s 'gh:github.com'` / `-s 'doppler-cli'`) and both now fall through to their ENV token."

**Falsifier:** if either service still resolves in the login keychain, "both were deleted" is false.

```
gh:github.com    PRESENT created=20260717014126Z modified=20260717014126Z
mde-fnox         PRESENT created=20260329091057Z acct=AUTH_TOKEN
doppler-cli      ABSENT rc=44
CONTROL absent   ABSENT rc=44   (identical error text — probe discriminates)
```

`cdat == mdat == 2026-07-17` — **predating the claimed 2026-08-02 deletion, and unmodified since**. So it was not deleted-and-recreated; it was never deleted.

**Second route** (`gh auth status`, rc=0 in <25s from this non-GUI process):

```
✓ Logged in to github.com account sortakool (GITHUB_TOKEN)     ← Active account: true
✓ Logged in to github.com account sortakool (…/gh/hosts.yml)   ← Active account: false
```

The two routes agree and refine each other: gh *does* use the ENV token, but **because `GITHUB_TOKEN` takes precedence**, not because the keychain entry is gone. The rule's conclusion is accidentally right; its stated mechanism is false, and **the hazard it documents — a keychain-backed `gh` wedging a background process on an unanswerable auth dialog — is unmitigated, not mitigated.** Half of a security remediation is recorded as complete.

Proposed replacement for `:43-45`:

> The `doppler-cli` entry was deleted (`security delete-generic-password -s 'doppler-cli'`) and `doppler` now falls through to its ENV token. ⚠️ **`gh:github.com` is still in the keychain** (created 2026-07-17, unmodified) — `gh` reaches for `GITHUB_TOKEN` first, so the entry is currently dormant rather than removed, and the hang hazard returns the moment that env token is absent.

I did **not** delete it — that is your call, and it is outward-facing on your credential store.

## 2 — gate #4, and the fix that is on no shipping branch

> `.claude/rules/…:123-125` — "4. **`clean_env()`** … strips `__MISE_DIFF` and the credential-bearing names from processes this repo spawns"

`clean_env` appears only at its own `def` (`child_env.py:60`) and two docstrings (`:19`, `:79`), plus `tests/test_child_env.py`. Zero production callers. Control arm, identical command shape: `without_env_diff` → 4 real production hits. This is the exact defect the rule convicts `betterleaks` of two entries above.

**The correction already exists** — `c9ac656` rewrites this block to name `without_env_diff()` — but:

```
c9ac656  not-in-HEAD  not-in-main   docs(rule): gate #4 named a function with zero call sites
78a30be  not-in-HEAD  not-in-main   fix(doctor,guard): two live defects the env=true reversal exposed
dc3f4e2  not-in-HEAD  not-in-main   docs: correct fnox/Doppler/keychain claims an agent audit found stale
46c8178  not-in-HEAD  not-in-main   feat(secrets): declare AGE_PRIVATE_KEY — three stores in sync
```

**Disagreeing with the brief:** you said "#507, #509, #510 touched both files, so some claims may already be corrected." Partly. `docs/secrets-doppler-fnox-keychain.md` is byte-identical between HEAD and `feat/age-private-key-in-baseline`, so `dc3f4e2`'s doc edits *did* ship. But `c9ac656`'s rule edits did **not** — the 43-line branch delta is exactly that commit. So **`.claude/rules/secrets-out-of-the-shell-env.md` on `main` still carries the stale gate #4**, plus the two live defects `78a30be` fixes. Those four commits are stranded on a local branch. That is the highest-leverage item here and it is invisible from this branch alone.

## 3-5 — the doc still teaches the retired posture

`docs/secrets-doppler-fnox-keychain.md:31-49` presents `env = "exec"` as current, marks it "**(ours)**" in the mode table, and names four opt-ins. Reality is global `env = true` + 50 inline overrides. The file's own correction sits at `:218-229` — **190 lines below the false claim**, so a reader following the document top-to-bottom acts on the retired posture first. `:204`'s inline comment contradicts the corrected table 14 lines later. `:21` says 49 secrets (now 50); `:90` says 3 per-secret opt-ins while `:43` says four — an inconsistency that predates the reversal.

The rule already flags this at `:161-162` ("read it as history until it is rewritten"), so it is known — but "until it is rewritten" has not happened, and the doc carries no banner. Minimum fix: a reversal banner at `:28` before the mode table, and delete the `env="exec"` clause from `:204`.

## Re-verified before reporting

Re-read at write-up time, immediately before this message: `git rev-parse HEAD` → `b208400` (unchanged), branch `feat/staleness-auditor-agent`, `git status` clean; `.claude/rules/…:123-125` and `:40-45`; `docs/…:31-35`, `:43-44`; `doctor.toml [fnox]`. Nothing had moved.

**Two probe self-corrections, both mine, both the same class:** `grep '^AGE_PRIVATE_KEY'` returned 0 because `fnox list` indents rows with a leading space; and my `^env = true$` regex returned 0 because config line 2 carries a trailing comment. Both would have produced confident false findings ("AGE_PRIVATE_KEY undeclared", "no global env setting"). Corrected before reporting — the global `env = true` **is** there, so the brief's ground truth is right and my first reading was not.

**Not settled:** the rule's "fnox reads a keychain secret in 0.03s" (`:37`) and "190 stuck processes, load 13.5" (`:41`) are inherited measurements I did not re-derive — timing them risks reading a value. Treat as unverified-inherited.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the audited files, git topology, `doctor.toml`, `child_env.py`
- [ray-manaloto/macos-development-environment](https://github.com/ray-manaloto/macos-development-environment) — referenced as issue #82 (the `bootstrap_config()` wipe); not re-probed this run

---

## Caller's verification (appended 2026-08-03, not part of the agent's report)

Recorded here rather than trimmed from the report above, per rule 2 (verbatim).

Findings independently re-probed by the caller are annotated in the session
handoff. One correction to the agent's finding 2 wording: the four commits are
**not** "stranded on a local branch" — they are pushed, on PR **#510**, which was
OPEN with auto-merge armed and `mergeState: DIRTY` since `main` advanced. The
substance stands: they were not on `main`, so `main` still carried the stale
gate #4 and the two live defects.

### DISPOSITION (2026-08-03, Ray approved all three follow-ups)

- **Finding 1 — RESOLVED.** `gh:github.com` deleted with
  `security delete-generic-password`. Control-armed both directions: before rc=0
  → after **rc=44**, while `mde-fnox` stayed rc=0 (so the probe had not gone
  blind) and a fresh absent term returned rc=44. `gh auth status` still rc=0 via
  `GITHUB_TOKEN`, and a **file-based** fallback the report did not note also
  survives at `~/.config/gh/hosts.yml` — so the entry was a third copy, and
  deleting it costs no re-login. The audited claim at
  `.claude/rules/secrets-out-of-the-shell-env.md:43` ("both entries were
  deleted … both now fall through to their ENV token") is **true as of this
  change**, so it needs no edit.
- **Finding 2 — RESOLVED.** `main` merged into the branch; #510 went
  `DIRTY` → `BLOCKED` (conflict cleared, awaiting checks). ⚠️ The first merge
  attempt was **not a merge** — a `check_conventional_commit` rejection cleared
  `MERGE_HEAD`, so the retry landed as a single-parent commit carrying main's
  contents without its lineage, and GitHub kept reporting `DIRTY`. Caught by two
  probes disagreeing (`git merge-base --is-ancestor` said no while the PR head
  *was* the commit); `git rev-list --parents -n1` settled it. Redone as a real
  two-parent merge, verified `main-is-ancestor rc=0` with the inverse as control.
- **Findings 3-5 — still open.** `docs/secrets-doppler-fnox-keychain.md` has not
  been rewritten; the reversal banner and the `:204` fix are unshipped.
- **Finding 6 (`REFUTED`) — no action, correctly.**
