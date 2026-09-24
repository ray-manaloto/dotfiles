Slice D (runtime-injected text) is done. The harness blocked my write of the final report to `SP/report-D-runtime.md` ("Subagents should return findings as text"), so the complete report is below. That path holds only my incremental working log (D1 to D12); a copy is at `report-D-runtime.worklog.md`. No repo file was edited, staged or committed, and the working tree is clean.

# Prompt audit, slice D: runtime-injected prompt text

**Scope:** text that reaches Claude while a session is running, not text loaded from a static instruction file. That means:
- every hook wired in `.claude/settings.json`, plus the hooks of plugins that file enables;
- the `agent()` prompts built in `.claude/workflows/*.js`;
- the vendored skills (graphify, context7-cli, find-docs), which are flag-only;
- Group 4: model-call census and token accounting.

**Target model:** Claude Opus 5.5 (thinking always on; effort default medium; follows instructions literally).

**Repo state:** branch `docs/prompt-audit-2026-09-24` at 1c4977eb.

## Summary

| Group | High | Medium | Low / flag |
|---|---|---|---|
| 1a pressure language | 1 (D1a) | 1 (D2) | 3 (D3, D12 graphify L208, D12 find-docs L48/50) |
| 1c over-specification / duplication | – | 1 (D7) | – |
| 1d re-insertion / unenforced | – | 1 (D1b) | 2 (D5, D8) |
| 2 history narrative / vendored skills | – | 1 (D6) | 1 (D12) |
| 3 contract accuracy | counted in D1a | – | 1 (D12 context7 trigger overlap) |
| 4 architecture | – | 2 (D10, D11) | – |

**The three highest-impact findings:**

1. **The graphify PreToolUse nudge (D1a and D1b).**
   - **What it does.** It injects "MANDATORY: … You MUST run graphify …" on every Bash call that runs grep, find or rg, and on every Grep, Read or Glob of a source file. Nothing deduplicates it; the time-to-live logic exists only in the unused strict mode.
   - **The wording breaks this repo's own standard.** Claude Code's hook docs say injected text should be factual statements, and that imperative "out-of-band system commands can trigger Claude's prompt-injection defenses" (`$CC/hooks.md:1031-1033`). The repo already enforces that on its own hook in `tests/test_mise_config_context.py:100-109`, and `mise_config_context.py` states: "the tenth identical copy is the decay it exists to beat."
   - **It gives wrong instructions.** It tells the model to run bare `graphify explain` and `graphify path`, which `graphify-first.md` forbids, and demands a query even when the graph is stale.
   - **Transcripts show it is ignored.** Session a6750a24 has 202 records carrying the nudge, 382 tool calls and **0** `graphify-query` calls. Session 94aea797 has 366 nudge records and 4 queries. This lane alone received it 18 times.
2. **The Group 4 census (D10).** There are 16 `agent()` call sites across the three workflows. Three of them do fully deterministic work:
   - gate-runner runs a fixed list of commands.
   - graphify-operator runs an ordered task list.
   - the modernization-audit haiku loader returns a file "EXACTLY as stored"; the script's own comment records that a haiku loader already failed at this.

   The workflow runtime has no shell or file primitive (`$CC/workflows.md:307,324`), so these steps can only leave the model by moving to the caller's side.
3. **Conflicting runtime instructions (D2, D7).**
   - The AskUserQuestion quality-deny says "do NOT fall back to … prose", while the eager rule `clarify-before-acting.md:7-8` says "when [the tool] is absent or denied, present … in prose". A model that reads literally gets two opposite answers for the same event.
   - The enabled `learning-output-style` plugin repeats `explanatory-output-style`'s Insights instruction nearly word for word, and both are enabled, so it arrives twice each session.

## Findings (highest confidence first)

### D1a: graphify nudge wording (pressure language, broken contract)
- **Location:** `python/src/dotfiles_setup/graphify.py:848-862` (`rewrite_hook_nudge`). The text comes from the vendor, graphify 0.9.65 `graphify/cli.py:18-41`. It is wired at `.claude/settings.json` PreToolUse `Bash|Grep` and `Read|Glob` through `scripts/graphify-hook-guard.sh`.
- **Evidence:**
  - "MANDATORY: graphify-out/graph.json exists. You MUST run graphify before reading source files. Use: `mise run graphify-query -- "<question>"` (scoped subgraph), `graphify explain "<concept>"`, or `graphify path "<A>" "<B>"`. … This rule applies to subagents too — include it in every subagent prompt involving code exploration."
  - `tests/test_graphify.py:862-863` asserts that `explain` and `path` pass through unchanged ("no task for it").
- **Pattern:**
  - 1a: `MANDATORY` / `MUST` with no stated reason.
  - Group 3: the text prescribes bare-binary commands that `graphify-first.md` forbids ("Always the mise tasks, never a bare `graphify` on `PATH`"), and demands a query unconditionally where the rule says "`stale` … fall back to source".
  - The "include it in every subagent prompt" clause copies the pressure text into every delegation.
- **Why obsolete:** Opus 5.5 responds strongly to the system prompt, so shouting causes over-triggering. Imperative hook text is documented to trip prompt-injection defenses (`$CC/hooks.md:1033`). The eager rule already carries the real, health-gated instruction.
- **Confidence:** High.
- **Action:** rewrite (Hunk 1).

### D1b: graphify nudge is re-injected on every call
- **Location:** `graphify.py:865-888`, which does no deduplication.
- **Evidence:**
  - The census above. The same parser counts tool_use records and `graphify-query` calls above zero, so it can see both.
  - The nudge is 190 or 400 characters per injection.
- **Pattern:** 1d, instruction re-insertion on a cadence, and an unenforced instruction that transcripts show being ignored.
- **Why obsolete:** Current models keep an instruction they were given once. The repo already built a once-per-session, per-agent marker for exactly this reason (`mise_config_context.already_seen`).
- **Confidence:** Medium.
- **Action:** rewrite (Hunk 2).
  - If the query rate stays near zero after Hunks 1 and 2, remove the hook entirely. The removal list:
    - the two PreToolUse entries in `.claude/settings.json`;
    - `.codex/hooks.json:19,29`;
    - `scripts/graphify-hook-guard.sh` and its entry at `bash_budget.py:107-117`;
    - `graphify.py`'s `hook_guard_main` and `rewrite_hook_nudge`;
    - `main.py:90,1226,2389-2390`;
    - the related tests in `tests/test_graphify.py`;
    - the `.gitignore:83` comment.
  - `hook_selfcheck` does not require this wiring; `tests/test_hook_selfcheck.py:332` only uses it as a fixture.

### D2: the AskUserQuestion quality-deny contradicts the eager fallback rule
- **Location:** `python/src/dotfiles_setup/ask_quality.py:225-226`
- **Evidence:**
  - The deny message: "Revise and re-ask — do NOT fall back to listing the options in prose, which costs the user a round-trip and is what this standard exists to stop."
  - The rule it cites (`clarify-before-acting.md:7-8`): "When it is absent or denied, present the same bounded options in prose and **STOP**".
- **Pattern:** 1a (a capitalised prohibition), and two instructions that disagree about the same event.
- **Why obsolete:** Opus 5.5 reads "denied" literally, and this hook *is* a PreToolUse deny.
- **Confidence:** Medium.
- **Action:** rewrite (Hunk 3).
  - `tests/test_ask_quality.py:203-207` only asserts `"prose"` and the rule path, and both survive the rewrite.
  - For slice A: the rule could say "denied by permissions".

### D6: history narrative inside the mise-config PostToolUse context
- **Location:** `python/src/dotfiles_setup/mise_config_context.py:85-91`
- **Evidence:** "A worked instance from 2026-09-01: a custom `{rc, gates[], outcome}` result sink was scoped across several turns … The rule was in eager context throughout; what was missing was a prompt at the moment of the edit."
- **Pattern:** Group 2 history narrative, plus 1c single-example over-indexing. The last sentence explains to a maintainer why the hook exists; it tells the model nothing it can act on.
- **Why obsolete:** A single worked incident pulls every mise-config edit toward one topic. The paragraphs above it already carry the rule reference and where the local docs are.
- **Confidence:** Medium.
- **Action:** remove the paragraph (Hunk 4). `tests/test_mise_config_context.py:100-129` requires `use-tool-builtins.md`, `knowledge-base/sources/mise/docs`, no imperative phrasing, and fewer than 1,500 characters. All four still hold.

### D7: output-style instructions injected twice per session
- **Location:** `.claude/settings.json:187,189` (introduced in fc8af71c, #34).
- **Evidence:**
  - Both `explanatory-output-style` and `learning-output-style` are set to `true`.
  - learning's SessionStart payload contains an "## Explanatory Mode" section restating explanatory's `★ Insight` instruction.
  - `docs/claude-plugin-config-hygiene.md:66-67` records that local scope used to disable both. The current `settings.local.json` no longer does.
- **Pattern:** 1c, duplicated rules that make the model reconcile two wordings of one instruction.
- **Confidence:** Medium.
- **Action:** rewrite (Hunk 5). Disable explanatory, since learning is its superset.
- **Flag only:**
  - learning mode says "Instead of implementing everything yourself … the user can write 5-10 lines", which pulls against the repo's routing of implementation to codex lanes. That is a product decision.
  - The untracked `settings.local.json` sets `outputStyle: "Concise"`, a third register.

### D10: Group 4, LLM executors doing deterministic work in the workflows
- **Location and evidence:** 16 `agent()` sites in total.
  - `gated-implementation.js`, 4 sites.
    - Judgment, keep: implementer (:88), cold-reviewer (:116), critic (:128).
    - Deterministic: **gate-runner** (:99, haiku), "Run every command in this JSON array, in order … Capture each rc".
  - `graphify-refresh.js`, 3 sites.
    - Judgment, keep: researcher (:68), staleness auditor (:97).
    - Deterministic: **graphify-operator** (:81, sonnet), "Run exactly this ordered JSON task list. Stop at the first rc that differs".
  - `modernization-audit.js`, 9 sites.
    - Judgment, keep: finder, 3 lens verifiers, synthesis, critic, re-find.
    - Deterministic: the **loader** (:133/:137, haiku), "return its JSON object EXACTLY as stored". The comment at :114 records that it was "defeated" re-typing a 28 KB JSON.
    - Partly deterministic: the gap-fetch download step (:48) and synthesis "STEP 0" (`mise run audit-aggregate`, :195).
- **Pattern:** Group 4, an LLM executor for a deterministic plan.
- **Confidence:** Medium.
- **Action:** move.
  - The workflow body only has `agent`, `pipeline`, `parallel`, `phase`, `log` and `args`. The deterministic steps therefore move to the caller's side: a mise task run before or after the workflow, with results passed through `args`.
  - For the loader: in reuse mode, send units down the existing `verifyPromptDisk` path, which already reads `findings/<slug>.json` from disk, and delete `loadPrompt`.
  - I wrote no hunk because the workflows cannot be run from this lane to verify an edit, and the change alters the `args` contract.
- The workflows are clean on Group 1:
  - The pressure words carry reasons ("NEVER cat it whole" because the file is 650 KB; "Default to refuted=true" is deliberate adversarial calibration).
  - No thinking, budget or sampling fossils.
  - Models are named by alias.

### D11: Group 4, no token accounting for runtime-injected text
- **Evidence:**
  - Static surfaces are budgeted: `md_size_budget` (`hk.pkl:680`) and `listing_budget.py` (about 7,470 tokens of standing skill and agent listing).
  - Nothing measures hook `additionalContext`: the graphify nudge, the planning-with-files pretool plan head, or plugin SessionStart payloads.
  - Nothing measures per-workflow `agent()` spend.
  - `docs/specs/research-nudge-hooks.md:64` notes hooks receive no context-usage field.
  - `token_audit.py` measures contract-token substrings, not model tokens.
- **Confidence:** Medium.
- **Action:** add a census task over native transcripts, following the `agentsview_pass.py` pattern: additionalContext bytes per hook and per session, and injections compared with the behaviour they ask for. D1b's numbers came from a 20-line version of this. It is the prerequisite for measuring Hunks 1 and 2.

### Low confidence and flag-only

- **D3: `hook_guard.py` deny reasons (:390-705).** Clean contracts that fire only on a deny. One Low note: the `secret_value_substitution` reason carries a dated incident ("…reached a transcript on 2026-08-02").
- **D4: SubagentStart contract (`hook_selfcheck.py:529-549`).** It fires once per delegate and is the only carrier for Explore and Plan agents, and every imperative has a reason. Keep.
- **D5: PostToolUse/Agent reminder (`hook_selfcheck.py:551-561`).**
  - "persist it VERBATIM now" restates the eager `agent-report-persistence.md` rule 1.
  - It is tied to the moment the duty applies and appended after the tool result, which is the form GUIDE 1d accepts, and it was motivated by real losses. Candidate for re-testing, not for a diff.
  - The token is bound at `hook_selfcheck.py:689`.
- **D8: third-party injectors enabled by settings.json (vendor text).**
  - planning-with-files 3.17.2 (OthmanAdi/planning-with-files):
    - It injects a 30-line plan head on every Write, Edit, Bash, Read, Glob or Grep call (`inject-plan.sh:12,131`), and a UserPromptSubmit hook every turn.
    - The root `task_plan.md` is 133,873 bytes.
    - I did not see it fire in this lane; its session guard may silence it there.
  - antigravity 0.27.1: its delegation nudge is keyword-gated and explicitly non-mandating.
  - The codex 1.0.6 Stop review gate is opt-in.
- **D12: vendored skills.**
  - **graphify** (Graphify-Labs/graphify, managed by `mise run graphify-update`, pinned at 0.9.65):
    - SKILL.md is 41 KB plus 44 KB of references.
    - Line 208: "**MANDATORY: You MUST use the Agent tool here. … If you do not use the Agent tool you are doing this wrong.**"
    - It mentions bare `graphify query/update/explain/path` 12 times and `mise run graphify` 0 times.
  - **context7-cli** and **find-docs** (upstash/context7 `skills/`):
    - Both were copied in c5a0715f; context7-cli matched upstream byte for byte at copy time, find-docs except for punctuation.
    - Both were later patched locally (+11/-8 and 5 lines), and there is no refresh task, so a re-vendor would silently drop the patches.
    - find-docs L48 "You MUST call `ctx7 library` first" is a real contract written in caps; L50 is a 3-attempt cap with a stop rule.
    - Three triggers overlap on one capability: find-docs, the `context7:*` plugin skills, and the context7 MCP instruction "Prefer this over web search". The MCP instruction contradicts `research-doc-sources.md` lane 2 (CLI before MCP for our own lookups).
- **Out-of-slice notes:**
  - `gh-cli-watch.md` prescribes `gh pr checks --watch` and `gh run watch`, which `hook_guard.py:556-573` denies (slice A).
  - `.codex/hooks.json:19,29` wires the graphify nudge for codex, although graphify's own `cli.py:2463-2466` says Codex Desktop rejects PreToolUse additionalContext (codex is out of scope).

## Proposed diff

There is one hunk per finding, all High or Medium confidence. The code in Hunks 1 and 2 was copied to a scratch file and checked there:
- `ruff format` is clean. `ruff check` reports only INP001 and CPY001, which come from the scratch location and do not apply inside the repo.
- `ty check` passes, and fails on an injected return-type error (control arm).
- Behaviour probes pass against the live vendor output and the updated test assertions. The old function still fails the new `explain` assertion (control arm).

### Hunk 1 (D1a)
```diff
--- a/python/src/dotfiles_setup/graphify.py
+++ b/python/src/dotfiles_setup/graphify.py
@@ -845,18 +845,42 @@ def graphify_rebuild_main(project_root: Path, *, target: str = ".") -> int:
     return graphify_health_main(project_root)
 
 
+#: Replaces graphify's hardcoded "MANDATORY ... You MUST run" nudges, stated as
+#: facts per Claude Code's hook guidance ($CC/hooks.md:1033: imperative
+#: out-of-band text can trip prompt-injection defenses) and the standard
+#: tests/test_mise_config_context.py pins for this repo's own hook text.
+_GRAPH_NUDGE = (
+    "graphify-out/graph.json exists for this repository. `mise run graphify-query "
+    '-- "<question>"` answers structural questions (callers, dependencies, where '
+    "a symbol lives) from it; `mise run graphify-health` reports whether it is "
+    "current."
+)
+
+
 def rewrite_hook_nudge(text: str) -> str:
-    """Rewrite graphify's own PreToolUse nudge text to this repo's mise tasks.
+    """Rewrite graphify's own PreToolUse nudge text to this repo's wording.
 
-    graphify's ``hook-guard`` subcommand hardcodes ``graphify query``/
-    ``graphify update`` in its advisory nudge copy (``graphify/cli.py`` — no
-    flag or env var changes the wording), which is a bare PATH invocation
-    that ``graphify-first.md`` forbids: two different graphify versions run
-    on this machine, and only ``mise run graphify-query``/``graphify-rebuild``
-    are guaranteed to resolve this repo's uv-locked version. Plain text
-    substitution — the JSON structure and every other field pass through
-    unchanged.
+    graphify's ``hook-guard`` subcommand hardcodes its nudge copy
+    (``graphify/cli.py`` — no flag or env var changes the wording). The two
+    ``MANDATORY:`` nudges are replaced whole with :data:`_GRAPH_NUDGE`: they
+    name bare-binary commands ``graphify-first.md`` forbids (including
+    ``graphify explain``/``path``, which have no mise task) and demand a query
+    regardless of graph health. Any other payload (the stale-file nudge) gets
+    plain substitution of the bare ``query``/``update`` commands.
     """
+    try:
+        payload = json.loads(text)
+    except ValueError:
+        payload = None
+    hook = payload.get("hookSpecificOutput") if isinstance(payload, dict) else None
+    context = hook.get("additionalContext") if isinstance(hook, dict) else None
+    if (
+        isinstance(hook, dict)
+        and isinstance(context, str)
+        and context.startswith("MANDATORY:")
+    ):
+        hook["additionalContext"] = _GRAPH_NUDGE
+        return json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n"
     return text.replace("`graphify query", "`mise run graphify-query --").replace(
         "`graphify update`", "`mise run graphify-rebuild`"
     )
--- a/tests/test_graphify.py
+++ b/tests/test_graphify.py
@@ -829,11 +829,12 @@
 def test_rewrite_hook_nudge_rewrites_bare_query_and_update() -> None:
     """Real graphify hook-guard output, captured 2026-08-30, gets rewritten.
 
     graphify's own nudge copy is hardcoded (graphify/cli.py) and names the
     bare binary — exactly what graphify-first.md forbids on this machine
-    (two graphify versions on PATH). `graphify explain`/`graphify path`
-    mentions are untouched: this repo has no mise task for them, so
-    rewriting would point at something that doesn't exist.
+    (two graphify versions on PATH). The MANDATORY nudges are replaced whole
+    by a factual sentence naming only mise tasks, so `graphify explain`/
+    `graphify path` (no mise task) and the imperative framing both disappear.
     """
@@ -846,6 +847,7 @@
     rewritten = rewrite_hook_nudge(search_nudge)
     assert '`mise run graphify-query -- \\"<question>\\"`' in rewritten
     assert "`graphify query" not in rewritten
+    assert "MANDATORY" not in rewritten and "You MUST" not in rewritten
     # Structure (everything but the rewritten substring) is untouched.
     assert rewritten.startswith('{"hookSpecificOutput":{"hookEventName":"PreToolUse"')
 
@@ -859,8 +861,9 @@
     rewritten_read = rewrite_hook_nudge(read_nudge)
     assert '`mise run graphify-query -- \\"<question>\\"`' in rewritten_read
-    assert "`graphify explain" in rewritten_read  # untouched — no task for it
-    assert "`graphify path" in rewritten_read  # untouched — no task for it
+    assert "`graphify explain" not in rewritten_read  # no mise task exists for it
+    assert "`graphify path" not in rewritten_read  # no mise task exists for it
+    assert "MANDATORY" not in rewritten_read
 
     stale_nudge = (
```

### Hunk 2 (D1b)
```diff
--- a/python/src/dotfiles_setup/graphify.py
+++ b/python/src/dotfiles_setup/graphify.py
@@ -26,6 +26,7 @@
 from dotfiles_setup import codec
 from dotfiles_setup.child_env import without_env_diff
 from dotfiles_setup.graphify_currency import GraphifyCurrencyError, locked_version
+from dotfiles_setup.mise_config_context import already_seen
@@ -530,9 +531,10 @@ def _run(
     args: list[str],
     *,
     cwd: Path,
     env: dict[str, str] | None = None,
+    stdin: str | None = None,
 ) -> subprocess.CompletedProcess[str]:
@@ -542,6 +544,7 @@ def _run(
         check=False,
         capture_output=True,
         text=True,
+        input=stdin,
         env=without_env_diff() if env is None else env,
     )
@@ -878,11 +902,30 @@ def hook_guard_main(project_root: Path, kind: str) -> int:
     that script's header. ``$1``/``kind`` is ``search`` (Bash|Grep matcher)
     or ``read`` (Read|Glob), graphify's own vocabulary.
+
+    The nudge is delivered once per session, per agent and kind (the
+    ``mise_config_context.already_seen`` marker): a repeated identical nudge
+    on every search/read is re-insertion, not information. The hook payload
+    is read here and handed to graphify on stdin, since reading it consumes it.
     """
     try:
-        result = _run(["graphify", "hook-guard", kind], cwd=project_root)
+        raw = sys.stdin.read()
+    except OSError:
+        raw = ""
+    try:
+        result = _run(["graphify", "hook-guard", kind], cwd=project_root, stdin=raw)
     except OSError:
         return 0
     if result.returncode != 0 or not result.stdout:
         return 0
+    try:
+        event = json.loads(raw) if raw.strip() else {}
+    except ValueError:
+        event = {}
+    if not isinstance(event, dict):
+        event = {}
+    session_id = str(event.get("session_id", ""))
+    agent_id = str(event.get("agent_id", ""))
+    if session_id and already_seen(
+        project_root, f"graphify-{kind}-{session_id}", agent_id
+    ):
+        return 0
     sys.stdout.write(rewrite_hook_nudge(result.stdout))
     return 0
--- a/tests/test_graphify.py
+++ b/tests/test_graphify.py
@@ -15,5 +15,6 @@
 import hashlib
+import io
 import json
 import shutil
 import subprocess
@@ -881,9 +883,12 @@ def test_hook_guard_main_rewrites_and_prints(
     monkeypatch: pytest.MonkeyPatch,
     tmp_path: Path,
     capsys: pytest.CaptureFixture[str],
 ) -> None:
-    def fake_run(args: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
-        _ = cwd
+    def fake_run(
+        args: list[str], *, cwd: Path, stdin: str | None = None
+    ) -> subprocess.CompletedProcess[str]:
+        _ = cwd, stdin
         assert args == ["graphify", "hook-guard", "search"]
         return subprocess.CompletedProcess(
             args,
             0,
             stdout='{"additionalContext":"run `graphify query \\"q\\"` first"}\n',
             stderr="",
         )
 
     monkeypatch.setattr("dotfiles_setup.graphify._run", fake_run)
+    monkeypatch.setattr("sys.stdin", io.StringIO(""))
 
     rc = hook_guard_main(tmp_path, "search")
 
     assert rc == 0
     assert "`mise run graphify-query --" in capsys.readouterr().out
 
 
+def test_hook_guard_main_nudges_once_per_session(
+    monkeypatch: pytest.MonkeyPatch,
+    tmp_path: Path,
+    capsys: pytest.CaptureFixture[str],
+) -> None:
+    """Same session + agent + kind: first call prints, second is silent."""
+    seen: list[str | None] = []
+
+    def fake_run(
+        args: list[str], *, cwd: Path, stdin: str | None = None
+    ) -> subprocess.CompletedProcess[str]:
+        _ = cwd
+        seen.append(stdin)
+        return subprocess.CompletedProcess(args, 0, stdout="NUDGE\n", stderr="")
+
+    monkeypatch.setattr("dotfiles_setup.graphify._run", fake_run)
+    payload = '{"session_id":"s1","tool_name":"Grep"}'
+    outs = []
+    for kind in ("search", "search", "read"):
+        monkeypatch.setattr("sys.stdin", io.StringIO(payload))
+        hook_guard_main(tmp_path, kind)
+        outs.append(capsys.readouterr().out)
+    assert outs == ["NUDGE\n", "", "NUDGE\n"]
+    assert seen[0] == payload  # the payload still reaches graphify
+
+
 def test_hook_guard_main_fails_open_on_nonzero_rc(
     monkeypatch: pytest.MonkeyPatch,
     tmp_path: Path,
     capsys: pytest.CaptureFixture[str],
 ) -> None:
-    def fake_run(args: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
-        _ = cwd, args
+    def fake_run(
+        args: list[str], *, cwd: Path, stdin: str | None = None
+    ) -> subprocess.CompletedProcess[str]:
+        _ = cwd, args, stdin
         return subprocess.CompletedProcess(args, 1, stdout="", stderr="boom")
 
     monkeypatch.setattr("dotfiles_setup.graphify._run", fake_run)
+    monkeypatch.setattr("sys.stdin", io.StringIO(""))
 
     assert hook_guard_main(tmp_path, "read") == 0
     assert capsys.readouterr().out == ""
 
 
 def test_hook_guard_main_fails_open_on_missing_binary(
     monkeypatch: pytest.MonkeyPatch, tmp_path: Path
 ) -> None:
-    def fake_run(args: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
-        _ = cwd, args
+    def fake_run(
+        args: list[str], *, cwd: Path, stdin: str | None = None
+    ) -> subprocess.CompletedProcess[str]:
+        _ = cwd, args, stdin
         message = "graphify not found"
         raise FileNotFoundError(message)
 
     monkeypatch.setattr("dotfiles_setup.graphify._run", fake_run)
+    monkeypatch.setattr("sys.stdin", io.StringIO(""))
 
     assert hook_guard_main(tmp_path, "search") == 0
```

Hunk 2 notes:
- The markers land in the gitignored `.agent/state/mise-config-context/`, which `already_seen` already uses. A later tidy-up could move `already_seen` into a shared module.
- `scripts/graphify-hook-guard.sh` is unchanged; it already passes stdin through.
- The scratch probe covered four cases:
  - same session and kind: printed first, then silent;
  - a different kind: printed;
  - a different agent: printed;
  - no session ID: always printed.

### Hunk 3 (D2)
```diff
--- a/python/src/dotfiles_setup/ask_quality.py
+++ b/python/src/dotfiles_setup/ask_quality.py
@@ -222,6 +222,7 @@ def decide(tool_input: Mapping[str, object]) -> str | None:
         "This ask does not meet the project's AskUserQuestion standard "
         f"(Ray, 2026-08-02; {_DOC}):\n"
         f"{bullets}\n"
-        "Revise and re-ask — do NOT fall back to listing the options in prose, "
-        "which costs the user a round-trip and is what this standard exists to stop."
+        "Revise the options and call AskUserQuestion again. This is a quality "
+        "deny, not the tool being unavailable, so that rule's prose fallback does "
+        "not apply; listing the options in prose would cost the user a round-trip."
     )
```

### Hunk 4 (D6)
```diff
--- a/python/src/dotfiles_setup/mise_config_context.py
+++ b/python/src/dotfiles_setup/mise_config_context.py
@@ -80,15 +80,7 @@ CONTEXT = """\
 was insufficient.
 
 mise's own documentation is on this disk at {docs}, so the check costs a grep \
-rather than a web fetch.
-
-A worked instance from 2026-09-01: a custom `{{rc, gates[], outcome}}` result \
-sink was scoped across several turns before anyone read those docs. mise turned \
-out to already provide the uniform log-location half — `MISE_LOG_FILE` plus \
-`MISE_LOG_FILE_LEVEL` — while the structured per-invocation result half is \
-genuinely absent, because the only completed-result store mise documents is the \
-task cache and "Only successful task runs are cached". The rule was in eager \
-context throughout; what was missing was a prompt at the moment of the edit.\
+rather than a web fetch.\
 """
```

### Hunk 5 (D7)
```diff
--- a/.claude/settings.json
+++ b/.claude/settings.json
@@ -185,7 +185,7 @@
     "pyright-lsp@claude-plugins-official": false,
     "pyright@claude-code-lsps": false,
-    "explanatory-output-style@claude-plugins-official": true,
+    "explanatory-output-style@claude-plugins-official": false,
     "hookify@claude-plugins-official": false,
     "learning-output-style@claude-plugins-official": true,
     "octo@nyldn-plugins": false,
```
After applying Hunk 5, run `mise run rule-sync` and `mise run plugin-health`.

## Checked and found clean
- `hook_guard.py`: all 20 deny reasons are contracts that fire only on a deny (one Low note, D3).
- `branch_guard._REASON` (`:68-79`) and `script_guard._REASON` (`:59-75`): contracts, each with a fix command.
- SessionStart `tool-currency-check` and `doctor` (`mise.toml:668-690`): silent unless drift, always rc 0, run once. No pressure words in `doctor.py` or `claude_doctor.py`.
- The `instructions_observer` InstructionsLoaded hook never prints.
- The SessionEnd `command-audit` hook writes a file, and its output does not reach the model.
- `mise_config_context` delivery: once per session per agent, statement-phrased (only D6 is a finding).
- The SubagentStart contract (D4).
- Workflow prompts: no prefill, thinking config, `budget_tokens`, temperature or word caps.
- No hook owned by the repo fires on every Bash call; the graphify nudge fires only on Bash calls that actually run a search tool, and that includes `ls | grep`.
- Method checks:
  - Every zero-result probe had a control arm: `md_size_budget` for the token-accounting grep, tool_use and query counts for the transcript census, `RECOMMENDED_MARKER` for the ask_quality test grep, and an injected type error for ty.
  - The vendored status of each skill was verified against git history and the upstream contents, fetched via `gh api`.

## GitHub repos touched
- [Graphify-Labs/graphify](https://github.com/Graphify-Labs/graphify): owner of the nudge text (installed `graphify/cli.py` 0.9.65) and of the vendored `/graphify` skill.
- [upstash/context7](https://github.com/upstash/context7): upstream `skills/find-docs` and `skills/context7-cli`, diffed against the vendored copies.
- [OthmanAdi/planning-with-files](https://github.com/OthmanAdi/planning-with-files): plugin hooks.json and the per-call pretool injection (installed cache, read locally).
- [anthropics/claude-plugins-official](https://github.com/anthropics/claude-plugins-official): the explanatory- and learning-output-style SessionStart payloads (installed cache, read locally).
- [openai/codex-plugin-cc](https://github.com/openai/codex-plugin-cc): the codex plugin's Stop review-gate hook (installed 1.0.6 cache, read locally; repo name inferred from the marketplace id, not fetched).
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base): offline Claude Code docs (`hooks.md:1020-1033`, `workflows.md:296-359`).
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles): the audited repo.