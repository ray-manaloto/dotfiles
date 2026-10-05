# Review brief: is the coord-router evidence good enough to build the router agent? (2026-10-04)

Ray (2026-10-04, verbatim): "/codex-sdlc-team to review and provide cited
proposal". He was answering this side-agent caution:

> The "58% could go to a specialist" figure is a rough upper bound from a
> small, skewed sample, not a measured saving … It assumes a perfect sorter
> … The sample took the first ~6 messages from each coordinator session …
> One reviewer labelled everything, with no second check … look at the
> offline classifier test … Its numbers for how often messages get routed and
> how often they get misrouted are the real measure.

## 1. Objective

Produce a CITED proposal that answers four questions:
(1) What do the existing measurements support, and what do they not support?
(2) Is the router agent (Ray's ruling "Router agent session") worth building
given those numbers, or should a cheaper alternative come first?
(3) What is the smallest additional measurement that would settle (2)?
(4) What should the spec and report say instead of anything they overstate?

## 2. Files (allowlist; edit only these)

- `docs/research/kb/reports/agents/coord-router-evidence-review-2026-10-04.md`
  (new: the cited proposal, ending with `## GitHub repos touched`)

## 3. Evidence to read (all in this worktree unless absolute)

- `docs/research/kb/raw/coord-router/inbound-sample-2026-10-04.jsonl`: 171 rows, 163 primary.
- `docs/research/kb/reports/agents/coord-router-freetext-2026-10-04.md`: sampling method, rubric, tier table.
- `docs/research/kb/raw/coord-router/classifier-eval/{predictions.jsonl,score.txt,rubric-and-format.txt}`
  and report `coord-router-research-2026-10-04.md` §9: sonnet ≥0.80 gives
  11.0% offload with 0.6% misroute; ungated 36.2% offload with 11.7% misroute;
  haiku "Prompt is too long".
- `docs/research/kb/reports/agents/coord-router-inventory-2026-10-04.md`: duty
  inventory and handoff weight. It shows that ~38% of handoff lines exist
  because the coordinator holds state. That load is separate from message
  routing.
- `docs/specs/coord-router-2026-10-04.md` rev 3: chain, specialists S4,
  rulings, spec-04 custody section.
- Coordinator transcripts, read-only:
  `~/.claude/projects/-Users-rmanaloto-dev-github-ray-manaloto-dotfiles/*.jsonl`.
  Peer messages are `type=attachment`, `attachment.type=queued_command`,
  `origin.kind=peer`, body `attachment.prompt`. Use them only for counting,
  such as whole-day traffic volume and the position-in-session distribution.
  Never copy bodies into the report.

## 4. Constraints

- READ-ONLY except the one allowlisted report. Do not run pytest, lint,
  verify or any mise gate. Do not push. Do not spawn Claude sessions. Do not
  edit the spec.
- Every claim cites a file:line, a command with its exit code, or a URL.
  A count must name the command that produced it.
- Separate the two benefits:
  - (a) fewer coordinator TOKENS from routing messages;
  - (b) a smaller coordinator HANDOFF from moving STATE to specialists (S4).
  These can have different value. Say which numbers bear on which.
- Rulings bind: build on PR2; router agent session; batcher plus watcher;
  containers out of scope; Q3 "neither"; one shipper per repo; one heavy
  slot host-wide; spec-04 command-id custody.
  Licensed dissent is welcome, but it must cite evidence.
- Print presence, never values, for any credential.

## 5. Verification

- The report states, for each statistic it relies on:
  - the denominator;
  - the sampling frame;
  - its bias direction;
  - a confidence interval or an explicit "no interval: n too small".
- The report includes at least one measured whole-population count (for
  example total peer messages to coordinators on 10-03/04, and the share that
  arrive in the first six of a session), with the counting command and its
  rc.
- Control arm: that counter finds the known message id
  `f6f25455-60c8-4b52-9ee5-4317b5d0b0a5`.

## 6. Commit

caller.

## 7. PREMISES

- L 163 primary / 94 specialist-labelled / 27 sessions:
  `coord-router-freetext-2026-10-04.md` "Current corpus" section.
- L sonnet ≥0.80 is 18 routed / 1 wrong out of 163:
  `classifier-eval/score.txt`.
- E the classifier saw only `text_first_300`, while labels came from full
  bodies: report §9.
- A the per-session first-six prefix is unrepresentative of whole-day
  traffic. Test this; do not assume it.
