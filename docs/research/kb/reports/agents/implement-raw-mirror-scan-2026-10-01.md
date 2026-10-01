# implement-raw-mirror-scan — 2026-10-01

Implementer lane for spec `spec-raw-mirror-scan.md` (scratchpad), branch `fix/raw-mirror-scan-exemptions`
at `3a861923`. Written incrementally. No credential-shaped literal is reproduced here; judged values are
named by role (minisign public key, Algolia DocSearch search-only key, etc.).

## Premise re-checks

| # | Result | Evidence |
|---|---|---|
| P3 | CONFIRMED | `grep -c` minisign-key prefix in `mise-cookbook_docker.md` → 1; `grep -c my_password environments.md` → 1 |
| P4 | CONFIRMED | both scripts end in `grep -v '^\.claude/'` over `git ls-files` |
| P5 | CONFIRMED | `bash_budget.py:82-87` — pairs 45, stub 57; `wc -l` → 45 / 57 (at budget, zero headroom) |
| P6 | gitleaks 8.30.1 + betterleaks 1.9.0 on host PATH (mise installs) | `which -a`, `version` |

## Progress

- Edited `scripts/check-claude-md-stub.sh` / `scripts/check-claude-agents-md-pairs.sh` in place: grep widened to
  `grep -v -E '^(\.claude|docs/research/kb/raw)/'`; header comments rewritten in place. `wc -l` → 57 / 45 (unchanged, at budget).
- `hk.pkl` step comments for `claude_md_import_stub` / `claude_agents_md_pairs` name the new exemption (comments only).
- Root `AGENTS.md` is 11,937 bytes (63 under agnix's 12,000 cap) — exemption note placed in `.claude/CLAUDE.md` instead.
- `.gitleaks.toml`: entries 1-4 + P1 trap header added; the two path-anchored 2026-09-29b mise entries deleted; Omarchy and all older entries kept.
- Tracked-tree scans after deletion: `betterleaks dir --redact --no-banner -c .gitleaks.toml docs/research/kb` rc=0 (25.36 MB);
  `… docs/research/runs` rc=0; `gitleaks dir --redact -c .gitleaks.toml .` rc=0 (44.52 MB).
- Control arm for "entries 2/4 replace the deleted entries": scratch config with entries 2 AND 4 removed →
  betterleaks kb rc=1, 2 findings: `generic-api-key` in `mise-dotfiles-2026-09-29/mise-docs/mise-cookbook_docker.md`,
  `generic-password` in `…/mise-docs/environments.md`. So the new entries are what keeps those two files green.
- Scanning `.gitleaks.toml` itself: both scanners report "scanned ~0 bytes" (the config path is skipped by the default
  allowlist), so the regex-form judged values in it cannot trip the hk scanner steps.
- Held scratch copy (8 files laid out under `<scratch>/held/docs/research/kb/raw/…`; `link-4.md` placed at
  `docs/research/kb/raw/cbm-link4/link-4.md`): NEW config → gitleaks rc=0, betterleaks rc=0. HEAD config (control) →
  gitleaks rc=1 (4 generic-api-key + **40** sourcegraph-access-token, all in link-4.md — P2 said 39; inherited 39 vs
  re-derived 40, 33 distinct lines), betterleaks rc=1 (generic-api-key ×4: vitepress config, showreel ×2, docker cookbook;
  generic-password ×1: environments/index.md) — matches P2 for betterleaks.
- Planted `github-pat` (built at runtime, scratch only) in the held mirror tree → gitleaks rc=1, betterleaks rc=1,
  both `github-pat` in the planted file. Planted file deleted.
- Stub/pairs arm with the packslip `AGENTS.md`+`CLAUDE.md` staged at their intended repo path:
  fixed → stub rc=0, pairs rc=0. Fix reverted in place → stub rc=1 (`…/repo-v1.4.0/CLAUDE.md: not a thin @AGENTS.md
  import stub`); pairs rc=0 with BOTH staged (a complete pair satisfies the pair check either way), so the pairs arm was
  re-run with only `AGENTS.md` staged → reverted rc=1 (`missing sibling …/CLAUDE.md`), fixed rc=0. Fix restored by copy.

## §B gate enumeration

| Gate | Reads raw-mirror AGENTS/CLAUDE? | On the real packslip mirror | Evidence |
|---|---|---|---|
| `claude_md_import_stub` | yes (`git ls-files`) | FAILED before fix; rc=0 after | arm above |
| `claude_agents_md_pairs` | yes (`git ls-files`) | passes with the pair; an AGENTS-only mirror FAILED before fix; rc=0 after | arm above |
| `doc_refs` (`dotfiles-setup check-doc-refs`, pathspec `**/AGENTS.md`) | **YES** | rc=0 (mirror has no path-shaped backtick refs) | armed: appending one bogus `` `scripts/<nonexistent>.sh` `` ref to the staged mirror AGENTS.md → rc=1 naming the mirror file |
| `md_size_budget` (`kb-setup md-budget`, `git ls-files`, class `agents_root` 200 lines / 24 KB) | **YES** | rc=0 (71 lines); "unimported AGENTS.md" bytes moved 40712→40748 when the mirror grew by 36 bytes | armed: +200 filler lines → rc=1 `…/repo-v1.4.0/AGENTS.md: 271 lines (file) > 200 for class 'agents_root'` |
| agnix (`mise run lint-docs`, `agnix . --strict`) | no — `.agnix.toml` excludes `docs/research/kb/**` | rc=0 | `.agnix.toml` exclude list |

## Machine check — `tests/test_gitleaks_raw_mirror_allowlist.py` (gitleaks only; betterleaks is host-only)

Six tests: control arm (defaults-only config flags the fixture: sourcegraph-access-token + generic-api-key ×3), judged FPs
→ rc=0 / 0 findings, planted PAT in mirror → rc=1 `github-pat` only, planted PAT in a showreel capture → rc=1,
commit-URL SHA outside `docs/research/kb/raw/` → rc=1 `sourcegraph-access-token`, and a structural check that no
`[[allowlists]]` entry has `paths` + `regexes` without `targetRules` (the P1 trap). 6 passed.

The control arm caught a dead first fixture: gitleaks' `sourcegraph-access-token` has `keywords = ["sgp_", "sourcegraph"]`,
so a bare 40-hex commit URL does NOT fire unless the file also says "sourcegraph" (link-4.md does). The fixture now carries
that keyword line. Test file scanned clean by gitleaks rc=0 and betterleaks rc=0 (scratch copy); an earlier draft tripped
betterleaks `generic-password` on a `PASSWORD = "my…` source fragment and was re-split.

### Mutation table (in place on `.gitleaks.toml`; restored by copy, `cmp` against the pre-mutation backup after each)

| Mutation | Result | Which tests went RED |
|---|---|---|
| drop `targetRules` from entry 1 (commit SHA, path `docs/research/kb/raw/`) | pytest rc=1, 3 failed | planted-in-mirror, planted-in-capture, structural — **P1 confirmed: the planted PAT went unreported** |
| drop `targetRules` from entry 2 (judged values, path `docs/research/kb/raw/`) | pytest rc=1, 3 failed | same three |
| drop `targetRules` from entry 3 (showreel captures path) | pytest rc=1, 2 failed | planted-in-capture, structural (planted-in-mirror stays green: the blind spot is captures-only) |
| delete entry 4 (`my_password`) | gitleaks pytest rc=0 (gitleaks has no `generic-password`); **betterleaks arm** on the FP tree rc=1, `generic-password …/environments.md` | betterleaks only, as expected |

### betterleaks arm (same four fixture cases, trees built from the test's own helpers in scratch)

| Case | rc | Findings |
|---|---|---|
| judged FPs | 0 | none |
| + planted PAT in mirror | 1 | `github-pat …/planted.md` |
| + planted PAT in showreel capture | 1 | `github-pat …/captures/x.json` |
| commit SHA outside raw | 0 | N/A — betterleaks 1.9.0 has no 40-hex sourcegraph rule (defaults-only control on the same tree: no sourcegraph finding, 4 others) |
| full `mise run gate -- run lint` with the packslip pair staged | ran `claude_md_import_stub`, `claude_agents_md_pairs`, `doc_refs`, `md_size_budget`, `betterleaks_verbatim_trees`, `gitleaks` — all ✔ | rc=0 | `.agent/gate-results/lint.log` (`✔` line for each step) |
| `mise run gate -- run verify` with the pair staged | suites.toml contracts | rc=0, 166 passed / 0 failed / 4 skipped (pre-existing human-only `policy.*` skips) | gate json |
| `mise run gate -- run pytest` with the pair staged | test suite | rc=0 | gate json |
| `mise run gate -- run lint-docs` with the pair staged | agnix | rc=0 | gate json |
| `pr.py` `_DOCS_PATTERNS` (`**/AGENTS.md`, `**/CLAUDE.md`) | path-match only — a mirror change makes `ship` require lint-docs; it does not read content | n/a | `python/src/dotfiles_setup/pr.py:181-189` |

### Arm commands for the two latent readers (pair staged at `docs/research/kb/raw/mise-packslip-docs-2026-09-30/packslip/repo-v1.4.0/`)

```bash
D=docs/research/kb/raw/mise-packslip-docs-2026-09-30/packslip/repo-v1.4.0
# doc_refs — verbatim mirror: rc=0; then the positive arm:
printf '\nSee `scripts/no-such-file-kq7.sh`.\n' >> $D/AGENTS.md; git add $D/AGENTS.md
uv run --project python dotfiles-setup check-doc-refs        # rc=1
#   …/repo-v1.4.0/AGENTS.md:71: unresolved path ref `scripts/no-such-file-kq7.sh`
# md_size_budget — verbatim mirror (71 lines): rc=0; then the positive arm:
for i in $(seq 1 200); do echo "filler line $i"; done >> $D/AGENTS.md; git add $D/AGENTS.md
uv run --project python kb-setup md-budget                   # rc=1
#   …/repo-v1.4.0/AGENTS.md: 271 lines (file) > 200 for class 'agents_root'
cp .agent/kb/raw/held-2026-09-30/$D/AGENTS.md $D/AGENTS.md   # restored; cmp → identical
```

Both latent readers are ticketed by the architect (doc_refs in dotfiles, md-budget in `kb_setup`).

### The 40-hit re-derivation (P2 said 39)

```bash
git show HEAD:.gitleaks.toml > <scratch>/head.toml    # HEAD = 3a861923
cd <scratch>/held && gitleaks dir --redact --no-banner -c <scratch>/head.toml -f json -r held-gl-head.json .   # rc=1
jq -r '.[].RuleID' held-gl-head.json | sort | uniq -c        # 4 generic-api-key, 40 sourcegraph-access-token
jq -r '.[]|select(.RuleID=="sourcegraph-access-token")|.StartLine' held-gl-head.json | sort -n | uniq | wc -l   # 33
```

All 40 are in `link-4.md` (placed at `docs/research/kb/raw/cbm-link4/link-4.md`), and the new config clears them (rc=0).

**Verdict:** no gate other than stub/pairs FAILS on the real vendored packslip `AGENTS.md`/`CLAUDE.md`. Two other gates
(`doc_refs`, `md_size_budget`) DO read raw-mirror instruction files and would fail on a different mirror (one with
unresolvable path-shaped backtick refs, or an `AGENTS.md` over 200 lines / 24 KB). Not widened: both are python
(`doc_refs.py` in `python/src/**`, `md_budget.py` in the knowledge-base's `kb_setup`), outside this spec's allowlist. Flagged
to the architect as a latent follow-up.

The pair was then `git rm --cached` + deleted; `git status` shows neither file before the commit.

## Final verification (tracked tree as committed, pair removed)

| Command | rc | Summary |
|---|---|---|
| `mise run gate -- run lint` | 0 | passed, 17.1 s |
| `mise run gate -- run pytest` | 0 | passed, 319 s |
| `mise run gate -- run verify` | 0 | 166 passed, 0 failed, 4 skipped (pre-existing human-only policies) |
| `mise run gate -- run lint-docs` | 0 | passed |
| `mise run rule-sync` (`.claude/CLAUDE.md` changed) | 0 | `OK rule-sync: 1 plugin(s) + 1 line(s) + 22 rule(s) + 2 agent(s)` |
| `KB_REPO_PATH=~/dev/github/ray-manaloto/knowledge-base mise run rule-sync` | 0 | same `OK` line; no gated drift (only the advisory divergence block, which blocks nothing) |
| `betterleaks dir --redact --no-banner -c .gitleaks.toml docs/research/kb` | 0 | no leaks, after deleting the two 09-29b entries |
| `betterleaks dir --redact --no-banner -c .gitleaks.toml docs/research/runs` | 0 | no leaks |
| `uv run --project python pytest tests/test_gitleaks_raw_mirror_allowlist.py -q` | 0 | 6 passed |
| `ruff check` / `ruff format --check` / `ty check` on the new test | 0 / 0 / 0 | clean |

## Dissent / notes

1. **Latent readers (§B).** `doc_refs` and `md_size_budget` read `docs/research/kb/raw/**/AGENTS.md`. They pass on the
   held mirror today, but the next vendored repo with a long `AGENTS.md` or with backtick file paths will fail them.
   One shared carve-out (for example, a `docs/research/kb/raw/` prefix in both exclude lists) belongs to a follow-up spec.
   `md_budget.DEFAULT_EXCLUDED_PREFIXES` is a knowledge-base engine constant shared by both repos, so a dotfiles-only fix
   would go through `check(exclude=...)`.
2. **Runtime effect not gated:** a non-stub vendored `CLAUDE.md` under `docs/research/kb/raw/` is a real nested memory
   file. Claude Code loads it lazily when it reads files in that directory (md-budget classifies it `nested`). The exemption
   keeps the gates quiet. It does not stop that load. This bears on #1472's destination question.
3. **P2 count:** inherited "39 sourcegraph-access-token"; re-derived 40 findings on 33 distinct lines (gitleaks 8.30.1,
   HEAD config, held link-4.md). All are cleared by entry 1.
4. Entry 1's rule only fires when the file also contains `sourcegraph` or `sgp_` (rule `keywords`). That explains why
   link-4.md trips it and most mirrors do not.

## GitHub repos touched

- [gitleaks/gitleaks](https://github.com/gitleaks/gitleaks) — read v8.30.1 `config/gitleaks.toml` for the `sourcegraph-access-token` rule's regex, entropy and keywords
