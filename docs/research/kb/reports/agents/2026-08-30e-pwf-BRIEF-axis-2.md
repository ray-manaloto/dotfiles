## Your axis — COLLISIONS WITH THIS REPO'S FILES AND GATES

Answer, each cited, and give a cardinality for each set you enumerate:

1. **`.agents/skills/` collision.** The plugin ships
   `.agents/skills/planning-with-files/`; the repo has three entries there and an
   hk step `session_review_skill_parity` asserting a byte-identical twin. Does
   installing the plugin write into the repo's `.agents/` tree, or only into the
   plugin cache? Settle this from the plugin's install path, not from assumption.
2. **Command-name collisions.** Enumerate all 13 commands the plugin registers.
   Cross-check each against the repo's own commands and skills (`.claude/skills/`,
   `.claude/commands/`, and the agent types in `.claude/agents/`). Name every
   collision or near-collision, including `/plan` versus the repo's `Plan` agent.
3. **Gate breakage.** For each of these hk steps, say whether the plugin's files
   would trip it if they landed in the repo tree, and whether they land there at
   all: `bash_logic_budget` (allowlist + line budget for `scripts/*.sh`),
   `no_lint_skip`, `claude_md_import_stub`, `claude_agents_md_pairs`,
   `md_size_budget`, `no_env_dump`. `hk.pkl` is the authority.
4. **Does anything it writes append to `AGENTS.md` or the root `CLAUDE.md`?**
   `AGENTS.md` has 125 bytes of headroom and the root `CLAUDE.md` must be
   byte-exactly `@AGENTS.md`. An append to either is a BLOCKER. Control-arm the
   answer.
5. **`.gitignore` impact.** It writes `task_plan.md`, `findings.md`,
   `progress.md`, `.planning/`, `.active_plan` to the project root. Check the
   repo's `.gitignore` for existing coverage and name exactly what would show up
   as untracked. Note that `do-not.md` item 5 forbids bulk `git add .`.

Write incrementally to:
/private/tmp/claude-501/-Users-rmanaloto-dev-github-ray-manaloto-dotfiles/84f08a9b-5231-4071-8759-b2d32945c99e/scratchpad/pwf-B-collisions.md
