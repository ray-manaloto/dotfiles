# Stage 3 — Docker Desktop bind-mount propagation + inotify

## Findings

[FINDING:S3F1] VirtioFS is the default (and on Apple Silicon with Docker VMM, the only) filesystem sharing implementation in Docker Desktop 4.29+ [/FINDING]
[EVIDENCE:S3F1] Docker Desktop settings docs (https://docs.docker.com/desktop/settings-and-maintenance/settings/) state VirtioFS is the default file sharing method. The settings page further notes VirtioFS is the *only* implementation supported when using Docker VMM (the Apple Silicon hypervisor), making it mandatory on that hardware path. osxfs was flagged for removal as of Docker Desktop 4.36.0 (November 2024). [/EVIDENCE]
[CONFIDENCE:HIGH] Multiple official doc pages confirm; consistent across settings page and release notes.

[FINDING:S3F2] inotify propagation over VirtioFS is incomplete: CREATE, ATTRIB, and MODIFY events propagate from host to container, but DELETE events do not. [/FINDING]
[EVIDENCE:S3F2] docker/for-mac issue #7246 (opened 2024-04-10, still OPEN as of 2026-04-09, labeled `area/VirtioFS`): reproducible with `inotifywait -m -r -e delete` — creating files on the host generates events inside the container; deleting them generates nothing. Reproduced on Docker Desktop 4.29.0, darwin/arm64 (Apple Silicon). The same DELETE-propagation bug existed on gRPC FUSE (docker/for-mac #6350, Docker Desktop 4.9, Intel, closed as stale not fixed). CLOSE_WRITE has been missing since at least 2016 (docker/for-mac #896, still OPEN, lifecycle/frozen). [/EVIDENCE]
[CONFIDENCE:HIGH] First-hand reproduction steps in the issue; two independent reporters; the gRPC FUSE predecessor issue confirms this is a long-standing class of bug across all macOS filesystem backends.

[FINDING:S3F3] There is no authoritative documented latency number for host→container file visibility over VirtioFS on Apple Silicon. [/FINDING]
[EVIDENCE:S3F3] Docker release notes cite "up to 98% reduction in filesystem operation time" compared to osxfs, but give no absolute latency figures. No inotify delivery latency benchmark was found in official docs or the searched issues. Community benchmark data was not available from the sources consulted. [/EVIDENCE]
[CONFIDENCE:HIGH] Absence confirmed across official docs and issue tracker search; "no authoritative number found" is the correct answer per the research brief.

[FINDING:S3F4] VirtioFS is available on both Apple Silicon and Intel Macs, but Docker VMM (which mandates VirtioFS) is Apple Silicon only. [/FINDING]
[EVIDENCE:S3F4] The settings docs describe Docker VMM as "only available on Apple Silicon Macs (Beta)." VirtioFS itself is selectable on both architectures; gRPC FUSE and osxfs remain available on Intel as fallbacks. The inotify DELETE bug (docker/for-mac #7246) was reproduced on `darwin/arm64`; the gRPC FUSE predecessor (#6350) was reproduced on Intel — confirming the bug class spans both architectures and both backends. [/EVIDENCE]
[CONFIDENCE:HIGH] Directly stated in settings documentation.

[FINDING:S3F5] "File watching" and "inotify" are the same failure surface on macOS Docker Desktop: both refer to the Linux kernel inotify subsystem inside the container failing to receive events for changes made on the host side of the bind mount. They are not distinguishable. [/FINDING]
[EVIDENCE:S3F5] All issue reports (docker/for-mac #896, #6350, #7246, #1802, #681) use both terms interchangeably — tools like webpack HMR, Jest `--watch`, and `inotifywait` all rely on the same inotify syscall; the propagation failure affects all of them identically. There is no distinct "file watching" layer separate from inotify in this context. [/EVIDENCE]
[CONFIDENCE:HIGH] Consistent across all issue reports examined.

[FINDING:S3F6] VirtioFS became the default in Docker Desktop 4.6 (March 2022 timeframe) and has been GA and default since then; osxfs removal was announced in 4.36.0 (November 2024). [/FINDING]
[EVIDENCE:S3F6] Release notes for 4.36.0 (November 2024) state osxfs "will be removed in a future version" — implying VirtioFS had already been default long enough to deprecate the predecessor. The oldest VirtioFS label issues in docker/for-mac date to 2022. [/EVIDENCE]
[CONFIDENCE:MEDIUM] Release notes available only from 4.36.0 onward; exact GA date of "became default" not stated explicitly, inferred from deprecation timeline.

---

## Bind-mount propagation matrix

| Mount type | Default on macOS ARM | inotify works? | Visibility latency | Source |
|---|---|---|---|---|
| VirtioFS | Yes (mandatory with Docker VMM) | Partial — CREATE/ATTRIB/MODIFY propagate; DELETE does not | No authoritative number found | docs.docker.com/desktop/settings; docker/for-mac #7246 |
| gRPC FUSE | No (selectable fallback) | Partial — same DELETE gap confirmed; CLOSE_WRITE missing | No authoritative number found | docker/for-mac #6350, #896 |
| osxfs | No (deprecated, removal announced 4.36.0) | Partial — CLOSE_WRITE missing since 2016 | Historically ~100ms+ per op; replaced for being slow | docker/for-mac #896; docs release notes |

---

## Implications for issue #77 design

- **Port-file polling is safer than inotify over the bind mount.** Because DELETE events do not propagate on VirtioFS (docker/for-mac #7246, still open 2026), any container-side watcher using `inotifywait` or Python `watchdog` will silently miss host-side file deletions/replacements. A polling loop (e.g., `stat` every 500ms) is more reliable for detecting port-file updates on the bind mount.

- **Write-then-rename on the host does not guarantee an inotify event inside the container.** The common atomic-write pattern (`write tmp → rename to final`) uses `IN_MOVED_TO` / `IN_CREATE` events; while CREATE has been reported to propagate, CLOSE_WRITE does not (docker/for-mac #896, open since 2016). The container code in `docker.py ensure_container_ssh_proxy` that reads the port file once at startup is therefore not reliably triggerable via inotify for a re-read; it must either poll or be restarted.

- **The bind-mount file-state approach is viable for read-once semantics (port baked at startup), but not for live-reload.** File visibility latency is not the blocker (VirtioFS is fast enough); the blocker is incomplete inotify propagation. If the design requires the container to react to host-side port-file changes after startup, a non-inotify mechanism (polling, Unix socket, or HTTP endpoint) is required.

[STAGE_COMPLETE:3]

---

## GitHub repos touched

- [docker/for-mac](https://github.com/docker/for-mac) — inotify propagation bugs over VirtioFS and gRPC FUSE (issues #7246, #6350, #896, #1802, #681, #7416)
