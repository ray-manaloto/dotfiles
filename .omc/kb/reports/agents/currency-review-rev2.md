# rev2 review — tool-currency engine (`feat/tool-currency-engine`)

Every claim below was produced by running python against the real modules in
`/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base`. Each negative claim
carries a control arm showing the same probe can return the other answer.

**Note:** the tree moved under me during the review (commits `dc6bff1`, `e5d15f7`,
plus uncommitted `sync.py` edits). Everything below is re-verified against the tree
as it stands now. Three defects I confirmed early were fixed concurrently; they are
listed at the bottom as *closed*, with proof they no longer reproduce.

---

## OPEN-1 — HIGH (auto_apply): a multi-release jump reviews only the NEWEST release's notes

**File:** `python/src/kb_setup/currency/upstream.py:194` (`probe`) → gate 3 in
`decide.py:_gate_markers`

`probe()` fetches exactly one release — `release_for_tag(github, latest)`. `_gate_patch`
meanwhile accepts *any* distance within the patch slot (`0.9.25 → 0.9.28` is a patch
bump). So when the pin has fallen several patches behind — the normal state, since this
workflow is not run daily — the engine scans **only the newest release body** and
auto-applies across every release it never read. A breaking change announced in 0.9.26
is invisible.

**Exact input:** pinned 0.9.25; PyPI latest 0.9.28; GitHub release v0.9.28 body
`"Routine: faster BFS."`; sync clean; no moved issues.

**Wrong output:** `auto_apply=True`, `6/6 gates`,
`graphify 0.9.25 → 0.9.28: auto-applying (6/6 gates)` — 0.9.26 and 0.9.27 unread.

**Proof — the decision:**
```
$ uv run python - <<'PY'
from kb_setup.currency import upstream
from kb_setup.currency.decide import decide
from kb_setup.currency.sync import SyncStatus, Finding, OK
up = upstream.UpstreamStatus(pypi_latest="0.9.28", github_tag="v0.9.28",
                             notes="Routine: faster BFS.", reachable=True, error="")
s = SyncStatus(tool="graphify", pinned="0.9.25", resolved="0.9.25",
               findings=(Finding("pin", OK, "ok"),))
v = decide(sync=s, upstream=up, moved=())
print(v.auto_apply, len(v.gates_passed), v.summary())
PY
True 6 graphify 0.9.25 → 0.9.28: auto-applying (6/6 gates)
```

**Proof — that the intermediate releases are genuinely never fetched** (fake `gh` on
PATH logging every invocation):
```
$ cat > /tmp/rev2/fakebin/gh <<'EOF'
#!/bin/sh
echo "$@" >> /tmp/rev2/gh-calls.log
cat /tmp/rev2/payload.json
exit 0
EOF
$ chmod +x /tmp/rev2/fakebin/gh; rm -f /tmp/rev2/gh-calls.log
$ echo '{"tag_name":"v0.9.28","body":"Routine: faster BFS."}' > /tmp/rev2/payload.json
$ PATH=/tmp/rev2/fakebin:$PATH uv run python -c "
from kb_setup.currency import upstream
print(upstream.release_for_tag('Graphify-Labs/graphify','0.9.28'))"
$ cat /tmp/rev2/gh-calls.log
api repos/Graphify-Labs/graphify/releases/tags/0.9.28
```
One call. Nothing asks about 0.9.26 or 0.9.27.

**Fix:** either scan every release between `current` and `latest`
(`GET /repos/{repo}/releases` and filter), or make gate 1 require *adjacency* —
`new.parts[2] == cur.parts[2] + 1` — so a multi-release jump always goes to the
interview. The second is one line and preserves the fail-closed posture.

---

## OPEN-2 — MEDIUM-HIGH (auto_apply): the breaking-marker list misses the spec's own synonyms

**File:** `python/src/kb_setup/currency/upstream.py:29-40` (`BREAKING_MARKERS`)

`markers` is a plain case-insensitive substring scan. It catches `breaking change`
(and `breaking changes`, `### Breaking changes`) but not three phrasings that are at
least as common in real release notes — including one the Conventional Commits spec
explicitly sanctions as equivalent.

**Exact inputs / wrong outputs** (pinned 0.9.25 → 0.9.26, tag present, sync clean):

| release body | auto_apply |
|---|---|
| `BREAKING CHANGE: config format changed` | False ← **control arm** |
| `### Breaking changes\n\n- config moved` | False ← **control arm** |
| `BREAKING-CHANGE: config format changed` | **True** (Conventional Commits' own hyphen synonym) |
| `**BREAKING**: the config format changed` | **True** (bolded — the GitHub release convention) |
| `feat!: drop the v1 config format` | **True** (conventional-commits `!` marker) |

The two control rows prove the gate is capable of stopping; the three below it are
real releases it would wave through unattended.

**Proof:**
```
$ uv run python - <<'PY'
from kb_setup.currency import upstream
from kb_setup.currency.decide import decide
from kb_setup.currency.sync import SyncStatus, Finding, OK
def verdict(notes):
    up = upstream.UpstreamStatus(pypi_latest="0.9.26", github_tag="v0.9.26",
                                 notes=notes, reachable=True, error="")
    s = SyncStatus(tool="graphify", pinned="0.9.25", resolved="0.9.25",
                   findings=(Finding("pin", OK, "ok"),))
    return decide(sync=s, upstream=up, moved=()).auto_apply
for b in ["BREAKING CHANGE: config format changed",
          "### Breaking changes\n\n- config moved",
          "BREAKING-CHANGE: config format changed",
          "**BREAKING**: the config format changed",
          "feat!: drop the v1 config format"]:
    print(verdict(b), repr(b))
PY
False 'BREAKING CHANGE: config format changed'
False '### Breaking changes\n\n- config moved'
True  'BREAKING-CHANGE: config format changed'
True  '**BREAKING**: the config format changed'
True  'feat!: drop the v1 config format'
```

**Fix:** match on a normalized body (strip `*`/`_`, collapse `-` and `_` to space)
before the substring scan, and add a regex for the conventional-commits bang
(`^\w+(\([^)]*\))?!:`). A bare `breaking` marker would also be defensible here given
the gate's job is to *route to a human*, not to classify.

---

## OPEN-3 — MEDIUM: gate 6 reports "step 1 currently green" when step 1 mostly did not run

**File:** `python/src/kb_setup/currency/sync.py:63-66` (`SyncStatus.ok`) →
`decide.py:_gate_sync` (GATES[5], "step 1 currently green")

`ok` is `not self.drifted`, and SKIP is not DRIFT. That is the documented intent for
the hook, but gate 6 reuses it as a positive assertion. The result: a host where the
tool is **not installed at all** produces 4 SKIPs out of 6 checks and still reports
green, and the bump auto-applies. This is the absence-of-evidence shape
`.claude/rules/probes-need-a-control-arm.md` exists to prevent — "nothing disagreed"
is being read as "everything agreed", on a run where almost nothing was checked.

**Exact input:** `mise.toml` pins `pipx:graphifyy = { version = "0.9.25", extras = ["all"] }`;
`binary` not on PATH; no manifest, no stamp, no resolvable install; PyPI latest 0.9.26
with a clean release body.

**Wrong output:**
```
  pin            ok    mise.toml pins pipx:graphifyy at 0.9.25
  resolution     skip  <binary> is not on PATH here
  extras         ok    pin declares the expected extras ['all']
  extra-probes   skip  install path not resolvable here without a subprocess
  manifest       skip  this repo pins no source manifest for the tool
  build-stamp    skip  this tool declares no build stamp
sync.ok = True  -> gate 6 'step 1 currently green' passes
auto_apply = True | graphify 0.9.25 → 0.9.26: auto-applying (6/6 gates)
```

**Proof:**
```
$ uv run python - <<'PY'
import tempfile
from pathlib import Path
from kb_setup.currency import sync, upstream
from kb_setup.currency.config import ToolSpec
from kb_setup.currency.decide import decide
td = Path(tempfile.mkdtemp())
(td/"mise.toml").write_text('[tools]\n"pipx:graphifyy" = { version = "0.9.25", extras = ["all"] }\n')
spec = ToolSpec(name="graphify", mise_key="pipx:graphifyy",
                binary="definitely-not-a-real-binary-xyz", extras=("all",), extra_probes=("networkx",))
st = sync.check_sync(td, spec)
for f in st.findings: print(f"  {f.check:14} {f.status:5} {f.detail}")
up = upstream.UpstreamStatus(pypi_latest="0.9.26", github_tag="v0.9.26",
                             notes="Routine bugfixes.", reachable=True)
print("sync.ok =", st.ok, "| auto_apply =", decide(sync=st, upstream=up, moved=()).auto_apply)
PY
```
(Control arm: the same `check_sync` on this repo's real config returns
`resolution ok` / `extra-probes ok`, i.e. it does distinguish — see the committed
`docs/currency/runs/2026-07-24-graphify.md`.)

**Fix:** gate 6 should require the load-bearing checks to have positively passed, not
merely not-failed — e.g. `resolution` and `build-stamp` must be `OK` (not SKIP) before
an unattended bump is authorized. SKIP staying non-red for the *hook* is right; SKIP
counting as consent for an *unattended action* is not.

---

## OPEN-4 — MEDIUM: `save_current`'s carry-forward guards `error` only, so a successful-but-empty observation still wipes the baseline

**File:** `python/src/kb_setup/currency/issues.py:155` (`save_current`) with
`issues.py:94-99` (`observe`)

The new carry-forward keys on `o.error`. But `observe` only sets `error` for a non-zero
`gh` exit or a JSON parse failure. A **200 whose body lacks the watched fields** parses
fine, yields `state=""`/`updated_at=""`/`comments=0` with `error=""`, and is therefore
treated as a good observation: it overwrites the stored baseline *and* — because `""`
differs from `"open"` — is reported as a tracked issue having moved. The next healthy
run then reports it as moved a **second** time, since the baseline it is compared
against is now the wiped one.

This is exactly the failure mode the docstring says the change exists to prevent
("Dropping it would silently erase the baseline"), reached through a degraded-success
response instead of a hard error.

**Exact input:** three consecutive runs against `gh` returning, in order,
a healthy payload → `{"state":null,"updated_at":null,"comments":null,"title":null}` →
the same healthy payload.

**Wrong output:**
```
1 healthy                state='open'   err=''   MOVED=[]
                         saved -> {'comments': 0, 'state': 'open', 'title': 't', 'updated_at': '2026-07-04T16:21:58Z'}
2 all-null fields        state=''       err=''   MOVED=['issue:1653']    <-- false alarm #1, baseline destroyed
                         saved -> {'comments': 0, 'state': '', 'title': '', 'updated_at': ''}
3 healthy again          state='open'   err=''   MOVED=['issue:1653']    <-- false alarm #2
                         saved -> {'comments': 0, 'state': 'open', 'title': 't', 'updated_at': '2026-07-04T16:21:58Z'}
```
Two spurious "tracked issue moved" ambiguities, each of which blocks an otherwise
unambiguous bump and burns an AskUserQuestion round-trip.

**Control arm** (run 4, a genuine close): `state='closed' MOVED=['issue:1653']` — the
diff does detect real movement, so runs 2 and 3 above are false positives, not a dead
probe.

**Proof:**
```
$ cat > /tmp/rev2/fakebin/gh <<'EOF'
#!/bin/sh
cat /tmp/rev2/payload.json
exit 0
EOF
$ chmod +x /tmp/rev2/fakebin/gh
$ PATH=/tmp/rev2/fakebin:$PATH uv run python - <<'PY'
import json, tempfile
from pathlib import Path
from kb_setup.currency import issues
from kb_setup.currency.config import ToolSpec, WatchItem
spec = ToolSpec(name="graphify", mise_key="pipx:graphifyy", github="Graphify-Labs/graphify",
                watch=(WatchItem(kind="issue", ref="1653"),))
td = Path(tempfile.mkdtemp()); PAY = Path("/tmp/rev2/payload.json")
HEALTHY = '{"state":"open","updated_at":"2026-07-04T16:21:58Z","comments":0,"title":"t"}'
def run(label, fake):
    PAY.write_text(fake)
    obs = issues.observe_all(spec)
    moved = issues.changes(obs, issues.load_previous(td, "graphify"))
    issues.save_current(td, "graphify", obs)
    print(label, obs[0].state, repr(obs[0].error), [o.key for o in moved],
          json.loads((td/'graphify-watch-state.json').read_text()).get('issue:1653'))
run("1 healthy",         HEALTHY)
run("2 all-null fields", '{"state":null,"updated_at":null,"comments":null,"title":null}')
run("3 healthy again",   HEALTHY)
run("4 CONTROL closed",  '{"state":"closed","updated_at":"2026-07-25T00:00:00Z","comments":1,"title":"t"}')
PY
```

**Fix:** make the carry-forward condition "this observation is not usable", not "this
observation errored" — e.g. `source = o if (not o.error and o.state) else previous.get(o.key)`,
and have `observe` set `error` when the payload is missing `state`/`updated_at` rather
than silently returning blanks.

---

# Categories where I found nothing real

## `report.append_row` — clean

No path found that loses a row or corrupts the table. Probed 50 randomized appends
(varying tool, upgrade/no-upgrade, auto_apply, detail/no-detail) plus seven
landing-page shapes:

```
appends: 50   rows present: 50   malformed rows (cell count != 4): 0
rule lines: 1  header lines: 1

  pristine committed landing page        rows 1 -> 2   tables=1
  CRLF line endings                      rows 1 -> 2   tables=1
  extra section appended below table     rows 1 -> 2   tables=1
  no trailing newline                    rows 1 -> 2   tables=1
  empty file                             rows 0 -> 1   tables=1
  BOM prefix                             rows 1 -> 2   tables=1
  10 existing rows                       rows 11 -> 12 tables=1
```
The one theoretical fragility — `_TABLE_RULE` is matched as an exact string, so a
reformatted `| --- | --- | --- | --- |` rule would fragment the log into a second
table — is not reachable in practice: I ran the repo's own formatter
(`mise exec -- rumdl check --fix`) over `docs/currency/README.md` and it leaves the
rule byte-identical. Not reporting it.

Re-verified against the current `report.py` after the `_cell()` escaping was added:
50/50 rows, 0 malformed, 1 table; and a pipe-bearing verdict now renders as
`| a\|b | a\|b 1\|2, current: clean |` instead of splitting the row.

## `upstream.Version` — clean as it now stands

After the `is_patch_bump_from` fix (it now delegates to `__gt__` instead of comparing
raw tuples), every edge case I could construct behaves correctly:

```
  '0.9'    -> '0.9.0'      patch_bump=False   (same version, correctly not an upgrade)
  '0.9.25' -> '0.9.25.0'   patch_bump=False
  '0.9.25' -> '0.9.26'     patch_bump=True
  '0.9.25' -> '0.10.0'     patch_bump=False   (pre-1.0 minor = breaking channel)
  '0.9.25' -> '0.9.25.1'   patch_bump=True
  '0.9.09' -> '0.9.10'     patch_bump=True    (leading zero, numeric compare)
  '1.2.3'  -> '1.2.<10^24>' patch_bump=True   (bignum, no overflow)
  '0.9.25' -> '0.9.-1'     patch_bump=False   (negative rejected as a downgrade)
  garbage: '' 'v' 'latest' '1.0.0rc1' '1.0.0.post1' '1.2.3+local'  -> all parse to None
           -> gate 1 raises the "could not be parsed" ambiguity (fails closed)
```
`int()` also accepts `+26`, `2_6`, `" 26"` and non-ASCII digits, but each resolves to
the correct numeric value and PyPI cannot emit those strings as a version, so there is
no reachable wrong decision. Not reporting it.

---

# Confirmed, then fixed while the review was running

Recording these so you know the review covered them and that the fixes hold. All three
reproduced when I found them and no longer reproduce now.

- **`"body": null` defeats the empty-notes gate.** `str(payload.get("body", ""))`
  returned the 4-char string `"None"` for a release published without notes, which is
  non-empty and sailed past `_gate_markers` → `auto_apply=True, 6/6 gates`. Now
  `auto_apply=False, 1 question(s) for review`. Fixed in `e5d15f7`.
- **`_artifact_commit` returned confident nonsense for a node *named* `built_at_commit`.**
  My probe got `'attribute", "source_file": "export.py"}\n  ]'` instead of the SHA;
  the SHA-shaped-value regex now returns `'deadbeef1234567'` correctly. (Control: the
  live 352 MB `graphify-out/graph.json` has exactly 1 occurrence, at offset 352327084 —
  the real key — so this was latent, not firing.) Fixed in the working tree.
- **A rogue rebuild at the same git HEAD was a false green.** `built_at_commit` is
  `_git_head()` (verified in `graphify/export.py:315`), identical across every rebuild
  at one commit, so `build-stamp` reported `ok | artifacts were built by the pinned
  0.9.25` for a graph a stale 0.9.23 had rebuilt. The `size:mtime_ns` fingerprint now
  reports `drift | artifacts changed since they were stamped`. Fixed in the working
  tree; `CLAUDE.md` updated to match.

---

# Category 5 follow-up — `save_current` / `load_previous` round trip

Positive result first: **the carry-forward change itself is correct.** A 4-run `gh`
outage keeps the baseline intact and the real close is detected on recovery:

```
run1 healthy (baseline open)                        MOVED=[]      state_keys=['issue:1653']
run2..run5 gh ERRORS                                MOVED=[]      state_keys=['issue:1653']   <- baseline held
run6 healthy again, issue CLOSED during the outage  MOVED=['issue:1653']
```
Three ways it can still silently drop a baseline, all with control arms:

## OPEN-5 — HIGH: a truncated state file loses every baseline with **zero** signal

**File:** `issues.py:160` (`save_current` — `path.write_text(...)`) with
`issues.py:117-121` (`load_previous` — `except OSError, json.JSONDecodeError: return {}`)

`save_current` writes non-atomically. An interrupted run / ENOSPC / a killed session
leaves a half-written JSON object. `load_previous` then swallows the parse error and
returns `{}` — which is **indistinguishable from "first ever run"**. Every tracked
issue silently reverts to first-observation semantics, so the next real movement on
every item is reported as no movement, and nothing anywhere says the history was lost.

```
run1 healthy (2 baselines stored)              MOVED=[]
   state file truncated mid-object; load_previous -> {}
run2 BOTH issues CLOSED after the truncation   MOVED=[]        <-- both misses
   ^ no MOVED, no error surfaced anywhere

CONTROL (identical run2, state file intact):
run2 BOTH issues CLOSED                        MOVED=['issue:1653', 'issue:1824']
```
graphify itself guards exactly this in `export.py` (`write_json_atomic`, commented
"a crash/ENOSPC mid-write must not truncate a good graph.json"). Fix: write to a
temp file and `os.replace`, and make `load_previous` distinguish "absent" from
"unreadable" so an unreadable state file becomes a finding rather than silence.

## OPEN-6 — MEDIUM: a no-op config edit re-keys an item and orphans its baseline

**File:** `config.py:48` (`WatchItem.key`) vs `issues.py:60` (`observe` uses
`item.repo or default_repo`)

`observe` resolves `repo` through `default_repo`, so `{kind="issue", ref="1653"}` and
`{kind="issue", ref="1653", repo="Graphify-Labs/graphify"}` fetch the **same issue** —
but `key` includes `repo`, so they are `issue:1653` and
`issue:Graphify-Labs/graphify#1653`. Adding an explicit, identical `repo =` to an
existing entry — a harmless-looking tidy-up — silently orphans the baseline, and the
prune drops the old key in the same write, so it is unrecoverable.

```
run1 config without repo=  (baseline open)      MOVED=[]  state_keys=['issue:1653']
run2 config gains repo=, issue CLOSED same run  MOVED=[]  state_keys=['issue:Graphify-Labs/graphify#1653']

CONTROL (config unchanged):
run2 issue CLOSED                               MOVED=['issue:1653']
```
Fix: build `key` from the **resolved** repo (`item.repo or default_repo`) so identity
does not depend on whether the config spells out a default.

## OPEN-7 — LOW: prune + re-add is blind for exactly one run

Documented ("Items no longer in the config are pruned"), but the consequence is not:
a re-added watch item is treated as first-ever-observed, so anything that happened
while it was unwatched is silently skipped. Its own built-in control arm — `1653`,
never unwatched, is reported in the same run that misses `1824`:

```
run1 both watched (baseline open)               MOVED=[]
run2 1824 removed from currency.toml -> pruned  MOVED=[]
run3 1824 re-added; it CLOSED while unwatched   MOVED=['issue:1653']   <-- 1824 missing
```
Worth a docstring line at minimum; prune-with-tombstone if you want it airtight.

**No key can be resurrected.** `payload` is built only from keys present in
`observations`, so a stale entry can never reappear — the failure mode here is always
silent *loss*, never phantom data.

## GitHub repos touched

- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) — the reviewed diff (PR #4).
- [Graphify-Labs/graphify](https://github.com/Graphify-Labs/graphify) — `export.py` read as ground truth.
