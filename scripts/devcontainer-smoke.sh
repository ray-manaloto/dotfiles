#!/usr/bin/env bash
# devcontainer-smoke.sh — Tier 1/2/3 smoke checks run INSIDE the devcontainer.
#
# Invocation modes:
#   - postCreateCommand (devcontainer.json): runs automatically on first create
#   - Manual: `devcontainer exec --workspace-folder . scripts/devcontainer-smoke.sh`
#
# Tiers (per ralplan-consensus-devcontainer-build-mise-chezmoi-resync §5):
#   Tier 1 — Tools+hk:      mise ls; which clang++ python uv hk; hk run pre-commit --all
#   Tier 2 — Python+mounts: uv pytest 65/65; stat ~/.ssh ~/.claude /workspaces/${ws}
#   Tier 3 — Sanitizers+lifecycle: clang++ asan+ubsan; mise-user volume owner; github ssh
#
# Tier 4 (CLion remote toolchain) is manual and out of scope here.
set -euo pipefail

WORKSPACE_FOLDER="${WORKSPACE_FOLDER:-/workspaces/$(basename "$PWD")}"

echo "::group::Tier 1 — tools + hk"
mise ls
which clang++ python uv hk
# Use the image-only hk config (installed at /etc/hk/hk.pkl by Dockerfile).
# The project's ./hk.pkl includes host-only steps (docker_bake_check ->
# @devcontainers/cli, agnix, etc.) which are not present inside the image.
# HK_FILE is hk's built-in config-file override (per hk env_variables docs).
HK_FILE=/etc/hk/hk.pkl hk run pre-commit --all
echo "::endgroup::"

echo "::group::Tier 2 — pytest + mounts"
uv run --project python pytest tests/ -x -q
stat "${HOME}/.ssh"
stat "${HOME}/.claude"
stat "${WORKSPACE_FOLDER}"
echo "::endgroup::"

echo "::group::Tier 3 — sanitizers + lifecycle"
td=$(mktemp -d)
cat > "$td/hello.cc" <<'CC'
#include <cstdio>
int main() { std::puts("ok"); return 0; }
CC
clang++ -fsanitize=address,undefined -O1 -g "$td/hello.cc" -o "$td/hello"
"$td/hello"
rm -rf "$td"

echo "[tier3] mise-user volume ownership"
owner="$(stat -c '%U' "${HOME}/.local/share/mise")"
if [ "${owner}" = "${USER}" ]; then
  echo "  OK: ${HOME}/.local/share/mise owned by ${USER}"
else
  echo "  FAIL: ${HOME}/.local/share/mise owned by ${owner}, expected ${USER}" >&2
  exit 1
fi

echo "[tier3] ssh -T git@github.com (transport check)"
# This validates the SSH *transport* to github.com — DNS, TCP, key exchange,
# host-key trust, key file readability — NOT credential completion. Inside
# `devcontainer exec` there is no PTY and no SSH_AUTH_SOCK, so a passphrase-
# protected host key cannot decrypt (the macOS Keychain that normally unlocks
# it is unreachable from Linux). Real git push workflows rely on an IDE
# attaching via the sshd feature with agent forwarding.
#
# IgnoreUnknown swallows macOS-only directives (UseKeychain, etc.) that the
# host's bind-mounted ~/.ssh/config carries in but Linux OpenSSH rejects as
# fatal. Built-in OpenSSH facility (see .claude/rules/use-tool-builtins.md).
#
# A "Permission denied (publickey)" response from github.com is a SUCCESS
# signal for image validation: it proves the full SSH stack reached the
# server and offered a key. Any other failure (DNS, network, host-key
# mismatch, fatal config) is a real bug.
ssh_out=$(ssh -o "IgnoreUnknown=UseKeychain,AddKeysToAgent" \
              -o BatchMode=yes \
              -o ConnectTimeout=10 \
              -T git@github.com 2>&1 || true)
if echo "${ssh_out}" | grep -qE "successfully authenticated|Permission denied \(publickey\)"; then
  echo "  OK: github ssh transport reachable"
else
  echo "  FAIL: github ssh transport broken" >&2
  echo "${ssh_out}" | sed 's/^/    /' >&2
  exit 1
fi
echo "::endgroup::"

echo "devcontainer smoke: tiers 1-3 OK"
