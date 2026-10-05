# LLVM fix round 4 working evidence

Initial HEAD ec7959bb, branch feat/llvm-23-detect-bump; clean tracked tree.
Scope: six specified files; rows 1 and 3-8; pins remain 22; no push.
Re-read cold-reviewer-llvm-fix3-4d6c666c-2026-10-03.md and nested instructions.
Confirmed installed Renovate 44.132.2 deb datasource has no releaseTimestamp;
lookup/filter-checks.js has positive control and explicitly proceeds for timestamp-optional.
Current test fixture omits packageRules; update fixture to include the real LLVM group and Ubuntu pocket rule, because missing rules must now fail parity.
No code/spec contradiction found. Evidence belongs to this lane; coordinator findings/index/native goal untouched.

Before implementation: new regression selection 19 failed / 3 passed, rc 1.
Failures cover rows 1, 3, 4, pocket deletion and each URL, codename drift,
group/negation signature drift, epoch-less classification, all four duplicate
active/commented combinations, bad gzip header URL, corrupt deflate and truncated gzip.
Existing capture binding, epoch-present control and missing-Version control already pass.
Research attempt 1: all sources ran; Last30Days failed schema validation because
ranking_query missing. Other providers succeeded with verified GitHub empty controls.
Preserved attempt-1 manifest; correcting plan and retrying strict-five.

## Final behavior and gates before commit

Rows 1/3/4: operator wording now explicitly says no soak, 58 LLVM entries
(52 active + 6 commented) and 14 Ubuntu entries, index presence is not
installability, verify-apt-pins covers active pins on one platform only.
Row 5: parity requires one deb negation rule with exactly release/archive,
updates/archive and security/security URLs, main/amd64, derived from the
validated LLVM template codename. Missing rule and drifting URLs are rejected.
Row 6: gzip/parser exceptions (OSError includes BadGzipFile, EOFError,
zlib.error, KeyError, ValueError and TypeError) normalize to ValueError with
URL in _index_versions; public CLI returns 1 with no traceback. Real truncated
and corrupt deflate bytes are tested with HTTP 200.
Row 7: _APT_LLVM_VERSION remains unchanged; both Renovate selectors derive
from its anchored, epoch-required pattern. The manager capture expected string
also derives from that pattern; its existing JSON encoding already agrees.
Native Renovate 44.132.2 RE2 extraction, predicates and actual packageRules
application confirmed epoch-bearing, epoch-less and embedded-signature controls;
all routes agree. Native current inventory: 58 LLVM + 14 Ubuntu.
Row 8: bootstrap_pins refuses every active/commented duplicate combination,
with full-file line numbers. Planner's earlier rewrite-duplicate test now
expects the required earlier inventory rejection for duplicate pins.

Allowed targeted suite: 281 passed, no skips. Ruff check/format and changed-file
ty clean; renovate-validate confirmed RE2 live, token-audit rc 0, llvm-parity rc 0.
Live apt-liveness --markdown rc 0: 72 pins (66 active + 6 commented), 58 LLVM
(52 active + 6 commented), 14 Ubuntu; all exact pins published on amd64/arm64.

## Research and actual tools

Strict-five attempt 3 passed; manifest is bound to this turn:
/Users/rmanaloto/.codex/research-coverage/01a102ac-1ac1-7352-a8a1-3e84a9d99915/01a102ac-1e2c-7922-8b3e-bb6e84e9948d/manifest.json
All GitHub issues/discussions/releases arms have verified empty results with
positive controls; Exa, ctx7 Context7, Firecrawl developer/search, and Last30Days
returned successful evidence. All raw hashes are checked by native
validate_strict_five, not inferred from the process exit alone.
Primary docs: https://docs.renovatebot.com/configuration-options/#minimumreleaseagebehaviour
https://docs.renovatebot.com/modules/manager/regex/ and
https://docs.renovatebot.com/string-pattern-matching/.
Primary pinned source: installed Renovate 44.132.2 deb datasource and
lookup/filter-checks.js; positive releaseTimestamp control in lookup; no
releaseTimestamp in deb. Native deb doc scrape saved in firecrawl-deb-docs.md.
GitHub code search ran with positive README and fresh absent controls.

Skill used: research-sweep. App connectors / plugin MCP tools: none.
Last30Days cached plugin script ran indirectly through fanout with explicit plan.
Actual research routes: native fnox codex_research, mise/uv research-fanout;
gh REST/GraphQL/search; Exa HTTP; ctx7 CLI; Firecrawl developer API/search CLI
and scrape CLI; Last30Days Python engine; web primary-doc reads.
Validation tools: uv, ruff, ty, pytest, Renovate validator/Node native RE2,
curl for live indexes, mise llvm-parity/apt-liveness, git.

## Deviations / failed attempts

No implementation scope deviation or spec contradiction. No prohibited gates,
docker, installability run, push, pin/path/lock/Dockerfile/IWYU/workflow changes.
Incremental evidence uses this lane's report so coordinator findings/index/native
goal remain untouched. Research uses the developer-required research-gate checkout.
RESEARCH INCOMPLETE applied to attempt 1 (Last30Days missing ranking_query) and
attempt 2 (web source unavailable; no available planned sources remain).
Both failed manifests preserved; corrected to grounding source; attempt 3 passed.
Initial Ruff fix rc 1 for formatting and keyword-only bool test parameters;
corrected without suppressions. Initial post-fix targeted pytest rc 1 (280
passed) for obsolete duplicate-rewrite diagnostic; retargeted to required
new inventory diagnostic; final targeted suite green. Before run rc 1 was
intentional, proving the requested regression failures.
Supplemental read-only research controls/native Renovate proof and git scope
checks accompany the requested gates. Normal git hooks will run on commit.

Normal pre-commit hook is running its configured extra checks; all observed
checks are green so far. This includes its repository-wide ty check, whereas
the explicit lane ty gates were limited to the five changed Python files.
The hook is required by lane orders; it was not bypassed. No full pytest,
mise run lint/verify, docker or verify-apt-pins was invoked.

## Final delivery

Commit: `2c0ca279d78790696e1f1ca17d1def0b8640cea7`. One commit on feat/llvm-23-detect-bump; six authorized files; exact trailers; clean tree; never pushed.
Native pre-commit and commit-message hooks passed. Ruff reported all checks passed and format reported five files unchanged; patch numstat unchanged. No hook retry or suppression needed.

## Exit receipts (verbatim)

```text
EXIT=apt-liveness-live=0
EXIT=code-negative=0
EXIT=code-positive=0
EXIT=code-search=0
EXIT=commit-1=0
EXIT=firecrawl-deb-docs=0
EXIT=llvm-parity=0
EXIT=native-signature=0
EXIT=postcommit-audit=0
EXIT=precommit-audit=0
EXIT=pytest-before=1
EXIT=pytest-targeted-1=1
EXIT=pytest-targeted-2=0
EXIT=renovate-validate=0
EXIT=research-fanout-2=1
EXIT=research-fanout-3=0
EXIT=research-fanout=1
EXIT=research-manifest-verify=0
EXIT=ruff-check-1=0
EXIT=ruff-fix=1
EXIT=ruff-format-check=0
EXIT=ruff-format-write=0
EXIT=token-audit=0
EXIT=ty-1=0
EXIT=ty-final=0
```
