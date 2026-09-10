# Staleness audit — mise backend/registry/minimum_release_age prose (2026-09-10)

Ground truth used (supplied by team-lead this session, with its own control arms):
- mise 2026.9.2-9.4 promoted the `packslip` backend to Tier 1; the registry
  shorthand for e.g. `hk` now defaults to Packslip when only Packslip manifests
  exist for a release.
- Measured (`MISE_MINIMUM_RELEASE_AGE=0`): bare `fnox` -> 1 version;
  `github:jdx/fnox` -> 53. Bare `usage` -> 2; `aqua:jdx/usage` -> 100. Control
  `node` -> 865.
- `.devcontainer/mise-system.toml:330` sets `minimum_release_age = "7d"`,
  which hides the 1-2 packslip releases, so `fnox@latest`/`usage@latest` are
  unresolvable and `mise run lock-image` fails every convergence pass.
- The plan is to change that setting to `"0s"` repo-wide and fix schema
  directives.

This lane is Claude/Sonnet-5 only — `codex` was not invoked (read-only prose
audit against small, precisely-scoped corpora; direct grep/read was faster and
the ground truth was already fully specified by the caller). Everything below
is my own reasoning with probes run directly, not a codex verdict.

Method note: `mise run graphify-query -- "minimum_release_age packslip fnox
usage lock-image backend registry"` returned `TRUNCATED: showing 58 of 585
nodes` (rc=3) — per `graphify-first.md`, truncation means unavailable; fell
back to direct source grep for the rest of this audit.

---

## Findings table

| # | Verdict | Anchor | Claim | Probe + control arm |
|---|---|---|---|---|
| 1 | CONFIRMED-STALE | `.github/workflows/refresh.yml:348-350` | "mise run lock-image inherits env and injects no token itself; anonymous, its convergence loop is EXPECTED to exhaust GitHub's rate limit and raise 'did not converge in 5 pass(es)'." | `mise registry fnox` -> `packslip:github.com/jdx/fnox github:jdx/fnox` (packslip is default); with `minimum_release_age="7d"` every one of the 5 passes filters `fnox@latest`/`usage@latest` to the same too-young-to-resolve set, deterministically — retrying does not change wall-clock age meaningfully within one workflow run. Control: `mise registry rtk` -> `aqua:rtk-ai/rtk github:rtk-ai/rtk` (packslip absent; rtk resolution is unaffected, confirming the grep/registry probe discriminates tool-by-tool) |
| 2 | CONFIRMED-STALE | `python/src/dotfiles_setup/image_lock.py:78-79` (module constant docstring) | "`mise lock` resolves through GitHub, and anonymous quota exhausts mid-run; each pass fills what the previous could not." | Same probe as #1 — for `fnox`/`usage` under the current `7d` gate, no pass can ever "fill what the previous could not" because the filtered candidate set doesn't grow with wall-clock time inside a single run. Control: `node` -> 865 versions (a real tool where rate-limit-driven partial resolution across passes is plausible) |
| 3 | CONFIRMED-STALE | `python/src/dotfiles_setup/image_lock.py:289-295` docstring + `:312-314` log message | "Earlier passes are allowed to fail — that is what the loop is for, since exhausted GitHub quota is the expected mid-run failure." / log: `"mise lock pass %d/%d exited %d — retrying (rate limits are the expected cause)"` | Same mechanism as #1/#2. The convergence loop only inspects `returncode`, not stderr text (`run_lock_passes`, `python/src/dotfiles_setup/image_lock.py:296-319`), so it cannot distinguish a transient rate-limit failure from a deterministic `minimum_release_age` filter-to-empty failure — both surface identically as "did not converge in 5 pass(es)". The log message actively misdirects an operator toward "wait/retry/add a token" for a failure that retrying can never fix |
| 4 | CONFIRMED-STALE (about to become true the moment the planned edit lands) | `.devcontainer/mise-system.toml:321-330` | "Supply-chain hardening: ignore tool versions younger than 7 days when resolving `latest`/fuzzy requests… NOTE: `mise lock` resolves `latest` WITHOUT this cutoff while bun enforces it at install, so a locked latest younger than 7d fail-closes (PR #169). Exempt fast-releasing tools via minimum_release_age_excludes (mise-runtime.toml `[settings]` does this for the AI CLIs)." / `minimum_release_age = "7d"` | This whole comment block is internally consistent **today** (value is genuinely `"7d"`). It becomes a contradiction the instant the value is edited to `"0s"`: the comment hard-codes "7 days"/"7d" three times and describes `minimum_release_age_excludes` as the escape hatch, which becomes vestigial (no gate left to exempt anything from) once the base value is `0s`. Flagged per team-lead's explicit instruction — must be rewritten in the SAME diff as the value change, not left describing a mechanism whose premise no longer holds |
| 5 | CONFIRMED-STALE (same class as #4) | `.devcontainer/mise-runtime.toml:23-33` | "The AI CLIs below release faster than weekly, so the 7d minimum_release_age gate (mise-system.toml `[settings]`) makes their locked 'latest' uninstallable almost always… Native escape hatch, scoped to this tier so mise-system.toml (a base-hash input) stays byte-identical." / `minimum_release_age_excludes = ["npm:@google/gemini-cli"]` | Two problems, not one: (a) literal "7d" reference goes stale exactly like #4 the moment the base value flips to `0s`; (b) **this mechanism was scoped to ONE tool (`npm:@google/gemini-cli`) and never extended to `fnox`/`usage`**, which sit in the very same `[tools]` block two lines below the comment (`.devcontainer/mise-runtime.toml:41-42`) and are subject to the identical failure shape (a `latest` pin the gate makes unresolvable) — the exclude list's own scope is the reason nobody had to widen it before the packslip promotion changed fnox/usage's registry-default backend. Control: `mise registry fnox`/`mise registry usage` both list `packslip:` first (see #1); `mise registry npm:@google/gemini-cli` is not a registry-shorthand entry at all (it's already backend-qualified `npm:`), so its inclusion in the exclude list was always for release-cadence reasons, not a backend-default reason — a genuinely different root cause than fnox/usage's, confirming the exclude list's scope was deliberate and narrow, not an oversight that happens to also cover fnox/usage |
| 6 | REFUTED | `mise.toml:50` — `"aqua:jdx/rtk-ai/rtk" = "0.47.0" # aqua is the registry's first backend (\`mise registry rtk\`)…` | Claims aqua is rtk's first/default registry backend | `mise registry rtk` -> `aqua:rtk-ai/rtk github:rtk-ai/rtk` — aqua genuinely is listed first; packslip does not appear at all for this tool. This comment is accurate and NOT part of the staleness the packslip promotion introduced. Control: same command shape as #1/#5, `mise registry hk` -> `packslip:github.com/jdx/hk aqua:jdx/hk` (packslip now first for hk, proving the probe discriminates tool-by-tool rather than always returning "aqua first") |
| 7 | NEEDS-VERIFICATION | `.config/mise/conf.d/shared.toml:31` — bare `hk = "1.57.0"` (no explicit backend prefix) | No doc currently asserts which backend this bare pin resolves through, but `mise registry hk` now returns `packslip:… aqua:…` (packslip first) — a change from whatever pre-packslip-promotion default existed. I found no stale prose actively claiming "hk resolves via aqua" to contradict, so this is not a finding against existing text, but it IS a latent risk: if `mise install`/`mise lock` on this pin silently switched backends underneath the bare shorthand, the hk-pin-parity check in `tool-currency-check/SKILL.md` (`hk.pkl` step 2) still only greps version numbers, not backend — it would not notice a backend switch. Probe that would settle it: `mise ls hk` on a clean re-lock, or `MISE_MINIMUM_RELEASE_AGE=0 mise install hk@1.57.0 --dry-run -v` and inspect which backend line it prints. Not run here — read-only audit, and this host's `mise ls hk` output (1.48.0/1.52.0/…/1.54.1 shown, not 1.57.0) suggests the pinned version isn't even installed locally yet, so a live resolution probe would mutate local mise state, which I avoided under the read-only constraint |

---

## Detail: findings #1-#3 (the rate-limit misattribution — highest harm)

Three separate places in the repo assert, in different words, that a `lock-image`
convergence failure is caused by exhausted GitHub rate limits and that retrying
(more passes, a token) is the fix:

1. `.github/workflows/refresh.yml:348-350` (a CI step comment, directly guiding
   what `GITHUB_TOKEN`/`MISE_GITHUB_TOKEN` are for and what a convergence
   failure means).
2. `python/src/dotfiles_setup/image_lock.py:78-79` (module-level constant
   docstring for `DEFAULT_PASSES`).
3. `python/src/dotfiles_setup/image_lock.py:289-295` (docstring) and `:312-314`
   (the actual `logger.warning` text an operator reads live during a
   `mise run lock-image` run).

All three describe the SAME mechanism (`run_lock_passes`,
`python/src/dotfiles_setup/image_lock.py:281-320`): retry up to
`DEFAULT_PASSES` (5) times, treat only the last pass's `returncode` as
authoritative. That loop genuinely was built for, and does correctly handle,
transient anonymous-GitHub-quota exhaustion for tools with many candidate
releases (`node` -> 865 versions, control-armed above).

It does **not**, and structurally cannot, handle the `fnox`/`usage` failure
mode the team-lead is fixing: `minimum_release_age = "7d"` filters `fnox` to 1
resolvable version and `usage` to 2, and that filtered set does not grow
between passes within a single run — there's nothing for "the next pass" to
fill in. `mise lock` hard-errors on an unresolvable tool since 2026.6.13 (a
fact the code's own docstring at `image_lock.py:293` already states), which
means EVERY pass fails identically and the loop exhausts all 5 attempts before
raising `ImageLockError`. The log line an operator actually sees —
`"mise lock pass %d/%d exited %d — retrying (rate limits are the expected
cause)"` — actively misdirects toward waiting out a quota window or adding a
`GITHUB_TOKEN`, neither of which touches the real cause.

**Harm if left as-is post-fix:** once `minimum_release_age` moves to `0s`,
these three sites become moot for this specific failure (the gate stops
filtering fnox/usage to nothing) — but the misdiagnosis pattern they encode
stays live for the NEXT tool that ships as few releases as fnox/usage did, or
for any future re-introduction of a nonzero age gate. Recommend rewording all
three to name BOTH causes (`transient quota` vs `deterministic
minimum_release_age filter-to-empty`) and pointing at the config, not just
"retry"/"add a token".

## Detail: findings #4-#5 (the "7d" literal, about to contradict itself)

Both `.devcontainer/mise-system.toml:321-330` and
`.devcontainer/mise-runtime.toml:23-33` name "7 days"/"7d" as hard-coded prose,
not as a reference to the live setting value. The moment
`mise-system.toml:330`'s `minimum_release_age = "7d"` becomes `"0s"`, both
comments describe a gate that no longer exists in the form they describe. This
is exactly the contradiction the team-lead flagged as the thing to catch
before shipping.

Finding #5 additionally surfaces something the team-lead's brief didn't
explicitly ask for but is directly load-bearing for the fix: the
`minimum_release_age_excludes` mechanism was deliberately scoped to ONE tool
(`npm:@google/gemini-cli`) for a release-cadence reason unrelated to fnox/usage's
packslip-default-backend problem. If the actual fix direction changes from
"flip the global gate to 0s" to "add fnox/usage to the excludes list" at any
point in review, the current exclude-list comment's framing ("Exempt
fast-releasing tools via minimum_release_age_excludes") already supports that
alternative — but the comment would still need fnox/usage's actual reason
(packslip's small release count triggering the SAME symptom via a DIFFERENT
mechanism than gemini-cli's fast cadence) spelled out, or a future reader will
assume all three tools share one root cause when they don't.

## Re-verified before reporting

Re-ran the exact grep commands against `.devcontainer/mise-system.toml`,
`.devcontainer/mise-runtime.toml`, `.github/workflows/refresh.yml`, and
`python/src/dotfiles_setup/image_lock.py` in the same tool call sequence used
to write this report (not from memory of an earlier read) — no edits had
landed between my first read and this write-up (git status was clean at
session start per the environment snapshot, and I made no writes). The
`mise registry <tool>` probes (fnox, usage, rtk, hk) were run live, immediately
before compiling the findings table, from the actual pinned `mise` on this
host — not inferred from prose.

## What I did NOT check

- `.claude/skills/lock-shared/SKILL.md`, `.claude/skills/context7-cli/SKILL.md`,
  `.claude/skills/find-docs/SKILL.md`, `.claude/skills/mintlify/SKILL.md`,
  `.claude/skills/graphify/SKILL.md`,
  `.claude/skills/pkl-import-hyphen-alias-expertise/SKILL.md`: grepped for
  `minimum_release_age|packslip|rate limit|backend|registry`; only benign,
  unrelated "rate limit" hits (context7/mintlify API rate limits, not mise's).
  Control arm: same grep shape against `docs/rules-evidence/mise-tasks-only.md`
  and `docs/rules-evidence/tool-currency-and-native-first.md` also returned
  zero hits for the target terms while a control grep for `mise` (a term known
  present) returned 8 and 19 hits respectively in those same two files —
  confirms the zero-hit result is a real absence, not a broken grep.
- `~/.claude/projects/-Users-rmanaloto-dev-github-ray-manaloto-dotfiles/memory/MEMORY.md`
  (already in my context this session): index has no entry mentioning
  `minimum_release_age`, `packslip`, or lock-image rate-limit framing. Existing
  mise-lock-related entries (`feedback_mise_lock_reuses_locked_version`,
  `feedback_mise_lock_whole_file_is_destructive`) are about destructive
  whole-file relocks, an unrelated failure class — not flagged as stale here.
- `mise.toml:82-95` codex/antigravity registry-shorthand commentary: read in
  full, makes no claim about packslip or minimum_release_age; not stale.
- Did not probe finding #7 live (`mise install`/`mise lock` dry-run) to avoid
  mutating local mise state under the read-only constraint; left as
  NEEDS-VERIFICATION rather than asserted.

## GitHub repos touched

- [jdx/mise](https://github.com/jdx/mise) — registry backend resolution
  (`mise registry <tool>` probes) referenced throughout; not fetched via API,
  probed via the locally pinned `mise` binary only.

_None else — this audit was entirely local grep/read plus local `mise
registry` probes; no remote fetch was performed._
