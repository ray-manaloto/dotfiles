# Code review — #522 `5bce39f`, STANDARDS axis

Diff: `git diff a7eecc2...HEAD` — 4 files, +84/-35.
`.devcontainer/AGENTS.md`, `.devcontainer/devcontainer.json`,
`docs/secrets-doppler-fnox-keychain.md`, `mise.toml`.

Tooling already green (lint rc=0, pytest 1210, verify 113, lint-docs); nothing
below duplicates a check that ran.

---

## HARD VIOLATIONS

### H1 — The documented opt-out is the exact anti-pattern `mise.local.toml.example` forbids, and it has no working alternative

The diff prescribes, in two places:

`.devcontainer/AGENTS.md:52`
```
`mise.local.toml`: `[tasks.up] env = { DOPPLER_CONFIG = "dev" }`.
```
`docs/secrets-doppler-fnox-keychain.md:108` (a NEW line)
```
| **`dev`** | **43** | nothing, by default. Retained as a per-clone opt-out via
`mise.local.toml` `[tasks.up] env = { DOPPLER_CONFIG = "dev" }` |
```

`mise.local.toml.example` says the opposite, in capitals:

> **WARNING: do NOT override by redefining a task (`[tasks.up]`,
> `[tasks.dev-rebuild]`, …). A `[tasks.<name>]` block in mise.local.toml
> REPLACES the whole task — it strips the task's `run` body, so `mise run up`
> silently becomes a no-op.** mise task tables do NOT deep-merge (verified on
> mise 2026.7.0). Use `[env]` only. See `feedback_mise_local_toml_replaces_task`.

`mise.toml:240-250` — the comment block **immediately above the line this diff
edits** — repeats it and explains the fix: `BASE_IMAGE` and
`DEVCONTAINER_SSH_PORT` are written as `{{ env.VAR | default(value='…') }}`
precisely "so a per-clone gitignored mise.local.toml `[env]` … overrides them
WITHOUT redefining the task."

`DOPPLER_CONFIG = "dev_personal"` is a **bare literal**, not templated. So the
sanctioned `[env]` route does not work either (a task-scoped `env` literal beats
a config-level `[env]`), and the prescribed `[tasks.up]` route no-ops
`mise run up`. **The opt-out this diff leans on has no working mechanism at
all.**

This is not inherited breakage the diff merely passed through: the shape existed
before, but the diff *promotes* it — `dev`'s entire remaining justification
("Retained as a per-clone opt-out") now rests on it, and the "Add a secret"
section (`:349-352`) was rewritten to point at it too.

**Fix:** template it like its two neighbours —
`DOPPLER_CONFIG = "{{ env.DOPPLER_CONFIG | default(value='dev_personal') }}"` in
all three `mise.toml` sites (`:251`, `:277`, `:771`), add `DOPPLER_CONFIG` to
`mise.local.toml.example`'s "Overridable vars" list, and change both prose sites
to `[env]`.

### H2 — The commit invalidated one of its own citations

`docs/secrets-doppler-fnox-keychain.md:107` cites
`` `.devcontainer/devcontainer.json:198` ``. The diff added 3 lines to that
file's header comment, so `initializeCommand` moved to **201**; line 198 is now
`"forwardPorts": [2222],`.

Control-armed — every *other* line citation in the diff resolves, so the probe
discriminates: `renovate_dryrun.py:98,99` ✓ (`GITHUB_API_TOKEN`,
`MISE_GITHUB_TOKEN`), `Dockerfile:311,564` ✓ (`export
MISE_GITHUB_TOKEN="$GITHUB_TOKEN"`), `mise.toml:615` ✓
(`[tasks.renovate-dryrun]`), `graph_bakeoff.py:618` ✓ (`"env_key":
"NVIDIA_API_KEY"`), `on-create.sh:54` ✓ (`mise install -y`),
`suites.toml:507-511` ✓, `mise.toml:251,277,771` ✓. 7 of 8 correct, 1 broken by
this commit.

Nothing catches it: `hk.pkl:448` `doc_refs` globs
`AGENTS.md`/`**/AGENTS.md`/`.claude/rules/*.md`/`.claude/skills/**/*.md` —
`docs/*.md` is outside it, and it validates path existence, not line numbers.

---

## JUDGEMENT CALLS

### J1 — Shotgun Surgery, and it is real, not tool-forced

One fact ("which Doppler config") is written in **6** places:
`mise.toml:251`, `:277`, `:771`, `devcontainer.json:201`'s
`${DOPPLER_CONFIG:-dev_personal}` fallback, plus the `:69` comment and two prose
docs. The three `mise.toml` literals are *not* forced — `BASE_IMAGE` and
`DEVCONTAINER_SSH_PORT` are duplicated across the same tasks too, but they at
least route through one templated default. Fixing H1 collapses the override
surface to one place and makes the JSON fallback the single literal.

### J2 — Duplicated prose: the same rationale narrative, three times

The "43 ⊂ 49, the 6 extras are host-side, the accepted cost is `AGE_PRIVATE_KEY`"
argument is written at three different lengths: `.devcontainer/AGENTS.md:53-61`
(9 lines), `devcontainer.json:69-74` (6 lines), and
`docs/secrets-doppler-fnox-keychain.md:117-150` (the full version). The repo's
own remedy is documented — `md-size-budgets.md`: "move reference content to a
sibling doc and **link it by path**". The two short copies should be one
sentence plus a link to the doc.

### J3 — `.devcontainer/AGENTS.md` headroom is now 5.6%

11,334 B against agnix AGM-003's hard 12,000-char ceiling — **666 B left**, and
this diff spent ~640 B of it. `md-size-budgets.md` calls AGM-003 the binding
constraint for an `AGENTS.md` ("Both must pass; for an `AGENTS.md`, AGM-003 binds
first"). J2's fix is also the fix here.

### J4 — The smoke probe cannot tell which config was downloaded

The diff states the gap honestly for the contract
(`suites.toml:507-511` "name no config at all … A wrong `DOPPLER_CONFIG` stays
green"), but the same blindness sits in `scripts/devcontainer-smoke.sh:59`, which
the diff did not touch:

```sh
doppler_count=$(env | grep -cE "^(DOPPLER_PROJECT|DOPPLER_CONFIG|DOPPLER_ENVIRONMENT|EXA_API_KEY|GITHUB_TOKEN|BRAVE_API_KEY|GEMINI_API_KEY)=" || true)
```

Every one of those 7 canaries is in **both** configs (`dev` ⊂ `dev_personal`), so
the tier-3 probe passes identically under either — `probes-need-a-control-arm.md`
rule 1/8: it is armed for "no secrets" but has only one face for "wrong config".
A `dev_personal`-only canary (`NVIDIA_API_KEY`, or a `DOPPLER_CONFIG` value
assert) would make it discriminate, at near-zero cost, and would be the one thing
that actually pins the 6 duplicated literals in J1 together.

### J5 — A named-but-unticketed deferred gap

`zero-skip-policy.md` rule 4: an approved deferral gets "a GitHub Issue … with
the full context". The rewritten section states the contract gap is "unchanged"
and that the `DOPPLER_TOKEN` swap is "**Stated as unblocked, not as verified**" —
both correctly hedged, neither carrying an issue number. Compare the surrounding
prose, which cites `#83`, `#487` freely.

---

## Not findings (checked, clean)

- **`doctor.toml` untouched** — I checked whether `.claude/CLAUDE.md`'s "changing
  your setup means changing `doctor.toml` in a reviewed diff" binds. It does not:
  `doctor.toml` pins the fnox `env_true` 50-name set, which is unchanged, and it
  has never modelled `DOPPLER_CONFIG` (grep: 0 hits; control `DOPPLER_TOKEN` → 1
  at `:52`). The diff's own claim that "`doctor.toml` models `dev_personal` only"
  is accurate in that indirect sense.
- **Evidence discipline in the new prose is good** — the two-route control arm on
  mise's token priority (cached `llms-full.txt:4004-4008` **and** live
  `jdx/mise:src/env.rs:591`, with a bogus-var control), the `fnox` → "0 lines,
  control gh/uv/python → 15" arm, and the explicit "decided knowingly … Do not
  'fix' it back" all satisfy `probes-need-a-control-arm.md` rules 5 and 6. The
  section that admits the file "has now been wrong about `dev` twice in opposite
  directions" is the correct handling per `verify-before-advancing.md`'s
  provenance note.
- No baseline smell beyond J1/J2 applies — there is no code here to carry
  Feature Envy, Primitive Obsession or Repeated Switches.

## GitHub repos touched

- [jdx/mise](https://github.com/jdx/mise) — cited in the diff as `src/env.rs:591`
  for the GitHub-token priority chain; verified only as a citation, not fetched.
