#!/usr/bin/env bash
# ensure-docker-up.sh — make sure the Docker daemon is reachable.
#
# Used by hk steps that depend on `docker ps` (docker_bake_check,
# devcontainer_json_validate). Without this preflight, those steps
# fail with a confusing "no such file or directory" when Docker Desktop
# is stopped.
#
# Behavior:
#   1. If `docker info` succeeds → exit 0 immediately.
#   2. If the `docker desktop` CLI plugin is available → `docker desktop
#      start` and poll `docker info` until ready (or timeout).
#   3. Otherwise (Linux runner, Colima, no Docker Desktop) → fail with a
#      clear message instead of hanging.
#
# Timeout is generous (60s) because cold-starting Docker Desktop on macOS
# can take 20-40s.
set -euo pipefail

TIMEOUT_SECONDS="${ENSURE_DOCKER_TIMEOUT:-60}"

if docker info >/dev/null 2>&1; then
	exit 0
fi

if ! command -v docker >/dev/null 2>&1; then
	echo "ensure-docker-up: docker CLI not on PATH" >&2
	exit 1
fi

if ! docker desktop --help >/dev/null 2>&1; then
	echo "ensure-docker-up: Docker daemon is down and 'docker desktop' CLI is not available." >&2
	echo "  Start your Docker runtime manually and re-run." >&2
	exit 1
fi

echo "ensure-docker-up: Docker Desktop is not running — starting it..." >&2
# `docker desktop start` requires the Docker.app process to already be
# running on macOS; if the app is fully quit it can hang. `open -a
# Docker` launches the app, then `docker desktop start` brings up the
# engines and is a no-op if they are already starting.
if [ "$(uname -s)" = "Darwin" ] && ! pgrep -x "Docker Desktop" >/dev/null 2>&1; then
	# Don't suppress `open -a Docker` failure: a missing/corrupt Docker.app
	# is the most actionable error we could surface here. Still tolerate
	# non-zero exit because `pgrep` may race the app (already starting).
	open -a Docker >&2 || echo "ensure-docker-up: 'open -a Docker' returned non-zero — continuing to docker desktop start" >&2
fi
# Capture DD start stderr/stdout to a log so timeout diagnostics include
# the actual failure reason (e.g., Electron tray IPC broken-pipe seen on
# 2026-04-28). Without this, the user sees only a generic 60s timeout.
DD_START_LOG="${TMPDIR:-/tmp}/ensure-docker-up.$$.log"
docker desktop start >"${DD_START_LOG}" 2>&1 &
start_pid=$!

cleanup() {
	kill "${start_pid}" 2>/dev/null || true
	rm -f "${DD_START_LOG}" 2>/dev/null || true
}

deadline=$(( $(date +%s) + TIMEOUT_SECONDS ))
while [ "$(date +%s)" -lt "${deadline}" ]; do
	if docker info >/dev/null 2>&1; then
		echo "ensure-docker-up: Docker Desktop is up." >&2
		cleanup
		exit 0
	fi
	sleep 2
done

echo "ensure-docker-up: timed out after ${TIMEOUT_SECONDS}s waiting for Docker Desktop to become ready." >&2
echo "ensure-docker-up: last 20 lines of 'docker desktop start' output:" >&2
tail -20 "${DD_START_LOG}" >&2 || true
cleanup
exit 1
