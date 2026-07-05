---
name: pkl-import-hyphen-alias-expertise
description: "Use when a Pkl file imports hyphenated filenames - an `as` alias is required. (Historical: pklr once lacked import/spread; parity-verified fixed at hk 1.49, the HK_PKL_BACKEND=pkl override is retired.)"
---

# Pkl Import Alias Required for Hyphenated Filenames

## The Insight
When splitting pkl config into shared modules, filenames with hyphens (e.g., `hk-common.pkl`) MUST use an `as` alias in the import statement. Pkl treats hyphens in identifiers as syntax errors. (Historical note: early `pklr` (Rust) evaluators did not support `import`/spread; verified FIXED by hk 1.49 — the check/fix plans under pklr and the pkl CLI are byte-identical, so the `HK_PKL_BACKEND=pkl` override was retired in #160 T12.)

## Why This Matters
The hk.pkl split (PR #42) created `hk-common.pkl` for shared checks. Initial attempts to `import "hk-common.pkl"` without an alias, or using `pklr` as the backend, produced cryptic evaluation failures with no clear error message pointing to the import.

## Recognition Pattern
- Pkl evaluation fails with syntax or identifier errors after adding imports
- You're on an OLD hk (<1.47) with pklr and import/spread syntax
- Filename contains hyphens and import doesn't use `as` alias

## The Approach
1. Always alias hyphenated pkl imports: `import "hk-common.pkl" as common`
2. On hk ≥1.49 the default pklr backend handles import/spread (no override needed)
3. Verify with `hk validate` after any pkl config changes
4. (Retired) the HK_PKL_BACKEND=pkl override was removed repo-wide in #160 T12

## Example
```pkl
// WRONG — hyphen in implicit identifier
import "hk-common.pkl"

// WRONG — pklr doesn't support import
// HK_PKL_BACKEND=pklr

// RIGHT
import "hk-common.pkl" as common
// HK_PKL_BACKEND=pkl
hooks { ["pre-commit"] { steps { ...common.hygiene } } }
```
