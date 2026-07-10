# Research: coexistence, hybrid, or migration cost — mise dotfiles vs chezmoi (Run r3, angle #3/3)

Domain: mise dotfiles vs/with chezmoi. This angle answers: can mise
`[dotfiles]` and chezmoi run together (hybrid), what would a full
replacement cost given the devcontainer-only apply model and the
`.chezmoiignore` mise-overlay gate, and what should THIS repo do
(replace / complement / neither)?

Date: 2026-07-10. Baseline grounding: `.omc/research/research-20260709-r2-inventory/report.md`,
plus this run's sibling angle reports (read in full before starting):
`docs/research/runs/research-20260710-r3-mise-dotfiles/agents/mise-dotfiles-caps.md`
(angle #1, mise dotfiles capability surface) and
`docs/research/runs/research-20260710-r3-mise-dotfiles/agents/chezmoi-parity.md`
(angle #2, feature-by-feature chezmoi-dependence inventory of `home/`).
This report does not re-derive their findings from scratch; it cites them
directly where load-bearing and independently re-verifies the specific
facts this angle's recommendation rests on (read the underlying `home/`
files itself rather than trusting the summary alone).

## Findings

### 1. Hybrid is technically possible only under strict file-ownership partitioning — and this repo has no current driver for it

mise dotfiles' declarative model is per-target-path: each `[dotfiles]`
entry (whole-file or block/line edit) claims one target path or one
`(path, id)` edit-slot (angle #1 §2, §6, sourced from
`https://mise.jdx.dev/dotfiles.html`). chezmoi's `home/` source tree
already claims 17 target paths outright (angle #2 §0 inventory). For a
hybrid to be safe, no target path may be claimed by both tools
simultaneously — otherwise the two apply mechanisms fight over the same
file with no coordination protocol between them (neither tool is aware
of the other's existence; confirmed absent from both tools' docs, see
§2 below).

The one place the two models could interoperate without collision is
mise's **block/line edit mode**, explicitly designed to "manage one
small piece of a file something else owns" (angle #1 §2, §6) — i.e.
inserting a marker-delimited block into a file chezmoi does NOT
template-own. But there is no such target in this repo today: every
file chezmoi manages under `home/` is either a whole `.tmpl` chezmoi
owns outright, or a static file — there is no "foreign-owned file that
needs one line poked into it" gap in the current `home/` tree for mise
dotfiles' edit mode to fill. Concretely: nothing in `home/` needs both
"the OS-conditional, distro-branching, prompt-driven templating chezmoi
already does" AND "a small marker-delimited edit mise could
additionally own" — the repo's actual file set (`home/**`, 17 entries,
angle #2 §0) doesn't have a natural split point.

### 2. If a hybrid were attempted, apply-ordering must be added explicitly — it does not exist today

Chezmoi applies exactly once per container lifecycle, at
`onCreateCommand`: `.devcontainer/scripts/on-create.sh:41` runs
`chezmoi init --apply --source="${WORKSPACE_FOLDER}" --no-tty --force`
on **every** container create (comment at `on-create.sh:14-17`:
"managed files refresh every container create — persistent home volume
does NOT protect local edits to managed files"; corroborated by
`.devcontainer/AGENTS.md` "Reset-on-recreate" section). mise dotfiles is
never invoked anywhere in this repo — grepped/read `on-create.sh` end to
end (75 lines) and `devcontainer.json`'s lifecycle hooks
(`.devcontainer/AGENTS.md` "Devcontainer Lifecycle" table); the only
`mise` calls in the create path are `mise install -y` / `mise reshim`
for the interactive **tool overlay** tier (unrelated to dotfiles — it
installs mise-managed tool binaries declared in the chezmoi-rendered
`~/.config/mise/config.toml`, not dotfile files). So today there is
zero existing `mise dotfiles apply` call to reason about ordering
against — a hybrid would require a **new** line in `on-create.sh` after
the chezmoi step, and a **new** `[dotfiles]` table declared somewhere
mise can read it before that point in the lifecycle. Since chezmoi's own
`--force` re-render on every create would otherwise clobber anything
mise wrote to a chezmoi-templated file, the safe ordering is
chezmoi-first / mise-dotfiles-second — but per §1, there is no file in
this repo that would actually need mise to run second, so this remains
a hypothetical mechanism, not a shipped one.

Mechanically, mise dotfiles config would have to live in the **root**
`mise.toml` (unmanaged by chezmoi, already checked into the repo and
present at container-create time via the workspace bind-mount) rather
than the chezmoi-rendered `home/dot_config/mise/config.toml.tmpl`
overlay — using the overlay file would be circular (chezmoi would have
to render the file that declares mise's dotfiles entries before mise
could apply them, defeating any claim of independence from chezmoi).
This is a real design constraint on any future hybrid, not just a
detail.

### 3. No evidence in the wild of mise's native `[dotfiles]` feature being combined with chezmoi for the same files

A web search for hybrid/coexistence patterns
(`mise dotfiles chezmoi migrate OR coexist OR hybrid 2026`, 2026-07-10)
surfaced only the **pre-existing, structurally different** pattern:
repos like `dankaiser1808/dotfiles` and `shunk031/dotfiles` use chezmoi
for dotfile *content* and mise for tool/runtime *versions* — two
non-overlapping concerns, not mise's native `[dotfiles]` file-management
feature running alongside chezmoi's file-management for the same
targets. That pattern predates mise's `[dotfiles]` feature (v2026.6.6,
2026-06-13; angle #1 §1) and doesn't speak to it. A second search
(`jdx/mise github issues "chezmoi" dotfiles`, 2026-07-10) surfaced the
same repos and no GitHub issue/discussion about running the two
file-management systems together. Angle #1's own web search (§14 of
that report) reached the identical conclusion independently. This
corroboration across two separately-run searches raises confidence:
**as of 2026-07-10, mise `[dotfiles]` + chezmoi coexistence over the
same file set is an unvalidated, untried combination**, not a known
pattern with prior art to lean on.
Sources: web search results dated 2026-07-10 (queries above); mise
release date via `https://github.com/jdx/mise/releases/tag/v2026.6.6`.

### 4. Full-replacement cost — re-verified gap inventory, read directly from `home/`

Cross-checking angle #2's feature inventory against the actual files
(not just trusting the summary):

| Gap | Verified directly | Actual cost in THIS repo |
|---|---|---|
| `promptBoolOnce` interactive Mac-host prompting | `home/.chezmoi.toml.tmpl:37-39` — gates `is_dev_computer`/`is_personal` on `$isInteractive` (darwin, non-CI, TTY); this is a **persist-the-answer-once-to-a-data-file** mechanism | **Hard blocker.** Directly re-queried `https://mise.jdx.dev/dotfiles.html` (2026-07-10): the only "prompt" the docs mention is `mise dotfiles apply --yes` — a one-off "skip the y/n confirmation before applying" flag, **not** a data-gathering question persisted across runs. Categorically different mechanism; no mise substitute exists. |
| `.chezmoi.osRelease.id` distro branching | `home/dot_zshrc.tmpl:28` (bazzite), `home/dot_tmux.conf.tmpl:9-19` (ubuntu/debian/fedora/darwin) — read directly | **Low cost today.** `home/.chezmoi.toml.tmpl:1-6` itself documents "No third target exists in this repo" (only darwin host + linux devcontainer are real machines) — these branches are latent/future-proofing, not exercised by either of the two machines actually in use. Losing them costs nothing operationally today, only optionality for a hypothetical future third machine. |
| `stat "/.dockerenv"` → `$remote` gate | `home/dot_zshrc.tmpl:1`, `home/dot_bashrc.tmpl:1` (identical expression, read directly) — gates skipping a gpg-agent `SSH_AUTH_SOCK` override on remote/container | **Medium cost.** 5 of the 6 OR'd signals (`CODESPACES`, `SSH_CONNECTION`, `KUBERNETES_SERVICE_HOST`, `container`, `REMOTE_CONTAINERS` env vars) are coverable via mise's `env`/`get_env()` Tera functions (angle #1 §5); only the raw filesystem `stat` on `/.dockerenv` has no confirmed mise template-function equivalent (not in the cached `templates.html` function list, `docs/research/mintlify-cache/jdx/mise/llms-full.txt:1548-1632`). Whether the devcontainer actually sets one of the 5 covered env vars was **not verified in this session** (no live container to probe) — flagged as an uncertainty below, not asserted as safe. |
| `.chezmoiexternal.toml` remote URL fetch | `home/.chezmoiexternal.toml:7-10` — fetches `_mise` zsh completions from `raw.githubusercontent.com`, 168h refresh | **Low cost, arguably an improvement.** The file's own comment (`:2-5`) already documents the workaround: `mise completion zsh > _mise` generates the same artifact locally at apply/create time, no URL fetch needed at all — this gap has a same-file-documented, ready-made replacement, not merely a workaround. |
| `.chezmoitemplates/env` shared-fragment composition | `home/.chezmoitemplates/env:1` (`{{ output "mise" "activate" .SHELL }}`), called from `home/dot_profile.tmpl:1` and `home/dot_zshenv.tmpl:1` via `{{ template "env" (dict "SHELL" ...) }}` — read directly, confirms angle #2's finding | **Low cost.** Two call sites; duplicating the one-line `exec("mise activate " + shell)` in both files (mise's `exec()` is angle #1 §5's confirmed analog to chezmoi's `output`) trivially replaces the DRY abstraction at the cost of minor duplication. |
| `executable_` filename-attribute chmod | `home/dot_local/bin/executable_claude` (3-line wrapper) | **Low cost.** A single explicit `chmod +x` in the container-create script (or a `[dotfiles]` mode/permission key, if one exists — unconfirmed, angle #2 §4) fully substitutes for the one file that needs it. |
| `chezmoi managed` CI introspection gate | `.github/workflows/ci.yml:105-124` — spins up a scratch `HOME`, runs `chezmoi init --source "$SRC" --apply=false`, asserts `.config/mise/config.toml` IS in `chezmoi managed` output, read directly | **Medium cost, but a designed-for replacement exists.** `mise dotfiles status --missing` — re-confirmed by direct query against `https://mise.jdx.dev/dotfiles.html` (2026-07-10): "exit 1 if anything is out of sync" — is explicitly built for exactly this CI-gate use case (angle #1 §9). Rewriting the CI step is real work (new scratch-HOME setup, new assertion shape) but is not blocked on a missing capability. |
| Secrets / encrypted dotfiles | `home/.chezmoidata.yaml` (5 lines, read directly) — contains only `platforms:` list, **no encrypted or secret-bearing fields anywhere** in `home/` | **Zero cost.** This repo's secrets flow entirely through Doppler at the devcontainer level (`.omc/research/research-20260709-r2-inventory/report.md` "Secrets" section, `devcontainer.json:198` `initializeCommand`), never through chezmoi's age/gpg file encryption. The commonly-cited "chezmoi has secrets, mise dotfiles doesn't" gap (angle #1 §12) is real in general but **inapplicable to this repo specifically** — there is nothing to migrate on this axis. |
| `run_*`/`run_once_*` scripts | `Glob home/**/run_*` and `home/**/*run_once*` — angle #2 confirms zero matches | **Zero cost.** This repo doesn't use chezmoi's script-execution feature at all, so mise dotfiles' lack of a run-script equivalent (angle #1 §13) is moot here. |
| `.chezmoiremove` | `home/.chezmoiremove` — 15 lines, all comments, confirmed empty | **Zero cost.** Unused mechanism; nothing to port. |

Net read: of the ~10 chezmoi-specific mechanisms this repo's `home/`
tree exercises, **most have low-or-zero real migration cost** once
checked against actual current usage rather than the feature's
theoretical footprint — several gaps chezmoi-parity.md (angle #2)
correctly flagged as "not covered" turn out to be either unused-in-
practice (osRelease branches, `.chezmoiremove`) or trivially
workaroundable (the shared-template DRY helper, the external-URL
fetch, the `executable_` chmod). **Exactly one gap is a hard, no-known-
workaround blocker: `promptBoolOnce`** — the Mac-host
`is_dev_computer`/`is_personal` interactive setup flow has no mise
counterpart, confirmed by direct re-query rather than inference from
the docs' silence.

### 5. Devcontainer-only apply model: mechanically compatible, doesn't change the calculus

The devcontainer-only constraint (`chezmoi apply`/`update` DENY-listed
on the Mac host per `.claude/settings.json` and
`python/src/dotfiles_setup/hook_guard.py:64`, per this run's baseline
inventory) is orthogonal to the replace/hybrid question: mise dotfiles'
own apply model is **also** manual-only by design — "Dotfiles are only
applied when explicitly requested with `mise dotfiles apply` or as part
of mise bootstrap. They are never applied implicitly" (angle #1 §7,
`https://mise.jdx.dev/dotfiles.html`). Swapping the single `chezmoi
init --apply ...` line in `on-create.sh:41` for a `mise dotfiles apply
--force --yes` call is a mechanically trivial one-line substitution
that preserves the exact same "runs once per container create,
non-interactive, in-container-only" invocation shape. This is the ONE
part of a hypothetical migration that is genuinely low-risk — the
lifecycle-hook architecture (`devcontainer.json` → `on-create.sh`)
doesn't care which tool renders the files, only that it's called at the
right point. The cost is entirely in the feature-parity gaps of §4, not
in the apply-mechanics wiring.

### 6. `user.html` / `shell.html` — these pages do not currently exist on mise's docs site

Per the domain brief's instruction to check `mise user.html` and
`shell.html` for a dotfile/shell angle: neither URL resolves. Angle #2
already recorded `https://mise.jdx.dev/shell.html` returning HTTP 404
(2026-07-10). Independently re-checked here via `WebSearch` for
`mise.jdx.dev "shell.html" OR "user.html"` (2026-07-10): no such pages
appear in the site's current structure. What DOES exist and IS relevant
to shell/dotfile management: `mise.jdx.dev/cli/shell.html` (the `mise
shell` **subcommand** page, "sets a tool version for the current
session" — session-scoped tool pinning, unrelated to dotfiles),
`mise.jdx.dev/cli/activate.md` (cached at
`docs/research/mintlify-cache/jdx/mise/llms.txt:5`, "Initialize mise in
your current shell session by adding it to your shell's rc file" — this
is the mechanism `.chezmoitemplates/env`'s `{{ output "mise" "activate"
.SHELL }}` shells out to, already covered in §4's shared-template row),
and `mise.jdx.dev/dev-tools/shims.md` (cached, PATH-activation vs shims
comparison — general tool-activation docs, not dotfile-file-management).
None of these surface any additional coexistence or migration-relevant
capability beyond what angle #1 and this report's §4 already establish.
The domain brief's referenced URLs appear to be stale/hypothetical
paths rather than pages that moved.

## Recommendation: neither (for now) — re-evaluate on a concrete trigger, not on a calendar

**Do not adopt mise `[dotfiles]` as a second, coexisting system in this
repo today, and do not migrate off chezmoi.** Reasoning, weighing all
three options:

- **Replace** fails on one hard, unworkaround-able blocker
  (`promptBoolOnce`, §4) plus real (if bounded) rewrite cost on the CI
  gate (§4) and the `$remote` detection (§4) — and the feature itself
  is ~1 month old with zero third-party production validation anywhere
  found (§3, corroborating angle #1 §14) and no state-tracking database
  (angle #1 §7, a real safety-net regression versus chezmoi's tracked
  apply). The mechanically-easy part (§5, the on-create.sh apply-call
  swap) is not the bottleneck; the feature-parity gaps are.
- **Complement/hybrid** has no concrete driver: §1 shows this repo's
  actual `home/` file set has no natural split point where mise's
  block/line-edit-into-a-foreign-file capability would do something
  chezmoi's own templating can't already do, and §2 shows a hybrid
  would require inventing new apply-ordering machinery
  (a new `on-create.sh` step, a new non-chezmoi-managed `[dotfiles]`
  table location) purely speculatively — cost with no offsetting
  benefit today.
- **Neither** (status quo) costs nothing extra and loses nothing: every
  chezmoi feature this repo actively depends on today (§4's blocker row
  plus the actively-used osRelease/`$remote`/CI-gate mechanisms) keeps
  working exactly as it does now.

This is explicitly a **"not yet," not a "never"** recommendation. Per
this repo's own `.claude/rules/tool-currency-and-native-first.md`
philosophy (prefer native/framework mechanisms, re-check periodically)
and the `mise-first` tool-management principle in the root `AGENTS.md`,
mise dotfiles is worth re-checking on a **concrete trigger**, not a
fixed calendar date:

1. mise ships an interactive-prompt-and-persist mechanism (closing the
   `promptBoolOnce` gap), OR the repo's own need for
   `is_dev_computer`/`is_personal` prompting goes away (e.g. the Mac
   host stops needing per-machine data at all); AND
2. The feature accumulates independent production track record (this
   research found zero as of 2026-07-10, §3) or a mise minor/patch
   changelog entry indicates post-release hardening; AND
3. A genuine "small edit into a file something else owns" need actually
   arises in `home/` that chezmoi's own templating can't cleanly serve
   — at which point a **scoped** complement (mise dotfiles for that one
   new use case only, chezmoi keeping everything else) is the right
   shape, not a wholesale hybrid.

## Uncertainties / gaps

- **Whether the devcontainer sets any of the 5 non-`stat` `$remote`
  signals** (`CODESPACES`, `SSH_CONNECTION`, `KUBERNETES_SERVICE_HOST`,
  `container`, `REMOTE_CONTAINERS`) was not verified against a live
  container in this session (no running devcontainer available to
  probe `env` inside it). If none are set, the `/.dockerenv` `stat`
  check is load-bearing rather than redundant, raising §4's "$remote
  gate" row from Medium to a harder blocker. A follow-up should run
  `env | grep -E 'CODESPACES|SSH_CONNECTION|KUBERNETES|container|REMOTE_CONTAINERS'`
  inside the actual devcontainer to close this gap.
- **Whether mise dotfiles' `[dotfiles]` table entries can be wrapped in
  `{% if %}` to conditionally declare/omit entries** (needed to
  replicate `.chezmoiignore`'s machine-conditional gating, e.g. the
  linux-only mise-overlay hard gate) is unverified — inherited directly
  from angle #2 §3/§4, not independently resolved in this angle either.
  This affects the mechanical feasibility of §2's hypothetical hybrid
  (declaring dotfiles entries only on the devcontainer) as much as it
  affects a full replacement.
- **Whether mise dotfiles has a `mode`/permission key** replacing
  chezmoi's `executable_` filename-attribute chmod is unconfirmed (not
  stated on the fetched `dotfiles.html` page; angle #2 §4 flagged the
  same gap). Low-stakes either way since a one-line `chmod +x`
  workaround exists regardless.
- **No empirical test was run** — this entire angle (like angles #1 and
  #2) is documentation-and-source-reading based; no live `mise dotfiles
  apply --dry-run` was exercised against this repo's actual file set
  because no local mise environment was available in this Bash-broken
  research session (`Bash` tool fails with `No interpreter found for
  Python >=3.14` for the PreToolUse hook, blocking every shell command
  including plain `mise` invocations). A future session with a working
  devcontainer should validate the `mise dotfiles status`/`apply
  --dry-run` output against a scratch `[dotfiles]` table mirroring a
  handful of `home/` entries before treating any of §4's "low cost"
  assessments as proven rather than argued.
- **CHANGELOG/issue-tracker history for `[dotfiles]` since v2026.6.6**
  was not walked (no GitHub issue search restricted to the `dotfiles`
  label/keyword within `jdx/mise`'s own tracker was run beyond the two
  general web searches in §3) — post-release bugfixes or stability
  caveats specific to the feature are unconfirmed one way or the other.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — read `home/**` (dot_zshrc.tmpl, dot_bashrc.tmpl, dot_profile.tmpl, dot_tmux.conf.tmpl, .chezmoiexternal.toml, .chezmoidata.yaml, .chezmoitemplates/env, .chezmoi.toml.tmpl, .chezmoiignore, .chezmoiroot), `.devcontainer/scripts/on-create.sh`, `.devcontainer/AGENTS.md`, `.github/workflows/ci.yml` (chezmoiignore hard-gate CI step), `.claude/settings.json`/`python/src/dotfiles_setup/hook_guard.py` (host deny-list) for file:line evidence of every apply-mechanics and gap claim in this report; also read this run's sibling angle reports in full.
- [jdx/mise](https://github.com/jdx/mise) — fetched `mise.jdx.dev/dotfiles.html` twice (coexistence/migration text query, then the `status --missing` / prompt-mechanism re-query) and `mise.jdx.dev/bootstrap.html` (chezmoi-mention check), plus the `v2026.6.6` release tag for the feature's ship date; grepped the local mintlify cache (`docs/research/mintlify-cache/jdx/mise/llms.txt`) for the site's page index to confirm no dedicated `shell.html`/`user.html`/`dotfiles.html` cache entries exist.
- [twpayne/chezmoi](https://github.com/twpayne/chezmoi) — chezmoi is the pre-existing system throughout this repo's `home/` tree; no additional live chezmoi.io fetch was needed beyond what angle #2 already sourced (cited via that report, not re-fetched here).
- [dankaiser1808/dotfiles](https://github.com/dankaiser1808/dotfiles) and [shunk031/dotfiles](https://github.com/shunk031/dotfiles) — surfaced in web search as examples of the pre-existing chezmoi+mise (non-overlapping-concern) pattern; titles/descriptions only, not cloned or read.
