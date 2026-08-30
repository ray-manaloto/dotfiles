# Research: /grilling → /to-spec → /to-tickets → /implement compliance for #736

## Q1 — `/to-tickets`: input, output, triage

**Input**: not a specific issue shape — "Work from whatever is already in the conversation context. If the user passes a reference (a spec path, an issue number or URL) as an argument, fetch it and read its full body and comments." (`to-tickets/SKILL.md:15-17`). So it can consume the conversation directly OR a spec issue reference; it does not require the spec to carry any particular label to be accepted as input.

**Output**: "tracer-bullet vertical slices, each declaring the tickets that **block** it" (`to-tickets/SKILL.md:9`). Each ticket: Title, Blocked by, What it delivers (`to-tickets/SKILL.md:46-48`), then quizzes the user on granularity/blocking edges before publishing (`to-tickets/SKILL.md:42-56`).

**Triage**: yes, it applies triage itself on publish — "Apply the `ready-for-agent` triage label unless instructed otherwise — the tickets are agent-grabbable by construction." (`to-tickets/SKILL.md:63`). This is a real-tracker-only step (the local-file path has no label, just `**Status:** ready-for-agent` text in the per-ticket template, `to-tickets/SKILL.md:77`). So `/to-tickets` does its own labelling; it doesn't require a separate triage pass on its own output for GitHub. (Repo convention: `docs/issue-tracker.md:19-21` names the chain as `/wayfinder → /to-spec → /to-tickets → /triage / /implement` — `/triage` sits as an *alternative* branch alongside `/implement`, not a mandatory gate between `/to-tickets` and `/implement`.)

Also: "Do NOT close or modify any parent issue." (`to-tickets/SKILL.md:67`) — relevant if #736 is being kept open as the parent and tickets are children.

## Q2 — `/implement`: input, model/lane guidance

Full skill body (`implement/SKILL.md:1-16`) is four lines of process, no more:
```
Implement the work described by the user in the spec or tickets.
Use /tdd where possible, at pre-agreed seams.
Run typechecking regularly, single test files regularly, and the full test suite once at the end.
Once done, use /code-review to review the work.
Commit your work to the current branch.
```

**Input**: "the spec or tickets" (`implement/SKILL.md:7`) — deliberately either/or, no schema requirement beyond that. It does not require both; a spec alone or tickets alone both qualify as valid input.

**Lane/model choice**: the skill says NOTHING about implementation lane, model, or which CLI/agent should drive it. That entire layer (fable-orchestrator's codex/grok lane routing, `codex effort = xhigh`) is this repo's own bolt-on, declared in `.claude/CLAUDE.md`'s "Cross-vendor orchestration" section, not part of the mattpocock-skills `implement` skill at all. The skill is lane-agnostic; the orchestration doctrine sits entirely outside it.

The skill does prescribe: TDD at pre-agreed seams, regular typechecking + single-test runs, one full-suite run at the end, a `/code-review` pass, then commit to the current branch — no mention of PR creation (this repo's `mise run ship` fills that gap per `mise-tasks-only.md`).

## Q3 — `/prototype`: when it runs, relevance to #736

Per `wayfinder/SKILL.md:78`: prototype is a **HITL** ticket type, invoked when "how should it look" or "how should it behave" is the key question — i.e. it answers a design-fidelity question, not a general planning step. `prototype/SKILL.md:14-16` picks one of two branches:
- `LOGIC.md`: "Does this logic / state model feel right?"
- `UI.md`: "What should this look like?"

There is no third branch. Its own description frontmatter: "Build a throwaway prototype to answer a design question... sanity-check whether a state model or logic feels right, or explore what a UI should look like." (`prototype/SKILL.md:3`)

**Ordering**: it is NOT a required stage before `/to-spec`. `wayfinder/SKILL.md` treats it as one of four *ticket types* (Research/Prototype/Grilling/Task) resolved during map-charting when a specific question warrants it — parallel/optional, not sequential-mandatory. `to-spec/SKILL.md:57` only references it as an *optional exception* for encoding a decision precisely ("if a prototype produced a snippet that encodes a decision more precisely than prose can... inline it... note briefly it came from a prototype") — i.e. `/to-spec` accepts prototype output if one already happened, but does not require one.

**Relevance to #736**: per your framing, #736 is a CI/build-matrix infrastructure change (permanent 3-leg build matrix, OS-qualified tags, non-blocking arm64/ubuntu-26.04 leg) — not a state-model or UI question. Neither `LOGIC.md`'s nor `UI.md`'s trigger condition applies. `/prototype` should be skipped for #736; nothing in the chain requires it, and its own trigger conditions don't match this task's shape.

## Q4 — Best-practice gaps: infra spec vs `/to-spec`'s template

Template sections, verbatim (`to-spec/SKILL.md:21-75`): Problem Statement, Solution, User Stories, Implementation Decisions, Testing Decisions, Out of Scope, Further Notes.

The skill's own process notes (steps 1-2, `to-spec/SKILL.md:11-19`) are written in application-feature language: "Sketch out the seams at which you're going to test the feature... Check with the user that these seams match their expectations," and step 3 says apply `ready-for-agent` after writing.

**The section most likely to go thin or get faked for infra work is "User Stories."** The template's own instruction is explicit and feature-shaped: *"A LONG, numbered list of user stories... `1. As an <actor>, I want a <feature>, so that <benefit>`... This list... should be extremely extensive and cover all aspects of the feature."* (`to-spec/SKILL.md:31-41`) with a worked example about a "mobile bank customer." The skill has no infra/CI-specific variant or exemption — it implicitly assumes an end-user-facing feature with a human actor. For a build-matrix/CI change, the "actor" is really "the maintainer" or "CI itself," and a session under time pressure either (a) pads the list with strained pseudo-user-stories ("As a maintainer, I want a 3-leg matrix, so that...") that don't actually stress-test anything, or (b) skips/shrinks the section — both are gaps against the template's own stated bar ("extremely extensive... all aspects").

Two other likely gap points for infra specs specifically:
- **Implementation Decisions** explicitly forbids file paths/snippets ("Do NOT include specific file paths or code snippets. They may end up being outdated very quickly," `to-spec/SKILL.md:55`) — but infra specs (build matrices, workflow YAML) tend to be described in terms of exact file/job names because that IS the domain vocabulary; a session has to translate concrete CI job/leg names into decision prose without leaning on paths, which is an easy rule to violate by habit.
- **Testing Decisions** asks for "prior art for the tests (i.e. similar types of tests in the codebase)" (`to-spec/SKILL.md:65`) — for a build-matrix change, "tests" means CI runs/smoke tiers, not unit tests, and a session may under-fill this section if it defaults to thinking about test files rather than the repo's actual verification surface (`mise run verify`, smoke tiers, `verify-container-latest`) named in this repo's own `AGENTS.md`.

The template does NOT have an infra-specific exemption anywhere in the skill file — it is one template for all specs.

## Q5 — New issue vs updating an existing one

The skill's own wording, verbatim: **"Write the spec using the template below, then publish it to the project issue tracker."** (`to-spec/SKILL.md:19`) and the repo convention: **"When a skill says 'publish to the issue tracker' → Create a GitHub issue."** (`docs/issue-tracker.md:76-78`)

Neither says "create a NEW issue" explicitly, nor does either say "update an existing issue." The skill's verb is "publish," and this repo's own translation of that verb is unconditionally "Create a GitHub issue" — it does not branch on whether a related issue already exists. So per the literal skill + repo-doc text, `/to-spec` publishing onto an issue that already tracks the same feature (#736) is **not directly addressed** — the documented behavior is "create," not "update in place." Nothing in `to-spec/SKILL.md` or `docs/issue-tracker.md` licenses reusing/rewriting an existing issue body as the spec's target, and nothing forbids it either — it is simply unaddressed. This is a genuine gap between the documented process and the session's plan to reuse #736; if #736 already exists and was "freshly rewritten for this exact feature earlier in this session" (per L1/L2 premises), that predates and is external to what the `/to-spec` skill text itself specifies.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the target repo whose `docs/issue-tracker.md` and `docs/triage-labels.md` were read for repo-specific tracker conventions.

_No other repos' source was consulted — all skill files read are local plugin-cache files, not fetched from GitHub._
