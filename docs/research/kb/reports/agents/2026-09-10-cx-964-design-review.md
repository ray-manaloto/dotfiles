# Codex Design Review: Issue #964 Revisited Against Deterministic Failure Evidence

**Date:** 2026-09-10  
**Route:** routed through codex CLI (GPT-5.6-Sol, xhigh reasoning, read-only)  
**Status:** in progress

## Background

On 2026-09-10, `mise run lock-image` failed deterministically 5 times with the error:

```
fnox@latest: no versions found for fnox matching date filter
```

**Root cause:** mise 2026.9.2-9.4 promoted the `packslip` backend to tier 1;
the registry shorthand now selects it, and packslip only lists releases
carrying packslip manifests. Under the then-current `minimum_release_age =
"7d"`, all versions were filtered out, so `latest` was unresolvable.

**Misleading signal:** Throughout all 5 passes, `image_lock.py:311-314`
printed "retrying (rate limits are the expected cause)" — a hardcoded
message that misdirected investigation twice before the real cause
(version-filter drift) was found.

**Current fix:** `minimum_release_age = "0s"` across all mise configs
(2026-09-10, post-incident).

## Issue #964 Design (OPEN)

The issue proposes a **rate-limit gate** inside a `nick-fields/retry` action,
wrapping `mise lock` in the CI workflow, under the reasoning that the
current blind retry loop **cannot run** under `set -e`.

### The Design Under Review

1. **Root diagnosis:** `.github/actions/lock-refresh/action.yml:67` runs
   under `set -euo pipefail` (:38), so the first failing pass aborts the
   step. Measured with both arms: failing pass → 1 iteration, rc=1, never
   retries; succeeding passes → all 5 run. ✓ VERIFIED.

2. **Proposed solution:** Replace the blind loop with a composite action
   containing `wait-for-gh-rate-limit` (gates before retrying) inside a
   `nick-fields/retry` wrapper (retries the gate + the lock command together).

3. **Deliberately excluded:** The local `mise run lock-image` path keeps
   `run_lock_passes` (Python) unchanged, with its docstring promising
   "Earlier passes are allowed to fail." The current test
   `test_the_composite_and_the_local_task_resolve_the_same_way()` must
   have its docstring updated to name the **deliberate divergence by design**.

## Critical Question

**Does #964's design still hold now that a second, deterministic, NON-quota
failure class is proven to occur in the very loop it redesigns?**

Today's failure was:
- **Deterministic** — all 5 passes failed the same way, every time
- **Not a rate limit** — a version-filter mismatch that would never resolve
  with more retries or waiting
- **Mid-loop** — the failure occurred inside the lock command, not at a
  boundary

The question for codex: Should the convergence loop distinguish a retryable
failure from a deterministic one BEFORE spending remaining passes? If yes,
what concrete signal in `mise lock`'s output or exit code can discriminate them?

## Prompt for Codex

[See below — codex invocation pending]

---

## Codex Analysis

_Awaiting shell-out to codex. Report will be updated incrementally._

**Verdict: revise #964 before implementation.** Its `set -e` diagnosis remains correct, but gate-plus-retry does not distinguish deterministic failures. I read the live issue and current files; no files were edited.

**1. Q1: Design still holds? — Partially; the deterministic case becomes worse in wall-clock cost.**

The original defect remains: the composite enables `set -euo pipefail` at [action.yml:38](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.github/actions/lock-refresh/action.yml:38), then executes an unguarded lock command inside the loop at [action.yml:67](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.github/actions/lock-refresh/action.yml:67). The recorded failure/success controls confirm one failing iteration versus five successful iterations. [Research report:6–15](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/docs/research/kb/reports/agents/2026-09-03-rate-limit-retry-research.md:6)

However, the proposed gate reads `/rate_limit`, checks the selected resource, and sleeps when `remaining <= 1`. It never examines the lock command’s output. [Gate src/main.rs:10–45](https://github.com/jdx/wait-for-gh-rate-limit/blob/c68d44602cd9ecead5daaa39075e432e3f3827b4/src/main.rs#L10-L45)

Consequently:

- **Failure outcome:** unchanged; waiting cannot repair the supplied empty-candidate failure during these attempts.
- **Classification:** unchanged; available quota does not classify the command’s error.
- **Wall clock:** worse than today’s first-failure CI abort because retries repeat doomed work. The gate adds requests and, if quota is also exhausted, potentially a reset wait. **Exact additional duration: UNVERIFIED**, because the proposed composition was not executed.

Keep gate-inside-retry for quota recovery, but determine retry eligibility first. Incidentally, the module already documents another deterministic five-pass failure involving unsupported platforms. [image_lock.py:140–145](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/image_lock.py:140)

**2. Q2: Local path exclusion survives? — No, its stated justification is false.**

The supposedly interactive entrypoint already runs unattended in CI:

```yaml
run: mise run lock-image -- --no-container
```

That invocation appears at [refresh.yml:345–353](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.github/workflows/refresh.yml:345). Therefore, “local command” does not imply “human watching.”

The Python loop inherits subprocess output but examines only `returncode`; every failure receives the quota attribution, including the final attempt when no retry remains. [image_lock.py:305–320](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/image_lock.py:305)

**The deterministic-failure signal should propagate through both paths. I do not recommend divergence in resolution semantics or failure classification.**

The parity test’s promise is broader than its enforcement: it only checks that `--bump` and `--platform` occur in both command representations. It does not compare retry decisions, diagnostics, or even complete argument equality. [test_image_lock.py:249–264](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/tests/test_image_lock.py:249)

Changing its docstring alone would document divergence without testing the new behavior. Preserve its flag checks and add behavior coverage for the deterministic failure and a genuinely retryable failure in both entrypoints.

**3. Q3: Can distinguish failures? — Yes for located diagnostic cases; not from the current loop or exit code alone.**

Concrete signals exist:

| Signal | Verified meaning |
|---|---|
| `no versions found for … matching date filter` | Mise emits this when no versions are available with a cutoff active, after checking for a recorded version-list fetch failure. [tool_version.rs:63–76](https://github.com/jdx/mise/blob/v2026.9.4/src/toolset/tool_version.rs#L63-L76) |
| `unable to fetch versions for …: …` | A recorded fetch failure is reported separately, preserving its cause. It is **not automatically retryable** merely because fetching failed. [tool_version.rs:65–69](https://github.com/jdx/mise/blob/v2026.9.4/src/toolset/tool_version.rs#L65-L69) |
| `GitHub rate limit exceeded. Resets at …` | Generated for HTTP 403/429 with `x-ratelimit-remaining: 0` and a readable reset timestamp. [http.rs:1942–1962](https://github.com/jdx/mise/blob/v2026.9.4/src/http.rs#L1942-L1962) |
| HTTP warning containing `(transient)` | Mise’s HTTP retry path explicitly classifies the error before emitting this warning. [http.rs:2104–2127](https://github.com/jdx/mise/blob/v2026.9.4/src/http.rs#L2104-L2127) |

The supplied incident’s exact message therefore provides a concrete signal for stopping futile retries. It is not a complete taxonomy: the date-filter wording does not independently establish *why* the eligible catalogue is empty, and a transient warning earlier in a multi-tool invocation does not establish that its eventual terminal error is retryable.

There is **no distinct ordinary “version missing” versus “network transient” exit code** in the inspected paths: ordinary errors converge on status `1`. [main.rs:157–168](https://github.com/jdx/mise/blob/v2026.9.4/src/main.rs#L157-L168)

No additional setting is needed to make this unresolved-tool failure nonzero. That behavior was introduced in 2026.6.13; the CHANGELOG records “fail when active tools cannot resolve.” [CHANGELOG:3279](/private/tmp/mise-changelog.md:3279) `--json` describes version changes, not a structured error-classification interface. [Lock CLI documentation](https://mise.jdx.dev/cli/lock.html)

**UNVERIFIED:** an implemented classifier and its real two-arm execution. This review establishes available signals, not a tested implementation.

**4. Q4: Is wait-for-gh-rate-limit still right? — Suitable for quota-reset waiting; insufficient as the complete fix.**

The repository requires checking native capabilities before adding custom machinery. [use-tool-builtins.md:19–32](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/rules/use-tool-builtins.md:19)

Live probes against installed mise **2026.9.4** returned:

```text
error: unexpected argument '--wait-for-rate-limit' found
error: unexpected argument '--skip-rate-limited' found
```

Both exited `2`. Neither `wait` nor `sleep-until` appears in its native command inventory. [CLI inventory](https://mise.jdx.dev/cli/)

Relevant native capabilities are:

- **HTTP retries:** default `3`, independently confirmed by `mise --no-config settings ls --all --json`. They classify transient failures and use bounded backoff; the exhaustion diagnostic does not sleep until reset. [Settings](https://mise.jdx.dev/configuration/settings.html#http_retries), [http.rs:1942–1999](https://github.com/jdx/mise/blob/v2026.9.4/src/http.rs#L1942-L1999)
- **Better error attribution:** 2026.7.16 introduced reporting version-list fetch failures instead of blaming filters. This directly helps the review’s classification problem. [CHANGELOG:2035](/private/tmp/mise-changelog.md:2035), [current implementation](https://github.com/jdx/mise/blob/v2026.9.4/src/toolset/tool_version.rs#L63-L76)
- **Explicit release-age controls:** global/per-tool `minimum_release_age`, exclusions, and the CLI override. No automatic relaxation for backend/catalogue drift was found in the inspected settings. [Release-age settings](https://mise.jdx.dev/configuration/settings.html#minimum_release_age)

The working tree now explicitly sets `"0s"` in [mise.toml:106](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/mise.toml:106) and [mise-system.toml:336](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.devcontainer/mise-system.toml:336). These address eligibility; the quota gate does not.

There is also a dependency-bootstrap problem: upstream documented `mise x wait-for-gh-rate-limit` failing while installing the helper under exhausted quota, before the helper could wait. The proposed on-demand installation must account for that. [Upstream #11914, root cause](https://github.com/jdx/mise/pull/11914)

**5. Q5: Stale claims in #964? — Edit these specific sections.**

Against the [live issue body](https://github.com/ray-manaloto/dotfiles/issues/964#issue-5341880708):

- **§4, “Our failure is exhaustion mid-run.”** Narrow this to the quota failure class. Add the deterministic version-filter incident and specify that re-gating does not identify or repair it.
- **“Deliberately excluded”: “A local run is interactive.”** Remove this premise; [refresh.yml:353](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.github/workflows/refresh.yml:353) directly contradicts it.
- **“keeps run_lock_passes as-is.”** Revise the scope to include truthful diagnostics and consistent failure classification in the Python entrypoint. Its current behavior is visible at [image_lock.py:307–317](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/image_lock.py:307).
- **Parity-test docstring update.** Replace the docstring-only proposal with explicit behavioral requirements. The present test checks flags, not retry semantics. [test_image_lock.py:259–264](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/tests/test_image_lock.py:259)
- **§2, native-behavior research.** Add the existing fetch-versus-filter diagnostic distinction and refresh source anchors: the quota diagnostic is now at `http.rs:1942–1977`, rather than the issue’s historical `1809–1828`.
- **§4, on-demand helper installation.** Add the upstream cold-cache/bootstrap limitation identified above.

The exact phrase **“retrying (rate limits are the expected cause)” is not in the live issue body**. It is in the implementation; add it to the issue as misleading incident evidence and an explicit correction target.

Preserve the proven `set -e` diagnosis and default-three HTTP retry finding: both still hold.

**Evidence boundary:** I did not replay lock regeneration. The host reports 2026.9.4, but the recipe installs the Dockerfile’s current **2026.9.1** pin. The exact binary responsible for the supplied incident remains **UNVERIFIED** without its invocation/version receipt. [Dockerfile:115](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.devcontainer/Dockerfile:115), [image_lock.py:437–439](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/image_lock.py:437)
---

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — issue #964, image_lock.py, lock-refresh action, test coverage, mise config
- [jdx/mise](https://github.com/jdx/mise) — HTTP retry logic, version resolution, release-age filtering, error classification, CHANGELOG
- [jdx/wait-for-gh-rate-limit](https://github.com/jdx/wait-for-gh-rate-limit) — the proposed gate tool, installed via `mise x`
- [nick-fields/retry](https://github.com/nick-fields/retry) — the proposed retry action wrapper

---

**Report Status:** Complete. Codex exit code: 0. Verdict written 2026-09-10. All file:line citations present.
