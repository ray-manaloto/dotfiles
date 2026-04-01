#!/usr/bin/env bash
set -euo pipefail

RUN_ID="${1:?usage: branch_remediator.sh <run-id> [--push]}"
BRANCH="codex/ci-fix/${RUN_ID}"

if git show-ref --verify --quiet "refs/heads/${BRANCH}"; then
  git switch "${BRANCH}"
else
  git switch -c "${BRANCH}"
fi

if [[ "${2:-}" == "--push" ]]; then
  git push -u origin "${BRANCH}"
fi

printf '%s\n' "${BRANCH}"
