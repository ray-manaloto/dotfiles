# Spec review — PR #1426 (89b9e823) vs docs/specs/prompt-audit-C-apply.md

_Status: complete (2026-09-28). Read-only; diff `89b9e823~1..89b9e823`, non-astra hunks read in full; residue checked with `git grep -lF` at 89b9e823 (control: `codex-lane-mirror`, 12 hits)._

## (a) Missing / partial

1. **§5 grep gate unmet on the filesystem.** Spec: "each must print 0 for `.claude/agents` and `.codex/agents`: `grep -rlF …`". The command still hits gitignored Codex-app exports (`grep -rlF 'read line 8 of' .codex/agents` = 1). Tracked files are clean. Deferred to #1425 (OPEN), so it is not silently dropped.

Every C1–C15 hunk is otherwise present. No C16–C27 edit.

## (b) Not asked for by the spec

2. **TOML body edit.** Spec: TOMLs get only "the `description` tail … (C5)". The diff also changed "174 pages" → "the pages" in the body of `codex-sol-claude-code-expert.toml:63` (the commit message says so).
3. **`codex-sol-advisor.md` story removal (F5).** Spec lists this file for "(C4)" only. Two incident stories were deleted. Cold review F5 sanctioned this, but the spec was never amended.
4. **The md C5 tails dropped "Standing".** Spec: "the new description tails are the report's C5a-c wording" ("Standing critique lane…"). The diff has "Critique lane…". F8 flagged only the TOMLs' definite article, and said the md form "avoid[s] it".
5. Four new docs files (the spec plus three reports) fall outside §2's list. They are required by `agent-report-persistence.md`, so they are benign.

## (c) Implemented but wrong or changed meaning

6. **Grammar defect.** `codex-sol-staleness-auditor.toml` (and its astra twin) reads "not Claude — **a audit lane**". The spec shape was "— the standing <role> lane;". Dropping "standing" (F8) left an article that no longer fits.
7. **C9b citation still does not carry the claim (F4 only half-fixed).** The new text says "measured 2026-09-16 … a weakened test, a dismissed red lint, an attempted `--no-verify`" and cites `codex-call-audit-2026-09-23.md`. That file has `no-verify` 0 hits and `lint` 0 hits, and its `:149` calls even the two-writer detail "INHERITED … not re-derived". "Measured" plus an inherited, partial record overstates the evidence.
8. **C5 doctrine weakened in the TOMLs.** P8 rests on "codex lanes are standing, not contingent". None of the six TOML descriptions now says that, although the body line "the standing arrangement" survives (`.toml:28`). F8 objected only to the definite article, not the word ("a standing critique lane" would satisfy it).
9. **Minor.** The F2 carve-out lines run to about 120 characters inside otherwise-wrapped bullets (e.g. `adversarial-critic.md:148`). This is cosmetic, but it strains "Do not reflow untouched paragraphs".

Verified as meaning-preserving: C1+F7, C2 (600000 now present), C3+F2, C4, C6, C7a–f, C8, C10, C11, C12–C14, C15 (with F3's softening).

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the PR diff, spec, report C, cold review, and issue #1425 (state read).
