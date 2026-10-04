# KB codex sandbox posture: advisory verdict (codex-sol-advisor)

Status: evidence gathered; codex gpt-6.1-sol xhigh verdict pending (appended below when done).

## Probe results (codex-cli 0.160.0, scratch /Users/rmanaloto/.claude/jobs/f4b75d61/tmp/sbx-probe-m4x9v, probe file removed)

Probe 1, protection (via `codex sandbox -P <builtin>`; the subcommand has NO `-s`, it requires `-P`; built-ins `:workspace`, `:read-only`, `:danger-full-access` exist, `:danger-no-sandbox` does not):
| profile | ordinary.txt | .git/hooks/pre-commit | .codex/hooks.json | .agents/x.md | .git/config-probe |
|---|---|---|---|---|---|
| :workspace | WROTE | DENIED | DENIED | DENIED | DENIED |
| :read-only | DENIED | DENIED | DENIED | DENIED | DENIED |
| :danger-full-access | WROTE | WROTE | WROTE | WROTE | WROTE |
| plain sh (no codex), control | WROTE | WROTE | WROTE | WROTE | WROTE |
Both directions arm: the same script writes everything unsandboxed and is denied under :workspace, so the probe discriminates. Caveat: `codex sandbox` is not `codex exec -s`; arm 3 below uses the real exec path.

Probe 2/3 via real `codex exec` (model gpt-6.1-sol, effort low, probe lanes only), sandbox banner line from each log:
| arm | banner | NET (curl api.github.com) | uv-cache write | workspace write |
|---|---|---|---|---|
| A -s workspace-write | `workspace-write [workdir, /tmp, $TMPDIR]` | Could not resolve host | DENIED | WROTE |
| B + `-c sandbox_workspace_write.network_access=true` | `... (network access enabled)` | 200 | DENIED | WROTE |
| C + `--add-dir ~/Library/Caches` | `[..., /Users/rmanaloto/Library/Caches] (network access enabled)` | 200 | WROTE | WROTE |
| D -s danger-full-access | `danger-full-access` | 200 | WROTE | WROTE |
Network-off is real by default and `network_access=true` restores egress on 0.160.0. Caveats: results are the lane's self-report (the probe file existed afterwards, consistent with C/D; A/B denial is not separately artifact-proven, issue #1039 warns lane rc is not trustworthy); `sandbox_workspace_write.network_access` is NOT honoured by `codex sandbox -P :workspace` (still no DNS), only by exec.

## Claims in the prior draft: verified or refuted
- codex 0.160.0 installed: VERIFIED. `codex exec --help` has `-s read-only|workspace-write|danger-full-access`, `--add-dir`, `-C`, `-o`, `-p` (now `$CODEX_HOME/<name>.config.toml` layering, `CONFIG_PROFILE_V2`).
- "kb-codex has no sandbox override plumbing": REFUTED. `/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/python/src/kb_setup/codex_run.py:84` `sandbox_override`, `:100` use, `:647-707` CLI `--sandbox`; review path forwards as `-c sandbox_mode=` (`:515-516`). Path in draft (`kb_setup/codex_run.py`) was wrong; real path is under `python/src/`.
- `--dangerously-bypass-hook-trust` always passed: VERIFIED `codex_run.py:117` (exec path).
- `--add-dir ~/Library/Caches` only under workspace-write: VERIFIED `codex_run.py:107-112`.
- "dotfiles #1039/#1142 say workspace-write cuts the network": NOT SUPPORTED by those issues. #1039 evidence is out-of-tree writes (`~/.local/state/dotfiles`, `ps`, `~/.local/share/mise`) failing under workspace-write; #1142 is the `--ephemeral` spawn bug and a read-only lane lacking network. Neither mentions workspace-write blocking network (grep "network": 0 hits in #1039; #1142 hits are about the read-only lane). The network claim is true (probe A) but is KB's own `codex_run.py:17-19` fact and the dotfiles doc's, not those issues'. The real dotfiles driver is out-of-tree writes, which does not apply to KB lanes unless they run dotfiles-style gates.
- KB do-not #13 stale cites: confirmed present at `/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/.claude/rules/do-not.md:167-174` (rust-v0.152.1 line numbers); mechanism claim ("lose read-only protection") confirmed behaviourally by probe 1, though the protection is a workspace-write feature.

## codex advisor call: FAILED to deliver a verdict (twice)
- Run 1 (`/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.agent/kb/raw/codex-sol-advisor-verdict-sbx-95211-1791070954.md`, rc=0): codex loaded the repo's research-sweep skill and spent the run on the "strict-five" research audit; `fnox` failed `Keychain: secret 'DOPPLER_TOKEN' not found` (service `mde-fnox`), output was "RESEARCH INCOMPLETE". Only residue: "advisory recommendation remains option 2 for KB#863, with coordinator-owned commits" (no reasoning supplied).
- Run 2 (same prompt plus an explicit "no research runner" line; `...-r2.md`, rc=0): same derailment. Residue: "the earlier NO verdict remains local-file design advice" (a NO to something unstated).
- Neither is a usable verdict. No reasoning was backfilled here. Treat the one-line "option 2, coordinator commits" as an unexplained codex lean, not a ruling. Cause is likely the AGENTS/skill instructions codex loads from the dotfiles cwd (not isolated by `PLANNING_DISABLED`). A re-run from a cwd outside the repo, or via the claude-advisor escalation (token-routing trigger 1), is the caller's call.

## What the verified evidence supports (probe/code facts only, not codex's judgement)
- Protection is real and mode-specific: .git, .codex, .agents denied under workspace-write; all writable under danger-full-access (probe 1, both arms plus unsandboxed control).
- workspace-write+network+--add-dir works on 0.160.0 for network and uv cache (arms B, C); KB already plumbs it (`codex_run.py:100-117`) and already has `--sandbox` override (`:647-707`), so a no-sandbox implementer lane needs no new code.
- The dotfiles precedent's cited reasons (#1039 out-of-tree writes) are about dotfiles gates; #1039/#1142 do not cite a network cut. "Matching dotfiles" is not itself evidence KB lanes need it.
- Residual: `--dangerously-bypass-hook-trust` (`codex_run.py:117`) plus writable .codex under no-sandbox is a planted-hook path; a post-lane hash manifest detects but cannot prevent a hook that fires inside the same lane.

## GitHub repos touched
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — issues #1039, #1142 read
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) — codex_run.py, do-not.md #13 read
