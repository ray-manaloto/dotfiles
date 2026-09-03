> ## ⚠️ CORRECTION — this report's VERDICT is wrong (added 2026-09-03 by the architect)
>
> The conclusion "probably not applicable — mise + the loop already handle it" is
> **refuted on both of its supports**, by measurement made after this report was written:
>
> 1. It rests on *"the blind loop already accommodates mid-run quota exhaustion."* **It does
>    not.** `.github/actions/lock-refresh/action.yml:67` runs under `set -euo pipefail`
>    (`:38`), so the first failing pass ABORTS the step. Measured both arms: failing pass ->
>    1 iteration, rc=1, never retries; succeeding passes -> all 5 run. The loop retries only
>    when retrying is unnecessary. This report did not account for `set -e`.
> 2. It treats mise's internal retry as covering exhaustion. **It does not.**
>    `src/http.rs:1809-1828`: with `x-ratelimit-remaining: 0` mise warns "resets at ..." and
>    RETURNS, and comments that `retry-after` "is processed only if x-ratelimit-remaining is
>    not 0 or is missing". Waiting out a real exhaustion is exactly what mise declines to do
>    — and exactly what `wait-for-gh-rate-limit` does.
>
> The report's FACTUAL sections (mise's retry schedule and default of 3; the tool being a
> precursor gate rather than a wrapper) were independently re-verified against source and
> are sound. It is the verdict built on them that inverts.
>
> Superseded by **#964**, which carries the corrected analysis and the agreed design.

# Rate-Limit Retry Research: GitHub Rate Limits in CI Workflows

**Date:** 2026-09-03  
**Scope:** Compare blind fixed-count retry loops (current dotfiles) vs jdx/wait-for-gh-rate-limit approach; assess applicability to `mise lock` workflows.

---

## Current Dotfiles Implementation

**File:** `.github/actions/lock-refresh/action.yml` (mise-system.lock step)  
**Python equivalent:** `python/src/dotfiles_setup/image_lock.py:run_lock_passes()`

### The loop

```bash
for _ in 1 2 3 4 5; do
  MISE_ENV=runtime "$stage/mise-pinned" lock --bump --platform linux-x64 -C "$stage"
done
```

### Characteristics

- **5 fixed passes**, no backoff, no rate-limit awareness
- **Ignores each pass's exit code** — the loop always completes all iterations
- Token is passed: `GITHUB_TOKEN` and `MISE_GITHUB_TOKEN` env vars ARE set
- "Converged" is **inferred** rather than checked; no validation that the final pass succeeded
- Documented intent: "Each pass fills what the previous could not resolve; exhausted GitHub quota is the **expected mid-run failure**"
- Python docstring (line ~168): "Earlier passes are allowed to fail — that is what the loop is for, since exhausted GitHub quota is the expected mid-run failure."

### Exit-code handling

- Python `run_lock_passes()` (line ~178–182): checks `last.returncode == 0` EACH pass and **returns early on first success**
- If all 5 fail: stores the last `CompletedProcess` and `check_lock_result()` errors on it
- Bash action: no checking; relies on downstream `lock-collect` to validate coverage

---

## jdx/mise Approach: wait-for-gh-rate-limit

**Repository:** [jdx/wait-for-gh-rate-limit](https://github.com/jdx/wait-for-gh-rate-limit)  
**Invocation in mise release.yml:** [line ~310, e2e-linux job](https://github.com/jdx/mise/blob/b32e12449d2c0ce56ac161dec555ab46734b13cb/.github/workflows/release.yml#L310)

```yaml
e2e-linux:
  steps:
    - run: mise x wait-for-gh-rate-limit -- wait-for-gh-rate-limit
    - run: mise i
```

### How it works (source: src/main.rs)

1. **Queries `/rate_limit` endpoint**: Hits `https://api.github.com/rate_limit`
2. **Reads `remaining` count**: Extracts from `resources[resource].remaining`
3. **Resource-aware**: Defaults to "core" resource; accepts any named resource as first arg
4. **Sleeps to reset epoch** if `remaining <= 1`:
   - Calculates duration: `rate_limit.reset - Utc::now().timestamp()` + 1 second
   - Sleeps for that duration (full backoff until reset)
   - Prints `"GitHub {resource} rate limit exceeded, sleeping for {rel_time} until {reset_time}"`
5. **Otherwise reports**: If quota available, prints `"GitHub {resource} rate limit: {remaining}/{limit} - resets at {reset_time}"`
6. **Exit code**: Always `0` (success) — the tool is not a gate, it's a **wait-for** primitive

### Token handling

- Reads `GITHUB_TOKEN` or `GITHUB_API_TOKEN` env var if present
- Falls back to anonymous quota if unset
- Sends token as `Bearer` auth header

### Key limitation

**This is a precursor gate, NOT a retry wrapper.** It checks quota **before** a workload starts (before `mise i`). It does NOT:
- Wrap or retry an individual command
- Handle mid-run quota exhaustion
- Use exponential backoff (it sleeps to the epoch, which is binary: either quota remains or it doesn't)

---

## mise's Internal Retry Logic

**Source:** mise's own http.rs — the tool that `mise lock` uses for all GitHub API calls

### Retry mechanism

mise has **built-in exponential backoff with jitter** for ALL transient errors, including 429 (rate limit exceeded).

**Key functions:**

1. **`retry_async_with_retries()` (line 1959–2000):**
   - Uses `default_backoff_strategy(retries)` to generate delays
   - Classifies error as transient with `is_transient(&err)` 
   - Retries only on transient errors; non-transient errors fail immediately
   - Default: `Settings::get().http_retries()` (config-driven, not hard-coded)

2. **`default_backoff_strategy()` (line 1844–1857):**
   - Fixed schedule: `[200ms, 1s, 4s, 15s, 15s, 15s, …]`
   - Applies **equal jitter** per AWS guidance: `[d/2, d)` range
   - Repeats 15s after schedule exhausted
   - Respects `MISE_HTTP_RETRIES` env var (arbitrarily configurable)

3. **`is_transient()` (line 1910–1950):**
   - **DNS errors**: NOT transient (fail immediately)
   - **Timeout**: transient
   - **Connection refused**: transient  
   - **Request body drop mid-stream**: transient
   - **HTTP/2 REFUSED_STREAM**: transient (is_request() && no status)
   - **Status 408** (Request Timeout): transient
   - **Status 429** (Too Many Requests): **transient** ← **rate limits ARE retried**
   - **5xx server errors**: transient
   - **Other 4xx**: NOT transient (fail immediately)

### Example: what happens when `mise lock` hits rate limit

1. `mise lock` issues a GitHub API request to resolve a tool version
2. GitHub returns `429 Too Many Requests`
3. mise's HTTP layer catches it, sees status 429
4. `is_transient()` returns `true`
5. `retry_async_with_retries()` sleeps: ~200ms (±50%), then retries
6. Repeats up to `MISE_HTTP_RETRIES` times (default settable via config/env)
7. If quota recovers during backoff window, request succeeds
8. If all retries exhaust, error propagates to caller (`mise lock`)

**Result:** mise's retry is EXPONENTIAL BACKOFF with BOUNDED JITTER, not a fixed delay or a sleep-to-epoch.

---

## Applicability Assessment

### Problem statement: "quota exhausts mid-run across many tool resolutions"

The dotfiles loop and mise's retry solve **the same problem**, but at different layers:

| Layer | Dotfiles | mise | wait-for-gh-rate-limit |
|-------|----------|------|------------------------|
| **Purpose** | Retry failed `mise lock` invocations | Retry failed HTTP requests within `mise lock` | Precursor: check quota before expensive work |
| **Trigger** | Exit code of `mise lock` (non-zero) | HTTP status 429 | Quota level check (remaining ≤ 1) |
| **Backoff** | None (5 fixed passes) | Exponential: 200ms → 1s → 4s → 15s | Binary: sleep to epoch or continue |
| **Applies at** | Command level | HTTP request level (per API call) | Workflow step level (pre-gate) |
| **What it retries** | Entire `mise lock` command | Individual GitHub API calls | Nothing; just waits |

### Critical finding: are they redundant?

**NO, they are complementary BUT with a caveat:**

1. **mise's retry is the primary defense**: It handles quota exhaustion at the HTTP layer for every API call that `mise lock` makes. This already converts many transient rate-limit errors into retries with exponential backoff.

2. **The dotfiles loop is a **secondary defense at the command level**: If `mise lock` itself hard-fails (not just one API call), the loop reruns the entire command. This catches cases where:
   - Quota is exhausted so heavily that multiple tools fail in one `mise lock` run
   - Different tools need different resolutions, and partial success → partial lock file
   - The first pass locked tools A, B; quota exhausted mid-C; next pass locks C, D; eventually all converge

3. **wait-for-gh-rate-limit is optional**, meant for workflows where quota is **already depleted before work starts** (e.g., many prior jobs in a matrix). It's a "sleep until quota resets" gate, not a retry mechanism.

### Whether dotfiles should use wait-for-gh-rate-limit

**Unclear applicability**. The tool's value is:
- **If quota is fully exhausted BEFORE `lock-refresh` starts**: it saves ~X hours by sleeping instead of failing
- **If quota is still available**: it exits immediately with "remaining: N/M" message

But `lock-refresh` already passes `GITHUB_TOKEN`, which gives it authenticated quota. The blind loop already expects partial failures mid-run and converges. Using `wait-for-gh-rate-limit` as a precursor would add:
- A precursor API call (the `/rate_limit` query itself)
- An extra wait-step before `mise lock` starts
- No benefit if quota is available (it just checks, then proceeds)
- Conditional benefit only if quota is **already depleted globally** (rare in CI unless many jobs are serialized)

---

## Alternative Approaches

### 1. **Pass the token and rely on mise's built-in retry (current state)**

- **Pros**: mise already does exponential backoff for 429; minimal code
- **Cons**: Rate limit can still cause `mise lock` to exit non-zero after retries exhaust; the outer loop then reruns the whole command (less efficient than retrying individual APIs)
- **Status**: Already in place

### 2. **Increase `MISE_HTTP_RETRIES` (if it's below the default)**

- **Pros**: Extends the retry window for each API call without new code
- **Cons**: Adds latency if many calls fail; doesn't help if quota is **structurally insufficient** for the workload
- **How**: `MISE_HTTP_RETRIES=10` in the action (or env block)
- **Measurement**: Check current value; if not set, mise uses its default (unconfirmed in the code, but likely 3–5)

### 3. **Use wait-for-gh-rate-limit as a precursor gate**

- **Pros**: Fail-fast if quota is already exhausted; sleep once, then proceed
- **Cons**: Adds HTTP call; only useful if quota is already depleted (rare mid-run)
- **Applicability to dotfiles**: Low — the blind loop already converges; the extra gate adds latency for the common case (quota available)

### 4. **Check the last pass's exit code instead of assuming convergence**

- **Current bash action** (line ~60): `for _ in 1 2 3 4 5; do … done` (no rc check)
- **Improved**: Check `last_rc` before calling `lock-collect`
- **Code change**: ~3 lines
- **Impact**: Fail loudly if `mise lock` exits non-zero on the final pass (currently relies on downstream validation)

### 5. **Configure `mise lock --retries` if that flag exists**

- **Status**: Unknown — would need to check mise's lock command
- **Hypothesis**: mise may expose `--retries` or `--http-retries` as a flag
- **If yes**: Pass it directly to `mise lock`, overriding the global setting for this command
- **If no**: Not available

---

## Key Unknowns (Probes Needed)

1. **What is mise's default for `MISE_HTTP_RETRIES`?**
   - Setting in `src/env.rs` or `src/config/`?
   - Measured via `mise config` output?
   - Probe: Check `.devcontainer/mise-system.toml` and default behavior

2. **Does `mise lock` expose a `--retries` or `--http-retries` flag?**
   - Probe: `mise lock --help` inside the devcontainer

3. **How often does the blind loop actually need 4+ passes?**
   - Measurement: Grep CI logs for "pass 4" / "pass 5" entries
   - If rare (<5% of runs), the outer loop may be over-engineered

4. **Is `MISE_GITHUB_TOKEN` the right var, or should it be `GITHUB_TOKEN` only?**
   - mise's http.rs reads tokens from env; check which ones it honors
   - Probe: grep mise source for `GITHUB_TOKEN`, `MISE_GITHUB_TOKEN`, `GH_TOKEN`

5. **What is the actual latency cost of each pass?**
   - Bash action: does not emit timing; Python `image_lock.py` logs at INFO level
   - Measured in CI: typical `mise lock` runtime (seconds)

---

## Conclusion

**The blind 5-pass loop and mise's internal retry logic are not redundant; they operate at different layers:**

- mise's retry (HTTP level, exponential backoff) catches transient rate-limit errors on individual API calls
- The outer loop (command level, fixed 5 passes) retries the entire `mise lock` if it exits non-zero

**Whether wait-for-gh-rate-limit is worth adopting:** Probably not for dotfiles' lock-refresh job, because:
1. The job already has `GITHUB_TOKEN` (authenticated quota)
2. The blind loop already expects and handles partial failures
3. The precursor gate adds latency for the common case (quota available)
4. It would only save time if quota is **already depleted before the job starts** (rare)

**Recommended next steps:**
1. Verify mise's default `MISE_HTTP_RETRIES` and whether the token is being used
2. Check if `mise lock --help` exposes a retries flag
3. Measure how often the loop actually needs passes 4–5 in CI
4. (Optional) Document the "early exit on success" behavior to clarify why pass 1 often succeeds after quota recovery

---

## GitHub repos touched

- [jdx/mise](https://github.com/jdx/mise) — HTTP retry logic, rate-limit handling, backoff strategy
- [jdx/wait-for-gh-rate-limit](https://github.com/jdx/wait-for-gh-rate-limit) — precursor rate-limit gate tool
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — lock-refresh action, image_lock.py implementation
