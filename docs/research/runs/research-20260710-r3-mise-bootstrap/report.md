# Domain synthesis — mise bootstrap suite (bootstrap / macos-defaults / launchd / shell / user)

Run: `research-20260710-r3-mise-bootstrap` · Domain synthesis · 2026-07-10 ·
Writer: synthesis agent. Grounds three angle reports
(`agents/bootstrap-shell.md`, `agents/launchd-macos.md`,
`agents/user-integration.md`), the adversarial-verification verdicts on 8
load-bearing claims, r2 Run F (`.omc/research/research-20260709-r2-mac-automation/report.md`),
and `scripts/web-setup.sh`.

Environment note: Bash was broken across every angle (PreToolUse guard has no
Python ≥3.14 interpreter), so **nothing below was validated by an executed
probe** — all findings are docs + release-notes + working-tree reads. Every
`mise bootstrap ... --dry-run` / `--help` claim needs one hands-on pass on Ray's
actual Mac before any code is written. This is the single biggest caveat on the
whole domain.

---

## Executive summary — RECOMMENDATION UP FRONT

**mise's native `[bootstrap.macos.launchd.agents]` feature SHOULD replace the
plist-authoring/loading layer of Run F's hand-rolled LaunchAgent, but changes
nothing else in Run F's design.** Adopt it for the *trigger shell only*; keep
Run F's `dotfiles_setup.maintain` python module, its alerting fan-out
(ntfy + healthchecks + gh-issue), and the plain-launchd-vs-pitchfork venue
reasoning exactly as-is.

Three concrete calls:

1. **launchd (Q1): ADOPT, with a currency caveat.** Swap Run F's hand-written
   `~/Library/LaunchAgents/com.raymanaloto.dotfiles.maintain.plist` + manual
   `launchctl load` for a `[bootstrap.macos.launchd.agents.maintain]` TOML block
   applied via `mise bootstrap macos launchd-agents apply`. This is a strict
   improvement (declarative, in-repo config, `--dry-run` previewable, and free
   `status --missing` drift detection Run F's design lacked) for **zero new
   dependency** — mise is already a pinned host tool, so this dominates even
   Run F's secondary pitchfork option on Run F's own top decision axis. **BUT**
   the feature is ~4 weeks old and its `start_calendar_interval` key is only ~3
   days old (shipped v2026.7.1, 2026-07-07). This is *younger* than pitchfork
   was when Run F rejected pitchfork on maturity grounds — so pin the decision
   to a `--dry-run` sanity check on the exact generated plist, and confirm the
   real CLI subcommand spelling (three inconsistent spellings are on record —
   see Open Questions). `[bootstrap.macos.defaults]` is orthogonal and out of
   scope (no existing macOS-defaults code to retire; a future opt-in only).

2. **shell (Q2): mise does NOT help pick/standardize the devcontainer shell.**
   Neither `mise shell` (a per-session tool-version setter, a false cognate) nor
   `[bootstrap.mise_shell_activate]` (writes mise's *activation snippet* into rc
   files) *selects* a shell. Only `[bootstrap.user].login_shell` selects one
   (via `chsh`), and while it is Linux-capable, the repo has no existing chsh
   logic that lives at the mise layer to replace — the container login shell is
   already fixed to `/bin/bash` by `Dockerfile.host-user:39` (`useradd -s
   /bin/bash`), and cross-shell mise activation is already handled by the
   chezmoi-templated rc files. **No adoption recommended; net-new capability at
   best, ownership-conflict risk with chezmoi at worst.**

3. **web-setup.sh (Q3): mise bootstrap does NOT meaningfully simplify it.**
   `mise bootstrap` cannot replace step 1 (installing mise itself — same
   chicken-and-egg) or step 4 (persisting PATH into `$CLAUDE_ENV_FILE`, an
   Anthropic-harness mechanism mise has no concept of). It *could* collapse
   steps 2-3 into one `mise bootstrap --only tools,task` call **iff** a
   `[tasks.bootstrap]` is defined — a small win against real new surface area
   (`--only`/`--skip` part-name semantics, scoping away Mac-host config).
   **Not worth it for this script.** The `mise generate bootstrap` idea floated
   in one angle (swap `curl mise.run | sh` for a committed `./bin/mise` to dodge
   the allowlist) is **REFUTED** — see the refuted section.

**Overall posture:** one targeted adoption (launchd trigger), two "no" answers
(shell selection, web-setup.sh). This mirrors the repo's existing, already-
shipping `[bootstrap.packages]` adoption in the image — extending the same
`mise bootstrap <part> apply/status` pattern from apt-packages to the Mac-host
launchd surface is applying a validated-in-repo pattern to a second surface, not
adopting an unfamiliar tool.

---

## Q1 — Do mise launchd / macos-defaults / bootstrap supersede Run F's hand-rolled LaunchAgent?

### The feature is real, current, and inside the repo's pinned mise

`mise bootstrap` (whole-machine declarative setup) shipped v2026.6.6
(2026-06-13, "Declarative machine bootstrap"), was refined through v2026.6.14
(2026-06-25, "Bootstrap, end-to-end") and graduated out of experimental in
v2026.7.4 (2026-07-09). The image pins `ARG MISE_VERSION=2026.7.2`
(`.devcontainer/Dockerfile:115`) and the host sets `experimental = true`
(`mise.toml:47`), so the feature is present, not a future wait. This is
CONFIRMED (verification: 2 upheld / 3 votes) with one correction: it is **not
"unused"** — the packages sub-slice is already in production. `mise bootstrap
packages apply --manager apt --yes --update` and `mise bootstrap packages status
--json --missing` run as a load-bearing, anti-drift-gated build step
(`.devcontainer/Dockerfile:154-155`, `.devcontainer/mise-system.toml:100-115`).
Only the *other* sub-areas (dotfiles, macOS defaults, LaunchAgents, systemd,
login shell, repos, shell activation) are unused. That existing adoption is the
strongest argument the launchd extension is low-risk (angle
`user-integration.md` Finding 4).

### `[bootstrap.macos.launchd.agents]` maps 1:1 onto Run F's plist

Per `mise.jdx.dev/bootstrap/launchd.html` (live, 2026-07-10; not yet in the
local mintlify cache — see refuted claim on cache staleness), the TOML→plist
mapping covers every field Run F's design sketch hand-wrote:

| Run F hand-rolled | mise native | Verdict |
|---|---|---|
| plist XML at `~/Library/LaunchAgents/com.raymanaloto.dotfiles.maintain.plist` | `[bootstrap.macos.launchd.agents.maintain]` TOML → `~/Library/LaunchAgents/dev.mise.maintain.plist` | Superseded |
| `StartCalendarInterval Hour=6 Minute=30` | `start_calendar_interval = { hour = 6, minute = 30 }` | Superseded (only since v2026.7.1, ~3 days old) |
| `RunAtLoad=true` | `run_at_load = true` | Superseded 1:1 |
| `StandardOutPath`/`StandardErrorPath` | `stdout_path`/`stderr_path` (`~` expands) | Superseded 1:1 |
| PATH-prepend wrapper (`export PATH=.../mise/shims`) | `environment = { PATH = "..." }` + `program`/`args` split | Partially superseded — PATH problem moves from wrapper into the `environment` key, doesn't vanish |
| thin `scripts/maintain.sh` wrapper | `program = "<mise binary>"`, `args = ["run","maintain"]` | Superseded — the wrapper script can be dropped entirely |
| `launchctl load` (imperative) | `mise bootstrap macos launchd-agents apply` (declarative, idempotent, `--dry-run`) | Superseded + improved (adds drift detection) |
| `maintain.py` job logic (staleness, docker-context assertion, sync/verify, alerting) | **no mise equivalent** | **NOT superseded** — 100% still required |

Both `bootstrap-shell.md` (Finding 3) and `user-integration.md` (Finding 5)
independently reached this mapping. The `gui/<uid>` domain and modern `launchctl
bootstrap` verb mise uses are exactly what Run F's design independently verified.

### Bottom line

mise supersedes the **mechanical** plist-author/load/drift-check layer — a
strict improvement — and removes two hand-written layers (the plist XML and the
thin bash wrapper). It supersedes **nothing** in Run F's job body, alerting
design, or venue analysis. Net change if adopted: swap the outer trigger shell,
keep everything inside `mise run maintain`.

### `[bootstrap.macos.defaults]` — orthogonal, out of scope today

Manages Dock/Finder/keyboard/trackpad prefs (+ a raw `defaults write` escape
hatch), user-domain only, no sudo, never implicit
(`mise.jdx.dev/bootstrap/macos-defaults.html`). A repo grep found **zero**
existing macOS-defaults management code to retire (`launchd-macos.md` Finding 4,
`user-integration.md` Finding 6). It is also flatly against the repo's current
"chezmoi is devcontainer-only on this Mac; no host-state mutation" posture
(`AGENTS.md`). Verdict: legitimate future opt-in, **not** a simplification of
existing code — a new scope decision for Ray, not part of the launchd swap.

---

## Q2 — Does mise shell.html help pick/standardize the devcontainer shell?

**No.** Three distinct pages hide behind the "shell" label; none selects a shell
for the container:

- **`mise shell` (`cli/shell.html`)** — a false cognate. "Sets a tool version
  for the current session" (e.g. `mise shell node@20`). Nothing to do with
  bash/zsh/fish selection (`user-integration.md` Finding 2).
- **`[bootstrap.mise_shell_activate]`** — manages the mise *activation snippet*
  (`eval "$(mise activate zsh)"`) written into rc files via marker-delimited
  blocks; keys are per-user rc files (`zprofile`/`zshrc`/`fish`). It decides
  *how mise wires itself into shells that already exist*, not which shell runs
  (`bootstrap-shell.md` Finding 4).
- **`[bootstrap.user].login_shell`** — the *only* one that picks a shell, via
  `/etc/shells` + `chsh -s`, absolute paths required, Unix-only (so
  Linux-capable, unlike the macOS-only launchd/defaults parts). Narrow scope:
  login-shell convergence only, NOT user accounts / per-user config / dotfiles
  ownership / home-dir setup — those are separate bootstrap phases
  (`user-integration.md` Finding 1; verification CONFIRMED 3/3).

### Why adoption is not recommended

The repo already has cross-shell mise activation and a fixed container login
shell, both outside mise's bootstrap surface:

- Container login shell is hardcoded to `/bin/bash` at
  `.devcontainer/Dockerfile.host-user:39` (`useradd --uid 1000 --gid 1000 -m -s
  /bin/bash`). `[bootstrap.user].login_shell` would *interact with / replace*
  this `useradd -s` assignment, not add a purely-new capability.
- Cross-shell mise activation comes from the chezmoi-templated per-user rc files
  (`home/dot_bashrc.tmpl:26` and `home/dot_zshrc.tmpl:53`, each `eval "$(mise
  activate …)"`), re-rendered on every container create (`.devcontainer/AGENTS.md`
  "Reset-on-recreate"), plus the image-baked `/etc/profile.d/mise.sh` +
  `mise.zsh` (`Dockerfile:205-207`).

Adopting `[bootstrap.mise_shell_activate]` for the chezmoi-owned rc files would
put **two declarative tools claiming ownership of the same line in the same
file** — chezmoi's whole-file render vs mise's snippet convergence — a conflict,
not a simplification (`user-integration.md` Finding 3). chezmoi is this repo's
established, machine-differentiated (`chezmoi.os`) dotfiles source of truth.

**Important correction to the angle framing (see refuted section):** one angle
claimed `/etc/profile.d/` alone already delivers cross-shell determinism "by a
simpler route." Verification REFUTED this — the real activation path is the
chezmoi rc files; `/etc/profile.d/mise.zsh` (a `.zsh` file) is likely dead code,
never sourced by Ubuntu zsh, and `/etc/profile.d/*.sh` is only read by *login*
shells anyway. So the honest statement for Ray is: the repo's cross-shell
determinism is a **two-layer** setup (rc-file `eval` for interactive shells +
profile.d for login shells), not one simple system-wide mechanism — but the
conclusion holds regardless: **mise shell.html doesn't help pick the
devcontainer shell, and there's no clean code-reduction win.**

---

## Q3 — Does mise bootstrap simplify scripts/web-setup.sh?

**Marginally, and not worth it.** `scripts/web-setup.sh` does four things:
(1) install mise via `curl https://mise.run | sh` (:41-47); (2) `mise install`
(:54); (3) `uv python install 3.14 && uv sync --project python` (:58-61);
(4) persist PATH into `$CLAUDE_ENV_FILE` for the SessionStart-hook re-run
(:64-73).

- **Step 1 — cannot be replaced.** `mise bootstrap` is a subcommand of the mise
  CLI, so it requires mise already on PATH — the exact chicken-and-egg step 1
  solves. `mise.jdx.dev/bootstrap.html` states it "assumes mise is already
  installed and operational." (CONFIRMED 3/3.)
- **Step 4 — cannot be replaced.** `$CLAUDE_ENV_FILE` is a Claude-Code-specific
  SessionStart-hook mechanism (code.claude.com/docs/en/hooks; anthropics/
  claude-code issues #15840, #19357). mise's only env-persistence path writes
  activation snippets into shell rc files — a different, generic mechanism, not
  a caller-supplied one-shot env file. (CONFIRMED 3/3.)
- **Steps 2-3 — could collapse into one `mise bootstrap --only tools,task`
  call, IFF a `[tasks.bootstrap]` existed** holding `uv python install 3.14 &&
  uv sync --project python`. That is a real but modest win (1 command vs 2-3
  lines) against genuine new surface area: `--only`/`--skip` part-name semantics
  (v2026.6.12+), and the risk of silently picking up `[dotfiles]`/
  `[bootstrap.packages]` config meant for the Mac host. The script's own header
  stresses minimalism ("thin bootstrap"). Verdict from `bootstrap-shell.md`
  Finding 5: **not worth doing for web-setup.sh specifically** — revisit only if
  `[tasks.bootstrap]` gets defined for other reasons.

---

## Refuted / unverified claims

These were judged REFUTED or partially-false by the adversarial verification
pass and MUST NOT be asserted as true.

1. **REFUTED — "`mise generate bootstrap` downloads a pinned binary directly
   from GitHub Releases (not mise.run), so committing `./bin/mise` eliminates
   the mise.run allowlist need under Claude web's Trusted policy."**
   (Claimed in `bootstrap-shell.md` Uncertainty #1 as the "single most
   load-bearing actionable finding.") Verdict: 0/3 upheld, REFUTED. Ground truth
   from `jdx/mise` source `src/cli/generate/bootstrap.rs`: the generated
   `./bin/mise` install step fetches an installer from **`https://mise.jdx.dev/
   install.sh`** (or `/v{v}/install.sh`) — a mise-controlled domain, not a
   `github.com/.../releases/download/...` URL. The embedded install.sh only
   uses GitHub Releases *conditionally* (version mismatch or
   `MISE_INSTALL_FROM_GITHUB` set); by default it falls back to `mise.jdx.dev`.
   `scripts/web-setup.sh:24-31` already buckets `mise.jdx.dev` with `mise.run`
   as **not** reachable under the default Trusted policy. So this swap does
   **not** eliminate the allowlist need and does not piggyback on
   already-reachable GitHub. **Do not pursue the `./bin/mise` swap as an
   allowlist workaround.** (The remaining web-setup.sh conclusion — mise
   bootstrap can't replace steps 1 or 4 — stands independently.)

2. **REFUTED — "`/etc/profile.d/mise.sh` + `mise.zsh` alone is the simpler
   mechanism already delivering cross-shell determinism, and the repo has no
   existing login-shell selection logic."** (Claimed in `bootstrap-shell.md`
   Finding 4 / re-verification.) Verdict: 0/3 upheld, REFUTED on two grounds.
   (a) `/etc/profile.d/mise.zsh` is likely dead code — Debian/Ubuntu `/etc/
   profile` only globs `*.sh`, and Ubuntu zsh doesn't source `/etc/profile.d`
   by default; real zsh activation comes from the chezmoi-templated
   `home/dot_zshrc.tmpl:53`. (b) Login-shell selection logic DOES exist:
   `.devcontainer/Dockerfile.host-user:39` `useradd … -s /bin/bash` hardcodes
   it — the grep for literal `chsh|login_shell` missed it because it's expressed
   as `useradd -s`. So `[bootstrap.user].login_shell` would replace an existing
   assignment, not add a purely-new capability. (mise's `[bootstrap.
   mise_shell_activate]`/`[bootstrap.user].login_shell` keys are themselves
   real, current features — that part checks out.)

3. **REFUTED (as an inference) — "mise's Docker/container cookbook has no
   mention of bootstrap, corroborating that mise bootstrap is an
   interactive/host-machine feature, not a devcontainer-provisioning one."**
   (Claimed in `bootstrap-shell.md` Finding 4.) Verdict: 0/3 upheld. The narrow
   fact is true (`mise.jdx.dev/mise-cookbook/docker.html` has zero "bootstrap"
   hits), but the inference is contradicted by primary evidence: mise's own CI
   guide (`mise.jdx.dev/continuous-integration.html`, "Using the bootstrap
   script") documents `mise generate bootstrap` for Docker/GitLab-CI image
   builds; mise ships a dedicated `mise generate devcontainer` subcommand; and
   **this repo itself** uses `mise bootstrap packages apply` to provision the
   devcontainer base image (`.devcontainer/Dockerfile:154-155`). So "bootstrap
   is host/interactive-only" is false. This does not change any Q1-Q3 conclusion
   (the launchd/defaults/user parts genuinely ARE macOS-host-oriented), but the
   "cookbook silence proves host-only" argument must not be used.

4. **Unverified — exact CLI subcommand spelling.** Three mutually inconsistent
   spellings are on record: `mise bootstrap macos launchd-agents apply`
   (v2026.6.14 release notes + WebSearch synthesis), `mise bootstrap launchd
   apply` (Arch Linux man page), and the v2026.6.6-era forms. `launchd-macos.md`
   §5 flags this explicitly as unresolved. **Do not hardcode any spelling** —
   `mise bootstrap --help` on Ray's actual installed version is a hard
   prerequisite.

5. **Unverified — `kickstart` invocation surface and `program`/`args`-vs-shell
   one-liner semantics.** Whether `program` may be `/bin/zsh` with `args =
   ["-lc", "exec mise run maintain"]` (carrying Run F's wrapper shape over
   unchanged) vs requiring a direct executable was inferred from summaries, not
   a verbatim doc read (`launchd-macos.md` Uncertainties #1-2). Confirm with a
   raw page dump + `--dry-run` before writing TOML.

6. **CONFIRMED but worth flagging — the local mintlify cache and its documented
   `ok` mirror for `jdx/mise` are stale/broken for this feature area.** Cached
   `llms.txt` has no bootstrap/shell/launchd/user pages; the mirror
   `www.mintlify.com/jdx/mise/llms.txt` now returns **HTTP 410 Gone** (and so do
   per-page `.md` fetches, and a cross-check on `twpayne/chezmoi` — the mirror
   mechanism itself appears retired). Real content is only on
   `mise.jdx.dev/*.html` (VitePress), whose own `/llms.txt` and `.md` suffixes
   404. Verdict: CONFIRMED 3/3. **Action: the `jdx/mise` row in
   `docs/research/mintlify-catalog.md:73` (probed `ok` 2026-04-06) needs
   re-probing/correcting, and the bootstrap pages should be queued for the next
   cache refresh.** Every citation in this domain is a live fetch, none
   cache-backed.

---

## Open questions for Ray (with recommended answers)

1. **Adopt `[bootstrap.macos.launchd.agents]` for the maintain job now, or wait
   for the feature to mature?** *(Recommended: adopt, but gate on a `--dry-run`
   sanity pass. The zero-new-dependency win is real and it's mise-native, but
   `start_calendar_interval` is ~3 days old — younger than pitchfork was when
   Run F rejected pitchfork on maturity. A dry-run of the generated plist +
   confirming it loads correctly is the cheap insurance. If the dry-run is
   clean, adopt; if it's flaky, keep Run F's hand-rolled plist for one more
   cycle and re-check via `tool-currency-check`.)*

2. **Which CLI subcommand spelling is correct on your Mac's installed mise?**
   *(Recommended: run `mise bootstrap --help` and `mise bootstrap macos --help`
   (or `mise bootstrap launchd --help`) on the host before writing anything —
   three spellings are on record and the synthesis deliberately hardcodes none.)*

3. **Adopt `[bootstrap.macos.defaults]` to codify Dock/Finder/trackpad prefs?**
   *(Recommended: not now. It's a net-new host-state-mutating surface with no
   existing code to retire, and it cuts against the current "chezmoi is
   devcontainer-only on this Mac / no host mutation" posture. Revisit only if you
   decide you want declarative Mac-prefs management as a deliberate new scope.)*

4. **Simplify `web-setup.sh` steps 2-3 via a `[tasks.bootstrap]` +
   `mise bootstrap --only tools,task`?** *(Recommended: no. The win is ~1 line;
   the cost is `--only`/`--skip` part-name semantics plus the risk of picking up
   Mac-host config in a web-container script. Skip it. And do NOT pursue the
   `mise generate bootstrap` / `./bin/mise` allowlist-dodge — it's refuted; it
   routes through `mise.jdx.dev`, which is equally not-allowlisted.)*

5. **Refresh the mintlify cache / fix the catalog row for `jdx/mise`?**
   *(Recommended: yes, low priority. The `ok` mirror is 410 Gone; queue the
   `mise.jdx.dev` bootstrap pages and correct `mintlify-catalog.md:73` so future
   sessions don't trust a dead mirror.)*

6. **Verify the host's actual mise version before shipping any of this.**
   *(Recommended: `mise --version` on the Mac. The feature needs ≥v2026.6.6 for
   launchd and ≥v2026.7.1 for calendar intervals; the host self-updates and sets
   `experimental = true` at `mise.toml:47`, so it's almost certainly fine, but
   confirm before relying on it.)*

---

## Contradictions against the r2 / domain-brief baseline

- **Run F's core recommendation is NOT contradicted — it is refined.** Run F
  recommended a hand-rolled `gui/<uid>` launchd LaunchAgent with
  `StartCalendarInterval` running `mise run maintain` (CONFIRMED 3/3 against the
  primary source). This synthesis keeps that venue and job design intact; it
  only proposes swapping the *authoring mechanism* (hand-written plist →
  `[bootstrap.macos.launchd.agents]` TOML) that did not exist / was not surfaced
  when Run F was written. Flag for Ray: Run F's "zero new dependency, revisit
  pitchfork later" reasoning now has a *third* option (mise-native launchd) that
  wins on Run F's own top axis — this strengthens rather than overturns Run F.
- **One angle's headline "actionable finding" is refuted** (the `mise generate
  bootstrap` / GitHub-Releases allowlist claim, `bootstrap-shell.md` Uncertainty
  #1). Flagging loudly because that angle called it "the single most
  load-bearing finding" — it is false and must not be actioned.
- **One angle's cross-shell-determinism framing is refuted** (`/etc/profile.d`
  as the simpler mechanism + "no login-shell logic"). The Q2 *conclusion*
  (mise doesn't help pick the devcontainer shell) is unaffected, but the
  supporting mechanism was mischaracterized.

---

## GitHub repos touched

- [jdx/mise](https://github.com/jdx/mise) — `mise bootstrap` command suite
  (bootstrap.html, bootstrap/launchd.html, bootstrap/macos-defaults.html,
  bootstrap/shell.html, bootstrap/user.html, cli/shell.html,
  cli/bootstrap/mise-shell-activate.html, continuous-integration.html,
  mise-cookbook/docker.html), CHANGELOG.md + release notes v2026.6.6→v2026.7.5,
  `src/cli/generate/bootstrap.rs` (install-host mechanism), and the older
  `mise generate bootstrap` installer-script feature; the feature family under
  evaluation.
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — grounding
  reads: `scripts/web-setup.sh`, `.devcontainer/Dockerfile` (MISE_VERSION pin,
  `mise bootstrap packages` build step, `/etc/profile.d/mise.{sh,zsh}` writes),
  `.devcontainer/Dockerfile.host-user` (`useradd -s /bin/bash` login shell),
  `.devcontainer/mise-system.toml` (`[bootstrap.packages]` precedent + rename
  comment + `experimental = true`), `mise.toml` (host `experimental = true`),
  `home/dot_bashrc.tmpl`, `home/dot_zshrc.tmpl`, `.devcontainer/AGENTS.md`,
  `docs/research/mintlify-catalog.md`, and the r2 Run F report this domain
  compares against.
- [anthropics/claude-code](https://github.com/anthropics/claude-code) —
  code.claude.com/docs hooks (`$CLAUDE_ENV_FILE` SessionStart mechanism),
  issues #15840 / #19357 / #11649 (CLAUDE_ENV_FILE as a Claude-Code-specific
  feature).
- [twpayne/chezmoi](https://github.com/twpayne/chezmoi) — dotfiles source of
  truth this repo uses (rc-file ownership conflict analysis); mintlify mirror
  cross-check (also 410 Gone).
