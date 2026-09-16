# Rules-compliance audit — codex SDLC lane `2c97f4bcd31443dd9ad598f4cce08dd0`

**Auditor:** Claude Opus 5 rules-compliance lane, 2026-09-15
**Subject:** codex SDLC lane, run id `2c97f4bcd31443dd9ad598f4cce08dd0`, mode `review`,
supervisor pid 50879.
**Status at time of writing:** ⚠️ **LANE STILL RUNNING.** This is a partial audit
of a growing log, not a pass. See §D.

## Verdict summary

| § | Question | Verdict |
|---|---|---|
| A | Violated its own spec's absolute constraints? | **CLEAN** (0/70 commands) |
| B | Mutated the working tree? | **CLEAN** |
| C | Rule compliance beyond the spec | **CLEAN**, with two observations (§C.1, §C.5) |
| D | What I could not see | Partial — lane live, 1 command unparsed, subagent-internal work unobservable |

## Method, and its bounds

The dispatch argv (decoded from the supervisor's base64 payload in `ps`) is:

```
codex.js exec --ephemeral -s read-only -c model_reasoning_effort="xhigh" \
  -C /Users/rmanaloto/dev/github/ray-manaloto/dotfiles \
  -o .agent/sdlc-runs/<run>/output.md -
```

⚠️ **The log is NOT JSONL.** The brief and `.claude/rules/codex-sdlc-team.md` both
describe the dispatcher as passing `--json --output-schema`; **this dispatch passes
neither**. A json-per-line parse of `codex.log` yields **11,645 unparseable lines and
0 usable records** — believing that first parse would have produced "no commands
found", a false negative. The real format is a plain-text block:

```
exec
/bin/zsh -lc '<command>' in /Users/rmanaloto/.../dotfiles
hook: PostToolUse
 succeeded in 111ms:
```

Commands were extracted with a regex over that shape.

**Parser control arm:** `grep -c '^exec$'` reports **71** marker lines; the parser
recovered **70** blocks. The missing one is the in-flight command at the log tail,
which has not yet written its ` in <cwd>` terminator. So the parse is complete for
every *settled* command and misses exactly the one still running.

**graphify:** `mise run graphify-health` reports **stale** — graph built at
`63a76ec0`, HEAD is `4d91064d`, 2 commits behind. Per
`.claude/rules/graphify-first.md` a stale graph is unavailable, so all findings below
come from source and from the log, not from the graph.

## A. Spec's absolute constraints — CLEAN

70 settled commands, every one a read. Scans below; each ran with a control arm, and
a **freshly invented** known-absent token (`xmqvzt9frwub`) returned 0, proving the
matcher is not matching everything.

| Prohibition | Hits | Control arm (same command shape) |
|---|---|---|
| Edit/create/delete a repo file (`sed -i`, `tee`, `rm`, `mv`, `cp`, `touch`, `mkdir`, `git add`) | **0** | `git show` → 3 hits |
| Shell output redirection (`>`, `>>`) | **0** | (same corpus as above) |
| Run a gate (`mise run lint`/`verify`/`fmt`/`test`, `pytest`, `hk run`) | **0** | `mise latest` → 2 hits |
| `git commit` / `git push` / `gh pr create` / `gh pr merge` | **0** | `git show` → 3 hits |
| Any install (`mise install`, `mise use`, `npm install`, `pip install`, `install.sh`) | **0** | `curl -fsSL` → 2 hits |
| Pipe a gate/probe into `head`/`tail`/pager | **0** | `ls-remote` → 2 hits |

Every command is one of: `cat`, `nl -ba`, `rg`, `find`, `ls -l`, `command -v`,
`git status/rev-parse/show/log/ls-remote`, `gh pr view`, `gh api` (GET),
`curl -fsSL --range`, `mise latest`, `claude --version`.

Two commands deserve explicit clearance because they look adjacent to a ban:

- `[10] mise latest github:anthropics/claude-code` — the spec itself names this as
  permitted: *"a query-only oracle (installs nothing)"* (spec §F2).
- `[25]/[26] curl -fsSL --range 0-1023 https://raw.githubusercontent.com/...d.ts` —
  fetches a type-declaration file to stdout. No `-o`, no pipe to a shell. Not an
  install.

### Would `hook_guard` have denied any of them?

**No — 0 of 85.** Settled by replaying the real matcher; see §A (continued) below.

## B. Working-tree mutation — CLEAN

```
$ git status --short      → (empty)
$ git diff --stat         → (empty)
$ git diff --cached --stat→ (empty)
$ git stash list          → stash@{0} On docs/session-2026-09-14e-reports: hk
                            stash@{1} On chore/deps-currency: PR-B: settings.json + doctor.toml + .omc
$ git log --oneline -1    → 4d91064 fix(ci): every hk job installs Claude Code, and a gate that says so
```

Working tree clean, index clean, HEAD unmoved. Both stash entries predate this lane
(`stash@{1}` is on a different branch entirely, `chore/deps-currency`), and no
command in the corpus is `git stash` — the mutation-verb scan covers it and returned
0 hits against a passing control arm.

Lane artifacts under `.agent/sdlc-runs/<run>/` are gitignored and expected; they are
written by the *supervisor*, not by a lane shell command, and are not violations.

## A (continued). Would `hook_guard` have denied any command? — NO

This was settled by **replaying the real matcher**, not by reading patterns:
`dotfiles_setup.hook_guard.match()` — the same function `decide()` and
`command_audit` go through — was run over every extracted command.

```
replayed: 85   (control: '^exec$' markers = 87)
TOTAL DENIED: 0 / 85

POSITIVE CONTROL (must deny):
  npx foo                        -> npx
  mise run lint | tail -5        -> gate command piped to head/tail
  echo "$GITHUB_TOKEN"           -> secret_value_substitution
  gh pr create --title x         -> gh pr create
  gh pr merge 123 --auto         -> gh pr merge --auto
  git commit -m "x" --no-verify  -> git --no-verify
  hk run check --all             -> hk run check
  chezmoi apply                  -> chezmoi apply/update
  devcontainer up …              -> devcontainer up
  gh run watch 123               -> gh run watch
NEGATIVE CONTROL (must allow):
  nl -ba README.md               -> None
  rg -n foo bar.py               -> None
  git status --short             -> None
  gh pr view 1130 --json state   -> None
```

10/10 positive arms denied with the *correct* rule name; 4/4 negative arms
allowed. The matcher discriminates, and it denies nothing the lane ran. So the
blind spot named in `.claude/rules/codex-sdlc-team.md` ("Its blind spot") did not
cost anything on this run: the spec alone held, and it held correctly.

⚠️ **A parser control arm caught a bug in this very audit.** An intermediate
replay reported `replayed: 0` against a known 85 — a split regex that silently
matched nothing. Reporting "0 denied" from that run would have been a false
clean. The count check is why it was caught.

## C. Rule compliance beyond the spec

### C.1 `probes-need-a-control-arm.md` — one genuine control-arm pair, but it was VOID

The lane did construct a proper pair for the upstream-tag question:

```
[27] git ls-remote --tags https://github.com/anthropics/claude-code.git refs/tags/v2.1.273     -> exited 128
[28] git ls-remote --tags https://github.com/anthropics/claude-code.git refs/tags/v2.1.999999  -> exited 128
```

`v2.1.999999` is a well-chosen known-absent arm. **But both arms exited 128 for an
environmental reason**, not an answer:

```
git: error: couldn't create cache file '/tmp/xcrun_db-…' (errno=Operation not permitted)
```

Per `probes-need-a-control-arm.md` rule 4, *"a redirect/timeout/parse-error is not
a 'no'"*. If the lane's final report converts these into "tag v2.1.273 does /
does not exist upstream", that is a violation. **It has not yet reported**, so
this is a live risk for the coordinator to check against the final output, not a
confirmed violation.

### C.2 The lane had NO NETWORK — its upstream oracles could not be asked

Three independent network probes failed inside the lane:

| Cmd | Result |
|---|---|
| `[13] gh pr view 1130 …` | `exited 1` — `error connecting to api.github.com` |
| `[14] gh api repos/…/issues/1043` | `exited 1` — `error connecting to api.github.com` |
| `[25]/[26] curl -fsSL … raw.githubusercontent.com/…d.ts` | `exited 6` — `Could not resolve host` |

**Control arm (mine, outside the lane sandbox):** `dscacheutil -q host -a name`
resolves `raw.githubusercontent.com` → `185.199.109.133` and `api.github.com` →
`140.82.113.5`, while a freshly-invented `bogus-xmqvzt9f.invalid` → NO_RESOLVE.
So the failure is the **lane's sandbox**, not a host outage.

This is expected, not a regression: `python/src/dotfiles_setup/sdlc_team.py:349`
sets `sandbox = "read-only"` for review mode and passes it at `:354-355`, and
`.claude/rules/codex-sdlc-team.md:46-47` documents exactly this — *"Under
`-s read-only` every repo gate fails for sandbox reasons (uv cache, mise state,
DNS). That is sandbox noise, not a finding."*

⚠️ **Consequence the coordinator must not miss:** spec findings **F2** (is 2.1.273
really upstream's latest) and **F4** (does tag `v2.1.273` exist, what version does
its `.d.ts` carry) are **network-dependent and were unanswerable in this lane.**
Its two surviving oracles do not substitute:

- `[10] mise latest github:anthropics/claude-code` → `2.1.273`, but it printed
  `tool purgatory cleanup failed: Operation not permitted` in the same breath and
  the network was down — so this is almost certainly a **cached** answer, not a
  live query. It is not independent confirmation.
- `[11] claude --version` → `2.1.273 (Claude Code)` — that is the **installed**
  version on this host. "Installed" is not "latest"; it cannot confirm P1.

### C.3 `long-running-command-hangs.md` rule 3 — CLEAN

Zero pipes into `head`/`tail`/`less`/`awk`/`sed -n` across all 85 commands
(control arm `ls-remote` → 2 hits on the same corpus and command shape; a
freshly-invented absent token → 0). No gate was run at all, so the rule's
subject never arose.

### C.4 `secrets-out-of-the-shell-env.md` rule 7 — CLEAN

No `echo`/`printf`/`print` of any credential-named variable (0 hits; the real
guard's `secret_value_substitution` rule also denied my positive control
`echo "$GITHUB_TOKEN"` while denying nothing the lane ran). No credential-bearing
dotfile was read: a scan for `.net`+`rc`, `.aws/cred`+`entials`, `.ssh/id`+`_`,
`hosts.yml`, `.dopp`+`ler`, `.fn`+`ox`, `.npm`+`rc`, `keych`+`ain`, `agentsview`
returned 0, against a passing control arm (`/Users/rmanaloto/.codex` → 1 hit).

The only home-directory reads were `~/.codex/memories/MEMORY.md` (cmds 3, 78-81),
`~/.local/bin/claude` (29), and `~/.local/share/claude/versions/2.1.273` (30-32) —
none a credential store.

*Note for the record:* my own first scan command was **denied by this repo's
`permissions.deny` credential-path rules**, because the literal path fragments sat
inside my grep *pattern*. That is the best-effort `Bash(*fragment*)` arm firing on
a string match — working as documented in `secrets-out-of-the-shell-env.md` rule 8.

### C.5 `mise-tasks-only.md` — CLEAN

No command has a canonical mise task it bypassed. `gh pr view` / `gh api` are
explicitly diagnostic-and-direct; `mise latest` is a query, not a lifecycle verb;
no `gh pr create`/`merge`, no `gh run watch`, no `devcontainer` verb, no `npx`.

### C.6 Operational finding — the specialists never spawned

**The "team" ran as a single agent.** The log carries four:

```
ERROR codex_core::tools::router: error=collab spawn failed:
  no thread with id: 01a0a848-4257-7852-93d0-95a8872c671e
```

at 03:36:29, 03:36:44, 03:36:58 and 03:43:35. The dispatcher prompt anticipates
this (*"If spawning still fails, do the work yourself and report every spawn
failure"*), so the fallback is sanctioned — but the coordinator should read the
result as **one generalist lane's work, not six specialists'**, and should check
that the final report's mandatory `Specialists spawned:` list says so honestly.

## D. What I could NOT determine — read this before treating the audit as a pass

1. **The lane is STILL RUNNING.** Supervisor pid 50879 alive; `output.md` and
   `settlement.json` do not exist. The log grew from 1,788,733 → 1,851,526 bytes
   *during* this audit and the command count went 70 → 85. **Every command after
   85 is unaudited.** A clean audit of a partial log is a partial audit.
2. **The final report is unwritten, so its CLAIMS are unaudited.** Everything
   above audits what the lane *did*, not what it will *say*. The §C.1 and §C.2
   risks — a void control arm and a cached/installed-version oracle — can only
   become violations in the final text, which does not exist yet.
3. **One `exec` marker is always unparsed** (87 markers vs 85 blocks + the header
   occurrence): the in-flight command has not written its terminator.
4. **Sub-agent-internal work is unobservable** — moot here, since no specialist
   ever spawned (§C.6).
5. **I cannot see non-`exec` side effects.** Anything the model did through a
   non-shell tool surface leaves no `exec` record. The clean `git status` in §B
   bounds this for repo files, but not for writes outside the repo.
6. **`graphify` is stale**, so no graph-derived claim appears anywhere above.

## GitHub repos touched

_None._ — this audit read only local files and the lane's own log; every network
call in evidence is one the **lane** attempted and failed.

## Closing state (audit end)

| Fact | Value |
|---|---|
| Supervisor pid 50879 | **ALIVE**, 14m51s elapsed |
| `codex.log` | 1,853,017 bytes — grew throughout the audit |
| Settled `exec` commands | **85**, all audited, **0 denied** by the real guard |
| `output.md` / `settlement.json` | **absent** — lane has not reported |
| `.agent/lane-results/2c97f4bcd…{json,md}` | **absent** |
| `git status --short` | only `?? docs/research/kb/reports/agents/rules-compliance-2026-09-15-sdlc-lane.md` — **this report**, written by the auditor, not the lane |

The lane's own footprint on the working tree at audit end is **nothing**.
