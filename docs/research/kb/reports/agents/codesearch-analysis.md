## Verdict

The smallest correct design is one Python installer command plus thin, explicit lifecycle callers. Do **not** add required Claude provisioning to root `[hooks].postinstall`: mise hook failures are warning-only, CI invokes installation in multiple phases, and the devcontainer ignores root `mise.toml`.

There is licensed dissent against the current checkout:

- The ruling says the native installer is Claude’s sole owner, but the devcontainer still declares `claude-code = "latest"` through mise and locks version `2.1.270` ([mise-runtime.toml](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.devcontainer/mise-runtime.toml:58), [mise-runtime.lock](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.devcontainer/mise-runtime.lock:583)).
- The authoritative bootstrap version is `2.1.272`, explicitly with no mise pin ([sources.toml](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/schemas/sources.toml:48)).
- `validate_plugin()` claims native ownership but still asks `mise exec` to resolve `github:anthropics/claude-code` ([fnhook_gates.py](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/fnhook_gates.py:56), [validation call](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/fnhook_gates.py:233)).
- Image smoke currently requires `claude` in the built image, which conflicts with per-user installation after container creation ([image.py](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/image.py:1042)).

A root-only `mise.toml` change therefore cannot satisfy the devcontainer requirement.

## Twelve-repository evidence

The corpus contains 12 search hits: **9 executable installer excerpts and 3 comment-only matches**. Of the 9 executable examples, 7 guard installation and 2 run unconditionally. None installs an exact version; one explicitly requests `latest`, while eight omit the argument and therefore receive the documented default, `latest` ([Anthropic’s cached setup documentation](/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/agent-harness-docs/docs/claude-code/setup.md:291)).

| Repository | Visible mechanism | Version | Idempotency | Visible invocation |
|---|---|---|---|---|
| `bellini666/dotfiles` | Inline shell; update if found, install otherwise ([excerpt](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/docs/research/kb/reports/agents/codesearch-mise-claude-installer.md:2)) | Default/latest | Installation guarded, but every rerun updates | Enclosing caller omitted |
| `naa0yama/devtool-wsl2` | Inline Bash with Linux/Darwin check ([excerpt](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/docs/research/kb/reports/agents/codesearch-mise-claude-installer.md:17)) | Default/latest | Unconditional | Enclosing caller omitted |
| `hiramekun/dotfiles` | Named `[tasks.agents]` run array ([excerpt](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/docs/research/kb/reports/agents/codesearch-mise-claude-installer.md:29)) | Default/latest | Unconditional | Manually callable task; no caller shown |
| `kjgarza/snowyowl` | Two `command -v` guarded bodies; one named task ([excerpt](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/docs/research/kb/reports/agents/codesearch-mise-claude-installer.md:44)) | Default/latest | Presence-idempotent against any PATH Claude | Named task shown; no caller shown |
| `carljohan/dotfiles` | Canonical native-path guard plus postcheck ([excerpt](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/docs/research/kb/reports/agents/codesearch-mise-claude-installer.md:72)) | Explicit `latest` | Presence-idempotent | Task heading/caller omitted |
| `advaypakhale/dotfiles` | Named one-line task; same guard idiom as its tmux task ([excerpt](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/docs/research/kb/reports/agents/codesearch-mise-claude-installer.md:87)) | Default/latest | Presence-idempotent at native path | Manually callable task; no caller shown |
| `ericboehs/dotfiles` | Runs native `--version`; reinstalls if missing/broken ([excerpt](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/docs/research/kb/reports/agents/codesearch-mise-claude-installer.md:102)) | Default/latest | Health-idempotent | Enclosing caller omitted |
| `RickDavis404/ai-infra-platform` | Comments describe a pinned npm wrapper and `npm_args` ([excerpt](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/docs/research/kb/reports/agents/codesearch-mise-claude-installer.md:114)) | Pin claimed, but declaration/version absent | Unproven | No executable wiring shown |
| `pagerguild/guilde-lite` | Commented curl instruction only ([excerpt](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/docs/research/kb/reports/agents/codesearch-mise-claude-installer.md:129)) | Default/latest example | N/A | Nothing active |
| `abnoumaru/dotfiles` | Inline `command -v` guard ([excerpt](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/docs/research/kb/reports/agents/codesearch-mise-claude-installer.md:144)) | Default/latest | Presence-idempotent against any PATH Claude | Task heading/caller omitted |
| `jalevin/dotfiles` | Inline `command -v` guard ([excerpt](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/docs/research/kb/reports/agents/codesearch-mise-claude-installer.md:159)) | Default/latest | Presence-idempotent against any PATH Claude | Task heading/caller omitted |
| `jtsoi/dotfiles` | Historical comment; current config says install CLI by hand ([excerpt](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/docs/research/kb/reports/agents/codesearch-mise-claude-installer.md:174)) | Unspecified | N/A | Human/manual |

No excerpt proves a `depends` or hook caller. No excerpt shows an external shell script invoked by a task; the shebangs are inside TOML multiline strings. The npm-wrapper classification is also comment-only evidence.

The search control—12 precise matches versus 22,528 for the broad query—shows that the query discriminates, but it does not establish completeness across private repositories, forks, or GitHub indexing gaps.

## Recommended wiring

Add one canonical task:

```toml
[tasks.claude-install]
description = "Install pinned native Claude Code when absent"
run = "uv run --project python dotfiles-setup claude-install"
```

The Python command should:

1. Reuse `schema_vendor.load_sources()` and require exactly one `claude-code` entry.
2. Define presence as an executable `$HOME/.local/bin/claude`, rather than any `claude` on `PATH`.
3. Return immediately when that executable exists, regardless of version. The exact pin is the initial bootstrap version; the native updater owns steady-state currency.
4. When absent, fetch the installer with a bounded command whose return code is checked independently.
5. pass the fetched bytes to `bash -s 2.1.272`, obtaining the version from `schemas/sources.toml`.
6. Check the Bash return code, then verify that the canonical executable exists and reports `2.1.272` immediately after installation.
7. Fail on missing or duplicate pins, download failure, installer failure, missing output, or an incorrect newly installed version.

Downloading and invoking Bash as two checked subprocesses avoids the masked downloader status of a raw `curl | bash` pipeline. Anthropic documents both the canonical native path and exact-version syntax ([setup documentation](/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/agent-harness-docs/docs/claude-code/setup.md:205), [exact version form](/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/agent-harness-docs/docs/claude-code/setup.md:339)).

Invoke it explicitly:

- **macOS host:** after `mise install`, through `mise run claude-install` or a fail-closed canonical setup task.
- **GitHub Actions:** after the second/full setup-mise phase in every job that invokes the Claude gate. Do not rely on `postinstall`; setup-mise has two installation phases ([action.yml](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.github/actions/setup-mise/action.yml:24)), and hook failure does not reliably fail provisioning.
- **Devcontainer:** remove the mise declaration and lock entry, then call the same Python helper from `on-create.sh` after home ownership repair. Root config is ignored inside the container ([devcontainer.json](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.devcontainer/devcontainer.json:164)), and installing during image build would be hidden by the mounted user home. The container already puts `~/.local/bin` first ([Dockerfile.host-user](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.devcontainer/Dockerfile.host-user:68)).

Keep the existing root `postinstall = "mise reshim && hk install --mise"` unchanged. A presence test alone is thin shell logic, as the community examples demonstrate. Pin lookup, downloading, failure propagation, installation, and verification together form non-trivial orchestration and belong in Python under the repo’s [zero-bash rule](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/rules/zero-bash-logic.md:1).

Finally, make `validate_plugin()` execute the canonical native binary directly and fail when it is absent. Installation must stay outside the read-only validation gate.

## Required verification for implementation

| Assertion | Positive arm | Reversion/failure arm |
|---|---|---|
| Exact bootstrap pin | Isolated temporary home installs fixture pin `9.8.7` | Dropping the `bash -s 9.8.7` argument produces a different version and fails |
| Absence-only behavior | Missing canonical path invokes installer once | Existing executable at another version remains byte- and mtime-identical; installer must not run |
| PATH ownership | A competing PATH `claude` does not suppress native installation | Replacing the canonical-path test with `command -v` fails |
| PATH independence | Native executable off PATH still skips installation | A PATH-based implementation attempts a second install and fails |
| False-success rejection | Successful installer creates executable and correct version | Installer returns zero but creates nothing; command returns nonzero |
| Pin integrity | Exactly one schema row permits installation | Missing or duplicate Claude rows fail before network access |
| Gate ownership | `validate_plugin()` invokes the absolute native path | A fake PATH or mise Claude is never selected |
| CI topology | Public workflow invokes the installer after tool setup | Removing that step fails a topology assertion |
| Container topology | Public on-create lifecycle invokes the helper as the runtime user | Restoring the runtime mise declaration or deleting the lifecycle call fails |

A real integration pass should then exercise the public entrypoint with isolated homes on macOS, an Ubuntu Actions runner, and the devcontainer. Rerunning with network unavailable after the first successful installation is a useful control: it proves the presence arm truly avoids the installer.

No repository gates ran. Graphify query and health were attempted as required; both returned direct `rc=1` because the read-only sandbox prevented mise from creating its temporary directory, so the review used the rule-authorized targeted source fallback.

An untracked `docs/research/kb/reports/agents/mise-lifecycle-research.md` appeared during delegated work despite the report-only instruction. Removal via `rm` returned `rc=1`, and the patch fallback was rejected because the sandbox is read-only. It remains alongside the two pre-existing checkout changes; no tracked source file was modified by this review.

Spawn failures were fully accounted for: the initial configuration, documentation, and Python spawns each failed once with `no thread with id` and succeeded on the required history-free retry. My direct workflow spawn then hit the root thread limit, so the configuration specialist spawned it. Its workflow and image child spawns also each hit `no thread with id` once and succeeded on their single history-free retries.

Specialists spawned:

- `sdlc-config-specialist` — `/root/config_review`
- `sdlc-documentation-specialist` — `/root/docs_review`
- `sdlc-python-specialist` — `/root/python_review`
- `sdlc-workflows-specialist` — `/root/config_review/gha_postinstall_review`
- `sdlc-image-specialist` — `/root/config_review/devcontainer_claude_review`
- No other specialists were spawned.

