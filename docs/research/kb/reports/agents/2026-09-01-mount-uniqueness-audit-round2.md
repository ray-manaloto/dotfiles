# Devcontainer mount & volume uniqueness audit — Round 2

**Scope:** the 9 files in `~/.local/state/dotfiles/` (the source of the
unscoped `mounts[0]` bind mount, `docs/research/kb/reports/agents/2026-09-01-mount-uniqueness-audit.md`
Finding 2) beyond `authorized_keys` and `doppler.env`, which round 1 already
covered — not repeated here. One verdict per file: writer, reader, atomic or
not, and whether a second clone/arch can observe or clobber the wrong one.

Status: IN PROGRESS — writing incrementally.

## Finding 1 — `hk-lint.log`: unscoped, real evidence-integrity risk — but HOST-side, not container-side (Sev: MEDIUM)

**Writer:** `python/src/dotfiles_setup/lint.py`. `DEFAULT_LOG_FILE = Path.home()
/ ".local" / "state" / "dotfiles" / "hk-lint.log"` (line 48). `run_guarded()`
(lines ~100-122) does:

```python
log_file.write_text("")   # truncate so the tail is this run only
env = {**os.environ, "HK_LOG_FILE": str(log_file), "HK_LOG_FILE_LEVEL": "debug"}
proc = subprocess.Popen(command, start_new_session=True, env=env)
```

— **not per-run** (no PID/timestamp in the path), a **hard truncate** on
every invocation, and the `hk` subprocess appends debug output to it for the
duration of the run. On timeout, `_print_log_tail()` (lines ~92-99) reads
whatever is currently on disk and prints the last 40 lines as the diagnosis.

**Reader:** the same process (`_print_log_tail`) on timeout, and — per
`.claude/rules/long-running-command-hangs.md` rule 2 — any human or agent told
to "read `~/.local/state/dotfiles/hk-lint.log`" after a lint failure or hang
(that rule explicitly warns the sibling `~/.local/state/hk/hk.log` is a
DIFFERENT, usually-stale file — so this exact path is the one people are
steered to trust).

**Atomic?** No. `write_text("")` truncates in place; there is no lock, no
temp-file+rename, no per-PID path.

**Can a second clone or the second arch of this workspace clobber it?**
Depends on WHERE `mise run lint` runs, and this splits the finding from
round 1's Finding 2 rather than merging with it:

- **Container-side is NOT the collision path.** Confirmed
  `.devcontainer/Dockerfile.host-user:71`: `HOME=/home/${DEVCONTAINER_USER}`
  is a build-time, static Dockerfile `ENV`, baked into the overlay image for
  BOTH arches. Inside either container, `Path.home()` resolves to
  `/home/<user>`, the **home-volume mount target** — already confirmed
  correctly scoped per (workspace × arch) in round 1's Finding 1. So a
  `mise run lint` run *inside* a container writes to that container's own
  scoped home volume, never touching the shared `/tmp/dotfiles-host-state`
  bind-mount path at all. **Two arch containers of this workspace running
  `mise run lint` concurrently do NOT collide on this file** — control-armed
  by re-reading the Dockerfile ENV and the home-volume scoping already
  proven in round 1.
- **Host-side IS the collision path.** On the Mac, `Path.home()` is the same
  `/Users/rmanaloto` for every terminal, regardless of which clone's
  directory `mise run lint` runs from (host-run lint is the documented
  primary path — `AGENTS.md` "Build Type 1 — Local Linting"). Two terminals
  running `mise run lint` concurrently — two windows on the SAME clone, or
  two DIFFERENT clones — both resolve to the identical
  `~/.local/state/dotfiles/hk-lint.log`.

### Concrete interleaving

1. Terminal 1 (clone A, or window 1) runs `mise run lint`; `run_guarded()`
   truncates `hk-lint.log` and starts `hk` writing debug lines into it.
2. Before terminal 1's run finishes, terminal 2 (clone B, or window 2 on the
   same clone) runs `mise run lint` too; its `run_guarded()` **also
   truncates the same file** and starts its own `hk` appending to it.
3. Both `hk` processes now append to the same inode concurrently — the file
   becomes an interleaved mix of two unrelated runs, and whichever
   truncation happened last erases the other run's progress so far.
4. **The recorded `rc` for each process is still correct** — `proc.wait()`
   returns THAT process's own exit code, never crossed with the other run.
   But the diagnostic BODY the rules tell you to read (`_print_log_tail` on
   timeout, or a human/agent manually catting the file after a failure) can
   be entirely — or partially — the OTHER run's output. That is the
   evidence-integrity failure `.claude/rules/verify-before-advancing.md`
   warns about ("read a file-based `rc`, never a piped tail") extended one
   step further: here the FILE ITSELF, not a pipe, can misattribute.

**Is this plausible, or contrived?** Not contrived. This session's own live
evidence (round 1) shows 15+ concurrently-existing dotfiles clones/worktrees
on this Mac, and running `mise run lint` from two of them (or two windows on
one) inside the same ~1-minute window (observed: the current 304,027-byte
log spans exactly one `hk run check --all`, which itself is normally a
sub-2-minute operation) is an ordinary devloop pattern, not an edge case.

**Severity: MEDIUM.** The file is disposable (regenerated every run, never a
source/`.git` artifact) and the pass/fail signal (`rc`) is never wrong — but
the diagnostic artifact you are told to trust at exactly the moment
(a hang or failure) you most need it can misattribute a different run's
content, silently.

## Finding 2 — `sync-ghcr.io_..._dev.json`: real cross-workspace state pollution, confirmed by code AND live data (Sev: MEDIUM-HIGH)

**Writer:** `python/src/dotfiles_setup/sync.py`, `write_sync_record()`
(line 272). **Path:** `_state_file(image_ref)` (lines 228-229) — keyed
**only on the base image ref** (`ghcr.io/ray-manaloto/dotfiles-devcontainer:dev`,
sanitized to a filename), never on workspace or arch.

**Reader:** `read_sync_record()` (lines 226-267), consumed by
`SyncStatus.container_current` / the `mise run sync` convergence check that
decides whether an overlay rebuild is needed.

**Atomic?** No. `write_sync_record()` does a plain **read-modify-write**:
`existing = read_sync_record(image_ref)` (line 297) → merges into
`containers = dict(existing.containers)` (line 303) → writes back via
`path.write_text(json.dumps(...))` (line 320) — no lock, no temp-file +
atomic rename. Classic TOCTOU shape.

**Is the base-image sharing itself a bug?** No — `registry_digest` and
`local_image_id` describe the ONE shared base image this Mac's Docker daemon
holds; sharing those fields across every clone is correct and intentional
(the module docstring says so explicitly: "the record stays shared across
architectures, not keyed per-arch" — avoids every clone re-detecting a base
pull redundantly).

**The bug is inside `containers`.** `container_image_id(names)`
(lines 436-456) filters `docker ps` by **both**
`names.workspace_label` AND `names.arch_label` — i.e. it resolves "the
overlay image ID for THIS workspace's THIS-arch container," genuinely
per-(workspace × arch) data. `write_sync_record()` then stores it as
`containers[names.arch] = cid` (lines 306-308) — **keyed by arch alone**,
inside a file keyed by image_ref alone. **There is no workspace dimension
anywhere in the storage path** for a value that is workspace-specific by
construction.

### Live confirmation

This Mac has 15+ distinct dotfiles clones/worktrees (round 1's
`docker volume ls` enumeration: `checkout`, `arm64-main`,
`codex-task-orchestration-v2`, `goal-history`, `issue-753-writer-lease`,
`issue-763`, `pr671`, five `repo-*` variants, plus this workspace), any of
which can run `mise run sync` against the SAME base image ref. Yet exactly
**ONE** `sync-ghcr.io_...json` file exists on this Mac, and its content
right now is:

```
{"registry_digest": "sha256:02027ef3...", "local_image_id": "sha256:abe74f57...",
 "containers": {"amd64": "sha256:670921fd..."}}
```

— one entry total, for one arch. There is no per-workspace fan-out; whichever
workspace synced last for a given arch is the only one whose convergence
state survives on disk.

### Concrete interleaving

1. Workspace A (`273897ea`, amd64) runs `mise run sync` → `write_sync_record`
   reads the current record → computes A's own overlay id via
   `container_image_id` (workspace+arch filtered) → writes
   `containers["amd64"] = A_cid`.
2. Workspace B (e.g. `8ca71197`, also amd64) runs `mise run sync` shortly
   after. Its `read_sync_record` sees A's record (same `registry_digest`/
   `local_image_id` — both point at the identical shared base image) → merges
   `containers["amd64"] = B_cid` over the SAME dict key → **A's entry is
   gone**.
3. Because `write_text()` is non-atomic and there is no lock, this is ALSO a
   genuine race if A and B sync concurrently (not just sequentially):
   whichever `write_text()` lands last wins outright, independent of read
   order.
4. Workspace A next checks `SyncStatus.container_current` (any `mise run
   sync`, or `land`/`ship`'s convergence gate) and reads
   `containers["amd64"] = B_cid` — **B's overlay id, attributed to A's
   workspace**. Compared against A's real current overlay id, `A_cid ==
   B_cid` is false, so `container_current` reports `False` (stale) even
   though A's own overlay genuinely is current.

**Direction of the defect is fail-safe, not fail-silent**: a clobbered entry
reads as "stale," triggering an unnecessary rebuild rather than skipping a
needed one — it never causes a workspace to run against a container it
should have rebuilt. But it directly matches what was asked: **a second
clone CAN read a verdict computed for a different workspace**, and the
registry-ref-only filename is **not sufficient scoping** for the
per-workspace `containers` payload it holds. In practice this manifests as
spurious rebuild churn across every clone sharing this Mac and this base
image, every time two of them sync the same architecture close together.

**Fix shape** (not implemented — read-only audit): key `containers` by
`f"{names.hash}:{names.arch}"` rather than `names.arch` alone, reusing the
already-tested `workspace_hash()` helper (`devcontainer_names.py:153`) —
smaller and safer than adding new locking logic, per
`.claude/rules/use-tool-builtins.md`.

## Finding 3 — `dag-tick.lock`: correctly unscoped for what it protects (Sev: none — control-armed negative)

**Writer/locker:** `python/src/dotfiles_setup/dag_tick.py:231` —
`LOCK_PATH = Path.home() / ".local" / "state" / "dotfiles" / "dag-tick.lock"`,
with the comment: *"One tick at a time — a second tick that finds the lock
held exits 0 silently rather than racing a respawn/stop against the first."*

**What `dag_tick` actually is** (traced via the module + `mise.toml:624`'s
comment "Fired every 60s by the [LaunchAgent]"): a **host-only, per-Mac**
background-job reaper for Claude Code's own background nodes
(`JOBS_DIR = Path.home() / ".claude" / "jobs"`,
`DAEMON_DIR = Path.home() / ".claude" / "daemon"`), invoked via a macOS
LaunchAgent that execs `~/.local/bin/mise` directly. **It has no
relationship to devcontainers, workspaces, or CPU architecture at all** — it
is one global process tending one global job roster for this Mac, full stop.

**Does the lock serialise clones that should run independently, or protect a
scope it doesn't cover?** Neither — it protects EXACTLY the scope it should:
"at most one dag-tick process running on this Mac at a time," which is
correct because the resource it guards (`~/.claude/jobs`, `~/.claude/daemon`)
is itself Mac-wide, not per-clone. A per-workspace lock here would be WRONG
— it would let two ticks race against the same shared job roster.

**Verdict:** not a devcontainer mount-uniqueness defect. It happens to live
in `~/.local/state/dotfiles/` purely as a filing convention ("host state this
project's tooling owns"), not because it needs container/workspace scoping.
Confirmed by control arm: re-reading `dag_tick.py`'s own domain (host
LaunchAgent, host job dir) shows the lock's scope and the resource's scope
already match.

## Finding 4 — `guard-fail-open.log`: shared by design, and the design is sound (Sev: none — control-armed negative)

**Writer:** `scripts/pretooluse-guard.sh`, `fail_open()` (lines 26-32):

```bash
LOG="${DOTFILES_GUARD_FAILOPEN_LOG:-$HOME/.local/state/dotfiles/guard-fail-open.log}"
fail_open() {
  mkdir -p -- "$(dirname -- "$LOG")" 2>/dev/null &&
    printf '%s\t%s\t%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$1" "$PWD" >>"$LOG" 2>/dev/null
  exit 0
}
```

**Reader:** `python/src/dotfiles_setup/command_audit.py`,
`FAIL_OPEN_LOG` (line 600) + `fail_open_summary()` (lines 606-630), consumed
by the session-end command-audit report.

**Atomic?** The write is `printf ... >>"$LOG"` — **append**, not truncate
(the opposite pattern from Finding 1 and Finding 2). A single `printf` of one
short tab-separated line is well under `PIPE_BUF`, so POSIX guarantees the
kernel `write()` for an `O_APPEND` fd is atomic — concurrent appends from
different sessions interleave AT THE LINE LEVEL, not the byte level; no
line can be spliced from two writers.

**Is the shared path itself a bug?** No — and this is explicitly documented,
not accidental: `command_audit.py:598-599`: *"Per-user state, not per-repo:
the wrapper may fail open precisely because the repo's toolchain is not
resolvable, so the record cannot depend on it."* A guard that fails open
because `uv`/Python 3.14 is missing cannot reliably compute a per-repo path
either — scoping this log by repo would be self-defeating for the exact
failure mode it exists to catch.

**Can you tell which session/clone a given fail-open belongs to?** Yes — the
brief's framing ("a shared path means you cannot tell which session's guard
failed open") does not hold here: every line embeds `$PWD` as its third
field, so each entry is self-identifying by repo/clone even though the file
is shared. The reader is also defensive against interleaving noise:
`_FAIL_OPEN_FIELDS = 3` and `fail_open_summary()` skips any line with fewer
than 3 tab-separated fields ("a short line is a partial write, not a
fail-open — skip it rather than count it wrongly," line 604) — so even the
one theoretical hazard append-mode doesn't fully rule out (two writers
racing to open/create the file for the very first `mkdir -p` while it does
not yet exist) degrades to "one record dropped," never "one record
misattributed."

**Verdict:** correctly shared, correctly append-only, correctly
self-identifying per line, correctly defensive on read. This is the pattern
Findings 1 and 2 should have used and did not. No fix needed.

## Finding 5 — `ssh-agent-port` / `ssh-agent-proxy.pid` / `ssh-agent.target` / `host-ssh-proxy.log`: confirmed DEAD residue, four independent checks (Sev: none — cleanup only)

Content: `ssh-agent-port`=`63597`, `ssh-agent-proxy.pid`=`81264`,
`ssh-agent.target`=`/var/run/com.apple.launchd.NlopaSJTzb/Listeners`,
`host-ssh-proxy.log`=0 bytes. All four share mtime **Apr 9 2026**.

The brief is right that mtime alone doesn't settle liveness (a 0-byte log
could still be actively `>>`-appended-to-nothing by a live but silent
process, and a stale-looking pid file could be reused by PID recycling).
Four independent, code-based checks, none relying on the timestamp:

1. **No writer/reader in the tracked tree.** `grep -rln` for all four
   filenames across the entire repository returns only two files: this
   audit's own round-1 report, and two *historical research reports*
   (`docs/research/runs/research-20260407-ssh-devcontainer/report.md` and
   `.../research-20260409c-dockerdesktop-ssh/stages/stage-2.md`) that
   **describe the now-superseded design in prose** — neither is executable
   code, and neither is a current writer.
2. **Never tracked as a state file, and their writer was deleted.**
   `git log --diff-filter=A` for these exact filenames returns nothing (they
   were always gitignored runtime state, never committed — expected). But
   `git log -S"ssh-agent-proxy"` (round 1) found the SOURCE that wrote them:
   `8cba29b refactor(devcontainer): delete dead Python SSH proxy code (#77
   stage 2)` and `5a9de96 fix(devcontainer): bound ssh-bridge failure path
   to ≤3.5s` — a host-TCP↔container-socket proxy, deliberately removed.
3. **The recorded PID is not running.** `ps -p 81264` returns no matching
   process (checked fresh this round, independent of round 1's check).
4. **No LaunchAgent registered for it.** `launchctl list | grep -i
   "ssh.agent\|ssh.proxy\|dotfiles"` shows only macOS's own built-in
   `com.openssh.ssh-agent` (unrelated — a different service under a similar
   name) and the two `dev.mise.dotfiles-dag-*` agents (Finding 3's
   mechanism). No `*-ssh-agent-proxy-*` or `*-host-ssh-proxy-*` label
   exists in the launchd registry at all — if a daemon were meant to be
   running this, launchd doesn't know about it either.

**Verdict:** confirmed dead by four independent read-only checks (source
search, git history of the deleting commit, process table, launchd
registry) — not inferred from mtime. These four files are inert leftovers
from the pre-Docker-Desktop-native-socket SSH proxy, superseded by the
`/run/host-services/ssh-auth.sock` bind mount covered in round 1's
Finding 3. No corruption risk (nothing reads or writes them), but they are
misleading clutter in the same directory that holds live, load-bearing
state — worth a housekeeping delete in the same change that fixes Findings
1 and 2.

## Round 2 summary

| File | Writer | Atomic write? | Second clone/arch can clobber the WRONG one? | Verdict | Severity |
|---|---|---|---|---|---|
| `hk-lint.log` | `lint.py:run_guarded()` — fixed path, hard truncate every run | No | Host-side only (container `HOME` resolves to the already-scoped home volume, confirmed); two host-side `mise run lint` invocations (any clones/windows) DO clobber/interleave | Evidence-integrity risk on the diagnostic log, `rc` itself unaffected | MEDIUM |
| `sync-ghcr.io_..._dev.json` | `sync.py:write_sync_record()` — read-modify-write, no lock | No | Yes — `containers[arch]` has no workspace key; confirmed live (15+ clones, 1 file, 1 entry/arch) | Cross-workspace state pollution → spurious rebuilds (fail-safe direction) | MEDIUM-HIGH |
| `dag-tick.lock` | `dag_tick.py` — host-only LaunchAgent lock | N/A (lock, not data) | No — by design; the resource it guards is itself host-wide | Correctly scoped for its actual (non-devcontainer) domain | None |
| `guard-fail-open.log` | `pretooluse-guard.sh:fail_open()` — append-only, self-identifying via `$PWD` per line | Yes (POSIX `O_APPEND` atomicity for a short line) | No — every entry names its own repo/session; reader defensively drops partial lines | Correctly designed shared audit log | None |
| `ssh-agent-port` / `-proxy.pid` / `.target` / `host-ssh-proxy.log` | Dead — no current writer exists | N/A | No — confirmed dead via 4 independent checks | Cleanup-only residue | None |

Net for the full 11-file directory (rounds 1 + 2 combined): **two real
unscoped-and-racy state files** (`doppler.env`, `sync-ghcr.io_..._dev.json`),
**one evidence-integrity risk** (`hk-lint.log`), **one correctly-designed
shared file that should be the template for fixing the other two**
(`guard-fail-open.log`), **one correctly host-wide lock**
(`dag-tick.lock`), and **four dead files** (the ssh-agent-proxy trio +
`host-ssh-proxy.log`). `authorized_keys` (round 1) is unscoped but
content-idempotent, so low severity despite the shared path.

## GitHub repos touched

_None._ This round also read only files inside the local `dotfiles` repo
working tree and local `docker`/`git`/`launchctl`/`ps` state; no external
repo, doc site, or API was consulted.

---
Status: ROUND 2 COMPLETE (new file).
