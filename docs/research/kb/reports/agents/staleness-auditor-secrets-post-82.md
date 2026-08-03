# Staleness audit — secrets corpus post-mde-#82 (2026-08-03)

Audit of this repo's secrets prose after two ground-truth moves on 2026-08-03
(mde #82 fixed and merged; dotfiles #519 rewriting the prose that said
otherwise). The caller's #519 rewrite was treated as a **prime suspect**, and the
caller's handoff numbers as claims to attack, not as inputs.

No credential value was read or printed. `fnox get` / `fnox export` /
`doppler secrets get` were never run; `security` was never invoked with `-w`.
The live fnox config was parsed with `tomllib` for **key names and field
presence only** (`value` and `sync` were popped before any print).

Control terms invented fresh for this run: `ctrl_zz_florn_9931`,
`ZZ_CTRL_FLORN_9931`, `zzq_florn_kbctrl_5518`.

---

## Ground truth, independently re-derived

| fact | probe | result |
|---|---|---|
| mde #83 merged as `716b17d` on mde `main` | `git merge-base --is-ancestor 716b17d origin/main` | **rc=0** (control: `HEAD HEAD` → rc=0) |
| `716b17d` is mde `origin/main` HEAD | `git log --oneline -3 origin/main` | `716b17d …(#83)` / `27e42d0 fix(ci)…(#84)` / `d71b790` |
| this host runs code byte-identical to merged main | `git diff --stat 691e866 origin/main -- src/mde/secrets/manage.py` | **empty, rc=0**. Checked-out branch is still `fix/bootstrap-config-reroute-through-fnox` @ `691e866` (upstream `gone`; NOT an ancestor, rc=1 — squash merge) |
| exactly ONE ref carries pre-fix `manage.py` | `ls-tree` sweep over all 45 `refs/heads` + `refs/remotes` | `feat/secrets-crud-architecture-a` (marker=0); `fix/bootstrap-…`, `origin`, `origin/main` → marker=2 |
| 49-ciphertext churn survives the fix | merged `manage.py:183`, `:225` | both call `_run_fnox_sync_age()` = `fnox sync --provider age --global --force` |
| live fnox config | `tomllib` | 50 secrets · global `env = true` · **50** inline `env = true` · **0** `env = "exec"` · 49 with `sync`, `AGE_PRIVATE_KEY` the sole exception · 49 doppler / 1 keychain (`DOPPLER_TOKEN`) |
| `doctor.toml [fnox]` | `tomllib` | `env = True`, `env_true` len **50**, **set-equal** to live names (control: `ctrl_zz_florn_9931` in neither) |
| `fnox-baseline` runs and passes | `mise run doctor -- --verbose` | `PASS doctor[fnox-baseline]` (3 unrelated `mcp-*` DRIFT findings) |

⚠️ **Probe correction, recorded because it nearly produced a wrong branch
count.** My first sweep filtered with `git cat-file -e "$ref:$path"`, which
returned **rc=0 for refs that do not contain the file** — it was seeing the path
on disk. The control `git cat-file -e d71b790:src/mde/secrets/manage.py` printed
`exists on disk, but not in 'd71b790'` at rc=128, which exposed it. Redone with
`git ls-tree -r --name-only`, armed both ways (fabricated
`src/mde/secrets/ctrl_zz_florn_9931.py` → 0 rows; `src/mde/secrets/` → 5 real
files). This is the same `cat-file` hazard recorded in session 08-03-c.

---

## Verdicts

| # | Verdict | Anchor | Claim | Probe + control arm |
|---|---|---|---|---|
| 1 | **CONFIRMED-STALE** | `docs/rules-evidence/secrets-out-of-the-shell-env.md:91`, `:101-102`, `:526-529` | "The same setting **fixed** the `[redacted]` digit-masking … It returns if `mde-py` re-bootstraps the config." | `mise run p2996-hash` → `0748f3[redacted]46e984492`; control `uv run … p2996-hash` → `0748f3146e984492`. Masking is live NOW. §1 |
| 2 | **CONFIRMED-STALE** | `docs/specs/secrets-takeover.md:659`, `:517`, `:600`, `:184`, `:426`, `:635` | "`.claude/rules/secrets-out-of-the-shell-env.md` \| The **live** secrets doctrine — `env = "exec"`, the 4 opt-ins, the `mde-py` wipe." | live config: 0 `env="exec"`, 50 opt-ins; merged `manage.py` has no template. Spec mtime **2026-08-02 13:27**, predates both moves. §2 |
| 3 | **CONFIRMED-STALE** | `python/src/dotfiles_setup/doctor.py:9-15` | "the variable **is** exec-only in fnox" / "The fnox env-mode settings **are** one `bootstrap-config` run from a wipe. The generator emits `provider` + `value` only" | merged `manage.py:420-421` writes only `if not …exists()`; `:440` reconciles. Same claim carries a ✅ FIXED marker in the rule and the guide, and none here. §3 |
| 4 | **CONFIRMED-STALE** (internal contradiction) | `.claude/rules/secrets-out-of-the-shell-env.md:171-172` vs `:180-183` | "no machine layer exists yet, so this rule is the only layer" — 9 lines above "**Now machine-enforced** — `hook_guard`'s `secret_value_substitution`" | `hook_guard.py:527` defines the rule; `tests/test_hook_guard.py:702` covers it (control: `zz_florn_rule_9931` → 0). #474 OPEN. §4 |
| 5 | **CONFIRMED-STALE** | `.claude/rules/secrets-out-of-the-shell-env.md:21-24` | "the confinement work in #432 … and #441 … **Those tickets need re-judging.**" | `gh issue view` → #432 **CLOSED/COMPLETED 2026-07-31T02:35:49Z**, #441 **CLOSED/COMPLETED 2026-08-02T01:41:39Z**. §5 |
| 6 | **CONFIRMED-STALE** | memory `feedback_secrets_live_in_the_shell_env.md` — SUPERSEDED block + frontmatter `description` | "`mde-py`'s `bootstrap_config()` **still regenerates the file**"; "Durable fix = mde-py's generator"; description "invoker still unattributed" | refuted by merged `manage.py`; the invoker IS attributed in the same file's body (`mde-secret-add LINEAR_API_KEY`). §6 |
| 7 | **CONFIRMED-STALE** (minor) | `python/verification/suites.toml:502` | "DO NOT DROP — see **AGENTS.md** Secrets Injection section." | `grep -i secret AGENTS.md` → **rc=1, 0 hits** (control: `Quick Start` → 1). Real location `.devcontainer/AGENTS.md:43`. §7 |
| 8 | **REFUTED** | `.claude/rules/secrets-out-of-the-shell-env.md:85-89` | the whole "✅ FIXED 2026-08-03" block | all four assertions verified — see Ground truth. Including "one stale local branch": **exactly one**, control-armed |
| 9 | **REFUTED** | `docs/secrets-doppler-fnox-keychain.md:170-178` | "Across all **45** refs … exactly **4** carry `manage.py`"; "every other ref (**41**)" | `for-each-ref \| wc -l` → 45; `ls-tree` sweep → 4; 45−4=41 ✓ |
| 10 | **REFUTED** | `docs/secrets-doppler-fnox-keychain.md:178` | "`mde/secrets/__init__.py:76` imports `manage` lazily inside the call" | line 76 is `from mde.secrets.manage import add_secret`, inside `_handle_crud` ✓ |
| 11 | **REFUTED** | `docs/secrets-doppler-fnox-keychain.md:206` | "`AGE_PRIVATE_KEY`, which is **doppler-primary** with no sync block" | `provider = doppler_dotfiles_dev_personal`, no `sync` key ✓. The lone keychain secret is `DOPPLER_TOKEN` ✓ |
| 12 | **REFUTED** | `docs/secrets-doppler-fnox-keychain.md:128-131` | `build.doppler-secrets-wired` "**name no config at all**" (`suites.toml:507-511`) | `per_path_tokens` = `"--env-file",` / `dotfiles/doppler.env",` / `&& doppler secrets download --format docker`. No config token. Line anchor exact |
| 13 | **REFUTED** | `.claude/rules/secrets-out-of-the-shell-env.md:97-126` | `no_env_dump`, `betterleaks` wired; `clean_env()` has ZERO production call sites | `hk.pkl:259` / `hk.pkl:272` (control: `zz_florn_gate_9931` → 0). `clean_env` appears only at its definition (`child_env.py:60`) + tests; control `without_env_diff` → `graphify.py:52`, `graph_bakeoff.py:152` ✓ |
| 14 | **REFUTED** | `docs/rules-evidence/…:249-255` | the one dated #82 status block | accurate, correctly scoped, and it is the only place that flags KB #74 as open. The "keep the rest verbatim" call **holds** for §§104-269 and §§326-532 — every one of those carries a date in its heading or its lead |
| 15 | **REFUTED** | `docs/rules-evidence/…:411-427` | the four facts the previous audit found deleted | all four present under "Smaller facts that had no other home", incl. the knowledge-base **#74** pointer ✓ — #519 applied the predecessor's finding 5 |

---

## 1. CONFIRMED-STALE (P0) — the digit-masking claim, refuted live

Verbatim, `docs/rules-evidence/secrets-out-of-the-shell-env.md:91` and `:100-102`:

> ## The same setting fixed the `[redacted]` digit-masking
> …
> Those are telemetry flags, not secrets. The digit-masking was never a mise bug;
> it was collateral from treating a non-secret as a secret. **It returns if
> `mde-py` re-bootstraps the config.**

**Falsifier:** if `mise run` masks a digit today, "fixed" is false — and if the
thing that brought it back was not an `mde-py` re-bootstrap, the stated condition
is wrong as well as the tense.

**Route 1 — the mechanism's precondition** (`tomllib`, names and flags only):

```
GEMINI_TELEMETRY_ENABLED:     DECLARED, fields={'provider': 'doppler_…', 'env': True}
GEMINI_TELEMETRY_LOG_PROMPTS: DECLARED, fields={'provider': 'doppler_…', 'env': True}
LANGSMITH_WORKSPACE_ID:       DECLARED, fields={'provider': 'doppler_…', 'env': True}
ctrl_zz_florn_9931:           absent                      <- CONTROL
```

Both telemetry flags are live in this shell, `printenv | wc -c` → **1** each
(`LANGSMITH_WORKSPACE_ID` → 0). That is precisely the "short value marked
redacted" condition the section describes as removed.

**Route 2 — live reproduction, with a control arm:**

```
$ mise run p2996-hash
0748f3[redacted]46e984492                             # 25 chars
$ uv run --project python dotfiles-setup p2996-hash   # CONTROL: same command, no mise
0748f3146e984492                                      # 16 chars, rc=0
```

Same prefix `0748f3`, same suffix `46e984492`; `mise run` replaced exactly one
character with `[redacted]`. The probe discriminates — the non-mise arm returns
the value unmasked.

**The condition that was lost.** The return trigger is stated as *only* an
`mde-py` re-bootstrap. What actually fired was the **2026-08-02 posture
reversal**: `env = true` re-exported the short all-digit flags, so mise redacts
them again. The auto-memory `feedback_mise_run_masks_digits.md` already records
this correction — *"Note the trigger this file predicted was the wrong one — a
hedge naming one cause is not coverage of the class"* — so the corpus disagrees
with itself, and the **tracked** artifact is the stale one.

This matters beyond tidiness: a reader who trusts `:91` will quote a number out
of a `mise run` log.

**Proposed replacement for `:91-102`:**

> ## The `[redacted]` digit-masking — fixed by `env = "exec"`, and BACK since the reversal
>
> mise redacts every occurrence of a redacted variable's **value** in task
> output. fnox marks all its variables redacted, and two —
> `GEMINI_TELEMETRY_ENABLED` and `GEMINI_TELEMETRY_LOG_PROMPTS` — hold
> one-character all-digit values, so mise masked every digit in every
> `mise run` line. `LANGSMITH_WORKSPACE_ID` is worse: an **empty** value.
> Those are telemetry flags, not secrets; the masking was never a mise bug.
>
> `env = "exec"` removed the condition on 2026-07-27 by keeping them out of the
> shell. ⚠️ **The 2026-08-02 reversal put it straight back** — under
> `env = true` all three are exported again. Re-measured 2026-08-03:
> `mise run p2996-hash` → `0748f3[redacted]46e984492` against a non-mise control
> arm of `0748f3146e984492`. **Read every number from a non-`mise` invocation or
> a recorded `rc=`.**
>
> The prediction this section carried — "it returns if `mde-py` re-bootstraps
> the config" — named the wrong trigger. A **policy reversal** fired instead. A
> hedge that names one cause is not coverage of the class.

At `:526-529` (inside the explicitly-verbatim exec-era block) leave the prose
alone but append one bracketed editorial line, since the bolded sentence reads
as live guidance:

> *[2026-08-03: it did return — via the posture reversal, not a re-bootstrap.
> See "The `[redacted]` digit-masking" above.]*

---

## 2. CONFIRMED-STALE (P0) — the spec still calls the retired posture "the live secrets doctrine"

`docs/specs/secrets-takeover.md:659`, the evidence index:

> | `.claude/rules/secrets-out-of-the-shell-env.md` | The live secrets doctrine — `env = "exec"`, the 4 opt-ins, the `mde-py` wipe. |

**Falsifier:** if the live config still ran `env = "exec"` with 4 opt-ins, this
row would be right. It parses as `env = true`, 50 opt-ins, 0 exec-only.

**Why this outranks the other spec hits.** The spec's own acceptance bar A1
(`:61`) says *"An implementing session reads **this spec and the repo's rules,
and nothing else**"* — so this row is the spec telling an implementer what the
rule contains, and it describes the opposite of what the rule now says. The
spec does carry a prominent STATUS block (`:19-42`), but it is entirely about a
`/to-spec` protocol error; **nothing in it warns that the technical content
predates the posture reversal or the #82 fix.** mtime is `2026-08-02 13:27`,
before both.

Companion hits, same cause:

| anchor | verbatim | now |
|---|---|---|
| `:517` | "the four `env = true` opt-ins live in that shell by design" | **50** |
| `:600` (§5 item 16) | "The **four** `env = true` opt-ins sit in the interactive shell **by design**" | **50** — and #470 is still OPEN, so the item itself stands; only the number is wrong |
| `:184` | "the hand edit has a **half-life** — `mde-py`'s `bootstrap_config()` regenerates the file and never re-emits it" | it no longer regenerates |
| `:426` (T8) | "dropping mde's `.zshrc.d` fragment retires the `bootstrap_config()` wipe trigger" | the wipe class is fixed at source; the **49-ciphertext churn** is what T8 would now retire |
| `:635` | "The fnox config-wipe fix itself. Its cause is diagnosed … ships outside this map as ordinary work." | it shipped — mde #83 |

**Proposed:** add one dated block immediately after the existing STATUS block
(do not rewrite §§1-8 — this is a planning artifact and its decisions stand):

> ## ⚠️ STATUS 2 — the secrets posture moved under this spec (added 2026-08-03)
>
> This file was written **2026-08-02, before** two ground-truth moves, and its
> secrets facts have not been re-derived since:
>
> 1. **The posture reversed.** fnox is `env = true`: **all 50** credentials are
>    in every shell and every agent, by design (Ray, 2026-08-02). Every "`env =
>    "exec"`" and "the four `env = true` opt-ins" below (`:517`, `:600`, `:659`)
>    is the **retired** posture. § 5 item 16 still stands — #470 is open — but
>    the number is 50, not 4.
> 2. **The wipe class is fixed at source.** `macos-development-environment#82`
>    is CLOSED, #83 merged as `716b17d`: `bootstrap_config()` reconciles through
>    `fnox` and writes the file only when it does not exist. `:184`, `:426` and
>    `:635` describe a regeneration that no longer happens. What **survives** is
>    the full `_run_fnox_sync_age()` on every add/remove — all 49 `sync`
>    ciphertexts churned (merged `manage.py:183`, `:225`).
>
> The decisions in §§1-4 and §6 are unaffected; the rationale sentences above
> are not.

and replace the `:659` row with:

> | `.claude/rules/secrets-out-of-the-shell-env.md` | The live secrets doctrine — `env = true` (all 50 in every shell, by design since 2026-08-02), the `no_env_dump` / `secret_value_substitution` gates, and the record of the exec-only era it replaced. |

---

## 3. CONFIRMED-STALE — `doctor.py`'s module docstring is the one place the wipe is still live

`python/src/dotfiles_setup/doctor.py:9-15`:

> 1. **Context7 MCP running anonymous.** The plugin's ``.mcp.json`` interpolates
>    ``${CONTEXT7_API_KEY:-}``; the variable **is exec-only in fnox**, so the header
>    resolved to an EMPTY STRING. …
> 2. **The fnox env-mode settings are one ``bootstrap-config`` run from a wipe.**
>    The generator emits ``provider`` + ``value`` only, so ``env = "exec"``, the
>    opt-ins, and every ``sync`` block vanish on regeneration.

**Falsifier:** if merged `bootstrap_config()` still emitted a template, item 2
would be current.

It does not. Merged `manage.py:420-421` writes the file only
`if not _FNOX_CONFIG_PATH.exists()`; `:440` calls `_reconcile_declarations`.
And `CONTEXT7_API_KEY` is not exec-only — the live config has **0** `env="exec"`.

The list is introduced as "session 2026-07-29 found three live defects", which is
past-framing — but item 2's body is written in the **present tense** and states a
mechanism that no longer exists. The asymmetry is what makes it a finding: the
identical claim carries a **✅ FIXED 2026-08-03** marker in
`.claude/rules/secrets-out-of-the-shell-env.md:85` and a whole corrected section
in `docs/secrets-doppler-fnox-keychain.md:152-166`, and **nothing** here. #519's
scope did not include `python/`.

This is a module docstring on live code, so a reader opening it to understand
what `fnox-baseline` is *for* reads item 2 as its current rationale.

**Proposed** — append to item 2, leaving the historical sentences intact:

> 2. **The fnox env-mode settings were one ``bootstrap-config`` run from a wipe.**
>    The generator emitted ``provider`` + ``value`` only, so ``env = "exec"``, the
>    opt-ins, and every ``sync`` block vanished on regeneration.
>    ✅ **Fixed upstream 2026-08-03** — ``macos-development-environment#82``
>    CLOSED, #83 merged as ``716b17d``: declarations are reconciled through
>    ``fnox`` itself and the file is written only when absent. Two reasons this
>    check still earns its place: every add/remove still churns all 49 ``sync``
>    ciphertexts, and one stale local branch still carries the pre-fix code.
>    Since 2026-08-02 the mode is ``env = true`` by decision (all 50 in every
>    shell), so item 1's "exec-only" is history too — what ``fnox-baseline``
>    now pins is that mode plus the full 50-name set.

---

## 4. CONFIRMED-STALE — rule 7 contradicts itself nine lines apart

`.claude/rules/secrets-out-of-the-shell-env.md:171-172`:

> Gap tracked in #474; **no machine layer exists yet, so this rule is the only
> layer.**

`:180-183`:

> **Now machine-enforced** — `hook_guard`'s `secret_value_substitution` denies
> `${<CREDENTIAL_NAME>:-|:=}` in a Bash command; that closes the #474 gap for
> this shape …

Probe: `hook_guard.py:527` defines `secret_value_substitution`;
`tests/test_hook_guard.py:702` covers it (`# --- secret_value_substitution
(#474 shape; landed 2026-08-02)`). Control: `zz_florn_rule_9931` → 0 hits in the
same file. `gh issue view 474` → **OPEN**, consistent with "closes it for this
shape" only.

The first sentence is residue from before the guard landed. A reader who stops
at the end of the first paragraph — the natural stopping point, since the second
is a nested ⚠️ aside — concludes there is no machine layer.

**Proposed replacement for `:171-172`:**

> Gap tracked in #474, still OPEN: one shape is now gated (below), every other
> shape is carried by this rule alone.

That is **6 words shorter than the original**, so it needs no offsetting trim.

### Budget note (the file is at 199/200 lines, 13,055 B)

Findings 4 and 5 are both in-place edits that do not add a line. If you also
want a line for the `#432`/`#441` correction, the cheapest offset is `:53-56`
— the `security add-generic-password` ACL/`-w`-returns-HEX paragraph — which is
**operational trivia about creating a keychain item**, is not referenced by any
rule below it, and is already stated in
`docs/secrets-doppler-fnox-keychain.md`. Moving it to
`docs/rules-evidence/secrets-out-of-the-shell-env.md` frees **4 lines / ~330 B**
and matches the `docs/rules-evidence/` doctrine in `md-size-budgets.md`.

---

## 5. CONFIRMED-STALE — two closed tickets described as needing action

`.claude/rules/secrets-out-of-the-shell-env.md:21-24`:

> and the confinement work in
> [#432](…/issues/432) (SCOPED-READ) and
> [#441](…/issues/441) (agent profile) is
> scoped to a hazard the host no longer avoids. **Those tickets need re-judging.**

```
#432  CLOSED / COMPLETED / closedAt 2026-07-31T02:35:49Z
#441  CLOSED / COMPLETED / closedAt 2026-08-02T01:41:39Z
```

Both were already closed when this sentence was written. "Those tickets need
re-judging" reads as an open action item on open tickets — the same shape the
previous audit caught for #487 ("latent and unfixed" for a closed ticket), so
this is a **recurrence**, not a one-off.

The substantive point is still true and worth keeping: the *conclusions* those
tickets reached were scoped to a hazard the host now accepts. Say that.

**Proposed replacement:**

> and the confinement work in
> [#432](…/issues/432) (SCOPED-READ) and
> [#441](…/issues/441) (agent profile) — both **closed COMPLETED**, 07-31 and
> 08-02 — reached conclusions scoped to a hazard the host no longer avoids.
> Their *findings* need re-judging before anything is built on them; the
> tickets themselves are done.

---

## 6. CONFIRMED-STALE — the auto-memory entry still asserts the generator regenerates

`memory/feedback_secrets_live_in_the_shell_env.md`, SUPERSEDED block:

> The incident history below stays accurate as a record — and its *mechanism*
> still matters, because **`mde-py`'s `bootstrap_config()` still regenerates the
> file.**

Refuted by merged `manage.py:420-421` / `:440`. Two more in the same file:

- body: *"It is a GENERATED file … so a hand edit survives only to the next
  bootstrap. **Durable fix = mde-py's generator.**"* — the durable fix shipped.
- frontmatter `description`: *"… fnox EXONERATED by an authorized write probe;
  **invoker still unattributed**"* — the invoker is attributed in this same
  file's own body (`mde-secret-add LINEAR_API_KEY`, 00:46:51). The description
  is what drives recall relevance, so it is the worst place for a contradiction.

**Proposed:** replace the SUPERSEDED block's last two sentences with —

> The incident history below stays accurate as a record. ✅ **Its mechanism is
> now fixed too:** `macos-development-environment#82` CLOSED 2026-08-03, #83
> merged as `716b17d` — `bootstrap_config()` reconciles declarations through
> `fnox` and writes the file only when it does not exist, so there is no
> template left to drop a field from. What survives: every add/remove still
> churns all 49 `sync` ciphertexts, and one stale local branch
> (`feat/secrets-crud-architecture-a`) still carries the pre-fix code.

and in the `description`, replace `invoker still unattributed` with
`invoker = the documented mde-secret-add happy path; FIXED upstream by mde #83`.

The `MEMORY.md` hook for this entry has the same residue (*"a `mde-py
bootstrap_config()` regeneration now lands on the DESIRED mode"*) — true as
stated, but it presumes a regeneration that no longer happens. Lower priority
than the file itself.

---

## 7. CONFIRMED-STALE (minor) — a contract points at a section that is not there

`python/verification/suites.toml:502`:

> description = "S1 SECRETS: … **DO NOT DROP — see AGENTS.md Secrets Injection section.**"

```
$ grep -n -i 'secret' AGENTS.md        -> rc=1, 0 hits      (TARGET)
$ grep -c 'Quick Start' AGENTS.md      -> 1                 (CONTROL: the grep works)
$ grep -rn -i 'secrets injection' .devcontainer/
.devcontainer/AGENTS.md:43:## Secrets Injection (Doppler)
```

Root `AGENTS.md` contains the string "secret" **zero** times. Four research
artifacts under `docs/research/runs/` cite the section correctly as
`.devcontainer/AGENTS.md § Secrets Injection`, so the right pointer is
well-established elsewhere. I did **not** establish whether the root reference
was ever correct — root `AGENTS.md` is at its 200-line ceiling and has been
trimmed repeatedly.

**Proposed:** `… DO NOT DROP — see .devcontainer/AGENTS.md § Secrets Injection (Doppler).`

---

## KB issue #74 — recommend CLOSE, not rewrite

`gh issue view 74 -R ray-manaloto/knowledge-base` → **OPEN**, last updated
2026-07-29T20:01:31Z. Its body is stale on **four independent axes**:

1. Premise: *"`fnox` is configured `env = "exec"` globally … secrets are no
   longer exported into the interactive shell."* — reversed 2026-08-02.
2. *"Currently 3 do (`EXA_API_KEY`, `GITHUB_TOKEN`, `MISE_GITHUB_TOKEN`)"* — now
   all 50.
3. *"⚠️ The generator does not manage the `env` field at all — and will WIPE
   it"*, with the `manage.py:318` template line — removed by #83.
4. *"**Blocked on:** The `mde-py` generator fix."* — unblocked.

Its recommendation 2 (*"`fnox exec --` (**preferred** — keeps the secret out of
the shell)"*) now **contradicts Ray's deliberate posture**, which is the worst
failure mode for an open ticket: a KB session picking it up would implement the
reversed decision.

**Why close rather than rewrite.** The only part not settled by the fix plus the
reversal is item 4, "add a gate that flags *config interpolates `$VAR` but `VAR`
is not `env = true`*". In dotfiles that gate exists (`doctor.py`'s
`mcp-env-opt-in`, observed PASS this session). In KB it has nothing to guard:

```
$ grep -rn '${[A-Za-z_][A-Za-z_0-9]*:-' $KB --include=… | grep -v /sources/ | wc -l
6                    <- CONTROL: the probe finds substitutions
$ … '${[A-Za-z_]*(KEY|TOKEN|SECRET|PASSWORD)[A-Za-z_]*:-' …                  -> 0
$ … 'zzq_florn_kbctrl_5518' …                                                 -> 0   <- CONTROL
$ ls $KB/.mcp.json                                    -> No such file or directory
```

Zero credential-shaped interpolations, no `.mcp.json`. The armed control (6 real
substitutions found) proves the probe is not blind.

**Recommended close comment:**

> Closing: the premise no longer holds on either axis.
>
> 1. **The posture reversed, deliberately.** fnox is `env = true` since
>    2026-08-02 — all 50 credentials are in every terminal and inherited by
>    every agent, by design (dotfiles
>    `.claude/rules/secrets-out-of-the-shell-env.md`). Recommendation 2 above
>    ("prefer `fnox exec --`") is now the *opposite* of the chosen posture, so
>    leaving this open risks a session implementing the reversed decision.
> 2. **The generator defect is fixed at source.**
>    `macos-development-environment#82` CLOSED 2026-08-03, fixed by #83
>    (`716b17d`): `bootstrap_config()` adds and removes declarations by invoking
>    `fnox` itself and writes the file only when it does not exist. There is no
>    template left to drop `env` or `sync` from. fnox was never at fault.
>
> The one item neither change settles — "add a gate that flags *config
> interpolates `$VAR` but `VAR` is not `env = true`*" — has nothing to guard in
> this repo: **0** credential-shaped `${VAR:-}` interpolations outside
> `sources/` (control: 6 non-credential substitutions found by the same probe),
> and no `.mcp.json`. dotfiles carries that gate as `doctor.py`'s
> `mcp-env-opt-in` check if it is ever needed here.
>
> Residual worth knowing: every `mde-secret-add`/`-rm` still churns all 49 age
> `sync` ciphertexts, and one stale local mde branch
> (`feat/secrets-crud-architecture-a`) still carries the pre-fix code.

---

## Dotfiles issues — bodies falsified by the fix or the reversal

| # | state | verdict |
|---|---|---|
| #470 | OPEN | **stands.** The rule already records the exposure as *accepted, not mitigated*, which is the correct disposition for an open ticket under this posture |
| #471 | OPEN | **stands** — `MISE_ENV_CACHE` is orthogonal to both moves |
| #488 | OPEN | **stands, and #83 sharpens it.** "Do the 49 `sync` blocks become part of the declared baseline?" is now the *only* surviving churn axis, so this is the ticket that inherits what #82 left behind. Worth saying so in the body |
| #503 | OPEN | **stands** — "where does the Doppler `token` declaration durably live, given the config is generated" still bites: the config is still generated, just no longer from a template |
| #474 | OPEN | **stands** — one shape gated, the rest not |
| #432, #441 | CLOSED/COMPLETED | see §5 — the *rule* misdescribes them, the issues themselves need nothing |

---

## Receipts — I agree with the caller's do-not-rewrite policy

`docs/receipts/{437,438,460,487}.md` cite `bootstrap_config()` as a live defect.
**Do not rewrite them**, for three reasons beyond "they are point-in-time
records":

1. Their verdicts were *correct when reached*, and one is now vindicated:
   receipt 438's preferred remedy — *"Route `bootstrap_config()` through `fnox`
   itself (`fnox set` / `fnox sync` per declaration)"* (`438.md:195`) — is
   **exactly what mde #83 implemented**. Rewriting that to past tense destroys
   the evidence that the analysis predicted the fix.
2. Receipt 437's row 8 is a record of a *misattribution being corrected*
   (unlocked write → codegen defect). Its value is entirely in the reasoning
   trail.
3. They are already reachable only through the spec's §8 evidence index and
   #431 — nobody lands on them cold.

**Are they dangerously misleading as-is? No, with one caveat.** The caveat is
that the *index* pointing at them is what a reader meets first, and that index
(spec `:653-659`) is stale for an unrelated reason anyway (§2). Fixing the
index's `.claude/rules/…` row and adding STATUS 2 gives every receipt reader the
dated correction without touching a single receipt. That is the cheapest
correct intervention, and it is already in §2's proposal.

---

## Re-verified immediately before writing this up

- `git status --short` in dotfiles → only this untracked report; `HEAD` still
  `1243805`. **Nothing moved under me during the audit** — unlike the previous
  run in this corpus, where the audited file grew 460 → 477 lines mid-run.
- Re-read at write-up time: `.claude/rules/secrets-out-of-the-shell-env.md`
  (**199 lines / 13,055 B**, matching the caller's figure exactly),
  `docs/secrets-doppler-fnox-keychain.md` (556 lines),
  `docs/rules-evidence/secrets-out-of-the-shell-env.md` (532 lines) — all three
  mtime `2026-08-03 12:58:13`; `docs/specs/secrets-takeover.md` (mtime
  `2026-08-02 13:27:42`, i.e. it predates both ground-truth moves — which is
  finding 2's whole point).
- Re-parsed live `~/.config/fnox/config.toml` and `doctor.toml` at write-up.
- Re-fetched `#432`, `#441` `closedAt` at write-up (finding 5 turns on the
  dates).
- Re-read rule 7's `:169-183` verbatim at write-up (finding 4 is an internal
  contradiction, so both anchors had to be current in the same read).
- `graphify query` was run for orientation per the local rule and its answer
  was **discarded**: it returned 210 nodes topped by this corpus's own prior
  audit reports and truncated at 55, i.e. it indexes the reports rather than the
  claims. **Nothing in this audit rests on it.**

## Where I could be wrong

- Finding 3 is a judgement call about tense, not a factual dispute — the list
  *is* introduced as history. My argument is the corpus asymmetry (same claim
  marked FIXED in two files, unmarked in the third), not that the sentence is a
  lie. If you read module docstrings as pure archaeology, downgrade it.
- Finding 7: I established the pointer is wrong **now**; I did not establish it
  was ever right. If root `AGENTS.md` never had that section, this is an
  always-wrong reference rather than staleness.
- I did not re-verify the 2026-07-29 / 2026-07-30 incident narratives beyond the
  artifacts they cite — their primary evidence is transcripts I cannot read.
- The digit-masking probe necessarily reveals that a fnox-declared variable
  holds a one-character value; the corpus already publishes that these are
  non-secret telemetry flags, so I judged the disclosure acceptable. I did not
  print any variable's value directly.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the audited corpus, `doctor.toml`, `doctor.py`, `hk.pkl`, `suites.toml`, `hook_guard.py`, issues #432/#441/#470/#471/#474/#488/#503
- [ray-manaloto/macos-development-environment](https://github.com/ray-manaloto/macos-development-environment) — `src/mde/secrets/manage.py` on `origin/main` (`716b17d`) and `691e866`, the 45-ref branch sweep, issue #82, PRs #83/#84
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) — issue #74 body, and the env-var-consumer sweep of the working tree
- [jdx/fnox](https://github.com/jdx/fnox) — the `env` tri-state semantics the config is read against
