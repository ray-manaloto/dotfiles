# Staleness audit — GitHub rate-limit prose (2026-09-10)

**Status:** In progress — codex invoked, awaiting output.

Ground truth established 2026-09-10:
- `mise run lock-image` failed all 5 passes on empty candidate set for `fnox@latest: no versions found for fnox matching date filter` — a packaging resolution failure, NOT quota exhaustion
- Root cause: mise 2026.9.2-9.4 promoted `packslip` to tier 1; packslip lists only releases with packslip manifests (fnox: 1 version vs control node: 865); prior `minimum_release_age = "7d"` filter removed all candidates
- The loop printed "rate limits are the expected cause" on all five passes and misdirected the session twice
- `jdx/wait-for-gh-rate-limit` is a 59-line precursor gate (GETs `/rate_limit`, sleeps until reset when `remaining <= 1`, always exits 0)

Corpora to audit:
- `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/docs/research/kb/reports/agents/2026-09-03-rate-limit-retry-research.md`
- `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/docs/research/runs/research-20260709-r2-updater/agents/mise-native.md` (around line 257)
- `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/image_lock.py` (docstring ~line 290)
- `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.github/actions/lock-refresh/action.yml` (loop ~line 67)
- `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/skills/lock-image/SKILL.md`
- `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/rules/persistence-gate-retry.md` (signature table)
- GitHub issues #964 and #908

Reasoning lane: codex `gpt-5.6-sol`, `model_reasoning_effort=xhigh`

---


## Summary — Two Explicit Questions Answered

### Question 1: Does any surviving document still tell a reader that a `lock-image` or `lock-refresh` failure is always or usually quota?

**YES.** Four documents carry claims asserting rate limits as the expected or expected-mid-run cause:

1. **`python/src/dotfiles_setup/image_lock.py:313`** — logs "rate limits are the expected cause" on ALL failures
2. **`docs/research/kb/reports/agents/2026-09-03-rate-limit-retry-research.md:49-50`** — states "exhausted GitHub quota is the expected mid-run failure"
3. **`docs/research/runs/research-20260709-r2-updater/agents/mise-native.md:251-263`** — states "Rate limits are the real cadence constraint"
4. **`.claude/skills/lock-image/SKILL.md:42-44`** — states "quota runs out partway, which is what the convergence loop is for"

All four were written BEFORE the fnox empty-candidate-set failure demonstrated that failures can be packaging resolution, not quota.

### Question 2: Does `.claude/rules/persistence-gate-retry.md`'s signature table need a row for the deterministic empty-candidate-set failure?

**YES.** The table at lines 45–52 has no entry for "backend tier promoted → minimum_release_age filters empty set" or similar. The fnox failure:

```
fnox@latest: no versions found for fnox matching date filter
```

has no signature row and would be misfiled as environmental if it recurs.

---

## Findings — codex verdict, recovered from the lane's stream

> **Provenance.** The lane went idle before transferring this. Its codex run
> (`gpt-5.6-sol`, xhigh, read-only) had completed and written 459,594 bytes to
> `/tmp/codex-staleness-output.txt`; the tracked report was still a stub reading
> "Codex Analysis Pending". Recovered from that stream by the coordinator rather
> than re-running the lane. The stream contained the final message twice; the
> last complete copy (lines 7255-7575, all 12 findings) is reproduced verbatim
> below.

**Yes: surviving prose still directs readers toward quota without diagnosing the failure.** The clearest examples are:

| Current anchor | Exact surviving wording |
|---|---|
| [image_lock.py:292](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/image_lock.py:292) | “exhausted GitHub quota is the expected mid-run failure.” |
| [image_lock.py:312](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/image_lock.py:312) | “retrying (rate limits are the expected cause)” |
| [lock-image/SKILL.md:69](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/skills/lock-image/SKILL.md:69) | “A short lock is the expected mid-run state, not a failure.” |
| [action.yml:19](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.github/actions/lock-refresh/action.yml:19) | “GitHub-backed resolutions are not rate-limited (the convergence loop exists because anonymous quota exhausts mid-run).” |
| [mise-native.md:255](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/docs/research/runs/research-20260709-r2-updater/agents/mise-native.md:255) | “Rate limits are the real cadence constraint on the mise side” |

**Yes: add an explicit empty-candidate signature, separate from quota and throttling.** However, the current persistence rule does **not** say that unmatched failures default to environmental. That part of the proposed diagnosis is refuted.

I audited the six local files at checkout `edb01c2466010c5c7e4cfc9959f240c6e7be2dbc`, read both issues live, and checked mise source at release commit `794948606e02cde091653a165291b06cae43c352` (`2026.9.4`). No files changed.

Your historical-truth requirement matters: several claims were already incorrect or unmeasured when introduced. I have **not** promoted those to `CONFIRMED-STALE`. Their `NEEDS-VERIFICATION` labels identify missing historical or causal evidence; the report separately states the current errors that are already proven.

### Finding 1: [NEEDS-VERIFICATION] — “Expected quota” is an unsupported diagnosis for individual failures

**Anchor:** `python/src/dotfiles_setup/image_lock.py:291–295,312–313` | “exhausted GitHub quota is the expected mid-run failure”; “retrying (rate limits are the expected cause)”.

Also `:79–80`: “anonymous quota exhausts mid-run; each pass fills what the previous could not. CI uses five and converges.”

**Falsifier:** The warning would be diagnostic only if the failure branch established quota exhaustion before printing it.

**Probe + control arm:**

- `nl -ba python/src/dotfiles_setup/image_lock.py | sed -n '281,320p'` → every nonzero `returncode` reaches the warning; there is no inspection of HTTP headers, stderr, or failure class.
- The same source at `:308–310` → `returncode == 0` returns immediately. This control confirms the branch discriminator is success versus failure, not quota versus resolution.
- `git blame -L 285,320 -- python/src/dotfiles_setup/image_lock.py` → wording and behavior originated in `394fddb`, 2026-08-08.
- `git show --stat 394fddb` → the introducing commit explicitly records: “Not exercised end-to-end: the happy path has never run.” It does not establish that quota was historically the usual failure.

**Second route:** mise’s `src/toolset/tool_version.rs:502–538` passes the date cutoff into latest-version resolution and returns `no_versions_found` when resolution fails. Its `src/backend/packslip.rs:1088–1092` filters release candidates by manifest availability. These independently support the packaging mechanism in your supplied incident.

The incident disproves an **exclusive** quota interpretation. One incident does not establish or disprove the statistical claim “usually quota.”

The warning also says “retrying” on the final failed attempt, when no attempt remains.

**Replacement text:**

Docstring:

> Run at most `passes` lock attempts, returning on the first success. A nonzero exit does not identify the cause: inspect mise’s diagnostic for transport failures, quota exhaustion, throttling, or version-resolution failures. Exhausting the attempts raises `ImageLockError`.

Warning:

> `mise lock pass %d/%d exited %d; inspect mise's diagnostic for the cause`

### Finding 2: [NEEDS-VERIFICATION] — The lock-image skill overstates both recovery and failure diagnosis

**Anchor:** `.claude/skills/lock-image/SKILL.md:69–73` |

> “A short lock is the expected mid-run state, not a failure.”

> “If every pass fails, a tool is genuinely unresolvable”

**Falsifier:** Partial output would need to identify recoverable quota exhaustion, and five failures would need to exclude persistent transport or quota failures.

**Probe + control arm:**

- Reading `image_lock.py:306–320` → the attempt count establishes neither condition.
- Control: `image_lock.py:308–310` exits on the **first** success; “Only the last pass has to succeed” inaccurately suggests a required fifth pass.
- `git blame -L 69,73 -- .claude/skills/lock-image/SKILL.md` → both assertions date to the same 2026-08-08 introduction, whose end-to-end happy path was explicitly unexercised.
- mise’s `CHANGELOG.md:3266–3279` → the 2026.6.13 change really does say “fail when active tools cannot resolve.” That factual clause survives.

The skill **does already mention unresolvable tools**. The defect is its categorical reasoning from partial output and attempt count.

**Replacement text:**

> A partial lock does not establish success or identify the failure’s cause. The local task makes up to five attempts and stops on the first success. Inspect mise’s diagnostic after a failure. Repeated empty-candidate errors require investigation of backend selection, available versions, and release-age filtering; immediate retries with unchanged inputs will not repair them. Persistent network or quota failures can also exhaust every attempt.

At `:10–11`, replace “converges under GitHub rate limits” with:

> runs bounded lock attempts and collects only after success and coverage validation

### Finding 3: [REFUTED] — The persistence rule does not classify unknown failures as environmental

**Anchor:** `.claude/rules/persistence-gate-retry.md:14` | “Confirm the failure mode is environmental.”

**Falsifier:** The rule would need an environmental fallback for unmatched signatures.

**Probe + control arm:**

- `rg -n 'no versions found|date filter|empty.candidate|packslip' .claude/rules/persistence-gate-retry.md` → no matches, rc=1.
- `rg -n 'getaddrinfo ENOTFOUND|FAIL: installed-tool set drifted' .claude/rules/persistence-gate-retry.md` → existing environmental and defect controls match at `:45` and `:48`.
- Fresh negative control, `rg -n -F 'audit_absence_7ec812b0_20260910'` across all six local corpora → no matches, rc=1.
- Full reading of the heuristic and “Applies to” section → no unmatched-error fallback; the stated scope is persistence, verify-local, land, sync, and container-up paths.

**Result:** The missing signature is confirmed. Automatic environmental classification is not.

**Replacement text — recommended addition:**

| Signature | Class | Action |
|---|---|---|
| `no versions found for <tool> matching date filter`, with successful version enumeration and no eligible candidates | version-resolution/configuration failure | Inspect the selected backend, available releases, and effective age cutoff. Diagnose before retrying; do not treat this as DNS, quota exhaustion, or throttling. |

Add:

> For lock-image and lock-refresh failures, use the lock-image skill. An unmatched signature is unclassified until its cause is established.

The qualification matters: mise 2026.9.4’s `tool_version.rs:63–73` explicitly distinguishes failed enumeration from an empty candidate result. Do not assume every historical version made that distinction.

### Finding 4: [NEEDS-VERIFICATION] — The CI convergence explanation was already wrong when introduced

**Anchor:** `.github/actions/lock-refresh/action.yml:51–54` |

> “Iterate for GitHub-rate-limit convergence … each pass fills what the previous could not resolve”

**Falsifier:** Under this step’s shell semantics, a failed invocation would have to reach the next iteration.

**Probe + control arm:**

```bash
/bin/bash --noprofile --norc -c \
  'set -euo pipefail; for _ in 1 2 3 4 5; do printf "pass=%s\n" "$_"; false; done'
```

→ `pass=1`, rc=1.

```bash
/bin/bash --noprofile --norc -c \
  'set -euo pipefail; for _ in 1 2 3 4 5; do printf "pass=%s\n" "$_"; true; done'
```

→ passes 1–5, rc=0.

These are actual shell replays, isolating exit handling; they do not simulate a GitHub service response.

**Historical arm:** `git show 352063a5:.github/actions/lock-refresh/action.yml` → the July 7 introduction already contains both `set -euo pipefail` and this loop. No formerly working retry behavior was established.

**Second route:** [Issue #964](https://github.com/ray-manaloto/dotfiles/issues/964) independently records the same failing and passing arms and proposes replacing the loop with a retry action containing the quota gate.

**Replacement text:**

> Known defect tracked by #964: under `set -e`, this loop aborts on its first failed command and repeats successful commands five times. It does not provide failure recovery. The proposed replacement rechecks quota inside each command retry.

A comment would expose the defect; it would not fix it.

**Attribution correction:** the current action does **not** print “rate limits are the expected cause”:

- Literal search in `action.yml` → no match.
- Identical search in `image_lock.py` → match at `:312`.

The five warning messages belong to the Python path in the audited implementation.

### Finding 5: [NEEDS-VERIFICATION] — Anonymous quota and cadence claims lack causal measurement

**Anchor:** `docs/research/runs/research-20260709-r2-updater/agents/mise-native.md:255–260` |

> “Rate limits are the real cadence constraint … resolutions exhaust anonymous quota”

The same explanation appears at `:26–28` and `:188`.

**Falsifier:** Measurements would need to show anonymous requests exhausting quota and limiting updater cadence.

**Probe + control arm:**

- `git show a667709:.omc/research/research-20260709-r2-updater/agents/mise-native.md` → the claim was present in the original July report.
- `git show 352063a5:.github/actions/lock-refresh/action.yml` → its cited implementation already exported both `GITHUB_TOKEN` and `MISE_GITHUB_TOKEN`.
- Control: mise 2026.9.4’s `src/github.rs:681,750` explicitly recognizes these token variables. Exporting them is meaningful, although configuration alone does not prove that every request used a valid credential.
- The shell arms in Finding 4 refute the claimed CI recovery mechanism.

The action’s stronger assertion at `:18–20`, that exporting tokens makes resolutions “not rate-limited,” is also incorrect: authenticated requests remain subject to primary and secondary limits. [GitHub rate-limit documentation](https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api)

The July document mentions `wait-for-gh-rate-limit` without explaining its mechanics. It **does not explicitly call it a retry wrapper**; that allegation should not be reported as fact.

**Replacement text:**

> Updater cadence can be constrained by authenticated API limits, transient failures, and version-resolution failures. Keep the token variables exported, but use request diagnostics to identify the actual failure. `wait-for-gh-rate-limit` checks a primary quota resource before work and may wait for its reset; it does not retry commands. The CI loop’s failure handling is broken under `set -e` and is tracked by #964.

### Finding 6: [REFUTED] — The September report’s verdict is clearly marked superseded

**Anchor:** `docs/research/kb/reports/agents/2026-09-03-rate-limit-retry-research.md:1,21` |

> “CORRECTION — this report’s VERDICT is wrong”

> “Superseded by #964”

**Falsifier:** The report would need to present its conclusion as current without an explicit correction.

**Probe + control arm:**

- `nl -ba …/2026-09-03-rate-limit-retry-research.md` → the correction precedes the report and names the disputed conclusion and both failed supports.
- `git show --format=fuller --no-patch cd01504` → the introducing commit deliberately preserved the report as historical evidence and added the correction.
- Control: the shell replay in Finding 4 confirms the banner’s central `set -e` correction.

**Result:** The verdict at `:256–260` is explicitly superseded. Preserve the historical report; expand its correction where necessary rather than silently rewriting what the research lane originally returned.

### Finding 7: [NEEDS-VERIFICATION] — The banner’s endorsement of factual sections is too broad

**Anchor:** September report `:17–19` | “The report’s FACTUAL sections … are sound.”

**Falsifier:** Every factual assertion covered by that endorsement would need to agree with the implementation.

**Probe + control arm:**

| Surviving assertion | Independent probe and result |
|---|---|
| `:46`: “Ignores each pass’s exit code — the loop always completes all iterations” | Failing shell arm → one iteration, rc=1; successful control → five. |
| `:48`: “no validation that the final pass succeeded” | `set -e` aborts on **any** unsuccessful pass; Python explicitly checks each return code. |
| `:56`: “Bash action: no checking; relies on downstream … coverage” | The shell exits before reaching collection on a failed pass. |
| `:165`: “handles quota exhaustion … for every API call” | mise’s status classifier retries 429 but excludes ordinary 403; no reset-epoch wait occurs. |
| `:205`: “Fail-fast if quota is already exhausted” | Gate source `main.rs:37–39` sleeps in that branch; the available-quota control proceeds. |
| `:138`: “~200ms (±50%)” | `equal_jitter` computes `0.5 + random * 0.5`: the range is `[100ms,200ms)`, not `[100ms,300ms)`. |

**Historical arm:** `git show cd01504:docs/research/kb/reports/agents/2026-09-03-rate-limit-retry-research.md` establishes that the contradictory statements and correction entered together. Earlier truth has not been established.

The unqualified convergence claims at `:151–170`, `:180`, `:193`, `:207`, and `:254–260` inherit the same problem. Claims about rare exhaustion, saved hours, and how often passes 4–5 are needed have no supporting measurement in this report.

**Replacement text — correction overlay:**

> Preserve the body below as historical research. Its CI exit-handling statements, guaranteed-convergence reasoning, universal exhaustion coverage, “fail-fast” description, and symmetric-jitter example are incorrect. The verified backoff schedule and precursor-gate classification remain useful with the qualifications recorded here. Workload frequency and latency claims remain unmeasured.

### Finding 8: [REFUTED] — The retry schedule and default survive; exhaustion needs precise wording

**Anchor:** September report `:115–130` | schedule `[200ms, 1s, 4s, 15s, …]`, equal jitter, and transient-status classification.

**Falsifier:** Current source would need a different schedule, default, or status predicate.

**Probe + control arm:**

- Read mise `src/http.rs:1979–1999` → the documented schedule, repeated 15-second ceiling, and `[d/2,d)` jitter are present.
- Read `settings.toml:1416–1418` → default retries are **3**.
- Read `src/http.rs:2045–2075` → DNS is excluded; timeout/connect/body/request-without-status failures and 408/429/5xx are included.
- Control: 403 does not satisfy the status predicate; 429 does.

**Important qualification:** `display_github_rate_limit` is a **logging function**. Its `return` at `:1962` does not itself terminate the surrounding request retry loop. Consequently:

- mise does not wait until the quota reset epoch.
- A 429 exhaustion response can still receive ordinary bounded retries.
- A normal 403 exhaustion response is not retried by this status predicate.

GitHub documents that primary exhaustion can return either 403 or 429. [GitHub rate-limit documentation](https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api)

**Replacement text:**

> mise uses bounded, jittered retries for classified transient failures, including HTTP 429. It does not wait until GitHub’s quota-reset timestamp. Do not interpret a 429 alone as distinguishing throttling from primary exhaustion; inspect the remaining-quota headers and diagnostic.

The old body’s “default … likely 3–5” at `:201` should also be marked resolved: the verified default is 3.

### Finding 9: [REFUTED] — The tool really is a precursor gate, not a retry wrapper

**Anchor:** September report `:92–95` | “This is a precursor gate, NOT a retry wrapper.”

**Falsifier:** The implementation would need to launch or retry a workload.

**Probe + control arm:**

- Browser source read of `jdx/wait-for-gh-rate-limit/src/main.rs` → complete 59-line file; last file-changing commit shown as `c68d446`, July 6.
- `main.rs:10–24` → one `/rate_limit` request, token selection from `GITHUB_TOKEN` or `GITHUB_API_TOKEN`, and resource selection defaulting to `core`.
- Positive branch at `:37–39` → `remaining <= 1` sleeps until reset plus one second.
- Control at `:40–45` → available quota proceeds, with status output unless quiet.
- Full-file inspection → no child command execution and no workload retry loop. [Gate source](https://github.com/jdx/wait-for-gh-rate-limit/blob/c68d44602cd9ecead5daaa39075e432e3f3827b4/src/main.rs)

**Result:** This description survives. A primary-quota check does not establish that secondary throttling is absent, and it does not reserve quota for the following workload.

### Finding 10: [NEEDS-VERIFICATION] — “Always exits 0” was already an overstatement

**Anchor:** September report `:82` | “Always `0` (success) — the tool is not a gate”.

**Falsifier:** Every execution path would have to return success.

**Probe + control arm:**

- Gate source `main.rs:19–24` → request, HTTP-status, JSON, and missing-resource errors propagate with `?`.
- Control: both ordinary quota branches end at `Ok(())`, `:45`.
- The live file’s last change predates the September report, so this is an original factual error rather than an established later regression.
- [Issue #964](https://github.com/ray-manaloto/dotfiles/issues/964) already qualifies success with “unless the HTTP call itself fails,” although JSON and resource errors deserve inclusion too.

**Replacement text:**

> Returns success after a successful quota check and any required wait. Request, HTTP-status, response-decoding, or unknown-resource errors can return failure. It is a precursor gate; it does not execute or retry the workload.

### Finding 11: [REFUTED] — #964 proposes the stated replacement, but does not resolve the local misdirection

**Anchor:** [Issue #964, Proposed design and Deliberately excluded](https://github.com/ray-manaloto/dotfiles/issues/964) |

> “The gate goes INSIDE the retry”

> “The local … path keeps `run_lock_passes` as-is.”

**Falsifier:** The issue would need to omit the internal gate, include the local path, or claim the implementation had shipped.

**Probe + control arm:**

- Live issue reading → proposes a composite containing the gate inside `nick-fields/retry`, plus `MISE_HTTP_RETRIES=5`.
- Control: its status explicitly says research/design only; the current action still contains the original loop.
- Independent shell replay → confirms the defect the proposed retry wrapper addresses.
- Current `image_lock.py:312–313` → confirms the excluded local warning survives.

**Result:** The issue is accurately represented as a proposed CI retry repair. It is not evidence that packaging failures recover, nor that the local diagnostic has been corrected.

Its “~5s” versus “~35s” estimates are approximate **pre-jitter sleep totals**, excluding request durations. With equal jitter, the corresponding sleep sums are approximately `[2.6,5.2)` and `[17.6,35.2)` seconds.

**Replacement text — proposed clarification:**

> This design addresses CI command retry and primary-quota waiting. It does not make deterministic version-resolution failures recoverable. Correct the local failure attribution independently. Retry timing estimates exclude request durations and are reduced by equal jitter.

### Finding 12: [NEEDS-VERIFICATION] — #908’s symptom is not quota; its dependency mechanism remains hypothetical

**Anchor:** [Issue #908, Hypothesis](https://github.com/ray-manaloto/dotfiles/issues/908) | “Hypothesis (evidence below, NOT yet proven)”.

**Falsifier:** A controlled regeneration would need to establish that npm backend dependencies cause the undeclared `node` entry.

**Probe + control arm:**

- Live issue reading → the recorded failure is `stale mise.lock entries for removed tools: ['node']`, with a specific CI run/job.
- Read `tests/test_lock_coverage.py:189–207` → this assertion compares locked and declared tool sets; it does not inspect HTTP failures or quota.
- Current mise `src/backend/npm.rs:312–317` says backend dependencies order already-configured tools and “do not add missing tools.”
- Control at `:383–389` → default version enumeration uses HTTP without requiring node/npm; `npm.shell_out` takes a separate path.

That current source is evidence **against assuming** the issue’s proposed mechanism. It does not settle what the exact historical runner version/configuration did.

**Settling probe:** Reproduce the original runner/configuration in disposable environments, holding mise version, task tools, settings, and global configuration fixed. Compare npm declarations present versus absent, and user-global node present versus absent. Inspect regenerated lock contents in every arm.

**Replacement text:**

> The observed failure is a root-lock coverage mismatch involving an undeclared `node` entry. Its generating mechanism remains unverified. It is not evidence of GitHub quota exhaustion. Preserve the implicit-dependency explanation as a hypothesis until the controlled regeneration distinguishes it from task-scoped tools and configuration inheritance.

The remaining practical limitation is execution evidence: this read-only session blocked Graphify startup and uv cache initialization, so I did not recreate the five-pass lock incident or run live quota-exhaustion experiments. The incident and 1-versus-865 counts remain your supplied measurements; the shell behavior, surviving wording, history, issues, and cited source branches were independently checked.

## GitHub repos touched

- [jdx/mise](https://github.com/jdx/mise) — rate-limit handling, http.rs retry logic, backend version resolution
- [jdx/wait-for-gh-rate-limit](https://github.com/jdx/wait-for-gh-rate-limit) — precursor gate tool, 59-line implementation
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — lock-refresh action, image_lock.py, skills/rules being audited

