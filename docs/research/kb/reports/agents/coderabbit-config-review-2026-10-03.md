# CodeRabbit `.coderabbit.yaml`: full option review + schema-validated setup

Date: 2026-10-03. Read-only research (GET / GraphQL query only; no repo edits, no GitHub writes).
Status: COMPLETE. Builds on (does not redo)
`docs/research/kb/reports/agents/coderabbit-conversation-resolution-2026-10-03.md` (that report's
§3 option (c) is what this one specifies).

Scratch (all evidence files): `/Users/rmanaloto/.claude/jobs/9dcdab49/tmp/coderabbit/`
— `schema.v2.json`, `inventory.tsv` (every property path), `docs/*.md` (fetched pages),
`kb.coderabbit.yaml`, `dotfiles.coderabbit.yaml`, `neg-*.yaml`, `schema.v2.strict.json`,
`validation.log`, and the scripts that produced them (`walk.py`, `validate_all.py`, `strict.py`,
`probe_repos.py`, `probe2.py`).

## 0. Headline findings

1. **Repo file wins over the UI, and REPLACES it.** A `.coderabbit.yaml` is priority 2, under only
   org/workspace *global overrides*; it outranks the central `coderabbit` repo and every UI setting.
   Sources do NOT merge unless `inheritance: true` (§2).
2. **The published schema is only half-closed.** The root object has `additionalProperties: false`,
   but `reviews`, `chat`, `auto_review` and ~100 other nested objects do not: a typo such as
   `reviews.path_filter:` validates **rc=0** under both check-jsonschema and python-jsonschema (§4.3).
   A derived "strict" overlay closes 105 objects and makes that typo fail.
3. **`*.pkl` is in CodeRabbit's default ignore list** (meant for Python pickles), so `hk.pkl`,
   `hk-common.pkl`, `hk-image.pkl` — core config in both repos — are never reviewed today
   (`docs/configuration__path-instructions.md:311`). Re-adding `**/*.pkl` without `!` overrides it.
4. **No "summary-only" mode and no standalone auto-resolve key.** Thread auto-resolution exists only
   inside `request_changes_workflow` (on CodeRabbit's next review) or via the explicit
   `@coderabbitai resolve` / `approve` commands. `path_filters` is the only lever that guarantees no
   threads on a path.
5. **Docs/schema drift:** `remote_config` is documented (`getting-started/yaml-configuration.md:79-83`)
   but absent from schema.v2.json; a file using it FAILS validation (rc=1, §4.3).
6. **CodeRabbit reviews dotfiles too** (30/30 recent PRs carry a CodeRabbit comment; 10 unresolved
   CodeRabbit threads) — but dotfiles does not require conversation resolution, so they never block.

## 1. Repo state (measured, with control arms)

Script: `probe_repos.py`, `probe2.py` (scratch).

| Probe | knowledge-base | dotfiles | Control arm |
|---|---|---|---|
| `GET contents/.coderabbit.yaml` | 404 | 404 | `contents/.gitignore` → 200 in both |
| `GET contents/.coderabbit.yml` | 404 | 404 | same |
| Central repo `ray-manaloto/coderabbit` | 404 | — | `repos/ray-manaloto/dotfiles` → 200 |
| Visibility | public | public | — |
| Classic `required_conversation_resolution` | **true**, enforce_admins **true** | **false**, enforce_admins false | — |
| Ruleset `required_review_thread_resolution` | (no rules) | false (`pull_request` rule) | — |

**Does CodeRabbit review dotfiles?** Yes. GraphQL over the last 30 PRs (#1547..#1635): 30 PRs with
a `coderabbitai` comment, 6 `coderabbitai` reviews, 10 CodeRabbit-authored review threads, all 10
unresolved (e.g. #1633 on `python/src/dotfiles_setup/session_orphans.py` and a
`docs/research/kb/reports/agents/` report; #1622 on `worktree_guard.py`). Control: the same query
on knowledge-base (#770..#865) returns 29 PRs with CodeRabbit and its 38 threads, including #865's
six on `docs/research/reports/**` + `docs/artifacts/kb837-merge-options.html` — so the query sees
CodeRabbit where it exists. Other bot authors seen: `graphify-labs`, `repowise-bot` (both repos),
`greptile-apps` (KB).

**UI-side config may exist for dotfiles (unverified).** The #1633 walkthrough lists "Code guidelines
(6)": `AGENTS.md` and `tests/AGENTS.md` as *auto-discovered*, and four files as *configured* —
`.claude/rules/ci-local-parity.md`, `.claude/rules/verify-before-advancing.md`, and two
`docs/research/runs/*/report.md` (comment `issuecomment-5975009378`). No repo file exists, and the
schema default for `knowledge_base.code_guidelines.filePatterns` is `[]`, so "configured" points at
UI settings or link-following from AGENTS.md (all four are cited in `AGENTS.md:110,144,160,188`, but
so are ~8 other rules that are NOT listed, so link-following alone does not explain it). The API
cannot read UI settings; `@coderabbitai configuration` on a PR would (a GitHub write — Ray's call).
This matters because of §2: a committed file without `inheritance: true` silently drops any UI
config.

## 2. Config-source precedence (docs)

Source: `https://docs.coderabbit.ai/guides/configuration-overview.md` (saved
`docs/guides__configuration-overview.md`) and `/configuration/configuration-inheritance.md`.

| Priority | Source |
|---|---|
| 0 (highest) | Workspace global overrides (Enterprise) |
| 1 | Organization global overrides (UI) |
| 2 | **Repository file** — `.coderabbit.yaml` or `.coderabbit.config.ts` |
| 3 | Central repository — `.coderabbit.yaml` in the org's `coderabbit` repo |
| 4 | Repository settings (UI) |
| 5 | Organization settings (UI) |
| 6 | Workspace settings (Enterprise) |
| 7 (lowest) | Schema defaults |

(`configuration-overview.md:182-244`; identical table `configuration-inheritance.md:40-98`.)

- **Repo file overrides the UI: yes.** And by REPLACEMENT: *"Configuration sources don't merge by
  default"* (`configuration-overview.md:184`); the worked example says a local file that omits a
  setting gets the **default**, not the org/central value (`:250`).
- `inheritance: true` (root key, default false — schema `inheritance`, `configuration-inheritance.md:11-14`)
  merges with the next level up; chain stops at the first level without it (`:28-32`). Objects deep
  merge, scalars child-wins, arrays child-first then unique parent items deduped by
  `path`/`label`/`name`/`id`/`key` (`:132-139`).
- Global overrides beat even the repo file (`configuration-overview.md:262-264`) and can force
  `inheritance: true` org-wide (`:316-318`).
- `.coderabbit.yaml` beats `.coderabbit.config.ts` if both exist (`configuration-overview.md:148-150`).
- **The feature branch's file is used for that PR's review** (`getting-started/yaml-configuration.md:23`)
  — a PR can change its own review config; forks use the target branch's
  (`reference/review-commands.md:685-687`).
- Diagnosis: `@coderabbitai configuration` prints the resolved YAML annotated per key with its
  source (`configuration-overview.md:252-254`; `review-commands.md:521-537`);
  `@coderabbitai generate configuration` opens a PR exporting it (`review-commands.md:540-556`).
- Per-PR override in the PR **description**: `@coderabbitai configuration override` + YAML block,
  limited to `reviews.review_details` and `knowledge_base.code_guidelines.filePatterns`
  (`review-commands.md:653-664`).

## 3. Full option inventory (schema walked programmatically)

**Schema evidence.** `https://coderabbit.ai/integrations/schema.v2.json` answers **301 →
`https://www.coderabbit.ai/integrations/schema.v2.json`**, which returns 200, `application/json`,
78,992 bytes, ETag `"78f815e0191974741a96734d4df21924"`, `Last-Modified: Sun, 04 Oct 2026 00:49:46 GMT`
(i.e. republished today), `cache-control: max-age=3600`. sha256 (raw bytes)
`b16cfbfb90e8030b6ba1c16a166ec8ed4d7e1a7841116dc014d2bd3fd9f5a240`. Control: `schema.v9.json` (with
`-L`) → 404. Correction to the brief: a non-following GET of the bare `coderabbit.ai` URL returns
301 for BOTH v2 and v9, so a 200-vs-404 split only discriminates with redirects followed.
Dialect `https://json-schema.org/draft/2020-12/schema`; no `$id`, no `$ref`/`$defs` (fully inlined).
`Draft202012Validator.check_schema` passes (it ran in every python-jsonschema arm, §4.3).

**Counts** (`walk.py` → `inventory.tsv`, 305 rows, 305 unique paths): 10 top-level keys;
by subtree `reviews` 236 (of which `reviews.tools` = 59 tools), `knowledge_base` 31,
`issue_enrichment` 13, `chat` 10, `code_generation` 10, and 1 each for the five scalars.
`additionalProperties: false` appears on only **5** objects: root, `reviews.tools.htmlhint`,
`reviews.tools.stylelint`, `knowledge_base.mcp`, `knowledge_base.linked_repositories[]`.

The brief's guessed top-level list is partly wrong: `path_filters`, `path_instructions`, `profile`,
`request_changes_workflow`, `auto_review`, `tools`, `finishing_touches` are all **under `reviews`**;
the real top level is `language, tone_instructions, early_access, enable_free_tier, inheritance,
reviews, chat, knowledge_base, code_generation, issue_enrichment`.

### 3.1 Top-level scalars

| Key | Type / default | What it does | Relevance |
|---|---|---|---|
| `language` | enum (≈90 locales) / `en-US` | Review language | none |
| `tone_instructions` | string / `""` | Free-text tone for reviews + chat | low; could say "terse, no praise" |
| `early_access` | bool / false | Early-access features | keep false (stability) |
| `enable_free_tier` | bool / true | Free-tier features for non-paid users | leave default |
| `inheritance` | bool / false | Merge with parent config levels | **decision point** (§2, Q2) |

### 3.2 `reviews` (236 paths) — grouped

| Area | Keys (default) | What it does | Relevance |
|---|---|---|---|
| Strictness | `profile` (`chill`; enum quiet/chill/assertive) | Volume of feedback | **KB: `quiet`**; dotfiles: `chill` |
| Approval gate | `request_changes_workflow` (false); `allow_author_approval` (true) | CHANGES_REQUESTED on actionable comments; resolves addressed threads on next review; approves when clean | **keep false** while rate-limited (§5) |
| Summary / walkthrough | `high_level_summary` (true), `_instructions`, `_placeholder`, `_in_walkthrough`; `collapse_walkthrough` (true); `changed_files_summary`, `sequence_diagrams`, `estimate_code_review_effort`, `assess_linked_issues`, `related_issues`, `related_prs` (all true); `poem` (false); `in_progress_fortune` (true) | Content of the summary comment (comments, NOT threads) | trim noise; no effect on merge blocking |
| Status surfaces | `review_status` (true), `review_details` (false), `review_progress` (true), `commit_status` (true), `fail_commit_status` (false) | Status messages/check runs; `review_details` lists ignored files + suppressed comments | `review_details: true` makes path_filters auditable |
| Titles | `auto_title_placeholder`, `auto_title_instructions` | Auto-generate PR title | none |
| Labels / reviewers | `suggested_labels` (true), `labeling_instructions[]`, `mutually_exclusive_groups`, `auto_apply_labels` (false), `suggested_reviewers` (true), `auto_assign_reviewers` (false), `suggested_reviewers_instructions[]` | Label/reviewer suggestions | off (single-maintainer repos) |
| AI-agent prompts | `enable_prompt_for_ai_agents` (true) | "Prompt for AI Agents" block in inline comments | keep (agents act on threads) |
| **Scope** | `path_filters[]` ([]) | Glob include/`!`exclude; also drives sparse-checkout | **primary lever** |
| **Guidance** | `path_instructions[]{path,instructions}` ([]) | Per-glob review guidance | shape remaining review |
| Run control | `abort_on_close` (true), `disable_cache` (false) | Abort on close; cache | default |
| Slop | `slop_detection{enabled:true, include_all_authors:false, label}` | Flags low-quality PRs (public repos) | default (authors are collaborators) |
| **Auto review** | `auto_review{enabled:true, description_keyword:"", auto_incremental_review:true, auto_pause_after_reviewed_commits:5, ignore_title_keywords[], labels[], drafts:false, base_branches[], ignore_usernames[]}` | When reviews run | `auto_pause…: 0`; `ignore_usernames` for bots |
| Finishing touches | `finishing_touches{docstrings, unit_tests, simplify(false), autofix, fix_ci, resolve_merge_conflict}.enabled` (true except simplify), `custom[]{enabled,name,instructions}` | Agentic follow-up actions (open PRs / commit) | disable docstrings/unit_tests (noise); keep autofix opt-in |
| Pre-merge checks | `pre_merge_checks{override_requested_reviewers_only, docstrings{mode:warning,threshold:80}, title{mode,requirements}, description{mode}, issue_assessment{mode}, custom_checks[]{mode,name,instructions}}` | Gates; `error` can block only with request_changes_workflow | docstrings → `off` (dotfiles#1633 shows a 56% < 80% warning) |
| Post-merge | `post_merge_actions[]{enabled,name,prompt}` | Agent actions after merge | none |
| Tools | `tools.<59 tools>.enabled` (all true) + per-tool options | Linters whose output feeds review | §3.3 |

### 3.3 `reviews.tools` (59)

All default `enabled: true`. Relevant to these repos and already run locally by hk (duplicate
findings become blocking threads in KB): `ruff` (+`config_file`), `shellcheck`, `markdownlint`,
`yamllint`, `hadolint`, `actionlint`, `zizmor`, `gitleaks` (Betterleaks), `trufflehog`,
`languagetool` (+rules/categories/level), `ast-grep` (+`rule_dirs`, `util_dirs`, `essential_rules`,
`packages`), `github-checks`, `semgrep`/`opengrep`, `osvScanner`, `trivy`, `checkov`, `skillspector`
(AI-agent skill/MCP config scanner — new signal for `.claude/skills/**`), `presidio`, `clang`,
`cppcheck`, `pylint`, `flake8`. Irrelevant language tools: biome, eslint, swiftlint, php*, golangci,
detekt, rubocop, buf, regal, pmd, clippy, sqlfluff, squawk, prismaLint, oxc, luacheck, brakeman,
etc. Full list: `inventory.tsv` rows `reviews.tools.*`.

### 3.4 Other top-level areas

| Area | Keys | Relevance |
|---|---|---|
| `chat` | `art` (true), `allow_non_org_members` (true), `auto_reply` (true), `integrations.{jira,linear}.usage` (auto), `jira.issue_template` | `art: false`; `allow_non_org_members` matters on public repos |
| `knowledge_base` | `opt_out`, `web_search.enabled`, `code_guidelines{enabled, filePatterns[] (string or {files,applyTo})}`, `learnings{scope, approval_delay}`, `issues.scope`, `jira/linear`, `pull_requests.scope`, `mcp{usage, disabled_servers}`, `automatic_linking_mode` (disabled), `automatic_repository_linking` (deprecated), `linked_repositories[]{repository,instructions}` | `code_guidelines` auto-reads `**/AGENTS.md`, `**/CLAUDE.md` etc. (schema description); `linked_repositories` could cross-link dotfiles↔KB |
| `code_generation` | `docstrings{language, path_instructions[]}`, `unit_tests{path_instructions[]}` | only if finishing touches used |
| `issue_enrichment` | `auto_enrich.enabled` (false), `planning{enabled:true, auto_planning{enabled, labels[]}}`, `labeling{labeling_instructions[], auto_apply_labels}` | issue-side; leave default |

Not in schema but documented: `remote_config` (shared config by repo/url,
`getting-started/yaml-configuration.md:57-107`). TypeScript alternative `.coderabbit.config.ts` with
optional npm `@coderabbitai/config` (latest 1.1.0, published 2026-10-01; ships `.d.ts` types only,
no JSON schema — checked the tarball).

## 4. Schema-validation setup

### 4.1 This repo's conventions (dotfiles)

- `schemas/sources.toml` rows {tool, file, version, source, pin_source, sha256}; the codex row is
  the precedent for an **unversioned** URL: *"its `version` is only a label … `sha256` is what
  verifies them"* (`schemas/sources.toml:10-12`; `schema_vendor.py:118-126` `_VENDORED_PIN_TOOLS`).
- `mise run schema-vendor-refresh` → `dotfiles-setup schema-vendor refresh` (`mise.toml:1504-1506`):
  `_source_url` falls back to the recorded `source` for untemplated tools (`schema_vendor.py:225-267`);
  fetched bytes are `_hygiene_normalize`d through hk fixers before hashing (`:337-372`); `curl -fsSL`
  follows redirects (`:387-389`). Codex has a derived sibling (`codex-agent.json`, rederived in
  `refresh`, `:471-492`).
- `mise run schema-vendor-check` (`mise.toml:1500-1502`) = suite `config.schema-vendor-drift`
  (`python/verification/suites.toml:2928-2946`); directive lines are bound separately by
  `config.schema-vendor-directives-bound` (`:2948-2975`, `require_lines`).
- CI: `refresh.yml` `schema-refresh` job (`.github/workflows/refresh.yml:505-577`) — its `paths:`
  list must name every vendored file "in lockstep" (`:567-577`; #1443 broke main by missing one).
- **Validator already pinned:** `"pipx:check-jsonschema" = "0.38.0"` in
  `.config/mise/conf.d/shared.toml:40` (locked in `.config/mise/mise.lock:601` and
  `.devcontainer/mise-system.lock:4997`), used today only by `scripts/validate-devcontainer-json.sh:71`
  (against a REMOTE URL). python `jsonschema` 4.26.0 is in `python/uv.lock:1112` (used by
  `tests/test_orchestration_contracts.py:11`). hk 2.3.0 has **no** jsonschema builtin (161 builtins
  listed from `jdx/hk@v2.3.0/pkl/builtins`; only `mdschema`, `yamlfmt`, `yamllint`,
  `sort_package_json` match json/yaml/schema; control: `yamllint.pkl` present). `yamllint 1.38.0`
  is pinned (`shared.toml:50`).

### 4.2 Proposal (dotfiles)

1. **Vendor** a new `sources.toml` row, modelled on codex:
   ```toml
   [[schema]]
   tool = "coderabbit"
   file = "schemas/coderabbit.json"
   version = "2026-10-04"   # label only: Last-Modified of the reviewed bytes
   source = "https://www.coderabbit.ai/integrations/schema.v2.json"
   pin_source = "schemas/sources.toml (vendored; unversioned SaaS schema)"
   sha256 = "<hygiene-normalised hash written by refresh>"
   ```
   Code changes: add `"coderabbit"` to `_VENDORED_PIN_TOOLS` (no pin resolver exists — CodeRabbit is
   SaaS), let `_source_url` use the recorded URL, add `schemas/coderabbit.json` to `refresh.yml`'s
   `paths:`. Record the canonical `www.` URL (the apex 301s). Note the URL is unversioned and was
   republished the day of this probe, so the weekly refresh PR will churn; `sha256` is the only
   identity. (Churn rate unmeasured — the Wayback CDX query returned 503; named gap.)
2. **Derive a strict overlay** `schemas/coderabbit.strict.json` in `refresh` (same pattern as
   `codex-agent.json`): set `additionalProperties: false` on every object that declares `properties`
   and leaves it unset (`strict.py`: 105 objects). Justification: upstream accepts nested typos (§4.3),
   and CodeRabbit ignores unknown keys server-side as far as the schema says — so a misspelt
   `reviews.path_filter` would silently do nothing while gates pass. Risk: if CodeRabbit's server
   accepts keys its schema omits (e.g. `remote_config`), strict rejects them too — but the upstream
   schema already rejects `remote_config` at root, so this is no new class.
3. **Header** (first line of `.coderabbit.yaml`, yaml-language-server modeline syntax per
   `redhat-developer/yaml-language-server` README:86):
   `# yaml-language-server: $schema=./schemas/coderabbit.json` — the vendored copy, mirroring the
   `#:schema ./schemas/mise.json` convention (offline, no per-run network). Bind it with a new
   `per_path_lines` entry in `config.schema-vendor-directives-bound`.
4. **hk step** (custom; no builtin exists), in `hk.pkl`:
   ```pkl
   ["coderabbit_schema"] {
     glob = List(".coderabbit.yaml")
     check = "check-jsonschema --schemafile schemas/coderabbit.strict.json .coderabbit.yaml"
   }
   ```
   One command, no bash script (zero-bash-logic; no `bash_budget.py` entry). yamllint already covers
   `*.yaml` — needed, because JSON-schema validators load YAML with last-key-wins and cannot see a
   duplicate key (control: `neg-yaml-dupkey.yaml` → yamllint rc=1 `key-duplicates`).
   Optional: a `verify` suite asserting the hk step + header + sources row exist (pattern:
   `workflow.bash-logic-enforcement`).

### 4.3 Validation runs (actual rc)

`validate_all.py` runs every file through **two independent routes** — check-jsonschema 0.38.0
(`~/.local/share/mise/installs/pipx-check-jsonschema/0.38.0/bin/check-jsonschema --schemafile`)
and python `jsonschema.Draft202012Validator` from the dotfiles uv env. Log: `validation.log`.

| File | Defect injected | upstream schema (cj / py) | strict overlay (cj) |
|---|---|---|---|
| `kb.coderabbit.yaml` | none | **0 / 0** | **0** |
| `dotfiles.coderabbit.yaml` | none | **0 / 0** | **0** |
| `neg-root-bogus.yaml` | root key `revews_typo` | 1 / 1 ("Additional properties … 'revews_typo'") | 1 |
| `neg-enum.yaml` | `profile: loud` | 1 / 1 (not one of quiet/chill/assertive) | — |
| `neg-type.yaml` | `auto_pause_after_reviewed_commits: never` | 1 / 1 (not integer) | — |
| `neg-nested-bogus.yaml` | `reviews.path_filter_typo` | **0 / 0 — SCHEMA GAP** | **1** |
| `neg-remote-config.yaml` | documented `remote_config` | 1 / 1 (doc/schema drift) | — |

Both routes agree on every row, so neither validator is the broken probe. yamllint `--strict` with
dotfiles' `.yamllint.yaml` on both drafts: rc=0 (control dup-key file rc=1).
Draft sha256: KB `bf679c924e1dbd63b2b70656c307e76bbee5d1105b066e2b3d07ac739eb156da`, dotfiles
`5e0150eee1efee5f28f21622b1563a25a3874dc7320948af768160cce4e95a1a`; strict overlay
`248d7f892be00f80d08fd2f288135cc91fa4465ec6d3ec895fe294a887ede619`.

### 4.4 knowledge-base conventions

KB `schemas/` (20 tracked files) holds **its own** schemas (`fetch-receipt`, `guard-policy`,
`research-record`, `worktree`, …) used for datamodel-code-generator (`pyproject.toml:341`
`input-file-type = "jsonschema"`) plus vendored deps.dev/googleapis protos — **no `sources.toml`,
no vendor/refresh machinery**. `jsonschema` 4.26.0 is in KB `uv.lock:1003`; `check-jsonschema` is
NOT in KB `mise.toml` (grep: 0 hits). Options for KB: (a) vendor `schemas/coderabbit.json` +
`schemas/coderabbit.strict.json` and validate with a small `kb_setup` command using the
already-locked python `jsonschema` (no new tool); or (b) add `pipx:check-jsonschema` to KB's mise
and copy the dotfiles hk step. Refresh in KB would be a new mechanism; cheapest is to sync the
vendored bytes from dotfiles via the existing `rule-sync` cross-repo set (`rule-sync.toml`).

## 5. Draft configs and the thread question

Drafts (validated, §4.3): scratch `kb.coderabbit.yaml`, `dotfiles.coderabbit.yaml`.

**KB draft essentials** — `inheritance: false`; `reviews.profile: quiet`;
`request_changes_workflow: false`; `review_details: true`; summary noise off;
`auto_review.auto_pause_after_reviewed_commits: 0`; `path_filters` excluding the trees KB's own
`hk.pkl` treats as records — `docs/research/**`, `docs/session-review/runs/**`,
`docs/currency/runs/**`, `docs/goals/*-goal.md`, `docs/direction/**` (`proseExclude`,
KB `hk.pkl:182-186`), plus `docs/agents/evidence/**`, `docs/artifacts/**` (#865), `sources/**`,
`graphify-out/**`, `raw/**` (`baseExclude`, KB `hk.pkl:23-105`), vendored protos; and
`**/*.pkl` to re-include `hk.pkl`. `path_instructions` restrict `python/**` to defects and `**/*.md`
to factual errors. Tools duplicated by hk off (`ruff`, `markdownlint`, `languagetool`, `yamllint`);
finishing-touch docstrings/unit_tests off; `pre_merge_checks.docstrings.mode: "off"`.
Replayed against #865: all six threads were on `docs/research/reports/**` and `docs/artifacts/**`,
both excluded → zero threads (inference from the path list, not a live CodeRabbit run).

**dotfiles draft essentials** — same shape, `profile: chill`; excludes mirror
`hk-common.pkl:42-64` (`docs/research/**`, `docs/specs/**`) plus `docs/receipts/**`,
`docs/handoffs/**`, `docs/agents/goal-history.md` (append-only), the five vendored
`schemas/*.json` + `.claude/types/claude-code.d.ts` (sources.toml), graphify-managed skill bytes;
`**/*.pkl` re-included; path instructions encode zero-bash-logic, SHA-pinned actions,
no-inline-suppressions; hk-duplicated tools off (`ruff`, `shellcheck`, `hadolint`, `actionlint`,
`yamllint`, `markdownlint`, `languagetool`). `ignore_usernames: [renovate[bot]]` is marked
UNVERIFIED (gh reports the author as `app/renovate`; CodeRabbit matches "exact match; not email
addresses" — schema `reviews.auto_review.ignore_usernames` description, `inventory.tsv`).

**How threads get auto-resolved — options, all from docs:**

| Mechanism | Behaviour | Fit |
|---|---|---|
| `path_filters` exclusion | Excluded files get no review content at all (`path-instructions.md:84-86`) | **Guaranteed** for those paths — the recommended lever |
| `request_changes_workflow: true` | Next review resolves threads the changes addressed (`request-changes-workflow.md:65-66`); during a rate-limited run it "may still resolve" addressed threads but approval stays pending (`:94-96`); adds a CHANGES_REQUESTED review per actionable review (`:57-58`) | Poor while most KB PRs are rate-limited (9 of the last 30 KB summary comments say rate-limited, `probe2.py`; `pr.py:69`) |
| `@coderabbitai resolve` (top-level comment) | Resolves ALL CodeRabbit comments (`review-commands.md:472-493`) | Blanket; prior report rejected automated use (suppression) |
| `@coderabbitai approve` | Resolves all, then approves only if request_changes_workflow on (`review-commands.md:446-469`) | Same |
| `reviews.allow_author_approval: false` | Stops the PR author using resolve/approve (`request-changes-workflow.md:102-110`) | Irrelevant unless resolve is automated |

There is **no** key that keeps inline review but posts no threads, and no per-thread auto-resolve
outside request_changes_workflow (grep of all 20 fetched pages for `auto.?resolv`: 0 hits; control:
`resolves addressed threads` found at `request-changes-workflow.md:65`).

## 6. Open questions for Ray (each with a recommendation)

1. **Commit the KB `.coderabbit.yaml` (path_filters + quiet)?** Recommend **yes** — removes the #865
   class while keeping conversation resolution for human threads. PRO: reviewed, versioned, zero
   protection change. CON: CodeRabbit stops reading research records entirely.
2. **`inheritance: false` or `true`?** Recommend **first post `@coderabbitai configuration` on one
   open PR in each repo** (a GitHub write, so yours to approve) to see what UI config exists, then
   choose `false` (file is the single source of truth). PRO: everything reviewable in git. CON: if
   the UI holds the dotfiles "configured" guideline sources (§1), `false` drops them silently.
3. **Validate against the strict overlay or the upstream schema?** Recommend **strict** — upstream
   passes nested typos (`neg-nested-bogus` rc=0). CON: a derived artifact to maintain; may reject a
   key CodeRabbit accepts but forgot to publish.
4. **Vendor via `schema_vendor` (unversioned, sha256-only like codex)?** Recommend **yes** in
   dotfiles; KB consumes the bytes through `rule-sync`. CON: weekly refresh PRs may churn
   (Last-Modified = probe day).
5. **Exclude `docs/specs/**` in dotfiles?** Recommend **yes**, matching `hk-common.pkl:64` (verbatim
   user requirements). CON: loses CodeRabbit's read of design specs; dotfiles has no
   conversation-resolution gate, so the noise costs nothing at merge time — the alternative is a
   lighter `path_instructions` entry instead.
6. **Turn off hk-duplicated CodeRabbit tools?** Recommend **yes** (ci-local-parity already runs
   them). CON: loses CodeRabbit's own runs of zizmor/gitleaks — keep those on (draft does).
7. **Keep `request_changes_workflow` off?** Recommend **yes** until rate limiting stops; revisit then.

## Named gaps

- UI-side settings unreadable via API; `@coderabbitai configuration` not posted (GitHub write).
- Schema change frequency unmeasured (Wayback CDX 503).
- `ignore_usernames` spelling for Renovate unverified.
- No live CodeRabbit run of either draft; the #865 replay is path-list inference.
- Whether CodeRabbit's server rejects or ignores unknown nested keys is undocumented.

## GitHub repos touched

- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) — `.coderabbit.y{a,}ml` probes, protection, PR threads/comments (#770..#865), local `hk.pkl`, `schemas/`, `pr.py`
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — `.coderabbit.y{a,}ml` probes, protection/rules, PR reviews (#1547..#1635), `schemas/sources.toml`, `schema_vendor.py`, `hk.pkl`, `refresh.yml`
- [ray-manaloto/coderabbit](https://github.com/ray-manaloto/coderabbit) — central-config repo probe (404)
- [jdx/hk](https://github.com/jdx/hk) — v2.3.0 `pkl/builtins` listing (no jsonschema builtin)
- [redhat-developer/yaml-language-server](https://github.com/redhat-developer/yaml-language-server) — `$schema` modeline syntax (README:86)
- [coderabbitai/mono](https://github.com/coderabbitai/mono) — repository of npm `@coderabbitai/config` (tarball inspected via npm registry, not GitHub)
