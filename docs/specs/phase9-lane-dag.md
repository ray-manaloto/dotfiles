# Phase 9 lane DAG — roles, agents, models, effort

Status: RATIFIED with `task_plan.md` Phase 9 on 2026-09-21 (Ray). This file is the source of truth for the graph; a
rendered view of the same graph, with the research-source status and findings tables, is published at
<https://claude.ai/artifact/RwUfffidCMAYdPJ49jYgQc> (private to the operator).

Research and plan only. The one architecture ruling that binds everything below: there is exactly ONE entry point for
offloading work to codex — the `/codex-sdlc-team` skill (arguments only) -> `mise run sdlc-team` -> the python library
`dotfiles_setup.sdlc_team`, which builds the typed request from a code-generated input model. `model` and `effort` are
REQUIRED on that model and have no default. Hooks on both the Claude and the codex side refuse a codex call that bypasses
it. Feature scope for the entry point is the ratified matrix:
`docs/research/kb/reports/agents/feature-matrix-final-2026-09-21.md`.

```mermaid
flowchart TD
  RAY["Ray<br/>rulings, user-level changes,<br/>plan-attest"]:::ray
  ARCH["Architect (this session)<br/>Claude Fable 5.1<br/>specs, routing, refutation"]:::claude

  subgraph PRE["Preconditions (the only code in Phase 9)"]
    P0["9.0 land #1202<br/>codex-sol-implementer, xhigh"]:::codex
    P1["9.1 bump codex 0.154.0 to 0.155.1<br/>mise run lock-shared"]:::gate
    P1B["9.1b app-server daemon gate<br/>auto-update ON (Ray); daemon at or ahead of pin,<br/>never stale; threads + goals survive restart"]:::gate
    P2["9.2 add research mode to<br/>mise run sdlc-team"]:::codex
  end

  subgraph ENTRY["The ONE entry point (skill to mise task to python library)"]
    SK["/codex-sdlc-team skill<br/>params, hints, arguments<br/>judgement only"]:::claude
    MT["mise run sdlc-team<br/>thin task, no logic"]:::gate
    PY["python: dotfiles_setup.sdlc_team<br/>code-generated input model + enums<br/>universal logger, PID tracking<br/>unknown permutation fails closed"]:::gate
    HK["enforcement hooks<br/>Claude function hook + codex hook<br/>refuse any codex call that bypasses this"]:::gate
  end

  DISP["sdlc-dispatcher<br/>model + effort REQUIRED on the input model, no defaults<br/>routes, waits, never edits"]:::codex

  subgraph TEAM["codex SDLC specialists (effort high, research mode)"]
    S1["sdlc-documentation-specialist<br/>9.5 herdr setup + verify<br/>9.8 offline docs to KB sources/"]:::codex
    S2["sdlc-python-specialist<br/>9.6 herdr as claude-codex channel<br/>9.7 unified skill design"]:::codex
    S3["sdlc-config-specialist<br/>9.4 codex CLI flag contract<br/>9.9 codex currency"]:::codex
    S4["sdlc-workflows-specialist<br/>9.9 Renovate / refresh wiring"]:::codex
  end

  V["9.3 verify-then-use<br/>every source in the table below:<br/>context7, exa, firecrawl, last30days,<br/>agentsview, graphify; one live call + control arm each"]:::gate
  HIST["History first<br/>agentsview + repo inventory<br/>Claude Sonnet, read-only"]:::claude

  PV["premise-verifier<br/>Claude, read-only"]:::claude
  COLD["cold-reviewer<br/>Claude Opus, by ref"]:::claude
  SETTLE["SdlcTeamSettlement<br/>claimed vs rollout-observed,<br/>fails closed"]:::gate
  OUT["3 reports + ratified plan<br/>+ Mermaid spec + this page"]:::gate

  RAY --> ARCH
  ARCH --> HIST --> ARCH
  ARCH --> P0 --> P1 --> P1B --> P2 --> V
  ARCH -- "skill args only" --> SK --> MT --> PY
  PY -- "generated typed request" --> DISP
  HK -. guards .-> PY
  INV["9.11 agentsview inventory of<br/>every codex call to date"]:::claude --> PY
  V --> DISP
  FR1["9.6b reviewer 1<br/>Claude Fable agent<br/>reads both predecessors end to end"]:::claude
  FR2["9.6b reviewer 2<br/>codex-astra-advisor, gpt-6-astra, xhigh<br/>independent, same brief"]:::codex
  FM["reconciled feature matrix<br/>keep, migrate, enhance, drop<br/>disagreements shown"]:::gate
  ARCH --> FR1 & FR2
  FR1 & FR2 --> FM --> PV
  FM -- "final matrix for ruling" --> RAY
  FM -- "gates 9.7 skill design" --> S2
  DISP --> S1 & S2 & S3 & S4
  S1 & S2 & S3 & S4 --> SETTLE --> ARCH
  ARCH --> PV --> ARCH
  ARCH --> COLD --> ARCH
  ARCH --> OUT --> RAY

  classDef ray fill:#ede6f7,stroke:#5b3f8c,color:#22162f
  classDef claude fill:#f8e9dc,stroke:#9a4a16,color:#2e1705
  classDef codex fill:#dcf0f1,stroke:#0f5f66,color:#06262a
  classDef gate fill:#f4efcf,stroke:#7a6a12,color:#2a2404
```

## Roster

| Role | Agent | Model | Effort | Writes |
|---|---|---|---|---|
| Operator | Ray | — | — | user-level skills, codex plugin enablement, `plan-attest` |
| Architect | the coordinating Claude session | Claude Fable 5.1 | session | `task_plan.md`, specs, rulings |
| History | read-only Claude agents | Claude Sonnet | default | reports only |
| Router | `sdlc-dispatcher` | required on the input model | required | nothing |
| Research | `sdlc-documentation` / `python` / `config` / `workflows-specialist` | required on the input model | required | reports + raw sources (`research` mode, plan 9.2) |
| Precondition code | `codex-sol-implementer` | gpt-5.6-sol | xhigh | branch commits |
| Predecessor review | a Claude Fable agent + `codex-astra-advisor` | Claude Fable 5.1 / gpt-6-astra | default / xhigh | one report each |
| Premise check | `premise-verifier` (to be re-homed repo-owned) | Claude | default | nothing |
| Cold review | `cold-reviewer` | Claude Opus | default | its report |

Today the six `.codex/agents/codex-sdlc-*.toml` files pin `model_reasoning_effort = "high"` and declare no `model`; whether
a request-level effort reaches the specialists is unmeasured (matrix row A5, plan 9.4).

## Why the families are split

Codex does the volume. Claude keeps the two checks that only work from a different model family than the implementer:
premise verification before dispatch and cold review after. On #1202 those caught a hand-maintained duplicate file, a
verdict refresh that could disarm the gate, and a test-harness artifact reported as a production bug.

## GitHub repos touched

_None._ The graph is derived from `task_plan.md` and the reports it cites.
