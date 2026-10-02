# Host load review — 2026-10-02

> Persisted verbatim by the coordinator (dotfiles-20261002.coordinator) at receipt.
> The subagent (read-only Opus general-purpose) could not write this path itself:
> the shared checkout refused writes from the un-isolated bg session.

## Summary returned by the subagent

### Top 5 recommendations

1. **Take `command-audit` off SessionEnd** — the largest single attributable load. At 15:52, **7 concurrent `mise → uv → python dotfiles-setup command-audit` chains** (21 procs, ≈117% CPU, 1.57 GB), 4 orphaned to ppid 1 and running 4-7.5 min. Each scans the 50 latest sessions + every nested transcript = **814 MB** of JSONL (`command_audit.py:81`, `:263-270`). SessionEnd is capped at 60 s (`$CC/hooks.md:3346`, `:430`) so the configured `timeout: 120` is clamped and the cancelled grandchildren are never reaped; output is discarded (every run overwrites `.agent/command-audit.md`). Only 4 dotfiles sessions wrote transcripts in the last hour, yet ~10 new chains started in 6 min. Fix: make it on-demand (task exists, `mise.toml:770`), or if kept: `async: true` + single-instance `flock` + scan only the payload's `transcript_path`. Control arm: `ps` count of chains (7 today → expect ≤1); a second concurrent run exits on the lock.
2. **Host-wide heavy-gate lock** — one `fcntl.flock` on a well-known path (e.g. `~/.local/state/dotfiles/heavy-gate.lock`) taken by `gate run pytest`, ship's gate phase, the pre-push test step, and KB `kb_setup.gates`. Would have prevented today's KB `test` 57 s → ~13 min and both timeouts (#838). Pattern already exists at `codex_lane.py:300-315`. Control arm: start gate A then B; B reports "waiting" and runs only after A releases.
3. **Cap xdist on the shared host** — KB runs `-n auto` (`mise.toml:460`); xdist 3.8.0 without psutil resolves that to `os.cpu_count()` = 12 workers (`xdist/plugin.py:16-55`), and `kb_setup/gates.py:277,583-586` runs lint/test/brain-audit/graph-size concurrently. Native fix: `PYTEST_XDIST_AUTO_NUM_WORKERS=4` in the KB `test` task env (`--maxprocesses` is the other native cap), plus `--dist loadgroup` + `xdist_group` so the 756 MB-graph tests share one worker. Control arm: xdist prints "created: 4/4 workers" with the env vs 12/12 without.
4. **One dotfiles suite per ship, not two** — ship runs pytest as a gate (`pr.py:340-341`), then `git push` (`pr.py:523`) triggers the hk pre-push `test-hook-isolated` pytest again (`hk.pkl:872-890`): ≈2 × 365 s serial. ADR-0001 forbids local `HK_SKIP_STEPS`, so drop ship's own pytest gate and let the stricter pre-push step block the push. Control arm: `ps` sample during a ship counts pytest starts (2 → 1); a failing test still blocks the push and auto-merge is not armed.
5. **Cut per-tool-call hook cost** — a dotfiles Bash call spawns ≈12-14 processes / 4 Python starts: guard (5, `scripts/pretooluse-guard.sh:36,40`), graphify guard (4-5; runs `dotfiles-setup` which launches a second Python `graphify`, `graphify.py:966`), planning-with-files (2). Measured under load: guard 1.2-1.9 s, graphify guard **3.9 s**. Estimate (not measured): ~800 process starts/min across 18 sessions. Fix: merge the two guards into one Python invocation; call the venv entrypoint directly instead of `uv python find` + `uv run`. Claude's own git calls go through the mise shim: **1.88 s vs 0.13 s** for `/usr/bin/git`; one bg-spare had 4 `(mise)` + 1 shimmed git at ≈116% CPU. Putting `/usr/bin` or mise's install dir ahead of shims would fix it — a user-level change (Ray's call).

### Direct answers

- **Load sources now:** load 128/121/111 at 15:52, then 39/74/94 by 15:59. In order: SessionEnd `command-audit` scans; shim-and-git chains from Claude's internal git calls; statusline scripts (`subagent-statusline.sh` 59.6%); per-tool-call hook Pythons. The 18 bg-spares hold 10.1 GB RSS but little CPU; the docker VM 9.1 GB at ≈5% CPU. The dotfiles pytest is serial; it had been running inside ship for 22 min (recorded gate time 365 s).
- **Heavy-slot discipline:** advisory only. `flock|fcntl|lockfile|semaphore|filelock|portalocker` across gate/ship/lint code in both repos = 0 hits; the same grep hits `codex_lane.py:70,310`, `dag_tick.py`, `session_store.py`, KB `currency/sync.py`, so the probe discriminates.
- **Worker caps:** yes, cap them; the env knob is native and needs no code; a load-derived count would be custom and only if a fixed cap is insufficient.

### Unverified

- What triggers the ~10 SessionEnd runs per 6 min (spare-session recycling, `claude agents` exits, `/clear`). One parent was `claude agents`, one an interactive `--brief` session; the rest unattributed.
- Whether `graphify` and `python3` resolve to shims inside bg sessions' hook PATH.
- The tool-call rate is an estimate.

---

## Full report

Read-only investigation of host slowness (macOS arm64, 12 logical cores = 8 P + 4 E,
96 GiB, swap 4.0/5.1 GB used). No process was signalled, no gate/pytest/build was run.
Raw probe output: `.agent/kb/raw/host-load-2026-10-02/` (`ps.txt` 15:52, `ps-2.txt` 15:58,
`rstate-{1,2,3}.txt`, `hook-timing.txt`, `uptime.txt`, `vm_stat.txt`).

Load at probe start 15:52: **128.10 121.17 110.73**, 115 processes in `R` state.
At 15:58-15:59: 38.7 / 74.1 / 94.2 (falling), 10-18 processes in `R`.

### 1. What generates the load (snapshot 15:52, `ps.txt`)

| category | procs | %CPU sum | RSS | note |
|---|---:|---:|---:|---|
| `dotfiles-setup command-audit` (SessionEnd hook) chains | 21 (7 python + 7 uv + 7 mise) | **116.9** | 1.57 GB | 7 concurrent python scans; oldest 7m35s; 4 orphaned to ppid 1 |
| `git` (all) | 5 | 125.7 | 187 MB | Claude-internal `git -c core.askPass= …` / `rev-parse` / `symbolic-ref` |
| `(mise)` shim stubs + `shims/git` | 5 | 116 | 250 MB | bg-spare 14677 spawned 4 `(mise)` + 1 `shims/git` at once |
| statusline scripts | 5 | 76.6 | 105 MB | `subagent-statusline.sh` 59.6% at 1 s old |
| PreToolUse guards | 4 | 31.3 | 146 MB | per tool call |
| `claude bg-spare` | 18 | 21.6 | **10.1 GB** | |
| `claude --bg-pty-host` | 20 | 0.4 | 1.7 GB | |
| docker VM | 1 | 5.1 | 9.1 GB | 2 devcontainers up + `fnox exec -- devcontainer up` in flight |
| pytest | 1 (ship → serial `pytest tests/ -x -q`, 22m32s) | ~0 | 180 MB | recorded gate duration 365 s |
| kb-setup serve / serve-memory | 16 | 0 | 245 MB | 4 idle pairs |

#### 1a. SessionEnd `command-audit` (largest attributable source)
- `.claude/settings.json` SessionEnd `*` → `mise -C … run command-audit -- --output …/.agent/command-audit.md`, timeout 120.
- Scans 50 latest sessions + all nested transcripts (`command_audit.py:81`, `:263-270`), full read + json.loads per line: **814 MB** window (project dir 2.1 GB, 151 roots, 2,694 transcripts).
- SessionEnd budget capped at 60 s (`$CC/hooks.md:3346-3351`, `:430`); cancelled tree not reaped — 4 of 7 mise parents re-parented to pid 1, ran 4-7.5 min. Output discarded; all runs overwrite the same file (mtime 15:12 while 7 in flight).
- Fires on every reason (`clear`, `resume`, `other`…, `$CC/hooks.md:3318-3327`); parents seen: `claude agents` (28990), interactive `--brief` (22097). 4 root transcripts touched in the last hour vs ~10 new chains in ~6 min.
- KB has the same shape: SessionEnd `brain-transcript-audit` + `kb-session-reflect` (both `mise run`, t=60).

#### 1b. Per-tool-call hook churn
dotfiles Bash call: pretooluse-guard (bash → `uv python find` → subshell → `uv run` → python; 5 procs, 1 Python; `scripts/pretooluse-guard.sh:36,40`) + graphify-hook-guard (bash → uv run → python → `graphify` Python, `graphify.py:966`; 4-5 procs, 2 Python) + planning-with-files 3.21.0 pre-tool-use (sh → python3 fast path, `claude-hook.sh:108-123`; 2 procs) + zsh snapshot ≈ **12-14 processes, 4 Python starts**. Edit/Write adds PostToolUse `uv run … mise-config-context` + pwf; Read/Glob = graphify read chain + pwf; Agent adds `hook_selfcheck subagent-contract` twice.
KB Bash call: `.venv/bin/graphify hook-guard` + `uv run kb-setup hookguard` + `mise run kb-instruction-shell-write` (→ uv run kb-setup) + pwf ≈ 8 processes, 4 Python starts.
Measured under load (`hook-timing.txt`): pretooluse-guard 1.24/1.60/1.94 s; graphify-hook-guard search **3.89 s**; KB mise-run hook 0.59 s; bare venv python 0.12 s.
Estimate (not measured): ~70 tool calls/min across 18 sessions × ~12 ≈ 800 spawns/min, ~280 Python starts/min.

#### 1c. mise shim on Claude's git
`shims/git` is the mise Mach-O binary; `which -a git` lists the shim first. `shims/git --version` 1.88 s vs `/usr/bin/git --version` 0.13 s (load ~40). jq, uv, python3 and graphify are also shimmed.

#### 1d. pytest/xdist
dotfiles serial everywhere (`mise.toml:289-295`, `pr.py:340-341`). KB `mise.toml:460` `-n auto`; xdist 3.8.0 without psutil → `os.cpu_count()` = 12 (`xdist/plugin.py:16-55`). `kb_setup/gates.py:277` `CONCURRENT_SAFE={"lint","test","brain-audit","graph-size"}` runs together (`:583-586`). 756 MB graph.json loaded per worker by graph tests; #838 timeouts with load 19→84.

### 2. Heavy-slot discipline
Advisory only: zero lock primitives in `dotfiles_setup/{lint,pr,gate_result,session_gate,fnhook_gates}.py` or KB `kb_setup/gates.py`. Control arm: the same grep hits `codex_lane.py:70,310`, `dag_tick.py`, `session_store.py`, `codex_verdict.py`, KB `currency/sync.py`.

### 3. Native caps and double suite
xdist: `PYTEST_XDIST_AUTO_NUM_WORKERS` overrides auto (`plugin.py:16-24`); `--maxprocesses` caps auto/logical (`:84-90`, `:322-323`); `-n logical` needs psutil; none is load-aware. Recommend env cap in the KB test task; `--dist loadgroup` + `xdist_group` for graph tests. Double suite: ship pytest gate (`pr.py:340-341`) then pre-push `test-hook-isolated` (`hk.pkl:872-890`); ADR-0001 forbids local `HK_SKIP_STEPS`, so drop ship's own pytest gate (or key a typed result to the pushed tree SHA, custom). Trade-off: lengthens the ssh-idle window already covered by `_PUSH_SSH_KEEPALIVE` (`pr.py:504-508`).

### 4. Ranked recommendations
1. Take command-audit off SessionEnd (or async + flock + scope to `transcript_path`). Small. Prevents 7 orphaned 4-7 min scans (~1.2 cores, 1.6 GB). Control arm: ps count 7 → ≤1; a second concurrent run exits on the lock.
2. Host-wide heavy-gate flock shared by dotfiles gate/ship/pre-push and kb gates. Medium. Prevents the #838 13-min/timeout class and concurrent ships. Control arm: B waits until A releases; a crashed holder releases on fd close.
3. `PYTEST_XDIST_AUTO_NUM_WORKERS=4` on the KB test task, plus loadgroup for graph tests. Trivial. Control arm: "created: 4/4 workers" vs 12/12.
4. One dotfiles suite per ship. Small. Saves ~365 s serial per ship. Control arm: 2 → 1 pytest starts; a failing test still blocks the push.
5. Hook cost: merge the guards into one Python, call the venv entrypoint directly, take `shims/` off Claude's git PATH (user-level, Ray's call). Small-medium. Control arm: no-op Bash round-trip time; `(mise)` child count under bg-spares.
Also: limit concurrent bg sessions (18 bg-spares = 10 GB; no native limit verified).

### Open / unverified
- What triggers the ~10 SessionEnd chains per 6 min.
- Whether bg-session hook PATH resolves graphify/python3 to shims.
- Tool-call rate is an estimate.

## GitHub repos touched
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — settings.json hooks, scripts, command_audit.py, pr.py, hk.pkl, mise.toml
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) — mise.toml test task, kb_setup/gates.py, hooks, issue #838
- [pytest-dev/pytest-xdist](https://github.com/pytest-dev/pytest-xdist) — installed 3.8.0 source for -n auto / --maxprocesses / PYTEST_XDIST_AUTO_NUM_WORKERS
- [OthmanAdi/planning-with-files](https://github.com/OthmanAdi/planning-with-files) — installed plugin 3.21.0 hooks/claude-hook.sh (cache copy only)
