# jdx/usage — what it generates, and what a new CLI on it costs

**Agent:** jdx-usage-generator · **Date:** 2026-08-04 · **Status:** COMPLETE

Binary probed: `/Users/rmanaloto/.local/share/mise/installs/usage/4.1.0/usage`
(`usage-cli 4.1.0`, released 2026-07-28 per `usage/CHANGELOG.md:3`).
Shallow clones in scratchpad: `jdx/usage`, `jdx/fnox`; pre-existing `jdx-mise`,
`jdx-hk`. Raw sources persisted to `.agent/kb/raw/usage-*.md`, `fnox.usage.kdl`.

## Bottom line

`usage` is **"OpenAPI for CLIs"** (the README's own framing). It is a spec
format (KDL) plus a standalone binary that turns that spec into completions for
5 shells, markdown docs, man pages, JSON, typed TS/Python SDKs, a Fig spec, and
an MCP server — **and can also be the argument parser at runtime for a program
in any language**.

For the three jdx Rust CLIs it is a *superset layer over clap*: clap still
parses; usage generates everything downstream from a spec clap emits. For a
**non-Rust CLI it is a full substitute** — proven by experiment below.

Three answers that change the decision:
1. **`usage` does not replace clap in a Rust CLI** — it consumes clap's tree.
   You still write clap.
2. **A Python CLI gets the whole downstream stack from a hand-written KDL file**
   with zero Rust. Experiment run, all arms green.
3. **There is no `usage init` / template / scaffold.** You write the first KDL
   by hand, or emit it from clap/cobra.

---

## Q1 — What `usage` generates, and from what

Input in every case is a **usage spec**: a `.usage.kdl` file (`-f`), a raw
string (`--spec`), stdin (`-f -`), a `usage` shebang script, or the stdout of a
CLI invoked with `--usage-cmd`.

`usage --help` (verbatim, 4.1.0):

```
Commands:
  bash           Execute a shell script using bash
  complete-word  Generate shell completion candidates for a partial command line [alias: cw]
  exec           Execute a script, parsing args and exposing them as environment variables [alias: x]
  fish           Execute a shell script using fish
  generate       Generate completions, documentation, and other artifacts from usage specs [alias: g]
  lint           Lint a usage spec file for common issues
  mcp            Serve a usage spec over the Model Context Protocol [alias: mcp-server]
  powershell     Execute a shell script using PowerShell
  sponsors       Show the companies sponsoring usage and the jdx.dev open source tools
  zsh            Execute a shell script using zsh
Options:
      --usage-spec  Outputs a `usage.kdl` spec for this CLI itself
```

### The generator surface (`usage generate --help`)

| Artifact | Command | Notes |
|---|---|---|
| Shell completions | `usage g completion <SHELL> <BIN>` | **bash, fish, nu, powershell, zsh** |
| Shell init for all shebang scripts | `usage g completion-init <SHELL>` | bash, fish, zsh; source once from rc |
| Fig / Amazon Q spec | `usage g fig` | |
| JSON spec | `usage g json` | |
| Man page | `usage g manpage [-s SECTION] [-o FILE]` | |
| Markdown docs | `usage g markdown [-m --out-dir …] [--url-prefix …] [--html-encode] [--replace-pre-with-code-fences]` | `-m` = one file per subcommand → a docs site |
| Typed SDK | `usage g sdk -l <typescript\|python> -o <DIR>` | subprocess wrapper, not a native binding |
| MCP server | `usage mcp -f <spec>` | stdio JSON-RPC; **describes**, does not execute |
| Spec lint | `usage lint <FILE> [-f json] [-W]` | |

⚠️ **Docs are ahead of the shipped binary on SDK languages.** `docs/spec/index.md:11`
claims "type-safe SDK client libraries for **TypeScript, Python, and Rust**", but
4.1.0 refuses Rust:

```
$ usage g sdk -f vaultpy.usage.kdl -l rust -o /dev/null
error: invalid value 'rust' for '--language <LANGUAGE>'
  [possible values: typescript, python]
```

(The clone is `--depth 1` of `main`, so the docs are at HEAD and 4.1.0 is the
last release — the Rust SDK is either unreleased or aspirational. Do not plan on
it.)

### Runtime argument PARSING is in scope too

This is the part that is easy to miss and is the whole answer to Q3:

- `usage exec <INTERPRETER> <SCRIPT> [ARGS]…` — parses args per the spec and
  exposes them as `usage_<name>` **environment variables** to the script.
- `usage bash|zsh|fish|powershell <SCRIPT> [ARGS]…` — same, for shell scripts.
- `usage complete-word` — the runtime completion engine that generated
  completion scripts call back into on every keystroke.

### Completions are DYNAMIC, not a static word list

`usage g completion zsh vaultpy -f vaultpy.usage.kdl` emits a script that:
1. hard-checks for the `usage` binary — *"Error: usage CLI not found. This is
   required for completions to work in vaultpy."* → **`usage` is a RUNTIME
   dependency of the completions on the end user's machine**;
2. writes the spec into `${XDG_CACHE_HOME:-~/.cache}/usage/usage__usage_spec_<bin>.spec`;
3. delegates each keystroke to
   `command usage complete-word --shell zsh -f "$spec_file" -- "${(Q)words[@]}"`.

With `--usage-cmd "<bin> usage" --cache-key <version>` it instead re-derives the
spec by calling your CLI, cached per version — that is what fnox does.

### The MCP server (4.1.0, PR #746) — describe, not execute

Real JSON-RPC handshake against my toy spec (`usage mcp -f vaultpy.usage.kdl`,
rc=0):

```
INIT: {"protocolVersion":"2024-11-05","capabilities":{"tools":{}},
       "serverInfo":{"name":"usage","version":"4.1.0"},
       "instructions":"Describes a CLI from its usage spec. Every command, flag and
        argument may carry an `effect`: `read` only inspects state, `write` changes it,
        `destructive` removes …"}
TOOL: list_commands     — "Every command in the CLI, with its effect. Start here."
TOOL: describe_command  — "Full detail for one command: help, flags, arguments…"
```

Only 2 tools, both read-only. It teaches an agent the CLI's shape and — via
`effect=` (added 3.6.0 #739 for commands, 4.0.0 #742 for flags/args) — which
commands are `read` / `write` / `destructive`. **Directly relevant to a secrets
CLI:** it is the mechanism by which an agent can be told `get` is read and
`remove` is destructive, without the agent guessing.

### Other spec features worth knowing for a secrets CLI

`docs/spec/index.md` (persisted at `.agent/kb/raw/usage-spec-reference.md`):

```kdl
config_file ".mycli.toml" findup=#true
flag "-u --user <user>" help="User to run as" env="MYCLI_USER" config="settings.user" default="admin"
```

> "The priority over which is used (CLI flag, env var, config file, default) is
> the order which they are defined, so in this example it will be
> `CLI flag > env var > config file > default`."

So **env-var and config-file backing of flags is a first-class spec feature**,
not something you implement.

---

## Q2 — Direction of generation: **clap → KDL, checked in, AND verified in CI**

Answer is **(b) + (c)**: emitted from clap definitions, committed to the repo,
and a CI job re-renders and asserts an empty diff. A small hand-authored
*extras* file is appended for what clap cannot express.

⚠️ **I got this wrong on the first pass and am correcting it.** My first probe
was `grep -rn 'usage.kdl' <repo>/.github/workflows` → 0 hits, and I concluded
"no CI drift check". The control arm I ran (`grep -rln 'cargo'` → 2 files)
proved the probe could *see the directory* but not that I had aimed at the right
token — the workflow invokes the task **by name** (`mise run render`), so the
filename never appears. Re-probing on `render` found the check in all three
repos. A control arm proves the probe can see; it does not prove you pointed it
at the right thing.

### The emitter — `jdx-fnox/src/commands/usage.rs:8-19`

```rust
impl UsageCommand {
    pub async fn run(&self, _cli: &Cli) -> Result<()> {
        use clap::CommandFactory;
        let cmd = Cli::command();
        let spec: usage::Spec = cmd.into();          // clap Command -> usage::Spec

        let min_version = r#"min_usage_version "1.3""#;
        let extra = include_str!("../assets/fnox-extras.usage.kdl").trim();

        println!("{min_version}\n{}\n{extra}", spec.to_string().trim());
        Ok(())
    }
}
```

`fnox usage` is a `#[command(hide = true)]` subcommand. The standalone-crate
equivalent for a CLI that doesn't want the `usage` crate as a dep is
`clap_usage::generate(&mut cmd, "example", &mut stdout)`
(`usage/clap_usage/README.md`).

### The regeneration task — `jdx-fnox/mise.toml:88-96`

```toml
[tasks."render:usage"]
description = "Generate CLI documentation from usage"
depends = ["build"]
run = [
  "fnox usage > fnox.usage.kdl",
  "rm -rf docs/cli && mkdir -p docs/cli",
  "usage g markdown -mf fnox.usage.kdl --out-dir docs/cli --url-prefix /cli",
  "usage g json -f fnox.usage.kdl > docs/cli/commands.json",
  "prettier --write docs/cli",
]
```

### The CI drift gate — identical in all three repos

`jdx-fnox/.github/workflows/ci.yml:298-305`, `jdx-hk/.github/workflows/ci.yml:219-226`,
`jdx-mise/.github/workflows/test.yml:247-256`:

```yaml
      - name: mise run render
        run: mise run render
      - name: assert render produces no diff
        run: |
          if [ -n "$(git status --porcelain)" ]; then
            echo "::error::'mise run render' produced changes. Run it locally and commit."
            git status
            git diff HEAD
            exit 1
```

mise's `render` chain (`jdx-mise/tasks.toml:64-96`) also renders man pages
(`usage generate manpage --file mise.usage.kdl > man/man1/mise.1`) and
completions off the same spec.

### The hand-authored half — small, and only what clap cannot say

| Repo | Generated spec | Hand-authored extras |
|---|---|---|
| fnox | `fnox.usage.kdl` — **275 lines**, 46 `cmd`, 71 `flag` | `src/assets/fnox-extras.usage.kdl` — **13 lines** |
| hk | `hk.usage.kdl` — **775 lines** | `src/hk-extras.usage.kdl` — **0 bytes** (empty) |
| mise | `mise.usage.kdl` — **5,457 lines** | `src/assets/mise-extra.usage.kdl` — **99 lines** (mostly a Tera template mapping command paths to source files for doc links) |

fnox's entire hand-written KDL:

```kdl
// Dynamic completions for fnox commands
complete "key" run="fnox list --complete 2>/dev/null || true"
complete "name" run="fnox provider list --complete 2>/dev/null || true"
complete "profile" run="fnox profiles --complete 2>/dev/null || true"
complete "config_file" type="file"
```

**That is the whole shape of the split: clap emits structure; you hand-write the
dynamic completion hooks and the safety/effect metadata clap cannot express.**

### mise shows the richer pattern — post-process the derived Spec in Rust

`jdx-mise/src/cli/usage.rs:18-63` mutates the `usage::Spec` after conversion:

```rust
pub fn spec() -> usage::Spec {
    let cli = Cli::command().version(Resettable::Reset);
    let mut spec: usage::Spec = cli.into();
    spec.default_subcommand = Some("run".to_string());          // `mise foo` completes like `mise run foo`
    if let Some(run) = spec.cmd.subcommands.get_mut("run") {
        run.args = vec![];
        run.mounts.push(usage::SpecMount::new("mise tasks --usage".to_string()));  // dynamic sub-spec
        run.restart_token = Some(":::".to_string());
    }
    crate::cli::command_effects::apply(&mut spec);              // read/write/destructive table
    spec
}
```

`SpecMount` is worth flagging for a secrets CLI: it **mounts a sub-spec produced
at completion time by another command**, so completions can cover things not
known at build time (mise uses it for task names; the analogue would be secret
keys or profiles).

`jdx-mise/src/cli/command_effects.rs:1-40` is a doc-comment worth reading
verbatim if a secrets CLI is going to expose an MCP surface:

> "**An unlisted command means "unknown", not "safe".** Consumers treat the
> absence of a value as "ask", so leaving a command out is the conservative
> choice and mislabeling one `read` is the dangerous one."

and the classification is kept as **one table** deliberately: *"a safety
classification is much easier to review as a single list than as annotations
scattered over sixty files."*

### Notable coupling: fnox's `completion` command shells out to `usage`

`jdx-fnox/src/commands/completion.rs:16-27` — `fnox completion <shell>` runs:

```
usage g completion <shell> fnox --usage-cmd "fnox usage" --cache-key <CARGO_PKG_VERSION>
```

fnox vendors no completion generation at all and **requires the `usage` binary
at runtime** for its own `completion` subcommand.

---

## Q3 — Usable from a NON-Rust CLI? **YES. Experiment run, all arms green.**

I hand-authored `vaultpy.usage.kdl` — a 30-line spec for a fictional Python
secrets CLI `usage` has never seen — and drove the real 4.1.0 binary against it.
Spec source: scratchpad `toy/vaultpy.usage.kdl` (3 subcommands, aliases, global
+ per-command flags, 2 `complete` hooks).

`usage lint` on it: `Found 0 error(s), 0 warning(s), 1 info(s)` (the info is
`missing-cmd-help` on the root), rc=0.

### 3a. Completions for all five shells, with no binary present

`command -v vaultpy` → **not found** at generation time.

```
$ usage g completion <sh> vaultpy -f vaultpy.usage.kdl
bash rc=0 1925B   zsh rc=0 2498B   fish rc=0 1577B   nu rc=0 1796B   powershell rc=0 1986B
```
Control arms on the zsh output: `grep -c 'vaultpy'` → **12**;
`grep -c 'quuxfrobnicate'` → **0**. The probe discriminates.

### 3b. The completion engine, exercised directly

| Arm | Command | Result |
|---|---|---|
| subcommands | `usage cw --shell zsh -f … -- vaultpy ''` | `g / get / list / ls / set`, each with help text |
| prefix filter | `… -- vaultpy 'l'` | only `list`, `ls` |
| **positional-aware** | `… -- vaultpy get '--'` | `--profile` (get's own) **+** `--verbose` (global); **not** `--json` (list's) |
| **dynamic hook, binary absent** | `… -- vaultpy get ''` | `sh: vaultpy: command not found` / `exited with code 127 · sh -c vaultpy list` — proves the hook really shells out |
| **dynamic hook, real Python binary** | same, after putting a 6-line `python3` `vaultpy` on `$PATH` | `db_password / api_token / ssh_key` — the Python program's own stdout |
| prefix-filtered dynamic | `… -- vaultpy get 'db'` | `db_password` only |
| negative arm | `… -- vaultpy get 'zzq'` | empty, rc=0 → discriminates |

The dynamic hook cost one line of KDL: `complete "KEY" run="vaultpy list"`.

### 3c. Docs / man / JSON / SDK off the same hand-authored spec

- `usage g markdown -mf vaultpy.usage.kdl --out-dir md` → `get.md`, `set.md`,
  `list.md`, `index.md` — each with Usage line, Aliases, Arguments, Flags. rc=0.
- `usage g manpage -f …` → valid roff (`.TH VAULTPY 1`, `.SH SYNOPSIS`, …).
- `usage g json -f …` → structured spec with `required`, `double_dash`, `hide`
  per arg.
- `usage g sdk -f … -l python -o sdk-py` → **4 files** (`client.py`, `types.py`,
  `runtime.py`, `__init__.py`), header `# @generated by usage-cli from
  vaultpy.usage.kdl. Do not edit manually.`:

```python
class Vaultpy:
    def __init__(self, bin_path: str = "vaultpy") -> None: ...
    @property
    def ls(self) -> List: """Alias for list."""
class Get:
    """Print a secret's value. Aliases: g"""
    def exec(self, args: GetArgs, flags: Optional[GetFlags] = None) -> CliResult:
```

It is a **subprocess wrapper**, stated as such in `docs/cli/sdk.md`: *"it invokes
your CLI binary via `subprocess.run` / `child_process.spawn`, not a native
binding."*

### 3d. Runtime parsing — the shebang model replaces argparse

`usage/examples/test-exec-help.py`, run against the real binary:

```python
#!/usr/bin/env -S usage exec python3
# USAGE bin "test-exec-help"
# USAGE flag "-f --force" help="Force the operation"
# USAGE arg "<file>" help="File to process"
import os

print(f"force: {os.environ.get('usage_force', '')}")
```

| Arm | Output |
|---|---|
| `usage exec python3 ./tp.py --force in.txt` | `force: true` / `verbose: ` / `file: in.txt`, rc=0 |
| `… --help` | full rendered help (Usage, Arguments, Flags), rc=0 |
| `… ` (missing required) | `Error: × Missing required arg: <file>`, **rc=1** |
| `… --nope x` | `Error: × unexpected word: x` |

Comment syntax by language: `#USAGE` (bash/python), `//USAGE` or `// [USAGE]`
(JS/Go-style) — `docs/cli/scripts.md`, `examples/test-usage-double-slash.js`.
Tab-completion for shebang scripts is **opt-in**: `source <(usage g
completion-init bash)` once in the rc file, then every usage-shebang script on
`$PATH` completes with no per-script step.

### Verdict on Q3

A Python CLI gets, from one hand-authored KDL file: 5-shell dynamic
completions, per-subcommand markdown docs, a man page, a JSON spec, a typed
Python/TypeScript SDK, an MCP describe-server, and — optionally — the entire
argument parser, `--help` renderer and validator. **The only cost is that the
`usage` binary must be installed on the end user's machine for completions to
function** (a `mise use usage` or a package dep; it is a single Rust binary).

### Non-Rust generators that exist upstream

`integrations/cobra` (Go) — `cobra_usage.Generate(rootCmd) string` converts a
Cobra tree to KDL, with the documented pattern of a `--usage-spec` flag checked
before `Execute()`, then `mycli --usage-spec | usage generate completion bash`
(`.agent/kb/raw/usage-cobra-integration.md`). There is **no Python/argparse or
click generator** — a Python CLI hand-authors the KDL or writes its own emitter.

---

## Q4 — Starter / template: **there is none**

Control-armed searches:

- `usage --help` lists 10 subcommands: `bash, complete-word, exec, fish,
  generate, lint, mcp, powershell, sponsors, zsh` — **no `init` / `new` /
  `scaffold`**.
- `usage generate --help` lists 7 generators: `completion, completion-init, fig,
  json, manpage, markdown, sdk` — **no `scaffold`**.
- `grep -rniE 'usage (init|new|scaffold)|scaffold|template repo|starter'` over the
  whole `jdx/usage` clone → **2 files**, and both hits are the *same aspirational
  bullet*: `README.md:11` and `docs/spec/index.md:13` — "Scaffold one spec into
  different CLI frameworks—even different languages". It is a listed *reason to
  adopt the spec*, not a shipped command. Control arm: `grep -rli 'completion'`
  over the same tree → **90 files**, so the probe sees plenty.
- No `templates/`, no `create-*` package, no `cargo generate` template in the repo.
  `docs/` contains only `spec/` (the format reference) and `cli/` (generated
  command reference) — the tutorial-shaped page is `docs/cli/scripts.md`, which
  is the shebang walkthrough, not a project starter.

**So the "start a new CLI" path is:** write the KDL by hand from
`docs/spec/index.md` (its two worked examples — a flat CLI and a nested-subcommand
CLI — are effectively the template), or generate it from an existing clap/cobra
tree. `usage lint` is the only scaffolding-adjacent affordance.

Docs site: **https://usage.jdx.dev** (VitePress, built from `docs/` — `docs.yml`
deploys to GitHub Pages). Sources persisted under `.agent/kb/raw/usage-*.md`.

---

## Q5 — Authoring cost, from the worked examples

| | fnox | hk | mise | my toy Python spec |
|---|---|---|---|---|
| Spec lines | 275 | 775 | 5,457 | 30 |
| Subcommands (`cmd`) | 46 | — | — | 3 |
| Flags | 71 | — | — | 4 |
| **Lines per subcommand (incl. its flags)** | **~6** | — | — | **~8** |
| Hand-authored KDL | 13 lines | 0 bytes | 99 lines | **all 30** |

Read the shape from `fnox.usage.kdl` — a subcommand with an alias, a flag and a
positional is 5 lines:

```kdl
cmd exec help="Execute a command with secrets as environment variables" {
    alias x
    flag --replace help="Run the command in fnox's process, keeping the same PID…"
    arg "[COMMAND]…" help="Command to run" required=#false double_dash=automatic var=#true
}
```

**What ~6 lines/subcommand buys:** completions in 5 shells that are dynamic and
positional-aware, a per-command markdown docs site, a man page, a JSON spec, a
typed SDK in 2 languages, a Fig spec, an MCP describe-server with read/write/
destructive safety metadata, and (if you want it) the parser itself. For a Rust
CLI on clap the marginal authoring cost is **near zero** — the 275 lines are
generated; you write ~13.

## Caveats to carry into a decision

1. **`usage` must be installed at runtime** for completions to work on the end
   user's machine — the generated scripts hard-fail with an explicit error if
   it is missing. For a Rust CLI you can avoid this by vendoring the `usage`
   crate, but fnox chose to shell out.
2. **The Rust SDK target is documented but not in 4.1.0.** Only `typescript`
   and `python`.
3. **`usage mcp` describes, it does not execute** — 2 read-only tools. An agent
   still runs the CLI itself.
4. **The generated spec must be committed and gated** — all three jdx repos use
   the same `mise run render` + `git status --porcelain` assert-no-diff CI step.
   Without it the checked-in KDL silently rots away from clap.
5. **Issues are disabled on `jdx/fnox`**, so the absence of upstream complaints
   about any of this is absence of a venue, not absence of a problem. `jdx/usage`
   does have issues open (PR numbers up to #753 in the 4.1.0 changelog).

---

## GitHub repos touched

- [jdx/usage](https://github.com/jdx/usage) — the subject: shallow-cloned, read README/docs/examples/`clap_usage`/`integrations/cobra`, and exercised the local 4.1.0 binary against a hand-written toy spec.
- [jdx/fnox](https://github.com/jdx/fnox) — shallow-cloned for `fnox.usage.kdl`, `src/commands/usage.rs`, `src/commands/completion.rs`, `src/assets/fnox-extras.usage.kdl`, `mise.toml`, `.github/workflows/ci.yml`.
- [jdx/mise](https://github.com/jdx/mise) — read `src/cli/usage.rs`, `src/cli/command_effects.rs`, `mise.usage.kdl`, `tasks.toml`, `.github/workflows/test.yml` for the richest post-processing + CI-drift-gate example.
- [jdx/hk](https://github.com/jdx/hk) — read `hk.usage.kdl`, `src/hk-extras.usage.kdl`, `src/cli/usage.rs`, `.github/workflows/ci.yml` as the third instance of the same pattern.
- [spf13/cobra](https://github.com/spf13/cobra) — named as the Go CLI framework the `integrations/cobra` generator converts from (docs read, repo not cloned).
- [scop/bash-completion](https://github.com/scop/bash-completion) — referenced by `usage g completion --include-bash-completion-lib` as a prerequisite for bash completions.
- [kdl-org/kdl](https://kdl.dev) — the spec's document language (docs reference only).
