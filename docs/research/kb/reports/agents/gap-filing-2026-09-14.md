# Gap filing — session 2026-09-14e (issue-filer)

**Lane:** issue-filer (write-capable: `gh issue create`/`gh issue comment` only,
`-R ray-manaloto/dotfiles` explicit on every call).
**Source:** `docs/research/kb/reports/agents/coverage-sweep-2026-09-14.md`,
"THE UNTRACKED LIST" section (A1-A9), per team-lead brief with `FILE ISSUES: yes`.

## Method

For every item, re-ran the coverage-sweep's control-armed search
(`gh issue list -R ray-manaloto/dotfiles --state all --search "<term>"`) against
live issue state before drafting, to catch any duplicate filed since the sweep
ran. Every `file:line` anchor cited in a drafted body was re-read from the
current working tree before filing (not trusted from the source report).

## Result table

| Item | Action | Result |
|---|---|---|
| A1 (renovate matchFileNames) | New issue | **#1116** |
| A2 (pin-parity blind spots) | New issue | **#1117** |
| A3 (doctor.toml contradiction) | New issue | **#1118** |
| A4 (claude-pin decision, #1043 stale) | Comment on existing issue (per brief — NOT a new issue) | **comment on #1043** — https://github.com/ray-manaloto/dotfiles/issues/1043#issuecomment-5672459329 |
| A5 (advisor `<scope>` collision) | New issue | **#1119** |
| A6 (one-hook-per-event gate) | New issue | **#1120** |
| A7 (lock_shared.py bring-up/timeout) | New issue | **#1121** |
| A8 — one-off frequency gate | New issue (prerequisite #266 named, not a duplicate) | **#1122** |
| A8 — require_control_arm handler | New issue | **#1123** |
| A8 — session-start guard-health probe | New issue | **#1124** |
| A9 (parallelization question unanswered) | New issue | **#1125** |

A8's other two proposals (TS hook budget, tool pin sync) were confirmed already
covered — **#1101** and **#1094** respectively — and were NOT re-filed, per the
brief. A8's guard-fail-open-visibility proposal was confirmed covered by
**#1057/#1096/#1097** and also not re-filed.

## Control-arm verification performed before filing

Every term below returned **0** open+closed issue hits before filing (fresh
control terms not reused from any prior report, since a published control
string stops discriminating once it's in the corpus):

- `matchFileNames` (A1) — control-present: `renovate.json` -> 12 hits.
- `expected_install_method`, `check_one_process_per_event`, `matchers_exact`,
  `require_control_arm` (A3, A6, A8) — all 0; control-present terms `pin_parity`
  search variants and `1094` (known to appear in #1095's title context)
  confirmed the search mechanism discriminates.
- `advisor-scope` / `codex-sol-advisor` (A5) — non-matching hits returned (none
  about the fallback-path collision specifically); confirmed genuinely
  uncovered by reading #1112's and #1114's bodies directly.
- `lock_shared` (A7) — one loose hit (#993, the modernization epic, not about
  this defect).
- `one-off frequency`, `watchdog`, `guard health`, `hook runner`,
  `parallelization-plan` (A8, A9) — checked against #266, #1057/#1096/#1097,
  #1101, #1094, #1112, #994 by reading each body; none covers the specific
  proposal filed.

## Anchor corrections made while drafting

- A1: confirmed `ci.yml:287-288` lists `hk-common.pkl`/`hk-image.pkl` as build
  inputs, `hk.pkl` is not (matches report).
- A3: confirmed `doctor.toml:264` / `:248-263` and `claude_doctor.py:66,
  229-238` verbatim.
- A4: confirmed the live pin is `mise.toml:43` (not `:26`, which the original
  #1043 text still cites for the retired npm pin); confirmed the `mise exec
  "github:anthropics/claude-code@2.1.270" -- claude --version` -> 2.1.270 rc=0
  claim structurally (not re-run live in this lane — carried from the source
  report's own measurement, cited as such).
- A7: confirmed `lock_shared.py:298-305`'s `subprocess.run` call has no
  `timeout=` kwarg, and `grep -n "mise run up" lock_shared.py` -> 0 hits.
- A9: confirmed `git branch --list 'adv/*'` still shows
  `adv/parallelization-plan-2026-09-14` locally; `git diff main
  adv/parallelization-plan-2026-09-14` is empty (branch currently matches
  `main` at the point it was cut — noted as a minor correction to the source
  report's "uncommitted work" framing, which likely referred to session-local
  scratch state rather than the branch's own commits).

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — every
  issue create/comment call above; re-read `renovate.json`, `pin-parity.toml`,
  `.github/workflows/ci.yml`, `doctor.toml`,
  `python/src/dotfiles_setup/claude_doctor.py`,
  `python/src/dotfiles_setup/lock_shared.py`,
  `.claude/agents/codex-{sol,astra}-advisor.md`,
  `docs/research/kb/reports/agents/adv-hook-consolidation-2026-09-14.md`,
  `docs/research/kb/reports/agents/watchdog-rules-2026-09-14.md`,
  `docs/research/kb/reports/agents/adv-goal-review-2026-09-14.md`, and issues
  #1043, #1057, #1063, #1079, #1090, #1093, #1094, #1096, #1097, #1099, #1100,
  #1101, #1112, #1113, #1114, #266, #994.
