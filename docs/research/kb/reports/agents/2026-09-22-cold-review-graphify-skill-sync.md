# Cold review: graphify skill-surface refresh automation

**Diffed:** `main` @ `10a17128d29e30b2fe7f70cfbc8fa6515030b537` .. `fix/graphify-update-skill-version-sync` @ `fb89c433778b904a1e589230c822b5357054f129` (single commit `fb89c433 feat(graphify): automate skill-surface refresh`, HEAD of the branch).

Cold review per this repo's CLAUDE.md: codex (GPT-5.6 Sol) authored the diff, Opus cold lens required (cross-family). No spec/plan read before forming findings below; constraints cross-checked afterward against fresh reads of the named files.

Status: COMPLETE.

---

## Findings

### 1. MEDIUM — misleading justification + reintroduced silent-success bug in `.claude/skills/graphify/SKILL.md` (and `.codex/`'s copy)

`.claude/skills/graphify/SKILL.md:521-525` (diff hunk) drops a locally hand-added
`raise SystemExit(1)` from Step 5's shrink-guard:

```python
wrote = to_json(G, communities, 'graphify-out/graph.json', community_labels=labels)
if not wrote:
    print('ERROR: refused to shrink graphify-out/graph.json (existing graph has more nodes; #479).')
    print('If this shrink is intentional (you deleted files), re-run a full build with --force.')
print('Report updated with community labels')   # <- always runs, incl. on failure
```

Confirmed this line was a **repo-local deviation from the vendor package**, not
an artifact of this diff's edits: `diff <(git show main:.claude/skills/graphify/SKILL.md)
python/.venv/…/graphify/skill.md` (the currently-installed 0.9.65 package) shows
exactly one line of difference — this `raise SystemExit(1)`. The new
`refresh_skills()`/`install_skill()` machinery (`graphify_skill.py`) treats any
byte-difference from the packaged file as "drift" and overwrites it — by
design, confirmed live: `refresh_skills` on `main`'s tree would back up
main's copy to `SKILL.md.bak` and replace it with the vendor's.

The new docs added to justify this
(`.claude/skills/graphify-skill-install/SKILL.md` "Automatic refresh…" section)
say: *"the repo's own update wrapper already fails closed on its return
code"* — but that sentence is about `graphify_skill_refresh_main`'s own exit
code (whether the **file copy** succeeded), not about the embedded Python
snippet's exit code that the removed line controlled. Those are two unrelated
subprocess/exit-code domains. The actual behavior change: an agent following
Step 5 today, on a real shrink refusal, now sees `ERROR: refused to
shrink…` immediately followed by `Report updated with community labels` — a
false-success line that was previously unreachable (the process exited
first). This is independent of any exit-code reasoning: that final `print`
was never inside the `if not wrote:` block, so removing the `raise` alone
reintroduces the misleading message.

Because `mise run graphify-update` (the routine graph-rebuild task per
`.claude/rules/graphify-first.md`) now calls `refresh_skills()` automatically
on every successful rebuild, **any future repo-local safety patch to vendor
skill content will be silently overwritten the next time anyone runs the
routine rebuild task** — not just on a deliberate version bump. The only
recovery trail is an untracked `SKILL.md.bak` (not gitignored, so visible in
`git status`, but nothing prompts a human to look at it — no hk step, no
doctor check, no suites.toml contract references `.bak`).

This is a **known, named tradeoff** (the PR's own docs call it out), so I'm
not flagging the design decision itself — repo-local patches to third-party
vendor content are inherently fragile — but the stated **justification is
factually wrong**, and the specific regression (a misleading success message
on a real error) is real and reachable from the routine, unattended task path.

### 2. LOW — new dependency surface (`pillow`) enters `graphifyy[all]` unremarked

`python/uv.lock` diff adds `{ name = "pillow" }` under graphify 0.9.65's
`all` extras (was not present at 0.9.61). Not a defect, but worth a
one-line callout since `openai` is *also* already in that extras group
(pre-existing) — the new "never invokes graphify.llm" boundary in the SKILL.md
docs is exactly the right thing given that surface, but nothing pins down
*why* Pillow showed up (likely image/vision support in graphify itself). No
action needed; noting for the record.

## Clean report

Checked, and found fine, by re-reading the code fresh and running live
commands (not by trusting the lane's self-report):

- **`.agents/skills/graphify/SKILL.md` byte-identity + stub marker.**
  `diff <(git show main:.agents/skills/graphify/SKILL.md) <(git show
  fb89c433:…)` → identical. Contains `DELIBERATE STUB` at line 6. No
  `.agents/skills/graphify/references/` directory exists in the diff's tree
  (`git ls-tree -r fb89c433 -- .agents/skills/graphify/` shows only
  `SKILL.md` + `.graphify_version`).
- **Zero agent/LLM tokens reachable from the refresh path.** Grepped
  `graphify.py`, `graphify_skill.py`, `doctor.py`, `main.py` for
  `graphify.llm`, `dedup-llm`, `label`, `agy`, `codex`, `claude-cli` — no
  import of `graphify.llm`, no subprocess call to any labeling/agent CLI in
  the `refresh_skills`/`check_skills`/`graphify_update_main` call chain.
  `graphify_skill.py` doesn't even import `subprocess`. The one live test
  (`test_refresh_skills_updates_managed_surfaces_and_only_the_agents_stamp`)
  patches `subprocess.run`/`Popen` to `pytest.fail` and calls `refresh_skills`
  — passes.
- **Idempotency.** Same test: `refresh_skills(project_dir)` called twice
  returns non-empty then `()`, and asserts `not list(project_dir.rglob("*.bak"))`
  after a from-scratch (non-drifted) run. Live-verified against the real
  repo too: running `dotfiles-setup doctor` and `mise run pin-parity` against
  the actual checked-out tree at `fb89c433` shows **zero** graphify findings —
  the tree is already in the refreshed, stable state.
- **Version-drift gate vs. pin-parity vs. `python/pyproject.toml`, LIVE (not
  just read).** Ran `uv run --project python dotfiles-setup pin-parity`
  against the real tree: `OK graphify` across all 5 declared sites
  (`python/pyproject.toml` both occurrences, `graphify.py`'s
  `EXPECTED_GRAPHIFY_VERSION`, and all three `.graphify_version` stamps), all
  reading `0.9.65`. Repo-wide grep for `0.9.61` finds it only in historical
  `docs/research/kb/reports/agents/*.md` (frozen records, correctly
  untouched per `agent-artifact-conventions.md` rule 8) and two prose-only
  spots (`pin-parity.toml`'s own incident narrative,
  `dependency_currency.py`'s dated measurement example) — no live/functional
  site left un-bumped, and no new unregistered version literal introduced.
- **`.claude/skills/graphify/.graphify_version` tracking.** `git ls-files`
  confirms all three `.graphify_version` stamps (`.claude`, `.codex`,
  `.agents`) are tracked; `.gitignore`'s old
  `.claude/skills/graphify/.graphify_version` ignore line is removed and
  replaced with an explanatory comment.
- **`doctor.py` private-API import boundary.** The two new helper functions
  (`_graphify_stamp_findings`, `_graphify_path_binary_findings`) use only
  `importlib.metadata.version`, `shutil.which`, and `subprocess.run(["graphify",
  "--version"])` — no `graphify.install._PLATFORM_CONFIG` or other private
  access. `graphify_skill.py` remains the sole carrier of the documented
  `SLF001` allowance.
- **`.agents/skills/graphify-skill-install/SKILL.md` addition is genuinely
  docs-only.** Its added section is byte-identical prose to the `.claude`
  copy's addition; `dotfiles-setup skills-mirror --check` run live against
  the checked-out tree returns `skills-mirror OK` (rc=0) — the mirror is not
  stale. Confirmed it does not touch `.agents/skills/graphify/` (the stub) —
  only `.agents/skills/graphify-skill-install/`, a different skill.
- **Whole-`suites.toml` `per_path_tokens` replay** (not just the new
  `workflow.graphify-skill-refresh-wiring` suite): wrote a standalone script
  reading every `per_path_tokens` entry in the real
  `python/verification/suites.toml` against the real tree — **0 failures**
  across the whole file, confirming the new suite's tokens genuinely match
  and nothing else regressed.
- **Test quality, not just presence.** `tests/test_graphify_skill.py`'s
  refresh/check tests assert exact backup/no-backup behavior, the
  `MANAGED_PLATFORMS`-mutation guard test (proves the "agents stays
  stub-only" invariant is actually load-bearing, not just asserted against
  itself), and drift-reason enumeration by exact tuple match (not a substring
  check). `tests/test_doctor.py`'s four new tests assert specific finding
  text (stamp path named, "mise run graphify-update" named, "repo pin"/
  "user-global mise pin" named) rather than just "findings non-empty".
  `tests/test_graphify.py`'s reshaped pin-binding test
  (`test_graphify_runtime_constant_matches_project_pin`) trades a
  grep-the-source-literal technique for importing the same
  `EXPECTED_GRAPHIFY_VERSION` constant the production code uses — a real
  improvement (no separate literal to drift), with the cross-check moved to
  the (live-verified) `pin-parity` gate rather than dropped.
- **Live pytest, not just the claimed count.** Ran the four directly-relevant
  test files myself: `211 passed` in 0.75s, rc=0
  (`tests/test_graphify_skill.py tests/test_doctor.py tests/test_pin_parity.py
  tests/test_graphify.py`). Then ran the FULL suite myself:
  `uv run --project python pytest tests/ -q` → **`3718 passed, 11 deselected
  in 275.51s`, `rc=0`** — read from the redirected log file, not from the
  background-task completion notification (which reported "exit code 0" but
  per `feedback_background_task_notification_can_lie` that notification is
  not trusted as evidence on its own). The count matches the lane's claim
  exactly.

## Status: COMPLETE

Both SHAs resolved and diffed directly (`git diff <base>..<head>`, no
reliance on the lane's restatement). One finding (MEDIUM, misleading
justification text + a real reintroduced UX bug in vendor skill content,
not a lint/test/security hole). Every constraint in the cross-check list
verified against a fresh read of the relevant file plus a live command,
not accepted from the lane's self-report.

