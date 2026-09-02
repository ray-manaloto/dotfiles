# Lane briefs index — session 2026-09-02c (`dotfiles-20260902.000`)

Per `.claude/rules/agent-report-persistence.md` §5: every findings-bearing lane
maps BOTH its brief and its report to an artifact. #601's seven review rounds
lost all seven briefs to an ephemeral scratchpad — the reports survived, the
questions that produced them did not. This file is the brief half.

| Lane | Brief — the question it was given | Report |
|---|---|---|
| `premise-verifier` (ITEM 11 r1) | Verify the PREMISES block of the first schema spec; hunt unlisted premises, especially `.claude/settings.json` readers that could break on a new top-level key, and any gate asserting a byte/line/first-line count on the twelve candidate files | `2026-09-02-premise-verify-item11.md` |
| `taplo-research` | Does taplo cache schemas on disk and where; what offline/no-network flags exist and do they kill validation too; can a `.taplo.toml` associate schemas by glob; can taplo point at a vendored local schema; 2-4 public repos showing how they handle it in CI | `2026-09-02-taplo-schema-network.md` (⚠️ architect correction prepended — its `--offline` flag and disk-cache claims are REFUTED) |
| `premise-item11-r2` | Re-verify the REWRITTEN spec's premises (all rows new); read r1's report first since its M2 forced the rewrite; hunt position-sensitivity in other parsers of the six TOML files, and any first-line/byte-count assertion | `2026-09-02-premise-verify-item11-r2.md` |
| `item11-impl` | Implement the vendored-schema spec (`SPEC FILE:` pointer, xhigh, `COMMIT: lane`), then 3 respec rounds: the 5 cold-review fixes; hold the typos half; apply the verified scoping config | **N/A — implementer lane.** Its value is its commits (`96d7067`, `4f1d527`, `0b5dd99`, `3c4a3ca`), not findings. Structured CODEX REPORTs quoted in the handoff. |
| `item11-codex-review` | Cold review `96d7067` vs `df95413`, intent withheld. Is the byte-verbatim claim substantiated; can any check only pass; is the new PR-opening job's permission/trigger/failure behaviour correct; are the three scanner exclusions scoped to what they claim; what behaves differently with and without network | `2026-09-02-cold-review-item11-codex.md` |
| `item11-opus-review` | Same ref, cross-family lens, briefed at OMISSION-type defects: every error/empty/missing/timeout/no-network branch; a state where a gate reports success having validated nothing; what the change did NOT do; the CI job's unhappy paths; whether each new test would still pass if its behaviour were reverted | `2026-09-02-cold-review-item11-opus.md` |
| `typos-scoping-research` | Can typos scope an allowlist per-file or per-glob rather than project-wide; what `[type.<name>]` does; in-file directives; `[files] extend-exclude`'s real cost; rank the options | `2026-09-02-typos-scoping.md` (⚠️ architect correction prepended — its recommended config returns rc=2) |
| `injection-facts` | Is `paths:` real or aspirational and WHEN does it load; which hook events inject to the MODEL and which carry a file path; is once-only native or hand-built; deny-rule vs hook-deny authority; does `FileChanged` fit; the Codex equivalent; and what this repo ALREADY has | `2026-09-02-path-scoped-injection-facts.md` |
| `rule-scoping-practices` | Is path-scoping actually best practice or a local idea; is there a published heuristic like our trigger test; how do real setups avoid injection spam; enforcement layering; the Codex equivalent; and **is there any measured claim that instruction volume affects adherence** | `2026-09-02-rule-scoping-practices.md` |
| `prior-injection-research` | Mine this repo's OWN prior work: pwf's dedup design, the ~19.7% eager-corpus audit and its uncut remainder, existing hook state conventions, related issues, and `paths:` git history — flagging anything that CONTRADICTS the forming plan | `2026-09-02-prior-injection-research.md` |
| `logger-history` | Was structlog (or another logging library) previously DECIDED; implemented, partial, or reversed? A reversal we do not know about would make "adopt structlog" actively wrong. Control-arm any null result | `2026-09-02-logging-library-history.md` |

## Two lanes reported mechanisms that do not exist

`taplo-research` claimed a `--offline` flag and a working disk cache; both
refuted by measurement. `typos-scoping-research` claimed a control-armed config
that returns rc=2. **Both cited real source code.** Their persisted reports each
carry a prepended `ARCHITECT CORRECTION` with the measured arms. The pattern —
lanes read source competently and report what SHOULD happen, with the "I tested
it" claim being the part that fails — is recorded in `.agent/notepad.md`.

## GitHub repos touched

- [OthmanAdi/planning-with-files](https://github.com/OthmanAdi/planning-with-files) — upstream defects #237, #238, #239 filed against it this session.
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — this repo; issues #911, #912 filed.
