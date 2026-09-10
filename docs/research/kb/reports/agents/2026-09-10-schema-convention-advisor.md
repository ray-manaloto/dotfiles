# Advisory: `#:schema` convention for the four mise config files

**Task type:** read-only research/audit (not a codex-reasoning decision — this
was pure fact-finding: grep, read, and one empirical taplo probe. No `codex
exec` call was made; nothing here required xhigh reasoning, only verified
evidence). Per `codex-advisor`'s own charter, a "fully-specified... fact
lookup" is the wrong job for a codex-reasoning consult, and that is what this
was — so I did the research directly rather than shelling out.

**Repo root:** `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles`

---

## 1. Is `#:schema <relative-path-to-vendored-file>` the ratified house style?

**Yes — established, and there is a written architectural rationale, not just
convention-by-example.**

- `python/src/dotfiles_setup/schema_vendor.py:4-11` (module docstring):
  > "`mise.toml`, `ruff.toml` and `typos.toml` each carry a first-line
  > `#:schema ./schemas/<tool>.json` directive (taplo, wired via hk's `taplo`
  > builtin, `hk.pkl:167`). The referenced files are vendored under `schemas/`
  > rather than pointed at a remote URL, because taplo does NOT cache schemas
  > between runs — measured: a second `taplo lint` with the network blocked
  > still returns rc=1 'failed to fetch schema'. A remote `#:schema` would make
  > `mise run lint` a per-run network dependency and a red gate whenever the
  > schema host is unreachable."
- `python/verification/suites.toml:2482` (suite `config.schema-vendor-drift`
  description) repeats the same rationale verbatim.
- Confirmed present today: `mise.toml:1` → `#:schema ./schemas/mise.json`,
  `typos.toml:1` → `#:schema ./schemas/typos.json`,
  `ruff.toml:1` → `#:schema ./schemas/ruff.json`.
- The design was arrived at via an explicit refutation: an earlier research
  pass (`docs/research/kb/reports/agents/2026-09-02-taplo-schema-network.md`)
  initially recommended relying on taplo's on-disk cache (Option A), citing
  taplo's `cache.rs` source. That was **measured wrong** on the installed
  taplo 0.10.0 (see the "ARCHITECT CORRECTION" block at the top of that
  report): a second run with network blocked still returned rc=1
  "failed to fetch schema" — no cache directory was ever created. Vendoring
  (Option C) is the option the correction confirms actually removes the
  network dependency, control-armed both ways (vendored+correct → rc=0;
  vendored+wrong schema → 8 real errors, proving validation runs; missing
  vendored path → rc=1, fails loudly).

**Conclusion: `#:schema ./schemas/<tool>.json` pointing at the sha256-verified
vendored copy under `schemas/` is the ratified house style, not an
accident of three files happening to agree.** The `# :schema` (space) form on
the other three mise files is not a competing convention — it is inert
(taplo's directive parser requires no space after `#`, confirmed by the fact
that `schema_vendor.py`'s docstring and the suite below only ever name the
three files that use the no-space form as "carrying" the directive).

## 2. For a file NOT at the repo root, is the path file-relative or root-relative?

**Empirically verified just now (not merely cited) — file-relative, not
CWD-relative and not repo-root-relative.**

I ran taplo 0.10.0 (`/Users/rmanaloto/.local/share/mise/installs/taplo/0.10.0/taplo`,
same binary this repo's `hk.pkl:167` `Builtins.taplo` step resolves via mise)
against three fixtures in a scratch dir, copying the real
`schemas/mise.json`:

| Fixture | Directive | CWD when run | Result |
|---|---|---|---|
| `root.toml` | `#:schema ./schemas/mise.json` | repo-fixture root | rc=0 |
| `sub/relative-to-file.toml` | `#:schema ./schemas/mise.json` | fixture root (not `sub/`) | **rc=1** — taplo's own error names the resolved path: `schema_url=file://…/sub/schemas/mise.json` (i.e. resolved relative to the FILE, not CWD, and that path doesn't exist) |
| `sub/relative-to-cwd.toml` | `#:schema ../schemas/mise.json` | fixture root | rc=0 |
| `sub/relative-to-file.toml` (same file) | `#:schema ./schemas/mise.json` | **cd'd into `sub/`** | still rc=1, same resolved path `sub/schemas/mise.json` — proves it isn't CWD-relative either, even when CWD is made to match |

A second probe confirmed the pattern holds at 3 levels of nesting
(`a/b/c/deep.toml` with `#:schema ../../../schemas/mise.json"` → rc=0).

**So each of the three not-yet-fixed mise config files needs a directive
whose `../` count matches its own depth below the repo root, all pointing at
the same `schemas/mise.json`:**

| File | Depth | Correct directive |
|---|---|---|
| `mise.toml` (repo root) | 0 | `#:schema ./schemas/mise.json` (unchanged, already correct) |
| `.devcontainer/mise-system.toml` | 1 | `#:schema ../schemas/mise.json` |
| `.devcontainer/mise-runtime.toml` | 1 | `#:schema ../schemas/mise.json` |
| `.config/mise/conf.d/shared.toml` | 3 | `#:schema ../../../schemas/mise.json` |

This is the one item where the pre-existing repo research
(`2026-09-02-taplo-schema-network.md`, Q4) explicitly flagged itself
**"UNVERIFIED in one direction — I did not test this locally against an
actual taplo invocation"**. That gap is now closed by direct measurement
above, not by re-citing the same unverified claim.

## 3. Does anything currently gate the `#:schema` directive?

**Yes, and it is narrowly scoped to exactly three files — the other three
mise config files are outside its coverage today.**

`python/verification/suites.toml:2500-2513`, suite
`config.schema-vendor-directives-bound`:

```
paths = ["mise.toml", "ruff.toml", "typos.toml"]
per_path_lines = {
  "mise.toml" = ["#:schema ./schemas/mise.json"],
  "ruff.toml" = ["#:schema ./schemas/ruff.json"],
  "typos.toml" = ["#:schema ./schemas/typos.json"],
}
```

Its own description explains *why* it exists as a second, independent gate:
the sibling suite `config.schema-vendor-drift` (`suites.toml:2481-2499`) lists
those same three files in its `paths` field, but its `schema_drift` handler
(`verify.py`'s `_handle_schema_drift`) **never reads that field** — only
`entry["name"]` — so that listing is "purely decorative" for directive
presence. `require_lines`/`per_path_lines` is what actually binds the literal
directive text; deleting a directive from one of those three files fails this
suite even though the drift suite can't see it.

**Neither suite mentions `.config/mise/conf.d/shared.toml`,
`.devcontainer/mise-system.toml`, or `.devcontainer/mise-runtime.toml`.** If
those three files' directives are fixed (space removed, path corrected) but
this suite's `paths`/`per_path_lines` are not extended, the fix is
**unenforced** — a future edit could silently re-break or delete any of the
three new directives with nothing red. Extending
`config.schema-vendor-directives-bound` (and ideally
`config.schema-vendor-drift`'s `paths` list, for consistency, even though
that field is decorative today) in the same change that fixes the three
directives is the way to avoid re-creating the exact gap this suite's own
description was written to close.

Separately, `hk.pkl:167`'s `Builtins.taplo { batch = true }` step has no glob
override, so it lints (and therefore schema-validates) every `*.toml` in the
repo on every `mise run lint` — confirmed no `.taplo.toml`/`taplo.toml`
exists anywhere in the repo (`find . -iname "taplo*"` → 0 hits) so there is no
separate association config to also update; the directive lives inline in
each file, as it does today for the three already-correct files.

**Control arm for the "nothing gates it" claim on the three untouched
files:** grepped `suites.toml` for each of `shared.toml`, `mise-system.toml`,
`mise-runtime.toml` — 0 matches in a schema-related context (they appear only
in unrelated suites about mise tool-version pins, e.g. the
`config.schema-vendor-drift` paths list at line 2495 citing
`.config/mise/conf.d/shared.toml` only as the **typos** version-pin source,
not as a directive target). Control-arm-positive: the same grep shape finds
`mise.toml`/`ruff.toml`/`typos.toml` bound at line 2503. So the 0-result is a
real absence, not a broken grep.

## 4. Any ratified decision/issue about hot-linking `mise.jdx.dev` vs vendored?

**No open or closed GitHub issue specifically litigates this.** Searched
`gh issue list -R ray-manaloto/dotfiles --state all --limit 100/200 --search
"schema"`, `"ITEM 11"`, and `"mise.jdx.dev"` (not `gh search`, per the
constraint). Hits were all tangential (issue #943 "Logging migration lane 7:
graphify, schema-vendor…", #165 "hk: adopt mdschema builtin", #863 KB
build-receipt schema, #953/#184 unrelated "Tool currency report" issues whose
titles happen to contain no schema reference — false-positive from the
search index, discounted). None discusses the vendored-vs-remote decision for
mise config files. Issue #160 (the devcontainer/config-retiering epic that
"ITEM 11" belongs to) mentions "SCHEMA 4→5" and `mise system status --json`
schema — both unrelated (build-hash versioning and a different runtime JSON
shape, not the TOML `#:schema` directive).

**The decision IS ratified, but in code + docs, not in a tracked issue**: the
`schema_vendor.py` docstring (item 1 above) and the
`config.schema-vendor-drift`/`-directives-bound` suite descriptions are the
authoritative record — they are more load-bearing than an issue would be,
since `mise run verify` and the drift-check task actively enforce them. There
is no contradicting ratified decision to be aware of; extending the same
convention to the other three files is directly in line with the existing
one, not a new precedent.

Control arm for the search tool itself: the same `--search` invocation
against `"mise.jdx.dev"` returned 4 real (if unrelated) hits, proving the
search index is live and a 0-result for the exact hot-link-vs-vendor question
is a genuine absence, not a broken query.

## 5. Does `schemas/sources.toml` pin mise schema v2026.9.1 while the host runs a newer version — and does it matter?

**Confirmed, and it does not matter for the directive-fixing change.**

- `schemas/sources.toml:19` pins `version = "2026.9.1"` for the mise schema.
- The host's installed mise reports `2026.9.4 macos-arm64 (2026-09-09)`
  (`mise --version`).
- But `check_drift` does **not** compare against the host's installed mise —
  per `schema_vendor.py:17-24`, it reads the CURRENT pin from
  `.github/actions/setup-mise/action.yml` via regex. That file pins
  `version: "2026.9.1"` at both its call sites
  (`.github/actions/setup-mise/action.yml:39` and `:44`).
- Ran the actual check: `uv run --project python dotfiles-setup
  schema-vendor check` → `schema-vendor: all vendored schemas match their
  current pins` (rc=0, verified just now). So there is **no drift** by this
  repo's own definition — my host's ahead-of-CI local mise install is
  irrelevant to the gate, and the vendored `schemas/mise.json` is the schema
  for the version CI actually pins.
- **This does not block or complicate the directive-fixing change.** The
  `sha256` in `sources.toml:22` matches the vendored file's actual bytes
  (implied by the drift check passing); adding three more `#:schema ../…`
  lines pointing at the same already-current, already-verified
  `schemas/mise.json` needs no schema refresh first.

---

## Recommendation (for the caller applying this)

1. Fix the three inert directives from `# :schema …` (space, dead) to the
   no-space form, each pointing at the depth-correct relative path measured
   in §2 above — never the `https://mise.jdx.dev/schema/mise.json` remote URL
   the inert lines currently reference, per the ratified network-avoidance
   rationale in §1.
2. In the same change, extend `config.schema-vendor-directives-bound`'s
   `paths`/`per_path_lines` in `python/verification/suites.toml` to cover the
   three newly-fixed files, so the fix is gate-enforced rather than
   silently reversible (§3). Consider the same for
   `config.schema-vendor-drift`'s `paths` list for consistency, though that
   field is currently decorative.
3. No schema refresh, version bump, or `sources.toml` edit is needed (§5).

## What I could not verify

- Whether VS Code's "Even Better TOML" extension (the other stated consumer
  in some `#:schema` prior art, not cited by name in this repo's own
  rationale) resolves the directive identically to taplo CLI 0.10.0 — out of
  scope here since the repo's own gate is taplo via hk, not an editor
  extension, and nothing in the repo asserts editor-extension behavior.
- Whether a newer taplo release changes the file-relative resolution
  measured in §2; measured only against the exact binary
  (`/Users/rmanaloto/.local/share/mise/installs/taplo/0.10.0/taplo`,
  `taplo 0.10.0`) that `hk.pkl:167`'s `Builtins.taplo` step resolves via mise
  in this repo today.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — this
  repo; read `schema_vendor.py`, `suites.toml`, `sources.toml`,
  `setup-mise/action.yml`, prior research reports, and the issue tracker
  (`gh issue list --search`).
- _No third-party repo source was fetched for this report_ — the file-relative
  resolution question (§2) was settled by running the pinned `taplo` binary
  directly rather than reading `tamasfe/taplo` source, which is a stronger
  form of evidence than the citation-only claim in the prior research report.
