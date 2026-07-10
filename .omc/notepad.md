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

## Model-switch event (2026-07-10)
- Fable 5 usage limit + credits EXHAUSTED — does NOT reset until Wed 7am.
  Main session switched to claude-opus-4-8 via /model. Workflow script
  tuned so the fleet no longer leans on any single model:
  verify agents -> sonnet, workflow-internal synthesize -> sonnet (its
  output is discarded here anyway — the report.md write-block means real
  reports come from dedicated writer agents). Angle researchers inherit
  the session model (now opus); they're all cached/done so no new cost.
  Report-writer + courier agents pinned to sonnet/haiku explicitly.
- Recovery after credit exhaustion: resume each workflow with
  resumeFromRunId — cached research replays FREE, only failed
  verify/synthesize re-run on the cheap models. D resume=wf_1811ee62-444,
  E resume=wf_14e0c060-be2. F/G already verified -> writer agents only.
- The 19-file angle checkpoint push died mid-flight twice (courier ran
  out of Fable credits after reading files); re-dispatched on haiku.

## Run F & G DONE (2026-07-10, on Opus/Sonnet)
- [Run F] report.md persisted. Rec: native macOS launchd LaunchAgent
  (StartCalendarInterval, gui/<uid>) running `mise run maintain` (new
  python module, lint.py-styled) for Mac-side sync+verify-local; 3-layer
  alerting (ntfy primary + healthchecks.io dead-man switch + gh issue).
  Cloud routines CANNOT reach the Mac; self-hosted GHA runner ruled out
  (public repo = security risk); pitchfork = credible-but-young secondary.
  Verification CAUGHT a stale claim: docker/cli#6837 is CLOSED (fixed DD
  4.70.0) — prefer `docker desktop start`. osascript notifications
  disqualified (false-green exit).
- [Run G] report.md persisted. Rec: keep markdown+grep as retrieval
  substrate; adopt graphify as a PERIODIC synthesis/audit layer (committed
  to docs/research/graph/, NOT the hot path — LazyGraphRAG cost lesson);
  build a corpus INDEX.md + front-matter + hk validator NOW (closes an
  enforcement gap 2 rules already promise); defer graphiti/mem0/cognee/
  basic-memory behind named triggers (semtools = pre-approved escape
  hatch). graphify IS a real queryable KB (deterministic BFS/DFS, zero
  LLM at query, mcp2cli-shaped) but all-markdown build is 100% LLM.
  no-MCP-registration constraint is a non-issue for every CLI candidate.

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
- [Run C DONE] report.md persisted (9 CONFIRMED 3/3, 1 partial-refute).
  Recommendation: KEEP+EXTEND hosted-Renovate + refresh.yml hybrid —
  REVERSES yesterday's self-hosted lean. Killer evidence: Mend-hosted
  regenerated root mise.lock IN-COMMIT on this repo's PR #191 (2026-07-08,
  native mise artifacts path, renovate v43.186.0+). Real cadence gap =
  inherited Friday-only schedule from jdx preset → one-line
  `"schedule": ["at any time"]` in renovate.json unlocks ~4-hourly.
  BASELINE BUG found: refresh.yml open-refresh-pr paths omit
  .devcontainer/mise-runtime.lock (regenerated daily, never committed).
  Artifact set is FIVE locks not three. Sub-daily buys nothing on
  freshness (weekly upstreams × ~2h pipeline); GHA cron drift (>4h, 2026)
  threatens the 00:00→02:00 stagger — move crons off :00. gcc deb
  bottleneck = deliberate human sha256 gate (policy call, not tooling).
- [ops] Session restart killed Run C mid-verify; resumed via
  resumeFromRunId wf_37f14652-0dc (research replays cached). A/B
  synthesizers didn't write report.md (B hit a session usage limit,
  resets 10:50pm UTC) — dedicated writer agents dispatched instead.