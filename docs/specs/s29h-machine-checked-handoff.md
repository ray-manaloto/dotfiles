# S29-H — machine-checked PR claims + generated handoff state

Ruling: Ray, 2026-09-29b-late (AskUserQuestion), `task_plan.md` § Current Phase "RULING 2026-09-29b-late" + its
ADDENDUM ("catch it by machine rather than by a model's round-trip should ALWAYS be the protocol").
Root cause: `findings.md` § "2026-09-29b — root cause: stale PR state in task_plan.md at handoff (repeat offender)".

## 1. Objective

A session handoff and the plan's active section state PR facts in prose ("#1454 … (auto-merge armed)",
"#1449 auto-merge"). Nothing compared that prose to GitHub, so a merged PR kept reading "armed" and a RED PR kept
reading "auto-merge" until a model round-trip happened to notice (twice: 2026-09-29 #1449, 2026-09-29b #1454).

Outcome:

- **(a)** `mise run handoff-check` extracts every PR/issue state claim from the handoff AND from the active section
  of `task_plan.md`, fetches the live facts from GitHub, and fails (`rc=1`) on any claim GitHub contradicts. A GitHub
  lookup that fails is a finding (`pr_claim_unverifiable`, `rc=1`) — never a pass.
- **(b)** `mise run session-state` also lists the repo's open PRs and the PRs merged since the previous handoff, each
  rendered in the SAME claim vocabulary (a) parses, so a State section pasted from it verifies itself.

## 2. Files

Create:

- `python/src/dotfiles_setup/pr_facts.py` — the shared GitHub layer (bounded `gh` runner, check classification,
  `PrFacts`, `fetch_facts`). Exists so `handoff_check` and `session_state` share it without an import cycle.
- `tests/test_pr_facts.py`

Modify:

- `python/src/dotfiles_setup/handoff_check.py`
- `python/src/dotfiles_setup/session_state.py`
- `python/src/dotfiles_setup/main.py` — only the `session-state` parser/dispatch (`--since`), ~:1530-1538 and ~:2816-2818.
- `tests/test_handoff_check.py`, `tests/test_session_state.py`
- `mise.toml` — the `description` strings of `[tasks.session-state]` (:1006) and `[tasks.handoff-check]` (:1016) only.

Do NOT touch: `task_plan.md` (coordinator-only), `.plan-attestation`, `.claude/**`, `.agents/**`, `docs/**` (the architect already
edited the skills and the rule line and regenerated the `.agents/` mirror before dispatch; goal-history follows), `findings.md`/`progress.md` except append-only.

## 3. Interfaces

### `pr_facts.py`

```python
GH_TIMEOUT = 120

def run_gh(args: list[str], repo_root: Path) -> tuple[int, str]:
    """Moved verbatim from session_state._gh (session_state.py:144-163): rc 0 -> stdout;
    TimeoutExpired -> (124, "gh lookup timed out"); OSError -> (127, str(exc));
    else (rc, stderr or stdout or "no diagnostic"). env=child_env.without_git_context()."""

class CheckBucket(Enum):  PASS = "pass"; FAIL = "fail"; PENDING = "pending"

def classify_check(check: dict[str, object]) -> CheckBucket:
    """value = check.get("conclusion") or check.get("state") or check.get("status"), upper-cased.
    PASS: SUCCESS, NEUTRAL, SKIPPED, PASS (the set at session_state.py:174).
    FAIL: FAILURE, ERROR, CANCELLED, TIMED_OUT, ACTION_REQUIRED, STARTUP_FAILURE.
    Anything else, including a non-string value: PENDING."""

@dataclass(frozen=True)
class CheckCounts:  passed: int; failing: int; pending: int   # total = sum

def count_checks(rollup: object) -> CheckCounts | None:
    """None when rollup is not a list of dicts (fail closed, like session_state._checks_summary)."""

class ItemKind(Enum):  PR = "pr"; ISSUE = "issue"

@dataclass(frozen=True)
class PrFacts:
    number: int
    kind: ItemKind
    state: str            # PR: "OPEN" | "MERGED" | "CLOSED" (gh pr view); issue: "OPEN" | "CLOSED" (upper-cased)
    auto_merge: bool      # PR: autoMergeRequest is not null; issue: False
    checks: CheckCounts   # issue: CheckCounts(0, 0, 0)

def fetch_facts(repo_root: Path, number: int) -> PrFacts | str:
    """str = unverifiable detail ("gh api exited <rc>: <first diagnostic line>" or "malformed ...").
    1. run_gh(["api", f"repos/{{owner}}/{{repo}}/issues/{number}"]) -> JSON object; "pull_request" key
       present => PR, absent => ISSUE (state from "state").
    2. PR only: run_gh(["pr", "view", str(number), "--json", "state,autoMergeRequest,statusCheckRollup"]).
    Any non-zero rc, JSON error, wrong shape, or count_checks(...) is None => return str."""
```

**Import seam (pinned — premise report MISSING #1):** both `session_state` and `handoff_check` do
`from dotfiles_setup import pr_facts` and call `pr_facts.run_gh(...)` / `pr_facts.fetch_facts(...)` /
`pr_facts.count_checks(...)` through the MODULE ATTRIBUTE at call time — never `from dotfiles_setup.pr_facts import
run_gh`. `pr_facts` itself calls `subprocess.run` via the module attribute. So the one patch target for every unit
test is `monkeypatch.setattr(pr_facts, "run_gh", fake)`; convert the 6 existing `session_state._gh` patches in
`tests/test_session_state.py` to it, with a fake that dispatches on `args` (branch-PR list / open list / merged list)
so each query gets its own payload. Delete session_state's private `_gh` and `_GH_TIMEOUT`; `GH_TIMEOUT` stays 120
(the timeout arm at `tests/test_session_state.py:303` asserts it on every call). Re-express `_checks_summary` via
`count_checks`; its `N/M passing` text and its `None` for a malformed rollup are unchanged.

### `handoff_check.py`

```python
class Verdict(Enum):  # add
    PR_CLAIM_MISMATCH = "pr_claim_mismatch"
    PR_CLAIM_UNVERIFIABLE = "pr_claim_unverifiable"

class ClaimWord(Enum):
    OPEN = "OPEN"; MERGED = "MERGED"; CLOSED = "CLOSED"; RED = "RED"; GREEN = "green"
    LANDED = "landed"; AUTO_MERGE_ARMED = "auto-merge armed"; AUTO_MERGE = "auto-merge"

@dataclass(frozen=True)
class Claim:  number: int; word: ClaimWord; source: str; line: int   # source: handoff display path or "task_plan.md"

def active_section(plan_text: str) -> str | None:
    """From the line of the heading active_phase() matches (the LAST one, :278-281) up to, not including,
    the next line matching ^##\\s (level two only; ### stays inside), or EOF. None when no active heading."""

def extract_claims(text: str, *, source: str, line_offset: int = 0) -> list[Claim]:
    """See § 4 extraction rules. line = 1-based line in the SOURCE FILE (line_offset + index)."""

def claim_holds(word: ClaimWord, facts: PrFacts) -> bool | None:
    """None = the word is not checkable for this kind (PR-only words on an ISSUE). § 4 semantics."""

def check_with_claims(repo_root, text, *, show=show_attestation,
                      facts: Callable[[Path, int], PrFacts | str] | None = None,
                      source: str = "handoff",
                      deadline_s: float = CLAIMS_DEADLINE_S) -> tuple[list[Finding], int]:
    """The existing four groups, then the claim findings. Returns (findings, claims_checked).
    facts=None resolves pr_facts.fetch_facts AT CALL TIME (so a pr_facts.run_gh patch reaches it)."""

def check(repo_root, text, *, show=show_attestation, facts=None, source="handoff") -> list[Finding]:
    """Unchanged signature for the ~22 existing callers: check_with_claims(...)[0]."""

def render(findings, *, source, claims_checked: int = 0) -> str
```

`CLAIMS_DEADLINE_S = 300`: a TOTAL wall-clock budget for all claim fetches (each `run_gh` is still bounded at 120 s).
Numbers not fetched before it expires each get `pr_claim_unverifiable` with detail `claim-check deadline (300 s)
expired before lookup`. `main` calls `check_with_claims` with the display `source` it already computes and passes
the count to `render`. The OK line keeps its exact existing prefix and appends `; N PR claim(s) match GitHub`
(N = claims whose `claim_holds` returned True/False, i.e. excluding `None`; 0 allowed).

Finding shapes:

- mismatch — `citation`: `#1454 auto-merge armed (task_plan.md:1022)`; `detail`: `GitHub reports PR #1454
  state=MERGED auto-merge=yes checks fail:0 pending:0 pass:13`.
- unverifiable — ONE finding per number, not per claim; `citation`: `#1454`; `detail`: `GitHub lookup failed (<str
  from fetch_facts>) — N claim(s) unchecked; a failed lookup is never a pass`.

### `session_state.py`

```python
@dataclass(frozen=True)
class PrSummary:
    number: int; title: str; author: str; state: str   # "OPEN" | "MERGED"
    auto_merge: bool; checks: CheckCounts | None; merged_at: str | None

@dataclass(frozen=True)
class Snapshot:  # add fields
    open_prs: tuple[PrSummary, ...] | None     # None = UNVERIFIABLE (or --no-pr: see render)
    merged_prs: tuple[PrSummary, ...] | None
    since: str | None                           # ISO-8601 UTC "YYYY-MM-DDTHH:MM:SSZ"
    since_source: str | None                    # "--since" | "<handoff path> mtime" | "24h fallback"

def default_since(repo_root: Path, now: datetime) -> tuple[str, str]:
    """mtime of handoff_check.newest_handoff(repo_root) in UTC; none -> now - 24h."""

def gather(repo_root, *, limit=DEFAULT_COMMITS, with_pr=True, since: str | None = None) -> Snapshot
```

GitHub reads (both through `run_gh`, `--limit 100`):

- `gh pr list --state open --json number,title,author,autoMergeRequest,statusCheckRollup`
- `gh pr list --state merged --search "merged:>=<since>" --json number,title,author,mergedAt`

CLI: `session-state [--no-pr] [--since <ISO-8601>]`; an unparsable `--since` → stderr + rc=2. `main.py` passes it
through the argparse parser.

Rendering — append after the existing `open PR` line; the row grammar IS the claim grammar:

```text
- **open PRs** (7):
  - #1449 OPEN, auto-merge armed, RED (fail:2 pending:0 pass:12) — `Update image-build inputs` (@app/renovate)
  - #1141 OPEN, green (fail:0 pending:0 pass:9) — `Add native AgentsView service` (@sortakool)
- **merged since** 2026-09-29T22:15:03Z (.agent/plans/session-2026-09-29b.md mtime) (1):
  - #1455 MERGED 2026-09-29T22:30:00Z — `Update dependency aqua:betterleaks/betterleaks to v1.9.0` (@app/renovate)
```

Check word per open row: `RED` if failing ≥ 1; else `green` if total ≥ 1 and pending == 0; else `PENDING` (not a
claim word) or `no checks`. `auto-merge armed` only when armed. Titles go inside backticks with every backtick in the
title replaced by `'`. A failed lookup renders `- **open PRs**: UNVERIFIABLE — gh did not return a usable answer`
(same for merged). `--no-pr` renders `not requested (--no-pr)` for both.

## 4. Constraints and invariants

**Extraction** (`extract_claims`):

- Visible text only: blank out fenced code blocks (factor the fence walk at `handoff_check.py:232-251` into one
  `_visible_lines` helper returning the visible lines AND the unclosed-fence token (or None), which BOTH
  `_task_carrier_findings` (for `UNCLOSED_FENCE`, :267-274) and extraction use — behaviour of the former unchanged),
  then per line drop inline code spans (`` `…` ``) and `~~…~~` strikethrough spans before matching.
- A reference is `(?<![\w#/])#(?P<n>\d+)\b` — so `KB#814`, `owner/repo#12`, `<PR#>` are NOT references.
- A reference's window is the rest of its line up to the next reference on that line (or EOL).
- In the window, in this order, each hit consumed (masked) before the next pattern runs:
  1. `(?i)\bauto-merge\s+armed\b` or `(?i)\barmed\s+auto-merge\b` → AUTO_MERGE_ARMED
  2. `(?i)\bauto-merge\b(?![\w-])` → AUTO_MERGE (so `auto-merges`, `auto-merged` are NOT claims)
  3. case-SENSITIVE `\bOPEN\b`, `\bMERGED\b`, `\bCLOSED\b`, `\bRED\b`
  4. `(?i)\blanded\b`, `(?i)\bgreen\b`
- Multiple distinct words in one window → one claim each; the same word twice → one claim.

**Semantics** (`claim_holds`), PR:

| word | holds iff |
|---|---|
| OPEN / MERGED / CLOSED | `state` equals it (gh reports a merged PR as MERGED, not CLOSED) |
| landed | `state == "MERGED"` — a necessary condition; post-merge land success is not on GitHub. Say so in the docstring |
| auto-merge armed | `state == "OPEN"` and `auto_merge` — `autoMergeRequest` PERSISTS after merge (measured: #1456 MERGED, auto=true), so OPEN is required |
| auto-merge | `state == "OPEN"`, `auto_merge`, and `failing == 0` — the bare word predicts a merge; a RED armed PR will not merge (the 2026-09-29 #1449 case) |
| RED | `failing >= 1` |
| green | total ≥ 1, `failing == 0`, `pending == 0` |

ISSUE: OPEN/CLOSED compare `state`; every other word → `None` (not checkable, not a finding, not counted).

- Fetch each number at most once per run (cache), across handoff + plan.
- Plan claims come from `active_section(task_plan.md)` only, with correct file line numbers; skipped when
  `task_plan.md` is absent (existing fresh-clone behaviour).
- Unit tests make NO network call: inject `facts=` / monkeypatch `pr_facts.run_gh`. Existing tests stay green; update
  only assertions that pin the OK line or the removed `_gh`.
- Repo conventions: py3.14, ruff + ty clean, zero inline suppressions (`no_lint_skip`), no bash, `json.loads` as
  `session_state` already does (:186; no msgspec needed), tests under repo-root `tests/`.
- Do not change `handoff-check`'s exit-code contract beyond: any new finding ⇒ rc=1.

## 5. Verification

```bash
mise run gate -- run lint
mise run gate -- run pytest
mise run gate -- run verify
```

Plus the real-integration arms (report each rc and the relevant output lines verbatim):

1. **FAIL arm, real stale text, live GitHub:** `mise run handoff-check -- .agent/plans/session-2026-09-29b.md` → rc=1
   with `pr_claim_mismatch` citing `task_plan.md:1108` and `task_plan.md:1162` (the `#1449 … → auto-merge` lines) (#1449 is
   OPEN, armed, RED today). No other claim finding. Do NOT edit `task_plan.md` to make it pass — the coordinator
   corrects that text after this lands (ADDENDUM: check first, then fix the text).
2. **FAIL arm, 09-29b fixture:** copy the handoff to the scratchpad, append the line
   `- #1454 research-sweep tuning (auto-merge armed)`, run handoff-check on the copy → a `pr_claim_mismatch` citing
   `#1454 auto-merge armed`.
3. **Unverifiable arm:** the same copy under `GH_HOST=bogus.invalid` (or an equivalent that makes `gh` fail without
   touching credentials) → `pr_claim_unverifiable`, rc=1. Never print a token.
4. **session-state live:** `mise run session-state` → the open-PR list includes `#1449 OPEN, auto-merge armed, RED`;
   the merged list's `since` comes from the newest handoff mtime. Then paste that output into a scratch handoff copy and
   run handoff-check on it → its PR rows produce no finding.
5. **`merged:>=` datetime arm (premise A1):** `mise run session-state -- --since 2026-09-29T00:00:00Z` lists #1454 and
   #1456; `--since 2026-09-29T22:00:00Z` lists #1456 but not #1454 (merged 21:52:30Z). If GitHub ignores the time part,
   report it — do not work around it silently.

## 6. Commit

`caller`. Leave the tree uncommitted; report changed paths and every gate/arm rc.

## 7. PREMISES

| # | kind | claim | cite (read this session) |
|---|---|---|---|
| P1 | L | `_ACTIVE_HEADING` = last `##` heading containing `NEXT SESSION`; `active_phase` returns it | `handoff_check.py:43`, `:278-281` |
| P2 | I | `check(repo_root, text, *, show=...)` returns the four finding groups; `main` computes `source` and exits 1 on findings | `handoff_check.py:331-343`, `:358-393` |
| P3 | P | the fence walk to reuse | `handoff_check.py:232-251` |
| P4 | I | `Verdict` members today | `handoff_check.py:106-116` |
| P5 | I | `session_state._gh` contract (rc/diag, 124 timeout, 127 OSError, child_env) | `session_state.py:144-163` |
| P6 | L | passing set `{SUCCESS, NEUTRAL, SKIPPED, PASS}`; value = conclusion/state/status | `session_state.py:174-178` |
| P7 | I | `Snapshot`, `gather`, `render`, `main` (`--no-pr` only; unknown arg rc=2) | `session_state.py:63-71`, `:232-303` |
| P8 | I | CLI parser + dispatch for both commands | `main.py:1530-1556`, `:2816-2824` |
| P9 | L | mise task definitions | `mise.toml:1005-1018` |
| P10 | P | test harness style: monkeypatched `subprocess.run`, `_COMMAND_TIMEOUT = 30` | `tests/test_handoff_check.py:1-40` |
| P11 | L | live: #1449 PR OPEN auto=true FAILURE:2 NEUTRAL:1 SKIPPED:8 SUCCESS:3; #1456 PR MERGED auto=true; #1450 MERGED auto=true with FAILURE:1 | `gh pr view … --json state,autoMergeRequest,statusCheckRollup`, this session |
| P12 | L | live: #963 and #1388 are ISSUES (no `pull_request` key); #1063 is a closed-unmerged PR | `gh api repos/ray-manaloto/dotfiles/issues/N`, this session |
| P13 | L | prototype extraction over today's handoff + active section found 19 claims; the only contradicted ones are the two `#1449 … → auto-merge` lines (lines 120 and 174 counted within the active section) | scratchpad `proto.py`, this session |
| P14 | E | findings carry PR number, claim word, file:line, gh state/check counts — repo metadata only, no PII; bounded by claims in two files | this spec § 3 |
| A1 | A | `gh pr list --search "merged:>=YYYY-MM-DDTHH:MM:SSZ"` honours the time component | UNVERIFIED — verification arm 5 |
| P15 | P | `gh api repos/{owner}/{repo}/...` placeholder form is already on `land`'s live path | `pr.py:824-834` (:828) |
| P16 | I | `gh pr list --json` exposes `author{login}`, `autoMergeRequest`, `statusCheckRollup`, `mergedAt` (P11 measured `pr view`, not `pr list`) | UNVERIFIED — arm 4 settles it |
| P17 | E | session-state stdout gains PR titles (human free text, unbounded — render as-is inside backticks), author logins (public GitHub identifiers), mergedAt; nothing stored | this spec § 3 |
| P18 | L | active section today = `task_plan.md:989-1406`; the contradicted claims are file lines :1108 and :1162 | premise report P13 |
| N1 | note | window rule attributes `#1435 + #963 CLOSED` (:1160) to #963 only — accepted by design | premise report |
| N2 | note | claims are judged at CHECK time: a handoff true when written fails at resume once GitHub moves — intended drift detection; handoff-check now needs network (offline ⇒ rc=1 unverifiable) | ruling: "a gh failure is UNVERIFIABLE (never a pass)" |
