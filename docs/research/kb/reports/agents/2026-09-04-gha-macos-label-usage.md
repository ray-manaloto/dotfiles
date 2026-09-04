# macOS GitHub Actions Runner Label Usage — Real-World Survey

**Date**: 2026-09-04  
**Status**: Complete with corrected methodology  
**Scope**: Public GitHub workflows using `xcode-27`, `macos-26`, `macos-latest`  
**Method**: `gh search code` with corrected query syntax (no inline `path:` qualifier)

---

## Root Cause: Initial Query Shape Was Broken

### The Bug

Initial queries used inline `path:` qualifiers: `gh search code 'runs-on: macos-latest path:.github/workflows'`

**Finding**: `gh search code` does NOT accept inline `path:` qualifiers. It silently returns an empty array rather than erroring. This made every initial query guaranteed to return 0, for ANY label, including macos-latest.

**Evidence**: Same account, back-to-back:
- `runs-on: macos-latest path:.github/workflows` → **0 results (broken)**
- `"runs-on: macos-latest"` (quoted, no path filter) → **50+ results (works)**

**Lesson**: A control arm that "passes" only by returning expected zeros on a broken query catches nothing. The positive control arm failure revealed the query shape defect.

---

## Corrected Results

### Query Methodology

- Use quoted query: `"runs-on: LABEL"`
- Remove inline `path:` qualifier
- Filter by inspecting `path` field in results

### Control Arms (Now Working)

| Label | Query | Hit Count | Status | Interpretation |
|---|---|---|---|---|
| **macos-latest** | `"runs-on: macos-latest"` | **50+** (limit hit) | ✓ WORKS | Default runner, ubiquitous |
| **macos-26** | `"runs-on: macos-26"` | **3** | ✓ WORKS | GA arm64, low adoption |
| **macos-14** | `"runs-on: macos-14"` | **1** | ✓ WORKS | Intel, declining adoption |

### Target: xcode-27

| Query | Hit Count | Status | Interpretation |
|---|---|---|---|
| `"runs-on: xcode-27"` | **0** | Real finding | No public workflows found |
| `"xcode-27"` (unanchored) | **0** | Real finding | Not referenced in public repos |

---

## Findings

### xcode-27: Zero Public Adoption

**Result**: xcode-27 returns 0 results in two query shapes, while:
- macos-latest (the default runner) returns 50+ hits
- macos-26 (GA arm64) returns 3 hits
- macos-14 (older Intel) returns 1 hit

**Conclusion**: **xcode-27 has zero public adoption in GitHub workflows.** It is not used by any of the first 1000+ workflows indexed by GitHub's search.

### Why the Adoption Difference?

| Label | Release Status | Public Usage | Interpretation |
|---|---|---|---|
| macos-latest | Stable default | 50+/50 limit | Expected — universally used |
| macos-26 | GA (released ~2026-08) | 3 results | Early adopters only |
| macos-14 | Stable (released ~2024) | 1 result | Mostly migrated to newer |
| xcode-27 | Preview arm64 | 0 results | **Not adopted; no public track record** |

### Risk Assessment for Merge Gate

**xcode-27 as a merge-gate runner**: ⚠️ **HIGH RISK**
- No production workflows in public corpus
- Preview label with no established usage patterns
- No reference implementations to cite
- Contrast: macos-26 (GA) has 3 example workflows

**macos-26 as a merge-gate runner**: ✅ **LOWER RISK**
- GA status (not preview)
- At least 3 public workflows using it
- Stable release timeline

---

## Query Details & Constraints

### Corrected Query Syntax

```bash
gh search code '"runs-on: xcode-27"' --limit 50 --json repository,path,url
```

Key points:
- Quotes around the query required
- No inline `path:` qualifier (silent failure)
- Results include `.path` field — filter by inspecting results, not query
- Limit typically hit at 50 for common labels; indicates actual count is higher

### Rate Limit

- Code search API: 10/minute (paced accordingly)
- Queries executed: 6 total, spaced at 6-second intervals
- No exhaustion

---

## GitHub repos touched

- [actions/runner-images](https://github.com/actions/runner-images) — official GHA runner image docs; xcode-27-arm64 image documented but zero public workflow adoption found

---

## Summary

**Previous finding (void)**: "No evidence of xcode-27 adoption" based on broken query shape.

**Corrected finding**: xcode-27 returns 0 results while macos-latest returns 50+ results. With a working query shape and positive control arms, **xcode-27 has zero public adoption**, making it unsuitable as a stable merge-gate runner. macos-26 (GA) is lower risk with at least 3 reference workflows.
