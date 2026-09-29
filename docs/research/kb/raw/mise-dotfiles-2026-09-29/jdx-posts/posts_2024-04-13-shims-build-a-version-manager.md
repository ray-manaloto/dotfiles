[Skip to content](https://jdx.dev/posts/2024-04-13-shims-build-a-version-manager/#main)

On this page

I’ve spent the last decade of my career in the developer productivity space. In that time
I’ve helped countless developers setup their dev environments. Something I see time and
time again are developers struggling with version managers for their programming languages.

These tools are generally fine, but developers often don’t understand how they work which
leads to frustration trying to get it to do what they want. In this article, we’ll build
our own mini-version manager from scratch and along the way you’ll get an idea of how they
work under the hood.

## Version Managers [\#](https://jdx.dev/posts/2024-04-13-shims-build-a-version-manager/\#version-managers)

Most developers use some kind of version manager to help select which version of a language
to use when working on different projects. Pretty much every language has a set of these tools
like nvm for node, or pyenv for python. There are also polyglot tools like [mise-en-place](https://mise.jdx.dev/) or asdf that support multiple languages.

These tools usually use shims in order to function. In this article, we’ll build our own version manager
for node from scratch to understand how shims work.

## What is a shim? [\#](https://jdx.dev/posts/2024-04-13-shims-build-a-version-manager/\#what-is-a-shim)

Shims are a generic programming concept that [Wikipedia](https://en.wikipedia.org/wiki/Shim_%28computing%29) defines as:

> In computer programming, a shim is a library that transparently intercepts API calls and changes the arguments
> passed, handles the operation itself or redirects the operation elsewhere.

However when _I_ am talking about shims, I’m using a narrower definition and referring
to shims in the context of CLIs. These are used to intercept calls to things like `python`
or `node` and change the behavior in some way like selecting a particular version of python/node.

They behave as if you were talking to the real `python` or `node`, but they aren’t. They’re a proxy to the real thing.
This is why it can be a tricky concept. You often don’t see them and generally pretend they do not exist.
It’s when things stop working correctly that problems arise. And software being software, this happens
with a decent amount of frequency.

In general, these articles will focus on shims used for programming language tools like `python` and `node`,
because that’s where the problems arise most frequently but it’s far from the only place you’ll encounter
shims. Pretty much any CLI tool you install (such as with `npm install -g`) will
be using some-or often several-shims when you execute them.

## The Developer’s Experience [\#](https://jdx.dev/posts/2024-04-13-shims-build-a-version-manager/\#the-developers-experience)

When we’re done, we’ll have a version manager that can switch between different versions
when inside of different directories like the following:

```bash
$ cd ~/src/proj1
$ node -v
20.0.0
$ cd ~/src/proj2
$ node -v
18.0.0
```

This will make use of a file in the root of each project called `.node-version` which species
the version of node that should be used. This will be done in phases building up to this end state.

## Fetching our nodes [\#](https://jdx.dev/posts/2024-04-13-shims-build-a-version-manager/\#fetching-our-nodes)

First we need to do a bit of setup. We’ll install the node versions into `~/.nodes/`
which our version manager will expect to find them in. To do this, we’ll need to
first install [`node-build`](https://github.com/nodenv/node-build) and use
it to install our node versions:

```bash
$ node-build 18.0.0 ~/.nodes/18.0.0
$ node-build 20.0.0 ~/.nodes/20.0.0
```

_Note: of course you can install any 2 node versions, these are just examples. This article_
_will eventually go out of date and it may be best to select the 2 newest **even** releases._

We can test these node versions with the following:

```bash
$ ~/.nodes/18.0.0/bin/node -v
v18.0.0
$ ~/.nodes/20.0.0/bin/node -v
v20.0.0
```

## Basic Shim [\#](https://jdx.dev/posts/2024-04-13-shims-build-a-version-manager/\#basic-shim)

Before we create our first shim, we need a place to put it that is on PATH. I like to put my shims
into `~/bin`, but you can use anything. If this isn’t already on PATH you’ll need to add it inside of
`~/.bashrc`, `~/.zshrc`, or whatever file your shell uses.

Assuming that is in place, create a file called `~/bin/node` with the following contents:

```bash
#!/bin/bash
nodes_dir="$HOME/.nodes"
exec "$nodes_dir/20.0.0/bin/node" "$@"
```

Then you need to make it executable and test it:

```bash
$ chmod +x ~/bin/node
$ node
v20.0.0
```

_Note: if it isn’t working, check to make sure that `~/bin` is on PATH with `echo $PATH`. Also check that the output_
_of `which node` is `~/bin/node`. `~/bin` must be before anything else that might have `node` inside of it._

Now let’s break down elements of our shim:

- `#!/bin/bash` \- What shell to use to run the script. This is called a [shebang](https://en.wikipedia.org/wiki/Shebang_%28Unix%29) and is required.
- `nodes_dir="$HOME/.nodes"` \- A variable to store the path to our node versions. This is a good practice to make it easier to change later.
- `exec` \- Technically optional, this “execs” the node process to replace the bash process with node. This reduces the # of processes, keeps the process tree cleaner, and makes it so signals pass to the node process directly. The downside of this is you can’t add any commands _after_ executing node since bash replaces itself after `exec`.
- `"$nodes_dir/20.0.0/bin/node"` \- The path to the node binary we want to run. This is hardcoded to node-20 but we’ll fix that in the next step.
- `"$@"` \- This is a special variable that contains all of the arguments passed to the shim. This is important for arguments like “-v” to get passed correctly. You don’t want to use `$*` since that will break quoted arguments.

## Manual switching via environment variable [\#](https://jdx.dev/posts/2024-04-13-shims-build-a-version-manager/\#manual-switching-via-environment-variable)

Now let’s modify this to allow us to actually switch between node versions:

```bash
#!/bin/bash
nodes_dir="$HOME/.nodes"
exec "$nodes_dir/$NODE_VERSION/bin/node" "$@"
```

We can now change the node version either inline, or by exporting NODE\_VERSION in our shell session:

```bash
$ NODE_VERSION=18.0.0 node -v
v18.0.0
$ NODE_VERSION=20.0.0 node -v
v20.0.0
$ export NODE_VERSION=18.0.0
$ node -v
v18.0.0
$ export NODE_VERSION=20.0.0
$ node -v
v20.0.0
```

## Automatic switching via `.node-version` file [\#](https://jdx.dev/posts/2024-04-13-shims-build-a-version-manager/\#automatic-switching-via-node-version-file)

While we could switch using the environment variable like above, we would need
to remember to do this every time we switched directories. Now we’ll add support for reading
a `.node-version` file in the root of the project:

```bash
#!/bin/bash
nodes_dir="$HOME/.nodes"
node_version=$(cat .node-version)
exec "$nodes_dir/$node_version/bin/node" "$@"
```

Now we get our automatic switching behavior:

```bash
$ cd ~/src/proj1
$ echo "18.0.0" > .node-version
$ node -v
v18.0.0
$ cd ~/src/proj2
$ echo "20.0.0" > .node-version
$ node -v
v20.0.0
```

This file could be committed to the project to ensure everyone is on the same version.

## Homework [\#](https://jdx.dev/posts/2024-04-13-shims-build-a-version-manager/\#homework)

As your homework, figure out how to do the following:

- Add a check to ensure the `.node-version` file exists.
- Use `.node-version` as a fallback if `NODE_VERSION` is not set. (btw this is “correct” behavior for version managers, env vars always take precedence)
- Recurse directories to find the nearest `.node-version` file if it doesn’t exist in the current directory.
- Support “v” prefixes e.g. \`echo “v18.0.0” > .node-version (this is idiomatic for node version managers)
- Add autoinstalling of node versions if they don’t exist in `~/.nodes` (hint: use `node-build`)

## Pro-tips [\#](https://jdx.dev/posts/2024-04-13-shims-build-a-version-manager/\#pro-tips)

### `\#!/usr/bin/env bash` [\#](https://jdx.dev/posts/2024-04-13-shims-build-a-version-manager/\#usrbinenv-bash)

I prefer using `#!/usr/bin/env bash` as the shebang in my scripts instead of `#!/bin/bash`.
This will cause the shell to use whatever `bash` is on PATH instead of what is specifically in `/bin/bash`.
On macOS, for example, bash is super out of date, but if you install a newer bash with homebrew,
`#!/usr/bin/env bash` will use the homebrew version instead.

### `\#!/bin/sh` [\#](https://jdx.dev/posts/2024-04-13-shims-build-a-version-manager/\#binsh)

If you’re writing a shim that doesn’t use any bash-specific features, you can use `#!/bin/sh` instead.
This can be faster for instance in Ubuntu because `sh` uses `dash` instead.

### `nodes_dir=${NODES_DIR:-$HOME/.nodes}` [\#](https://jdx.dev/posts/2024-04-13-shims-build-a-version-manager/\#nodes_dirnodes_dir-homenodes)

Using this to set the `nodes_dir` variable allows you to override the default by setting the `NODES_DIR` environment
variable. By convention, environment variables are in all caps but local variables are lowercase.

Note: `nodes_dir` does not get passed to the node process because
it is not exported,
however, this can still be problematic if “nodes\_dir” is used as an
environment variable. To prevent that, I might do the following:

```fallback
exec "${NODES:-$HOME/.nodes}/20.0.0/bin/node" "$@"
```

That way we’re not creating any local variables that may conflict with environment variables.

### Bash “strict mode” [\#](https://jdx.dev/posts/2024-04-13-shims-build-a-version-manager/\#bash-strict-mode)

By default, bash scripts won’t stop executing if a command fails. You generally do not
want this to happen so it’s better to add the following to the top of your scripts:

```bash
set -e
```

That makes if fail on errors, but I prefer adding a couple of extra flags in all of my scripts to make them more robust:

```bash
set -euo pipefail
```

- `-e` \- Exit immediately if a command fails.
- `-u` \- Exit if you try to use an unset variable.
- `-o pipefail` \- Exit if any command in a pipeline fails.

### `set -x` [\#](https://jdx.dev/posts/2024-04-13-shims-build-a-version-manager/\#set--x)

If you’re debugging a script, you can add `set -x` to the top of your script to print out each command before it is run.
This prints out each command that gets executed which can be helpful for debugging.

## Learn more [\#](https://jdx.dev/posts/2024-04-13-shims-build-a-version-manager/\#learn-more)

To learn more about how shims are used in mise-en-place and whether or not you should use
them (because in mise it’s optional), read my next article on the topic: [Shims: How they work in mise-en-place](https://jdx.dev/posts/2024-04-13-shims-how-they-work-in-mise-en-place).