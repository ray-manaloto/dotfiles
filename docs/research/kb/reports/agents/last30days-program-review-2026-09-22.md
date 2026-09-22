# last30days program review, items a-e (2026-09-22)

> Persisted verbatim at receipt by the coordinator (session 2026-09-22d), from the
> delegate's final message. Header line: "🌐 last30days v3.25.0 · synced 2026-09-22".

**Method.** I used the last30days plugin only. It ran 12 times, all rc=0, over 2026-08-23..2026-09-22:
- **Round 1:** five broad topics, each with a `--plan` and `--github-repo`.
- **Round 2:** seven narrow topics restricted to `--search=github,x,reddit,hackernews`, including a control topic ("Plugin4Shell").

I did not use host WebSearch, because the brief said last30days only. So the skill's Step 0.55 lookup of handles and subreddits came from my own knowledge, not from searches.

Raw evidence is in `/private/tmp/claude-501/-Users-rmanaloto-dev-github-ray-manaloto-dotfiles/b72c95e0-c9b0-4405-9c38-6bd9885f2f71/scratchpad/l30/` (`out1-5.md`, `r2A-G.md`, `save/`, `save2/`). A short summary is appended to `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/findings.md`.

**Control arms.** Every "not found" below was checked with a term I knew was present, searched the same way in the same file. The Plugin4Shell control run returned 12 HN, 4 X and 1 GitHub item, so the narrow-topic setup can return results.

## a. knowledge-base graphify corpus: no change (unverified on release content)

- **Repo counts.** Graphify-Labs/graphify has 120,495 stars and 1,459 open issues as of 2026-09-20 ([repo](https://github.com/Graphify-Labs/graphify)).
- **No release notes or issue lists.** The GitHub lane returned only the repo summary. So I have **no community evidence about 0.9.57 to 0.9.65 changes**. Existing `graphify-features-2026-09-22.md` stays authoritative for that.
- **Pitfalls people reported:**
  - [u/spf13](https://reddit.com/r/LovingOpenSourceAI/comments/1w6ag0o/comment/p7m8eoh/) (16 upvotes, 2026-09-03): "Used it a lot. Found it to be very cumbersome to use. Constantly out of date. Complicated to setup and maintain." They switched to colbymchenry/codegraph.
  - [u/sanctityforreal](https://reddit.com/r/LovingOpenSourceAI/comments/1w6ag0o/comment/p7lmzfz/) (10 upvotes): "this doesn't meaningfully reduce token usage".
  - [@3lsh916](https://x.com/3lsh916/status/2100179463862362496) (2026-09-16) asked whether the graph updates incrementally or needs a full re-index. No answer was captured.
  - "Constantly out of date" matches this repo's own history with stale graphs.
- **Possible replacements.** Both are alternatives, not drop-in replacements for the KB committed-corpus pipeline. Neither is evaluated.
  - [codegraph](https://x.com/RubanBhatia/status/2101306641585213761) (2026-09-19): described as "more purpose-built for engineers: call paths, dependencies".
  - [graf](https://github.com/ctxrs/graf) (Show HN 2026-09-22, 3 pts): claims to be a "1000x faster graphify in Rust".
- **Adjacent:** [graphify-csharp](https://github.com/zachsaw/graphify-csharp) (Show HN 2026-09-12, 46 pts).

## b. Codex currency: changes the codex-doctor design

- **The daemon now has its own update lifecycle.** Community posts back up what `codex-daemon-history-2026-09-22.md` already found:
  - [@abugiza_](https://x.com/abugiza_/status/2099737730154430868) (2026-09-15): a pre-release `codex app-server daemon update --from-cli` "can replace and pin the daemon from the invoking CLI package, including downgrades and local builds… migrates legacy daemon installs into a dedicated package directory". Status: in development.
  - [@CodexReleases](https://x.com/CodexReleases/status/2100746656925061487) (2026-09-18): "Daemon update schedules are configurable via codex app-server daemon update; saved threads and active goals recover after daemon restarts."
  - [@CodexChanges](https://x.com/CodexChanges/status/2100746509947994207) (2026-09-18): "Preserve standalone release pins during daemon updates" and "Ensure the standalone updater runs on managed daemon starts".
- **Change X (repo rule: use the tool's built-in first).** Codex's standalone install now ships its own updater, update schedule and pin handling. A custom codex-doctor that reports "behind latest" and blocks lanes would partly duplicate that. Before building it:
  - check whether `codex app-server daemon update` (schedule and pin) covers "bring to latest";
  - limit the doctor to reporting and gating on a floor version.
  - The pin-preservation behaviour also means the repo-recorded synced version should match the version the standalone updater has pinned, not fight it.
- **Security floors the doctor should enforce:**
  - Plugin4Shell is a zero-click RCE: a git branch named like a commit SHA defeats plugin SHA pins, and background auto-update makes it no-click. It is fixed in **Codex 0.146.0** and **Claude Code 2.1.179** ([air.security](https://www.air.security/blog-posts/plugin4shell), HN 2026-09-17; [@AIPulsePoint](https://x.com/AIPulsePoint/status/2102413761269358998)).
  - Sandbox escapes Overpatch and Heapjack are reportedly fixed in **Codex CLI 0.149.0** and **Desktop build 26.818.21641** ([@Read0nlyNet](https://x.com/Read0nlyNet/status/2102340462933594620), 2026-09-22). This is **single-source and unverified**.
- **npm is still active.** Pre-releases still ship there: [@MattHProgrammer](https://x.com/MattHProgrammer/status/2102412817840431336) (2026-09-22) used `npm install -g @openai/codex@alpha`. Moving off npm is a choice about which channel the repo tracks, not an escape from a dead channel.
- **Other pitfalls:**
  - A Codex outage issue ([#28756](https://github.com/openai/codex/issues/28756), HN 2026-09-03, 102 pts).
  - [CmdBrief](https://x.com/CMDBrief/status/2102427716175667468) (2026-09-22): "Codex's status hooks go quiet but its terminal still shows Working". A doctor or hook that infers state from hook events can misread a busy lane as idle.
- **Model rollout:** GPT-6 Sol and Luna are rolling out in Codex ([@OpenAIDevs](https://x.com/OpenAIDevs/status/2102461540075261958), 2026-09-22).

## c. planning-with-files shared plan across Claude Code and Codex: no change

- **Repo counts.** OthmanAdi/planning-with-files has 27,072 stars and 16 open issues as of 2026-09-21 ([repo](https://github.com/OthmanAdi/planning-with-files)).
- **It is recommended to Codex users as a skill:** [@lksmlabc](https://x.com/lksmlabc/status/2101764835658682560) (2026-09-20, 116 likes, 123 replies) lists it first of eight "Codex must-install" skills.
- **Nobody discusses a shared multi-vendor plan with enforced hook parity.** The pwf-codex run returned the repo and @lksmlabc (the control), and nothing on shared plans or coordinator-only plans. The "A-enforced" proposal has no community precedent, for or against.
- **Pitfall that bears on hook parity:** the CmdBrief "status hooks go quiet" report above.
- **Unverified claim:** [@3dgiordano](https://x.com/3dgiordano/status/2102127415170326659) (2026-09-21) says agent-plugins 0.9.0 runs "same hooks as Claude Code, zero changes" on Codex. If true, cross-vendor hook portability is being attempted elsewhere.
- **Background reading:** Maggie Appleton, [Planning with Agents](https://maggieappleton.com/planning-agents) (HN 2026-09-15).

## d. Wrapper skills for hidden plugin skills: no change to the approach; two leads

- **`disable-model-invocation` is widely used on purpose, to keep manual skills out of context.**
  - [@letscallsal](https://x.com/letscallsal/status/2100998735018832226) (2026-09-18): "The win is disable-model-invocation: true".
  - [@aeon_ogawa](https://x.com/aeon_ogawa/status/2100065890234724541) (Qiita, 2026-09-16).
  - [@boboga777](https://x.com/boboga777/status/2099793674100158922) (2026-09-15).
  - Matt Pocock's to-spec, to-tickets and implement skills set it deliberately. Wrapping them undoes a choice the author made on purpose.
- **Codex equivalent:** [@simonwongio](https://x.com/simonwongio/status/2097710923318518248) (2026-09-09) shows `agents/openai.yaml` → `policy: allow_implicit_invocation: false`. Their `/configure-skill-invocation` skill (`npx skills add`) edits frontmatter in place, which is the opposite direction. **No existing tool that makes plugin skills model-invocable was found.** The planned wrapper plus sync task stays custom.
- **`skillOverrides` has no community evidence either way.** It got 0 hits, while `disable-model-invocation` got 45 in the same file. Your measurement that it does not apply to plugin skills stands.
- **Lead 1 (unverified):** the [Claude Code 2.1.280 changelog](https://x.com/ClaudeCodeLog/status/2102442227033116867) (2026-09-22) says "a skill's state options in /plugin can be clicked". Per-skill state inside `/plugin` could be a native toggle that makes wrappers unnecessary. Check the offline docs (`$CC/`) before building.
- **Lead 2:** "Claude Code now reads AGENTS.md if there is no CLAUDE.md" (HN 2026-09-18, 737 pts, [changelog](https://code.claude.com/docs/en/changelog)). This is a native feature that bears on the root `CLAUDE.md` = `@AGENTS.md` stub. It is outside items a-e, but flagged under the prefer-built-ins rule.

## e. Every mise tool and uv dependency at latest, including hk 2.0: no change; one pitfall

- **Nobody discusses hk 2.0.** In that run's raw file, "hk 2.0" appears only in the query header, while "jdx/hk" has 14 hits. The X results are polluted by "HK" meaning Hong Kong, mostly BTS posts.
- **Repo counts:** jdx/hk has 1,178 stars and 16 open issues ([repo](https://github.com/jdx/hk), 2026-09-15). jdx/mise has 34,198 stars and 67 open issues.
- **Signal from the author:** [@jdxcode](https://x.com/jdxcode/status/2092600718418997303) (2026-08-26) says hk and usage "have had their adoption harmed by not choosing TOML (though I stick by those decisions)". So pkl stays; this is not evidence of a config-format switch in 2.0. A YouTube comment on the [devtools.fm interview](https://www.youtube.com/watch?v=aEkpFeJoKvk) agrees: "pkl files are hard to read".
- **Pitfall for "always latest":** [@jdxcode](https://x.com/jdxcode/status/2102469199490850979) (2026-09-22): "renovate modifies the lockfiles and each PR does another full CI run. basically i have an N² CI queue". On grouping updates, [he adds](https://x.com/jdxcode/status/2102471584938156138) "at least 1 usually fails, so if I did this I wouldn't have mergeable PRs". This repo already uses `group:all`; expect the same trade-off, where one failing bump blocks the whole group.

## Lanes that failed or returned partial results

- **Web grounding:** HTTP 422 on every run, so no web results at all.
- **TikTok and Instagram:** HTTP 402, ScrapeCreators credits exhausted (10 times each).
- **Reddit ScrapeCreators backup:** HTTP 402 (6 times).
- **Jobs:** HTTP 422.
- **ArcticShift r/ClaudeAI listing:** HTTP 422, so Reddit coverage of r/ClaudeAI is incomplete.
- **YouTube:** HTTP 429 on 2 transcripts, and ScrapeCreators transcript fallback 402.
- **GitHub project mode:** returned only a repo summary per repo, with no release or issue list ranked. That is why "no release evidence" for a, b and e is a limit of this lane, not proof that nothing was released.
- **Cross-contamination:** the engine's "From your library" block injected findings from the parallel runs that share a save directory. I ignored that block.
- **Hong Kong noise:** as above, the X results for "hk 2.0" were mostly about Hong Kong.
- **My own error:** the first launch failed with rc=2 because zsh does not word-split a flag variable. It was re-run with the flags written out.

## GitHub repos touched

- [openai/codex](https://github.com/openai/codex): item b, repo stats; outage issue #28756
- [Graphify-Labs/graphify](https://github.com/Graphify-Labs/graphify): item a, repo stats
- [OthmanAdi/planning-with-files](https://github.com/OthmanAdi/planning-with-files): item c, repo stats
- [anthropics/claude-code](https://github.com/anthropics/claude-code): item d, repo lane (147,632 stars)
- [mattpocock/skills](https://github.com/mattpocock/skills): item d, passed as a repo target (no ranked items)
- [jdx/hk](https://github.com/jdx/hk): item e, repo stats
- [jdx/mise](https://github.com/jdx/mise): item e, repo stats
- [colbymchenry/codegraph](https://github.com/colbymchenry/codegraph): item a, named alternative (not read)
- [ctxrs/graf](https://github.com/ctxrs/graf): item a, Rust alternative (HN item only)
- [zachsaw/graphify-csharp](https://github.com/zachsaw/graphify-csharp): item a, adjacent tool (HN item only)
- [SecOpsNews/news](https://github.com/SecOpsNews/news/issues/74149): Plugin4Shell control-topic hit
