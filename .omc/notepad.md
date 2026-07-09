# Notepad — r2 deep-research round (2026-07-09, remote session)

## Session constraints (load-bearing)
- Remote container: Bash fully blocked (PreToolUse hook can't start — no
  Python >=3.14; fails closed). All research via WebSearch/WebFetch/
  Read/Grep; delivery via GitHub MCP push_files to
  `claude/refine-local-plan-7knttu` + draft PR.
- `.omc/` from Ray's Mac absent here; yesterday's unified-image run claims
  carried into Runs A/B as re-verify targets.
- `/graphify` user skill absent here → Run G KB pilot deferred to Mac.

## Findings as they land
- [step 0] Inventory re-verified + persisted:
  `.omc/research/research-20260709-r2-inventory/report.md`. Key reframes
  vs the original brief: Doppler already wired (devcontainer.json:198 +
  contract + smoke tier-2), fnox already in runtime tier
  (mise-runtime.toml:41), issue #83 pre-exists; updater baseline already
  daily (refresh.yml 00:00 auto-merge + ci.yml 02:00 nightly + hosted
  Renovate w/ 6 customManagers; Dependabot 24h floor).
