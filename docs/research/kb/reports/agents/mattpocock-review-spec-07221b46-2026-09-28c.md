# Spec review — 07221b46 vs docs/specs/s28b-0-audit-fix-now.md

Scope: `git diff 07221b46~1...07221b46` (one commit, 45 files). H9/T12/T15 are absent from the diff, as required.
H1 short form and H23's `N` are accepted deviations. H1 still holds for the value that ships. Renovate's regex
`CLANG_P2996_REF["= ]+<sha>` (`renovate.json:132`) cannot match bake's `variable "CLANG_P2996_REF" {\n default = …`
(`docker-bake.hcl:100-101`). Nit: the regex still matches the Dockerfile `ARG` (`:426`), so Renovate CAN move that dead
default. That is the divergence #1434 describes, and H2's comment says it exactly.

## (a) Missing / partial

1. **C4 is not in the PR.** Spec: "Persist `.agent/logs/codex-review-handoff-branch.log`'s final message verbatim as
   `…/codex-review-lens-p2996-branch-2026-09-28.md` (new path; include it in this PR)." `git ls-tree` at 07221b46 has
   no such file, and it is not untracked on disk either. It is a coordinator action, but the spec binds it to this PR.
2. **§5 step 10** (the H10 live arm, both arms, rc recorded) and **C5** (`codex-schema-check`) have no evidence in the
   diff. They may exist outside it, but this review cannot confirm them.

## (b) Scope creep

None of substance. Two new report files (`codex-sol-implementer-s28b-0-…`, `spec-scribe-s28b-0-…`) appear under the
reports tree. §4 says "No file under `docs/research/kb/reports/agents/` is modified". These are new files, not
modifications, and `agent-report-persistence.md` requires them. §4 contradicts H7b; Ruling Q1 wins, and the 23d briefs
file is untouched.

## (c) Implemented but wrong

1. **H5's mirror output is self-referential (MEDIUM).** Spec H5: "A standing advisor lane (codex gpt-5.6-sol; its astra
   twin is equivalent, neither is the default)". `codex-lane-mirror` copied "astra twin" verbatim, so
   `.claude/agents/codex-astra-advisor.md:4` now reads "codex gpt-6-astra; its astra twin is equivalent". The same holds
   for `.codex/agents/codex-astra-advisor.toml` ("its astra twin is equivalent"). The astra lane now names itself as its
   own twin. Fix: a neutral phrase in the sol source, such as "its sol/astra twin is equivalent" or "neither sol nor
   astra is the default", then re-mirror.
2. **H21 (LOW).** "~~…(~2.5 h cold in CI)~~ — refuted…; weigh cadence against that cost." After the strike-through,
   "that cost" has no antecedent. The review (`sdlc-team-p2996…md:141`) gives 80–120 min cold for the compiler/final
   tiers; name that figure.
3. **H10 (LOW).** The control arm uses `$S` (`cp .plan-attestation "$S/att.bak"`), and the recipe never defines it.

Verified correct, both arms:

- H19: `--comments --json` exits rc=1 with "specify only one of --comments or --json". Non-TTY `--comments` omits the
  title (0 hits); the control without `--comments` gets 1 hit.
- H8: the regex matches `## 2026-09-28 —` and not `## 2026-09-28b —`.
- H16/H23: the literals are at `sync.py:879-890` and `pr.py:612,910`.
- H24: the grep counts 46 (control: 320 `[tools.` tables).
- A3: confirmed by `sdlc-team-p2996…md:141`.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — spec, diff, #1434 read-only via `gh issue view`
