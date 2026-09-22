# Raw probe artifacts — session 2026-09-22d

Promoted from the session scratchpad at handoff so the cited measurements survive.

- `skilloverrides-probe/` — `claude -p --model haiku --settings <file>` runs in the dotfiles repo (Claude Code 2.1.280).
  `so-base.json` = `{}`; `so-on.json` = skillOverrides "on" for `to-spec`/`mattpocock-skills:to-spec`/`to-tickets`;
  `so-ctl.json` = `{"skillOverrides":{"chezmoi-check":"off"}}` (control). Results: base → to-spec ABSENT, chezmoi-check PRESENT;
  on (2 runs, `so-on-*.answer.txt`) → to-spec ABSENT; ctl → chezmoi-check ABSENT. `*.init.json` shows the slash registry
  lists `mattpocock-skills:to-spec` in both arms (registry ≠ model listing). Conclusion: skillOverrides does not reach plugin skills.
- `wrapper-skill-probe/` — throwaway project skills loaded via `--add-dir`: `probe-at2` `@`-references a file holding a fresh
  token (recovered by the model: `KIWI-18965-15498`, absent from the prompt); `probe-at` `@`-references the mattpocock
  to-spec SKILL.md (its `## Process` body loaded); `probe-bang` (`!`cat …``) failed the -p shell permission check.
- codex install: the served `https://chatgpt.com/codex/install.sh` was byte-identical to `scripts/install/install.sh` at
  `rust-v0.156.0` (sha256 `150e3cf675682efeaac115aa3747add3f27887896d04ce6d0b56478d8b428bf6`).
