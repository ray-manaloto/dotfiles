<!-- verbatim final report of premise-verifier on docs/specs/research-fanout.md (rev 1), session dotfiles-20260926.000 -->

PREMISE REPORT (read-only lane: I could not write `findings.md` or run Bash/graphify, so this came from direct Read/Grep. Please persist it.)

ROWS: 13 checked — 7 CONFIRMED (2 provenance corrected) / 0 REFUTED / 4 UNVERIFIABLE / 2 ASSUMED (1 checkable)

- **1 — CONFIRMED, but it's the wrong precedent for the pass-through.** Registration is at `main.py:1531-1539` and dispatch at `:2823-2825`. However, session-state declares `--no-pr` and rebuilds argv; it doesn't pass the rest of argv through. The actual pass-through precedents are `process git-isolated` using `REMAINDER` (`main.py:1632`) and plan-attest using `nargs="*"` plus a separator (`main.py:1546-1551`, `:3112`).
- **2 — CONFIRMED.** `session_state.py:290` has `def main(args: list[str], repo_root: Path) -> int`.
- **3 — CONFIRMED.** `mise.toml:996-999`.
- **4 — CONFIRMED.** `child_env.py:77-92`.
- **5 — CONFIRMED.** `pyproject.toml:5` has `requires-python = ">=3.14"`.
- **6 — CONFIRMED (provenance corrected).** The row cites `command -v`, not a file:line. `ctx7` is at `mise.toml:66` and `firecrawl-cli` at `mise.toml:139`. `gh` is pinned only in the user-global config (`~/.config/mise/config.toml:131`, as `github-cli`). It's missing from `mise.toml`, `shared.toml` and `mise-system.toml`.
- **7 — CONFIRMED (provenance corrected).** Glob found all four script paths (3.21.1, 3.24.0, 3.25.0 in the Claude cache; 3.25.0 in the codex cache). "Highest-version" has to be a numeric comparison, not string order.
- **8, 9 — UNVERIFIABLE (sourced from a report).** Both match the inventory report (`:30` for exa, `:32` for firecrawl). They are live API claims, so reading code can't settle them. `E` is also the wrong kind for them: they aren't emission rows.
- **10 — UNVERIFIABLE (sourced from a report).** Matches inventory `:81` (6 results vs 14).
- **11 — UNVERIFIABLE (the test conditions don't match).** The ~100 s figure was measured with `--plan …` and `python3.14` (multisource `:63`). The spec's command drops `--plan`. The compact mode itself does exist: `last30days.py:658`, where it is the default `--emit`.
- **12 — ASSUMED.** The raw report `:31` confirms a GraphQL `type:DISCUSSION` search with control 0 vs 63. It doesn't record whether the query used a `repo:` qualifier.
- **13 — ASSUMED (checkable).** `.agent/kb/raw/mise-warn-src-ctx7.md:1-105` shows plain text: a numbered list of library IDs, then `### ` sections, each with a `Source:` URL. Only the first ID gets a docs call, so "one Item per library hit with the docs text as snippet" doesn't hold together.

MISSING:
- **`REMAINDER` rejects a leading flag.** `plan_attest.py:104-110` records that `REMAINDER` only absorbs flags when the first token is not a flag. `main()` uses `parse_args` (`main.py:3112`). So the §5 check `mise run research-fanout -- --list-sources` would exit 2. The fix must go in `main.py`, which §2 allows (for example, extend the separator logic there, or use `parse_known_args`).
- **PLR0913 (too many arguments) on the pinned `fan_out` signature.** It has 7 parameters. Ruff runs with `select=["ALL"]` and no `pylint.max-args` override (`pyproject.toml:63-86`), so the default limit of 5 applies, and inline `noqa` is banned. Bundle the arguments into a request dataclass, as `WaitRequest` and `OrphanRequest` do (`main.py:2835`, `:2844`). I didn't run ruff to confirm this.
- **S310 (ruff's URL-open audit) is not ignored.** The repo has no `urllib.request` precedent; the existing HTTP code shells out to `curl` (`gcc_sha.py:129`). Check that a dynamically built URL passes S310 without a suppression.
- **Tests have no network guard.** `conftest.py` has no socket blocking, and `tests/AGENTS.md:97-100` asks for injected seams. But `main(argv, repo_root)` has no seam, so the §5 exit-code tests for 0 and 1 either hit the network or patch our own module, which `tests/AGENTS.md:94` forbids.
- **`clean_env` does strip `GITHUB_TOKEN`.** The `TOKEN` pattern at `child_env.py:49-51` matches it, so the keep set is required. last30days' keep set leaves out `GITHUB_TOKEN`, so it falls back to `gh auth token` (`github.py:53-59`, 5 s timeout). That is the keychain route `secrets-out-of-the-shell-env.md` warns about. The doctor's key list (`doctor.py:203-221`, 17 names) is also not the 6 names the spec gives.
- **Items vs. compact output.** Compact output is markdown, not JSON. `--emit=json` exists (`last30days.py:658`).
- **`.raw.json` holding text.** ctx7 and compact last30days output are text, so `<source>.raw.json` would hold non-JSON.
- **Unstated behavior choices.** The spec doesn't say whether the firecrawl canary keeps the `repos=` filter, or whether a user-supplied `--timeout` overrides the 180 s last30days default.
- **Non-blocking: no hard gate on new mise tasks or subcommands.** The `workflow.*-wiring` contracts in `suites.toml` exist only per feature. The inventory report (`:94`) calls for a mise-tasks-only row and a contract, but §4 forbids touching `.claude/`. Only `taplo` and hk's `mise` builtin check the new task.

INTERNAL CONTRADICTIONS:
- **"No LLM in the loop" (§1) vs. last30days without `--plan`.** Keeping `XAI_API_KEY` turns on an xAI planner and reranker (`providers.py:271-279`, `planner.py:375-377`). Keys in `~/.config/last30days/.env` bypass `clean_env` entirely.
- **Compact output vs. the error rule.** §4 says unparsable JSON is `ERROR`, but §3 asks for `--emit=compact`, which is markdown.
- **Exit-code tests vs. the `main` signature.** The §5 exit-code tests need fakes, but the §3 `main(argv, repo_root)` signature has nowhere to inject them.

VERDICT: correct the spec first. What blocks:
1. The `REMAINDER` leading-flag failure breaks the spec's own §5 check.
2. The `fan_out` signature trips PLR0913 with suppressions banned (not run).
3. last30days' planner contradicts §1.
4. `main` needs seams for the exit-code tests.

Paths: `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/docs/specs/research-fanout.md`, `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/plan_attest.py`, `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/main.py`, `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/pyproject.toml`


---

<!-- verbatim final report of premise-verifier re-check of spec rev 2 (changed rows only) -->

**PREMISE REPORT (rev 2 delta only)**

This lane is read-only, so nothing was written to `findings.md`. Please persist this report.

**Rows: 4 re-checked. 3 confirmed (1 with provenance corrected), 1 confirmed with a wrong precedent citation.**

- **Row 1: the mise half is confirmed; the `session_gate` half is misdescribed.** `mise.toml:1619-1621` does run `uv run --project python python -m dotfiles_setup.session_gate`. But `session_gate.py:509-510` is `raise SystemExit(main())`, and its `main(argv=None)` requires `--repo-root` (`:459-462`). It does not pass `Path.cwd()`. The repo's own way of finding the repo root is `MISE_PROJECT_ROOT`: `session_gate.py:272` reads it with a fallback to `Path.cwd()`, and `mise.toml:1625` passes `--repo-root "$MISE_PROJECT_ROOT"`.
- **Row 6: confirmed (provenance corrected).** `mise.toml:66` pins `npm:ctx7` 0.5.12 and `:139` pins `npm:firecrawl-cli` 1.24.6. `~/.config/mise/config.toml:131` pins `github-cli` 2.101.0. The Source column still cites "premise-verifier" instead of these lines.
- **Row 11: confirmed at 3.25.0.** `--emit` choices include `json` (`last30days.py:658`), and `--plan` skips the internal LLM planner (`:805`). `--github-repo` exists at `:843`.
- **Row 13: confirmed.** In `.agent/kb/raw/mise-warn-src-ctx7.md`, every `### ` section is followed two lines later by a `Source:` line (`:39/41` through `:93/95`). One caveat: each ID sits on a `Context7-compatible library ID:` line inside a multi-line numbered entry (`:3-4`), not in a bare list.

**Your specific questions**

- **Task cwd is the project root: confirmed.** The default task `dir` is `"{{ config_root }}"` (`schemas/mise.json:3415`). `mise.toml` has no `[task_config]`. Its two `dir = "python"` lines are `[deps.uv]` (`:7`) and the task `deps:python` (`:253`). Neither `.config/mise/` nor `mise.local.toml` sets a `dir`. `uv run --project` does not change cwd.
- **`python -m` resolves `dotfiles_setup` from the repo root: confirmed.** `python/.venv/.../__editable__.dotfiles_setup-0.1.0.pth` contains `.../dotfiles/python/src`. Two existing tasks already rely on this (`mise.toml:1621`, `:1633`).
- **S310 accepts an f-string starting with `https://`: unverifiable.** There's no local ruff rule doc: the mintlify cache and the KB sources have 0 hits, while the control grep for `ruff` in the same cache returned 10. From memory, not checked: ruff allows a literal or f-string that starts with `https://`, and flags a plain variable URL.

**Missing / new contradictions**

- **S310 vs. the `http` seam (load-bearing).** §3 says `default_http` is a Protocol seam, which means it takes the URL as a parameter. At the `urlopen` call that URL is a variable, not a literal. §4 requires a literal, and ruff checks each call site on its own, so the implementer will likely hit the §4 STOP. The spec needs to fix the seam's shape: for example, the seam takes host and path, and the `f"https://..."` string is built at the `urlopen`/`Request` call itself.
- **§4 says `.env` is something "no env scrub can reach". The plugin code contradicts this.** Setting `LAST30DAYS_CONFIG_DIR=""` disables the config file (`lib/env.py:31-35`).
- **Keychain and `pass` are unstated credential sources.** last30days reads 23 keys from the macOS Keychain, including `XAI_API_KEY` and `OPENAI_API_KEY` (`env.py:65-73`, `:346-419`, `timeout=5` per key). It also reads the same keys from `pass` (`:422-458`). Setting `LAST30DAYS_SKIP_KEYCHAIN` turns the Keychain source off (`:60`, `:362`). The KNOWN LIMIT section needs to name these sources.
- **`GH_TOKEN` doesn't prevent the fallback.** last30days reads only `GITHUB_TOKEN` (`lib/github.py:53`), then falls back to `gh auth token` (`:59`).
- **Minor citation drift.** `main.py:2835` is `OrphanRequest`. `WaitRequest` is at `:2844`, defined at `bounded_wait.py:27`.

**VERDICT: correct the spec first.** Fix the S310/seam shape (otherwise the implementer hits the STOP), the refuted `.env` claim, and the unnamed Keychain source. The `session_gate` precedent wording is not blocking.

Files: `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/docs/specs/research-fanout.md`, `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/session_gate.py`, `/Users/rmanaloto/.claude/plugins/cache/last30days-skill/last30days/3.25.0/skills/last30days/scripts/lib/env.py`
