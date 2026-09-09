# Brief — cold review of the S1b smoke-test fix (commit `2669d64`)

Persisted per `.claude/rules/agent-report-persistence.md`, which puts the
**brief** in scope alongside the report: #601's seven review rounds left all
seven briefs in an ephemeral scratchpad, so the reports survived but the
questions that produced them did not.

- **Lane:** `fable-orchestrator:codex-reviewer` (GPT-5.6 Sol via the `codex` CLI).
- **Why that lane:** the diff was Claude-authored, so an Opus cold pass would
  have been same-family. Per `.claude/CLAUDE.md`, either CLI reviewer qualifies
  as the cold lens for a Claude-authored diff; `grok` is not installed here.
- **Report:** `docs/research/kb/reports/agents/2026-09-08-cold-review-s1b.md`
- **Outcome:** no defects blocking ship. One inherited (not introduced)
  `always()`/cancelled exposure → issue #981.

## The brief, verbatim

> Cold review one commit. Do NOT ask what it is for — judge only what the code does.
>
> REF: commit `2669d64` on branch `fix/smoke-test-always-runs-s1b` in
> /Users/rmanaloto/dev/github/ray-manaloto/dotfiles
> Read it with: `git show 2669d64`
>
> Two files change: `.github/workflows/build-publish.yml` and
> `python/verification/suites.toml`.
>
> SCOPE — answer these, and stop:
>
> 1. Does the added `if:` on the `smoke-test` job do what the YAML says it does,
>    under real GitHub Actions job-condition semantics? Specifically: with the
>    default implicit `success()` replaced by this explicit expression, is any
>    FAILURE path now let through that was previously gated? Enumerate the
>    upstream result combinations (`plan` and `build` each: success / failure /
>    skipped / cancelled) and say for each whether `smoke-test` runs, and whether
>    that is correct. Pay attention to `cancelled()` — the commit message does not
>    mention it.
>
> 2. `build` is a matrix job with `continue-on-error: ${{ !matrix.target.blocking }}`
>    and one leg is known-red. Does `needs.build.result == 'success'` still hold
>    when that leg fails? Verify against the actual `continue-on-error` semantics
>    for matrix legs, not from memory — cite where you confirmed it.
>
> 3. The two contract tokens in `suites.toml`. For EACH, determine independently
>    how many places in `.github/workflows/build-publish.yml` match it. State the
>    count you measured and the command you measured it with. Then answer: could
>    the contract be satisfied by a site OTHER than the smoke-test job's `if:` —
>    including by a comment, or by the `manifest` job? If a token is over- or
>    under-anchored, say which and why.
>
> 4. Downstream: `dev-tag` (`if: needs.smoke-test.result == 'success'`) and
>    `manifest`. Now that `smoke-test` can RUN in states where it previously
>    skipped, is there any state where `smoke-test` ends `failure` or `cancelled`
>    and a downstream job proceeds when it should not — or conversely stays
>    skipped when it should run? Read the real conditions in the file.
>
> RULES
> - Every claim carries a `file:line` or a command + its output. An uncited claim
>   must be labeled UNVERIFIED.
> - A negative finding needs a control arm: before reporting "X does not appear",
>   run the same probe shape against something you know IS present and say so.
> - Do not propose a rewrite. Report defects.
> - If you find nothing in a numbered area, say "no finding" for that number
>   rather than padding.
>
> PERSISTENCE — do this INCREMENTALLY, not at the end:
> Write your report to
> `docs/research/kb/reports/agents/2026-09-08-cold-review-s1b.md`
> as you go. Create it with your first finding; update it after each numbered
> area. Do not hold findings in memory to write up at the end. End the file with
> a `## GitHub repos touched` section.
>
> Then SendMessage your findings list back to me as your LAST action, before going
> idle. Text you emit without SendMessage does not reach me.

## What the brief shape bought

Two things worth reusing, both of which produced findings the author had not
asked for directly:

1. **Naming the thing the commit did NOT mention** ("Pay attention to
   `cancelled()` — the commit message does not mention it") surfaced the one
   real exposure, and the reviewer went further and established it was
   *inherited*, which is what kept it out of this PR and into #981.
2. **Asking for an INDEPENDENT re-measurement** of the token counts, rather
   than "confirm the tokens are unique", produced the control arm that proved
   the `strategy:` anchor load-bearing rather than merely restating the claim.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the repo under review.
