# Staleness audit — rewritten `docs/secrets-doppler-fnox-keychain.md` (2026-08-03)

Adversarial audit of the caller's rewrite. Ground truth re-derived independently on
this host; the caller's handoff numbers were treated as claims to attack, not as
inputs. Every probe carries a control arm, and every control term was invented
fresh for this run (`ZZ_CONTROL_TROMBIDIUM_4417`, `ZZ_CTRL_HALOTHANE_8802`,
`ctrl_nonexistent_florapex_5518`, `ctrl-absent-vermiculate-3390`,
`ctrl-bogus-quillfeather-7724`, `ZZ_AUDIT_KRELLBOSH_2214`,
`CTRL_ABSENT_PLIMWORTH_6207`, `zzq-flumbertine-8814`,
`ZZ_NOSUCH_BRANDLEQUIN_7741`). No credential value was read or printed;
`security` was never invoked with `-w`/`-g`, and `fnox get` / `fnox export` /
`fnox list --values` / `doppler secrets get` were never run.

⚠️ **The audited file MOVED under me mid-audit** — see § "Re-verified before
reporting". All anchors below are against the **477-line** version present at
02:32 on 2026-08-03.

## Verdicts

| # | Verdict | Anchor | Claim | Probe + control arm |
|---|---|---|---|---|
| 1 | **CONFIRMED-STALE** | `:159-162`, `:294-296` | "`bootstrap_config()` rebuilds the file from a template …" / "until #82's fix ships it also rewrites the whole config" | The editable venv imports the **fixed** module. `rev-parse HEAD` → `691e866`; `manage.py` clean (control: `.claude/settings.json` → ` M`); `.venv/bin/python -c "import mde.secrets.manage"` → `…/src/…/manage.py`, `has _reconcile_declarations: True`. §1 below |
| 2 | **SUSPECT** | `:284` | step 7 offline cache recipe `fnox sync KEY_NAME` | `--dry-run` without `-g` → `…to provider age:`; with `-g` → `…to provider age (global):`. The declaration lives in the global config and mde's own code uses `--provider age --global --force`. §2 |
| 3 | **SUSPECT** | `:54`, `:123` | keychain `mde-fnox` "holds `DOPPLER_TOKEN`"; "#487 … **Latent and unfixed**" | `find-generic-password -s mde-fnox -a DOPPLER_RO_TOKEN` rc=0 (control `-a CTRL_ABSENT_PLIMWORTH_6207` rc=44). `gh issue view 487` → **CLOSED / COMPLETED 2026-08-02**. §3 |
| 4 | **NEEDS-VERIFICATION** | `:469-470` | "`hk.pkl` — the `gitleaks`, `betterleaks`, `detect_private_key` and `no_env_dump` steps" | `gitleaks` and `detect_private_key` are defined in **`hk-common.pkl`** (`:98`, `:74`); only `betterleaks` (`hk.pkl:272`) and `no_env_dump` (`hk.pkl:259`) are in `hk.pkl`. §4 |
| 5 | **CONFIRMED-STALE (omission)** | removed content with no successor | four facts were **deleted, not moved** | 124 of 191 substantive removed lines are absent from the evidence file; most are legitimately superseded prose, but four are facts with no successor anywhere. Control: a known-moved line is found, a synthetic line is not. §5 |
| 6 | REFUTED | `:64-75` | 50 / 50 inline `env=true` / 49 doppler / 1 keychain / 49 age sync / 0 `env="exec"`; `AGE_PRIVATE_KEY` the only one without sync | `tomllib` parse → exactly those. Control: an injected `ZZ_CONTROL_TROMBIDIUM_4417` lacking `env`+`sync` **was** flagged by the same field-presence code |
| 7 | REFUTED | `:20` | global `env = true` on line 2 of the config | raw line 2 = `env = true  # ALL secrets are available…`; line 1 is the "Managed by" header |
| 8 | REFUTED | `:77-78` | `fnox check` → 50 secrets / 3 providers healthy; one `default` profile; fnox 1.32.0 | `fnox check` → `Found 50 secret(s) … Found 3 provider(s) … ✓ Configuration is healthy`; `fnox profiles` → `default (50 secrets)`; `fnox --version` → `fnox 1.32.0` |
| 9 | REFUTED | `:104-114` | `dev`=43 real, `dev_personal`=49 real, +3 auto-injected, `dev ⊂ dev_personal`, 6 extra, matching fnox's 49 one-for-one | `doppler secrets --only-names --json` → 46/52 total, 43/49 real; `dev − dev_personal = []`; the 6 extra are AGE_PRIVATE_KEY, GITHUB_API_TOKEN, LINEAR_API_KEY, MISE_GITHUB_TOKEN, NVIDIA_20260705, NVIDIA_API_KEY; set-equal to fnox's 49 doppler-backed names. Control: `--config ctrl_nonexistent_florapex_5518` → rc=1 |
| 10 | REFUTED | `:107` | `devcontainer.json:198` + `mise.toml:251,277,771` | all four line anchors verbatim-correct |
| 11 | REFUTED | `:123-128` | the `build.doppler-secrets-wired` contract "checks that *a* download happened, not which config" | `suites.toml:507-511` — `per_path_tokens` = `"--env-file",` / `dotfiles/doppler.env",` / `&& doppler secrets download --format docker`. **No config token** |
| 12 | REFUTED | `:180-185` | `doctor.toml [fnox]` = `env = true` + full 50-name `env_true` incl. `AGE_PRIVATE_KEY` | `tomllib` → `env=True`, `len=50`, set-equal to the live fnox names. Control: `ZZ_CTRL_HALOTHANE_8802` absent |
| 13 | REFUTED | `:136-144` | `which mde-py` rc=1 means nothing; `mde-secret-add` is a live zsh function; editable install | rc=1 (control `which fnox` rc=0); `type mde-secret-add` → shell function from `~/.zshrc.d/50-mde-secrets.zsh` (control `type ctrl-bogus-quillfeather-7724` rc=1); `50-mde-secrets.zsh:45` `local _bin="$MDE_PROJECT_DIR/.venv/bin/mde-py"`; `mde.pth` → `…/src` |
| 14 | REFUTED | `:146-155` | `691e866` local-branch-only, not an ancestor of `origin/main`, #82 OPEN, `manage.py` absent from `origin/main` | `merge-base --is-ancestor` rc=1 (control rc=0); `branch -a --contains` → one branch; `cat-file -e origin/main:…/manage.py` rc=128 (control `sync.py` rc=0); #82 OPEN. **`origin/main` is genuinely current** — `git ls-remote origin refs/heads/main` == local `origin/main` (`bd86064`), so "not an ancestor" is not a stale-ref artifact |
| 15 | REFUTED | `:331-344` | `fnox check` cannot see a lost declaration | Independently re-derived with my own fixture (1 key, not the caller's 2): declared → rc=0 `Found 51 secret(s)` ✓ healthy; deleted → rc=0 `Found 50 secret(s)` ✓ healthy. **Stronger than the doc says** — see §6 |
| 16 | REFUTED | `:353-360` | `doppler-cli` and `gh:github.com` keychain entries deleted; `mde-fnox` present | `find-generic-password -s` (no `-w`): `mde-fnox` rc=0, `gh:github.com` rc=44, `doppler-cli` rc=44. Both arms present: the probe finds a real item (rc=0) and misses a fresh bogus one (`ctrl-absent-vermiculate-3390` rc=44) |
| 17 | REFUTED | `:206-208` | this repo suggested `fnox exec -- env \| grep NVIDIA_API_KEY` on 2026-07-20 | `git log --all -S'fnox exec -- env \| grep NVIDIA_API_KEY'` → `7a8c8d6` / `d3ecab6`, both dated **2026-07-20**. Control: `-S'doppler secrets download'` → 7 commits |
| 18 | REFUTED | `:453-457` | `fnox scan` 0 wiring, control 14 for `gitleaks`; `fnox mcp` / `proxy` / `profiles` exist in 1.32.0 | `git grep -nI gitleaks -- '*.pkl'` → **14**, reproducing the doc's control exactly; `fnox scan` in config files → **0** (control, fresh term `zzq-flumbertine-8814` → 0). `fnox --help` lists `mcp`, `proxy`, `profiles`, `scan` |
| 19 | REFUTED | `:472-477` | the upstream guide is gone and not in that repo's git history | `find ~/dev -name 'doppler-fnox-keychain*'` → 0 (control: same `find` for `AGENTS.md` → 87). `git -C ~/dev/honeymoon-period log --all -- '*doppler-fnox-keychain*'` → 0 (control: `-- '*README*'` → 35; 843 unique files ever added, none matching `doppler`). ⚠️ the **directory** `~/dev/honeymoon-period` **does** still exist — only the file is gone |
| 20 | REFUTED | `:9-11` | the exec-era mode table, its opt-in list, and the Context7 incident moved **verbatim** | all three present in `docs/rules-evidence/secrets-out-of-the-shell-env.md:318-402` § "Moved here 2026-08-03", as block-quoted verbatim text. Control: a synthetic sentence is not found by the same matcher |
| 21 | REFUTED | `:303-321` | the diagnosis recipe's commands and expected strings | `fnox list` hides values by default (`-V/--values` opts in); `fnox sync -n/-p/[KEYS]` all valid; dry-run output is verbatim `[dry-run] Would sync 1 secrets in profile default to provider age:\n  AUTH_TOKEN (from doppler_dotfiles_dev_personal)` and, for a bogus key, `No secrets to sync` (control: `ZZ_NOSUCH_BRANDLEQUIN_7741`) |
| 22 | REFUTED | `:304-306` | "`fnox config-files` … Expect this one line" | from `$HOME` and from the repo root → one line. There is no `fnox.toml` in the dotfiles repo, so no second entry appears |
| 23 | REFUTED | `:325-329` | the step-3/step-4 result table | the rewrite **swapped** step 3 and step 4 relative to the old doc (old: 3 = `fnox exec`, 4 = shell) and correctly inverted the fault row from `present\|ABSENT` to `ABSENT\|present`. Semantics preserved |

---

## 1. CONFIRMED-STALE — the doc finds the editable-install branch dependency and then ignores it

Verbatim, `:159-162`:

> `bootstrap_config()` rebuilds the file from a template emitting `provider` +
> `value` only, preserving just `DOPPLER_TOKEN`; `add_secret` / `update_secret` /
> `remove_secret` each call it and then run a **full** `_run_fnox_sync_age()`,
> regenerating all 49 sync blocks with fresh ciphertexts.

and `:294-296`:

> ⚠️ **`mde-secret-add KEY` does steps 3-7 in one command and is the sanctioned
> mde interface — and until #82's fix ships it also rewrites the whole config.**

**Falsifier:** if the code the editable venv actually imports already contains the
#82 fix, both sentences describe `origin/main`'s behaviour in the present tense
about a host that does not run it.

**Route 1 — git:**

```
$ git -C ~/dev/github/ray-manaloto/macos-development-environment rev-parse --short HEAD
691e866
$ git -C … status --short -- src/mde/secrets/manage.py
                       (empty — clean)
$ git -C … status --short -- .claude/settings.json      # CONTROL: probe can see dirt
 M .claude/settings.json
```

**Route 2 — the interpreter that `mde-secret-add` actually invokes:**

```
$ …/macos-development-environment/.venv/bin/python -c \
    "import mde.secrets.manage as m; print(m.__file__); \
     print('has _reconcile_declarations:', hasattr(m,'_reconcile_declarations'))"
/Users/rmanaloto/dev/github/ray-manaloto/macos-development-environment/src/mde/secrets/manage.py
has _reconcile_declarations: True
has _render_initial_config: True
```

`_reconcile_declarations` and `_render_initial_config` exist only in `691e866`.
Its `bootstrap_config` docstring (`manage.py:372`+) states the consequence:

> In steady state this performs **no direct write** to the config: each
> declaration is added or dropped by invoking ``fnox`` itself …
> 2. **It cannot drop the ``env`` mode or a per-secret ``env = true`` opt-in**
>    (mde #82). Those were lost *by construction*, because the file was
>    regenerated from a template that never emitted them. Nothing is
>    regenerated now, so there is nothing to drop.

`_write_initial_config` runs only `if not _FNOX_CONFIG_PATH.exists()`.

**This is an internal contradiction, not merely an outdated fact.** The same
document establishes the premise at `:142-144` — *"That venv is an editable
install … so which code runs depends on which branch that sibling repo has checked
out"* — and at `:149-150` that the fix is checked out. It then asserts the pre-fix
behaviour as the live hazard, and the whole of § "What a regeneration would
actually cost now" (`:157-173`) is premised on a regeneration this host cannot
currently perform.

**What survives the correction and must not be dropped:** `add_secret` and
`remove_secret` **do** still call `bootstrap_config()` (`manage.py:180`, `:222`)
and **do** still run `_run_fnox_sync_age()` (`:183`, `:225`), which is
`fnox sync --provider age --global --force` — so **all 49 sync ciphertexts are
still churned on every add/remove**. `update_secret` is a literal alias for
`add_secret` (`manage.py:191-200`), so naming all three is correct.

**Proposed replacement for `:159-162`:**

> On `origin/main`, `bootstrap_config()` rebuilds the file from a template
> emitting `provider` + `value` only, preserving just `DOPPLER_TOKEN`. **That is
> not the code this host runs.** The editable venv imports
> `fix/bootstrap-config-reroute-through-fnox` (HEAD `691e866`, verified by
> importing the module and finding `_reconcile_declarations`), whose
> `bootstrap_config()` adds and drops declarations by invoking `fnox` itself and
> writes the file directly only when it does not exist — so it cannot drop the
> `env` mode or a per-secret opt-in. What every `add_secret` / `update_secret`
> (an alias) / `remove_secret` still does is run a **full**
> `_run_fnox_sync_age()` (`fnox sync --provider age --global --force`),
> regenerating all 49 sync ciphertexts.
>
> ⚠️ **The protection is a checked-out branch, not a shipped fix.** A
> `git checkout main` in that sibling repo silently restores the template-rewrite
> hazard, and nothing in this repo detects it.

**Proposed replacement for `:294-296`:** drop "until #82's fix ships it also
rewrites the whole config"; say instead that it churns all 49 sync ciphertexts,
and that the no-rewrite guarantee holds only while that sibling repo stays on the
fix branch.

## 2. SUSPECT — step 7's `fnox sync` is missing `--global`

`:284`:

> 7. Optional offline cache: `fnox sync KEY_NAME`.

**Falsifier:** if `fnox sync` without `-g` writes to the global config anyway,
the recipe is fine.

```
$ cd <scratchpad>            # no fnox.toml here
$ fnox sync --dry-run -p age AUTH_TOKEN
[dry-run] Would sync 1 secrets in profile default to provider age:
  AUTH_TOKEN (from doppler_dotfiles_dev_personal)
$ fnox sync --dry-run -p age -g AUTH_TOKEN
[dry-run] Would sync 1 secrets in profile default to provider age (global):
  AUTH_TOKEN (from doppler_dotfiles_dev_personal)
```

The `(global)` suffix appears only with `-g`, and `fnox sync --help` documents
`-g, --global   Write to global config (~/.config/fnox/config.toml)` against a
`-c` default of `fnox.toml`. mde's own shipped code uses
`fnox sync --provider age --global --force` (`manage.py:_run_fnox_sync_age`).

**Why SUSPECT and not CONFIRMED:** settling it needs a real (non-dry-run) `sync`,
which writes — outside the contract for this audit. The dry-run difference and
mde's usage are one route each, in agreement, but neither observes the write.
**Proposed text:** `fnox sync --global -p age KEY_NAME`, with a note that without
`--global` fnox targets a `fnox.toml` in the current directory, not the config the
declaration lives in.

## 3. SUSPECT — the `mde-fnox` row and the "#487 latent and unfixed" framing

`:54`:

> | **macOS Keychain** | machine-local bootstrap vault | service **`mde-fnox`**, holds `DOPPLER_TOKEN` — the credential that unlocks everything else |

`:123`:

> ⚠️ **Latent and unfixed:** the #487 read-only Doppler token is scoped to
> `dev_personal` …

```
$ security find-generic-password -s mde-fnox -a DOPPLER_TOKEN     ; echo rc=$?   # rc=0
$ security find-generic-password -s mde-fnox -a DOPPLER_RO_TOKEN  ; echo rc=$?   # rc=0
$ security find-generic-password -s mde-fnox -a CTRL_ABSENT_PLIMWORTH_6207 ; echo rc=$?   # rc=44
```

(attributes only; `-w` never used.) `mde-fnox` holds **two** accounts. `gh issue
view 487` → **CLOSED**, `stateReason: COMPLETED`, `closedAt 2026-08-02T21:44:57Z`;
its resolution comment records `dotfiles-fnox-ro-20260802`, project `dotfiles`,
config `dev_personal`, access **read**, no expiry, stored as
`mde-fnox`/`DOPPLER_RO_TOKEN`, "**not** the shell environment".

**The scoping mismatch the doc names is real and correctly stated** — `dev_personal`
vs the devcontainer's `dev`. What is off is the framing: "#487 … latent and
unfixed" reads as an open ticket, and `:54` tells a reader diagnosing the keychain
that `mde-fnox` holds one credential when it holds two — the second being the
whole product of #487. **Proposed:** `:54` → "holds `DOPPLER_TOKEN` **and**
`DOPPLER_RO_TOKEN` (#487's scoped read-only token)"; `:123` → "**Latent and
unfixed** *(the token exists — #487 is closed; the scoping mismatch is what is
unfixed)*".

## 4. NEEDS-VERIFICATION — the "See also" attributes two steps to the wrong file

`:469-470`:

> - `hk.pkl` — the `gitleaks`, `betterleaks`, `detect_private_key` and
>   `no_env_dump` steps.

```
hk-common.pkl:74   ["detect_private_key"] = Builtins.detect_private_key
hk-common.pkl:98   ["gitleaks"] = (Builtins.gitleaks) { …
hk.pkl:259         ["no_env_dump"] { …
hk.pkl:272         ["betterleaks"] = (Builtins.betterleaks) { …
```

Two of the four are defined in `hk-common.pkl`, which `hk.pkl` imports and spreads
— so "the steps `hk.pkl` runs" is defensible, but a reader sent to `hk.pkl` to
read the `gitleaks` step will not find it there. `hk-common.pkl:91` even says so:
*"`betterleaks` is the SECOND scanner and lives in hk.pkl, not here"*.
**Proposed:** "`hk.pkl` (`betterleaks`, `no_env_dump`) and `hk-common.pkl`
(`gitleaks`, `detect_private_key`)".

## 5. CONFIRMED-STALE (omission) — four facts were deleted, not moved

Ray's constraint was that exec-era content **move**, not be deleted. It largely
did (§20). But a mechanical diff finds four facts with no successor text anywhere
in the three changed files.

**Probe:** every substantive (`≥25`-char, blockquote-normalised) line removed from
the doc, tested for presence in `docs/rules-evidence/secrets-out-of-the-shell-env.md`.
124 of 191 are absent. Control arms: a line known to have moved
(*"Only secrets carrying an explicit per-secret `env = true` are exported."*) →
**found**; a synthetic line (*"…zomberwacke 6613"*) → **not found**. So the matcher
discriminates.

Most of the 124 are legitimately superseded — rewritten contract text, a rewritten
diagnosis recipe, the "single easiest mistake" framing the rewrite deliberately
corrects. These four are not:

| deleted fact | successor? | probe |
|---|---|---|
| *"Tracked for the sibling repo in knowledge-base issue **#74**."* | **none** | `grep -n '#74\|knowledge-base issue'` across all three changed files → 0 hits. Control: `grep -c '#82'` in the evidence file → 4 |
| *"Eventual intent (Ray, 2026-07-20): migrate this into a **skill** … Neither is done. Treat this file as the interim contract."* | **none** | same grep sweep → 0 hits for `Eventual intent` |
| *"fnox is already shell-activated on this machine (3 `FNOX_*` vars present)"* | **none** | 0 hits for `FNOX_` in the evidence file |
| *"An `age` provider is configured (`recipients = ["age16djrq…"]`)"* | **none** | 0 hits for `recipients` in the evidence file |

The `manage.py:318` template-line reference **did** survive
(`docs/rules-evidence/secrets-out-of-the-shell-env.md:191`), as did the
`add_secret`/`remove_secret`/`update_secret` line numbers (`:185-188`).

**Proposed:** append the four to the evidence file's § "Moved here 2026-08-03"
under a short "smaller facts that had no other home" heading — the knowledge-base
**#74** pointer especially, since it is the only record that the sibling-repo
defect is tracked on our side.

## 6. REFUTED, and the doc understates its own finding

`:331-344` says `fnox check` "for a *lost declaration* … can only pass". I
re-derived it with **my own** one-key fixture rather than reusing the caller's:

```
$ printf '[secrets]\nZZ_AUDIT_KRELLBOSH_2214 = { provider = "keychain", value = "ZZ_AUDIT_KRELLBOSH_2214" }\n' > declared.toml
$ printf '[secrets]\n' > lost.toml
$ fnox check -c declared.toml   -> rc=0  Found 51 secret(s)  ✓ Configuration is healthy
$ fnox check -c lost.toml       -> rc=0  Found 50 secret(s)  ✓ Configuration is healthy
```

Same verdict either way — the doc is right. It is also **weaker than reality**:
the declared key referenced a keychain item that does not exist, and default
`fnox check` still said healthy. The discriminating flag exists:

```
$ fnox check -c declared.toml -a
rc=0  ✓ Configuration is OK (with warnings)
      Secret 'ZZ_AUDIT_KRELLBOSH_2214' failed to resolve: Keychain: secret '…' not found
$ fnox check -c declared.toml --if-missing error
rc=1  Found 1 error(s):
      Secret 'ZZ_AUDIT_KRELLBOSH_2214' failed to resolve: Keychain: secret '…' not found
```

**Optional addition:** default `fnox check` also passes for a *declared but
unresolvable* secret; `fnox check --if-missing error` is the arm that fails
(rc=1). Neither form can see a **deleted** declaration — that remains
`doctor.toml`'s job. This same run is an independent second route for `:435-441`:
`fnox config-files -c <scratch>` listed **both** the scratch file and
`~/.config/fnox/config.toml`, and the counts (51 vs 50) confirm the merge.

## Numbers checked, one by one

| number | anchor | reproduces? |
|---|---|---|
| 50 secrets | `:26`, `:66` | ✅ `tomllib` → 50 |
| 50 inline `env = true` | `:29`, `:67` | ✅ 50/50 |
| 49 doppler-backed / 1 keychain | `:68-69` | ✅ |
| 49 sync blocks | `:70` | ✅, and `AGE_PRIVATE_KEY` is the sole exception |
| 0 `env = "exec"` | `:71` | ✅ (raw string count 0) |
| 43 / 49 Doppler real secrets, +3 auto | `:52`, `:104-110` | ✅ 46 and 52 raw |
| 6 extra in `dev_personal` | `:113` | ✅, enumerated |
| 3 providers | `:53`, `:77` | ✅ `age`, `doppler_dotfiles_dev_personal`, `keychain` |
| fnox 1.32.0 | `:8`, `:457` | ✅ `fnox --version` |
| 12.5× | `:191` | ✅ 50/4 |
| control of 14 for `gitleaks` | `:454` | ✅ under `git grep -nI gitleaks -- '*.pkl'` (other shapes give 32/38/105 — the doc should state the shape) |
| 813 lines (upstream guide) | `:474` | ⚠️ **unverifiable and labelled as such by the doc** — the file no longer exists and is not in git history. Inherited, not re-derived; correctly presented as history |
| 52 / 51 (`fnox check` fixture) | `:336-337` | ✅ shape reproduced with a 1-key fixture (51 / 50) |
| 0.99 / 1.33 / 3.12 s startup | `:444-445` | not re-run; the doc already labels the ≈1.7→≈2.7 figure **unverified inherited** and notes variance exceeds the delta — correct handling |
| 199 lines / 13004 bytes | — | **not present in any of the three files.** If the caller expected these in the deliverable, they are absent; nothing asserts them, so nothing is stale |

## Re-verified before reporting

- **`docs/secrets-doppler-fnox-keychain.md` moved under me mid-audit.** First read:
  **460 lines**. Re-read at write-up: **477 lines**, mtime `02:26:20` (my first read
  preceded it). Staged tree == worktree, so it was re-staged. Two sections I had
  queued as findings were already rewritten in the newer version and are **not**
  reported: the `fnox check` caveat (its control arm was circular — "a control arm
  on a genuinely-absent name also returns rc=0" restated the claim; it is now a
  measured two-arm fixture table at `:334-337`), and the shell-startup figure
  (`≈1.7s → ≈2.7s` was flatly asserted; it now carries three measurements, a
  `zsh -f` control, and an explicit "unverified inherited" label at `:442-449`).
  **Every anchor in this report is against the 477-line version.**
- Re-read at write-up time: `doctor.toml`, `~/.config/fnox/config.toml`,
  `docs/rules-evidence/secrets-out-of-the-shell-env.md`, `hk.pkl` /
  `hk-common.pkl`, `python/verification/suites.toml`, and the sibling repo's
  `src/mde/secrets/manage.py`. None of those had moved.
- `graphify query` was run for orientation and **its answer was discarded**: the
  graph still describes the *old* structure (`Incidents` at L250, `The four
  layers` at L17), i.e. it is stale for this file. Nothing in this report rests
  on it.

## Where I could be wrong

- Finding 1 depends on the sibling repo staying on `fix/bootstrap-config-reroute-through-fnox`.
  If it is switched to `main`, the doc's original text becomes correct again — which
  is itself the reason the replacement text should name the branch dependency
  rather than simply invert the claim.
- Finding 2 is one-route-plus-corroboration, never observed as a write. Do not
  treat it as settled.
- I did not attempt to verify the 2026-07-29 and 2026-08-02 incident narratives
  (`:400-422`) beyond the artifacts they cite; they are historical accounts whose
  primary evidence is transcripts I cannot read.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the audited doc, `doctor.toml`, `hk.pkl`, `suites.toml`, `hook_guard.py`, issue #487
- [ray-manaloto/macos-development-environment](https://github.com/ray-manaloto/macos-development-environment) — `src/mde/secrets/manage.py`, commit `691e866`, issue #82, PR list
- [jdx/fnox](https://github.com/jdx/fnox) — `fnox --help` / `check --help` / `sync --help` / `list --help` surface on 1.32.0, and the cached `docs/research/mintlify-cache/jdx/fnox/llms-full.txt`

---

## Caller's verification + DISPOSITION (appended 2026-08-03, not part of the agent's report)

Recorded here rather than trimmed from the report above, per
`.claude/rules/agent-report-persistence.md` rule 2 (verbatim).

Every actionable finding was **independently re-probed by the caller** before
acting on it — a second route, not a re-run of the agent's command.

- **Finding 1 (`CONFIRMED-STALE`) — FIXED.** Re-derived: importing
  `mde.secrets.manage` through `…/macos-development-environment/.venv/bin/python`
  resolves to that working tree and reports `_reconcile_declarations: True`,
  `_render_initial_config: True` (control: a bogus attribute → `False`), and
  `origin/main` has no `manage.py` at all. The agent is right and the
  contradiction was mine: the doc established the editable-install branch
  dependency and then asserted pre-fix behaviour as live. Rewritten to say the
  hazard is **held off by a checked-out branch, not by a landed fix**, that a
  `git checkout main` silently restores it, and that the 49-ciphertext churn on
  every add/remove happens on **either** branch. The `mde-secret-add` warning at
  step 9 was corrected the same way.
- **Finding 2 (`SUSPECT`) — ACCEPTED.** `fnox sync --help` confirms
  `-g, --global  Write to global config (~/.config/fnox/config.toml)` against a
  `-c` default of `fnox.toml`. Step 7 is now
  `fnox sync --global -p age KEY_NAME`, carrying the agent's own caveat that this
  is one route plus corroboration and was never observed as a write.
- **Finding 3 (`SUSPECT`) — FIXED, both halves.** Re-probed: `mde-fnox` holds
  **two** accounts, `DOPPLER_TOKEN` and `DOPPLER_RO_TOKEN`, both rc=0 (control
  `ZZ_CTRL_FRENDIBAR_7104` rc=44); `gh issue view 487` → **CLOSED /
  COMPLETED / 2026-08-02T21:44:57Z**. The four-layers row now names both
  accounts, and the "latent and unfixed" paragraph now says explicitly that the
  **token exists and #487 is closed** — the *scoping mismatch* is what is
  unfixed. The `build.doppler-secrets-wired` claim was strengthened with the
  agent's `suites.toml:507-511` token list.
- **Finding 4 (`NEEDS-VERIFICATION`) — FIXED.** Re-probed:
  `hk-common.pkl:74` `detect_private_key`, `hk-common.pkl:98` `gitleaks`,
  `hk.pkl:259` `no_env_dump`, `hk.pkl:272` `betterleaks`. "See also" now splits
  the four across the two files with line anchors and notes that all four *run*
  from the project config while only two are *defined* there.
- **Finding 5 (`CONFIRMED-STALE`, omission) — FIXED.** All four deleted facts
  (the knowledge-base **#74** pointer, the migrate-to-a-skill intent, the 3
  `FNOX_*` shell-activation fact, and the `age` `recipients` fact) appended to
  `docs/rules-evidence/secrets-out-of-the-shell-env.md` under
  § "Smaller facts that had no other home". Verified present, control-armed.
- **Finding 6's optional addition — ADOPTED, re-derived.** Own fixture,
  fresh control term: bare `fnox check` → rc=0 ✓ healthy; `-a` → rc=0 ✓ OK with
  warnings, names the secret; `--if-missing error` → **rc=1**, `Found 1
  error(s)`. The doc now carries that three-row table.
- **`gitleaks` control of 14 — shape stated**, per the agent's note: it holds
  under `git grep -nI <term> -- '*.pkl'`, and other shapes give other numbers.
- **Findings 6-23 (`REFUTED`) — no action, correctly.** Note finding 23: the
  agent verified that swapping steps 3 and 4 of the diagnosis recipe preserved
  the semantics of the result table. That inversion was deliberate (under
  `env = true` the shell is the primary lane) and it is the kind of edit that
  silently breaks a table.
- **The 199-line / 13,004-byte figures** the agent could not find are the
  *rule file's* size (`.claude/rules/secrets-out-of-the-shell-env.md`), reported
  to the user as a budget check, never asserted in any document. Nothing stale.

⚠️ **The audited file moved under the agent mid-run** (460 → 477 lines) because
the caller was still re-deriving inherited numbers. The agent detected it, re-read,
dropped two findings that the newer version had already fixed, and anchored
everything to the version it actually read. That is the correct handling of a
moving target, and it is also a caller error: an audit should start from a frozen
tree.
