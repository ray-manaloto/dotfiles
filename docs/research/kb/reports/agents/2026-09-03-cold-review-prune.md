# Cold review: `_prune_unknown_lock_tools` (commit 201c7f6)

Independent (pre-codex) verification notes, gathered by direct inspection and
mutation testing of the working tree at commit 201c7f6d141874c0c5961435a6723c2bdb0753a1.

## Setup verified
- `python/pyproject.toml` pins `requires-python = ">=3.14"`; the multi-except
  `except OSError, tomllib.TOMLDecodeError, TypeError, ValueError:` at
  `python/src/dotfiles_setup/lock_refresh.py:194` is valid PEP 758 syntax on
  3.14 (parses with `ast.parse`, `ruff check` clean, `ty check` clean).
- Real `mise.lock` (7097 lines, 32 `[[tools.X]]` blocks, 1191 `[conda-packages...]`
  blocks) has ALL conda-packages tables strictly BEFORE all tools blocks, and
  nothing after the last tools block. `_TOOL_ARRAY_HEADER_RE` extracted exactly
  32 headers matching the 32 parsed `tools` keys 1:1 (script-verified).
- Only caller is `lock_top_level_config_tools(project_root / "mise.toml")`
  (`main.py:2139`) — this function only ever prunes the ROOT `mise.lock`, never
  `.devcontainer/mise-system.lock`/`mise-runtime.lock`.

## CRLF
Confirmed by direct regex probe: `_TOOL_ARRAY_HEADER_RE`'s `[ \t]*$` anchor
matches ZERO headers against CRLF-terminated text (`$` in MULTILINE mode
matches before `\n`, leaving the `\r` unconsumed). Effect: if `stale` is
non-empty, `unlocated` becomes the entire stale set and the function raises
`ValueError` — a hard failure, not silent corruption. Current `mise.lock` is
LF-only, no `.gitattributes` forces CRLF, so this is latent, not live.

## Block-slicing algorithm
Verified correct by direct execution against a synthetic multi-block file
(4 tools, prune 2 non-adjacent) and against the REAL `mise.lock` (removed
`rumdl`, reparsed the result, confirmed `remaining == configured` and byte
count dropped by exactly the removed block's size, `rumdl` absent). Leading
content (the `# @generated` comment) survives. No comments-between-blocks
case exists in the real file today (only the one file-header comment).

## Post-prune validation: NOT tautological
Mutation test: forcing `stale = set(parsed_tools)` (i.e. treating everything
as stale, simulating a broken staleness computation) causes the post-prune
`remaining != configured` check to fire and raise — confirms the validation
is a real safety net, not dead code, and it correctly rejects a case where
the prune would otherwise silently drop configured-but-not-yet-relocked tools.

## Non-atomic write — real finding
`lock_path.write_text(pruned)` at `python/src/dotfiles_setup/lock_refresh.py:164`
truncates-then-writes; a kill/OOM/disk-full mid-write leaves a truncated,
invalid `mise.lock` on disk. This is consistent with an existing pattern
elsewhere in the same file (`lock_refresh.py:387`, `dest.write_text(candidate)`)
so it isn't a novel regression, but it is the single highest-consequence line
in this diff given the review brief's framing (rewrites a committed artifact
by byte offsets). No `os.replace`/tempfile atomic-write pattern used anywhere
in this module.

## Test capability — mutation-tested
Ran the 3 new tests against a fully neutered `_prune_unknown_lock_tools`
(`return` as the first statement, function body dead):
- `test_lock_top_level_config_tools_prunes_stale_entries` — FAILS (correctly
  detects the neutering). This is the only test that actually exercises
  removal.
- `test_lock_top_level_config_tools_keeps_extras_match` — STILL PASSES with
  the function fully neutered (a no-op function never writes, so
  `lock.read_text() == original` holds trivially).
- `test_lock_top_level_config_tools_does_not_rewrite_exact_lock` — STILL
  PASSES with the function fully neutered (no write ⇒ mtime unchanged
  trivially).

A second mutation (`stale = set(parsed_tools)`, i.e. always-stale) DOES fail
all three plus the pre-existing scoped-argv test, via the post-prune
validation exception — so tests 2 and 3 aren't completely inert, they just
don't independently prove the "prune correctly removes stale entries" claim;
that rests entirely on test 1.

## `_EXTRAS_RE` greediness
`\[.*\]$` with greedy `.*` will strip from the FIRST `[` to the LAST `]` at
end of string, so a hypothetical multi-bracket name like `"aqua:foo[a][b]"`
would have its entire `[a][b]` tail stripped rather than just the outer
group. Grepped `mise.toml` + `shared.toml`: no top-level `[tools]` key
currently has more than one bracket group, so this is not live, only
latent. Also noted: `top_level_config_tools()` (pre-existing, line 81)
already extras-normalizes before `_prune_unknown_lock_tools` is ever called
with `configured_tools`, so the re-normalization at `lock_refresh.py:110` is
redundant on the only real call path (defensive-but-dead code, not a bug).

## Error handling
`except OSError, tomllib.TOMLDecodeError, TypeError, ValueError:` at
`lock_refresh.py:194` covers: missing lock file (FileNotFoundError ⊂
OSError), malformed TOML, the two explicit `TypeError`s, and the three
explicit `ValueError`s raised inside `_prune_unknown_lock_tools`. Nothing
else escapes `_prune_unknown_lock_tools` under normal operation. `re.error`
is not a realistic risk (static patterns).

(Codex pass pending — findings below merge codex's independent read with the
above.)

## Codex (GPT-5.6 Sol, xhigh via `codex exec review`) — independent cold pass

Ref reviewed: commit `201c7f6d141874c0c5961435a6723c2bdb0753a1`, confined to
`python/src/dotfiles_setup/lock_refresh.py`, `tests/test_lock_refresh.py`,
`tests/test_lock_coverage.py`. Full raw output:
`/var/folders/z4/0p475gq56vvczc3y4qlt60f80000gn/T/codex-review-final.XXXXXX.pdtTEhptRk`.

### [P1] Block-boundary logic can delete an unrelated non-`tools` table

Codex's claim: a stale `[[tools.X]]` block followed by a `[conda-packages...]`
(or any other non-`tools` top-level table) before the next `[[tools.Y]]`
header, or before EOF, gets deleted along with the stale block — because the
cursor jump at `lock_refresh.py:145-149` advances straight to the *next
`[[tools.` header*, treating everything in between as owned by the stale
block. The post-prune validation at `lock_refresh.py:152-164` only checks
`tomllib.loads(pruned).get("tools")` equality; it never checks that other
top-level tables (e.g. `conda-packages`) survived, so this data loss is
silently written to disk.

**CONFIRMED by direct reproduction** (not just citation-checked — executed):

```
input:
[[tools.a]]
version = "1"

[[tools."conda:b"]]
version = "2"

[conda-packages.linux-x64."b-pkg-1.0"]
url = "https://example.com/b-pkg.conda"
checksum = "sha256:deadbeef"

[[tools.c]]
version = "3"

configured = {"a", "c"}   # "conda:b" is stale

output (via _prune_unknown_lock_tools):
[[tools.a]]
version = "1"

[[tools.c]]
version = "3"
```

The `[conda-packages.linux-x64."b-pkg-1.0"]` table — which has nothing to do
with the stale tool being removed — is silently deleted, and the function
returns successfully (validation only checks the `tools` set, which is
correct post-prune).

**Currently NOT live against the real root `mise.lock`**: verified all 1191
`[conda-packages...]` entries sit strictly before all 32 `[[tools.X]]`
headers, contiguous, with none after the first tools header (script-checked,
see above). So this defect cannot fire against the file's CURRENT layout.
But nothing in the code or in mise's documented lock format guarantees that
ordering going forward — it is an observed convention, not an enforced
invariant — and the one conda-backed tool in the real file today is
`conda:ffmpeg` (`mise.lock:5166`), so the precondition (a conda-backed tool
becoming stale while conda-packages entries are interleaved with or follow
other tool blocks) is not far-fetched if a future `mise lock` run or manual
edit changes section ordering. Severity: HIGH — this is exactly the
"corrupts an artifact rather than merely failing a test" class the review
brief called out, and it fails **silently successful** (rc=0, file written),
not loud.

### [P2] Non-atomic write (corroborates independent finding above)

Codex flags the same `lock_path.write_text(pruned)` at `lock_refresh.py:164`
as a non-atomic replace: an interruption (kill, disk-full, concurrent
reader) can leave `mise.lock` truncated/empty, and the caller's `except`
clause (`lock_refresh.py:193-197`) only logs and returns 1 — it does not
restore the file. Matches this reviewer's independent finding above.

### Test-capability finding (corroborates independent finding above)

Codex confirms, from static reading (not execution), that under a no-op
prune mutation only `test_lock_top_level_config_tools_prunes_stale_entries`
(`tests/test_lock_refresh.py:96-113`) would fail; the argv-building test
(`tests/test_lock_refresh.py:74-93`) and both no-change tests
(`tests/test_lock_refresh.py:116-153`) would still pass. This matches the
independent mutation-test result above exactly.

## Consolidated findings

| Severity | Claim | Citation |
|---|---|---|
| HIGH | `_prune_unknown_lock_tools`'s block-boundary logic treats everything between one `[[tools.X]]` header and the next as owned by the first block, so a stale block immediately followed by a non-`tools` top-level table (e.g. `[conda-packages...]`) has that unrelated table silently deleted too; post-prune validation only checks the `tools` key so this passes and is written to disk. Not triggerable against today's real `mise.lock` (conda-packages is fully contiguous before all tools blocks) but not prevented by any check either — an ordering assumption, not an enforced invariant. Reproduced directly. | `python/src/dotfiles_setup/lock_refresh.py:140-164` (cursor-jump logic `:145-149`, validation gap `:152-164`) |
| MEDIUM | `lock_path.write_text(pruned)` is a non-atomic truncate-then-write; a kill/OOM/disk-full mid-write can leave `mise.lock` truncated on disk, and the caller's broad except only logs + returns 1 without restoring the file. Same pattern pre-exists elsewhere in this file (`lock_refresh.py:387`), so not a novel regression, but it is the highest-consequence line in this diff. | `python/src/dotfiles_setup/lock_refresh.py:164`, caller at `:193-197` |
| MEDIUM | 2 of the 3 new tests (`test_lock_top_level_config_tools_keeps_extras_match`, `test_lock_top_level_config_tools_does_not_rewrite_exact_lock`) still pass if `_prune_unknown_lock_tools` is replaced with a no-op that never prunes or writes — mutation-tested directly. Only `test_lock_top_level_config_tools_prunes_stale_entries` actually exercises removal; coverage of "the feature deletes stale entries" rests on a single test. | `tests/test_lock_refresh.py:96-113` (the one test that fails), `:116-134` and `:136-153` (the two that don't) |
| LOW | `_TOOL_ARRAY_HEADER_RE`'s `[ \t]*$` anchor matches zero headers against CRLF-terminated text, so any needed prune on a CRLF lockfile raises `ValueError` (fails safe/loud, not silently) rather than pruning. Not live today (`mise.lock` is LF-only, no `.gitattributes` forcing CRLF). Reproduced directly. | `python/src/dotfiles_setup/lock_refresh.py:58` (`_TOOL_ARRAY_HEADER_RE` definition) |
| LOW / non-issue | Post-prune validation (`lock_refresh.py:152-163`, `tools`-set equality) is NOT tautological — mutation-tested by forcing `stale = set(parsed_tools)` (always-stale), which correctly triggers the validation's `ValueError`. It is a real safety net for the `tools` key specifically, just blind to other top-level tables (see HIGH finding above). | `python/src/dotfiles_setup/lock_refresh.py:152-163` |
| INFO / non-issue | `except OSError, tomllib.TOMLDecodeError, TypeError, ValueError:` (`lock_refresh.py:194`) is valid PEP 758 unparenthesized multi-exception syntax on the pinned `>=3.14` Python — parses, `ruff check` clean, `ty check` clean. Not a bug. | `python/src/dotfiles_setup/lock_refresh.py:194`; `python/pyproject.toml:5` |
| INFO / non-issue | `_EXTRAS_RE = re.compile(r"\[.*\]$")`'s greedy `.*` would over-strip a hypothetical multi-bracket key (e.g. `"aqua:foo[a][b]"` → strips the whole `[a][b]` tail), but no current top-level `[tools]` key in `mise.toml`/`shared.toml` has more than one bracket group — latent, not live. Also: the only real call path already extras-normalizes `configured_tools` before it reaches `_prune_unknown_lock_tools` (via `top_level_config_tools`, line 81), so the re-normalization at `lock_refresh.py:110` is redundant-but-harmless on that path. | `python/src/dotfiles_setup/lock_refresh.py:59`, `:81`, `:110` |

## GitHub repos touched

_None._ (No external repos consulted — pure local code/test inspection and execution.)
