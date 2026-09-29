[Skip to content](https://mise.jdx.dev/demo.html#VPContent)

On this page

# Demo [​](https://mise.jdx.dev/demo.html\#demo)

The following demo shows:

- how to use `mise exec` to run a command with a specific version of a tool
- how to use `mise` to install many other tools, such as `jq`, `terraform`, or `go`
- how to use `mise` to manage multiple versions of `node` on the same system

## Guided transcript [​](https://mise.jdx.dev/demo.html\#transcript)

This follows the recording's workflow. Commands and release requests below are kept usable for current mise; exact versions, paths, and output in the recording may differ. To follow along, [install mise](https://mise.jdx.dev/installing-mise.html) and use a Bash shell. The demo changes global tool defaults; use a scratch environment if you do not want those selections in your normal config.

### Run one command [​](https://mise.jdx.dev/demo.html\#run-one-command)

sh

```
mise exec node@26 -- node --version
mise exec terraform -- terraform version
```

`mise exec` installs a missing tool and makes it available to that child command. It does not select the tool for the calling shell or save it in `mise.toml`. A subsequent plain `node --version` uses whatever Node.js was already on the shell's PATH, if any.

### Activate and choose global defaults [​](https://mise.jdx.dev/demo.html\#activate-and-choose-global-defaults)

bash

```
eval "$(mise activate bash)"
mise use --global node@lts
node --version
which node
```

After the prompt updates, activation puts the selected Node.js installation on PATH. `lts` is a release request resolved by the Node.js backend, so its exact version changes over time. `which node` shows the executable chosen by this shell; with PATH activation, that is normally the real installed binary.

Add other global tools and inspect their selection:

sh

```
mise use --global terraform jq go
terraform version
jq --version
go version
mise ls --current
```

### Override defaults in a project [​](https://mise.jdx.dev/demo.html\#override-defaults-in-a-project)

sh

```
mkdir myproj
cd myproj
mise use node@26 pnpm@10
node --version
pnpm --version
cat mise.toml
```

The project config contains:

toml

```
[tools]
node = "26"
pnpm = "10"
```

Within this project, Node.js 26 overrides the global `lts` request. Leave the project and wait for the next shell prompt to restore the global selection:

sh

```
cd ..
node --version
mise ls --current
```

For a first project with tools, environment variables, and tasks, continue with [getting started](https://mise.jdx.dev/getting-started.html). For configuration overrides and upgrades, use the [walkthrough](https://mise.jdx.dev/walkthrough.html).

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)