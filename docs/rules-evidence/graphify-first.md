# Evidence: graphify-first

Archaeology moved out of the eager rule `.claude/rules/graphify-first.md`.

## Moved from the rule (2026-09-24 prompt audit)

Verbatim text removed from `.claude/rules/graphify-first.md` by the prompt audit (`docs/research/kb/reports/prompt-audit-2026-09-24.md`); kept here so the history survives.

> - Claude's permission deny also blocks the labeling command words anywhere in a
>   Bash string, including the double-quoted grep shape whose backticks zsh ran.
> ## `fresh` now means "no scanned-corpus change since the build"
> Health used to check only that the graph file existed, parsed, matched the schema,
> and that the INSTALLED graphify was the pinned version. **Nothing compared the
> graph to the code.** The graph in this clone was built 2026-08-31 and reported
> `fresh` for thirteen days and 76 commits, while this rule told every agent a
> `fresh` graph is citable and a PreToolUse hook made querying it MANDATORY before
> grepping. Two symbols a session needed that day — `plan_attest_main`,
> `claude_doctor_main` — were absent because their modules postdated the build,
> and the graph answered as though they did not exist. Measured against controls:
> `setup_parser` 76 hits, `handle_pr` 21, both subjects 0.
>
> `_staleness_problem` closes it with two independent sources: Git says what
> Graphify 0.9.65 made equality alone too strict. Measured on 2026-09-22, a
> `mise.toml`-only commit advanced HEAD from `122a4de1` to `45e09803`, while both
> ordinary update and `--force` reported no topology change and left
> `built_at_commit` untouched. Because `mise.toml` is not a manifest key, that
> no-op rebuild is now correctly fresh; a newly added file with a scanned
> extension would still be stale.
>
> **The two installs are aligned again as of 2026-09-21 — both 0.9.65.** `graphify`
> on bare `PATH` resolves the **user-global** pin
> (`~/.config/mise/config.toml`, outside this repo's review);
> `mise run graphify-query`/`graphify-rebuild` resolve **this repo's locked
> version** (`python/uv.lock`), which is what `graphify_health`'s
> `version drift` check compares against. `mise run pin-parity` now binds every
> repository-owned pin site, including the three tracked skill stamps. The
> user-global pin remains outside that registry by design; the shared checker
> compares the binary resolved from `DOTFILES_AMBIENT_PATH` with the lock and
> names the user-global mise fix when it drifts. SessionStart doctor invokes the
> offline form, so it never calls `mise latest` or probes graph health.
> The check reads whatever graphify package is installed in the process
> *checking* health right now. It says nothing about which binary actually
> *built* the graph bytes on disk — a graph rebuilt by a drifted PATH binary
> (a bare `graphify update .`) is indistinguishable from one built by the
> repo's pin, because nothing records who built it. **An earlier
> version of this rule claimed a rebuild stamp closed that gap; it did not —
> the stamp could only ever record whatever the rebuild itself always
> resolves, so the check it fed could never fail, and the one drift it
> existed to catch wrote no stamp at all. It was removed rather than kept as
> a check that always reports "fine".**


## From the rule: What fresh means — health implementation reference

`_staleness_problem` decides it from two independent sources: Git says what
changed after `built_at_commit` — a field **graphify itself** writes from HEAD
at export time — while `graphify-out/manifest.json` says which relative paths
Graphify scanned. Equality with HEAD is immediately fresh. Otherwise a
manifest-listed path is stale for any change status; an unlisted path is stale
only when newly added with an extension already present in the manifest. A
modified or deleted unlisted path stays outside the corpus even when its
extension matches a scanned file.


## From the rule: Nothing records WHICH graphify built the graph — audit explanation

`graphify` on bare `PATH` resolves the **user-global** pin
(`~/.config/mise/config.toml`, outside this repo's review); the mise tasks
resolve **this repo's locked version** (`python/uv.lock`), which
`graphify_health`'s `version drift` check compares against. `mise run
pin-parity` binds every repository-owned pin site; the SessionStart doctor's
offline check names the user-global fix when the PATH binary drifts from the
lock.

Health reads the graphify installed in the *checking* process. Nothing records
which binary *built* the graph bytes, so a graph rebuilt by a drifted PATH
binary (a bare `graphify update .`) is indistinguishable from one built by the
pin.


## From the rule: What fresh means — squash-merge incident

 — the
2026-08-31 graph's `b75fa3b` has six commits unreachable from HEAD and no branch
contains it.


## From the rule: Nothing records WHICH graphify built the graph — receipt implementation context

: nothing in this repo writes one (that's the knowledge-base's
committed-corpus pipeline; see `_receipt_problem`'s docstring in
`python/src/dotfiles_setup/graphify.py` for why this repo cannot build one
of its own for an on-demand graph).
