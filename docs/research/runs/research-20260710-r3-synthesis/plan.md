# r3 Phased Implementation Plan

Supersedes the automation/knowledge portions of
`.omc/plans/plan-20260710-r2-implementation.md`. Derived from the r3 synthesis
(`./report.md`) and the five r3 domain reports. Ordering is by dependency, not
importance: each phase unblocks the next.

**Convention mandate (applies to every buildable item below):** repeated action
→ **skill** → **mise task** → **python library** (zero-bash-logic); sync every
doc that describes it in the same change; wire a hook/agent double-check; and
land it only when the mandatory-checks checklist is green.

**Mandatory-checks checklist (every phase):**
- [ ] `mise run lint` → rc=0
- [ ] `uv run --project python pytest tests/ -x -q` → all pass
- [ ] `dotfiles-setup verify run` → 0 failed
- [ ] `.github/**` changed → `mise run pin-actions`
- [ ] `AGENTS.md`/`CLAUDE.md`/`.claude/**/*.md` changed → `mise run lint-docs` + size limits
- [ ] image/`.devcontainer/**` changed → `mise run verify-local` (or `verify-container-latest`)
- [ ] PR checks watched to terminal green; post-merge `main` CI `conclusion == success`

---

## Phase 0 — Quick, unblocking, low-risk (do first, mostly one-liners)

Each is independently shippable and removes a blocker or a hazard.

1. **Correct the conda claim in `.claude/rules/tool-currency-and-native-first.md`.**
   Rewrite the "mise rattler conda backend now writes sha256 + transitive deps
   to `mise.lock` … retires the custom snapshot" passage to reflect the refuted
   finding (conda only graduated its *experimental flag* at v2026.5.0; `jdx/mise#7700`
   still open; conda is in no lockfile tier). Add a one-line "do NOT retire
   `mise_snapshot.py` on this basis." *Docs-only; lint-docs + size limits.* (D)
2. **Kill Friday-only:** add top-level `"schedule": ["at any time"]` to
   `renovate.json` to override the `github>jdx/renovate-config` preset gate.
   *Validate with `renovate-config-validator` (already pinned).* (C)
3. **Fix the runtime-lock omission bug** in `.github/workflows/refresh.yml`
   (~lines 107-111): add `.devcontainer/mise-runtime.lock` to the
   open-refresh-pr add-paths so it is committed, not regenerated-then-discarded.
   *`mise run pin-actions`.* (C)
4. **Add the 7th Renovate customManager** for `wagoodman/dive`'s
   `DIVE_VERSION: 0.13.1` (`.github/workflows/image-analysis.yml:102`), using the
   `github-releases` datasource shape already used for gcc-latest/`MISE_VERSION`. (D)
5. **Let Renovate bump `MISE_VERSION` 2026.7.2 → 2026.7.5** (do not hand-bump;
   its PR carries the CHANGELOG). This unblocks Phase 3's `experimental` drop.
   *No code change — just don't block the Renovate PR.* (D)

---

## Phase 1 — Event-driven trigger keystone (C)

Turn `refresh.yml` into the reusable core and make a Renovate PR the event.

1. **Extract `refresh.yml`'s job into a reusable workflow** (`on: workflow_call`,
   thin-caller "Shape A"). Must be a **workflow, not a composite action** —
   composites can't read the App-token secrets needed to mint the refresh token.
   The caller passes `secrets: inherit` (custom App secrets do not cross the
   `workflow_call` boundary automatically). (C)
2. **Embed it in `ci.yml`** as a job, and **trigger on Renovate PRs** via the
   existing `pull_request` event scoped at the job with
   `if: github.actor == 'renovate[bot]'` — **not** `pull_request_target` (no
   untrusted-code-with-secrets), **not** a trigger-level branch filter. Renovate
   branches are same-repo, so `pull_request` already carries full secrets. (C)
3. **Keep a DAILY safety-net cron** (never Friday-only) as the backstop, and
   **move both crons off the `:00` minute** given first-party-measured ~3h GHA
   scheduled-queue drift; soften the 00:00→02:00 stagger docs accordingly. (C)
4. **Preserve auto-merge:** wire the companion-lock-regen job into `ci-gate`'s
   `needs:`, make the push-branch step idempotent, and add the refresh App to
   Renovate's `gitIgnoredAuthors`. (C)

*Checklist: `.github/**` → `pin-actions`; watch PR checks to green.*

---

## Phase 2 — Close the tool-currency blind spot + automate release notes (D)

Make the "event" actually see all ~108 tools. Convention: extend the existing
`tool_currency.py` → `mise run tool-currency` → daily job → standing issue →
`tool-currency-check` skill chain; do not build a parallel system.

1. **Image-tier coverage** in `tool_currency.py`: scratch-copy
   `.devcontainer/mise-system.toml`→`config.toml` and `mise-runtime.toml`→
   `config.runtime.toml` into a temp dir and run `mise outdated --bump --json`
   with `MISE_CONFIG_DIR=<tmp>` (+ `MISE_ENV=runtime`), reproducing the
   Dockerfile's own load mechanism. **Do not** use "cd .devcontainer" — mise's
   cwd-walk never finds hyphenated filenames, and there is no `MISE_CONFIG_FILE`
   arbitrary-path var. Fold in the `.tmpl` interactive tier the same way. (D)
2. **Floating Docker-family (B2):** add a read-only
   `gh release list --repo <o>/<r> --json tagName,name,publishedAt` batch over a
   static list (moby/moby, moby/buildkit, docker/buildx, devcontainers/spec) into
   the SAME daily job → a second chronological table in the standing issue. (D)
3. **Tracked `watchlist.toml`** (`python/src/dotfiles_setup/watchlist.toml`), one
   row per tool tagged by `class`, seeded from the D-report Q1 table — so "did we
   catch every tool" becomes a diffable file forever. (D)
4. **Extend the `tool-currency-check` skill** with the new steps (image-tier
   double-run; B2 floating-watch reading; `mise install` stderr grep for
   `deprecated` per v2026.7.2). Judgment artifacts land at
   `docs/research/tool-currency/<date>.md` with a `## GitHub repos touched`
   footer. *Docs-only skill change → `lint-docs`.* (D)

---

## Phase 3 — mise-native retirements where they map cleanly (B, D)

Only after Phase 0/2 land and `MISE_VERSION ≥ 2026.7.4` is live in the built
`:dev` image (not just the Dockerfile ARG).

1. **Drop `experimental = true`** (`.devcontainer/mise-system.toml:119`, and the
   host `mise.toml:47` after checking the host mise version) in a **separate PR**
   gated by CI + `mise doctor`. bootstrap/dotfiles graduated stable at v2026.7.4. (D)
2. **Adopt `[bootstrap.macos.launchd.agents.*]`** to replace only the
   plist-authoring + drift-detection (`status --missing`) layer of r2 Run F's
   hand-rolled LaunchAgent. **Keep** the `dotfiles_setup.maintain` python module,
   the ntfy+healthchecks+gh-issue alerting, and the launchd-vs-pitchfork venue
   reasoning. Gate on a `--dry-run` + `mise bootstrap --help` check on the actual
   Mac host (feature ~4 weeks old; `start_calendar_interval` landed v2026.7.1).
   Host-only, out of R1/R2/R3 scope. (B)
3. **Re-probe `get_env()` vs `env.VAR`** (v2026.7.2 restored the helper) with one
   throwaway `mise.local.toml` probe before touching the `mise.toml:180-183`
   comment. Cheap, non-blocking. (D)

*Not in scope: mise `[dotfiles]` (A, refused); `mise generate bootstrap` allowlist
dodge (B, refuted); devcontainer login-shell via mise (B, collides).*

---

## Phase 4 — Knowledge / context pilot (E)

Decoupled from Phases 0-3; needs no approval to start the subagent half.

1. **Build two read-only librarian subagents** as `.claude/agents/*.md`:
   `mise-librarian` and `docker-family-librarian`. Frontmatter
   `tools: Read, Grep, Glob`, `model: haiku`; system prompt names a prioritized
   corpus file list (mintlify cache → r2/r3 research reports → live repo config)
   with an explicit cache-staleness caveat (cache last refreshed 2026-04-07) and a
   hard ~700-token response cap. `hk-librarian` as a "+1" only if the first two
   clear the bar. (E)
2. **Measurement harness** (`mise run pilot-measure`, logic in `python/`): compare
   **main-loop context growth** (not total tokens) across two arms (main-loop
   grep/read baseline vs subagent delegation), in `/clear`ed sessions, with a
   gold-key-facts coverage check paired to every token number. Instruments:
   `count_tokens` API (deterministic cross-check) + `/usage` + JSONL
   `isSidechain:false` parsing. **GO bar: median ratio ≤0.35 AND coverage ≥
   baseline on every query** (confirm the bar with Ray first). (E)
3. **Graphify seed — GATED, Mac-only, on explicit approval.** `graphify extract .
   --backend claude-cli` (+ `.graphifyignore` excluding
   `docs/research/mintlify-cache/`), committed to `docs/research/graph/`. Never in
   the hot query path; a future `GRAPH_REPORT.md` is just one more corpus file for
   the librarians. Check graphify issue #730 (cost cascade) fix status first. (E)

---

## Cross-cutting: the tracked-path migration

r2 research lives under `.omc/research/**` (not visible on `git pull main`). r3
already lands under the tracked `docs/research/runs/**`. **Migrate the r2
artifacts** to `docs/research/runs/` (or leave them and index from there) so a
fresh clone — and any librarian subagent (Phase 4) — can index the full corpus.
`docs/research/runs/**` is agnix-excluded (`.agnix.toml`), so research prose in
`agents/` subdirs won't trip the agent-doc validator.

---

## Suggested PR sequencing

- **PR-1 (Phase 0):** 5 low-risk one-liners — rule fix, Friday-off, runtime-lock
  fix, DIVE customManager, (Renovate handles MISE_VERSION separately).
- **PR-2 (Phase 1):** reusable `refresh` workflow + Renovate-PR trigger + daily
  safety cron.
- **PR-3 (Phase 2):** `tool_currency.py` image-tier + B2 + `watchlist.toml` +
  skill extension.
- **PR-4 (Phase 3):** experimental-drop + launchd-native (each possibly its own
  PR; both gated).
- **PR-5 (Phase 4):** two librarian subagents + measurement harness (graphify
  seed separate, on approval).
