# Evidence — `tool-currency-and-native-first`

Archaeology and provenance behind
`.claude/rules/tool-currency-and-native-first.md`. Extracted from the rule so the
eager copy carries the directive and this file carries the case history. Read it
when you want to know *why* a line in that rule is worded the way it is, or
before changing one.

## The conda-lockfile case — and the two-week contradiction it left behind

*(r3 probe round, 2026-07-10; corrected in the rule 2026-07-24.)*

An earlier revision of the rule claimed mise's rattler `conda:` backend writes
per-platform `sha256` + transitive deps to `mise.lock` as of **v2026.5.0**, and
that this *retires* the custom `mise-system-resolved.json` snapshot plus
`mise_snapshot.py`.

**That was wrong, and the probe said so: 0 of 3.** v2026.5.0 only graduated the
conda backend's **experimental flag**. Conda resolutions still land in **no
lockfile tier**, and native conda locking remained open upstream
(`jdx/mise#7700`).

The failure is itself an instance of the rule: the *assumption* that conda had
reached lockfile parity lagged the code, exactly as docs do.

**The second defect is the more expensive one.** The snapshot machinery had
already been deleted — `mise_snapshot.py` went in `352063a` (#160 T4–T13) — yet:

| Doc | What it said | Reality |
|---|---|---|
| this rule | "do NOT retire `mise_snapshot.py`" | already deleted for ~2 weeks |
| `tool-currency-check` skill | "RETIRED in #160 T1" | correct |

Two docs, opposite claims about the same file, neither checked against the
filesystem. The durable fact worth carrying forward is **the conda lockfile
gap**, not the file's existence.

## The other three verified cases

- **`minimum_release_age` / `lockfile` / `lockfile_platforms` are native.** No
  custom cooldown or platform-scoping machinery was ever needed.
- **Renovate's native `mise` manager + the `github>jdx/renovate-config` preset**
  made **8 of 11** hand-rolled `customManagers` redundant (PR #161). This is the
  canonical example kept in the rule.
- **`get_env()` vs the Tera `env.VAR` variable** (mise 2026.7.0). The
  *documented* function was insufficient for a `mise.local.toml` `[env]`
  override; only empirically probing both revealed which one the task actually
  needed. The native mechanism is the default answer — but *verify which native
  mechanism*. This is the evidence behind rule 4.

Stated twice by Ray (2026-07-04): the managed tools here (mise, hk, Renovate,
uv, docker, chezmoi) move fast and their **docs lag their code**, so the merged
CHANGELOG/PRs are often the only truthful source.

## The failure mode the rule prevents

Shipping — or preserving — homegrown machinery for a problem the tool already
solves. You pay maintenance cost forever, and often get a *weaker* result
(version-only vs sha256-verified) than the native path.

## How currency is checked now — the shared engine

The version-currency MECHANICS (in-sync validation, release-note review,
tracked-issue movement, the six-gate auto-apply bar, the committed report) live
in the shared `kb_setup.currency` engine — a pinned `uv` git dep on the
knowledge-base package, so both repos run ONE implementation (D2/G4; dotfiles'
old broad-sweep module was deleted).

What this repo declares is `currency.toml` (graphify is deep-tracked; hk/uv/etc.
ride the broad `mise outdated` sweep) plus two thin mise tasks:

| Task | Delegates to | When |
|---|---|---|
| `mise run tool-currency` | `kb-setup currency daily` | the daily report `refresh.yml` upserts as the standing issue |
| `mise run tool-currency-check` | `kb-setup currency check` | the offline step-1 drift check the SessionStart hook runs every session (silent unless drift) |

The engine tracks **versions**. The rule's remaining, un-automatable job is the
**native-first judgment** — is a piece of custom code now superseded by a tool
feature (the `mise_snapshot.py` → `mise.lock` class)? Only a human decides
retirement.

## Machine enforcement (partial — judgment cannot be automated)

- **`workflow.tool-currency-wiring`** (`python/verification/suites.toml`) asserts
  the whole chain: `currency.toml` → the two mise tasks → the `kb-setup` dep in
  `python/pyproject.toml` → `refresh.yml`'s daily job → the SessionStart hook.
- **`hk_version_parity`** (`hk.pkl`, SHIPPED) asserts `hk@<ver>` is identical
  across `hk.pkl` / `hk-common.pkl` / `hk-image.pkl` and matches the `mise.toml`
  binary pin — catching pin drift the rule would otherwise catch by hand.
- **Renovate PRs carry the CHANGELOG** — bump review IS release-note review.
- **agnix** structurally validates the rule file and the skill.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the rule,
  the mise tasks, PRs #160/#161, commit `352063a`.

_Named in the extracted text but **not** resolved during this extraction (do not
treat these as verified links): `jdx/mise` (issue #7700, the
`github>jdx/renovate-config` preset) and the knowledge-base sibling repo that
hosts `kb_setup.currency`._
