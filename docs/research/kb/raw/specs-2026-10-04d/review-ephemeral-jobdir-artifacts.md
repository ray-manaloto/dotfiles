# SDLC review request: ratified artifacts stranded in an ephemeral `$CLAUDE_JOB_DIR`

Mode: REVIEW. Do not write to any repository file. Write only your output file.

## The defect class (reported 2026-10-04 by the retiring coordinator e67105a8, endorsed by Ray)

Coordinators write ratified specs, Ray's rulings and evidence logs (e.g. a `land`
rc log) into `$CLAUDE_JOB_DIR/tmp` (`~/.claude/jobs/<short-id>/tmp/`). That dir is
deleted by `claude rm <session>`, which is routine cleanup after a coordinator is
retired. The coordinator-handoff flow (unattended handoff brief → census of heavy
runs → successor launch → `retire` → later `claude rm`) neither moves those
artifacts to a tracked location nor refuses to remove a session whose job dir still
holds them. Copies placed in `.agent/` are gitignored, so `git clean -xdf` removes
them and other clones never see them.

Worked instance: five ratified specs (`spec-rgs-narrow-fix.md`,
`spec-implementer-lane-settlement.md`, `spec-retire-harness-ship.md`,
`spec-banner-ansi-fix.md`, `spec-banner-ansi-r2-full.md`) existed only in
`~/.claude/jobs/e67105a8/tmp/` plus untracked `.agent/sdlc-specs/` until the
successor committed them by hand to `docs/research/kb/raw/specs-2026-10-04d/`.

## Scope to read

- `python/src/dotfiles_setup/coordinator_handoff.py` (launch census, retire gate)
- `.claude/skills/coordinator-handoff/SKILL.md`
- `.claude/skills/session-handoff/SKILL.md`
- `.claude/rules/agent-artifact-conventions.md`
- `.claude/rules/agent-report-persistence.md`
- related tests under `tests/` for coordinator_handoff

## Questions

1. Confirm or refute the defect with file:line evidence: does any step of the
   handoff/retire flow inspect or migrate `$CLAUDE_JOB_DIR` contents? Is `claude rm`
   reachable after retire without such a check?
2. Propose fixes, ranked, each with: mechanism, files touched, how it fails closed,
   test/control arm, cost. Consider at least: (a) the census also inventories the
   old job dir's non-log artifacts and the brief lists them as owed migrations;
   (b) `retire` (or a new `rm` gate) refuses while the old job dir holds files not
   byte-present in a tracked path, with an explicit override; (c) a convention that
   ratified specs are written to a tracked path from the start (e.g.
   `docs/specs/` or `docs/research/kb/raw/specs-<date>/`), enforced by doc + check;
   (d) any native Claude Code mechanism that already covers this (cite `$CC/` docs at
   `~/dev/github/ray-manaloto/knowledge-base/sources/agent-harness-docs/docs/claude-code`).
3. Name anything else in the job dir that is load-bearing (rc logs of in-flight runs)
   and how the successor should adopt it.

## Output

Findings table (severity | claim | file:line | evidence), then ranked proposals,
then a recommended option. End with `## GitHub repos touched`.
