---
name: tool-admission-check
description: Vet a new tool or backend before adding it to the devcontainer image or mise manifest in this repo. Use when proposing a new tool, backend, registry, or package source and require docs-backed rationale, local feasibility proof, and a recorded acceptance or rejection decision.
---

# Tool Admission Check

## Overview

Do not add a new image tool blindly.

## Required Evidence

- upstream docs or release source
- chosen backend rationale
- local feasibility proof
- smallest validation command

## Minimum Validation

- `mise test-tool <tool>`
- `plugins/dotfiles-build-optimizer/scripts/local_preflight.sh tool <tool>`

## Memory Update

Record accepted or rejected tool decisions with `failure-memory`.
