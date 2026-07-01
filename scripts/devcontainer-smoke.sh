#!/usr/bin/env bash
# devcontainer-smoke.sh — Tier 1/2/3 smoke checks run INSIDE the devcontainer.
#
# Invocation modes:
#   - postCreateCommand (devcontainer.json): runs automatically on first create
#   - Manual: `devcontainer exec --workspace-folder . scripts/devcontainer-smoke.sh`
#
# Tiers (per ralplan-consensus-devcontainer-build-mise-chezmoi-resync §5):
#   Tier 1 — Tools+hk:      mise ls; which clang++ python uv hk; hk run pre-commit --all
#   Tier 2 — Python+mounts: uv pytest 187/187; stat ~/.ssh ~/.claude /workspaces/${ws}
#   Tier 3 — Sanitizers+lifecycle: clang++ asan+ubsan; mise-user volume owner; github ssh
#
# Tier 4 (CLion remote toolchain) is manual and out of scope here.
set -euo pipefail

echo "[devcontainer-smoke][start]"

WORKSPACE_FOLDER="${WORKSPACE_FOLDER:-/workspaces/$(basename "$PWD")}"

echo "::group::Tier 1 — tools + hk"
echo "[tier1] image identity — mise-system config hash"
# Gap A (image identity): the Dockerfile COPYs .devcontainer/mise-system.toml
# verbatim to the base SYSTEM config /usr/local/share/mise/config.toml. If the
# in-image hash differs from the mounted repo file, this container is running a
# STALE/cached image (e.g. devcontainer-cli reused a vsc-dotfiles-<hash>
# overlay) — rebuild before trusting any downstream check.
#
# #148: read $MISE_SYSTEM_CONFIG_FILE (the COPY target), NOT
# ${MISE_CONFIG_DIR}/config.toml. MISE_CONFIG_DIR is deliberately overridden at
# runtime (Dockerfile.host-user + devcontainer.json) to the USER config dir
# /home/<user>/.config/mise, a chezmoi-rendered file in the persistent home
# volume — a different file that false-fails this check on a current base.
sys_cfg="${MISE_SYSTEM_CONFIG_FILE:-/usr/local/share/mise/config.toml}"
repo_cfg="${WORKSPACE_FOLDER}/.devcontainer/mise-system.toml"
if [ -f "$repo_cfg" ]; then
  expected_cfg_hash="$(sha256sum "$repo_cfg" | cut -d' ' -f1)"
  actual_cfg_hash="$(sha256sum "$sys_cfg" | cut -d' ' -f1)"
  if [ "$actual_cfg_hash" != "$expected_cfg_hash" ]; then
    echo "  FAIL: in-image mise config ${actual_cfg_hash} != repo mise-system.toml ${expected_cfg_hash} (stale/cached image — rebuild)" >&2
    exit 1
  fi
  echo "  OK: image built from current mise-system.toml (${actual_cfg_hash})"
else
  echo "  SKIP: repo mise-system.toml not found at ${repo_cfg}"
fi
mise ls
# #143: assert the EXACT declared (tool, backend, version) set is installed, not
# just that mise reports zero (missing). Parse + compare logic lives in python
# (dotfiles_setup.image.verify_tools_main — zero-bash-logic), sharing the same
# core as build_smoke_script's injected assertion so the two smoke paths can't
# diverge (the #148/#150 lockstep lesson).
uv run --project python dotfiles-setup image verify-tools
which clang++ python uv hk
# Use the image-only hk config (installed at /etc/hk/hk.pkl by Dockerfile).
# The project's ./hk.pkl includes host-only steps (docker_bake_check ->
# @devcontainers/cli, agnix, etc.) which are not present inside the image.
# HK_FILE is hk's built-in config-file override (per hk env_variables docs).
HK_FILE=/etc/hk/hk.pkl hk run pre-commit --all
echo "::endgroup::"

echo "::group::Tier 2 — pytest + mounts + secrets"
uv run --project python pytest tests/ -x -q
stat "${HOME}/.ssh"
stat "${WORKSPACE_FOLDER}"

echo "[tier2] Doppler secrets injection"
# Verify doppler secrets were injected via --env-file. DOPPLER_PROJECT and
# DOPPLER_CONFIG are always present in any doppler download; use them as
# canary keys. Count total doppler-sourced env vars as a sanity check.
if [ -z "${DOPPLER_PROJECT:-}" ] || [ -z "${DOPPLER_CONFIG:-}" ]; then
  echo "  FAIL: DOPPLER_PROJECT or DOPPLER_CONFIG not set (doppler secrets not injected — is doppler authenticated on the host?)" >&2
  exit 1
fi
doppler_count=$(env | grep -cE "^(DOPPLER_PROJECT|DOPPLER_CONFIG|DOPPLER_ENVIRONMENT|EXA_API_KEY|GITHUB_TOKEN|BRAVE_API_KEY|GEMINI_API_KEY)=" || true)
if [ "${doppler_count}" -lt 3 ]; then
  echo "  FAIL: only ${doppler_count} doppler canary keys found (expected >= 3)" >&2
  exit 1
fi
echo "  OK: doppler secrets injected (${doppler_count} canary keys, project=${DOPPLER_PROJECT}, config=${DOPPLER_CONFIG})"
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

echo "[tier3] reflection compilers — ref pin + functional"
# The sanitizer block above uses the conda clang++ on PATH; it never touches
# the P2996 reflection compiler. Assert the clang-p2996 build (a) is a real
# bloomberg/clang-p2996 build and (b) its embedded source commit matches the
# CLANG_P2996_REF pinned in docker-bake.hcl — without this a stale/wrong-ref
# (or missing) reflection compiler is a silent false positive. Then compile a
# std::meta program with both reflection compilers (-fsyntax-only; the
# static_assert forces compile-time reflection evaluation, and clang-p2996's
# -stdlib=libc++ binary can't be run — libc++.so.1 is off the loader path).
test -x /opt/clang-p2996/bin/clang++ || { echo "  FAIL: /opt/clang-p2996/bin/clang++ missing" >&2; exit 1; }
test -x /opt/gcc-latest/bin/g++ || { echo "  FAIL: /opt/gcc-latest/bin/g++ missing" >&2; exit 1; }
expected_ref="$(grep -A2 'CLANG_P2996_REF' "${WORKSPACE_FOLDER}/docker-bake.hcl" | grep -oiE '[0-9a-f]{40}' | head -1)"
[ -n "${expected_ref}" ] || { echo "  FAIL: could not parse CLANG_P2996_REF from docker-bake.hcl" >&2; exit 1; }
p2996_version="$(/opt/clang-p2996/bin/clang --version)"
echo "${p2996_version}" | grep -q 'bloomberg/clang-p2996' || { echo "  FAIL: /opt/clang-p2996 clang is not a bloomberg/clang-p2996 build" >&2; exit 1; }
actual_ref="$(echo "${p2996_version}" | grep -oiE '[0-9a-f]{40}' | head -1)"
if [ "${actual_ref}" != "${expected_ref}" ]; then
	echo "  FAIL: clang-p2996 built from ${actual_ref} but docker-bake.hcl pins ${expected_ref}" >&2
	exit 1
fi
echo "  OK: clang-p2996 ref ${actual_ref} matches docker-bake.hcl"
# Gap C (#141): link + RUN, not just -fsyntax-only. The static_assert forces
# compile-time reflection evaluation; the RUN proves the emitted binary
# executes. clang-p2996's -stdlib=libc++ binary needs libc++.so.1, which is off
# the default loader path, so bake an rpath at the discovered in-image libc++
# dir (link-flag-only — no Dockerfile change, no cold rebuild). A p2996 libc++
# binary runs under Rosetta/QEMU (verified #141), so no emulation gate needed.
p2996_libcxx_so="$(find /opt/clang-p2996/lib -name 'libc++.so.1' 2>/dev/null | head -n1)"
[ -n "${p2996_libcxx_so}" ] || { echo "  FAIL: clang-p2996 libc++.so.1 not found in image" >&2; exit 1; }
p2996_libcxx_dir="$(dirname "${p2996_libcxx_so}")"
rd="$(mktemp -d)"
cat >"${rd}/refl.cpp" <<'CPP'
#include <meta>
#include <iostream>
enum class Color { Red, Green, Blue };
consteval int count_enumerators() {
  return static_cast<int>(enumerators_of(^^Color).size());
}
static_assert(count_enumerators() == 3);
int main() {
  int n = count_enumerators();
  std::cout << "reflection enumerators=" << n << std::endl;
  return n == 3 ? 0 : 1;
}
CPP
/opt/gcc-latest/bin/g++ -std=c++26 -freflection "${rd}/refl.cpp" -o "${rd}/refl-gcc" || { echo "  FAIL: gcc-latest reflection link failed" >&2; exit 1; }
"${rd}/refl-gcc" || { echo "  FAIL: gcc-latest reflection binary did not run to return 0" >&2; exit 1; }
/opt/clang-p2996/bin/clang++ -std=c++2c -freflection -freflection-latest -fexpansion-statements -stdlib=libc++ -Wl,-rpath,"${p2996_libcxx_dir}" "${rd}/refl.cpp" -o "${rd}/refl-clang" || { echo "  FAIL: clang-p2996 reflection link failed" >&2; exit 1; }
"${rd}/refl-clang" || { echo "  FAIL: clang-p2996 reflection binary did not run to return 0" >&2; exit 1; }
rm -rf "${rd}"
echo "  OK: both reflection compilers link + run a std::meta program"

echo "[tier3] home volume ownership + seed survivors"
# v6 single-home-volume contract: the whole /home/${USER} dir is a
# persistent named volume. Assert (a) mise install dir is user-owned
# (same invariant as pre-v6), and (b) the chezmoi-managed shell files,
# .ssh, and mise install dir were all seeded correctly on first create.
owner="$(stat -c '%U' "${HOME}/.local/share/mise")"
if [ "${owner}" = "${USER}" ]; then
  echo "  OK: ${HOME}/.local/share/mise owned by ${USER}"
else
  echo "  FAIL: ${HOME}/.local/share/mise owned by ${owner}, expected ${USER}" >&2
  exit 1
fi

for f in "${HOME}/.bashrc" "${HOME}/.zshrc" "${HOME}/.profile"; do
  if [ -e "$f" ]; then
    echo "  OK: ${f} exists"
  else
    echo "  FAIL: ${f} missing — chezmoi init may have wiped seeded files" >&2
    exit 1
  fi
done
for d in "${HOME}/.ssh" "${HOME}/.local/share/mise" "${HOME}/.local/tmp"; do
  if [ -d "$d" ]; then
    echo "  OK: ${d} exists"
  else
    echo "  FAIL: ${d} missing" >&2
    exit 1
  fi
done

# TMPDIR must be set to the home-volume path so tools that respect
# $TMPDIR land on the persistent volume, not the ephemeral overlay.
expected_tmpdir="${HOME}/.local/tmp"
if [ "${TMPDIR:-}" != "${expected_tmpdir}" ]; then
  echo "  FAIL: TMPDIR=${TMPDIR:-<unset>}, expected ${expected_tmpdir}" >&2
  exit 1
fi
echo "  OK: TMPDIR=${TMPDIR}"

echo "[tier3] SSH agent forwarding + github auth"
# Real end-to-end SSH auth via Docker Desktop's native magic socket at
# /run/host-services/ssh-auth.sock (see .omc/research/research-20260409c-dockerdesktop-ssh/).
# Runtime-pinned to Docker Desktop — Colima has no equivalent; issue #78 tracks
# eventual Colima replication.
expected_sock="/run/host-services/ssh-auth.sock"
if [ "${SSH_AUTH_SOCK:-}" != "${expected_sock}" ]; then
  echo "  FAIL: SSH_AUTH_SOCK=${SSH_AUTH_SOCK:-<unset>}, expected ${expected_sock}" >&2
  exit 1
fi
if [ ! -S "${expected_sock}" ]; then
  echo "  FAIL: ${expected_sock} is not a socket (Docker Desktop magic mount missing — are you on Docker Desktop? 'docker context ls' should show desktop-linux *)" >&2
  exit 1
fi
if ! ssh-add -L 2>/dev/null | grep -q '^ssh-'; then
  echo "  FAIL: ssh-add -L shows no identities (host ssh-agent empty? run 'ssh-add ~/.ssh/id_*' on the Mac)" >&2
  ssh-add -L 2>&1 | sed 's/^/    /' >&2 || true
  exit 1
fi
ssh_out=$(ssh -o BatchMode=yes -o ConnectTimeout=10 -T git@github.com 2>&1 || true)
if echo "${ssh_out}" | grep -q "successfully authenticated"; then
  echo "  OK: github ssh full auth via /run/host-services/ssh-auth.sock"
else
  echo "  FAIL: github ssh did not reach successful auth" >&2
  echo "${ssh_out}" | sed 's/^/    /' >&2
  exit 1
fi
echo "::endgroup::"

echo "devcontainer smoke: tiers 1-3 OK"

echo "[devcontainer-smoke][end]"
