# Premise verification — ITEM 11 revision 2 (schema references for config files)

Lane: `fable-orchestrator:premise-verifier` (Claude, read-only brief), 2026-09-02.
Spec under verification: `scratchpad/spec-item11-schemas.md` (session scratchpad, untracked).
Supersedes/extends `2026-09-02-premise-verify-item11.md` (revision 1).

**This lane HAD network** (Bash + `taplo` 0.10.0 at
`~/.local/share/mise/installs/taplo/0.10.0/taplo`), so the rows the architect
marked "mark UNVERIFIABLE" were instead **re-probed live, with control arms**.
Nothing below is carried from the architect's numbers.

---

PREMISE REPORT
ROWS: 11 checked — 7 CONFIRMED / 2 REFUTED (L9, A1) / 2 UNVERIFIABLE (L6, L7)

## Row-by-row

**L1 — CONFIRMED (re-probed, both arms).**
`taplo lint` on a scratch file carrying `#:schema https://mise.jdx.dev/schema/mise.json`
→ **rc=0**. Same file with `…/schema/NOPE-does-not-exist.json` → **rc=1**, and taplo
names why: `failed to fetch schema error=error decoding response body: expected value
at line 1 column 1`. The probe discriminates.

**L2 — CONFIRMED (re-probed on the REAL file bodies).**
Scratch copies of all four mise files with a real `#:schema` directive, `taplo lint`
each, counting lines matching `^error`:

| file body | rc | `^error` lines |
|---|---|---|
| `mise.toml` | 0 | 0 |
| `.config/mise/conf.d/shared.toml` | 0 | 0 |
| `.devcontainer/mise-runtime.toml` | 0 | 0 |
| `.devcontainer/mise-system.toml` | 0 | 0 |

**L3 — CONFIRMED (both arms).** `[toolz]` (unknown section) → rc=0, no error.
`node = 12345` under `[tools]` → **rc=1**, `error: 12345 is not valid under any of the
schemas listed in the 'oneOf' keyword`. Validation is type-level, not typo-level —
exactly as the row states.

**L4 — CONFIRMED (cross-control reproduced).** `ruff.toml` body under the ruff schema
→ rc=0, 0 error lines. The same body under the **typos** schema → **rc=1, exactly 2
`^error` lines**: `Additional properties are not allowed ('extend', 'lint' were
unexpected)` (emitted twice). The architect's "2" is reproduced independently.

**L5 — CONFIRMED.** `typos.toml` body under
`https://raw.githubusercontent.com/crate-ci/typos/master/config.schema.json` → rc=0,
0 error lines. (The `github.com/.../blob/...` form being an HTML page is not re-probed
here; it is not load-bearing — the raw URL demonstrably works.)

**L6 — UNVERIFIABLE HERE, non-blocking.** Not re-fetched. `additionalProperties: true`
on the Claude settings schema is a claim about a remote document; nothing on disk
settles it. Cost of being wrong is editor-only (see §4 of the spec: no gate parses
JSON `$schema` — confirmed independently in MISSING M3 below).

**L7 — UNVERIFIABLE HERE.** A prior run's rc; not reproduced. Non-blocking — the
spec's own §5 re-runs all three before the diff lands.

**L8 — CONFIRMED (both arms).** Unreachable/bogus schema URL → rc=1 (L1's arm).
Mismatched-but-valid schema → rc=1 (L4's cross arm). Both directions measured.

**I1 — CONFIRMED.** `hk.pkl:167` is `["taplo"] = (Builtins.taplo) { batch = true }`
(the surrounding comment at `hk.pkl:163-165` records #154 dropping `taplo_format`).
`git ls-files | grep -i taplo` → **rc=1, zero hits**; `ls -a | grep -i taplo` → zero
hits. No `.taplo.toml`/`taplo.toml` anywhere, so taplo runs on defaults with schema
handling enabled. `hk-common.pkl:42-64` `excludePaths` covers only
`docs/research/{mintlify-cache,trail/findings,runs,kb}/**`, `docs/specs/**` and
`.codex/` — none of the eight target files.

**L9 — ⛔ REFUTED (as worded), and the correction changes the work.**
The row claims "`renovate.json:2` and `home/dot_config/starship.toml:1` already declare
schemas … so a live TOML directive is existing precedent in this repo." Both halves of
the precedent claim fail:

- `renovate.json:2` is `"$schema": "https://docs.renovatebot.com/renovate-schema.json"` —
  **JSON, not TOML**. It is not evidence about taplo at all.
- `home/dot_config/starship.toml:1` is `"$schema" = 'https://starship.rs/config-schema.json'`
  — a **TOML key**, not taplo's `#:schema` comment directive. taplo does not associate a
  schema from a `$schema` key. Also not evidence about taplo.

So **there is no live `#:schema` TOML directive in the linted tree today**. Control-armed:
`git grep -n '#:schema'` returns 4 hits — two inside the excluded
`docs/research/mintlify-cache/**`, one inside the excluded
`docs/research/kb/reports/agents/**`, and one real one at
`home/dot_config/mise/config.toml.tmpl:1`, which is a **`.tmpl`** file (chezmoi source),
not a `.toml`, so the taplo builtin's TOML glob does not pick it up.

The consequence: this change would be the **first** live taplo schema association in
`mise run lint`. The spec's "existing precedent" framing understates the novelty.

**A1 (taplo caches fetched schemas between runs) — ⛔ REFUTED, both arms, and this is
the largest undisclosed cost in the spec.**

After **eight** successful runs that each fetched `https://mise.jdx.dev/schema/mise.json`,
the *same file* was linted again with the network blocked
(`HTTPS_PROXY=http://127.0.0.1:9 HTTP_PROXY=http://127.0.0.1:9`):

```
rc=1
 WARN taplo:…:load_schema: failed to fetch schema
   error=error sending request for url (https://mise.jdx.dev/schema/mise.json):
   error trying to connect: tcp connect error: Connection refused (os error 61)
ERROR taplo:lint_files: invalid file error=failed to load schema …
ERROR operation failed error=some files were not valid
```

Control arm, immediately after, identical command without the proxy vars: **rc=0**. So
the probe discriminates and the failure is the missing network, not the proxy vars
themselves. No schema cache directory exists at `~/Library/Caches/taplo` or
`~/.cache/taplo`; a `find ~ -maxdepth 4 -iname '*taplo*' -type d` returns only **mise's
tool-install** caches (`~/.cache/mise/taplo`, `~/Library/Caches/mise/taplo`,
`~/Library/Caches/codex-kb299-mise-cache/taplo`) — none of them a schema store. taplo
0.10.0 does expose `--cache-path`, but the hk builtin passes no such flag, so the cache
is never enabled.

**Consequence, stated plainly: with six live `#:schema` directives, `mise run lint`
becomes a network-dependent gate that fails CLOSED.** Offline, on a flaky link, or
during a `raw.githubusercontent.com` blip, the lint gate — and therefore
`mise run ship` — goes red for a reason unrelated to the diff. Two of the six URLs are
on `raw.githubusercontent.com`, which rate-limits. This is a decision the operator
should make explicitly; the spec currently books it as a held assumption in the other
direction.

---

## MISSING — premises the spec does not list

### ⛔ M1 (BLOCKING) — three of the six TOML files ALREADY carry the line, malformed. This is not an "ADD".

Byte-exact `head -1 | cat -v`:

```
.config/mise/conf.d/shared.toml => # :schema https://mise.jdx.dev/schema/mise.json
.devcontainer/mise-runtime.toml => # :schema https://mise.jdx.dev/schema/mise.json
.devcontainer/mise-system.toml => # :schema https://mise.jdx.dev/schema/mise.json
home/dot_config/mise/config.toml.tmpl => #:schema https://mise.jdx.dev/schema/mise.json
```

Note the **space** after `#` in the three tracked, linted files — and its absence in the
chezmoi template. `# :schema` is **not** taplo's directive; it is an ordinary comment.
Control-armed directly: a scratch file whose line 1 is `# :schema <mise schema>` and whose
body contains the type error `node = 12345` lints **rc=0**, while the identical file with
`#:schema` lints **rc=1**. The space is load-bearing.

So the work on those three files is *deleting one space*, not inserting a line — and
§2's table, which presents all six as additions, mis-describes the diff for half of them.
Only `mise.toml`, `ruff.toml` and `typos.toml` are genuine additions.

### ⛔ M2 (BLOCKING) — `.devcontainer/devcontainer.json` already has `$schema`, at a DIFFERENT URL, and not as the first key.

`.devcontainer/devcontainer.json:84`:

```
  "$schema": "https://raw.githubusercontent.com/devcontainers/spec/main/schemas/devContainer.schema.json",
```

The spec §2 asks to add `…/devContainer.base.schema.json` "as the FIRST key". Three
errors in one row: the key exists; the URL differs (`devContainer.schema.json` vs
`devContainer.base.schema.json`); and it is at line 84, not first. §4's instruction to
"preserve the leading comment block … the `$schema` key goes inside the object" is
already satisfied. This row must become either "leave alone" or an explicit,
justified URL *change* — and a URL change is a behaviour change for editors, not a
no-op. §2's "leave alone" list must gain this file.

### ⛔ M3 (BLOCKING, cost not disclosed) — editing shared.toml / mise-system.toml BUSTS the base image hash; mise-runtime.toml busts the dev hash.

`python/src/dotfiles_setup/p2996_hash.py` hashes **raw file bytes** (`_file_digest` →
`_sha256_hex(path.read_bytes())`, :327-329):

| file | hash tier | source |
|---|---|---|
| `.config/mise/conf.d/shared.toml` | `shared_config_digest` → **base hash** | `p2996_hash.py:366`, `BaseHashInputs` :95 |
| `.devcontainer/mise-system.toml` | `mise_system_config_digest` → **base hash** | `p2996_hash.py:360` |
| `.devcontainer/mise-runtime.toml` | `runtime_config_digest` → **dev hash** | `p2996_hash.py:503`, `DevHashInputs` :162 |
| `mise.toml`, `ruff.toml`, `typos.toml`, `.claude/settings.json`, `.devcontainer/devcontainer.json` | **none** | absent from all three input dataclasses |

Deleting one space from shared.toml or mise-system.toml therefore changes
`:base-<hash>`, misses the base-prep probe, and triggers a **base rebuild** in CI
(`p2996_hash.py:8-10`: "~30 min cold"). p2996 is decoupled since #160 T11, so the ~2h
compiler is *not* rebuilt — but this is emphatically not the ~10-min warm path, and
the base bust cascades into the dev hash. The spec presents this change as cosmetic;
it is an image rebuild.

**Second-order, same cause:** `IDENTITY_IMAGE_PATHS` (`image.py:289-293`) byte-compares
the in-image copies of **all three** of those files. Smoke tier-1 identity uses the
*merge-base* blob on a branch (`resolve_expected_identity_at_base`, `image.py:312-323`;
`identity_expected_hash` → `base_currency_blob`, :2024-2030), so local
`verify-container-latest` still passes on the branch — but after merge, the local
container's base is stale against main until CI republishes `:dev`, and
`verify-container-latest` is a **hard** gate on base currency
(`container.py:20-25`). Budget a `mise run sync` after landing.

### M4 (non-blocking, settles the architect's parser question) — nothing else that parses these files is position- or count-sensitive.

Readers checked, all comment-inert:

- `lock_refresh.py:114-145` `_merge_shared_tools` splices shared.toml's `[tools]` body
  into mise-system.toml by **regex on `^\[tools\]$`** and "next `^\[`" — text offsets
  derived from the headers, not line indices. A line-1 comment edit cannot move a
  splice point. (This was the highest-risk reader; it is safe.)
- `doc_refs.py:359-362` — `tomllib.loads(config.read_text()).get("tasks", {})` over
  `mise.toml` + `conf.d/*.toml`. Comments are dropped by the TOML parser; it only reads
  task names/aliases, never URLs, so the schema URL is not treated as a doc reference.
- `dependency_ownership.py:82` — `tomllib.loads((repo_root / "mise.toml").read_text())`.
- `lock_integrity.py:248` — `declared_tools(...)` over `mise.toml` + shared.toml, TOML-parsed.
- `image.py` `_tool_requested_version` / `resolve_declared_tools*` — TOML-parsed.
- `workflow_hooks.py:407` `MISE_CONFIGS` — glob list, not content.
- `token_audit.py:90,184` — substring token checks.
- mise itself parses TOML; a comment is a comment.

### M5 (non-blocking, settles the architect's byte/line-count question) — no first-line, byte-count or line-count assertion on any of the eight.

Every `suites.toml` entry naming these files uses `per_path_tokens` (whole-file substring),
e.g. `:159-160` (`mise.toml`), `:240-241`/`:262-263`/`:347-348`/`:1043-1062`
(`mise-system.toml`), `:147-148`/`:170-171`/`:183-184` etc. (`devcontainer.json`),
`:909-910` (`mise.toml` `[tasks.pre-commit]`). Substring checks are position-free.
The repo's only line-count gate is `hk.pkl:158-162`
(`dockerfile_host_user_thin_overlay`), scoped to `.devcontainer/Dockerfile.host-user`
alone. `md_size_budget` is markdown-class only. This reproduces revision 1's M4
independently.

### M6 (non-blocking, settles the architect's ruff question) — `ruff.toml`'s `extend` is unaffected by a leading comment, and this is already demonstrated in-tree.

`ruff.toml` **already begins with a six-line comment block**, and `extend =
"python/pyproject.toml"` is at line 7 and works (the file's own header records the
probe that established the behaviour). ruff parses TOML; a seventh leading comment line
changes nothing. No new risk.

### M7 (non-blocking) — §2's count is wrong.

"ADD the declaration to exactly these **ten**" is followed by two tables listing
**eight** files (6 TOML + 2 JSON). After M1 and M2, the true count of files needing an
edit is **four**: `mise.toml`, `ruff.toml`, `typos.toml`, `.claude/settings.json`
(plus three space-deletions, plus a decision on devcontainer.json's existing URL).

### M8 (non-blocking) — §3's tracked/untracked claim verified.

`.codex/config.toml`, `.codex/hooks.json`, `.claude/settings.local.json` are all
present-but-untracked (`git ls-files --error-unmatch` → N, `-e` → Y). `.mcp.json`,
`doctor.toml`, `.agnix.toml`, `.claude/ultrapowers-preferences.json`, `.gitleaks.toml`
are all tracked and present. §3 is accurate.

### M9 (non-blocking) — revision 1's M1 (`agnix --strict`) is NOT re-cleared here.

The architect states it was cleared by a live run. This lane did not reproduce that run
and takes no position; it is not settleable from disk.

---

## VERDICT

**Correct the spec before dispatch.** Four blockers. Three are the same family — the
spec describes a tree that is not the tree on disk — and the fourth is a cost the spec
books in the wrong direction:

- **M1** — `shared.toml`, `mise-runtime.toml`, `mise-system.toml` already carry
  `# :schema` (with a space, hence inert). The edit is deleting a space, not adding a
  line, and §2 says otherwise.
- **M2** — `.devcontainer/devcontainer.json:84` already declares `$schema`, at a
  *different* URL, not as the first key.
- **M3** — the undisclosed cost: two of the six TOML files are base-image hash inputs
  and one is a dev-hash input, so this "cosmetic" change forces an image rebuild and a
  post-merge `sync`.

- **A1** — REFUTED with both arms: taplo does **not** cache schemas between runs under
  the hk builtin's flags, so `mise run lint` becomes a network-dependent gate that fails
  closed offline, on six URLs, two of them on rate-limited `raw.githubusercontent.com`.

**L9 is also REFUTED** as worded: there is no live `#:schema` precedent in the linted
tree, so this change is the first one, not a continuation of an established pattern.

Everything the spec asserts about taplo's *behaviour* (L1-L5, L8, I1) is confirmed with
both arms. The defects are all in its model of the current file contents.

---

## GitHub repos touched

- [tamasfe/taplo](https://github.com/tamasfe/taplo) — the `taplo lint` binary (0.10.0) whose schema-directive behaviour every probe above measures.
- [jdx/mise](https://github.com/jdx/mise) — `https://mise.jdx.dev/schema/mise.json`, fetched live by the L1/L2/L3 probes.
- [astral-sh/ruff](https://github.com/astral-sh/ruff) — `ruff.schema.json` fetched live for the L4 pass arm.
- [crate-ci/typos](https://github.com/crate-ci/typos) — `config.schema.json` fetched live for the L4 cross-control and L5.
