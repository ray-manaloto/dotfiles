# Stream 4 — Adversarial/cost review: reminders vs gates (cited)

Agent: general-purpose (web, skeptic brief). Findings-bearing; persisted at receipt.

## BLUF
Evidence favors a **hard gate** (PreToolUse deny) as primary; per-turn reminders
are a *secondary* nudge, not a substitute. "Reminder blindness" for LLMs is
**unsupported**; but soft steering **decays** over multi-turn, position matters,
and instruction density lowers compliance.

## Q1 — Do repeated in-context reminders change behavior / habituate?
- **Lost in the middle** (Liu, TACL 2023): U-shaped primacy/recency; mid-context
  info is weakest. *Where* a reminder sits > *whether* it exists.
- **Multi-turn degradation** (Laban et al., MSR, arXiv 2505.06120): avg **39%
  performance drop** when instructions spread across turns vs single-turn;
  models rarely recover after a wrong turn. Strongest argument against relying
  on conversationally-delivered soft guidance.
- **Drift No More?** (arXiv 2510.07777, preprint): drift is BOUNDED not runaway;
  "**simple reminder interventions reliably reduce divergence**." → periodic
  reminders as a corrective ARE supported (secondary layer).
- **Habituation/"reminder blindness" = UNSUPPORTED for LLMs.** That's a human
  notification-UX effect. Prompt-repetition studies (arXiv 2512.14982) find
  repetition *helps* non-reasoning models, with **diminishing returns after ~2
  repetitions**. No evidence a model ignores an instruction *because* it's seen
  it before.

## Q2 — Where should an instruction live to be followed?
- **Instruction hierarchy** (OpenAI, arXiv 2404.13208; Model Spec): System >
  Developer > User > tool/third-party. → a **PostToolUse tool-result nudge is
  the LOWEST-trust tier** (same tier as untrusted web content).
- **System-prompt placement wins** (SCOPE; "Position is Power" 2505.21091):
  highest task accuracy + strongest behavioral pull.
- **Recency**: a `UserPromptSubmit` injection adjacent to the newest turn
  exploits the recency arm — 2nd-best slot (trades privilege for recency).
- Net: durable rules → **system prompt / CLAUDE.md**; per-turn user-adjacent =
  second-best; **PostToolUse tool-result = weakest**.

## Q3 — Costs of per-turn injection
- Token/latency cost mitigable via **prompt caching** ONLY if the reminder is a
  **byte-identical stable prefix**; per-turn variable content breaks the cache.
- Context-window pressure: every injection accretes; a nudge after EVERY command
  is the worst offender (40 commands = 40 mid-context distractors).
- **Over-instruction lowers compliance** (IFScale arXiv 2507.11538; "When
  Instructions Multiply" 2509.21051): monotonic degradation with instruction
  count — a per-turn reminder consumes the finite instruction-following budget.
- **Over-application** ("Position is Power"): an over-emphatic rule → model
  over-applies, e.g. refusing legitimate allowed diagnostics (`git status`).

## Q4 — Hard gate vs soft steering
Engineering consensus: **for a policy that must hold, use a deterministic gate,
not a prompt.** "The model should not be responsible for enforcing its own
constraints." Claude Code hooks are documented as bypass-proof (PreToolUse
`deny` blocks even under `--dangerously-skip-permissions`). Gate has **zero
decay**: turn 1 and turn 200 enforce identically — exactly where soft guidance
fails (Laban §Q1). Soft steering's residual value: the deny **reason string** is
a just-in-time, maximally-relevant nudge that arrives exactly when actionable,
and covers novel shapes the allowlist misses.

## Q5 — Highest-leverage intervention (ranked)
1. **Deterministic PreToolUse `deny` on disallowed shapes (already have).**
   Zero decay, no instruction-budget cost. Keep the reason **specific/actionable**
   ("use `mise run lint`") so the block TEACHES the substitution.
2. **Keep patterns narrow** — over-application is the main failure mode; leave
   diagnostics untouched (our rule already says this).
3. **One durable instruction at high privilege (CLAUDE.md), not fragmented.**
4. **A per-turn `UserPromptSubmit` reminder is a reasonable SECONDARY layer —
   but ONE short, cache-stable, singular line** (Drift-No-More supports it;
   IFScale caps it).
5. **A PostToolUse nudge after EVERY command is lowest-leverage, highest-cost —
   do NOT do the every-command version.** If wanted, make it **CONDITIONAL**
   (fire only when the command matched a soft-warn pattern) → targeted, not
   wallpaper.

## Evidence quality
- Strong/peer-reviewed: Lost-in-the-middle (TACL); Instruction Hierarchy;
  IFScale. Laban multi-turn (MSR, claimed ICLR'26 best paper — verify award).
- Preprint: Drift No More, Position is Power.
- Engineering wisdom (not RCT): hard-gate-beats-prompt (vendor docs +
  practitioner). Mechanism (hooks deterministic) = verifiable fact.
- **Thin:** no study on "does the SAME reminder every turn habituate?" — treat
  "reminders habituate" as unsupported; "reminders help w/ diminishing returns +
  budget cost" as defensible.

## Sources
- Lost in the Middle — <https://arxiv.org/abs/2307.03172>
- LLMs Get Lost in Multi-Turn — <https://arxiv.org/abs/2505.06120>
- Drift No More? — <https://arxiv.org/abs/2510.07777>
- The Instruction Hierarchy (OpenAI) — <https://arxiv.org/abs/2404.13208>
- IFScale — <https://arxiv.org/abs/2507.11538>
- When Instructions Multiply — <https://arxiv.org/html/2509.21051v1>
- Position is Power — <https://arxiv.org/html/2505.21091v2>
- SCOPE — <https://arxiv.org/pdf/2512.15374>
- Prompt Repetition — <https://arxiv.org/html/2512.14982v1>
- Claude Code hooks (deterministic deny) — <https://code.claude.com/docs/en/hooks-guide>
- Anthropic prompt caching — <https://platform.claude.com/docs/en/build-with-claude/prompt-caching>
- Guardrails-as-code — bh3r1th.medium.com/from-harness-to-enforcement... ; dev.to/aws/ai-agent-guardrails-rules-that-llms-cannot-bypass-596d

## GitHub repos touched

- [microsoft/lost_in_conversation](https://github.com/microsoft/lost_in_conversation) — multi-turn degradation study code.
