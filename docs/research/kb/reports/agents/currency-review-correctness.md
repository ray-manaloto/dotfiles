# Correctness review — `kb_setup.currency` (agent `rev-correctness`)

> **Provenance:** delivered via SendMessage on 2026-07-24, NOT written to disk by the agent.
> Persisted here verbatim at receipt-time per `.claude/rules/agent-report-persistence.md`.
> Reviewed `feat/tool-currency-engine` while the working tree was being edited; it
> re-snapshotted and re-verified. **All findings were re-verified against HEAD by the caller;
> 1A/1C/#3 and the `installs` index bug were fixed in commit `622acbe`, 1B and #4/#5 earlier.**

---

**Note: the working tree was being edited live while I reviewed.** Someone already fixed
(uncommitted, on top of 5f47970): `issues.save_current` baseline erasure, `graph._stamp_build`'s
pin fallback, `cli._currency` flag/mode parsing, and `RunRecord.has_content` for errored
observations. I re-snapshotted and reviewed the **current** tree; `decide.py`, `sync.py`,
`upstream.py`, `run.py` are unchanged from the commit. All 5 findings below were **proved by
executing the real modules**, and `uv run pytest tests/` is fully green with all 5 present.

## Critical

### 1A. `decide()` returns `auto_apply=True` when step 4 read nothing at all — confidence 95

`issues.py:48` + `decide.py:150-159`

`Observation.differs_from` returns `False` whenever `self.error` is set, so an errored
observation can never enter `moved`. `_gate_issues` looks only at `moved`. Result: an issue
that could not be fetched is indistinguishable from an issue that provably did not move — and
gate 5 is then reported as **passed**.

Reachable independently of gate 2: gate 2 needs `gh api repos/…/releases/tags/X` to work, the
watch items need `gh api repos/…/issues/N`. Any per-item failure — a transferred/deleted issue
(404), a repo rename (301), a transient 502, or a secondary rate limit that trips after the
release call — hits one and not the other. `currency.toml` declares no `repo` on the watch
items, so all four (#2101, #2086, #1653, #1824) resolve through `spec.github`; one transfer
404s all future reads of that item silently and forever.

Proved:

```
moved computed from ERRORED observations: ()
auto_apply: True
gates_passed: ('patch-level bump', 'PyPI latest has a matching GitHub tag',
               'no breaking/removal/deprecation marker', 'extras unchanged',
               'no tracked issue moved', 'step 1 currently green')
summary: graphify 0.9.25 → 0.9.26: auto-applying (6/6 gates)
```

This is the exact inversion of the module contract at `decide.py:8-11` ("anything this module
cannot read … is ambiguity, never consent"). `differs_from`'s "an unreadable run never counts"
is right for *movement*, but the errored state has to reach `decide()` on a separate channel.
Fix: pass `observations` into `decide()` and emit an Ambiguity when
`any(o.error for o in observations)`, or have `_gate_issues` take `(moved, errored)`.

### 1B. A GitHub release with a null body passes gate 3 with the literal string `"None"` — confidence 90

`upstream.py:162`

```python
return str(payload.get("tag_name", candidate)), str(payload.get("body", "")), ""
```

GitHub returns `"body": null` for a release published with no description. `.get("body", "")`
finds the key, returns `None`, and `str(None)` → `'None'`. Proved:

```
tag = 'v0.9.26'  body = 'None'
markers scanned in: 'None' -> ()
auto_apply: True
```

Two consequences: (a) gate 3 "no breaking marker" passes because there is nothing to scan — an
unattended bump on a release nobody wrote notes for, which `_gate_tag`'s own rationale
("Without notes there is nothing to review") says must be blocked; (b) `render_detail` prints
the word `None` under "### Release notes" in a committed report, which reads as content rather
than absence. Use `payload.get("body") or ""`, and make gate 2 (or a new gate) require a
non-empty body.

### 1C. `release_for_tag` fabricates a tag it never confirmed — confidence 88

Same line. `payload.get("tag_name", candidate)` **defaults to the tag we asked for**. Whenever
`_gh_api` returns `({}, "")` — it does that for any exit-0 response whose JSON is not an object
(`null`, empty stdout) — `release_for_tag` fabricates a tag that was never confirmed to exist:

```
release_for_tag -> ('0.9.26', '', '')     # tag invented, no error raised
```

`github_tag` is then truthy, gate 2 passes, and notes are empty so gate 3 passes too. Default
to `""`, not `candidate`.

## Important

### 3. `resolve_from_path` accepts *any* `*/shims/*` path as a mise shim — confidence 85

`sync.py:131` (`if "shims" in parts`) and `sync.py:260-263`

The test is "is there a path segment literally named `shims`", not "is this mise's shim dir".
pyenv (`~/.pyenv/shims/`), asdf (`~/.asdf/shims/`) and rbenv all use exactly that name. Proved:

```
/Users/x/.pyenv/shims/graphify  -> ('', 'shim')
/Users/x/.asdf/shims/graphify   -> ('', 'shim')
finding: Finding(check='resolution', status='ok',
                 detail='resolves through the mise shim (pin applied at call time)')
resolved reported as: '0.9.25'   <-- fabricated; nothing read it
```

`_check_resolution` then returns `pinned` as the *resolved* version, so `SyncStatus.resolved` —
printed as fact in the detail page ("resolved `0.9.25`") — is a value no code ever read from
the binary. This is the same false-green class as the 0.9.23-ahead-of-shims defect this module
was written to catch, and it feeds gate 6. This host is clean today, but the engine is
explicitly shared with dotfiles, so any host with pyenv/asdf gets a silent pass. Match the mise
data dir (`MISE_DATA_DIR` / `~/.local/share/mise/shims`), not the bare segment name.

Adjacent, same function, `sync.py:134`: `parts.index("installs")` takes the **first** match, so
a path with an earlier `installs/` segment reads the version from the wrong index. Use `rindex`.

### 4. `_artifact_commit` returns a wrong non-empty value whenever `built_at_commit` is not the final key — confidence 85

`sync.py:214-222`. `partition(b":")` splits at the first colon, so everything after the value is
kept and only stripped of `,\n }` and `"`. If any key follows `built_at_commit`, the returned
"commit" is a JSON fragment. Proved against a real graphify-shaped document:

```
_artifact_commit -> 'e14abc0b01a7afd53f322d9ceb97bf48cef1fc45",\n  "schema": 2'
```

Today's `graphify-out/graph.json` (352 MB) does end with the key, so this is latent — but it is
one upstream key-order change away, and it lands in the committed stamp's `artifact_commit`
field and in the drift message as `live_commit[:8]`.

The other direction is worse because it is silent: `fh.seek(size - 4096)` means a document where
the key sits more than 4 KB from EOF yields `""`. Proved: a 12 KB file with the key near the
front → `''`. That does not report a problem — it *disables* the tamper check (see #5). Bound
the value at the closing quote rather than partitioning, and treat "needle not found in the
tail" as a distinct unreadable state rather than as `""`.

### 5. `_check_stamp` goes green when the artifact is missing or its commit is unreadable — confidence 82

`sync.py:327` — `if live_commit and recorded_commit and live_commit != recorded_commit:`

`live_commit == ""` skips the "rebuilt outside the build task" branch entirely and falls through
to the version comparison, which passes. Proved:

```
with artifact   -> Finding('build-stamp', 'ok', 'artifacts were built by the pinned 0.9.25')
artifact DELETED-> Finding('build-stamp', 'ok', 'artifacts were built by the pinned 0.9.25')
```

So `graphify-out/graph.json` can be deleted, truncated, or replaced by anything whose
`built_at_commit` the tail scan cannot read, and step 1 reports "artifacts were built by the
pinned 0.9.25" — and gate 6 passes. Given the module's fail-closed contract, an artifact that is
configured but absent/unreadable should be DRIFT ("artifacts missing or unreadable — version
unverifiable"), not OK.

## One design note (not a finding) — STILL OPEN

`observe()` (`issues.py:64`) gives `kind = "local"` items a constant observation, so they can
never appear in `moved` and gate 5 can never block on them. The `label-communities-schema-gap`
item says "Re-probe on each bump" — nothing enforces that; an auto-applied bump ships without
the re-probe. **If that item is meant to be a hard stop, it needs to be an unconditional
Ambiguity, not a watch item.**

## Not bugs (checked and cleared — do not spend time here)

- `except OSError, subprocess.TimeoutExpired:` (`sync.py:160`, `232`) is valid — PEP 758, and
  the repo requires 3.14. Verified it parses.
- `Version.parse` fails closed on every realistic non-numeric PyPI form (`0.9.26rc1`, `.post1`,
  `+local`, `1!0.9.26` all → `None` → gate-1 Ambiguity). `is_patch_bump_from` correctly blocks
  `0.9.x → 0.10.0` and `1.x → 2.x`. Only cosmetic slack: `0.9.25 → 0.9.25.0` classifies as a
  patch bump.
- `report.append_row` / `_unique_detail_path`: no clobbering or data loss found; rows insert
  newest-first after the rule, a mangled landing page rebuilds the table rather than dropping
  the row, same-day runs get `-2`/`-3` suffixes.
- `issues` state round-trip is correct as of the uncommitted fix.

`uv run pytest tests/` is green with all five open findings present, so none of them has coverage.

---

## Caller's disposition (2026-07-24, commit `622acbe`)

| finding | disposition |
|---|---|
| 1A | FIXED — `decide()` now receives `observations` |
| 1B | FIXED earlier (`e5d15f7`) — whole `str(x.get(k, default))` class |
| 1C | FIXED — `tag_name` defaults to `""`, empty ⇒ error |
| 3 | FIXED — `_is_mise_shim` matches MISE_DATA_DIR / `~/.local/share/mise/shims`; `rindex` for `installs` |
| 4 | FIXED earlier (`3681b30`) — SHA-anchored regex, both ends scanned |
| 5 | FIXED earlier (`3681b30`) — `artifact_fingerprint` replaced the commit comparison |
| design note (local watch items can never block) | **STILL OPEN** — decide whether the schema-gap item is a hard stop |

## GitHub repos touched

- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) — the reviewed diff (PR #4).
- [Graphify-Labs/graphify](https://github.com/Graphify-Labs/graphify) — `export.py` read as ground truth.
