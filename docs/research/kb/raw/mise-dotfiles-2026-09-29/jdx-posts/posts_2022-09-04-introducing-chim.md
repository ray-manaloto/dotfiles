[Skip to content](https://jdx.dev/posts/2022-09-04-introducing-chim/#main)

On this page

_I had a 3-day weekend and decided to learn Rust while also putting together an idea I’ve_
_had for a few years now: [chim](https://chim.sh/)._

# Background [\#](https://jdx.dev/posts/2022-09-04-introducing-chim/\#background)

The problem I’ve wanted to solve is bootstrapping projects for local dev and CI/CD.
Essentially, how tool versions are defined and installed—tools being things like programming
language runtimes, package managers, and linters. For example, a project might require node-v18.8.0, jq-v1.6, and shellcheck-v0.8.0. Other versions of these tools may not be compatible.

### Local Dev [\#](https://jdx.dev/posts/2022-09-04-introducing-chim/\#local-dev)

Locally you might use asdf[1](https://jdx.dev/posts/2022-09-04-introducing-chim/#fn:1) or nvm[2](https://jdx.dev/posts/2022-09-04-introducing-chim/#fn:2). They’re good for making it when you `cd` into a
different project change the local versions—for instance one project might be running node-18
and another might be running node-16.

The downside is they rely either on complex shims or shell extensions in order to work—sometimes
both. They’re often a source of problems for beginners and experienced developers alike since
they break expectations of what `$PATH` should be doing. To illustrate: you typically can’t just
run `which node` to see exactly which `node` runtime is being used—asdf just say `~/.asdf/shims/node`.

### Production [\#](https://jdx.dev/posts/2022-09-04-introducing-chim/\#production)

In production, we generally only need a single version and automatically switching on `cd` is
not helpful. asdf and similar tools usually just get in the way and are more work to configure.

It’s common in production to install the dependencies in a Dockerfile. This can be done locally, but
many devs (myself included) find trying to code _inside_ a Docker container painful. It’s either a
chore to get files syncing correctly, forgetting that you’re in (or not in) the container, or you’re
dealing with poor performance emulating x64 on an ARM Mac.

Even if Docker isn’t used, production still likely has some way of installing dependencies
like that is cumbersome locally (e.g.: ansible or chef).

### Dev/Prod Parity [\#](https://jdx.dev/posts/2022-09-04-introducing-chim/\#devprod-parity)

Ultimately what we want is the ability to synchronize the toolset versions across
dev and prod. For example, there should be a single file that defines which version
of node is being used in my project and if I change that setting, it will change the
version in production as well as for my fellow developers when they pull the latest changes.

This is the goal of chim.

## What chim does [\#](https://jdx.dev/posts/2022-09-04-introducing-chim/\#what-chim-does)

A “chim” is a universal binary shim that (typically) defines a tarball, checksum,
and path to a platform-specific binary inside the tarball. For example, this is
a chim for nodejs (imagine it’s localed at `./bin/node`):

```toml
#!/usr/bin/env chim
[macos-arm64]
url = 'https://nodejs.org/dist/v18.8.0/node-v18.8.0-darwin-arm64.tar.gz'
path = 'node-v18.8.0-darwin-arm64/bin/node'
checksum = '4952a8ec7ca07328571ba0b06d228c2a8220041a6f07df4f46765c341a80ccd4'

[linux-x64]
url = 'https://nodejs.org/dist/v18.8.0/node-v18.8.0-linux-x64.tar.gz'
path = 'node-v18.8.0-linux-x64/bin/node'
checksum = '01c2060503bb42caa1c6cc2ee4b432f80c0b38ad46b4eed956774fb36302f46e'

[windows-x64]
url = 'https://nodejs.org/dist/v18.7.0/node-v18.7.0-win-x64.zip'
path = 'node-v18.7.0-win-x64\node.exe'
checksum = '9c0abfe32291dd5bed717463cb3590004289f03ab66011e383daa0fcec674683'
```

All that you need to do is install chim, create this file, make it executable, then
it can be run with `./bin/node`. Other developers can add this directory to `$PATH`
(possibly with [direnv](https://direnv.net/) automatically when entering a project
directory).

When the chim is run for the first time, it downloads the tarball, verifies the
checksum, extracts it to a cache directory, then executes node. Future invocations
will just execute node directly. I’ve measured the overhead for these future
runs at ~1ms on my machine (thanks to Rust) so it shouldn’t impact performance
significantly. (For reference, `node -v` without chim takes ~15ms on my box.)

This shim can easily be used in production as well. Just add the directory to `$PATH`
and now it’s using the same shims in production.

## Chimstrap [\#](https://jdx.dev/posts/2022-09-04-introducing-chim/\#chimstrap)

For a single binary this isn’t terribly helpful since instead of installing node
we now need to install chim before we can run the shim. To alleviate that, there is
a bootstrapping script that provides a platform independent executable of chim itself
called the [“chimstrap”](https://chim.sh/docs/installing/#chimstrap).

The chimstrap is just a shell script that behaves similarly to chim. It will download
chim from the GitHub Releases, and store it in a cache directory for future
invocations, and execute chim. It can be used like this:

```fallback
$ curl -o ./chim https://chim.sh/chimstrap
$ chmod +x ./chim
$ ./chim -v
chim 1.0.0
```

## `chim checksums` [\#](https://jdx.dev/posts/2022-09-04-introducing-chim/\#chim-checksums)

Updating checksums is bit of yak shaving that can be avoided with `chim checksums`. Update the
URLs[3](https://jdx.dev/posts/2022-09-04-introducing-chim/#fn:3), run `chim checksums ./path/to/chim` and it will update all of the checksums in the chim.

## Let me know what you think! [\#](https://jdx.dev/posts/2022-09-04-introducing-chim/\#let-me-know-what-you-think)

It’s a simple project, so it should be easy for me to support. Let me know if it works
for you or if it’s missing something that would be helpful for your use-case.

- [Discussions](https://github.com/chim-sh/chim/discussions)
- [Issues](https://github.com/chim-sh/chim/issues)

## Footnotes [\#](https://jdx.dev/posts/2022-09-04-introducing-chim/\#footnotes)

* * *

1. asdf in particular is a poor tool because it [increases the time to launch binaries](http://stratus3d.com/blog/2022/08/11/asdf-performance/) by 150ms (!). This can quickly make working with a project that uses asdf very slow. [↩︎](https://jdx.dev/posts/2022-09-04-introducing-chim/#fnref:1)

2. Only works for node, not other languages and tools. [↩︎](https://jdx.dev/posts/2022-09-04-introducing-chim/#fnref:2)

3. Or just leave the checksums out and `chim checksums` will add them. [↩︎](https://jdx.dev/posts/2022-09-04-introducing-chim/#fnref:3)