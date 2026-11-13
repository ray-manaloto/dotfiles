---
okf_version: "0.2"
type: "report"
title: "Agent-config linters: agnix and cclint"
description: "Why dotfiles runs agnix as the hk gate on its agent files and cclint as a report-only step, and the behaviour of each that the config relies on."
---

# Agent-config linters: agnix and cclint

This is research from 2026-11-13. The owner's ruling was to adopt both:
- agnix gates the agent files from hk;
- cclint reports on the Claude files and never fails a commit;
- the global `lint:agents` task runs both on the live configs.

Both tools were read at the released versions pinned in the global mise config: agnix 0.61.0, and cclint v0.63.0 (commit e67f0ff). Both were run on this repo and on the live configs.

## Compared

| | agnix (agent-sh/agnix) | cclint (dotcommander/cclint) |
|---|---|---|
| Lints | Claude Code, Codex, OpenCode, Gemini, Cursor and more, plus MCP, AGENTS.md and skills; 758 rules with stable IDs (README.md:20) | Claude Code only: agents, skills, commands, CLAUDE.md, settings and plugins |
| Install | Release tarballs per platform, each with a `.sha256` and a build-provenance attestation (`.github/workflows/release.yml:167`). mise's `github:` backend locks the three platforms with `provenance = "github-attestations"` | No release assets. The `go:` backend builds it with the global Go on every machine, and it reports version `dev` |
| Files from hk | Takes paths (`agnix [PATHS]...`); a path given on the command line is checked even when `.agnix.toml` excludes it | Takes files and directories (`cclint lint <files-or-dirs>`); it errors on any file that isn't .md or .json |
| Tuning | `.agnix.toml`: `tools`, `exclude`, `[rules] disabled_rules`, per-path `[[overrides]]`, inline suppression; output as text, JSON, SARIF or GitHub annotations | `--fail-on` (error, warning, suggestion) and baselines. It has no per-rule disable |
| Network | Telemetry is opt-in, and the release build compiles out the HTTP code | No network code |
| Prior art | hk steps in mokevnin/agentic-coding-design-patterns (`hk.pkl:31-34`) and hexlet-components/hexlet-ci-app (`hk.pkl:18-21`) | No external hook or CI user found |
| Churn | Releases every 1 to 3 days, from one main author; rule IDs and severities move between releases | A single maintainer; it follows each Claude Code release |

## What each found here

- **agnix**, with `.agnix.toml`, on the repo: 0 errors and 1 warning, a negative instruction with no alternative in the global AGENTS.md. Without the config it reported:
  - 1 error and 34 warnings because it reads the workflow docs (under an `agents/` folder) as Claude subagent files;
  - two false positives: a repo path it reads as a home folder, and a secret's name it reads as a secret.
- **cclint** found one real issue that agnix missed: an XML-like tag in an agent's description. It is fixed in the same change.

## How it runs

- **Pins:** the global mise config pins `github:agent-sh/agnix` and `go:github.com/dotcommander/cclint`, locked for macos-arm64, linux-x64 and linux-arm64.
- **hk steps:**
  - `agnix` runs on the agent files and fails the hook on an error.
  - `cclint` runs on the Claude .md and .json files with `allow_failure = true` (hk 2.9.0 `pkl/Config.pkl:798-812`): its findings print, and the hook goes on.
  - Warnings don't fail either step. agnix's `--strict` waits for the rewrite of the instruction files.
- **Global `lint:agents` task:** cclint reports on `~/.claude`, then agnix checks the Claude, Codex and OpenCode configs and decides the exit code. Skills synced from claude.ai and plugin files are linted too, so not every finding is ours to fix.

## Re-check on a bump

agnix changes rules between releases. On each bump, run `agnix .` in the repo and `mise run lint:agents`, then update `.agnix.toml` for any new false positive before merging.
