#!/usr/bin/env bash
# Refuse this machine's private paths in anything git would publish. PRIVATE_PATTERNS (one per line) is rendered
# by mise from [vars] at run time, so the patterns themselves never enter the repo.
#   no flags      every tracked file (or the files given)
#   --outgoing    every commit not yet on a remote, branches and tags alike (pre-push)
set -euo pipefail
: "${PRIVATE_PATTERNS:?run this through: mise run privacy:scan}"
pats="$(mktemp)"
trap 'rm -f "$pats"' EXIT
# Short values (a CI runner's HOME, say) would match ordinary text; keep only real paths.
printf '%s\n' "$PRIVATE_PATTERNS" | awk 'length($0) >= 8' >"$pats"
[ -s "$pats" ] || { echo "privacy:scan: no patterns rendered" >&2; exit 2; }

found=0
if [ "${usage_outgoing:-false}" = true ]; then
  while read -r commit; do
    if git show --format='%an <%ae>%n%cn <%ce>%n%B' "$commit" | grep -q -F -f "$pats"; then
      echo "privacy:scan: commit $(git log -1 --format='%h %s' "$commit") holds a private path" >&2
      found=1
    fi
  done < <(git rev-list --branches --tags --not --remotes)
else
  files=()
  if [ -n "${usage_file:-}" ]; then
    eval "files=(${usage_file})"
  else
    while IFS= read -r -d '' f; do files+=("$f"); done < <(git ls-files -z)
  fi
  for f in "${files[@]}"; do
    [ -f "$f" ] || continue
    if grep -I -n -F -f "$pats" -- "$f" | cut -d: -f1 | sed "s#^#privacy:scan: $f:#; s#\$# holds a private path#" >&2; then
      found=1
    fi
  done
fi
[ "$found" = 0 ] || { echo "privacy:scan: replace each host path with ~ or a {{ env.HOME }} template" >&2; exit 1; }
