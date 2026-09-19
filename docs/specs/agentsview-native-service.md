# AgentsView native local service

Status: MEASURED LOCAL BASELINE; broader qualification remains open.

## Measured local baseline

Snapshot recorded 2026-09-16 from ROOT's operating-service measurements and the
independent reviewer, plus this author's retained repository QA. These are
completed local checks, not instructions to repeat host setup:

- Native v0.43.0 serves the approved working archive below. Native GUI login,
  known full-content Claude/Codex sessions, reload, and retained authentication
  passed. Anonymous and bad-token protected requests returned HTTP 401.
- Both native user-level skills are current. Actual global mise status,
  skills, and known-session task calls returned direct rc 0.
- Controlled SIGTERM recovery changed service PID 14099 to 87002 and restored
  the protected HTTP 401 endpoint in 6.1 seconds. The same working-root binding,
  both known-session queries (rc 0), and GUI authentication/reload passed.
  This is launchd crash recovery, not reboot or long-duration qualification.
- Independent original/frozen preservation comparison passed for 21 files.
  ROOT owns its private receipt; runtime attestation and exact evidence pointers
  are retained in the final source-review manifest under
  `.agent/state/agentsview-native/source-freeze/`.
- Author lint returned rc 0; verify returned rc 0 (155 passed, 4 skipped).
  Corrected full pytest returned rc 0: 3125 passed, 2 skipped, 11 deselected.
  Author QA and exact receipts are in
  `.agent/state/agentsview-native/qa/final.json`.

The first full-suite invocation ran direct uv with host hk 2.0.0 instead of
mise's project-pinned hk 1.57.0. Its historical result (1231 passed, 1 failed,
1 skipped, 11 deselected) remains retained; it is not a baseline-source failure
or full-candidate evidence. The focused project-context audit control passed
all seven tests and matched the committed document without regeneration.
Run repository pytest from this worktree with project activation:

```sh
av_uv=/Users/rmanaloto/.local/share/mise/installs/\
aqua-astral-sh-uv/0.12.13/uv-aarch64-apple-darwin/uv
MISE_AUTO_INSTALL=0 UV_OFFLINE=1 UV_LOCKED=1 \
  mise exec -- "$av_uv" run --project python --locked --offline \
  pytest tests/ -x -q
```

The corrected full suite settled before the reviewed release-check TOML was
promoted byte-identically to `release-check.toml` in the native module. Its
separate byte/inventory/dry-run controls passed; this is not a post-promotion
full-suite claim. Scheduled native check execution is pending. Automatic
upgrades/rollback, reboot, offline behavior, and an extended feature matrix
remain unimplemented or unqualified; the overall goal is not complete.

## Agreed scope

Native browser GUI and CLI first, native user-level skills for both Claude and
`.agents`, and thin mise tasks with macOS login/crash recovery. Preserve the
custom controller worktree, but do not require its Python code, full-repository
gates, or runtime-spec framework for startup. DuckDB, remote access, and native
desktop app are nonblocking follow-ons. No remote uploads, AI features, or
Cursor setup.

## Native route

The pinned v0.43.0 binary (commit `9be7745`) is supervised directly by native
mise's LaunchAgent writer, running foreground `serve` with loopback auth and
normal sync enabled. Native `daemon status` also manages this writable process.
Do not run `daemon start/restart` alongside launchd: it detaches another process.
Use the isolated `login-apply` task to reconcile/recover; `login-stop` unloads
the exact native job without KeepAlive respawn. It does not delete its plist;
a later login loads that plist again. Persistent removal is a ROOT-owned,
reviewed restore/remove operation, not an invented mise subcommand.

Approved working archive:
`/Users/rmanaloto/Library/Application Support/AgentsView-M1-working-b0ae79c5365e-20260915/archive`.
Original `~/.agentsview` and the frozen preservation archive remain untouched.

## Privacy and authentication

`native-policy.toml` is a secret-free OVERLAY, not a replacement config.
ROOT must preserve the existing private cursor secret, auth token, installation
identity, and unrelated settings when merging. The native pinned
`EnsureAuthToken` generates/persists a random 256-bit token if one is absent.
Only the approved working config may change. Full archive content and tool
results are retained for canonical local Claude/Codex homes; all other
registered configurable providers are excluded from NEW local ingestion.
Historical provider rows stay readable. Disabling providers is not an export
restriction: do not execute remote, push, publish, embeddings, or AI commands.

Before start, ROOT must check effective config for active remote hosts,
session_sources, S3 roots, PG/DuckDB push jobs, embeddings, recall extraction,
insights, proxies or provider overrides and refuse conflicting settings rather
than silently erase them. Keep native secret redaction; never use `--reveal`.
Telemetry is disabled by environment, update checks by config/flags/environment.
No blanket zero-network guarantee is asserted from those switches alone.

ROOT creates private 0600 log files before launchd apply. Native startup logs
may contain auth-bearing information: never publish/capture their raw content.
After native auth generation, ROOT may project ONLY the existing auth token
to `native-server-token` using a reviewed one-shot private-file extraction,
exclusive creation, mode 0600, and no stdout/argv token value. No persistent
helper/controller is necessary. The token file is an auth reference, not a
second token or a regeneration policy. Refuse conflicting preexisting files.

`open` uses the token-free URL `http://127.0.0.1:8080`.
The native browser login prompt is documented, but its frontend/storage
behavior is now verified in pinned native source: password login persists the
token in same-origin localStorage and normal API requests use Bearer headers.
Native SSE watch/event requests include auth in internal query URLs; default
access logs record URL.Path only, not RawQuery or authorization headers.
Live local authentication/reload passed in ROOT's private browser smoke above.
For subsequent changes, ROOT verifies the real browser login privately; no
auth-bearing address URL, raw settings
response, clipboard/localStorage/network dump, screenshot or transcript
exposing credentials. ROOT has an existing browser runtime; no install needed.

## Configuration and global integration

Initial selected launchd apply uses the dedicated `native.toml`, isolated
global/system config inputs, and a ceiling/unique config filename. Verify the
actual native config inventory contains only these intended files before
host mutation. This avoids unrelated global/repository bootstrap resources.
The ceiling must be the bundle's PARENT, not the bundle itself: the first
read-only inventory excluded native.toml and returned no tasks. Correcting
that exposed native trust refusal. Exact-file process-local
MISE_TRUSTED_CONFIG_PATHS (no persistent mise trust write) then loaded precisely
native.toml and the two empty global/system files. Neither an env-isolation
name nor a hand-authored packet alone proves that inventory. Reviewed mise
v2026.9.9 dry-run renders/prints planned actions and then
continues without writing a plist or invoking launchctl (launchd.rs264–315).
The earlier contrary claim was incorrect. Dry-run plans alone still do not
prove a service is running.

ROOT completed the independently reviewed global task-include publication;
actual global status/skills/session calls returned rc 0. The author recorded
published global metadata SHA256
`4a27abf98c7a595b1a9cfe2106425ac45888bc297abe6c1f7d7513c187c7b5a3`.
For future publication, merge the absolute `tasks.toml` path into
`task_config.includes`, preserving unrelated keys and existing includes.
ROOT privately backs up the exact preimage, captures its digest, and provides
finite rollback targets before publication.
Do not apply the old custom bundle or merge the whole native launchd bundle
into global bootstrap configuration.

## Subsequent-change verification protocol

The local baseline above has already completed this protocol. Use it for a
reviewed host change; ROOT owns publication/activation, while this author owns
source documentation and the review manifest.

1. Independently review exact candidate bytes, private-config merge operation,
   token-file extraction, selected native host commands and config isolation.
2. Verify preservation receipts and immutable pinned executable/identity,
   working config preimage, approved paths, safe effective config, private logs,
   and actual isolated mise config inventory.
3. ROOT publishes the reviewed private working-config overlay and applies only
   the native LaunchAgent; collect real direct exit codes and settlement.
4. Verify actual native PID, executable, data cwd and loopback listener.
   Confirm `daemon status`, then authenticated `session get` for known
   Codex `codex:01a09c55-c7c2-75c0-9e94-414372f69f96` and Claude
   `0a2be257-d902-4375-bc27-242caf9a75f6`. Expected baseline message counts
   are at least 3527 and 1 respectively, not an exhaustive corpus claim.
5. Check protected unauthenticated API denial; privately authenticate the
   native browser and view a known full-content C/C session. CLI message
   bodies stay in private evidence; public projection is counts/IDs/outcome
   only. If the actual port is not 8080, STOP and reconcile literal URL/task/
   skill references before installing skills.
6. Native skills list, private backup of exact existing generated target files,
   then install default both without `--force`; inspect both install states.
   Refusal of a modified/foreign skill requires direction, never force.
7. ROOT merges the global task include with backup/rollback; exercise
   status/open/authenticated CLI through the installed task entrypoints.
8. Bounded stop/reconcile recovery smoke through exact native login tasks,
   matching the same working archive and privacy settings. This crash-recovery
   step does not replace the pending reboot qualification.

Use the existing reviewed 3f capture runner for bounded commands, separate
raw streams and explicit actual rc/finalization. Service-log/token/config
bodies are private and must never enter public capture streams. The measured
local service/browser/CLI/skills/crash-recovery baseline is satisfied; wider
qualification remains open. Repository integration still requires independent
review of the final source manifest and ROOT-owned exact-HEAD Git/PR work.
Use local AGENTS and the canonical project-activated pytest command above;
previous custom-tree results or wrong-host-context runs are not substitutes.

Window: checkpoint 2026-09-16T05:10:41Z; hard stop 05:25:41Z; cleanup reserve
920 seconds. Stop new work early enough to finalize evidence and handoff.

## Reused primary evidence

Pinned binary SHA256 `8faa1b4be50dab102349247d3321ad4826ef18da875c8c161d598f3f7d552303`.
Pinned configuration docs SHA256 `9dd55c2ab91001a0d4a7e12ae351b5bda5427a501a23cac2238f9cda51ba75eb`;
commands docs SHA256 `95d1514cc64c2999719db3c9b6ac84a7bae76d3a25e46ec08dbe814a664c68e0`.
Native help is retained in existing audit captures; no repeated network/docs/
backup/CLI-help collection was necessary. Exact transient evidence locations
and hashes are frozen in `.agent/state/agentsview-native/`, not promoted as
cross-clone runtime proof.
