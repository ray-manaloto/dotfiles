[Skip to content](https://jdx.dev/posts/2024-04-13-shims-how-they-work-in-mise-en-place/#main)

On this page

Assuming you’ve setup [mise](https://mise.jdx.dev/) and have it configured in a couple of
projects to switch between different versions of node, that will happen automatically
when entering the project directories:

```bash
$ cd ~/src/proj1
$ node -v
20.0.0
$ cd ~/src/proj2
$ node -v
18.0.0
```

The way that mise is able to switch this version depends on whether you’ve activated
mise with shims or not. In this article, I’ll explain how these methods work under the
hood and the pros and cons of using them.

## PATH [\#](https://jdx.dev/posts/2024-04-13-shims-how-they-work-in-mise-en-place/\#path)

The default behavior of `mise activate` is using the “PATH” solution. This is relatively easy to understand,
though the actual logic gets quite complex. Basically every time the prompt is displayed, mise first
runs itself to check what the environment variables should be in that directory based on the `.mise.toml`
files.

If the current directory has the following `.mise.toml` file:

```toml
[env]
FOO = "bar"
[tools]
node = "20"
python = "3.11"
```

Then mise will set PATH to include the following directories:

- `~/.local/share/mise/node/20/bin`
- `~/.local/share/mise/python/3.11/bin`

As well as set FOO to “bar”.

## Shims [\#](https://jdx.dev/posts/2024-04-13-shims-how-they-work-in-mise-en-place/\#shims)

Now let’s talk about shims. If you aren’t familiar with shims, I encourage you to first read my
other article on the topic:
[Shims: Build a version manager](https://jdx.dev/posts/2024-04-13-shims-build-a-version-manager).

The way mise works is a little different than what is described in that post though. Instead of creating
shims as bash scripts, mise shims are actually symlinks to the mise binary itself. You can see this
by listing the contents of the `~/.local/share/shims` directory:

```bash
$ ls -l ~/.local/share/shims/
lrwxr-xr-x  node@ -> /opt/homebrew/bin/mise
lrwxr-xr-x  npm@ -> /opt/homebrew/bin/mise
lrwxr-xr-x  python@ -> /opt/homebrew/bin/mise
lrwxr-xr-x  python3@ -> /opt/homebrew/bin/mise
lrwxr-xr-x  python3.11@ -> /opt/homebrew/bin/mise
```

This is the same binary you run when you run commands like `mise install` or `mise use`. When mise
starts up, one of the first things it does is check to see the name it was called as. If it’s “mise”,
then it operates like normal. If it’s anything else, it operates in “shim” mode.

In shim mode, it will first load the mise environment. This means all of the env vars in `.mise.toml`
files as well as all of the current tools listed in those configs. If we assume our mise config
is the following:

```toml
[tools]
node = "20"
python = "3.11"
```

Then as part of that logic it will set PATH to include the following directories:

- `~/.local/share/mise/node/20/bin`
- `~/.local/share/mise/python/3.11/bin`

From there, mise simply execs the command that it was called as with all of the arguments. So
if you called the `node` shim, with the `-v` argument, it would be the same as running the following
but with the mise environment loaded:

```bash
$ node -v
```

However because we’ve modified PATH inside of the shim execution, `node` won’t point to the mise shim and
end up in an endless loop, it will call `~/.local/share/mise/node/20/bin/node` instead.

## `mise x|exec` and `mise r|run` [\#](https://jdx.dev/posts/2024-04-13-shims-how-they-work-in-mise-en-place/\#mise-xexec-and-mise-rrun)

You don’t need to use either of the above solutions with mise. If you don’t want to modify your shell’s
rc file, you can instead use `mise x|exec` or `mise r|run` to explicitly run something with mise.

`mise exec` will load the mise environment just like it would be using the other methods (setting PATH and
other env vars in `.mise.toml` files), and execute whatever you passed into it like the following:

```bash
$ mise exec -- node -v
20.0.0
```

`mise r|run` is similar except it executes a [task](https://mise.jdx.dev/tasks/).

Sticking to `mise exec` and `mise run` is a nice way to keep your shell environment pristine and only
use mise when you explicitly want to.

## Pros/Cons [\#](https://jdx.dev/posts/2024-04-13-shims-how-they-work-in-mise-en-place/\#proscons)

Now in general, I tell people they should use shims in _non-interactive_ environments such as
CI/CD, scripts, and IDE configuration. This is because the PATH solution doesn’t work in those
environments at all. The prompt is never displayed there, so mise never has a change to update the
environment.

However in _interactive_ environments, I don’t recommend shims because it “breaks” `which`.
If you run `which node`, you’ll just get back the mise shim (e.g. `~/.local/share/shims/node@`)—which often isn’t that helpful. You can run `mise which node` to get the path,
but it’s an extra step that’s easy to forget. In my workflows, I often use `which` to find out what
tools I’m talking to so the PATH solution is a big help.

Another reason I don’t like shims is that it can only set arbitrary env vars when a shim is actually
called. For instance, if you set `FOO=bar` in your `.mise.toml`, then only when you call a shim like
`node` will mise have the opportunity to set FOO. If you simply run `echo $FOO` in your terminal,
mise won’t have set it because no shim was called. This is a problem for both interactive and non-interactive
environments.

This is one reason I added tasks to mise. Using tasks and `mise run`, there is no need to have activated
mise and setup shims or anything else. Anytime you’re using `mise run` you’ll already have the mise environment
fully setup.

## Conclusion [\#](https://jdx.dev/posts/2024-04-13-shims-how-they-work-in-mise-en-place/\#conclusion)

The way I suggest using mise is to use PATH for your local development and shims for IDE stuff. Things
in scripts and CI/CD should use tasks. That way you’re really getting the best solution in each of those
environments.