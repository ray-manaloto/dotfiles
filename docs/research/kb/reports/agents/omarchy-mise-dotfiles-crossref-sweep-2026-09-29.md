# Omarchy x mise dotfiles / bootstrap: cross-reference sweep (synthesis), 2026-09-29

Synthesis lane over three `research-sweep` fan-outs (`.agent/kb/raw/research-fanout/{omarchy-mise-dotfiles,mise-dot-bootstrap-omarchy,omarchy-mise}/manifest.json`),
the 19-claim JSON plus triage list handed in by the workflow, and **fresh live probes run in this lane on 2026-09-29**. Agent: Claude Opus 5.5 (1M),
session `5545fa41`. Raw sources for this lane: `.agent/kb/raw/omarchy-mise-xref-sweep/`. It builds on, and in part corrects, two earlier reports from the
same day: `mise-dotfiles-omarchy-2026-09-29.md` (lane O) and `omarchy-mise-crossref-2026-09-29.md` (lane X).

Trigger: Ray disputed lane O's headline ("Omarchy does NOT yet use mise dotfiles or `mise bootstrap`"). He cited jdx's post
<https://jdx.dev/posts/2026-09-07-dotfiles-that-save-themselves/>, which has an "On Omarchy" section.

## Answer

**Ray is right that Omarchy and mise dotfiles are closely linked. Lane O's headline was too flat. Its narrow claim still stands.**
"Omarchy uses mise dotfiles" can mean three different things, and the evidence gives a different answer for each:

1. **Omarchy's shipped code does not call it (TRUE, re-verified live).** At `omacom/omarchy` `quattro` @ `8b4eae66` (HEAD on 2026-09-29), no shipped file
   invokes `mise dot`, `mise dotfiles`, `mise bootstrap` or `history-watch`, and none declares `[bootstrap.*]` or `[dotfiles]`. Omarchy
   uses mise only for **tools**: `use`, `x`, `up`, `settings`, `trust`, `activate` and similar commands, the `omarchy-mise-install` wrapper stubs, and a
   `[tool_alias]` in `etc/mise/conf.d/omarchy.toml`. **jdx says the same thing himself**: "mise has a second half that Omarchy is not using yet:
   `mise bootstrap`" (jdx/mise#12709). DHH's sponsor post describes mise only as a runtime and agent-CLI manager.
2. **mise supports and documents Omarchy as a target, and Omarchy users use it today (TRUE; lane O under-weighted this).** Omarchy installs
   mise by default (the `mise-bin` package is in `install/omarchy-base.packages:81`), so `mise dot` is available on every current Omarchy machine.
   mise's own docs have Omarchy-specific instructions (`bootstrap/setup.md`, `history.md`: `mise dot capture --label "omarchy update" -- omarchy-update`).
   jdx's post has an "On Omarchy" recipe. At least one Omarchy user reports syncing a desktop and a laptop with mise dotfiles, including an encrypted file
   (omacom/omarchy#11029, CaffeinatedTech, 2026-09-15).
3. **Built-in Omarchy integration is an open proposal from the mise maintainer, and Omarchy has not accepted it.** The integration means
   menus, automatic file selection and capture around updates. jdx's proposal is omacom/omarchy discussion #11029 (open, "Ideas" category), mirrored in jdx/mise#13022. The broader
   "my machine" `mise bootstrap` proposal is jdx/mise#12709. In his own words: "The mise functionality is available today; the built-in Omarchy
   experience is still a proposal." No Omarchy maintainer has replied in #11029. Omarchy also has its own competing non-mise design:
   `plans/dots.md`, a bare Git repo at `~/.local/share/omarchy/dots.git` with a manifest, plus the open PRs #12037 and #6965. Its manual still
   recommends GNU Stow.

A precise one-line restatement: **Omarchy ships mise, and mise supports an Omarchy dotfiles workflow that users run today. Omarchy's own code and
installer do not integrate `mise dot` or `mise bootstrap` yet. That integration is jdx's open proposal.**

## Evidence

| # | Claim | Source (URL or file:line) | Quote / datum |
|---|---|---|---|
| E1 | Omarchy default branch HEAD at probe time | `gh api repos/omacom/omarchy/commits/quattro` | sha `8b4eae66…`, 2026-09-29T17:44:16Z; `basecamp/omarchy` redirects to `omacom/omarchy` |
| E2 | Shipped Omarchy code has no mise dotfiles or bootstrap calls | Live `git clone --depth 1` at `8b4eae66`; `grep -rIlE 'mise (dot\|dotfiles\|bootstrap)\|history-watch\|\[dotfiles\]\|bootstrap\.services\|mise-history'` | 3 files match, and all 3 are false positives: two markdown links `[dotfiles](31-dotfiles.md)` (`manual/03-…:39`, `manual/05-…:88`) and a test mock log variable `mise_history` (`test/shell.d/default-agent-test.sh:18`, used at `:579` as `grep -Fx "use -g $muse_package"`). Controls: `omarchy-mise-install` = 18 files (the probe can find hits); a freshly invented token = 0 (the probe can miss). |
| E3 | Which mise subcommands Omarchy actually uses | Same clone, `grep -rn -E '\bmise [a-z-]+' bin install migrations default etc` | `mise use` 32, `uninstall` 19, `rm` 19, `x` 12, `up` 6, `settings` 4, `trust` 3, `activate` 3, `where`/`ls`/`exec`/`tool-alias` 2, `run` 1. No `dot`, `dotfiles` or `bootstrap`. |
| E4 | Omarchy ships mise via pacman | `install/omarchy-base.packages:81` | `mise-bin` |
| E5 | Omarchy's mise system layer today | `etc/mise/conf.d/omarchy.toml` (only file under `etc/mise/`) | `[tool_alias]` `cursor-agent = 'http:cursor-agent[...]'` |
| E6 | Omarchy manual dotfiles advice | `manual/31-dotfiles.md:3,21` | "The files that live in `/usr/share/omarchy` belong to Omarchy itself" … "it's a good idea to backup all these dotfiles. [Stow is a great way to do that]" |
| E7 | Omarchy's in-house dotfiles plan does not use mise | `plans/dots.md` (171 lines; `grep -i mise` = 0 hits) | lines 27-28: "**Stow**: inverted model requiring file migration … **chezmoi / yadm**: third-party DSLs we'd be wrapping; overkill." |
| E8 | The mise maintainer says Omarchy does not use `mise bootstrap` | <https://github.com/jdx/mise/discussions/12709> body, line 3 (raw: `.agent/kb/raw/omarchy-mise-xref-sweep/d12709.md`) | "mise has a second half that Omarchy is not using yet: `mise bootstrap`, which converges a machine to a declared state." |
| E9 | The proposal is still unpresented or unaccepted by Omarchy | jdx/mise#12709, jdx reply 2026-09-02T20:24 | "I posted this here instead of omarchy since I wanted to refine this a bit more before presenting it to them" |
| E10 | mise features ship today; the Omarchy integration is a proposal | <https://github.com/omacom/omarchy/discussions/11029> body:5 (raw `d11029.body.md`) | "**The mise functionality is available today; the built-in Omarchy experience is still a proposal.** Omarchy already ships mise." |
| E11 | Same, with the release version | #11029, jdx reply 2026-09-13T20:05:46Z | "The dotfile history and sync features shipped in 2026.9.2; what's still a proposal is the built-in Omarchy integration—menus, automatically selecting files, and capturing updates." |
| E12 | An Omarchy user uses mise dotfiles today | #11029, CaffeinatedTech 2026-09-15T13:16:43Z and 2026-09-18 | "I've just set up mise dotfiles sync between my desktop and my laptop including an encrypted file." Later: nvim config synced with mise plus mason-lock. |
| E13 | Discussion #11029 status | GraphQL, live | category Ideas, `closed=false`, 2 top-level comments (shawnyeager, CaffeinatedTech) plus jdx replies; no Omarchy maintainer comment |
| E14 | jdx post, "On Omarchy" section | <https://jdx.dev/posts/2026-09-07-dotfiles-that-save-themselves/> (live curl 200; bogus path 404; text at `.agent/kb/raw/omarchy-mise-xref-sweep/jdx-blog-2026-09-07.txt`) | "`mise dot track ~/.bashrc` `mise dot track ~/.config/hypr/bindings.conf` `mise dot track ~/.config/hypr/input.conf` Add the `history-watch` service from above and run `mise bootstrap`. It runs as a systemd user service." |
| E15 | Feature version and platform services | same post | "That's what I added to `mise bootstrap` in mise 2026.9.2." / "mise handles the LaunchAgent on macOS, systemd user service on Linux, or Scheduled Task on Windows." |
| E16 | mise docs name Omarchy | `docs/research/kb/raw/mise-dotfiles-2026-09-29/mise-docs/bootstrap_setup.md:30,333`; `history.md:386-392`; `directories.md:94`; `bootstrap_packages_pacman.md:36`. Second route, live: `gh api /search/code?q=omarchy+repo:jdx/mise+path:docs` gives the same 4 files. | history.md:391 `mise dot capture --label "omarchy update" -- omarchy-update`; setup.md:333 "On Omarchy, start with individual configuration files you edit." Controls: `history-watch` in docs = 11 files; fresh token = 0. |
| E17 | mise has no Omarchy-specific code path | inherited from lane X Q3/Q4 (not re-derived here) | the `src/` hits are sponsor text, a pacman test fixture, a swift doc comment and a history test fixture |
| E18 | jdx's Omarchy PRs are tool-only | `gh api /search/issues?q=repo:omacom/omarchy+author:jdx` | #9596 "install default CLI tools through native lazy shims" (OPEN), #12828 (test, OPEN), #8074 "Use mise registry shorthands" (closed) |
| E19 | Competing Omarchy dotfiles PRs are open and not mise-based | `gh api repos/omacom/omarchy/pulls/{12037,6965}` | #12037 (jordanhubbard) "Add explicit preference sharing with recoverable local history", open; #6965 "Add git-based backup and restore", open |
| E20 | Wrapper race: Omarchy fix closed in favour of upstream | omacom/omarchy#6964 (closed 2026-08-16T11:07, unmerged), omarchybot comment | "Closing this in favour of a fix upstream in mise. The root cause is that `mise use -g` does a read-modify-write of the global config with no lock across the two halves" |
| E21 | The upstream fix | jdx/mise#12040 (merged 2026-08-15, "write config files atomically"); jdx in discussion jdx/mise#12067, 2026-08-16T21:40 | "This is fixed on `main` by #12069 … `mise use` now takes a cross-process lock for the read-modify-write phase, re-reads the config after acquiring the lock, and holds the lock through the atomic save" |
| E22 | Dotfiles hook consolidation (CORRECTED by verification: the original "closed, `merged_at` empty" was WRONG) | jdx/mise#11436 "feat(bootstrap): consolidate dotfiles commands": `merged=true`, merged_at 2026-07-28T19:13:38Z by jdx, merge commit `1deee622`; body: hides and deprecates top-level `mise dotfiles`, warnings from 2027.2.0, removal 2028.2.0. Docs: `mise-docs/bootstrap.md:400`, `dotfiles.md:148` | Docs: "The `pre-dotfiles` and `post-dotfiles` phases also wrap `mise dot apply`." #11432 (author Jelenkee) is where jdx proposed #11436. |
| E23 | Command spelling and the sync-race fix version | #11029 body:149,153 | "`mise dot` now exposes the complete dotfiles workflow. `mise dotfiles` and the existing `mise bootstrap dotfiles` spelling work too. The short name arrived in 2026.9.8" … "2026.9.9 fixes a race that could record untouched files as deleted and propagate those deletions to another machine." |
| E24 | Container-relevant constraint named by jdx | jdx/mise#12709 body:85 | "An enable-only mode for services and firewall. The Omarchy installer runs in a chroot with no live systemd … so the same declarations can run at install time and on the installed system." |
| E25 | Omarchy's lead describes mise as a tools layer | <https://en-au.omarchy.org/news/2026/08/omacom-foundation-to-be-premier-mise-sponsor/> (DHH, 2026-08-25) | "If you've used Omarchy, you've used mise … It's what manages the language runtimes … Every major coding-agent CLI in Omarchy ships as a lazy-loading mise stub in `~/.local/bin/`." |
| E26 | Watcher without a service manager | `mise-docs/cli_dotfiles_watch.md:28,36` | "`--once` — Reconcile and synchronize once and exit (for timers and cron)" |
| E27 | Community Omarchy setup does not use mise dotfiles | `timmo001/dotfiles` (live code search) | uses `.stowrc` (`--target=~/`) plus a custom TypeScript `dot` CLI; `mise` = 100 hits (tools); `history-watch` = 0; fresh token = 0 |
| E28 | A macOS migration example | <https://titouan.dev/notes/managing-dotfiles-with-mise> (2026-07-20) | "I recently replaced the custom Homebrew shell scripts I used to bootstrap my dotfiles with mise's new dotfiles support … the same setup works on macOS and Linux servers" (does not mention Omarchy) |

## Conflicts resolved

Resolution rule: shipped source and merged PR state beat issue and discussion threads, newer beats older, and the maintainer's statement about his own
proposal beats third-party summaries.

1. **"Omarchy doesn't use mise dotfiles" (lane O) vs "the jdx post shows Omarchy + mise dotfiles" (Ray, claims 2/18).** Both are true about
   different things. I trust the shipped source (E2/E3, re-derived live with both control arms) for "Omarchy code", and jdx's own words (E8/E10/E11) for
   "integration is a proposal". I trust E12/E14/E16 for "supported and used by Omarchy users". The post is a **user recipe**. It is not evidence of Omarchy code.
2. **Claim 6: "For Omarchy on macOS … LaunchAgent".** Rejected as phrased. Omarchy is an Arch Linux distribution, and the LaunchAgent sentence (E15) describes mise
   generally. On Omarchy the watcher is a systemd user service (E14; #11029 body:66).
3. **Claim 7: "For Docker/container-based Omarchy setups … automatic config synchronization during image builds".** Rejected. The quoted text
   (`mise bootstrap --adopt …`, `history.sync sync`) is about adopting the setup on a **second machine**. No source reviewed discusses image builds
   with dotfile history, and jdx names the no-systemd case as an unsolved requirement (E24). Container guidance below is inference, labelled as such.
4. **Claim 15: "mise PR #11436 consolidates dotfiles … hides and deprecates `mise dotfiles`".** STRUCK the earlier "closed unmerged" reading: verification
   shows #11436 **was merged** (2026-07-28, commit `1deee622`). The top-level `mise dotfiles` is a hidden, deprecated compatibility alias (warnings from 2027.2.0,
   removal 2028.2.0). It still works today (E23), so `mise dot` (2026.9.8) is the preferred spelling. Claim 15 is confirmed as written.
5. **Claim 16: "#11432 shows jdx was working on …".** Partly corrected: #11432 was opened by Jelenkee (hooks did not fire on `mise dotfiles apply`), and jdx replied there.
6. **Claim 11: "`/etc/mise/config.toml` providing Omarchy defaults".** This is the proposal's premise. It is not shipped. #12709 says "as of the lazy-tools change", but that change is
   omacom/omarchy#9596, which is still **OPEN** (E18). Today `etc/mise/` holds only `conf.d/omarchy.toml` with a `[tool_alias]` (E5).
7. **Claim 17: `plans/dots.md` bare repo.** Accurate as a **plan**, and it is not mise-based (E7). Lane O noted it is absent at tag v4.0.4 (inherited, not re-run).
8. **Claims 13/14 (#6964).** Confirmed closed unmerged. The upstream fix is two changes: mise#12040 (atomic write) and #12069 (cross-process lock) (E20/E21).
9. **jdx post paths are stale against current Omarchy.** The post uses `~/.config/hypr/bindings.conf` and `~/.local/share/omarchy`. `quattro` ships
   `bindings.lua`/`input.lua`, and Omarchy's files live in `/usr/share/omarchy` (E6; `config/hypr/` listing). The newer source wins, so use the `.lua` paths.
10. **Discussion numbering.** omacom/omarchy#11029 and jdx/mise#13022 are the same proposal, posted by jdx in both repos on 2026-09-09. #12709 is
    the earlier, broader "my machine" proposal. Claims citing either are consistent.
11. **Claim 8 lists #12038 as a community request for built-in dotfiles support.** It is actually jordanhubbard's design thread "Preference sharing: a manual first slice of the
    dots plan" (0 comments), which belongs to the non-mise dots track.

## Gaps

`unverifiedEmpty` was empty and `FAILED READS` was empty for the three fan-outs. The gaps below are unknowns in this lane. None of them is a "nothing found":

- **Omarchy maintainers' position is unknown.** No DHH, ryanrhughes or omacom reply exists in #11029 (E13). Silence is not rejection, but it is not acceptance either.
  Discord, X and the Omarchy site were not searched for a maintainer response in this lane. The last30days fan-out output was not re-read here.
- **The commit for the #12882/#12904 features lane X flagged** was not identified (#11436 itself is now identified: merge commit `1deee622`). Evidence for those is the docs only.
- **#12069's first release tag** was not confirmed. jdx said "not in v2026.8.6; next release".
- **The mise version in the Omarchy package repo today** is unverified. On 2026-09-15 it was 2026.9.7 per a user, and it must be 2026.9.9 or newer for safe sync. The auto-bump
  claim ("every 24h", jdx) is unverified.
- **No real integration evidence for containers.** Nobody, including this lane, has run `history-watch`, `mise dot watch --once` or `mise bootstrap --adopt` inside a
  devcontainer. Per `.claude/rules/real-integration-evidence.md`, every container recommendation below is **unverified** until run.
- **Inherited, not re-derived here:** the v4.0.4 tag grep (lane O), and the mise `src/` hit classification (lane X Q4).
- **Omarchy `manual/` "mac-support" page** was not re-read, so any Omarchy-on-Mac-hardware angle is unknown.
- **Triage hits not read in full:** `mise.jdx.dev/cli/bootstrap.html` (covered by the local mirror), `manual/17-ai.md`, and the `omarchy.org/manual/dotfiles/` web copy
  (superseded by the repo's `manual/31-dotfiles.md`). Omarchy PRs #13470 and #11435 were checked for state only (both open, tool-wrapper and Python scope, not dotfiles).

- **Critic gaps (added after verification):**
  - Container and devcontainer behaviour was never run (`mise bootstrap --adopt`, `mise dot watch --once`, history-watch). Next probe: `mise dot track`, `watch --once`, `rollback --dry-run`, `bootstrap --adopt` in the devcontainer, with a named-volume and a bind-mounted state dir.
  - First release tag containing the #12069 lock unconfirmed. Next probe: `git tag --contains` on the #12069 merge commit, or `gh api repos/jdx/mise/compare` between v2026.8.x tags.
  - Current `mise-bin` version in the Omarchy package repo and the 24h auto-bump claim unchecked. Next probe: `pacman -Si mise-bin` on an Omarchy mirror; the omarchy-pkgs build pin.
  - Inherited probes not re-derived: v4.0.4 tag grep (`git grep -i omarchy v4.0.4`) and mise `src/` hit classification (`grep -rin omarchy src/`); E17 rests on the second.
  - Skipped reads: Omarchy `manual/` mac page, `mise.jdx.dev/cli/bootstrap.html`, `manual/17-ai.md`, web copy of the dotfiles manual; PRs #13470 and #11435 state only. Next probe: read them and diff web vs `manual/31-dotfiles.md`.
  - Cross-reference search was not exhaustive: no `gh search issues/prs --include-prs` for omarchy in jdx/mise, nor for `mise dot`/`mise bootstrap`/`history-watch` in omacom/omarchy; other people's Omarchy+mise dotfiles repos sampled once (timmo001). Next probe: those searches plus `gh search code` for `mise dot track` in shell/TOML.
  - macOS guidance rests on one post (titouan.dev, no Omarchy mention); the LaunchAgent path was not run on this Mac. Next probe: `mise bootstrap services apply` local-only, then `launchctl list`, `mise dot status`.
  - The chroot/no-systemd enable-only mode (#12709) was not checked against current mise docs or `src/`. Next probe: grep for `enable-only`, `chroot`, `--no-start`; look for an implementing PR.
  - Omarchy maintainer position unknown beyond #11029 (Discord, X, omarchy.org news unsearched; last30days output not re-read). Next probe: search those and re-query #11029 and jdx/mise#13022 for new replies.

## Verification

Refuter and critic both ran (results supplied by the workflow, 5 load-bearing claims). Probes were on 2026-09-29.

| Claim | Verdict | Evidence |
|---|---|---|
| Omarchy shipped code (quattro @ 8b4eae66) never calls `mise dot`/`dotfiles`/`bootstrap`/`history-watch`; mise used for tools only | CONFIRMED | Fresh clone; `omarchy-mise-install` matched 18 files, an invented token 0; no mise hits for the dotfiles tokens; mise calls are `use`/`x`/`settings` plus `[tool_alias]`; `mise-bin` at `install/omarchy-base.packages:81`. |
| jdx says Omarchy does not use `mise bootstrap` yet, and posted in the mise repo before presenting to Omarchy | CONFIRMED | jdx/mise#12709 body and jdx reply 2026-09-02T20:24:08Z. |
| History/sync ship today (`mise dot` 2026.9.8, race fix 2026.9.9); Omarchy integration is an open Ideas proposal with no maintainer reply | CONFIRMED | omacom/omarchy#11029 is in Ideas; body:149-153; commenters are jdx, shawnyeager, CaffeinatedTech only (not checked against a maintainer roster). jdx reply 2026-09-13 says history and sync shipped in 2026.9.2. |
| mise documents Omarchy workflows; post has "On Omarchy" recipe; an Omarchy user runs mise dotfiles sync | CONFIRMED (line numbers off, content right) | jdx/mise docs: history.md:500-504 (actual numbers differ from E16), setup.md, pacman.md, directories.md; CaffeinatedTech 2026-09-15. jdx.dev post itself not re-opened by the verifier. |
| Input claim: mise PR #11436 was closed unmerged and `mise dotfiles` not deprecated | REFUTED | `gh api repos/jdx/mise/pulls/11436`: merged=true, 2026-07-28T19:13:38Z, merge commit `1deee622`; it hides and deprecates `mise dotfiles` (warnings 2027.2.0, removal 2028.2.0). Control: PR 12692 merged=true, so the field discriminates. |
| No source shows dotfile history used in Docker image builds (Conflicts item 3) | CONFIRMED, partly (not exhaustively verified) | #12709 says the Omarchy installer runs in a chroot without live systemd and needs an enable-only mode. |

Changes made: E22 and Conflicts item 4 corrected (PR #11436 merged; `mise dotfiles` is a hidden deprecated alias, still working). The Answer and Recommendation did not depend on the refuted claim, so the conclusion is unchanged: Omarchy code does not use mise dotfiles/bootstrap; mise supports and users run it; built-in integration is an open proposal. The only practical addition is to prefer `mise dot` over `mise dotfiles` in any plan.

## Recommendation (migration techniques for this repo)

### What to take from Omarchy and jdx (sourced)

1. **Adopt mise dotfiles at the user level, the way Omarchy users do.** Do not wait for a framework integration. The features ship in mise
   (2026.9.2+; `mise dot` 2026.9.8+; sync-race fix 2026.9.9+, E23). Pin mise ≥ 2026.9.9 before any sync between two machines.
2. **Put system defaults in the system layer and personal files in the user layer** (#11029 body:25, #12709). For us, the image carries
   `/etc/mise/conf.d/*` (our `mise-system.toml` analogue) and the person carries `~/.config/mise/config.toml` plus tracked files. Never bake personal
   history into the image.
3. **Track individual files and inspect directories first** (mise docs `bootstrap_setup.md:333`, E16). Classify what is per-machine (Omarchy example:
   monitors versus portable bindings, #11029 body:40), and use `os`/`profile` variants for real differences, not templates.
4. **Encrypt before the first capture** (`mise dot track PATH --encrypt` plus `[history.encryption].recipients` with a recovery key; #11029 body:123-131). History is
   permanent once published, and "adding encryption later does not remove older plaintext commits".
5. **Use labelled capture around risky mutating commands** (`mise dot capture --label "<op>" -- <cmd>`, E16). This is Omarchy's pattern around `omarchy-update`.
   For us it would wrap `mise run lock-*` and tool bumps, as a "what changed" query. It does not undo package effects.
6. **Keep the old safety net during rollout.** Omarchy's proposal keeps `.bak` behaviour during the initial rollout (#11029 body:17). For us, that means keeping chezmoi live until
   restore via `mise dot rollback --dry-run` / `undo` is proven for each file class.
7. **Serialize writes to the global config.** Lesson from #6964, E20/E21: our mise must include #12069 before any tooling runs concurrent `mise use -g`.

### Mac (`~/.config/mise` on this host) (inference from sources above; unverified until run)

- `mise dot track` each managed file, add `[bootstrap.services.mise-history] builtin = "history-watch"`, and run `mise bootstrap services apply`. mise installs a
  **LaunchAgent** on macOS (E15). Start local-only with no `origin set`. Prove `status`, `history`, `rollback --dry-run` and `undo` before any remote.
- Note: `chezmoi apply` is devcontainer-only on this Mac, and `mise bootstrap` writes to `$HOME`. Clear any host-side `mise bootstrap`/`mise dot apply` with Ray
  first, because it is the same class of host mutation the chezmoi deny rule exists to prevent (ask before acting).

### Docker devcontainer images and running containers (inference; no source demonstrates it; unverified)

- **Image build:** use declarative `[bootstrap.files]` / `[bootstrap.packages]` or plain `COPY` for image defaults. No history store and no watcher in the image
  (they are per-person runtime state). jdx lists the chroot/no-systemd constraint as needing an enable-only mode (E24). Treat service enablement at build time as
  unsupported unless the current docs say otherwise.
- **Running container:** the options are `mise bootstrap --adopt <setup repo>` in a lifecycle hook, or `mise dot watch --once` from a timer or hook
  (E26, the only documented route without a service manager). Keep `$MISE_STATE_DIR/history` on a named volume, not a bind mount (the virtiofs ownership
  flicker rule, `persistence-gate-retry.md`). Both options need a real two-arm test in the container before adoption.

### Correction to carry forward

Replace lane O's headline 1 in any plan or spec with the three-part statement in **Answer**, and cite E2/E8/E10/E12/E14. Any sentence of the form
"Omarchy does X with mise dotfiles" should say whether X is **shipped Omarchy code**, **user-level use of shipped mise**, or **proposal**.

## GitHub repos touched

- [omacom/omarchy](https://github.com/omacom/omarchy): shallow clone at `quattro` `8b4eae66` (grep, manual, plans/dots.md, etc/mise, packages); discussions #11029, #191, #5588, #12038; PRs #6964, #9596, #12037, #6965, #13470, #11435; issue/PR search (formerly basecamp/omarchy)
- [jdx/mise](https://github.com/jdx/mise): discussions #12709, #13022, #11432, #12597, #12067; PRs #11436, #12040 (and #12069 via jdx's comment); docs code search; merged-PR search for "omarchy"
- [timmo001/dotfiles](https://github.com/timmo001/dotfiles): community Omarchy setup (Stow + custom `dot` CLI, mise for tools)
- [zapling/mason-lock.nvim](https://github.com/zapling/mason-lock.nvim): referenced by the Omarchy user syncing nvim through mise (#11029), not read
