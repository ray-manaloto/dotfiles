# Review result

The three questions have different answers:

- **Q1:** No. Anthropic’s native installer has no documented system-prefix, destination, multi-user, or all-users mode.
- **Q2:** Yes. `mise install --system` is specifically documented for devcontainers with mounted home directories and installs outside the home.
- **Q3:** A mise task can invoke Anthropic’s installer, but no single mise declaration can make that installer perform a supported system-level installation. A `[tools]` declaration can instead install the native executable under mise ownership.

Implementation is presently blocked by licensed dissent: the repository already uses the mount-proof mise mechanism, while its doctor policy still requires native-installer ownership.

## Material specification corrections

1. **The masking consequence is overstated.**

   The home volume does cover the whole runtime home at [devcontainer.json:129](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.devcontainer/devcontainer.json:129), not the spec’s cited line 119. But because the mount lacks `volume-nocopy`:

   - A fresh empty volume receives the image’s existing home contents.
   - An existing non-empty volume obscures the image contents.
   - Later image rebuilds do not update the persisted copy.

   Therefore the real risk is existing-volume and image-upgrade behavior, not unconditional absence on first creation. [Docker documents both arms explicitly.](https://docs.docker.com/engine/storage/volumes/)

2. **The stated consequence is not the current repository state.**

   Claude is already declared in [mise-runtime.toml:63](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.devcontainer/mise-runtime.toml:63), installed with `mise install --system --locked` in [Dockerfile:683](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.devcontainer/Dockerfile:683), and exposed through system shims configured at [Dockerfile:74](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.devcontainer/Dockerfile:74). That installation is outside the mounted home.

3. **The ownership rules contradict that implementation.**

   [doctor.toml:264](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/doctor.toml:264) requires `expected_install_method = "native"`. The checker explicitly treats a mise-provided Claude as `package-manager` in [claude_doctor.py:94](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/claude_doctor.py:94) and advises reinstalling natively at [claude_doctor.py:316](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/claude_doctor.py:316).

4. **The backend comments are stale.**

   [mise-runtime.toml:59](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.devcontainer/mise-runtime.toml:59) says `http:claude`, but [mise-runtime.lock:583](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.devcontainer/mise-runtime.lock:583) records `aqua:anthropics/claude-code`. Current `mise registry` maps both `claude` and `claude-code` to the same Aqua/HTTP candidates, so the spec’s “`claude`, NOT `claude-code`” statement is false on tested mise 2026.9.9.

5. **The spec omits Anthropic’s supported system installation.**

   Anthropic now publishes signed apt, dnf, and apk repositories. These are system-level installations, but they are package-manager—not native-installer—owned, and upgrades occur through the OS package manager rather than Claude’s background updater. [Anthropic setup documentation](https://code.claude.com/docs/en/setup)

6. **The two postinstall mechanisms must be separated.**

   The excluded fail-open `[hooks].postinstall` is not the same mechanism as `[tools].<tool>.postinstall`. The latter propagates errors in the pinned source, but it remains unsuitable: it runs only when its containing mise tool installs and cannot change Anthropic’s installer destination. [Pinned mise source](https://github.com/jdx/mise/blob/v2026.9.8/src/backend/mod.rs#L3262-L3266)

## Q1 — Native installer system placement

**Verdict: no supported mechanism found.**

Live Claude Code 2.1.273 reports:

```text
Usage: claude install [options] [target]
Options:
  --force
  -h, --help
```

The target is a version or release channel, not a filesystem destination. Anthropic documents the native launcher as `~/.local/bin/claude`, pointing into `~/.local/share/claude/versions/`. It also documents that replacing the managed launcher with a custom script or symlink causes `/doctor` to report it and leaves launcher selection outside the updater’s control. [Installation and update behavior](https://code.claude.com/docs/en/setup)

Root is not categorically refused: Anthropic documents Docker installation as root, with `WORKDIR /tmp` to prevent a scan of `/` from hanging. That does not create a shared installation; by inference, it remains a per-user installation under root’s home. [Docker installation troubleshooting](https://code.claude.com/docs/en/troubleshoot-install)

Unsupported candidates and consequences:

- Spoofing `HOME`: undocumented; the runtime user’s actual home differs during self-update.
- Copying the binary to `/usr/local/bin`: not installer-managed.
- Adding a system symlink: treated as a custom launcher; updater does not manage it.
- Running as root: installs for root rather than the UID-1000 developer.
- apt/dnf/apk: supported and system-wide, but a separate package-manager installation without native background updates.

Exact `/doctor` output for an invented system-native layout remains unverified because creating one would violate review mode.

**Control arms:**

- `--force` present in `claude install --help`: direct `rc=0`.
- Fresh invented `--install-prefix-q18-z7m4`: direct `rc=1`.
- Official-corpus search for `DISABLE_AUTOUPDATER` and `bash -s stable`: `rc=0`.
- Fresh invented installer-prefix tokens: `rc=1`.

## Q2 — Mise mechanisms

| Mechanism | Verdict | Consequence |
|---|---|---|
| `mise install --system` | **Yes; direct answer** | Installs under `/usr/local/share/mise/installs`, outside home; mise owns updates |
| `MISE_SYSTEM_DATA_DIR` / `system_installs_dir` | **Yes** | Relocates the system installation root |
| `--shared` / `mise install-into` | Technically yes | Imperative destination selection, not a per-tool config declaration |
| `[dotfiles]` / `mise dot` | No | Manages files and dotfile history, not tool installation |
| `[bootstrap.services]` | No | Manages services or existing system units |
| `[bootstrap.packages]` | Yes, through apt/dnf/apk | First-party system package route; requires repository/key and package updates |
| `mise oci` | Technically yes | Experimental; builds another OCI image and conflicts with the established Bake architecture |
| External-binary requirement | No general declaration | PATH can satisfy some backend dependencies, but this is not a primary-tool ownership or repair contract |

The exact upstream cookbook says to use `mise install --system` when a devcontainer mounts its home, because normal user installations are hidden while `/usr/local/share/mise/installs` survives. [Mise Docker cookbook](https://mise.jdx.dev/mise-cookbook/docker.html#devcontainers-with-home-directory-mounts)

The repository already follows this shape. Its current lock resolves Claude 2.1.270 from Anthropic’s GitHub release assets through Aqua.

One remaining runtime risk is shadowing: [Dockerfile.host-user:77](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.devcontainer/Dockerfile.host-user:77) places `~/.local/bin` before the system mise shims. An old launcher persisted in the home volume can therefore shadow the baked installation. The current bare-image check at [image.py:1042](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/image.py:1042) cannot detect that.

**Control arms:**

- `mise install --help` contains `--system` and `/usr/local/share/mise/installs`: `rc=0`.
- Fresh invented `--home-survivor-q18-z7m4`: `rc=1`.
- `mise registry claude-code`: `rc=0`, Aqua and HTTP candidates.
- Fresh nonexistent registry key: `rc=1`.
- Existing runtime config key: `rc=0`, value `latest`.
- Fresh nonexistent config key: `rc=1`.

## Q3 — Can mise config drive the native installer?

**Qualified answer:**

- A `[tools]` entry does not directly execute an arbitrary vendor installer. HTTP, Aqua, and GitHub backends download and install artifacts; custom vfox/asdf plugins can implement logic but require separate plugin code and make mise the manager. [Mise backend model](https://mise.jdx.dev/dev-tools/backends/)
- A mise task can explicitly invoke a Python helper or Anthropic installer from a Dockerfile using `RUN mise run <task>`. This is supported task behavior. [Mise tasks](https://mise.jdx.dev/tasks/)
- That task does not alter the native installer’s documented `~/.local` destination.

Therefore:

- **One declaration can install Anthropic’s native executable outside home under mise ownership.**
- **No one-declaration shape makes Anthropic’s native installer perform a supported system installation.**

## Recommendation

Keep Q18—Claude baked into the image—but ratify a scoped ownership rule:

> Native installer owns Claude on the macOS host; mise/package-manager owns Claude inside the devcontainer.

Then retain the existing `mise install --system --locked` image route, explicitly reconcile the selected Aqua/HTTP backend, make the doctor expectation container-aware, remove the stale comments, and add an after-mount runtime ownership assertion.

This is preferable to introducing apt immediately because the system-mise route already exists, is lockfile-backed, lives in the thin runtime stage, and is the exact solution recommended by mise for mounted-home devcontainers.

Costs:

- No Claude-managed background self-update inside the container; upgrades require lock refresh and image rebuild.
- The doctor contract must distinguish host from devcontainer.
- Existing volumes may contain a shadowing `~/.local/bin/claude` that needs an explicit migration or rejection.
- Aqua/mise becomes part of the installation trust chain.

If native-installer ownership must also remain binding inside the container, the requirements are incompatible: no supported system target exists, and a post-mount repair becomes unavoidable.

## Required integration test

Use an isolated disposable home volume:

1. Pre-populate it without Claude, mount it over the entire user home, and start the actual devcontainer image.
2. Assert that `claude` executes and its resolved path is under the intended system installation, not `$HOME`.
3. Assert the expected version and installation method.
4. Mutation arm: build the fixture without `mise install --system`; the test must fail.
5. Shadow arm: add a stale executable at `~/.local/bin/claude`; the ownership assertion must fail even if `command -v claude` succeeds.

This closes the current false-pass class where the bare image has a `claude` command but the mounted developer environment resolves something else.

## Review execution

No repository gates, installer commands, checkout writes, reports, commits, or configuration mutations were performed. The mandatory Graphify query was attempted first and returned direct `rc=1` because the read-only sandbox blocked mise’s log/temp writes; targeted source inspection followed. Some subsequent mise inspection commands emitted the same sandbox warnings, but their direct return codes were captured.

All three initial history-bearing specialist spawn attempts failed with `no thread with id`. Each was retried exactly once without conversation history and succeeded.

### Specialists spawned:

- `sdlc-image-specialist` — `/root/native_installer_image_review`
- `sdlc-config-specialist` — `/root/native_installer_mise_review`
- `sdlc-documentation-specialist` — `/root/native_installer_docs_review`
- No other specialists were spawned.

