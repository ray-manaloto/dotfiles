# Explore agent report — writer_lease.py seam map (2026-08-27, session ad30e818, #791)

Brief: map `writer_lease.py` hold/check/status, holder lifetime + drain, transition derivation, `handoff_sha256`, owner-prefix parsing, in-flight schema/readers, loopback challenge, and the test names. Persisted verbatim at receipt per `.claude/rules/agent-report-persistence.md`.

---

Bash and Write are both unavailable in this session, so here is the report inline.

# writer-lease map

All anchors in `python/src/dotfiles_setup/writer_lease.py` unless prefixed.

## 1. Public entry points

| fn | lines | signature |
|---|---|---|
| `hold` | 1667–1708 | `hold(cwd: Path, *, request: LeaseRequest) -> int` |
| `check` | 1711–1736 | `check(cwd: Path, *, task_id: str, handoff_sha256: str) -> int` |
| `status` | 1739–1783 | `status(cwd: Path) -> int` |

Dispatch: `writer_lease_main` 2062–2088 (rc 2 + `writer-lease: {exc}` on `LeaseError`, 2084–2086).

`status()` payload (canonical JSON, one line, 1782):
- absent branches (1744–1749, 1755–1760): `cleanup_debt`, `common_dir`, `state`, `worktree`
- present branch (1770–1781): `cleanup_debt`, `common_dir`, `handoff_sha256`, `inflight` (sorted **tool_use_id keys only**, 1774), `owner`, `receipt_sha256`, `state` (`live`/`stale`, 1762), `task_id`, `transition`, `worktree`

`pid`, `holder_port`, `holder_token` are in the receipt (`_RECEIPT_KEYS` 72–89; written in `_new_receipt` 1426–1441) but are **NOT** in `status()` output. They *are* printed by `hold()` itself — the readiness line at 1690–1699 emits the whole receipt dict. `check()` prints only `receipt_sha256`, `status`, `task_id`, `worktree` (1725–1735).

## 2. Holder process lifetime + drain

- Loop: there is none — `hold` blocks on `release_requested.wait()` (1703) after publishing.
- Signals: `_release_signals` 1615–1626 traps **SIGTERM and SIGINT only**; both handlers do nothing but `release_requested.set()` (1617–1618), and prior handlers are restored in `finally` (1625–1626). No SIGHUP/SIGQUIT.
- Drain: `_release_when_drained` 1629–1664. `while True` (1635) → exclusive `_state_lock` with `retry_seconds=_STATE_LOCK_RETRY_SECONDS` (=3.0, line 57) → re-read snapshot; if receipt digest changed, raise "writer lease state changed beneath the live holder" (1643–1645).
- **The release-blocking condition is `if not current.inflight:` (1646)** — release/audit-append/`_write_fd(lease_fd, b"")` happen only inside that branch (1647–1663). Non-empty `inflight` falls through to `time.sleep(0.05)` (1664) and loops. **No timeout, no max iterations — it waits forever.** Poll interval 50 ms; each poll takes the exclusive state lock.
- Cleanup regardless: `server.close()` + `os.close(lease_fd)` in `hold`'s `finally` 1706–1708.

## 3. `transition` derivation

`_derive_transition` 1390–1416:
- `prior is None` → `("initial", "")`; a supplied prior digest is refused 1395–1397.
- prior exists, no expected digest → 1399–1401 "prior receipt exists; its exact digest is required".
- digest mismatch → 1406–1408 "expected prior receipt digest does not match stored receipt".
- **In-flight refusal, 1409–1414** (applies to *both* handoff and recovery, evaluated BEFORE the label is chosen):
  `"prior writer still has in-flight mutation tools; drain them before transfer"`
- Label: `transition = "handoff" if prior.active_receipt_sha256 is None else "recovery"` (1415) — i.e. recovery iff the audit still shows an unreleased active owner (`_validate_history` 807–829 sets `history.active`).
- `--expected-transition` is only an assertion: mismatch → `f"audit facts require {transition}, not {request.expected_transition}"` (`_publish_new_holder` 1574–1581).
- Second, audit-level guard on the same invariant: `_validate_acquired` 849–851 `"writer lease audit transfers with in-flight tools"`.

## 4. `handoff_sha256`

- It is a digest **of nothing this code computes**. The only constraint is `_validate_sha256` (288–296): 64 lowercase hex chars. Validated in `hold` 1672, `check` 1713, receipt validation 724, bootstrap pre-check 1827.
- Semantics: an opaque coordination token the caller invents and must reproduce. Stored in the receipt (1430), surfaced in `status` (1773), and enforced for equality in `_owned_snapshot` 1540–1542 (`"live lease handoff digest does not match"`). `_begin_tool` deliberately passes `handoff_sha256=None` (1881) so hooks skip that check.
- CLI: `--handoff-sha256` required on both `hold` and `check` (main.py:1437, 1452). Nothing in the tree derives it — tests use literals `"a"*64` / `"b"*64` (tests/test_writer_lease.py:26–27).
- `--expected-prior-receipt-sha256` (main.py:1446, optional): validated at 1402–1405 then compared to `prior.receipt_sha256` (1406). That value is `_sha256(receipt_raw)` over the canonical receipt bytes of the currently published generation (`_read_snapshot` 956, with canonicality pinned at 944–946). Bootstrap-allowlist path pre-validates it at 1828–1830.

## 5. `codex:` / `claude:` owner parsing

`_bootstrap_command` 1836–1858 — line **1857** `values["--owner"] == f"codex:{session_id}"` — is the **only** place any owner prefix is parsed or validated, anywhere in the tree.

Every other `owner` site treats it as an opaque non-empty string:
- `LeaseRequest.owner` 126; `_RECEIPT_KEYS` 83 (string, non-empty via 701–704)
- `hold` 1669–1671 — only `not request.owner.strip()`
- `_new_receipt` 1434; `status` output 1775
- CLI `--owner` main.py:1436 (no `choices`, no validator)
- `.codex/hooks.json` (whole file) and `scripts/writer-lease-hook-runner.py` do not touch owner.
- Tests deliberately use unprefixed owners (`"/root/task-a"`, `"claude-session-a"` — tests/test_writer_lease.py:366, 621), confirming no prefix enforcement outside the bootstrap allowlist. No `claude:` prefix is recognized **anywhere**, so a Claude session cannot use the bootstrap-allowlist escape at all.

## 6. In-flight entries and their readers

Schema `_INFLIGHT_KEYS` = `{receipt_sha256, session_id, started_at, tool_name}` (104), keyed by `tool_use_id`. Validation `_validate_inflight` 742–763 (exact key-set 751, all-non-empty-strings 754–759, sha256 760, tz-aware timestamp 761).

Writers: `_begin_tool` 1903–1908 (`session_id` = hook `session_id`, `started_at` = the audit event's `at`, 1906); removal `_finish_tool` 1946–1947. Audit twin built in `_validate_tool_started` 872–877 and byte-compared to the file at `_validate_history` 826–828 (`"writer lease audit and in-flight state disagree"`).

Every reader of `inflight`:
| site | line | what it does |
|---|---|---|
| `_read_snapshot` | 933, 947–950 | parse + canonicality |
| `_validate_history` | 826 | must equal audit-derived open tools |
| `_validate_acquired` | 849 | refuse acquire while tools open |
| `_validate_released` | 857 | refuse release while tools open |
| `_derive_transition` | 1409 | **refuses handoff/recovery** |
| `_release_when_drained` | 1646 | blocks release forever |
| `_begin_tool` | 1883 | duplicate `tool_use_id` check |
| `_finish_tool` | 1939–1947 | identity match then delete |
| `status` | 1774 | prints sorted keys |

**Stale-entry detection: none exists.** An entry carries no pid, no port, no token — only the *registering* `session_id` (a Codex/Claude session string, not an OS identity) and `started_at`. `started_at` is validated but never read for aging. The one liveness primitive available for reuse is `_holder_is_live` 1492–1513 (flock probe 1500–1506 → `_read_lock_token` 1453–1474 → compare to `_lock_token(receipt)` 1511 → `_challenge_holder` 1513) — but it proves the *lease holder process* is alive, and the holder and the registering session need not be the same process, so it cannot by itself decide "the session that opened this tool_use_id is dead". Receipt `pid` (1435) is likewise per-lease, not per-inflight-entry.

## 7. Loopback challenge / `holder_port`

- Server: `_HolderServer` 214–268 — binds `127.0.0.1:0` with `SO_REUSEADDR` explicitly **off** (221), `listen(4)` (223), 0.2 s accept timeout (224), ephemeral port captured at 225; daemon thread `writer-lease-holder-challenge` 226–230. Request handler `_serve` 242–268: reads a `{"nonce": str}` JSON, replies `{holder_token, nonce, schema}` canonical bytes (258–266), 0.5 s socket timeout (`_CHALLENGE_TIMEOUT_SECONDS`, line 56).
- Lifecycle: created/started in `hold` 1680–1682 (`holder_token = os.urandom(32).hex()`), closed 1707. Endpoint published into the receipt via `HolderEndpoint` 1688 → `_new_receipt` 1430–1432, and into the lock file via `_lock_token` 1444–1450 / `_write_fd(lease.fd, ...)` 1601.
- Verifier: `_challenge_holder` 1477–1489 — fresh `uuid4().hex` nonce, exact-dict equality on the reply (1489); any `OSError`/JSON error → `False` (1487–1488).
- Sole caller: `_holder_is_live` 1513, after the flock-still-held probe and the lock-token/receipt equality check (1511).
- **`status()` does exercise it** — line 1762 `state = "live" if _holder_is_live(state_dir, snapshot) else "stale"`. So `status` opens a TCP connection to the holder. `check()` reaches it too via `_owned_snapshot` 1527.

## 8. `tests/test_writer_lease.py` (2171 lines)

Bootstrap allowlist:
- `test_codex_hook_allows_only_plain_lease_bootstrap_without_an_owner` :680
- `test_bootstrap_rejects_environment_path_and_unpinned_argv` :896

Hold / transition:
- `test_real_linked_worktree_contention_and_pre_mutation_identity` :356
- `test_clean_digest_bound_handoff` :444
- `test_abrupt_death_requires_exact_digest_recovery` :482
- `test_malformed_receipt_fails_closed_without_rewriting_it` :551
- `test_independent_git_common_directories_do_not_contend` :583
- `test_crash_transition_is_derived_as_recovery_and_claude_bash_is_owned` :980
- `test_lease_flows_preserve_dirty_ignored_untracked_and_omc_bytes` :1033
- `test_invalid_audit_is_rejected_and_audit_failure_never_publishes_receipt` :831

In-flight / drain:
- `test_inflight_mutation_drains_before_handoff_and_posttooluse_releases_it` :923
- `test_recovery_refuses_inflight_until_write_stdin_completion_drains_it` :1078 (asserts the "in-flight" stderr from `_derive_transition` at :1123)
- `test_pinned_system_runner_uses_real_project_runtime_and_drains_posttooluse` :1206
- `test_failed_claude_bash_drains_for_clean_release_and_crash_recovery` :1937
- `test_completion_and_release_retry_overlapping_state_lock_many_times` :2108
- `test_many_tool_pairs_keep_one_linear_generation_with_full_audit` :1708

Status output:
- `test_status_is_non_mutating_and_unsafe_state_paths_fail_closed` :778
- `test_receipt_is_bound_to_the_actual_live_holder_not_any_flock` :729
- `test_malformed_reclaim_is_typed_debt_not_postcommit_denial` :2062 (`cleanup_debt` shape at :2102)

Other (hook/runtime/audit-storage, for completeness): :65, :78, :86, :114, :131, :612, :639, :805, :1152, :1299, :1336, :1383, :1464, :1531, :1638, :1801, :1857, :2017.

## Wiring

- mise.toml:662–664 `writer-lease-hold` → `uv run --project python dotfiles-setup writer-lease hold`; :666–668 `writer-lease-check`; :670–672 `writer-lease-status`. (These exact argv shapes are what `_bootstrap_command` 1848–1853 reconstructs as `[mise, "-C", worktree, "run", ...]`.)
- argparse: `_add_writer_lease_subcommand` main.py:1424–1453, called from `_add_report_parsers` main.py:1358; dispatch entry main.py:2171 `"writer-lease": lambda: sys.exit(writer_lease_main(args, Path.cwd()))`. `--expected-transition` uses `choices=TRANSITIONS` (main.py:1440).
- Codex hook: `codex_writer_lease_hook.py:17–37` → `codex_pretooluse_decision` (writer_lease.py:2057) → `hook_decision` 1999–2032. PostToolUse/PostToolUseFailure denials become `{"continue": false, "stopReason": ...}` (hook file 26–27), PreToolUse becomes `permissionDecision: deny` (28–35). `.codex/hooks.json` matcher is `^(Bash|Edit|Write)$` for both events; note `MUTATION_TOOLS` (writer_lease.py:50) also includes `apply_patch` and `NotebookEdit`, which that matcher never delivers.

One observation worth flagging: `_release_when_drained`'s unbounded wait (1635/1664) combined with the absence of any liveness data on in-flight entries means a hook that records `tool_started` and never gets its Post counterpart wedges the holder's SIGTERM path permanently — the holder ignores further SIGTERM/SIGINT because the handler only re-sets an already-set event (1617).

---

## GitHub repos touched

_None._ (local source read only)
