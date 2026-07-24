# Silent-failure audit — `kb_setup.currency` + `graph._stamp_build` (agent `rev-silent`)

> **Provenance:** delivered via SendMessage on 2026-07-24, NOT written to disk by the
> agent. Persisted here verbatim at receipt-time per
> `.claude/rules/agent-report-persistence.md`. Reviewed the working tree of
> `feat/tool-currency-engine` mid-session, so some findings were already fixed as it
> wrote; it credits those inline. **Findings F1–F9 were re-verified against HEAD by the
> caller and F1/F2/F3/F4/F5/F6 were then fixed in commit `622acbe`.**

---

Reviewed the **working tree** (staged, ahead of `feat/tool-currency-engine` HEAD —
`issues.py`, `report.py`, `graph.py`, `cli.py` were edited mid-review; two defects I found
in the committed version are already fixed there, noted at the bottom). Every finding below
is reproduced by running the real modules against the real `currency.toml` / `mise.toml` /
`graphify-out/graph.json`.

Also confirmed live: this host is genuinely drifted (`graphify --version` → **0.9.23** under
a **0.9.25** pin), and `check` correctly reports it. The engine works; what follows is where
it can't.

### F1 — CRITICAL — An unreachable GitHub makes gate 5 *pass*, and the bump auto-applies

`decide.py:151` (`_gate_issues`) · `issues.py:158` (`changes`) · `run.py:_run_one`

`observe()` returns `Observation(error=…)` on gh failure. `differs_from` correctly refuses
to call that movement, so `moved == ()`. But `decide()` only ever receives `moved` — it
never sees the observations — so `_gate_issues(())` returns `None`, and gate 5 **"no tracked
issue moved"** is reported as PASSED.

Proven with all 5 real watch items errored (`gh: HTTP 403 rate limit`) + a clean sync + a
patch bump:

```
auto_apply: True
gates_passed: (... 'no tracked issue moved', 'step 1 currently green')
summary: 'graphify 0.9.25 → 0.9.26: auto-applying (6/6 gates)'
```

`SKILL.md:43` says `auto_apply: true` → *"Proceed to step 4"* (apply the bump). So an
expired `gh` token, a rate limit, or being offline for GitHub-but-not-PyPI ⇒ **graphify is
bumped unattended while #2101/#2086/#1653/#1824 and the `label_communities` local watch were
never read.** This is precisely "cannot check" rendered as "checked and correct", on the one
gate whose whole job is to stop a bump.

**Wrong belief:** "All six gates were evaluated and passed." Reality: gate 5 was never evaluated.
**Fix:** pass `observations` into `decide()`; any `o.error` ⇒ an `Ambiguity` on `GATES[4]`
(and drop it from `gates_passed`). `gates_passed` must list gates *evaluated and passed*,
never gates *not evaluated*.

### F2 — CRITICAL — Tool not installed at all ⇒ "in sync"

`sync.py:264` (`_check_resolution`, `how == "absent"` → `SKIP`) · `sync.py:63`

`applies_here()` already answers "should this tool exist here?". So on a host where the tool
*is* declared applicable, "not on PATH" is drift, not un-checkable. It's classified `SKIP`,
`SyncStatus.ok` stays True:

```
ok: True | summary: 'graphify 0.9.25: in sync'
  resolution skip | graphify-not-installed is not on PATH here
```

**Scenario:** fresh clone, or `mise install` failed/was never run.
**Wrong belief:** "the binary I'm about to run matches the pin" — there is no binary. The
hook is silent, `kb-build` then runs whatever `graphify` a global pipx/homebrew provides later.
**Fix:** `absent` ⇒ `DRIFT` when `spec.applies_here()`.

### F3 — HIGH — NOT-APPLICABLE renders as "in sync"

`sync.py:68` (`SyncStatus.summary`) · `sync.py:63` (`ok`)

`check_sync` returns a single `platform`/`SKIP` finding for a foreign host — correct — but
`summary()` has no branch for it:

```
ok: True | summary: 'graphify : in sync'
```

On a Linux CI runner, `currency check --verbose` prints `[currency] graphify : in sync` (note
the empty version). `config.py:78` explicitly cites `probes-need-a-control-arm.md` to forbid
exactly this; the docstring is right, the renderer isn't.
**Fix:** if every finding is `SKIP`, summarise as `not applicable here` / `not verifiable
here` — a third state, not the green one.

### F4 — HIGH — A missing or misplaced `currency.toml` is a totally silent pass

`config.py:139-140` · `run.py:41-49`

`load()` returns `()`; `check()` loops zero times, `drifted` is empty, `return 0`, **nothing
printed**. Proven on a temp repo with no `currency.toml`: exit 0, zero output.

Same for a typo'd filter — `check(REPO, only="graphifyy")` on the *real* repo: exit 0, zero
output. (`run()` at least prints `no tools configured in currency.toml` to stderr, but that
message is a lie in the filter case: the config exists and is fine; the *filter* matched nothing.)

**Wrong belief:** the SessionStart hook is silent, which the design defines as "clean". A
renamed/moved config, a wrong `-C` in the hook command, or a future consumer repo that copies
the hook without the config, all produce a permanently-green check that never runs. This is
the "a check that can only pass" failure mode at the top level.

**The asymmetry is backwards.** A *malformed* config is loud — `tomllib` raises
`TOMLDecodeError` straight out of the SessionStart hook. A *missing* one is silent. The loud
case is the trivially-recoverable one; the silent case is the one that quietly disables the
check forever.

**Fix:** keep `()` for genuinely-unadopted repos, but distinguish "no config" from "config
with zero tools", and make `check` print a one-line `[currency] no currency.toml at <path> —
step 1 did not run` when the hook was explicitly wired. For `only=`, error out
(`unknown tool 'x'; configured: …`) with a non-zero rc from the CLI path.

### F5 — HIGH — Unreachable upstream is reported as "current"

`decide.py:81` (`Verdict.summary`) · `decide.py:60-63` (`has_upgrade`) · `report.py:211`

The *gate logic* is clean — `probe` returning `reachable=False` produces an `upstream
reachable` ambiguity and `auto_apply=False`. No caller treats it as "no upgrade available".
**But the rendering does.** `decide()` sets `latest=""` on the unreachable path, so
`has_upgrade` is False, so `summary()` emits the literal word *current*:

```
'graphify 0.9.25, current: 1 question(s) for review'
```

That string is the landing-table row (`report.py:211`) and the run's stdout line. A human
scanning `docs/currency/README.md` reads a committed assertion that 0.9.25 **is** the latest
version, on a run that never reached PyPI.

Related, same file: `report.py:177` prints `Reachable: yes` whenever `reachable=True`, even
when `upstream.error` holds a real `gh api … exited 1` from the tag lookup (`probe` sets
`reachable=True, error=tag_err`).
**Fix:** render the unknown as unknown — `graphify 0.9.25, latest unknown (pypi lookup
failed: …)`. Never let "we didn't look" print as "current".

### F6 — HIGH — `_stamp_build`'s swallow leaves a stale stamp asserting a false "built by the pin"

`graph.py:170` (`except (OSError, ValueError, ImportError)`) · `graph.py:132` (stamp written
**last**) · `sync.py:327`

Two compounding facts:

1. `build()` overwrites `graphify-out/graph.json` at the `shutil.copy` seed step and only
   calls `_stamp_build` at the very end (`graph.py:132`). Any failure in between — a
   `merge-graphs` non-zero, `_MERGE_SCRIPT` dying, Ctrl-C — leaves a **new/partial artifact
   under the old stamp**, and the stamp is never invalidated first.
2. When `_stamp_build` itself fails, the `except` warns into a wall of build output and the
   old stamp survives verbatim.

The rebuild-detector can't save you, because `built_at_commit` is the **repo git commit**,
not a content hash — rebuilding at the same commit with a different binary leaves it
identical. Proven:

```
stamp: version 0.9.25, artifact_commit aaaaaaaa
artifact REBUILT (by the stale 0.9.23), same repo commit, stamp write failed
_check_stamp -> ok | 'artifacts were built by the pinned 0.9.25'   <-- FALSE GREEN
```

**Wrong belief:** "the graph I'm querying was produced by 0.9.25." It was produced by 0.9.23,
or is half-merged.
**Fix:** delete/invalidate the stamp at the **start** of `build()` (before the first
`shutil.copy`), so any abort leaves "never stamped" (which already fails closed as DRIFT),
and only write the true stamp on success. Keep the swallow, but make it unmistakable — the
current warning is one line among hundreds.

### F7 — HIGH — `_artifact_commit` returning `""` silently disables the rebuild detector

`sync.py:209, 216, 219` · guarded at `sync.py:327` by `if live_commit and recorded_commit and …`

Three distinct failures all collapse to the same `""` as "no value to compare", and
`_check_stamp` then skips the comparison and falls through to a green:

| cause | result |
|---|---|
| artifact **missing entirely** (`:209`) | `ok — artifacts were built by the pinned 0.9.25` (there are no artifacts) |
| artifact unreadable, `OSError` (`:216`) | `ok — …` |
| `built_at_commit` not in the last 4096 bytes (`:219`) | `ok — …`, detector permanently dead |

All three reproduced. The tail scan *currently* works on the real 352 MB `graph.json`
(`built_at_commit` is the final key), but that's an undocumented dependency on graphify's key
ordering — the day it appends anything after it, this check goes green forever with no signal.

**Fix:** the missing-artifact case is unambiguous DRIFT ("stamped, but the artifact it
describes is gone"). For OSError / needle-not-found, return a sentinel distinct from "" and
report `build-stamp | drift | artifact commit unreadable — version unknown`. Cheap hardening:
scan the last N bytes *and* the first N; if the needle is in neither, say so.

### F8 — MEDIUM — Extras in the pin that `currency.toml` doesn't declare are unflagged

`sync.py:289` (`if not spec.extras: return SKIP`)

`_check_extras(spec_without_extras, ("all","video","secret-extra"))` → `skip | no extras
declared for this tool`. The check is one-directional: it catches "config expects extras the
pin lacks", never "the pin installs extras nobody declared" — which is a real supply-surface
change for a tool installed from PyPI. Contributes to gate 4 passing.

### F9 — MEDIUM — `check()` / `run()` always return 0

`run.py:49, 55` and `run.py:86, 122`

Defensible for the hook, and drift is loudly printed. The only genuinely-fatal condition it
hides is **F4** (config absent/typo ⇒ the check didn't run), which is invisible because it's
silent, not because of the exit code. Fix F4 and the always-0 contract is fine as-is. Note
`run()` shares the always-0 rule, so `mise run kb-currency` can never be used as a CI gate —
worth stating explicitly in the task description so nobody later assumes it can.

### Verified correct (worth keeping)

- `Observation.differs_from` refusing to count an errored run as movement (`issues.py:48`) —
  right call, prevents a rate-limit from manufacturing movement on every item.
- `save_current` **carries the prior value forward** for an errored observation instead of
  dropping it. I proved the drop-version (in the committed HEAD) silently loses exactly one
  real `open→closed` transition after a transient failure; the working-tree version fixes it.
- `_stamp_build` no longer falls back to the pin when `graphify --version` is unreadable; it
  stamps `""`, and `_check_stamp` reports `built by an unknown version` — verified fail-closed.
- `_check_manifest` treating an unreadable/absent manifest as DRIFT, and `read_stamp`
  returning `{}` ⇒ DRIFT "never stamped" — both fail closed correctly.
- `decide()`'s unreachable-upstream and unparsable-version paths genuinely fail closed at the
  *gate* level (only the rendering, F5, is wrong).
- `except OSError, json.JSONDecodeError:` (`sync.py:160,232`, `issues.py:119`, `graph.py:87`)
  is valid PEP 758 syntax and parses fine under the pinned 3.14.6 — not a bug, but it hard-floors
  the package at 3.14 with no `requires-python` complaint if anyone vendors `kb_setup` elsewhere.

**Priority order:** F1 (auto-applies a bump on unread issues) → F2/F4 (green when nothing was
checked) → F6/F7 (green about an artifact nobody verified) → F3/F5 (green wording over a
known-unknown) → F8/F9.

---

## Caller's disposition (2026-07-24, commit `622acbe`)

| finding | disposition |
|---|---|
| F1 | FIXED — `decide()` now takes `observations`; any `o.error` ⇒ Ambiguity on GATES[4] |
| F2 | FIXED — absent binary on an applicable host is DRIFT |
| F3 | FIXED — added `SyncStatus.verified`; renders "not verifiable here" |
| F4 | FIXED — missing config prints "step 1 did NOT run"; unknown `--tool` exits 2 |
| F5 | FIXED — renders "latest UNKNOWN" instead of "current" |
| F6 | FIXED — stamp cleared at the START of `build()` |
| F7 | FIXED earlier — replaced by `artifact_fingerprint` (size:mtime_ns) |
| F8 | FIXED — undeclared extras in the pin are DRIFT |
| F9 | ACCEPTED — always-0 is correct once F4 is fixed. **Open:** state in the `kb-currency` task description that it cannot serve as a CI gate |
| `report.py` "Reachable: yes" while `error` is set | **STILL OPEN** |

## GitHub repos touched

- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) — the reviewed diff (PR #4).
- [Graphify-Labs/graphify](https://github.com/Graphify-Labs/graphify) — `export.py` read as ground truth.
