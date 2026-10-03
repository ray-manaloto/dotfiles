# /code-review high — branch docs/session-audit-20261001-000 (2026-10-02)

Bundled `/code-review high docs/session-audit-20261001-000`, run by audit-000 at HEAD `25c1b8b1` (3 commits past `c6b8e825`). Final report, verbatim:

I found 8 issues in `docs/session-audit-20261001-000` (3 commits past `c6b8e825`). The worst is in `mise.toml`: the new `disable_tools` list leaves out the names mise actually uses for agy and Claude. It says every spelling is listed, but `agy` and `claude` stay enabled.

I checked these directly:
- **`disable_tools` gap:** with the branch's list set, a throwaway `mise.toml` pinning `agy`, `claude` and `ruff` still lists all three. Adding `agy,claude` drops those two while `ruff` stays, so the test can tell the cases apart.
- **mise registry (2026.10.0):** codex has no entry. The only Claude entry is `claude` → `aqua:anthropics/claude-code http:claude`, and agy's is `agy` → `aqua:google-antigravity/antigravity-cli`.
- **Ship's ssh keepalive:** `_PUSH_SSH_KEEPALIVE` is already on `origin/main` (`pr.py:507`), and the push failure is printed at `pr.py:647`.
- **`mise run apt-repo`:** it defaults to apt.llvm.org (`mise.toml:761`).
- **`codex update`:** it exists (codex 0.160.0).
- **typos `HEL` entry:** it is case-exact. `HEL` passes with rc=0; `hel` and `Hel` fail with rc=2.
- **Eager-file size limit (`md-budget`):** passes with rc=0.
- **Credential patterns in the new reports:** none found.

```json
[
  {
    "file": "mise.toml",
    "line": 160,
    "summary": "The new disable_tools list says every spelling is listed, but it leaves out the names mise actually uses: `agy`, `claude`, `aqua:anthropics/claude-code` and `http:claude`. Three of its own entries (`antigravity-cli`, `codex`, `claude-code`) are not mise registry names at all.",
    "failure_scenario": "Any config in this repo that sets `agy = \"…\"` or `claude = \"…\"` still gets a mise-managed copy. That copy can sit ahead of the native installer on PATH, which is exactly what the Ray 2026-10-01 native-only decision forbids. Measured: with the branch list in MISE_DISABLE_TOOLS, `mise ls --current` still shows agy and claude; adding `agy,claude` removes them while the ruff control row stays."
  },
  {
    "file": ".claude/rules/ai-cli-invocation.md",
    "line": 68,
    "summary": "The rule still says 'every mise name for it is in `disable_tools`' for agy. That remains false, because the registry short name `agy` is not in the list. Audit B2 was meant to fix this sentence, and the commit only changed the config.",
    "failure_scenario": "A reader trusts the eager rule and assumes `mise exec -- agy`, or an `agy` pin, can never resolve a mise copy. In fact `agy = \"x\"` installs and shadows the native binary, and nothing flags it until the doctor's native-only check runs."
  },
  {
    "file": ".claude/skills/pr-workflow/SKILL.md",
    "line": 128,
    "summary": "The new rc=141 row says to use the keepalive 'until that lands, re-run ship once', but the keepalive is already on main at the merge-base (pr.py:507, `_push_argv`). The row also contradicts itself: it says 'Not transient — re-running alone repeats it' and then tells you to re-run ship.",
    "failure_scenario": "An agent hits rc=141 even though the keepalive is in place (for example because a user `core.sshCommand` or `GIT_SSH` turns it off, per pr.py:528). The stale text sends it to wait for a fix that has already shipped and to re-run, which the same row says will repeat the failure. The real cause (an ssh config that overrides the keepalive) is never examined. The same text is in the .agents/skills mirror."
  },
  {
    "file": ".claude/skills/pr-workflow/SKILL.md",
    "line": 129,
    "summary": "The verify-apt-pins row sends you to `mise run apt-repo -- --toml --pin` for a superseded Ubuntu security/updates pin. With no `--repo`/`--suite`, that task lists apt.llvm.org's LLVM-22 packages, not the Ubuntu archive.",
    "failure_scenario": "Say `E: Version … for 'curl' was not found` after a security upload. Following the row prints LLVM-repo package versions: curl is missing, or for overlapping names the wrong version comes back. That gets pinned into mise-system.toml, and verify-apt-pins or the CI base build fails again."
  },
  {
    "file": ".claude/skills/pr-workflow/SKILL.md",
    "line": 127,
    "summary": "The rc=1 recovery row tells you to hand-run `git push --force-with-lease=<b>:<old-sha>` with the SHA read from `git ls-remote` just beforehand. That lease protects nothing, and the push skips the ssh keepalive ship adds.",
    "failure_scenario": "Because the 'expected' SHA was just read from the remote, the lease always matches, so this behaves like `--force` and can silently overwrite commits you never fetched, such as a bot push to the branch. The manual push also runs the 6-11 min pre-push suite with no ServerAliveInterval, so it hits the idle disconnect (rc=141) that the next row documents."
  },
  {
    "file": ".claude/skills/pr-workflow/SKILL.md",
    "line": 127,
    "summary": "The new row cites `pr.py:586` for ship's push, but line 586 is `create_rc = _stream(create, ...)` in the PR-create path. The push is at pr.py:643-647, inside `_push_argv`/`push_command`.",
    "failure_scenario": "A reader following the citation to check the 'no lease' claim lands in gh pr create code and finds no push. This repo treats a wrong file:line as stale evidence (`probes-need-a-control-arm.md`, `verify-before-advancing.md`), so it undermines the table's anchors."
  },
  {
    "file": ".claude/skills/session-handoff/SKILL.md",
    "line": 258,
    "summary": "The new sentence says 'only the uppercase harness-evolution-ledger shorthand is allow-listed (`typos.toml`)', but typos.toml allow-lists many identifiers (HOMEs, fpr, sherif, gae, CPY001, CPY, …).",
    "failure_scenario": "An agent reads the absolute claim and concludes a token like `fpr` or `CPY001` in a handoff must be a typo and rewrites it. That edits verbatim evidence or breaks a re-derivable anchor, which the typos.toml comments say must not happen. Also in the .agents mirror."
  },
  {
    "file": "docs/research/kb/reports/agents/session-audit-bugs-2026-10-01c.md",
    "line": 109,
    "summary": "The B2 disposition and its arms only tested short name versus full backend spec for the names already in the list. They never checked mise's registry names (`agy`, `claude`). The resulting FIX-NOW applied a list that still misses the real names, and the report records it as covered.",
    "failure_scenario": "Later sessions cite B2 (as mise.toml:159 now does) as proof that every spelling is disabled. The gap in the first finding is then treated as closed, and the KB #831 twin fix gets the same blind spot."
  }
]
```

## Disposition (audit-000)

All 8 FIX-NOW, applied in the follow-up commit on this branch (see its message). Finding 8 is a correction to `session-audit-bugs-2026-10-01c.md` B2, which stays verbatim; this file records the correction.

## GitHub repos touched

_None — local diff review._
