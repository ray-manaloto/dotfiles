# res-mise-upstream — 2026-09-13 (READ-ONLY)

Due-diligence on the `mise run update:all` lockfile failure (Q-A) and this
project's jdx/mise filing convention (Q-B). No source edited, no git/GitHub
mutation. All source reads are of `jdx/mise` at its current default branch via
`gh api repos/jdx/mise/contents/...` (HEAD at time of research: releases up to
`v2026.9.7`, matching the locally pinned mise `2026.9.7`).

## Q-A: is the `update:all` failure OURS or mise's?

### The exact mechanism, read from mise's own Rust source

`src/backend/pipx/lock.rs`, function `resolve_uv_lock` (the routine that
builds the temporary `pyproject.toml` + runs `uv lock` to produce a tool's
dependency-graph lockfile):

```rust
// lock.rs:186-192
let requires_python = if requires_python.trim().is_empty() {
    ">=3.8".to_string()
} else {
    format!(">=3.8,{requires_python}")
};
```

— an unconditional `>=3.8` lower bound is prepended to whatever
`requires_python` metadata mise fetched from PyPI/the simple index for the
package. It is **hardcoded**, not read from any settings/config surface.

```rust
// lock.rs:213
.args(["lock", "--no-build", "--no-config", "--no-python-downloads"])
```

— `--no-build` is likewise **hardcoded** on the `uv lock` invocation (and
again at `lock.rs:385` on the later `uv sync --frozen` install step). Nothing
in `mise.toml`/`config.toml` sets either of these; a pipx/pypi tool cannot
avoid them while dependency-graph locking is in effect for it.

**Both are DOCUMENTED, not accidental.** `docs/dev-tools/backends/pypi.md`
(fetched live):

> "The graph covers the package's supported Python range, **starting at
> Python 3.8**, and retains all published wheel targets for portability."
> (pypi.md:113)
>
> "**Wheels only:** every dependency needs a published wheel for the target
> Python version and platform. **Locked installs do not build source
> distributions.**" (pypi.md:100-101)

So this is intended design for uv-graph-locked pypi/pipx tools: mise asks uv
to resolve a **universal** lock spanning the package's whole declared Python
support window (floored at 3.8 when metadata doesn't already exclude it),
wheels-only, regardless of which interpreter mise will actually run the tool
under (`docs/dev-tools/backends/pypi.md:107-109`: "lock generation needs an
interpreter discoverable by uv, **though it need not match the tool's
configured Python version**"). When a transitive dependency (`jieba` for
`graphifyy`, `aiohttp` for `skypilot`) has no wheel published for a Python
version inside that floored range, and `--no-build` forbids falling back to
an sdist, `uv lock` fails — exactly the uv error captured in the brief
("resolution splits on `python_full_version == '3.8.*'`... no wheels...
`--no-build` is in force").

**Verdict on origin: THEIRS (mise's own hardcoded/documented behavior), not a
dotfiles config error.** Nothing in `~/.config/mise/config.toml` or this
repo's `mise.toml` sets `>=3.8` or `--no-build`; both are unconditional in
`resolve_uv_lock`/`install_uv_lock`. The trigger for the failure to surface at
all is `lockfile = true` (set at `~/.config/mise/config.toml:44` and
`mise.toml:137`), which turns on `Settings::lockfile_creation_enabled()` and
routes `mise upgrade`'s tool installs through `prepare_install_version` ->
`uv_lock_allowed` -> `resolve_uv_lock` (`src/backend/pipx.rs:315-343`). That
setting is a deliberate, common, documented choice (pin reproducible
versions) — not misuse.

### Q-A.1 — is there a supported per-tool opt-out?

**`lockfile = false` per tool (as proposed at `~/.config/mise/config.toml:195`)
is NOT REAL.** Read from source, both places a per-tool key could live:

- `PipxOptions` (`src/backend/pipx.rs:52-101`) recognizes exactly these
  install-time option keys, enumerated in `install_time_option_keys()`
  (`pipx.rs:568-576`): `extras`, `package_name`, `pipx_args`, `uvx_args`,
  `uvx`, plus `registry_url` (read separately). **No `lockfile` key exists
  here.**
- `[tool_config]` (config-root-scoped policy, `src/config/config_file/mod.rs:1178`):

  ```rust
  #[derive(Clone, Debug, Default, Deserialize)]
  #[serde(default, deny_unknown_fields)]
  pub(crate) struct ToolConfig {
      pub locked: bool,
  }
  ```

  `deny_unknown_fields` and the **only** field is `locked: bool`. A `lockfile`
  key here would be rejected outright (a real, structural absence — not "we
  didn't find a way to use it").

This corroborates the prior probe in the brief: `mise ls` accepting a bogus
tool-option key (`qzxwvnot_a_key`) at rc=0 proves `mise ls` doesn't validate
tool-option keys — it says nothing about whether `lockfile` is real, and
tracing the actual `Deserialize` structs settles that it is not, at either
scope.

**`locked_scopes` is the wrong knob for this.** It only bounds *invocation-wide
locked mode* — whether `--locked`/`MISE_LOCKED=1`/`locked = true` (in
`[tool_config]`) makes `mise install` **fail** when a tool lacks a recorded
lockfile URL (`settings.toml:1678-1707`, `e2e/lockfile/test_lockfile_locked_scopes`).
It does not gate whether `mise upgrade`/`mise lock` **attempts to generate** a
uv dependency graph for a tool in the first place — that gate is
`uv_lock_allowed`/`lockfile_creation_enabled`, upstream of `locked_scopes`
entirely. Excluding `"global"` from `locked_scopes` would not stop
`update:all` from trying (and failing) to regenerate the `graphifyy`/`skypilot`
locks; it would only change whether a *missing* lockfile blocks install.

**A real, already-existing per-tool opt-out DOES exist: `uvx = false`.**
Traced end to end:

```rust
// pipx.rs:12-17 (uv_lock_allowed)
pub(crate) fn uv_lock_allowed(&self, tv: &ToolVersion) -> bool {
    Settings::get().pypi.uvx != Some(false)
        && !PipxOptions::new(&tv.request.options()).uvx_disabled()
        && matches!(self.tool_name().parse::<PipxRequest>(), Ok(PipxRequest::Pypi(_)))
}
```

`uvx_disabled()` reads the tool option `uvx == "false"` (a *documented*,
recognized `install_time_option_keys()` entry). When `uvx = false` is set on
a tool, `uv_lock_allowed` returns `false`, so `prepare_install_version` never
calls `resolve_uv_lock` for that tool at all (`pipx.rs:317` gates on
`self.uv_lock_allowed(&tv)`) — it falls back to the legacy pipx installer with
version-only locking (no uv dependency graph, no `--no-build`, no synthetic
`>=3.8` floor). This is also documented, under "Using pipx"
(`docs/dev-tools/backends/pypi.md:161-176`):

```toml
[tools]
"pypi:ansible" = { version = "latest", uvx = false, pipx_args = "--include-deps" }
```

**So a fix exists today, without touching upstream or global settings**: set
`uvx = false` on `"pypi:graphifyy"` and `"pypi:skypilot"` (and — per the
in-repo comment at `~/.config/mise/config.toml:190-197` — the same class of
failure previously hit `azure-cli`, resolved there by removing `uvx_args`
rather than disabling uvx; `uvx = false` is the more general fix for a package
whose transitive deps genuinely lack old-Python wheels). Trade-off, stated
plainly: losing the uv dependency graph for that tool means version-only
locking (no hash-pinned transitive deps for it), and `pipx_args`/`uvx_args`
become usable again (since `validate_lock_options` only forbids them
*with* a uv dependency graph — `lock.rs:20-30`).

### Verdict

**Mixed, resolves in mise's favor for "is it a defect", but NOT in the
operator's favor for "must file upstream to unblock ourselves":**

1. The failure mechanism (`>=3.8` floor + `--no-build`, forcing a
   whole-Python-range wheel-only resolution) is mise's own hardcoded,
   *documented* design — not a dotfiles misconfiguration. THEIRS by origin.
2. The specific proposed workaround in this repo's own comments
   (`lockfile = false` per tool) does not exist as a config surface at any
   scope — that comment is aspirational/incorrect and should be corrected.
3. A real, already-shipped, documented per-tool escape hatch exists right now
   (`uvx = false`) that fully avoids the failure without any upstream change.
   **This makes local remediation available immediately**, independent of
   whatever comes back from filing upstream.
4. Filing upstream is still reasonable — but as a **feature request** (e.g.
   "let uv-graph lock generation target the tool's configured/active Python
   version instead of the documented 3.8 floor", or "make `--no-build`
   opt-out per tool without fully disabling uv") rather than a "mise is
   broken" bug report, since the current behavior matches its own docs.

## Q-B: how does this project file with jdx repos?

### jdx/mise has GitHub Issues DISABLED — confirmed live, twice independently

```
$ gh repo view jdx/mise --json hasIssuesEnabled,hasDiscussionsEnabled
{"hasIssuesEnabled":false,"hasDiscussionsEnabled":true}

$ gh api repos/jdx/mise --jq '{has_issues, has_discussions, archived}'
{"has_issues":false,"has_discussions":true,"archived":false}
```

Two independent API surfaces (GraphQL via `gh repo view --json`, REST via
`gh api`) agree. `gh issue list -R jdx/mise ...` itself fails with
`"the 'jdx/mise' repository has disabled issues"`.

**The operator's stated belief — "i think it is ok to post to jdx github
issues" — is factually wrong for this repo**, and this project already knew
it: `docs/receipts/440.md:246-247` (an earlier session) records the identical
finding verbatim:

> "`jdx/mise` has issues disabled, so the `jdx/mise#7700` reference carried in
> `.claude/rules/tool-currency-and-native-first.md` cannot be a repo issue and
> needs re-checking."

`jdx/mise#7700` (cited in `.claude/skills/lock-image/SKILL.md:52` and
`.claude/rules/tool-currency-and-native-first.md`) is confirmed live to be a
**Discussion** ("Add a Conda lockfile for reproducibility", category "Ideas",
state open), not an issue — `gh api repos/jdx/mise/issues/7700` -> 404,
`gh api repos/jdx/mise/discussions/7700` -> 200 with discussion payload.

**House convention, established by prior sessions**: file with jdx/mise via
**Discussions**, category "Troubleshooting and bug reports" for a bug-shaped
report (confirmed as an existing category from a real hit, discussion #12414)
or "Ideas" for a feature request (confirmed from #7700). `findings.md:4918`
records the operator's own prior-session ruling on this exact question: *"a
discussion exists; issues judged acceptable"* — that phrasing is now shown to
be based on an unverified premise; the correct, verified statement is
**"a discussion exists; issues are NOT accepted (disabled repo-wide) —
discussions are the only route."**

### Duplicate check — none found (both search arms control-armed)

Used GitHub's GraphQL discussion search (`search(type: DISCUSSION, ...)`
scoped `repo:jdx/mise`), which is authoritative since issues don't exist here.

| Query | Hits |
|---|---|
| `no-build pypi lock` | 0 |
| `uv lock no-build` | 16 (none on-topic; unrelated uv/venv issues) |
| `requires-python synthetic` | 0 |
| `pypi lockfile resolution fails` | 3 (none on-topic) |
| `graphifyy` | 1 (unrelated: "Mise cannot install npm packages") |
| `skypilot lockfile` | 0 |
| `jieba lock` | 0 |
| `python_full_version 3.8` | 0 |
| `synthetic python floor` | 0 |

Closest candidate, checked directly: discussion **#12414** ("[BUG] pipx:
Fails to install new versions") — read in full via GraphQL; it's about a
`mise WARN missing: pipx:zensical@...` warning after a Renovate version bump,
unrelated to uv dependency-graph resolution or `--no-build`. Not a duplicate.

**Control arm for the search itself** (per `probes-need-a-control-arm.md`,
freshly-invented strings, never previously written into any report):
`repo:jdx/mise zzqvbnotarealterm8271` -> `discussionCount: 0`;
`repo:jdx/mise pipx` -> `discussionCount: 604`. The search discriminates:
zero on nonsense, hundreds on a known-present term. The zero counts above are
therefore a genuine absence, not a broken probe.

### Ready-to-file discussion body (IF the operator decides to file)

Given the verdict above (documented behavior, but no configurable scope for
the resolution range, and no way to keep the uv dependency graph while
opting out of the 3.8 floor short of dropping to version-only locking via
`uvx = false`), the honest framing is a **feature request**, category
"Ideas":

> **Title:** pypi/pipx backend: let uv-graph lock generation target the
> configured Python version instead of the documented 3.8 floor
>
> **Body:**
>
> `docs/dev-tools/backends/pypi.md` documents that dependency-graph lock
> generation for `pypi:`/`pipx:` tools resolves "the package's supported
> Python range, starting at Python 3.8" with `uv lock --no-build`
> (`src/backend/pipx/lock.rs:186-213`). This is a universal, wheels-only
> resolution across the whole declared range, independent of the interpreter
> mise will actually install the tool under (also documented: "lock
> generation ... need not match the tool's configured Python version").
>
> For a tool whose transitive dependencies dropped old-Python wheels (no
> sdist fallback allowed under `--no-build`), this makes lock generation fail
> even though the tool only needs to run under a single, modern, already-
> configured interpreter (`[tools] python = "3.14"`). Two concrete cases:
> `pypi:graphifyy[all]` (transitive `jieba`) and `pypi:skypilot[aws]`
> (transitive `aiohttp`) both fail `mise upgrade`/`mise lock` today with uv's
> own hint "Consider using a more restrictive `requires-python` value" — a
> value mise itself is synthesizing, not one the user set.
>
> Today's only escape hatch is `uvx = false`, which drops the tool to legacy
> pipx version-only locking entirely (losing hash-pinned transitive deps).
> Requested: a way to scope uv-graph lock generation to the tool's configured
> `[tools] python` version (or an explicit `requires-python` override option,
> analogous to `extras`/`package_name` in `install_time_option_keys()`)
> instead of the hardcoded `>=3.8` floor, so a tool pinned to a current
> interpreter doesn't need wheels for versions it will never run under.
>
> mise 2026.9.7, uv 0.12.13, macOS arm64.

**Recommendation:** do NOT file yet. The `uvx = false` fix is available now
and untested by this lane (read-only mandate) — the operator should try it
first; if it resolves both tools cleanly, the discussion becomes a pure
feature request with no urgency, and can be filed at leisure (or skipped).

## GitHub repos touched

- [jdx/mise](https://github.com/jdx/mise) — `src/backend/pipx.rs`,
  `src/backend/pipx/lock.rs`, `src/config/config_file/mod.rs`,
  `src/config/settings.rs`, `settings.toml`, `docs/dev-tools/backends/pypi.md`,
  `e2e/lockfile/test_lockfile_tool_config_locked`, discussions #7700, #12414,
  and a `search(type: DISCUSSION)` sweep for duplicates. Subject of both Q-A
  and Q-B.
