# Run D — jdx/astral/chezmoi release-note mining: features that retire custom code

Synthesis of 5 angle reports (`docs/research/runs/research-20260709-r2-release-mining/agents/{mise-core,hk-pkl-pitchfork,astral,fnox-secrets,chezmoi-renovate}.md`) plus a completed 3-vote adversarial re-verification pass on the 10 load-bearing claims (`/tmp/claude-0/.../tasks/wnjt104lk.output`, `claimsVerified`). Window mined: 2026-01 through 2026-07-09. Today is 2026-07-10. Grounding baseline: `docs/research/runs/research-20260709-r2-inventory/report.md`. Tools covered: mise, hk, pklr, pitchfork, fnox, mise-env-fnox, jdx/renovate-config, uv, ruff, ty, chezmoi.

## Executive summary

Nothing in this window fully retires either of the two headline custom-code items agents were sent to check: `python/src/dotfiles_setup/lint.py`'s hk-timeout wrapper stays (hk has shipped **no** native timeout through 1.50.0, confirmed 3/3 by verification; mise's own native per-task `timeout` — shipped v2026.2.20 — is already layered *above* it as a 700s backstop and was deliberately kept as a non-replacement, confirmed 3/3), and `hk.pkl` stays as the lint engine (pklr's evaluator is still maturing at a 12-releases-in-4-weeks cadence). Four concrete, low-risk wins are ready to ship now; three medium-risk retirements are ready to stage behind a CI probe; the rest is watch-only.

**Ship now (low risk):**
1. Add `--minimum-release-age 7d` to both `mise lock` invocations in `.github/actions/lock-refresh/action.yml:31,58` — closes the PR #169 lock/install cutoff fail-close class at the source. The flag is real and live, but note the correction below: it shipped in **v2026.5.6 (2026-05-11)**, not v2026.5.7 as originally cited.
2. Fix the ruff/py3.14 comma-except doc collision in `python/AGENTS.md` — ruff 0.15.20 (already in `uv.lock`) is *today* rewriting `except (A, B):` → `except A, B:` under PEP 758 on `target-version = py314`, directly contradicting the repo's own documented trap rule.
3. Harden the `no_lint_skip` grep at `hk.pkl:98` for spaced suppression forms (`# ruff: disable[...]`) — ruff 0.15.0 stabilized these and the current grep only catches the space-less variants.
4. Add an explicit Renovate `"schedule"` override in `renovate.json` — the inherited `github>jdx/renovate-config` preset silently throttled ordinary PR creation to Fridays-only (since 2026-04-04), contradicting the repo's own `prConcurrentLimit`/`prHourlyLimit` throughput settings.

**Stage behind a CI probe (medium risk):**
5. Flip `github_attestations = true` in `mise-system.toml` (token-free attestation path shipped: PR #10127 → v2026.5.16, per-tool disable → v2026.7.0), then delete `strip_provenance()`/`_has_provenance_key()` in `lock_refresh.py:178-221` **only after** a green CI probe — `lock_refresh.py`'s own docstring notes provenance is still recorded regardless of the setting, so "unlocked" means the blocker cleared, not that the flip is already proven safe.
6. Drop `experimental = true` from `.devcontainer/mise-system.toml:119` once `.devcontainer/Dockerfile`'s `MISE_VERSION` ARG bumps to ≥2026.7.4 (lockfile, conda, and bootstrap have all graduated). **Important correction surfaced by verification**: the root `mise.toml:47` host-side `experimental = true` line is a *separate, unpinned* mise install on Ray's Mac not gated by that Dockerfile ARG at all — treat as two independent actions, not one.
7. Design (Run E to build): replace the host-side Doppler `initializeCommand` download (`devcontainer.json:198,84-88`) with in-container fnox+doppler. Confirmed 3/3: mise has zero native Doppler support; fnox's doppler provider is the jdx-native answer and fnox already ships unused in `mise-runtime.toml:41`. But the `mise-env-fnox` plugin specifically is **not ripe** (dormant, zero releases, author's own "I would probably advise avoiding this," an unfixed race condition — its issue #3 — that is exactly this repo's mise-managed-fnox configuration) — use the plugin-free mechanisms instead (`fnox activate`, `fnox exec`, or the new v1.30.0 `fnox mcp env="exec"` scoping).

**Watch only:** hk 1.48 group-inherited step settings (groups are execution barriers — would serialize the parallel lint gate), `hk test`/`tests{}` (no sandboxing upstream), `uv check`/`uv format`/`uv audit` (all still preview/being redesigned), ty 1.0 stabilization (still 0.0.x), mise monorepo unified lockfiles, `mise dotfiles`, pitchfork (not installed — cross-ref for Run F), and the preset's inherited `lockFileMaintenance`/`postUpgradeTasks: mise lock` (Mend-hosted postUpgradeTasks allowlist is undocumented — read the repo's own Renovate job log before acting).

## Retire / Adopt / Watch table

| # | Feature | Version (date) | Replaces / touches in-repo | Verdict | Risk | Adoption sketch |
|---|---|---|---|---|---|---|
| 1 | mise native per-task `timeout` | v2026.2.20 (2026-02-25) | Already adopted as backstop, `mise.toml:121-134` — does **not** retire `lint.py` (no hk-log-tail diagnostics on expiry) | **KEEP custom** (`lint.py`) | low | None; re-check if mise ever adds an on-timeout output-capture hook |
| 2 | `mise lock --minimum-release-age` | **v2026.5.6 (2026-05-11)** — corrected, see § Refuted | PR #169 fail-close class; `minimum_release_age_excludes` (`mise-runtime.toml:33`) | **ADOPT** | med (flag has no per-tool excludes → AI-CLI locks age to 7d unless kept excluded) | Add `--minimum-release-age 7d` to `lock-refresh/action.yml:31` and `:58`; decide excludes fate in the same PR |
| 3 | Versions-host token-free attestations + per-tool disable | PR #10127 → v2026.5.16 (2026-05-28); per-tool disable v2026.7.0 (2026-07-02, PR #10694) | `strip_provenance()`/`_has_provenance_key()` (`lock_refresh.py:178-221`) + blanket `github_attestations=false`/`slsa=false` (`mise-system.toml:151-156`) | **ADOPT, staged** | med (mise-versions.jdx.dev flakiness, jdx/mise#10284; `lock_refresh.py`'s own docstring says provenance is recorded regardless of the setting) | Flip `github_attestations = true`, per-tool-disable any tool missing from the cache, one CI probe build, delete `strip_provenance()` only after green |
| 4 | Feature graduations: lockfile / conda / bootstrap+dotfiles | v2026.2.0 / v2026.5.0 / v2026.7.4 (2026-07-09) | `experimental = true` at `mise.toml:47` (host) and `mise-system.toml:119` (image) | **ADOPT, two separate actions** | low | Image line: after Dockerfile `MISE_VERSION` ≥2026.7.4, drop, gate on CI + `mise doctor`. Host line: independently check the actual host mise version first — it is **not** gated by the Dockerfile ARG at all |
| 5 | fnox doppler provider (mise has no native Doppler/SOPS-only) | v1.20.0 (2026-04-04) | Host-side `initializeCommand` Doppler download chain (`devcontainer.json:198,84-88`) — issue #83 | **ADOPT-candidate (design, Run E builds)** | med (doppler CLI in image; host `DOPPLER_TOKEN` bootstrap not eliminated, only shrunk; 3 contracts to rewrite) | `doppler="latest"` in `mise-runtime.toml`; new `fnox.toml` `[providers] doppler={...}`; shrink initializeCommand to single-token handoff; activate via chezmoi shell template or `fnox exec` |
| 6 | fnox `mcp` broker + v1.30.0 `env="exec"` secret state | 1.30.0 (2026-07-09) | AI CLIs (`mise-runtime.toml:57-61`) currently inherit every secret via `--env-file` | **ADOPT-candidate (highest value)** | med — interacts with the `no_mcp_registration` hk step; needs `mcp2cli`-style spawn or an approved exception | Scope claude-code/codex/gemini-cli away from the full secret set; release notes explicitly cite preventing exposure to "inherited processes like AI coding agents" |
| 7 | mise-env-fnox plugin | unreleased; last commit 2026-03-09 | Would-be replacement for the same initializeCommand path; referenced by `.devcontainer/AGENTS.md`'s "Future: migrate to mise-env-fnox … (#83)" note | **WATCH — do NOT adopt** | high (author warns against it; issue #3 is an unfixed race with mise-managed fnox — exactly this repo's setup; fail-open on error) | Revisit only if it ships a release + fixes #3; correct the AGENTS.md future-note to point at plugin-free mechanisms instead |
| 8 | hk native timeout | does not exist through 1.50.0 (2026-07-06) | `lint.py`, `mise.toml [tasks.lint]` | **KEEP custom** | n/a | Refresh `lint.py`'s docstring "verified through 1.50.0"; re-check every hk release |
| 9 | hk cross-file version-parity check | already shipped in-repo | `hk.pkl:279-283` (`hk_version_parity`) + `min_hk_version` (`hk.pkl:19`) | **DONE** | — | Bump `min_hk_version` opportunistically when a 1.50-only feature is relied on |
| 10 | hk 1.48 group-inherited step settings | 1.48.0 (2026-06-11) | `prefix` duplication on 2 ruff steps (`hk.pkl:55-61`) | **WATCH** | groups are execution barriers → would serialize the parallel lint gate | Revisit if `glob`/`batch` become inheritable without the barrier semantics |
| 11 | hk step `tests{}` / `hk test` | 1.47.0 (2026-06-09) | Deferred probe note (`hk.pkl:361-367`) | **WATCH, stay deferred** | writes real files into `python/src/` (no sandbox upstream) | Adopt once upstream sandboxes; candidate upstream contribution |
| 12 | pklr 1.1.x evaluator semantics fixes | 1.0.0→1.1.3 (2026-06-09→07-06); hk 1.50.0 embeds 1.1.2 | 3 pkl configs' import/spread/amends | **ADOPT (process, not code)** | evaluator semantics still maturing (12 releases/4 weeks; `&&`/`\|\|` short-circuit only fixed 1.1.1, late June) | Re-run the pklr↔pkl `--plan -J` byte-diff parity probe on every hk pin bump; keep pkl CLI 0.31.1 as the oracle — do not retire it |
| 13 | pitchfork supervision suite | v1.0.0→v2.16.0 (2026-01-19→07-07) | Nothing today (not installed) | **WATCH → Run F** | one breaking release (v2.0.0) in-window; weekly minor cadence | Candidate for supervising host-side initializeCommand prereqs (Doppler refresh, SSH-sock chown) as launchd-registered daemons |
| 14 | uv auto Python download (`python-downloads=automatic`) + `uv python install --default` | long-stable; `--default` is preview | `.claude/settings.json:15` PreToolUse hook — bricked without Python ≥3.14 (this exact session's failure) | **ADOPT (bootstrap)** | low | Remote-session bootstrap: install uv binary → `uv python install 3.14`; hook self-heals. Retires nothing but un-bricks Bash |
| 15 | ruff 2026 style: PEP 758 unparenthesized `except A, B:` on py314 | 0.15.0 (2026-02-03), live in `uv.lock` at 0.15.20 | `python/AGENTS.md` comma-except trap + `feedback_python2_comma_except` memory | **ADOPT (doc fix)** | low | Update AGENTS.md + memory: on py314 the formatter owns this; the old safety rationale is obsolete |
| 16 | ruff spaced suppressions `# ruff: ignore/disable/file-ignore` | stabilized 0.15.0 | `no_lint_skip` grep (`hk.pkl:98`) misses spaced forms | **ADOPT (guard hardening)** | low | Extend the grep alternation to tolerate whitespace after `ruff:` |
| 17 | `uv check` (ty runner) | 0.11.18 (~2026-06) | `py_ty` custom step (`hk.pkl:77`) | **WATCH** | med — surface actively redesigned (astral-sh/uv#19768) | Re-evaluate once it grows ruff + per-path scoping; today can't express the T12 path set |
| 18 | `uv format` | preview gate `format` (since 0.8.13) | hk ruff builtins (`hk.pkl:55-60`); dev-group ruff pin | **WATCH** | med (still preview) | Revisit when the gate drops; could eventually retire the dev-group `ruff` entry, not the hk steps |
| 19 | `uv audit` (+ `UV_MALWARE_CHECK=1`) | preview, 0.11.15-22 (blog 2026-06-08) | Nothing today; complements async Trivy in `image-analysis.yml` | **WATCH/PILOT** | low | Add a non-gating `uv audit` lint-lane step once it leaves preview |
| 20 | ruff `--add-ignore` | 0.15.21 (2026-07-09) | Zero-skip policy | **REJECT** | — | Bulk-suppression is exactly the anti-pattern `zero-skip-policy.md` bans; add as a named violation example |
| 21 | ty 1.0 stabilization | targeted late 2026 | `py_ty` step, ty bump cadence | **WATCH** | med (diagnostics can change between any 0.0.x) | Keep deliberate `uv lock --upgrade-package ty` bumps; budget for new Pydantic diagnostics (0.0.57+) |
| 22 | chezmoi `--error-on-conflict` | v2.71.0 (2026-07-07) | Silent `--force` in `.devcontainer/scripts/on-create.sh:41` | **ADOPT** | low (probe `--no-tty` interplay first) | Bump `.chezmoiversion` → 2.71.0, swap `--force` → `--error-on-conflict` |
| 23 | chezmoi unknown-config-field detection | v2.70.1 (2026-04-08) | Manual template-typo review in `chezmoi-check` skill | **ADOPT (doc-only)** | none (already live at installed 2.70.5) | Note in `.claude/skills/chezmoi-check/SKILL.md` |
| 24 | Renovate preset `schedule` (Friday-only since 2026-04-04) | preset commit `63ff75f` (2026-04-04) | Misconfiguration, not code — `renovate.json` sets no `schedule` key | **ADOPT** | med — silently contradicts the repo's own throughput overrides | Add `"schedule": ["at any time"]` to `renovate.json`, or document deliberate acceptance |
| 25 | Renovate preset `lockFileMaintenance` (7-day age) | preset commits `96d8f88`/`bb598c4` (2026-04-23) | Overlaps the daily lock-refresh composite for root `mise.lock` | **WATCH** | low | Decide whether inherited LFM PRs and lock-refresh double-cover; consider disabling one |
| 26 | Renovate preset `postUpgradeTasks: mise lock` | preset commit `36dfaea` (2026-07-06) | Candidate partial retirement of lock-refresh (root/shared tiers only) | **WATCH** | med — Mend-hosted postUpgradeTasks allowlist is undocumented; devcontainer tiers (hyphen-named, all-`latest`) are outside the manager's file patterns regardless | Read `allowedCommands` from this repo's own Renovate job log before acting; lock-refresh survives for the image tiers no matter what |
| 27 | Renovate native mise manager: `conf.d` coverage + native `mise.lock` updates | current docs | No custom manager needed for `shared.toml` bumps | **KEEP (confirms status quo)** | none | Verifies e.g. chezmoi 2.70.5→2.71.0 bumps natively |
| 28 | Repo's 6 surviving customManagers (hk pkl schema, `.chezmoiversion`, clang-p2996, gcc-latest, ubuntu digest, MISE_VERSION) | — | `renovate.json:33-97` | **KEEP ALL 6** | — | Preset has zero customManagers of any kind — none absorbed |

## 1. mise (jdx/mise) — v2026.1.0 → v2026.7.5

Full detail: `agents/mise-core.md`. Cadence ≈75 releases in 26 weeks. The local mintlify cache (`docs/research/mintlify-cache/jdx/mise/llms-full.txt`) is materially incomplete — zero hits for "timeout", only one incidental hit for "lockfile" — every finding was verified against the live CHANGELOG/docs rather than the cache, per `tool-currency-and-native-first.md`.

- **Per-task `timeout`** (v2026.2.20, 2026-02-25) — already adopted as a 700s outer backstop above `lint.py`'s 600s wrapper (`mise.toml:121-134`, decision-15 comment, #160 T12.5). **CONFIRMED 3/3, no further action**: mise's native timeout kills the child via SIGTERM+5s grace+SIGKILL but has no equivalent to `lint.py:79-129`'s `_print_log_tail` hk-log-tail diagnostics.
- **`mise lock --minimum-release-age`** — real flag, confirmed live at `mise.jdx.dev/cli/lock.html`. **Shipped in v2026.5.6 (2026-05-11), not v2026.5.7 (2026-05-13)** — see § Refuted. The gap it closes is real: `.github/actions/lock-refresh/action.yml:31,58` calls bare `mise lock` with no cutoff flag, while `.devcontainer/mise-runtime.toml:25-33` carries `minimum_release_age_excludes` for the PR #169 fail-close class. **Adopt**: add `--minimum-release-age 7d` to both invocations; decide in the same PR whether the excludes line can drop.
- **Token-free attestations** — PR #10127 merged 2026-05-28, shipped v2026.5.16; per-tool `github_attestations` disable shipped v2026.7.0 (PR #10694, 2026-07-02). CONFIRMED at 2/3 votes upheld — the third verifier flagged that `lock_refresh.py`'s own docstring says provenance is still recorded regardless of the attestation setting, so the flip has not been implemented or CI-tested end to end. **This unlocks, but does not yet execute**, retirement of `strip_provenance()`/`_has_provenance_key()` (`lock_refresh.py:178-221`) and the blanket `github_attestations=false`/`slsa=false` (`mise-system.toml:151-156`). Stage carefully; watch jdx/mise#10284 (mise-versions.jdx.dev flakiness).
- **Feature graduations**: lockfile (v2026.2.0), conda (v2026.5.0, PR #9544), bootstrap+dotfiles (v2026.7.4, 2026-07-09). CONFIRMED, but one verifier caught a real bug in the pre-verification action step: `mise.toml:47`'s `experimental = true` is the **host** config on Ray's Mac — not gated by `.devcontainer/Dockerfile`'s `MISE_VERSION` ARG at all; only `.devcontainer/mise-system.toml:119` is. **Treat as two independent actions.**
- **Secrets**: mise has zero native Doppler support; native secrets = SOPS + direct age only. CONFIRMED 3/3. The jdx-native path for Doppler is fnox's `doppler` provider via plugin-free mechanisms — see § 4.
- **Stability signal, CONFIRMED 3/3**: in-window renames `[system.packages]`→`[bootstrap.packages]`, `prepare`→`deps`, `--before`→`--minimum-release-age`. Docs lag the CHANGELOG — changelog-first verification is not optional for this tool.

## 2. hk + pklr + pitchfork (jdx universe)

Full detail: `agents/hk-pkl-pitchfork.md`. Repo is already pinned to hk's newest release (1.50.0).

- **hk has no native timeout through 1.50.0** — CONFIRMED 3/3 (zero CHANGELOG mentions, no `timeout` key/`HK_TIMEOUT` env var). `lint.py`'s process-group timeout wrapper is **not retired**. Refresh its docstring to "through 1.50.0"; re-check on every hk bump.
- **hk cross-file version-parity check is already shipped** — CONFIRMED 3/3 by direct file read: `hk.pkl:279-283` (`hk_version_parity`, step "check-H") in parity at 1.50.0.
- **hk 1.48 group-inherited step settings** — real, but groups are execution barriers; not worth serializing the parallel lint gate. **Watch**, don't adopt. `hk test`/step `tests{}` (1.47.0) stays deferred (no sandbox upstream).
- **pklr (1.0.0→1.1.3): 12 releases in 4 weeks**, essentially all evaluator-semantics fixes. hk 1.50.0 pins pklr 1.1.2. **Adopt (process)**: re-run the pklr↔pkl parity probe on every hk pin bump; keep the pkl CLI 0.31.1 pin as the oracle.
- **pitchfork (v1.0.0→v2.16.0)**: not installed — cross-reference for Run F. Natural candidate for supervising devcontainer `initializeCommand` host-side prerequisites.

## 3. astral (uv, ruff, ty) — not cached, verified via remote fetch only

Full detail: `agents/astral.md`. Astral joined OpenAI's Codex team (2026-03-19); release velocity has not visibly dropped.

- **uv auto-downloads missing Python interpreters** (`python-downloads` defaults to `automatic`). This session's own PreToolUse-hook failure ("no Python ≥3.14") is an environment-bootstrap gap uv already solves. **Adopt** for constrained/remote sessions: install the uv binary → `uv python install 3.14`; the hook self-heals.
- **ruff 0.15.0 PEP 758 formatter change collides with repo doc guidance.** On `target-version = py314`, ruff format strips parens around exception tuples (`except (A, B):` → `except A, B:`) — but `python/AGENTS.md`'s comma-except trap says the opposite, and ruff 0.15.20 is already live in `uv.lock`. **Adopt (doc fix), immediately.**
- **Suppression-guard gap**: ruff 0.15.0 stabilized `# ruff: disable[...]` spaced block suppressions; `no_lint_skip` grep (`hk.pkl:98`) only matches space-less forms. **Adopt**: extend the grep.
- **`uv check`/`uv format`/`uv audit`**: real and shipping but thinner than the repo's hk-driven staged-file steps; **Watch**. **Reject and log**: `ruff check --add-ignore` (bulk-suppression, banned by zero-skip-policy).
- **ty**: still 0.0.x/beta, weekly cadence, stable targeted ~late 2026. No retirement candidate; the repo's unpinned-plus-locked-freeze posture is correct.

## 4. fnox + mise-env-fnox (secrets angle, issue #83)

Full detail: `agents/fnox-secrets.md`. CONFIRMED 3/3: mise has no native Doppler support; fnox's doppler provider is the jdx-native path; fnox already ships unused in the runtime tier.

- **fnox doppler provider (v1.20.0, 2026-04-04)**: mature (1.9k stars, 11 minor releases in ~3 months). A doppler-CLI wrapper, so it needs the Doppler CLI in the image; the container still needs a `DOPPLER_TOKEN` service token — bootstrap shrunk, not eliminated.
- **mise-env-fnox is NOT ripe** — 15 stars, 7 commits, zero releases, dormant 4 months; author writes "I would probably advise avoiding this"; open issue #3 (race with mise-managed fnox) is exactly this repo's config. **Watch, do not adopt the plugin.** Correct `.devcontainer/AGENTS.md`'s "Future: migrate to mise-env-fnox" note.
- **Plugin-free fnox alternatives, all shipped**: `fnox activate`, `fnox exec -- <cmd>` (with `FNOX_IF_MISSING=error`), and **v1.30.0's `fnox mcp env="exec"`** secret state, whose release notes explicitly cite "preventing exposure to inherited processes like AI coding agents" — the single highest-value fnox feature for this repo, since today's `--env-file` path broadcasts every secret to claude-code/codex/gemini-cli. Any MCP-broker use routes through `mcp2cli`, not the Claude CLI's `mcp add` subcommand (per `no_mcp_registration`).

## 5. chezmoi + jdx/renovate-config

Full detail: `agents/chezmoi-renovate.md`.

- **chezmoi v2.71.0 `--error-on-conflict`**: adoption candidate for `on-create.sh:41`'s silent `--force`. **Adopt**: bump `.chezmoiversion` → 2.71.0, swap `--force` → `--error-on-conflict` (probe `--no-tty` interplay first).
- **v2.70.1 unknown-config-field detection** already live at installed 2.70.5 — doc-only note in `chezmoi-check` skill.
- **jdx/renovate-config preset audit** — CONFIRMED 3/3: the preset has **zero customManagers**; **all 6 of the repo's customManagers survive** (none absorbed).
- **Inherited-preset gaps** (misconfiguration, not code): (1) preset gained a **Friday-only schedule** (2026-04-04) that the repo's throughput overrides contradict — add `"schedule": ["at any time"]`. (2) preset's `lockFileMaintenance` (7-day age) may overlap the daily lock-refresh — watch. (3) preset's `postUpgradeTasks: mise lock` (2026-07-06) is a candidate partial retirement of lock-refresh for root/shared tiers only, but Mend's hosted allowlist is undocumented — read the repo's own Renovate job log first; lock-refresh survives for the hyphen-named image tiers regardless.

## Refuted / unverified claims

One of the ten adversarially-verified claims is **REFUTED** on its stated evidence (0/3 upheld); the other nine are CONFIRMED, two with load-bearing nuance folded into the sections above.

- **REFUTED — `mise lock --minimum-release-age` version/date.** The claim asserted the flag shipped in v2026.5.7 (2026-05-13). All three verifiers independently checked the `jdx/mise` CHANGELOG and PR #9269 (merged 2026-05-10) and found it shipped one release earlier, in **v2026.5.6, released 2026-05-11** — v2026.5.7's changelog contains no mention of `lock`/`minimum-release-age`/`ls-remote`. **The underlying mechanism and adoption argument are NOT refuted**: the flag is real, live, documented; the composite genuinely doesn't use it; the excludes workaround genuinely exists. **Use v2026.5.6 (2026-05-11) in any downstream doc/PR — do not cite v2026.5.7.**

Nuances on CONFIRMED claims a downstream implementer must not drop:

- **Experimental-flag drop** — CONFIRMED, but the action step conflates two independent mise installs: `mise.toml:47` (host) is NOT governed by the Dockerfile ARG; only `mise-system.toml:119` is. Two separate actions.
- **Token-free attestation "unlocks retirement"** — CONFIRMED at 2/3. The dissenting verifier noted the flip has not been implemented or CI-tested end to end, and `lock_refresh.py`'s docstring says provenance is still recorded regardless. "Unlocked" = the blocker cleared, not "safe to merge unverified."

## Open questions for Ray

1. **Ship `mise lock --minimum-release-age 7d` on the composite now?** Recommended: yes — low risk, closes a real fail-close bug class. Decide excludes fate in the same PR.
2. **Attestation flip + `strip_provenance()` deletion — stage behind a CI probe?** Recommended: one CI probe build first; don't delete `strip_provenance()` until green.
3. **Experimental-flag drop — image line now, host line after checking the host version?** Recommended: yes for image (CI + `mise doctor` gated); investigate the host version independently.
4. **Hand the fnox+doppler in-container migration to Run E?** Recommended: yes — tool-side ripeness confirmed, plugin-free mechanisms are the path. Correct the AGENTS.md note in the same change.
5. **Renovate `schedule` override?** Recommended: add `"schedule": ["at any time"]` — the repo's own throughput settings signal an intent the inherited Friday-only schedule contradicts.
6. **`chezmoi --error-on-conflict` swap?** Recommended: cheap, low-risk — probe and ship with the `.chezmoiversion` bump.
7. **ruff/py3.14 comma-except doc correction now?** Recommended: yes, immediately — ruff 0.15.20 is already contradicting the documented guidance today.

## GitHub repos touched

- [jdx/mise](https://github.com/jdx/mise) — CHANGELOG, releases v2026.2.0 / v2026.2.20 / v2026.5.0 / v2026.5.6 / v2026.5.16 / v2026.7.0 / v2026.7.4 / v2026.7.5, PR/issue #9269, #10127, #10284, #10694, live docs, cached llms.txt
- [jdx/hk](https://github.com/jdx/hk) — CHANGELOG, Cargo.lock @v1.50.0, releases v1.44.0–v1.50.0, live docs
- [jdx/pklr](https://github.com/jdx/pklr) — CHANGELOG 1.0.0–1.1.3
- [jdx/pitchfork](https://github.com/jdx/pitchfork) — CHANGELOG v1.0.0–v2.16.0; cached mintlify docs
- [jdx/fnox](https://github.com/jdx/fnox) — CHANGELOG, releases (incl. v1.30.0), doppler provider source, cached llms-full.txt
- [jdx/mise-env-fnox](https://github.com/jdx/mise-env-fnox) — README, commit history, issues #1/#3/#8/#11/#13
- [jdx/renovate-config](https://github.com/jdx/renovate-config) — commit history since 2026-01, verbatim `default.json` audit
- [renovatebot/renovate](https://github.com/renovatebot/renovate) — docs (mend-hosted, modules/manager/mise), discussion #16555
- [twpayne/chezmoi](https://github.com/twpayne/chezmoi) — releases v2.69.2–v2.71.0, cached mintlify docs (flagged stale)
- [astral-sh/uv](https://github.com/astral-sh/uv) — CHANGELOG, releases 0.11.x, docs, issue #19768
- [astral-sh/ruff](https://github.com/astral-sh/ruff) — releases 0.15.0–0.15.21, v0.15.0 blog, suppression docs
- [astral-sh/ty](https://github.com/astral-sh/ty) — releases 0.0.49–0.0.57, beta announcement
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — all in-repo file:line grounding across all five angles (mise.toml, mise tiers + locks, lint.py, lock_refresh.py, lock-refresh action, Dockerfile, hk pkl trio, shared.toml, pyproject.toml, uv.lock, settings.json, devcontainer.json, .devcontainer/AGENTS.md, renovate.json, .chezmoiversion, on-create.sh, suites.toml, devcontainer-smoke.sh, issue #83)
