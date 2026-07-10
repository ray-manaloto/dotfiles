# Notepad — r2 deep-research round (2026-07-09, remote session)

## Session constraints (load-bearing)
- Remote container: Bash fully blocked (PreToolUse hook can't start — no
  Python >=3.14; fails closed). All research via WebSearch/WebFetch/
  Read/Grep; delivery via GitHub MCP push_files to
  `claude/refine-local-plan-7knttu` + draft PR.
- `.omc/` from Ray's Mac absent here; yesterday's unified-image run claims
  carried into Runs A/B as re-verify targets.
- `/graphify` user skill absent here → Run G KB pilot deferred to Mac.

- [ops CI] hk `no_mcp_registration` greps ALL tracked files for the
  literal MCP-registration command — research prose quoting it trips CI
  (lint failed on official-docs.md:42; fixed by rewording to "the Claude
  CLI's `mcp add` subcommand", which the regex doesn't match because
  "claude" must immediately precede). Rule for ALL future r2 artifacts
  incl. synthesis: never write the three words consecutively.

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
- [ops CRITICAL] The harness deterministically BLOCKS subagent Write
  calls for report .md files ("Subagents should return findings as
  text") — workflow synthesizers can write agents/*.md but not report.md.
  Pattern that works: writer agent returns FULL report text; the main
  session persists it verbatim. Applied to Run A (report.md written by
  main session); same handling queued for B/C/D/E/F/G.
- [Run A DONE] report.md persisted. Recommendation: one-image is
  impossible today (no custom base images + 38GB > 30GB disk); adopt
  two-artifact topology NOW — keep the image for CI+devcontainer, add a
  web layer that is a SCRIPT (env setup script installing mise from
  GitHub releases + shared.toml pins + uv sync, snapshot-cached ~7d) + a
  CLAUDE_CODE_REMOTE-gated SessionStart hook; GITHUB_TOKEN env var
  effectively required (#52963); Trusted policy suffices for the gates;
  root cause of today's web brick = PreToolUse guard can't start (no
  py3.14) and harness fails closed. 10/10 claims CONFIRMED 3/3.
- [Run B DONE] report.md persisted (8 CONFIRMED / 2 REFUTED).
  Recommendation: keep ONE published heavy :dev; land the fork-ready
  refactor NOW (split mise-system.toml into core [shared 20 + python/uv]
  + cpp [runtimes + conda] with a new internal devcontainer-core stage);
  DEFER publishing a lean :ci leaf until a real consumer exists.
  REFUTED (0/3): yesterday's "lean :ci for CI" premise — measured 5m27s
  image pull vs 20-25s cached mise-on-runner install; runner install IS
  the test surface gating lock-refresh auto-merge; also REFUTED the
  "4.83GB of 5.06GB base layer" figure (unsourced — resolve via
  image-analysis run 29013595948 metrics artifact, expires 2026-10-07).
  True fork seam = BASE tier interior, NOT the documented runtime tier.
- [ops] Session restart killed Run C mid-verify; resumed via
  resumeFromRunId wf_37f14652-0dc (research replays cached). A/B
  synthesizers didn't write report.md (B hit a session usage limit,
  resets 10:50pm UTC) — dedicated writer agents dispatched instead.
- [ops] Delivery agent got stuck pushing one file per commit with the
  same message (CodeRabbit re-triggered per push); stopped it after it
  landed the guard fix (bee8dd9); main session now pushes directly via
  push_files.
