# AgentsView native follow-ons

Status: follow-on inventory beyond the measured local baseline. See
`agentsview-native-service.md` for completed ROOT/reviewer runtime checks and
author QA. The operating native server/tasks are unchanged by this doc update.
The reviewed release-CHECK TOML is versioned; scheduled execution is pending.

## Local integration first

ROOT completed reviewed global task publication and measured its local task
entrypoints. Publication adds only the native tasks.toml path to
task_config.includes, preserving original order/entries and deduplicating.
For future changes use existing yq4.53.6 native TOML eval-all; raw configuration
and yq diagnostics stay in private0600 files. The historical global backup
38076 bytes/SHA573edbfa8e53208243ef2e17490522fe7e533696bf3f941e49dd4038a3219641
belongs to the prepublication source, not an assumed current preimage.
ROOT verifies an exact current-source backup before any later publication.

Native yq retained leading/inline/section/array comments in four synthetic
controls. Spacing was slightly normalized; byte-for-byte formatting is NOT
promised. The real global comment/diff check belongs to ROOT's private review,
not evidence inferred from synthetic controls. No custom comment restorer.

## Native command inventory

The pinned CLI exposes commands; existence is not authorization to execute
all of them. Reuse native --help and bundled skills instead of custom wrappers.

- Local service/history: serve, daemon, sync, session, projects, health, stats,
  doctor sync, version, usage daily/statusline, activity report and token-use.
  Some commands auto-start/write through the native daemon; status may clean
  stale runtime metadata. Use explicit authenticated server/token-file when
  reading the approved archive; do not infer default local SQLite equivalence.
- Native skills: install/list both user-level harnesses without --project or
  --force. ROOT rechecks known-absent target files immediately before install.
- Archive maintenance: db, prune, import, export and parse-diff. Destructive/
  bulk/export operations need exact scope and backup; not performed here.
- Optional access: native mcp with explicit server/token-file; no new MCP client
  configuration/listener in this local setup packet.
- Deferred local analytics: duckdb push/status for a LOCAL mirror; remotes and
  native desktop app remain nonblocking follow-ons, not shared archive upload.
  PG push/service, Quack/network serve or sync remotes require separate scope.
- Excluded now: capture producer work, hosted raw-sync/archive uploads, Cursor
  usage API/setup, embeddings/recall/model-backed work and remote publishing.
  Other exposed families (classifier, OpenAPI, secrets) are available but not
  broadly qualified/enabled by this inventory; never use secret --reveal.

## Reviewed check-only candidate; upgrades remain unimplemented

Reviewed native update --check --force reads releases and may write the
approved working update cache; --check does NOT install/replace the binary.
Do not run native binary self-update (--yes or non-check installation mode)
against the pinned mise tool. No update command or new job was executed here.

Local tasks/skills and service GUI/CLI/crash-recovery passed. Independent review
approved the separate check-only candidate, promoted byte-identically to
`.config/mise/agentsview-native/release-check.toml`. Its native mise job requests
StartInterval900 and only the pinned binary's update --check --force under
the approved working data/telemetry environment. Byte/inventory/dry-run controls
passed; actual scheduled execution/cadence is still pending, not proven by TOML.
Explicit release-check network access and cache writes must be disclosed;
serve's disabled update endpoint/telemetry does not imply that the explicit
check is network-free. Private logs must never contain configuration/token data.

A new stable release triggers a ROOT-owned, exact reviewed mise pin/binary
promotion and native regression smoke, preserving privacy and archive identity.
Checks do not automatically install updates. No new custom upgrade controller,
poller, versioned-health architecture or provider work is needed.

Primary inventory: existing pinned command/configuration docs at commit9be7745,
retained exact CLI help, and ROOT's reviewed update path. Fine-grained command
mutations not already qualified remain unknown, not safe by default. Exact
global operation and comment control captures live under
.agent/state/agentsview-native/global-include/.
