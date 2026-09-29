[Skip to content](https://jdx.dev/posts/2026-09-05-introducing-mr-boxington/#main)

On this page

I’m introducing [mr-boxington](https://mr-boxington.jdx.dev/), a build cache for Rust that shares compilations across your machine and cleans up after itself. The command is `mbx`. Set it up once and keep running `cargo build`, `cargo test`, and `cargo clippy` as usual.

The pitch is **fix `target/`**.

If you work on several Rust projects, you probably have a lot of disk space tied up in build outputs. Add git worktrees and you get another copy of those outputs for every branch you’re working on. Delete them to reclaim space, and the next build spends time recreating much of the same work.

You can point checkouts at a shared target directory, but then Cargo’s directory lock makes builds wait for each other. Separate targets let builds run together, but now they’re compiling the same dependencies and competing for the same CPU and memory.

mbx brings five things together:

- **Automatically pruned targets.** Old build outputs get cleaned up, with disk budgets that apply without configuration.
- **One shared cache.** Compatible compilations can be reused across projects and checkouts.
- **Warm worktrees.** A new checkout can reuse what another checkout already built.
- **Parallel Cargo commands.** Tests, Clippy, and builds can run together with a shared resource budget and without compiling identical work twice.
- **Memory-aware scheduling.** mbx measures compiler memory use and checks available memory before starting more work.

## Keep using Cargo [\#](https://jdx.dev/posts/2026-09-05-introducing-mr-boxington/\#keep-using-cargo)

Install with [mise](https://mise.jdx.dev/):

```sh
mise use --global --postinstall "mbx setup --yes" mr-boxington
```

This installs mbx and runs `mbx setup --yes`, which adds a `[wrappers.cargo]` entry to your global mise config and runs `mise reshim`. Automatic Cargo wrapping requires mise 2026.8.16 or newer. With mise activated in your shell, run your usual commands:

```sh
cargo build
cargo test --all-features
cargo clippy --workspace
```

For editors, SSH sessions, and agents that don’t activate mise, follow the PATH instructions setup prints. `mbx doctor` checks the setup. The [installation guide](https://mr-boxington.jdx.dev/getting-started) has the details.

Cargo still resolves dependencies and plans the build. mbx sits around the compiler invocations, restoring outputs it has seen before and running the compiler when it hasn’t. It starts a cache agent inside each build command and exits with that command. There’s no persistent daemon to manage.

## Automatically pruned target directories [\#](https://jdx.dev/posts/2026-09-05-introducing-mr-boxington/\#automatically-pruned-target-directories)

Caching alone doesn’t solve the pile of abandoned target directories.

For a checkout without an existing `target/`, mbx creates a managed target under its cache root and leaves a `target` symlink in the checkout. Paths like `target/debug/my-app` still work. If there’s already a real target directory, mbx asks before replacing it; non-interactive builds leave it alone.

The [managed target directories](https://mr-boxington.jdx.dev/managed-targets) are collected when their checkout disappears, they’ve gone unused for 30 days by default, or they exceed the configured budget. The shared action cache has its own size budget. Defaults scale with the disk, and collection runs after builds, at most once an hour.

You can inspect the cache and preview cleanup. Here’s illustrative output; counts, sizes, and paths will vary by machine:

```console
$ mbx cache stats
store: /home/you/.cache/mbx/actions
objects: 12480 (8.2 GiB)
action results: 1860 (3.4 MiB)
total: 8.2 GiB
checkouts: 6 live, 2 stale
target directories: 8 (24.6 GiB)

$ mbx gc --dry-run
would have evicted 640 objects and 95 action results (1.1 GiB); 7.1 GiB remain
would have dropped 2 stale checkout records
would free 2 target directories (6.4 GiB, 2 abandoned and 0 live); 18.2 GiB remain
```

The dry run leaves the files in place. `mbx gc` performs the collection immediately.

There are settings for sizes and retention if you want them. The default experience should be that you build things and mbx takes care of the leftovers.

## One shared cache, warm worktrees [\#](https://jdx.dev/posts/2026-09-05-introducing-mr-boxington/\#one-shared-cache-warm-worktrees)

Every participating build uses the same cache on the machine. If two projects compile a dependency with matching inputs, that work can be reused too. mbx keys compilations by their inputs and normalizes known checkout-specific paths, so moving to another directory doesn’t by itself make a build cold.

Build your project, then create a worktree at the same commit:

```sh
cargo build
git worktree add --detach ../my-project-review HEAD
cd ../my-project-review
cargo build
```

Cargo prints its usual build output, followed by mbx’s cache summary. For example, the second build might end like this (illustrative counts, with Cargo’s output abbreviated):

```console
$ cargo build
   Compiling my-project v0.1.0 (/home/you/my-project-review)
...
mbx[cache]: 139 hits, 8 misses, 4 not looked up, 7 bypassed; 0 B downloaded, 0 B uploaded, 12.4 MiB stored locally
```

Those hits are compilations restored from the shared cache. Misses need compiling, “not looked up” means mbx didn’t have a key yet, and bypasses are work it deliberately left uncached.

The second build can restore cacheable compilations from the first, even though it’s in a different directory with a fresh target. Change a crate and its affected compilations need rebuilding; unchanged dependencies can still be reused. A different compiler, feature set, or other relevant input can produce a different cache key.

This matters even more when several people or coding agents are working in separate worktrees on one machine. Each checkout gets its own outputs while benefiting from the shared cache.

On filesystems that support reflinks, mbx restores files using copy-on-write clones. They share storage until modified, while writes to a restored file remain isolated from the cache. Where cloning isn’t available, mbx copies the files. Cache reuse still works, but those copies use additional disk space.

## Run Cargo commands in parallel [\#](https://jdx.dev/posts/2026-09-05-introducing-mr-boxington/\#run-cargo-commands-in-parallel)

Two independent Cargo processes don’t coordinate their resource use. Each can start enough compiler processes to keep the machine busy on its own. mbx makes them share one machine-wide resource budget.

If two builds ask for an identical cold compilation at the same time, one compiles it and the other waits for that result instead of repeating the work.

Cargo’s target-directory lock still applies, so concurrent commands need separate targets. For example, in a POSIX shell:

```sh
CARGO_TARGET_DIR=target/clippy cargo clippy --workspace &
CARGO_TARGET_DIR=target/tests cargo test --workspace &
wait
```

That lets the commands overlap while sharing cached work and compiler capacity. The [architecture docs](https://mr-boxington.jdx.dev/how-it-works) explain how the scheduling works.

You can watch it with:

```sh
mbx tui
```

The build summary also distinguishes hits, misses, compilations it couldn’t look up, and work it deliberately bypassed. A good hit rate isn’t very useful if most of the build never entered the cache.

## Watch memory before starting more work [\#](https://jdx.dev/posts/2026-09-05-introducing-mr-boxington/\#watch-memory-before-starting-more-work)

Running those Cargo commands together is why mbx needs to watch memory, too. Counting compiler processes isn’t enough. Some crates and links need much more memory than others, and the rest of your applications need RAM too.

mbx measures how much memory compilations use and uses that history to decide how much work to run together. A heavy compilation takes a larger share of the budget. While other compilations are running, it also checks available memory before admitting work with a known estimate, so it can hold off when the machine doesn’t have enough room.

By default, the scheduler budgets 85% of physical memory, using the container’s limit when applicable. This helps avoid piling more compiler processes onto a machine that’s already under pressure. It’s still an estimate: an unseen crate can use more than expected, and a single compilation that needs more RAM than the machine has won’t fit just because it’s running alone.

## What about CI? [\#](https://jdx.dev/posts/2026-09-05-introducing-mr-boxington/\#what-about-ci)

There’s a [GitHub Action](https://github.com/jdx/mr-boxington-action) that installs mbx and uses GitHub Actions cache to carry the store between jobs. Fork pull requests can warm from a cache built on `main`; pull requests don’t publish remote objects. There is also a [self-hostable cache server](https://mr-boxington.jdx.dev/cache-server) for trusted environments that need a shared remote.

Local development is the strongest reason to try mbx today. Remote caching works, but it doesn’t yet consistently beat `Swatinem/rust-cache` on GitHub-hosted runners. Measure your complete workflow before switching. The [benchmarks](https://mr-boxington.jdx.dev/benchmarks) explain the scenarios and link to the runs behind the results.

## Prior art and limits [\#](https://jdx.dev/posts/2026-09-05-introducing-mr-boxington/\#prior-art-and-limits)

mbx follows earlier compiler-cache work in [sccache](https://github.com/mozilla/sccache) and [kache](https://github.com/kunobi-ninja/kache). kache directly inspired its design. mbx began inside mise’s task runner and became a separate CLI; you don’t need mise to use it.

It won’t cache everything. When mbx can’t describe the inputs precisely enough, it runs the compiler normally. That includes some native links and compiler configurations. It also gives crates whose sources keep changing private incremental state; that state stays out of the shared cache. The [limits page](https://mr-boxington.jdx.dev/limits) covers the tradeoffs.

A cold build still has to compile, and keeping track of cacheable work adds overhead. The payoff comes when another build can reuse that work, especially after changing branches or creating a fresh worktree.

Try it on a project you build often, then build it in another worktree. I’d like to hear where it saves you time, where it misses work you expected it to reuse, and what still gets in the way.

[Get started](https://mr-boxington.jdx.dev/getting-started) · [Source and issues](https://github.com/jdx/mr-boxington)