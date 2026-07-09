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
- [Run A verified, 3-vote CONFIRMED] Web sessions: custom base images NOT
  supported ("not yet supported" — setup script on Ubuntu 24.04 or
  docker-compose sidecar are the only paths); ~4 vCPU/16GB RAM/30GB disk;
  docker+dockerd+compose ARE installed and ghcr.io is on the trusted
  allowlist — but 38GB image > 30GB disk, only a slimmed sidecar image
  fits; setup script (root, ~5-min budget, non-zero exit blocks session) +
  ~7-day filesystem snapshot cache = the de-facto custom-image mechanism
  (tools AND pulled docker images persist across sessions).
- [Run B verified, 3-vote CONFIRMED] 5-stage Dockerfile (devcontainer-base
  → clang-builder-cold → p2996-export → devcontainer →
  devcontainer-runtime; :dev = stage 5); warm path = registry manifest
  probes (:base-/:p2996-/:dev-<hash16>) + digest-pinned named contexts,
  NOT layer cache; dev-hash folds whole Dockerfile + runtime toml/lock,
  base/p2996 hashes cover only sentinel slices → a new lean stage OUTSIDE
  the sentinels busts only :dev-<hash> once, heavy caches stay warm = the
  key preservation property for any topology delta.
- [ops] Session restart killed Run C mid-verify; resumed via
  resumeFromRunId wf_37f14652-0dc (research replays cached). A/B
  synthesizers didn't write report.md (B hit a session usage limit,
  resets 10:50pm UTC) — dedicated writer agents dispatched instead.
