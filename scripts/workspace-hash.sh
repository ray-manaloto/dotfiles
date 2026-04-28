#!/usr/bin/env bash
# workspace-hash.sh — print an 8-char hash of $PWD to stdout.
#
# Used by mise.toml [tasks.up], [tasks.ps], [tasks.prune] to produce a
# stable per-workspace suffix for Docker container/volume names. Sibling
# clones of dotfiles/ on the same Mac get distinct hashes so volumes
# don't collide (Codex v3 finding — see
# .omc/plans/home-volume-consolidation-draft.md C10/C11/C12).
#
# Single source of truth replaces three identical-but-copy-pasted blocks
# in mise.toml that risked drift on the next refactor.
#
# Portable hash detection: sha256sum is Linux default; shasum is macOS
# default. Try both. Fail loud (no fallback to any other algorithm) if
# neither is available — the contract is "8-char SHA-256 prefix"; using
# md5 or another digest would change volume names across hosts.
set -euo pipefail

if command -v sha256sum >/dev/null 2>&1; then
	printf '%s' "$PWD" | sha256sum | cut -c1-8
elif command -v shasum >/dev/null 2>&1; then
	printf '%s' "$PWD" | shasum -a 256 | cut -c1-8
else
	echo "workspace-hash: neither sha256sum nor shasum found — cannot compute workspace hash" >&2
	exit 1
fi
