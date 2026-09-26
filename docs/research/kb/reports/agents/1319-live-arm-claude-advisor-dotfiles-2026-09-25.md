# #1319 live arm — `claude-advisor` (dotfiles), 2026-09-25 — also the F13 / item 23(f) advice

Spawned via the `Agent` tool (`subagent_type: claude-advisor`) from session `dotfiles-20260925.001`
(`e0054614-0df9-4dff-9b50-af3b534871e1`). Returned: yes. 14 tool uses, 190.6 s. It answered the question Ray still
owes (task_plan.md remainder 23(f)): should `claude-doctor` call a one-patch lag "BROKEN"? This is advice only;
the ruling is Ray's.

## Report (verbatim)

**Verdict: KEEP-BROKEN** — keep `running != latest` as `INVALID` (enforcing). The only defect is the *word*: one line of vocabulary, not the severity.

Graph was `stale` (built 9c624360, HEAD 43b212b5); answered from source. Control arm: `BROKEN` returned 0 hits in `python/` but hits in `register.ts:375` and `harness.ts:480`, so the 0 was real.

**Deciding risk** — the repo's function hooks are typechecked against the vendored hook API `.claude/types/claude-code.d.ts`, pinned at `schemas/sources.toml:53` to `2.1.283` (= latest). A binary *behind* that pin can lack an API a hook calls, and a function-hook runtime failure fails OPEN and SILENT (2026-09-11d). `running == latest` at `python/src/dotfiles_setup/claude_doctor.py:509-518` is currently the *only* assertion keeping `running >= pin`; `_pin_currency_check` (:304-325) compares pin-vs-latest, never running-vs-pin. Softening removes that guard with no replacement. The `.d.ts` bytes did change across patch bumps (distinct sha256 at 2.1.277 vs 2.1.283), so this is live, not theoretical.

The deny is already narrow enough: read-only tools, escape hatches, `doctor.toml` edits and any Bash naming `claude`/`mise` pass (`register.ts:315-340`), and the hook **refreshes before denying** (`register.ts:396-412`), so the auto-updater race F13 observed self-heals — which is exactly why no deny fired on 09-25b.

SPLIT-BY-LAG-SIZE: reject — Claude Code moves only the third component (2.1.270→283 in 12 days), so a semver split makes the deny arm dead and a count threshold is a magic number with no control arm.

**Do differently** — reword `.claude/skills/claude-doctor/hooks/register.ts:375` (and the `.agents/…` mirror) from "install is BROKEN" to "install is not current — repair before continuing", and relax `tests/fixtures/claude_doctor_hook/harness.ts:480` `/BROKEN/`. Reserve "BROKEN" for method-mismatch / clean-marker failures if Ray wants two leads.

**Could not verify** — whether `.282→.283` specifically changed the hook API. Probe: `diff <(curl -s …/v2.1.282/mods/types/claude-code.d.ts) <(curl -s …/v2.1.283/…)`.

Prior codex verdict: none — this is Ray's owed ruling, not an escalation.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — `claude-doctor` source, hook and fixtures read
