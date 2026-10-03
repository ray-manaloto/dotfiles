# #1505 — /code-review high

- Target: merge SHA `461ee74b18c6db0e3961a556abf5577689b80e81` (chore/agy native only)
- Lens: built-in `/code-review high` (forked, task `a11562043cd9d8bec`, 15 tool uses, 217s)
- Verdict: **FINDINGS** — 7

## Verbatim result

```json
[
  {
    "file": ".claude/rules/ai-cli-invocation.md",
    "line": 7,
    "summary": "The eager rule now contradicts itself. Line 7 still says \"Invoke every AI CLI through `mise exec --`\", while the new line 68 says never to rely on `mise exec -- agy`.",
    "failure_scenario": "An agent reading the rule's opening directive (which this commit did not change) runs `mise exec -- agy ...`. antigravity-cli is now unpinned and disabled, so this resolves whatever `agy` is on PATH, possibly a leftover mise copy. That is the exact stale-binary hazard lines 66-68 forbid, and two lines of the same always-loaded rule give opposite instructions."
  },
  {
    "file": ".claude/rules/ai-cli-invocation.md",
    "line": 67,
    "summary": "The rule says \"every mise name for it is in `disable_tools`\", but the project list only has the short name `antigravity-cli`. The full backend key `aqua:google-antigravity/antigravity-cli` is missing.",
    "failure_scenario": "This commit's own comment says the project `disable_tools` REPLACES the global list here. The global config notes that matching is literal on the config key and that every spelling must be listed. So any config that names the tool by its full key is not disabled inside this repo. Examples: a stale worktree, the knowledge-base checkout before e91fb84b, or a later `mise use aqua:google-antigravity/antigravity-cli`. mise would then install or activate a mise agy, and the rule's claim is false."
  },
  {
    "file": "mise.toml",
    "line": 171,
    "summary": "The commit found that the project `disable_tools` replaces the global list, but only re-added `antigravity-cli`. The global entries `aqua:openai/codex`, `codex`, `claude-code`, `npm:@anthropic-ai/claude-code` and `github:anthropics/claude-code` are silently dropped for every mise call in this repo.",
    "failure_scenario": "Ray's rule is that claude, codex and agy come only from native installers. Inside this repo, a config or `mise use` that names `codex` or `claude-code` by any of those keys is no longer disabled, so the native-only policy quietly stops applying here. This is also a patch on the symptom: the repo copies one entry of a user-global list. The global config already moved the real guard to `auto_install_disable_tools`, which projects do not override. The fix should list every spelling or rely on that global mechanism, not hand-sync one entry."
  },
  {
    "file": ".claude/rules/ai-cli-invocation.md",
    "line": 26,
    "summary": "The canonical agy invocation was switched to a different binary (native `~/.local/bin/agy`, 1.2.14) with no new probe in the evidence note. The re-probe section (line 99) also still says \"run the pinned CLI's own help\", though agy is no longer pinned.",
    "failure_scenario": "This breaks the rule's own instruction (`.claude/rules/ai-cli-invocation.md` § Re-probe rule): \"Before changing any invocation, run the installed CLI's own help ... Record positive and negative arms in the evidence note.\" `docs/rules-evidence/ai-cli-invocation.md` still only has the 2026-09-25 `mise exec -- agy` 1.2.11 probes. The new canonical `--print` form is unproven on the binary it now names."
  },
  {
    "file": ".claude/rules/ai-cli-invocation.md",
    "line": 68,
    "summary": "The rule forbids relying on bare `agy` because a leftover mise copy may sit first on PATH. But the adopted antigravity plugin, which is the sanctioned entry point, always resolves bare `agy` from PATH, and the change does nothing to remove the leftover copy.",
    "failure_scenario": "The plugin's `scripts/agy-delegate.sh:261/409`, `scripts/doctor.sh:261` and `hooks/check-agy.sh:10` all use `command -v agy` / `agy`. If the stale mise copy the rule warns about is first on PATH, every `antigravity:*` delegate, review or doctor run uses it. `eval_cases.py`'s `tier1.lanes-declared-or-degraded` also checks PATH, so it would count that stale copy as the lane resolving. The commit adds no `mise uninstall`, reshim or doctor check, so the hazard is documented, not removed."
  },
  {
    "file": "mise.toml",
    "line": 114,
    "summary": "The new comment says \"the former `antigravity-cli` aqua pin is gone from every mise config\". That was false when committed, and tracked docs still contradict it.",
    "failure_scenario": "The knowledge-base `mise.toml` still pinned antigravity-cli until e91fb84b, about 40 minutes later. KB `currency.toml` still tracks `[tool.antigravity-cli]`. `docs/specs/mise-native-dotfiles-plan.md:594/605` still plans `antigravity-cli` as a user-global mise pin (tier U). A later reader who trusts the comment won't look for remaining pins, and the spec tells them to re-add one."
  },
  {
    "file": ".claude/rules/ai-cli-invocation.md",
    "line": 26,
    "summary": "The canonical invocation hard-codes `$HOME/.local/bin/agy`, a host-only path, but the rule says it applies to all direct CLI calls from this repo. Nothing installs agy there inside the devcontainer at this commit.",
    "failure_scenario": "An agent working in the devcontainer, the repo's real dev environment, follows the canonical block. It gets `no such file or directory` (rc 127) instead of a declared \"lane unavailable, fall back to Opus\" path. The rule gives no in-container alternative or presence check before the call."
  }
]
```

All seven findings are documentation or config consistency problems. None is a crash in shipped code. The top three are the main ones: the rule contradicts itself, the "every mise name is disabled" claim is false, and the project `disable_tools` list drops the global codex/claude-code entries.

Most findings come from reading the diff and the tree at the commit. I did run a few probes:
- **Plugin:** the antigravity plugin (0.28.0) resolves bare `agy` from PATH.
- **Shims:** no mise `agy` shim exists on this host right now, so finding 5's PATH hazard isn't live today.
- **Knowledge-base:** its pin was removed in e91fb84b.
- **Line 7:** the current worktree's line 7 now treats agy differently from codex and opencode, which suggests finding 1 was fixed later.

This review was read-only. I didn't write anything to `findings.md`, so the report needs to be saved by you.

## Lane triage (second read) — appended after receipt

Re-read at main `785c3708`.

| # | Severity at merge | At HEAD | Disposition |
|---|---|---|---|
| 1 | MED | FIXED: `ai-cli-invocation.md:7` now says "codex and opencode through `mise exec --`, agy by its absolute native path" | none |
| 2 | MED | FIXED: `mise.toml:161-169` lists `antigravity-cli`, `agy` and `aqua:google-antigravity/antigravity-cli` | none |
| 3 | MED | FIXED: the same list carries `codex`, `aqua:openai/codex`, `github:openai/codex`, `npm:@openai/codex` and `claude…` (comment `mise.toml:154-160` cites B2) | none |
| 4 | LOW | STILL TRUE: `docs/rules-evidence/ai-cli-invocation.md:118-126` records only the 2026-09-25 `mise exec -- agy` 1.2.11 probes, with no native-path probe of the canonical `--print` form | noted, below the MED bar |
| 5 | LOW | Plugin resolves bare `agy`, but the reviewer measured no mise `agy` shim on the host, so the hazard is latent | noted |
| 6 | LOW | STILL TRUE: `docs/specs/mise-native-dotfiles-plan.md:594/605` still lists `antigravity-cli` as a tier-U user-global mise pin | noted (stale spec prose) |
| 7 | MED | FIXED: `.devcontainer/scripts/on-create.sh:40-45` installs native agy into the home volume (#1526) | none |

No MED+ finding survives at HEAD, so no issues were filed. The LOW items 4 and 6 are offered to the coordinator as one docs touch-up.

## GitHub repos touched

- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) — the reviewer cross-checked KB commit e91fb84b and KB `currency.toml`
