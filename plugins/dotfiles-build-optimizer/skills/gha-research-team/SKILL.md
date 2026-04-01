---
name: gha-research-team
description: Launch a bounded multi-agent research team for a failed CI run in this dotfiles repo. Use when a normalized GitHub Actions failure report exists and you need parallel analysis across docker-bake, Dockerfile, chezmoi, mise, devcontainer, hk, Python automation, synthesis, and verification. Prefer OMX/team orchestration first and Codex native subagents as fallback.
---

# GHA Research Team

## Overview

Split one failed CI run into specialist lanes, then synthesize one recommended remediation plan.

## Required Lanes

- Docker Bake lane
- Dockerfile/multi-stage lane
- chezmoi lane
- mise lane
- devcontainer lane
- hk lane
- Python automation lane
- synthesis lane
- verifier/critic lane

## Expectations

Each lane must return:

- current defect
- probable root cause
- smallest local validation command
- recommended fix
- confidence

## Tool Split

Use the GitHub plugin for:

- branch discovery
- commit comparison
- PR search
- PR metadata or patch retrieval

Use `gh` for:

- run/job/log retrieval
- artifact-aware Actions triage

## Synthesis Rule

Do not return parallel essays. Return one ranked remediation plan.
