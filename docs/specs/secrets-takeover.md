# Spec — the secrets + chezmoi-source takeover

The assembling document for [#431](https://github.com/ray-manaloto/dotfiles/issues/431). Its
destination, verbatim:

> A **buildable spec** for the dotfiles repo taking over this Mac's chezmoi source **and** its
> secrets CRUD — retiring `bootstrap_config()` from the host path and retiring the
> `macos-development-environment` repo.

Everything that decides *what* to build already exists and is scattered: **14 decisions** in #431's
body, **9 receipts** under `docs/receipts/` (`436, 437, 438, 440, 441, 445, 446, 448, 460` — the
five earliest decisions, `433/434/439/432/435`, predate the receipt practice and have only their map
bullet), and a throwaway prototype branch (`origin/prototype/432-secrets-cli-shape`, never merges).
Nothing assembles them. That is this file's whole job.

**This spec is a planning artifact.** No code ships from it. Each step becomes ordinary work with
its own PR and its own gates.

> ## ⚠️ STATUS — this is an INPUT to `/to-spec`, not its output (corrected 2026-08-02)
>
> This file was hand-written. The protocol is **`/wayfinder` → `/to-spec` → `/to-tickets` →
> `/implement`** (`docs/issue-tracker.md`), and `/to-spec` is **user-invoked only** — so the session
> that reached the edge of #431's map substituted its own document for the skill's. What that
> dropped, concretely: `/to-spec`'s **seam sketch checked with the user**, its **User Stories** and
> **Testing Decisions** sections, and its standing *"do NOT include specific file paths or code
> snippets — they go stale fast"* (which **A2 below actively contradicts**).
>
> **Two things follow, and neither is optional:**
>
> 1. **The map is not done, so `/to-spec` is not yet due.** `wayfinder`'s done-condition is
>    *"nothing left to decide"*, and resolving a ticket must **graduate** newly-sharp fog into fresh
>    tickets. #431 has **zero open children and 19 fog items** — the frontier stalled. Sharp items
>    become `wayfinder:<type>` tickets **before** any spec is written.
> 2. **A6 is superseded for sharp items.** "Name every open item as open in the spec" is the wrong
>    instrument under wayfinder: a fog item you can phrase precisely is a **ticket**, not a spec
>    bullet. § 5 stays as the classification work-product, but it is a *triage input* for
>    graduation, not the resting place.
>
> What survives unchanged: the assembled decisions (§§ 1–4), the evidence index (§ 8), and the
> `NEW` decisions in § 6 — those are real work, and `/to-spec` should consume them.
> Publishing to `docs/specs/` rather than a tracker issue is **not** part of the error: #431's Notes
> says *"Specs here are persistent… we do not adopt the disposable-spec habit."*

> ## ⚠️ STATUS 2 — the secrets posture moved under this spec (added 2026-08-03)
>
> This file was written **2026-08-02, before** two ground-truth moves, and its secrets facts
> have not been re-derived since:
>
> 1. **The posture reversed.** fnox is `env = true`: **all 50** credentials are in every shell
>    and every agent, by design (Ray, 2026-08-02). Every "`env = "exec"`" and "the four
>    `env = true` opt-ins" below (`:517`, `:600`, `:659`) is the **retired** posture. § 5
>    item 16 still stands — #470 is open — but the number is 50, not 4.
> 2. **The wipe class is fixed at source.** `macos-development-environment#82` is CLOSED, #83
>    merged as `716b17d`: `bootstrap_config()` reconciles declarations through `fnox` and
>    writes the file only when it does not exist. The `:184`, `:426` and `:635` sentences
>    describe a regeneration that no longer happens. What **survives** is the full
>    `_run_fnox_sync_age()` on every add/remove — all 49 `sync` ciphertexts churned.
>
> The decisions in §§ 1–4 and § 6 are unaffected; the rationale sentences above are not.

**Resolution decreases with distance** (approved 2026-08-02). Phases 1–2 carry PR-sized steps;
phases 3–4 carry the transition, its exit gate and its open items, and are deepened when their
preconditions come near. That is deliberate: #448 records `mise dotfiles` → `mise bootstrap
dotfiles` as the **4th command rename in ~7 weeks**, so steps written against that surface today
would need rewriting rather than filling in.

---

## 0. Acceptance bar — what makes this spec "buildable"

#431's *Not yet specified* list contains the line **"The spec's own acceptance bar: what makes it
'buildable'."** This section is that bar. It is seven criteria, each **falsifiable by reading the
finished spec** — a bar you cannot fail is not a bar
(`.claude/rules/probes-need-a-control-arm.md`). **Approved by Ray, 2026-08-02.**

### A1 — Single-entry

An implementing session reads **this spec and the repo's rules, and nothing else**, to execute the
next unstarted step. #431 and the receipts are cited for **evidence** — *why* a thing is done that
way — never as required reading to know *what* to do.

*Fails when:* you pick any step and cannot act on it without opening a receipt to learn the
instruction.

### A2 — A step is one PR

Every step is sized to land as a single PR, and states three things: the **files** it
creates/edits/deletes, the **gate** that proves it landed, and **one line** of why it exists.

*Fails when:* a step names no files, or spans two phases, or is too large to gate in one run.

### A3 — Provenance on every step

Every step carries either `← #NNN` (the decision ticket that authorizes it) or **`NEW`** (a decision
this spec makes). Every `NEW` also appears in § 6 for explicit approval — the spec is allowed to
decide, but never silently.

*Fails when:* a step carries neither marker.

### A4 — Phase exits are machine-checkable, and both arms are named

Each phase ends with a **named command** whose PASS is that phase's definition of done, and the spec
states **what makes it FAIL**. A phase that exits on "looks right", or on a check with no reachable
failing arm, fails this bar.

This is not ceremony: #460 measured `fnox check` as **a probe that can only pass** — intact,
lost-35 and an unknown-provider control all `rc=0` — so a plan that had leaned on it would have
shipped a gate that never fires.

*Fails when:* a phase exit has no command, or no stated failing arm.

### A5 — Preconditions carry the sequence lock

The four transitions — **repair → takeover → CLI → chezmoi-migration** — stay four, never one
(accepted adversarial finding). The spec expresses that as **stated preconditions per phase**, not
as prose ordering, so that starting a phase early is a check you can fail rather than a habit you
can forget. #436's ordering correction is of this kind and appears as a precondition: *keep the
`apply` deny → move the source → verify → then flip*, because freeing `apply` while `sourceDir`
still points at mde opens the exact window the invariant exists to close.

*Fails when:* a phase could be started with the previous phase's exit gate red and the spec does not
say so.

### A6 — Every open item is classified; none is resolved

#431's *Not yet specified* list has **19 bullets** (re-derived here, not inherited: `awk` over the
section, control-armed — a bogus token in the same corpus returns 0). One of them is this acceptance
bar, so **18** outlive it. Every one appears in § 5, assigned to a phase (or to "out of band"), and
marked **blocking** or **non-blocking** for that phase.

Resolving them is explicitly out of scope — the lock is *name them as open*. Omitting one is the
failure.

*Fails when:* an open item is absent, or unclassified, or quietly answered.

⚠️ **SUPERSEDED IN PART (2026-08-02) — see the STATUS banner.** Under `wayfinder`, a fog item you can
**phrase precisely** is a **ticket**, not a spec bullet, *"even if it's blocked and you can't act on
it yet."* So A6's classification is the right *triage*, and the wrong *destination* for the sharp
ones. § 5 stands as the work-product; the sharp rows graduate to `wayfinder:<type>` child issues
before `/to-spec` runs.

### A7 — Rollback per transition

Each phase names its **most likely half-landed state** and the way back out of it. Phases here move
live host state (a chezmoi source, a shell-init chain, 49 secret bindings), so "we would just fix
it" is not a plan.

*Fails when:* a phase has no rollback line.

### What the bar deliberately does NOT require

- **Not** that any open item be resolved (A6 says the opposite).
- **Not** effort or time estimates.
- **Not** that tickets be filed — the spec is the artifact; ticket-filing happens when a phase
  starts, against the tree as it is then.
- **Not** uniform detail across all four phases (see *Resolution*, above).

---

## 1. Phase 1 — REPAIR

**What changes:** nothing moves. mde still owns the chezmoi source and every fnox writer. This phase
makes the *current* host correct and, more importantly, **observable** — so that phase 2 has a
baseline to move away from and a gate that can tell it something broke.

**Preconditions:** none. This phase can start today.

### R1 — the fnox secret NAME SET in the doctor baseline ← #460

**Why:** the doctor is blind to a lost update past the deepest opt-in. Measured: 35/49 secrets with
all four opt-ins intact → **0 findings**, a false pass; the deepest opt-in sits at ordinal **34 of
49, line 55 of 70**, so **14 of 49 secrets** are past the last thing the doctor checks.

**Files:**
- `doctor.toml` — `[fnox]` gains `secrets = [ …49 names… ]`.
- `python/src/dotfiles_setup/doctor.py` — `check_fnox_secret_set`, alongside `check_fnox_baseline`,
  reporting **both** directions: declared-but-gone, present-but-undeclared.
- `tests/test_doctor.py` — one test per direction.

**Gate:** `mise run doctor -- --verbose` names the new check as PASS on the live host; the two tests
bind the failing arms (drop a declared name → finding; add an undeclared one → finding).

**Notes:** a **count floor misses a rename** — that is why it is the name set, and it is the same
argument `check_fnox_baseline`'s own docstring already makes for the opt-in set. Names are not
secrets, and 4 of 49 are already declared in this file. The cost accepted: every legitimate add or
remove needs a `doctor.toml` diff, which is the doctor's stated doctrine, not a new tax.

### R2 — apply `if_missing = "error"` to the live fnox config, and assert it ← #435, NEW (the apply half)

**Why:** #435 decided this on 2026-07-31 and it is **still not applied**. One hand-set
`if_missing = "error"` turns a failed resolution from `rc=0` + WARN into **`rc=1`** — the native
knob that replaces asserting 52 entries (3 provider blocks + 49 bindings).

**Files:**
- `~/.config/fnox/config.toml` — host state, not repo state. The hand edit.
- `doctor.toml` — `[fnox]` gains the `if_missing` axis.
- `python/src/dotfiles_setup/doctor.py`, `tests/test_doctor.py` — the check and both arms.

**Gate:** doctor PASS on the live host; a test fixture without the key produces a finding.

**Notes:** the hand edit has a **half-life** — `mde-py`'s `bootstrap_config()` regenerates the file
and never re-emits it. That is not a reason to skip it; it is the reason the assertion ships in the
same step. The assertion is what survives; the edit is what the assertion is *about*. `NEW` covers
only the decision to apply it now rather than wait for phase 2 to retire the generator.

### R3 — the remaining #435 baseline axes ← #435

**Why:** #435 took the baseline from 2 axes to 5 under one measured rule — **assert iff drift is
SILENT**. R1 and R2 carry two of the three additions; this step carries the rest.

**Files:**
- `doctor.toml` — `[fnox]` gains **profile names + membership** and **`[mcp]` absent**.
- `python/src/dotfiles_setup/doctor.py`, `tests/test_doctor.py`.

**Gate:** doctor PASS; tests bind an added profile, a changed membership, and a re-appeared `[mcp]`
block.

**Notes:** the profile axis asserts **today's truth — `default` only**. The `agent` profile is
created in phase 3 (`NEW`, § 6), so this axis is not written speculatively; phase 3 widens it in the
same PR that creates the profile. Stated limit, from #435 and not softened: asserting `[mcp]` absent
**protects the file, not the host**.

### R4 — the doctor learns about chezmoi ← #436, NEW (declaring today's source)

**Why:** the host is in **real chezmoi drift right now and nothing this repo runs reports it** —
`chezmoi status` → 3 files `MM` (`.config/mise/config.toml`, `.gitconfig`, `.zshrc`), while
`doctor.toml`/`doctor.py` mention chezmoi **0** times (control arm: `fnox` → 3 and 43).

**Files:**
- `doctor.toml` — a new `[chezmoi]` section: the **expected active `sourceDir`** and a
  drift-reporting switch.
- `python/src/dotfiles_setup/doctor.py`, `tests/test_doctor.py`.

**Gate:** doctor reports the 3 live `MM` entries as findings on this host today (that is the check
*working*, not failing the phase); a fixture with a re-pointed source produces a
sourceDir finding.

**Notes:** phase 1 declares the **observed** source, which is **still mde**. That is deliberate
(`NEW`): it detects an unauthorized re-point now, and it makes the phase-2 flip arrive as a
**reviewed one-line diff** rather than as an unremarked change of reality. #436's *relative*
`sourceDir` / `[hooks]` present / `destDir` absent claims are post-flip assertions and land in T7,
not here — a committed literal path fails in whichever of Mac or container it was not written for,
which is exactly why #436's decision 4 was superseded by decision 7.

### Phase 1 exit gate

```
mise run doctor -- --strict --verbose     # exit 0, and every R1–R4 check named PASS
uv run --project python pytest tests/test_doctor.py -x -q
```

**PASS** = `--strict` exits 0 with all four new checks reporting PASS by name.
**FAIL arms, each demonstrated in `tests/test_doctor.py`:** a dropped secret name; an added
undeclared secret; a missing `if_missing`; an extra profile; a re-appeared `[mcp]`; a re-pointed
`sourceDir`. A check with no demonstrated failing arm does not count toward this gate (A4).

The live `MM` drift is **reported, not gated** — resolving it is a phase-2 precondition (§ 2), and
conflating the two would block phase 1 on work that belongs to the takeover.

### Phase 1 rollback

Repo changes revert with `git revert`. The one host mutation is R2's single line in
`~/.config/fnox/config.toml`; removing it restores the prior behaviour, and nothing depends on it.
`mde-py` may remove it for you — that is the documented half-life, and R2's assertion is what
notices.

---

## 2. Phase 2 — TAKEOVER

**What changes:** dotfiles' `home/` becomes this Mac's chezmoi source, and mde leaves the host path.
This is the phase with real blast radius.

**Preconditions — all hard:**

1. Phase 1's exit gate is green.
2. **The 3 live `MM` drifts are resolved**, each explicitly: content captured into the source, or
   deliberately abandoned. An unresolved `MM` at flip time is content the next `chezmoi apply`
   deletes.
3. **The `apply` deny rule is still in force.** It is freed in T7 and not before — freeing it while
   `sourceDir` still points at mde opens the exact window the invariant exists to close (#436's
   ordering correction, which an earlier draft had backwards).
4. **The unmanaged-but-load-bearing sweep has run** (§ 5 item 13). #434's inventory covered
   *managed* files only; the takeover's blast radius is precisely the unmanaged set.

### T1 — make dotfiles' source readable on this Mac ← #439

**Why:** dotfiles' source is **`rc=1` unreadable on this Mac today** — `home/.chezmoiignore:24`
branches on `.is_personal`, a data key only mde's own config template emits. Nothing else in this
phase can be rehearsed until this is fixed.

**Files:** `home/.chezmoiignore` — retire `is_personal`; `.ssh/config` and `.gnupg/**` gate on
`.chezmoi.os` instead.

**Gate:** `chezmoi --source ./home execute-template` and `chezmoi --source ./home managed` both
`rc=0` on this Mac. FAIL arm: they are `rc=1` today, which is the control.

**Notes:** this makes `.chezmoiignore` **data-free**, which dissolves #434's C1.

### T2 — merged `[data]` and a derived identity ← #439

**Why:** the merged config needs three keys and no more, and the devcontainer has **no git identity
today**.

**Files:** `home/.chezmoi.toml.tmpl` — `[data]` is `remote`, `git.name`, `git.email`; identity comes
from `gh api user`, derived once here. `[doppler]` is **dropped** — it has zero template consumers.

**Gate:** `chezmoi --source ./home execute-template` renders on Mac and in the devcontainer; the
container's rendered `.gitconfig` carries a `[user]` block. FAIL arm: an empty `user.email` in
either render.

### T3 — the linux allow-list gate ← #439, #446

**Why:** per-OS source trees are what chezmoi **deliberately declines** to support, so the
fail-closed half moves to a gate: a committed allow-list checked for **set equality**, so an extra
target is a leak and a missing one is a drop — both loud.

**Files:** the committed allow-list (**#439's 13 targets**) and its checker, wired to run in **both**
the devcontainer and CI.

**Gate:** set-equality PASS in both environments. FAIL arms, both required: add a target to the
source without the list → **leak** finding; remove one from the list → **drop** finding.

**Notes:** the list ships at **13** here and goes to **14** in T4b — #446's net map effect — because
the 14th entry is a file T4b creates. Widening it here instead would report a **DROP** until T4b
lands, and splitting the widening from the file would put one change in two PRs (A2).

### T4 — import the four resolved collisions ← #446, #445

Four sub-steps; each is its own PR.

**T4a — `.gitconfig` ← #446.** Merged file = dotfiles' behaviour-only `home/dot_gitconfig` **plus**
#439's `[user]`. Three things are **dropped, not merged**: `core.excludesFile` (git reads
`$XDG_CONFIG_HOME/git/ignore` natively — 3 arms on both machines), all **8** `[safe] directory`
entries (inert on both machines — every path is uid 501, three are not repos, and the container's
bind mount presents uid 1000 = the container user), and the whole `[credential]` block, whose arch
branch is **inverted for this Mac** (it renders the `/opt/homebrew` helper, which is absent, while
the binary that exists is the `/usr/local` amd64 one) — so it prints `No such file or directory` on
every HTTPS credential lookup. All three repos use SSH remotes; the native path is
`gh auth setup-git`. `[filter "lfs"]` is byte-equivalent and needs no reconciliation.
*Gate:* `git config --list --show-origin` on the applied file names no missing helper; FAIL arm is
today's error string.

**T4b — `home/dot_config/git/ignore` ← #446.** mde's `dot_gitignore_global` moves here, **ungated**,
and T3's allow-list goes `13 → 14` **in this same PR**.
*Gate:* set-equality at 14. FAIL arm: the file added with the list left at 13 → **DROP** — which is
also the proof the gate is live.

**T4c — `home/dot_tmux.conf` ← #446.** Plain file, **not a template** — dotfiles' only templating is
a powerline branch dead on both machines (no `powerline-daemon` on the Mac; **no tmux at all** in
the container, which ships zellij). Content = mde's 49 lines minus its mde-repo-absolute
`status-right`, plus dotfiles' `mode-keys vi`, `escape-time 10` and repeatable `-r -T prefix` pane
binds, **plus mde's `extended-keys` pair** — which this repo's own
`.claude/skills/tmux-extended-keys/SKILL.md` names `home/dot_tmux.conf.tmpl` as the file to edit and
prescribes, while dotfiles' copy has never had them. Deletes `home/dot_tmux.conf.tmpl`, and
therefore also edits `.claude/skills/tmux-extended-keys/SKILL.md:51,94`, which names the `.tmpl`
path — leave it and the skill points at a file that no longer exists.
*Gate:* the skill's prescribed lines are present in the applied file; tpm does not clobber
(`sensible.tmux` guards with `*_not_changed`, measured). FAIL arm: the skill's grep finds nothing.

**T4d — the shell-init chain ← #445.** `~/.zprofile` **never becomes a chezmoi target** — it and
`~/.zshrc` are third-party installer accretion targets (`.zshrc`'s drift is **100%** installer
appends). Through the chezmoi era the `.zshrc.d` loader lives **in the template**; the mise
`[dotfiles]` edit-entry form is **post-migration** (phase 4), because chezmoi whole-file ownership
and a mise block in the same file fight forever and mise's "explicit dotfiles win" is mise deferring
to *mise's own* `[dotfiles]`, with no reciprocal deference from chezmoi. `home/dot_zshenv.tmpl` is
**retired, not rewritten**: its `{{ output "mise" "activate" }}` bake is a function of the applying
process — chezmoi runs as a mise shim, so the render carries **38** unsets here and **21** in the
container against **0** from a cleared shell. starship on both machines; `~/.config/starship.toml`
(a 5,122-byte orphan, managed and initialized by nothing) gains an owner; mde's
`oh-my-zsh/custom/aliases.zsh` becomes a `.zshrc.d` fragment.
*Gate:* T3's set-equality widened to `.zshrc.d/**` and `.zprofile.d/**`; a login shell in both
environments starts clean. FAIL arm: a container render containing Mac-only fragments.

### T5 — capture the live mise config into an OS-branched template ← #440

**Why:** **hard precondition, not cleanup.** `chezmoi diff` shows the next apply deletes 4
hand-added `[tasks."update:*"]` sections, `[shell_alias]` and the guard comment from
`~/.config/mise/config.toml`. They move into the template **first**, or the handover reproduces the
wipe class on day one.

**Files:** `home/dot_config/mise/config.toml.tmpl` becomes **one OS-branched source file** — darwin
branch = the host config *including* the captured content, linux branch = the existing devcontainer
overlay; `home/.chezmoiignore`'s darwin gate for this target is retired.

**Gate:** `chezmoi diff ~/.config/mise/config.toml` shows **no deletions**. FAIL arm: today's diff,
which deletes all six items. Note the target must be **absolute** — a relative one prints "not
managed" and exits `rc=0`.

**Notes:** this is the one place the map goes the **opposite** way to #435, deliberately. *Assert
iff drift is silent* points at assertion here too, but assert-only presumes an existing non-dotfiles
writer; this file has exactly one (mde's template) and the map retires it, so assert-only would
orphan the target into the unmanaged-but-load-bearing class.

### T6 — gate the unscoped `mise lock` ← #440

**Why:** the destructive act is the **unscoped command, not the `[hooks]` key**. Measured at mise
2026.7.18: bare `mise lock` takes `[conda-packages.linux*]` **802 → 0**, while
`--platform macos-arm64` leaves all 802 **untouched** and `--platform linux-x64` kills exactly its
own 137 rows. A `[hooks]`-token check both misses a task that shells out to bare `mise lock` and
over-bans legitimate hooks.

**Files:** a hard CI gate on the command shape; `python/verification/suites.toml` binds the wiring.

**Gate:** the gate fails a synthetic bare `mise lock` and passes `mise lock --platform macos-arm64`.
Both arms required.

**Notes:** two received claims are corrected and must not be re-inherited: the victim is
`[conda-packages.*]`, **not** the `[tools.*.platforms.*]` table (which is what *survives*), and
*"do NOT run `mise lock --platform macos-arm64`"* is **false**.

### T7 — the flip ← #436

**Why:** this is the transition itself, and its ordering is the finding: **keep the `apply` deny →
move the source → verify → then flip.**

**Files:**
- The chezmoi config's `sourceDir` → this repo (host state).
- `home/` gains chezmoi-native **`[hooks].pre`** on `apply` and `update`, reading `CHEZMOI_ARGS` and
  aborting when `--source`/`-S` names anything but this repo. This is the **only pre-execution
  binding available**.
- `python/src/dotfiles_setup/hook_guard.py` + `tests/test_hook_guard.py` — a **new** `_RULES` entry
  with its own `since`: `init` and `update` denied, **`apply` freed**.
- `doctor.toml` + `doctor.py` — R4's axis updated to #436's three post-flip claims: a **relative**
  `sourceDir`, `[hooks]` present and pointing into that source, `destDir` absent.

**Gate:** `mise run doctor -- --strict` exits 0 with the three new claims PASS; `chezmoi status` is
clean; the guard's tests bind `chezmoi init` → deny, `chezmoi update` → deny, `chezmoi apply` →
allow.

**Notes, stated not argued away:** the Claude guard layer is **defence-in-depth, not the binding** —
`-S`/`--source`/`--config` are chezmoi **global** flags, so the live rule already permits
`chezmoi --config=… apply`, `chezmoi -S /tmp/x apply` and `chezmoi --source=/tmp/x apply`; **four**
live escapes, three of them on `apply` itself. A command-string regex **cannot bind the source**.
Accepted residuals: `--config=/elsewhere` defeats layers 1 and 3 together and nothing available
closes it; path equality is not repository identity; layer 3 detects *after* an `init --apply` has
written. Also corrected: the *writer vs readers* framing is false — chezmoi's own help calls `init`
*"Setup the source directory **and** update the destination"* and `update` *"Pull and apply"*; none
is a reader, and the operative distinction is what the takeover **needs** (`apply`).

### T8 — mde leaves the host path ← #434, #445

**Why:** dropping mde's `.zshrc.d` fragment retires the `bootstrap_config()` wipe trigger — but
**silently**, and along with `fnox activate`. Both consequences ship with their replacement, not
before it.

**Files:** the mde `.zshrc.d` fragment and `~/.zprofile.d/macos-dev-env.zsh` leave the host path;
their load-bearing content (including `MISE_ENV_CACHE=1`, § 5 item 2) is either carried forward
deliberately or dropped deliberately — never by omission.

**Gate:** a fresh login shell on this Mac resolves secrets and starts clean; `mise run doctor
-- --strict` exits 0. FAIL arm: a missing `fnox` environment in a new shell.

### Phase 2 exit gate

```
mise run doctor -- --strict --verbose
chezmoi status                                  # empty
mise run lint && uv run --project python pytest tests/ -x -q && mise run verify
mise run verify-container-latest                # the allow-list gate, in-container
```

**PASS** = doctor 0, `chezmoi status` empty, all repo gates green, and the 14-target set-equality
gate green in **both** the devcontainer and CI.
**FAIL arms:** a 15th target (leak), a 13-entry list (drop), a non-empty `chezmoi status`, a
`sourceDir` that is not this repo.

### Phase 2 rollback

**Most likely half-landed state:** the source is imported and `sourceDir` is flipped, but one target
renders wrong.

**Way back:** `sourceDir` is one config value — re-point it at mde and `chezmoi apply`. mde is not
deleted by this phase; it stops being *on the host path*.

**The state that is NOT recoverable** is a `chezmoi apply` from a partially-imported source deleting
host content the source does not carry. Two things prevent it, and both are load-bearing: precondition
2 (no unresolved `MM`), and rehearsing every apply with `chezmoi diff ~/<absolute target>` — a
**relative** target prints "not managed" and exits **`rc=0`**, i.e. a probe that reports safe
because it never looked.

---

## 3. Phase 3 — THE SECRETS CLI

Coarse by design (see *Resolution*). Deepened when phase 2's exit gate is green.

**Preconditions:** phase 2's exit gate green. In particular the CLI must not be built against a host
whose secrets config is still regenerated by a retired repo's writer.

**The shape — settled, do not re-derive ← #432:** three agent verbs over a **plain CLI** —
`exec` (scoped), `list` (names only), `status`. **The agent cannot write**: origination is
human-only, so there is no agent write path to secure. `fnox mcp` exists and is **not adopted** —
`[mcp] tools` can remove `get_secret` (probed), but that buys nothing once you measure that **exec
does not confine**, and profiles scope *both* channels, so the CLI loses nothing on the control that
was chosen. Lane 2 picks CLI.

**The exposure model — corrected by measurement, use this wording ← #431 Notes, #432:**
**SCOPED-READ**, not "reference-only". `fnox exec -- sh -c 'echo ${#EXA_API_KEY}'` returns **36**
(arms: 0 for a non-secret name, 0 outside fnox). The model is: the agent is never *handed* a value,
and what is in scope during an exec is capped to that command's own secrets.

**Confinement ← #441:** adopt `[profiles.agent.secrets]` + `--no-defaults` — explicit and additive,
empty at creation, each entry a duplicated per-secret binding defaulting to `env = false`; activated
at the call site by the CLI, with `FNOX_NO_DEFAULTS=true` in the invoking **mise task's `env`** so
the safe default is *tracked* rather than remembered; **never `FNOX_PROFILE` alone** —
`fnox exec -P <nonexistent>` **fails OPEN**: 49 secrets, `rc=0`, zero stderr (5 control arms). The
per-profile config file `fnox.<profile>.toml` is **unreachable here** (project-config-only, and
mutually exclusive with `--no-defaults`).

**Second tier ← #441:** `env = false` + `[proxy.rules]`, adopted as a **ceiling, not a gate** —
injected set = rule table ∩ resolvable scope, and a missing profile starts cleanly at `rc=0`. No
live request has been made through it.

**Consumers ← #431 Notes:** the Claude Code and Codex plugins. Hooks + agent documentation are the
enforcement fallback if plugins prove insufficient.

**Exit gate — PROVISIONAL, confirmed when this phase is deepened.** A4 applies at whatever depth a
phase is written, so it gets a command now rather than a promise:

```
env -i <cli> exec --profile agent -- sh -c 'echo ${#OUT_OF_PROFILE_SECRET}'   # expect 0
env -i <cli> exec --profile agent -- sh -c 'echo ${#IN_PROFILE_SECRET}'       # expect nonzero
<cli> exec --profile does-not-exist -- true                                   # expect nonzero rc
```

**PASS** = out-of-profile length 0, in-profile nonzero, missing profile **refused**.
**FAIL arm, and it is today's behaviour:** `fnox exec -P <nonexistent>` **fails OPEN** — 49 secrets,
`rc=0`, zero stderr. Converting that to a refusal is the CLI's job, so the third line is the arm
that proves the CLI added something.

⚠️ **`env -i` is load-bearing, not tidiness.** Run from the interactive shell, the first probe
**passes for the wrong reason** — § 5 item 16: a parent-shell export survives both
`fnox exec --no-defaults` and `fnox proxy run`, and the four `env = true` opt-ins live in that shell
by design.

**Rollback:** additive. The CLI is a new binary nobody is forced to invoke, and the `agent` profile
is removable. The one thing that does not roll back cleanly is a consumer plugin already shipped
against the verbs.

---

## 4. Phase 4 — CHEZMOI → MISE MIGRATION

Coarse by design. This phase has no start date and is **not** scheduled by this spec.

**The decision ← #448:** `mise bootstrap dotfiles` is the **destination**; chezmoi holds the Mac
through the takeover. This is a decision on **timing, not a tie** — no capability blocker survived
measurement against mise 2026.8.0. What defers it is blast radius (14 targets + the CI gate +
`hook_guard` + `doctor.toml` + the `chezmoi-check` skill + `check-chezmoi-templates.sh`, all at
once, while #431 is mid-flight) and maturity.

**Preconditions — re-evaluation after #431, then ANY ONE of:**

1. `auto_env` defaults on (mise **2027.6.0**);
2. one full release cycle with **no command rename** (`mise dotfiles` → `mise bootstrap dotfiles`
   was the 4th in ~7 weeks);
3. a `home/**` change chezmoi makes awkward.

**What must be re-run, not inherited ← #448:** #434's inventory and #439's allow-list survive
because chezmoi survives, but **not "unchanged"** — both predate the merge and must be re-run
against the merged tree, tool-independently, as #431 work.

**The gate stays set-equality ← #448:** `chezmoi managed` has no mise analogue, **and
`status --missing` is not one** — it detects drift on *declared* entries and is blind to an
unauthorized 15th target.

**Carried into this phase ← #445:** the `.zshrc.d` loader moves from the chezmoi template to mise
`[dotfiles]` **edit entries**, plus `[bootstrap.mise_shell_activate]` (`zprofile = "shims"`,
`zshrc = "activate"` — mise's own example, and exactly this Mac's hand-rolled two-layer setup).
Measured idempotent by construction: apply ×2 → *"all edits are applied"*, where chezmoi's
`modify_` gives **2** blocks in 3 renders without a hand-written strip.

**Exit gate — PROVISIONAL, confirmed when this phase is deepened.**

```
<the set-equality gate>, re-run against the merged tree with mise as the applier   # 14 == 14
mise <bootstrap dotfiles> status --missing                                         # rc=0, converged
```

**PASS** = set equality holds with mise applying, and `status --missing` is `rc=0`.
**FAIL arm, already measured:** delete one mise-written edit block → **`rc=1`**; re-apply → `rc=0`
(armed `rc=0 / rc=1 / rc=0` across converged / block-deleted / re-applied).
**And the arm this gate does NOT have:** `status --missing` is blind to an unauthorized 15th target
— it only checks *declared* entries — which is why set-equality stays and does not become
`status --missing`.

**Rollback:** the largest of the four. chezmoi remains installed and its source remains in this
repo, so re-pointing is a config change — but any `[dotfiles]` edit blocks mise has written into rc
files must be removed, and `mise ... status --missing` is armed for exactly that (measured
`rc=0` / `rc=1` / `rc=0` across converged / block-deleted / re-applied).

---

## 5. Open items — all 19, classified, none resolved

Per A6. **Blocking** means the phase cannot exit until the item is settled; **non-blocking** means it
must be *stated* in that phase's design and may remain open.

| # | Item | Phase | Status |
|---|---|---|---|
| 1 | Whether any macOS mechanism (keychain ACL, launchd helper, second OS user, TCC) can distinguish the agent process from the human's shell on one uid. ⚠️ "no vendor attempting it" is corrected — `fnox proxy run` is attempting it, and names the same limit unprompted. | 3 | non-blocking |
| 2 | `MISE_ENV_CACHE=1` is **live on this Mac** ([#471](https://github.com/ray-manaloto/dotfiles/issues/471)) — caches resolved secrets encrypted on disk, with a documented staleness trap. Set by mde's `~/.zprofile.d/macos-dev-env.zsh`, i.e. **the same file as item 13** — those two open items are one item. | 2 | **blocking** (T8) |
| 3 | The devcontainer secrets lane: `doppler secrets download` → `~/.local/state/dotfiles/doppler.env` → `runArgs --env-file`, and the `scripts/devcontainer-smoke.sh` canary set. Untouched by research. | 3 | non-blocking |
| 4 | Provisioning a scoped, read-only, expiring Doppler service token. Unblocked by #437, and now the **only** available enforcement for single-writer. | 1 | non-blocking |
| 5 | Whether the secrets CLI eventually graduates to its own repo. | 3 | non-blocking |
| 6 | `--no-defaults` has **no config-level enforcement**. `FNOX_NO_DEFAULTS` in a tracked mise task's `env` is the best available answer and is still a call-site mechanism — it does not reach a direct `fnox` invocation, and a same-uid agent can unset it. Making it impossible is unsolved. | 3 | non-blocking (must appear as an accepted residual) |
| 7 | The 49 `sync` blocks. Drift is silent ⇒ #435's rule says assert; whether that is *harm* was left depending on which store is source of truth. ⚠️ #437 later decided **Doppler is the declared source of truth**, so this item's stated premise may be superseded — flagged, deliberately **not** resolved here. | 1 | non-blocking |
| 8 | The keychain provider's service is named **`mde-fnox`** — after the repo being retired. Renaming is a data migration across 49 keychain entries, not a config assertion. | 2 | non-blocking |
| 9 | Whether `dotfiles-secrets` wraps `fnox` or reimplements the resolution path. The shape is settled either way. | 3 | non-blocking |
| 10 | **The spec's own acceptance bar.** | — | **RESOLVED by § 0** — the one item this session was asked to answer |
| 11 | Whether Doppler serialises writes **server-side**. Unanswerable from docs; needs a live concurrent-write experiment. | out of band | non-blocking |
| 12 | Whether an **undocumented** Doppler conditional-write header exists — the rendered docs were read, not an OpenAPI spec. | out of band | non-blocking |
| 13 | A systematic sweep for **unmanaged-but-load-bearing** host files. `~/.zprofile` was the first found; #445 decided that one file and deliberately did **not** generalise. The sweep is **unrun**. | 2 | **blocking** (precondition 4) |
| 14 | The host is in real chezmoi drift right now and nothing this repo runs reports it (3 `MM`). | 1 report / 2 resolve | **blocking** (R4 reports; phase-2 precondition 2 resolves) |
| 15 | mde's `chezmoi.timeout` check is a flaky margin, not a fault — 30s limit, 25s actual. An mde defect. | out of band | non-blocking (deferred mde session) |
| 16 | **Inherited environment defeats every scoping mechanism** ([#470](https://github.com/ray-manaloto/dotfiles/issues/470)) — a parent-shell export survives both `fnox exec --no-defaults` and `fnox proxy run`. The four `env = true` opt-ins sit in the interactive shell **by design**, so any agent started from that shell holds them regardless of active profile. The largest unclosed hole in the exposure model. | 3 | non-blocking (must appear as an accepted residual, **and** it is the trap in phase 3's exit-gate note) |
| 17 | The proxy's exposure set is the **rule table**, not the profile — one global union serves every lane, and adding a rule widens every lane at once. Per-lane narrowing has no mechanism here. | 3 | non-blocking |
| 18 | A new **silent-drift axis** for #435's baseline: `SecretConfig` has no reference form, so every agent-reachable per-secret binding is **copied** into the profile and can diverge from its top-level original silently. #435's membership axis checks membership, not divergence. | 3 | **blocking** (the profile step) |
| 19 | **Nothing verifies the proxy end-to-end** — header substitution into `authorization`, allowed vs rejected destinations, and the ephemeral CA path are unverified. | 3 | non-blocking |

**Count check:** 19 rows; item 10 resolved by § 0 ⇒ **18 open**, which is what A6 requires the spec
to carry.

---

## 6. Decisions this spec makes (`NEW` — needing approval)

The spec is allowed to decide, never silently (A3). Four:

1. **The phase assignment itself.** #431 names four transitions and 14 decisions but never says
   which decision lands in which transition. §§ 1–4 assign them. A decision put in the wrong phase
   here is a spec bug, not a re-litigation of the decision itself.
2. **Phase 1 declares the *observed* `sourceDir` (still mde), not the target one** (R4). It buys two
   things: detection of an unauthorized re-point today, and a phase-2 flip that arrives as a
   reviewed one-line diff.
3. **The `agent` profile is created in phase 3, not phase 1** — so R3's profile axis asserts today's
   truth (`default` only) rather than a speculative future, and phase 3 widens the axis in the same
   PR that creates the profile.
4. **`if_missing = "error"` is applied to the live host in phase 1** (R2), rather than waiting for
   phase 2 to retire the generator that erases it. #435 decided the assertion; the *apply* half is
   this spec's call. The half-life is real and is exactly why the assertion ships with it.

---

## 7. Deliberately out of scope

- The four execution phases settled in the 2026-07-30 grilling session (`.mcp.json` emptying,
  `doctor.toml` correction, the hk 1.53.0 bump, closing Renovate #236) — decided, not decisions.
- [#421](https://github.com/ray-manaloto/dotfiles/issues/421) (four-tool `shared.toml` bump) — a
  plain chore issue.
- The fnox config-wipe fix itself. Its cause is diagnosed (`mde-py`'s `bootstrap_config()` rebuilds
  the file and never re-emits `env`), its trigger is known (`mde-secret-add`, the documented happy
  path), and `mise run doctor`'s `fnox-baseline` check already detects it every session. No fog ⇒
  not a decision ⇒ ships outside this map as ordinary work.
- **Upstream fnox work.** #438's lane 1 is tracked locally only (#460) and was deliberately not
  filed upstream.

## 8. Evidence index

The spec is single-entry (A1); this table is where to look when you want the *workings*.

| Source | Carries |
|---|---|
| [#431](https://github.com/ray-manaloto/dotfiles/issues/431) | The map: destination, notes, 14 decisions, 19 open items, out of scope. |
| `docs/receipts/436.md` | The four live guard escapes, `[hooks].pre`, the ordering correction. |
| `docs/receipts/437.md` | Doppler as source of truth; fnox cannot write to it (from source). |
| `docs/receipts/438.md` | `flock`, the dead-inode analysis, the two-tier guard, the 5/10 caller re-counts. |
| `docs/receipts/440.md` | The 802 → 0 `mise lock` measurement; why write, not assert-only. |
| `docs/receipts/441.md` | Profiles, `--no-defaults`, the proxy as ceiling; the rigged-fixture reversal. |
| `docs/receipts/445.md` | The shell-init chain; the `.zshenv` shim-bake measurement. |
| `docs/receipts/446.md` | `.gitconfig`'s four areas, `.tmux.conf`, the 13 → 14 allow-list. |
| `docs/receipts/448.md` | chezmoi vs mise; the deferral's real reason. |
| `docs/receipts/460.md` | The doctor's blind zone; `fnox check` as a probe that can only pass. |
| `origin/prototype/432-secrets-cli-shape` | The CLI shape spike. **Never merges.** `git show origin/prototype/432-secrets-cli-shape:python/prototypes/secrets_cli_shape/policy.py`. |
| `.claude/rules/secrets-out-of-the-shell-env.md` | The live secrets doctrine — `env = true` (all 50 in every shell, by design since 2026-08-02), the `no_env_dump` / `secret_value_substitution` gates, and the record of the exec-only era it replaced. |

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — this repo: the map, the
  receipts, `doctor.toml`, `home/`, and every gate named above.
- [ray-manaloto/macos-development-environment](https://github.com/ray-manaloto/macos-development-environment) —
  the repo being retired; where every fnox writer and the current chezmoi source live.
- [jdx/fnox](https://github.com/jdx/fnox) — profiles, `--no-defaults`, the proxy, `if_missing`.
- [jdx/mise](https://github.com/jdx/mise) — `bootstrap dotfiles`, `mise_shell_activate`, `mise lock`.
- [twpayne/chezmoi](https://github.com/twpayne/chezmoi) — `[hooks].pre`, global flags, `managed`.
