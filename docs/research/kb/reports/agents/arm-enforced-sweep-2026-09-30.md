# Arm test of the enforced sweep stages: does `mise skills sync` link skills for Claude Code?

Date: 2026-09-30. Synthesize node: opus / high. Question: *Does `mise skills sync` link skills
for Claude Code?*

## Answer

**Yes, and it is shipped code, not only a proposal.** `mise skills sync` writes one symlink per skill
into a directory. By default that directory is the `skills.dir` setting, `.claude/skills`, under the
project root (the directory of the nearest mise config). `-g/--global` links into `~/.claude/skills`
instead. Both are Claude Code's project and personal skill locations. The skills come only from
tools that were installed with the `packslip:` backend and that declare a skill in their packslip.
Any other tool contributes nothing.

Three separate claims support this answer:

1. **What mise ships.** The feature landed in mise **v2026.9.2** (2026-09-07) via #12779/#12780, and the
   release notes say so. On this Mac, the installed binary (**mise 2026.9.18**) prints the same
   `--help` text as the docs page. Its default is `.claude/skills` and its `-g` flag targets
   `~/.claude/skills`. Probe: `mise skills sync --help` returned rc=0. As a control, the same command
   with a bogus subcommand returned rc=2, so the probe can tell a real subcommand from a missing one.
2. **What mise's docs and PRs describe or recommend.** `skills.auto_sync` (off by default) and
   `skills.prune` are settings. PR #13275 added a one-time hint because skills were "easy to miss
   entirely". A `.agents/skills` directory is suggested for agents that look there.
3. **What a third party (Claude Code) documents.** A project or personal `<skill-name>` entry "can be
   a symlink to a directory elsewhere on disk. Claude Code reads `SKILL.md` from the target"
   (`$CC/skills.md:129`). This is why a symlink-based sync actually loads in Claude Code. mise's own
   pages do not assert it.

**The sweep is INCOMPLETE on one axis.** The code-search stage's must-hit control
(`filename:skills.rs repo:jdx/mise`) returned 0. So the code search is **not shown to discriminate**,
and its 39 hits for `skills sync` are unverified as code evidence. The answer above does not rest on
code search. It rests on the release notes, the docs mirror and the live `--help` probe of the
installed binary.

## Evidence

| Claim | Source | Quote |
|---|---|---|
| sync links the active tools' skills where an agent looks (ships) | https://mise.jdx.dev/cli/skills/sync.html (mirror `docs/research/kb/raw/arm-enforced-sweep-2026-09-30/links/1.md`, read in full) | "Link the active tools' skills where an agent looks for them" |
| default DIR is `.claude/skills` under the project root | same page; also the live `mise skills sync --help` (mise 2026.9.18, rc=0) | "Writes one symlink per skill into DIR … DIR defaults to the `skills.dir` setting, `.claude/skills`, under the project root: the directory of the nearest mise config." |
| `-g` targets Claude Code's user-level dir | same page and the live `--help` | "**`-g --global`** — Link into ~/.claude/skills instead of the project's directory" |
| only mise-made links are replaced or pruned | same page | "Only links mise made, which point into its installs directory, are ever replaced or, with --prune or the `skills.prune` setting, removed. A real directory or a link of your own at a skill's name is left alone and reported." |
| shipped in a release (the SHIPS claim) | https://github.com/jdx/mise/releases/tag/v2026.9.2 (`.agent/kb/raw/research-fanout/mise-skills-sync-claude/github-releases.raw`) | "`mise skills ls` / `mise skills sync` link a tool's Agent Skills into `.claude/skills` at the pinned version. ([#12779] … [#12780] …)" |
| design PR (states the intent) | https://github.com/jdx/mise/pull/12780 (`…/mise-skills-sync-claude/github-issues.raw`) | "`mise skills sync` writes one symlink per skill into the project's `.claude/skills` (`--dir` for another agent's location, `--global` for `~/.claude/skills`)" |
| PR test coverage (the PR's own checklist, not re-run here) | https://github.com/jdx/mise/pull/12780 | "Unit tests: skill discovery per source and sync semantics: link, unchanged, version switch, foreign directory and link left alone, duplicate name skipped, prune of a stale mise-made link" |
| skills come only from `packslip:` tools | https://mise.jdx.dev/cli/skills.html (quoted in the input claims; **not mirrored**, see Gaps) | "A tool installed with the `packslip:` backend may declare an agent skill: a directory holding `SKILL.md` …" |
| `auto_sync` and a custom dir (docs recommendation) | https://mise.jdx.dev/dev-tools/packslip-resources.html (quoted in the input claims; **not mirrored**) | "`[settings.skills] dir = \".agents/skills\" auto_sync = true prune = true`" |
| `auto_sync` off by default; a hint was added | https://github.com/jdx/mise/pull/13275 | "`skills.auto_sync` is `false` by default, so installing a tool that ships a skill fetched it and then said nothing." |
| Claude Code follows symlinked skill dirs (third party) | `~/dev/github/ray-manaloto/knowledge-base/sources/agent-harness-docs/docs/claude-code/skills.md:129` | "a `<skill-name>` entry in the enterprise, personal, or project location can be a symlink to a directory elsewhere on disk. Claude Code reads `SKILL.md` from the target" |

### Code search

| query | role | count | rc |
|---|---|---|---|
| `skills sync repo:jdx/mise` | query | 39 | 0 |
| `filename:skills.rs repo:jdx/mise` | must-hit | 0 | 0 |
| `zzvqkw9314xpl repo:jdx/mise` | known-absent | 0 | 0 |

The known-absent arm correctly returned 0. The must-hit arm also returned 0. A search that cannot
find a file it must find has not shown it can say "yes", so its 39 hits are **not** used as evidence.
The docs page names the file as `src/cli/skills/sync.rs`, not `skills.rs`. So the must-hit query
itself may simply be wrong (a TOKEN-SPELLING bound, per `probes-need-a-control-arm.md` rule 3). This
is inferred, not verified.

### Dependency-repo fan-out

| repo | query | rc | manifest |
|---|---|---|---|
| jdx/mise | mise skills sync Claude Code | 0 | `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.agent/kb/raw/research-fanout/arm-enforced-sweep-2026-09-30/deps/jdx--mise/1/manifest.json` (issues ok 10; discussions ok 1; releases empty_verified 0, control count 1) |
| jdx/mise | packslip | 0 | `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.agent/kb/raw/research-fanout/arm-enforced-sweep-2026-09-30/deps/jdx--mise/2/manifest.json` (issues ok 10; discussions ok 10; releases ok 10) |
| jdx/packslip | mise | 0 | `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.agent/kb/raw/research-fanout/arm-enforced-sweep-2026-09-30/deps/jdx--packslip/1/manifest.json` (issues ok 10; **discussions empty_unverified 0, control count 0**; releases ok 5) |

The primary run manifest was also read:
`/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.agent/kb/raw/research-fanout/mise-skills-sync-claude/manifest.json`
(issues ok 10; releases ok 1, which is v2026.9.2; exa ok 10).

### Offline mirrors

| link | mirror file | rc | bytes | failure |
|---|---|---|---|---|
| https://mise.jdx.dev/cli/skills/sync.html | `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles.worktrees/research-enforcement-20260930/docs/research/kb/raw/arm-enforced-sweep-2026-09-30/links/1.md` | 0 | 2321 | (none) |

The caller link (https://mise.jdx.dev/cli/skills/sync.html) is **cited and was read in full** from
this mirror.

## Conflicts resolved

- **Docs page vs installed binary.** No conflict. The mirrored page and `mise skills sync --help` on
  mise 2026.9.18 match word for word on the default DIR, `-g`, `--dir` and `--prune`. The live binary
  is trusted as the primary source for the SHIPS claim, and the page corroborates it.
- **PR #12780 (merged state unknown from the manifest) vs the release notes.** The manifest items for
  #12780 carry no `merged`/`state` field, so the PR alone cannot prove the feature shipped. The
  v2026.9.2 release notes list #12780 as shipped, and the local binary has the subcommand, so both of
  those win. The PR is used only as a statement of intent and of test scope.
- **"Designed specifically for Claude Code" (an input claim) vs `--dir`.** This is an overstatement.
  The defaults target Claude Code's directories, but `--dir` and `skills.dir` exist for other agents'
  locations, and the docs suggest `.agents/skills`. So it is Claude-Code-*defaulted*, not
  Claude-Code-*only*.
- **"Comprehensive test coverage" (an input claim).** This rests only on the PR's own checklist, which
  is not re-run here. It is reported as the PR's claim, not as a measurement.

## Verification

All stages ran (critic, adjudicator and reconcile did not fail; FAILED STAGES: none). One load-bearing
claim was refuted-tested. No UPHELD refuted or misleading verdicts, so nothing in the Answer or
Recommendation was struck or qualified, and the conclusion does not change. It stays "yes, shipped",
with the sweep INCOMPLETE on the code-search axis.

| Claim | Status | Evidence |
|---|---|---|
| `mise skills sync` (v2026.9.2, #12780) writes one symlink per skill into `skills.dir` (default `.claude/skills` under the project root; `-g` = `~/.claude/skills`); installed 2026.9.18 `--help` rc=0, bogus subcommand rc=2 | **Confirmed. Refuter's "misleading" verdict overturned by the adjudicator.** | The refuter re-ran both probes (help rc=0, `mise skills bogusxyz` rc=2) and found the #12780 line in the v2026.9.2 release body. It argued the claim omitted that skills come only from `packslip:` tools, that links point into the installs dir, that foreign dirs and links are left alone (prune needs `--prune`/`skills.prune`), and that `skills.auto_sync` exists. The adjudicator re-ran both probes (rc=0 with "one symlink per skill"; rc=2) and showed the report's Answer and Evidence already state every one of those points. The refuter also reported the mirror `links/1.md` missing. That was a wrong-checkout probe: the file exists in the research-enforcement-20260930 worktree (2321 bytes), confirmed by a second route (`ls` plus grep of the prune, auto_sync and "left alone" lines). |
| Mirror path `links/1.md` exists | **Confirmed** (refuter's absence result was aimed at the main checkout) | See above. |
| Claude Code follows symlinked skill dirs | Unverified end to end | Cited from the local KB mirror line 129 only; see Gaps 7 and 8. |
| Skills come only from `packslip:` tools; `auto_sync` docs quote | Unverified (inherited) | `/cli/skills.html` and `packslip-resources.html` not mirrored; see Gap 3. |
| Code-search hits (39) | Unverified, not used as evidence | Must-hit control returned 0. |

## Gaps

1. **MANDATORY GAP: the code search is not shown to discriminate.** The must-hit control
   (`filename:skills.rs`) returned 0, so `sync.rs` was never confirmed through code search, and none
   of the 39 query hits count as evidence.
2. **`jdx--packslip/1` github-discussions returned `empty_unverified`, and its control arm also
   returned 0.** Whether jdx/packslip discussions mention mise skills is **unknown**. This is not
   "nothing found".
3. **The mise `/cli/skills.html` and `/dev-tools/packslip-resources.html` pages were not mirrored.**
   Their quotes arrive only through the input claims (inherited, not re-read here).
4. **The end-to-end effect was not measured.** No `packslip:` tool that declares a skill was installed
   and synced here, so this report does not show a symlink appearing in `.claude/skills` or Claude
   Code listing it. Only the `--help` surface was probed. It is also unmeasured whether any tool this
   repo pins uses the `packslip:` backend with a declared skill. Per the docs and #13780, the
   registry has only just started switching tools such as timoni and worktrunk.
5. **Mirror gaps: none.** The one link mirrored with rc=0 and 2321 bytes. **Failed reads: none.**
6. Triage hits #11289, #13267, #13269, #13712, packslip#139, vaayne/agent-kit and
   komune-io/mise-claude were listed but not read in full. They are named here as unread. (Critic
   adds #13780 and #13597 to the unread list; next probe: read each in full with `gh issue view` or
   `gh pr view`, focusing on bugs, limitations and Claude Code specifics, and skim the two third-party
   repos for how they link skills.)

Critic gaps (appended; each with its next probe):

7. **Claude Code loading of the links was never measured end to end.** Only `--help` and Claude Code
   docs saying symlinked skill dirs are followed. No symlink was created in `.claude/skills` and
   Claude Code was never shown listing the skill. Next probe: install a `packslip:` tool that
   declares a skill into a scratch project, run `mise skills sync --dir <scratch>/.claude/skills`,
   confirm the symlink, start `claude` there and check `/skills`; use a no-skill tool as the negative arm.
8. **Claude Code symlink-following is cited only from a local KB mirror**, with no freshness or version
   check, and no confirmation that project-level `.claude/skills` symlinks behave like personal ones in
   the installed version. Next probe: fetch https://code.claude.com/docs/en/skills live and compare to
   mirrored line 129, confirm `claude --version`, test a symlinked skill in a scratch project.
9. **Skills-only-from-`packslip:` rests on un-mirrored pages** (Gap 3). Next probe: mirror
   https://mise.jdx.dev/cli/skills.html and https://mise.jdx.dev/dev-tools/packslip-resources.html, and
   read `src/cli/skills/sync.rs` plus the skill-discovery source in jdx/mise at tag v2026.9.2 to confirm
   only packslip-backend tools are discovered.
10. **Shipped vs proposed vs documented-by-others is not cleanly separated.** PR #12780's merged state is
    unknown, the release-notes claim rests on a raw manifest rather than the release page, and the
    2026.9.18 binary's inclusion of the feature rests on `--help` alone. Next probe: `gh pr view 12780
    --json state,mergedAt,mergeCommit`, fetch the v2026.9.2 release body directly, `git tag --contains`
    on the merge commit, and run `mise skills ls` / `mise skills sync --dry-run` (if available) as a
    behavioral rather than help probe.
11. **The code-search must-hit failure was never re-run**; the wrong-filename cause is inferred only.
    Next probe: `path:src/cli/skills/sync.rs repo:jdx/mise` as the must-hit, alongside the original
    query, to see which token spelling the search needs.
12. **The jdx/packslip discussions fan-out was `empty_unverified`** (control also 0), and packslip's own
    skill-declaration docs and packslip#139 were never read. Next probe: query packslip discussions with
    a known-present term as control, read the packslip README and skill-declaration docs or schema, and
    read packslip#139.
13. **Whether this repo pins any `packslip:` tool with a declared skill, and whether `auto_sync` would
    dirty the tracked `.claude/skills` tree, is unmeasured.** Next probe: `mise skills ls` in the repo,
    grep the mise config for `packslip:`, run `mise skills sync --dir <scratch>` and check `git status`.

## Recommendation

Treat `mise skills sync` as the native mechanism for putting version-pinned tool skills into
`.claude/skills`. Per `tool-currency-and-native-first.md`, do not hand-roll a symlinker. Before
relying on it in this repo, close gap 4. Run `mise skills ls` in the repo and check whether any pinned
tool declares a skill at all. If one does, run a scoped `mise skills sync --dir <scratch>` as the
positive arm, with a tool that declares no skill as the negative arm. Also decide deliberately
whether `skills.auto_sync` belongs in `mise.toml`. It writes into `.claude/skills`, which is a
tracked tree here, so any symlinks it creates would appear in `git status`. Re-run the code-search
stage with a must-hit that exists (`path:src/cli/skills/sync.rs repo:jdx/mise`) to fix the sweep's
control arm.

## Provenance

| node | agentType | model | effort |
|---|---|---|---|
| plan+fetch | general-purpose | sonnet | medium |
| deps:jdx/mise | general-purpose | sonnet | low |
| deps:jdx/packslip | general-purpose | sonnet | low |
| mirror:1/1 | general-purpose | haiku | (default) |
| triage | Explore | sonnet | low |
| mirror-index | general-purpose | haiku | (default) |
| read-link:1 | Explore | sonnet | low |
| read:1/1 | Explore | haiku | (default) |
| synthesize | general-purpose | opus | high |
| refute:1/1 | general-purpose | sonnet | medium |
| critic | Explore | sonnet | medium |
| adjudicate | general-purpose | opus | high |
| reconcile | general-purpose | sonnet | medium |

## GitHub repos touched

- [jdx/mise](https://github.com/jdx/mise) — `skills sync` docs, PRs #12780/#13275/#13780/#13597, release v2026.9.2, code search
- [jdx/packslip](https://github.com/jdx/packslip) — dependency fan-out (issues, releases; discussions unverified-empty)
- [vaayne/agent-kit](https://github.com/vaayne/agent-kit) — exa triage hit, not read
- [komune-io/mise-claude](https://github.com/komune-io/mise-claude) — exa triage hit, not read
