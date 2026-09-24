# Spec — triage all 335 open issues into ONE universal devcontainer task + a phased plan

## Why this exists

The operator's words: *"must triage all open issues and plans to make sure we
only have **one universal task** for this to avoid all this confusion."*

The confusion is real and measured. This session spent three audit rounds and
twelve rulings on a "next task" (agentsview) that had been reassigned to another
project, while the operator's actual primary goal sat in unblocked issues nobody
had cited. **Four separate retrieval failures happened today** — information that
existed, was correct, and that nobody searched for.

## ⭐ You have FULL ACCESS and NETWORK. This is new.

As of commit `38ed61f`, `mise run sdlc-team` no longer passes `-s` or
`--ephemeral`. You inherit the machine's `danger-full-access` and you **can run
`gh`**. Every prior SDLC lane was silently network-blocked.

**The operator has authorised FULL AUTONOMY for this run**: label, comment,
cross-link, close, and create issues directly. Do the work; do not merely
propose it.

## ⚠️ FILE RULES — nothing enforces these but this spec

Some are prohibitions, some are REQUIREMENTS. Read each.

1. **Do NOT write `task_plan.md`.** It is coordinator-only with no exception
   (`.claude/rules/agent-report-persistence.md`). Write your proposed plan to
   **`.agent/plans/task_plan-delta-triage-2026-09-15.md`** and the coordinator
   applies it.
2. **`findings.md` and `progress.md`: APPEND ONLY — required, not forbidden.**
   ⚠️ An earlier version of this spec forbade them outright and a lane correctly
   stopped under licensed dissent, because
   `.claude/rules/notepad-enforcement.md:24` REQUIRES findings appended during
   investigation. The real constraint is HOW: **append**, never rewrite. A lane
   truncated both files on 2026-09-09 by opening its section with its own
   heading as the whole file. Read the file, append your section, never replace.

3. **Persist your findings-bearing report VERBATIM at receipt** to
   `docs/research/kb/reports/agents/issue-triage-2026-09-15.md`
   (`.claude/rules/agent-report-persistence.md:61`). Write it incrementally —
   a lane that dies after triaging 200 issues should leave 200 recoverable.
4. **Do NOT touch `git`** — no commits, branches, pushes, or merges.
5. **Do NOT close an issue you cannot cite a reason for.** Every close needs a
   one-line justification in the close comment.
6. **Do NOT delete or edit issue BODIES.** Add comments and labels; never
   overwrite authored text. (An empty fetch + replace once wiped a body at rc=0.)
7. **Never pipe a command into `head`/`tail`** to capture a result.

## Inputs

- **`docs/research/kb/raw/open-issues-2026-09-15.tsv`** — all **335** open
  issues, `#number \t [labels] \t title`, snapshotted this session.
  ⚠️ That count is control-armed: `gh issue list --limit 200` returns 200 and
  `--limit 300` returns 300 — both are BOUNDS. Two independent routes agree on
  335 (`--limit 500`/`1000`, and the search API's `total_count`). Use `--limit
  500` or the API, never a smaller bound.
- `task_plan.md` (read only) — the current phased plan.
- `.agent/plans/session-2026-09-15.md` (read only) — this session's rulings.

## The operator's rulings that constrain the plan

| # | Ruling |
|---|---|
| **Order** | **(1)** land PR #1128 (fix `validate_plugin`, CI green) → **(2)** hk v2 (PR #1090) → **(3)** the devcontainer goal. Ratified in this session's grilling. |
| **Primary goal** | **TWO devcontainers running on this Mac — one amd64, one arm64 — and `/verify` that they run.** The operator chose two over #873's "three images" framing. |
| **agentsview** | **OUT OF SCOPE for this repo's next task** — reassigned to another project. #1014-#1018 must be re-dispositioned accordingly, NOT planned as next work. |
| **hk v2 first** | Deliberate: hk is the lint engine every gate runs through, so bumping it mid-image-work makes a red gate unattributable. |

## Deliverable 1 — the ONE universal devcontainer task

Define a single task that subsumes every open issue about images, architectures,
bake axes and devcontainer bring-up. Known members (verify and extend from the
TSV — 58 titles match the goal surface, and the search API reports 84 issues
mentioning "devcontainer" including bodies):

- **#678** — native ARM64 devcontainer on the Mac. **UNBLOCKED**: #676, #677 CLOSED.
- **#873** — arm64/ubuntu-24.04 image running live. Parent **#849 CLOSED**.
- **#669** — the parent spec (dual-arch substrate), OPEN.
- plus #745, #841, #845, #851, #853, #854, #860, #861, #865, #866, #867, #871,
  #963, #985, #1106, #1121 and anything else the TSV surfaces.

For each: **SUBSUME** (folded into the universal task), **KEEP SEPARATE** (with
why), **CLOSE** (with why), or **BLOCKED-BY** (naming what).

State the universal task as an outcome with **commands and exit codes**, never
adjectives — `.claude/rules/probes-need-a-control-arm.md` and the existing
`task_plan.md` Phase-1 style. The verify surface already exists: `verify-local`,
`verify-arch` (R3), `verify-ssh-inbound` (R1), `verify-container-latest`.

⚠️ #873 warns the images are **deliberately not content-symmetric** — the trunk
compiler snapshot publishes for one architecture only — so smoke assertions must
be architecture-aware or an arm64 leg fails on an artifact that does not exist
upstream. Carry that into the task.

⚠️ #678's sharpest criterion: *"the architecture assertion checks 'the
architecture asked for' rather than a fixed value."* Check whether `verify-arch`
does that today, and say so with `file:line`.

## Deliverable 2 — triage ALL 335

Every open issue gets exactly one disposition. Apply it with `gh`:

- **`needs-triage` (11)** — resolve each; remove the label once dispositioned.
- **unlabelled (107)** — give each at least a type label.
- **duplicates** — close the later one, comment both directions with the link.
- **stale/superseded** — close, citing the commit or issue that superseded it.
- **everything surviving** — map to a phase in Deliverable 3.

Report counts per disposition, and list every issue you CLOSED with its reason.

## Deliverable 3 — the phased plan delta

Write `.agent/plans/task_plan-delta-triage-2026-09-15.md`: the proposed
`task_plan.md` structure, phases in the operator's ratified order, each phase
naming its issues. Quote the exact anchor text you propose replacing so the
coordinator can apply it mechanically.

## Constraints

- Cite `file:line` or `#issue`. An uncited claim is labelled unverified.
- Every negative finding needs a control arm; **invent the known-absent token
  fresh** — tokens from earlier reports are now IN the corpus.
- Run no repository gates (they are the coordinator's).
- If the spec contradicts the repo or itself, STOP and report it. Do not guess.

## PREMISES (verify before relying on them)

| # | Premise | Where |
|---|---|---|
| P1 | 335 open issues, and the TSV holds all of them | `docs/research/kb/raw/open-issues-2026-09-15.tsv`; re-check with `--limit 500` |
| P2 | #676 and #677 are CLOSED, so #678 is unblocked | `gh issue view 676 677` |
| P3 | #849 is CLOSED | `gh issue view 849` |
| P4 | You can actually run `gh` now | run `gh issue view 678` and report whether it worked |
