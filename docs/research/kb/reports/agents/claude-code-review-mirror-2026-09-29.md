# Claude Code review docs offline mirror, 2026-09-29

## Commands (real rc)
- `firecrawl --status`: rc=0, key present (presence only). Credits BEFORE 541/1000, AFTER 527/1000 (10 scrapes; above the 150 floor). Concurrency limit 2; ran sequentially, 3s spacing, retry-on-fail loop (never triggered).
- `firecrawl scrape <url> --format markdown -o <f>` for ultrareview, code-review, index, claude-code-on-the-web, web-quickstart, costs, errors, github-actions, github-enterprise-server, routines: all rc=0, non-empty.
- `curl` https://code.claude.com/docs/llms.txt: 200 (50458 B). /docs/en/llms.txt: 404 (control: wrong path). `curl <page>.md` for the two review pages: 200.
- `gh release view v2.1.285 -R anthropics/claude-code --json body`: rc=0, 21439 B.

Output: /Users/rmanaloto/dev/github/ray-manaloto/dotfiles/docs/research/kb/raw/claude-code-review-2026-09-29/ (14 files incl. INDEX.md). See INDEX.md.

## Diff vs KB corpus (`.../agent-harness-docs/docs/claude-code/`)
Firecrawl output carries site nav chrome (ultrareview 95 nav lines), so a raw diff is noise. Control: the site's own `<page>.md` is the same MDX-derived format as the KB copy; diffing that. Both pages differ in real content, so the KB copies are STALE.

ultrareview.md (KB 18563 B vs live 18889 B), live is newer:
- Base can be a commit id or tag.
- Posting now: sends the review session ID to the Anthropic API, which posts stored findings (KB: via a cloud session). Outcomes: Posted / Already posted / Failed.
- New edge cases: "First commit" (reviews every file after launch-dialog confirmation; `claude ultrareview` and `claude -p` refuse; needs v2.1.277+); "No merge base"/no base branch fallback needs dialog confirmation or the subcommand run by the human, `-p` refuses; Claude running the subcommand via Bash is refused the whole-repo review; "Nothing to review" message names branch/case.
- New states: review stopped (session stopped/archived), session not found (deleted or account switched), resume with `claude --resume`.
- Exit code 1 now includes "stopped before finished". `--post` prints link to stderr.
- Free runs table unchanged (Pro 3, Max 3, Team/Ent none); rest is table reformatting only.

code-review.md (KB 34082 B vs live 33212 B), live is newer:
- "collapsible extended reasoning" renamed to a collapsed "Why this was flagged" section.
- Troubleshooting: Code Review now retries some interrupted reviews itself; check run titles now "Code review failed" / "timed out" (KB: "encountered an error"); summary says if a new review was auto-queued.
- Other diffs are table formatting only (filtered).

Also: KB changelog.md tops out at 2.1.273 and has zero mentions of 2.1.285, so the KB corpus lags at least 12 releases.

## v2.1.285 changes touching /ultrareview and Code Review (from release body)
- Fixes: misleading "core.worktree is set" error; git worktree with `core.longpaths` upload; uploads no longer include credential files named like `server:8443.key`; slow uploads on odd filenames; WSL refusal for colon/trailing dot/space names; Windows linked worktree of a repo rooted at home.
- Changes: PR reviews and `/ultrareview` now run when `disableWorkflows` is on unless set by MDM/managed settings; symbolic refs left out of upload (checkout whose branch is a symbolic ref is refused); requires git 2.31+ on macOS/Linux, `--separate-git-dir` checkouts refused; partial clones sent as working-tree snapshot on git>=2.31, refused on older git if files missing.
- Code Review: org menu in "Add a repository" loads more on scroll; check run states when REVIEW.md wasn't applied (very large PR, symlink).

## Digest: how /ultrareview works (10 lines)
1. `/ultrareview` (= `/code-review ultra`) or `claude ultrareview` launches a cloud-sandbox multi-agent review, ~5-10 min.
2. Targets: working diff (uploads local checkout) or a PR (`github.com` only); optional base branch, commit or tag.
3. A fleet of agents finds candidates; an independent verification step confirms each against real code behavior.
4. Needs claude.ai sign-in; not on third-party providers or with `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC`.
5. Pricing: Pro/Max 3 free runs, then usage credits (~$5-25/review); Team/Enterprise none free.
6. Runs as a tracked cloud session; can be stopped/archived; `claude --resume` re-attaches.
7. Non-interactive: `claude ultrareview [--json] [--timeout N (45 default)] [--post|--no-post]`; exit 1 = launch fail/stopped/error/timeout; running it yourself is the consent for whole-repo and billing prompts.
8. `--post` (v2.1.227+) posts findings as ONE plain comment via your connected GitHub account through the Anthropic API.
9. Diff size limits fall back with explicit refusals (first commit, no merge base, no branches).
10. 2.1.285 hardened uploads (git 2.31+, credential-file filtering, symbolic refs, partial clones) and made it run under `disableWorkflows`.

## GitHub repos touched
- [anthropics/claude-code](https://github.com/anthropics/claude-code) — v2.1.285 release body
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) — offline corpus diffed (local clone)
