# Code review — SPEC axis — commit `5bce39f` (PR #522)

Diff: `git diff a7eecc2...HEAD` — 4 files, +84/-35.
Spec: scratchpad `spec-522.md` (handoff `.agent/plans/session-2026-08-03-e.md` + the
user's AskUserQuestion decision, which superseded the "do not arrive with a patch"
clause).

**Verdict: the diff faithfully implements the chosen option. One real defect (D1),
one nit. No scope creep.**

## Verified anchors

| Spec claim | Probe | Result |
|---|---|---|
| `mise.toml:251,277,771` → `dev_personal` | tree-wide `grep -rn DOPPLER_CONFIG` | ✅ all three; no `= "dev"` survives |
| `devcontainer.json` fallback also changed | same grep | ✅ `${DOPPLER_CONFIG:-dev_personal}` at `:201` (was `:198`). **The pin/fallback disagreement hazard does not exist anywhere** |
| `suites.toml` unchanged, gap not overclaimed | `git diff -- python/verification/suites.toml` → empty; prose reads "⚠️ **The contract still names no config, and that gap is unchanged.**" | ✅ correctly states the gap remains; no overclaim |
| `LINEAR_API_KEY` / `NVIDIA_20260705` retained, wrong finding retracted | grep | ✅ neither removed; docs:127 now reads "**other projects on this host** (Ray, 2026-08-03)". `grep "no consumer\|unused credential"` → rc=1 (control: `AGE_PRIVATE_KEY` in same file → hit) |
| `AGE_PRIVATE_KEY` cost recorded | read | ✅ three places: commit body ("Accepted cost, decided knowingly"), docs § "The accepted cost, stated rather than argued away", `.devcontainer/AGENTS.md` |
| `AGENTS.md:52` inversion complete | read | ✅ override now `DOPPLER_CONFIG = "dev"` (was `dev_personal`) |
| fnox 0 lines in image | `grep -c fnox mise-system.toml Dockerfile` → 0,0; **control** `-E "\bgh\b\|\buv\b\|\bpython\b"` → 4,8 | ✅ probe discriminates |
| mise token precedence | `mintlify-cache/jdx/mise/llms-full.txt:4004-4008` | ✅ verbatim: 1 `MISE_GITHUB_TOKEN`, 2 `GITHUB_API_TOKEN`, 3 `GITHUB_TOKEN` |
| Consumer citations | `renovate_dryrun.py:98,99` ✅ · `graph_bakeoff.py:618` (`env_key: NVIDIA_API_KEY`) ✅ · `Dockerfile:311,564` (`export MISE_GITHUB_TOKEN="$GITHUB_TOKEN"`) ✅ · `on-create.sh:54` (`mise install -y`) ✅ · `mise.toml:615` (`[tasks.renovate-dryrun]`) ✅ | all land |

## (a) Missing / partial

**M1 (partial, low).** The chosen option's PRO said the #487 RO token becomes
"trivial" to repoint. Not done — correctly, it was outside the option's text, and the
prose labels it "Stated as unblocked, **not as verified**". Honest, not a gap.

No gate was added. The user explicitly rejected "Keep split, add the missing gate",
so its absence is faithful, and the prose does not pretend otherwise.

## (b) Scope creep

**None.** All three files beyond `mise.toml` are necessary completion:

- `devcontainer.json:201` — the load-bearing one. Left at `:-dev`, a clone invoking
  `devcontainer up` without the mise task env would silently download the OLD config.
  Changing only `mise.toml:251,277,771` would have created exactly the hazard the
  brief asked about.
- `devcontainer.json:69` + `.devcontainer/AGENTS.md:50-52` — both stated
  `DOPPLER_CONFIG=dev` and documented the override in the **opposite** direction; the
  diff falsifies them.
- `docs/secrets-doppler-fnox-keychain.md` (the largest hunk) — its table asserted
  "`dev` → the devcontainer". Untouched, the repo's own secrets doc would contradict
  the code. Necessary.

## (c) Implemented but wrong

**D1 — MEDIUM: the documented per-clone opt-out does not work, and the diff
propagated it.** Commit body: *"`dev` is retained as a per-clone opt-out via
mise.local.toml."* Both edited docs spell it:

> `.devcontainer/AGENTS.md:52` — ``Override per-clone via `mise.local.toml`: `[tasks.up] env = { DOPPLER_CONFIG = "dev" }`.``
> `docs/secrets-doppler-fnox-keychain.md:108` — same form.

`mise.local.toml.example` forbids exactly this, verified on mise 2026.7.0:

> "WARNING: do NOT override by redefining a task (`[tasks.up]`, …). A `[tasks.<name>]`
> block in mise.local.toml **REPLACES the whole task** — it strips the task's `run`
> body, so `mise run up` silently becomes a no-op. Use `[env]` only."

`mise.toml:242-244` says the same. And the `[env]` escape hatch is unavailable here:
`BASE_IMAGE` / `DEVCONTAINER_SSH_PORT` are templated `{{ env.VAR | default(...) }}`,
but `DOPPLER_CONFIG` is a **literal**, so an `[env]` value is ignored. There is
therefore *no* working opt-out. Pre-existing (the old text said the same with
`dev_personal`), but this commit makes it load-bearing and edited both lines without
fixing it. Fix: template `DOPPLER_CONFIG` like its siblings and add it to
`mise.local.toml.example`'s "Overridable vars" list — which the diff also leaves
un-updated.

**N1 — nit.** The docs' control-arm citation "(control: gh/uv/python → 15)" measures
**12** by my grep shape (4 + 8). The arm fired non-zero, so the probe discriminates
and the claim stands; the number is imprecise.

## Spec checklist item 1 (the investigation)

Delivered in the commit body + the docs § "The 6 extras" table: all 6 names, a
consumer each, safe enumeration (`--only-names` counts only; no value in the diff or
message). Not persisted as a standalone agent artifact, but it was the main session's
own work, so `agent-report-persistence.md` does not bind.

## GitHub repos touched

- [jdx/mise](https://github.com/jdx/mise) — GitHub-token priority table, read from the
  local `docs/research/mintlify-cache/jdx/mise/llms-full.txt` (no network).
