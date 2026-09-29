[Skip to content](https://mise.jdx.dev/#VPContent)

# mise-en-place

Development tools, environments, and tasks

mise is pronounced **“meez”**

Define your tool versions, environment variables, and project commands in `mise.toml`. mise installs the tools and makes the configuration available in your shell, editor, and CI.

[Get started →](https://mise.jdx.dev/getting-started) [Watch the demo](https://mise.jdx.dev/demo)

$`curl https://mise.run | sh`Copy

macOS & Linux · [Installing on Windows?](https://mise.jdx.dev/getting-started#installing-mise-cli)

≡ mise.tomlExample configuration

ToolsEnvironmentsTasksBootstrap

\# Tool versions for this project

```
[tools]
node = "24"
python = "3.13"
terraform = "1.13"
```

Illustrative output ~/my-project

```
$ mise install
✓ node, python, terraform installed
Tool versions ready for this project.
```

[Explore tools ↗](https://mise.jdx.dev/dev-tools/)

Project configuration in mise.toml

- Open source & MIT licensed
- macOS, Linux & Windows
- Single CLI

## What mise manages

[$ mise use node@24\\
**Dev tools**\\
Install hundreds of tools, select versions per project, and switch automatically as you move between directories. \\
Dev tools](https://mise.jdx.dev/dev-tools/) [$ mise env\\
**Environments**\\
Load project environment variables from `mise.toml`, .env files, secrets, and shell commands when you enter a directory. \\
Environments](https://mise.jdx.dev/environments/) [$ mise run test\\
**Tasks**\\
Build, test, lint, and deploy commands defined next to the tools and env they need, with dependencies and parallel runs. \\
Tasks](https://mise.jdx.dev/tasks/) [$ mise bootstrap\\
**Bootstrap**\\
Apply the machine setup you declare: OS packages, dotfiles, repos, services, macOS defaults, and development tools. \\
Bootstrap](https://mise.jdx.dev/bootstrap)

Coming from asdf? Your `.tool-versions` already works. [Enable files like .nvmrc, too](https://mise.jdx.dev/configuration.html#idiomatic-version-files).

## Switch between project environments

Activate mise in your shell once. From then on, entering a project puts its installed tool versions on your `PATH` and loads its environment variables. Leave the project and mise restores the environment for your new directory.

- Shell hooks for bash, zsh, fish, nushell, PowerShell, and more
- Shims for editors and scripts that never source your shell rc
- `mise exec` and `mise-action` for Docker and CI

api/mise.toml`[tools]
node = "22"

[env]
APP_ENV = "api"`$ cd ~/work/apidashboard/mise.toml`[tools]
node = "24"

[env]
APP_ENV = "dashboard"`$ cd ~/work/dashboard

↓

Active shell~/work/api

Node22

APP\_ENVapi

Choose a project to see its environment. Shell activation and installed tool versions are required.

Declare your setup **mise.toml**`[bootstrap.packages]
[bootstrap.repos]
[dotfiles]
[bootstrap.services]`

↓`mise bootstrap`

**Packages** brew · apt · scoop · winget

**Repositories** Project checkouts

**Dotfiles** Link · copy · template

**Services** Background processes

`mise bootstrap plan` previews declarative resource changes before you apply them.

## Set up a machine with mise bootstrap

Declare the packages, repositories, dotfiles, and services your machine needs, then apply them with `mise bootstrap`. Preview declarative resource changes with `mise bootstrap plan`. Add shell activation and platform-specific settings to keep machine setup alongside your tools.

- Packages through brew, apt, dnf, pacman, apk, mas, scoop, and winget
- Dotfiles as symlinks, copies, or templates, plus single-line edits
- Remote hosts over SSH with `mise bootstrap remote`

`mise bootstrap --from git@github.com:you/dotfiles.git`

[Read the bootstrap guide](https://mise.jdx.dev/bootstrap)

— Tool registry

1000+tools in the registry, from node to terraform

[node](https://mise-versions.jdx.dev/tools/node) [python](https://mise-versions.jdx.dev/tools/python) [ruby](https://mise-versions.jdx.dev/tools/ruby) [go](https://mise-versions.jdx.dev/tools/go) [rust](https://mise-versions.jdx.dev/tools/rust) [java](https://mise-versions.jdx.dev/tools/java) [deno](https://mise-versions.jdx.dev/tools/deno) [bun](https://mise-versions.jdx.dev/tools/bun) [terraform](https://mise-versions.jdx.dev/tools/terraform) [kubectl](https://mise-versions.jdx.dev/tools/kubectl) [zig](https://mise-versions.jdx.dev/tools/zig) [swift](https://mise-versions.jdx.dev/tools/swift) [php](https://mise-versions.jdx.dev/tools/php) [elixir](https://mise-versions.jdx.dev/tools/elixir) [erlang](https://mise-versions.jdx.dev/tools/erlang) [dotnet](https://mise-versions.jdx.dev/tools/dotnet) [pnpm](https://mise-versions.jdx.dev/tools/pnpm) [uv](https://mise-versions.jdx.dev/tools/uv) [awscli](https://mise-versions.jdx.dev/tools/awscli) [gh](https://mise-versions.jdx.dev/tools/gh) [jq](https://mise-versions.jdx.dev/tools/jq) [ripgrep](https://mise-versions.jdx.dev/tools/ripgrep) [browse the registry](https://mise.jdx.dev/registry)

Sourced from [aqua](https://mise.jdx.dev/dev-tools/backends/aqua), [GitHub releases](https://mise.jdx.dev/dev-tools/backends/github), [cargo](https://mise.jdx.dev/dev-tools/backends/cargo), [npm](https://mise.jdx.dev/dev-tools/backends/npm), [pipx](https://mise.jdx.dev/dev-tools/backends/pipx), [go](https://mise.jdx.dev/dev-tools/backends/go), [gem](https://mise.jdx.dev/dev-tools/backends/gem), [http](https://mise.jdx.dev/dev-tools/backends/http), [asdf](https://mise.jdx.dev/dev-tools/backends/asdf), [vfox](https://mise.jdx.dev/dev-tools/backends/vfox), and [more](https://mise.jdx.dev/dev-tools/backends/).

[— Related project\\
\\
**Share Cargo builds with Mr Boxington** \\
\\
Give every Cargo checkout one shared, self-pruning compilation cache, locally and in CI.\\
\\
mr-boxington.jdx.dev](https://mr-boxington.jdx.dev/)

## Run your first project task

1. Step 1

### Install mise



On macOS or Linux, use the installer below. See [Windows and package manager instructions](https://mise.jdx.dev/installing-mise) for other options.





$ curl https://mise.run \| sh



$ ~/.local/bin/mise --version

2. Step 2

### Activate your shell



For zsh, add this line and restart your shell. Follow the [activation guide](https://mise.jdx.dev/getting-started#activate-mise) for other shells. You can also skip activation and use `~/.local/bin/mise exec` or `~/.local/bin/mise run`.





$ echo 'eval "$(~/.local/bin/mise activate zsh)"' >> ~/.zshrc



\# Restart your shell before continuing.

3. Step 3

### Add tools



From your project directory, `mise use` installs a tool and saves its version request in `mise.toml`.





$ mkdir mise-example



$ cd mise-example



$ mise use node@24

4. Step 4

### Add env vars and tasks



Save a task alongside its environment, then run it. Commit `mise.toml` to share the setup. See [the complete example](https://mise.jdx.dev/getting-started#set-up-a-project) to print both the tool version and environment.





$ mise set NODE\_ENV=development



$ mise tasks add hello -- node -p process.env.NODE\_ENV



$ mise run hello



development


— Ready when you are

## _Allez._ Prep your station.

`curl https://mise.run | sh`

[Getting started](https://mise.jdx.dev/getting-started) [Watch the demo](https://mise.jdx.dev/demo) [GitHub](https://github.com/jdx/mise)

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)