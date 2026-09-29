[Skip to content](https://mise.jdx.dev/dev-tools/backends/gem.html#VPContent)

On this page

# gem Backend [​](https://mise.jdx.dev/dev-tools/backends/gem.html\#gem-backend)

The `gem` backend installs Ruby command-line applications from RubyGems into separate tool directories. Keep application gems in your project's `Gemfile` and install them with Bundler. The code for this is inside of the mise repository at [`./src/backend/gem.rs`](https://github.com/jdx/mise/blob/main/src/backend/gem.rs).

## Dependencies [​](https://mise.jdx.dev/dev-tools/backends/gem.html\#dependencies)

This backend needs Ruby and its `gem` command. Gems with native extensions also need the compiler and libraries required by that gem.

## Usage [​](https://mise.jdx.dev/dev-tools/backends/gem.html\#usage)

Declare Ruby and RuboCop in the same project:

sh

```
mise use ruby@3.4 gem:rubocop
mise exec -- rubocop --version
```

This writes both entries to `mise.toml`. Add `-g` for global configuration.

toml

```
[tools]
ruby = "3.4"
"gem:rubocop" = "latest"
```

mise's wrappers set `GEM_HOME` for the selected tool. A RuboCop configuration that uses project-specific plugins may be better run with `bundle exec rubocop` from a Gemfile that declares those plugins.

## Ruby upgrades [​](https://mise.jdx.dev/dev-tools/backends/gem.html\#ruby-upgrades)

If the Ruby version used by a gem package changes (whether managed by mise or the system), you may need to reinstall the gem. This can be done with:

sh

```
mise install -f gem:rubocop
```

Reinstall under the Ruby version you intend to use. On Unix, mise-managed Ruby shebangs follow a minor-version path so patch upgrades can keep working; moving to another minor version or changing native-extension compatibility can still require a reinstall.

## Settings [​](https://mise.jdx.dev/dev-tools/backends/gem.html\#settings)

Set these with `mise settings set [VARIABLE]=[VALUE]` or by setting the environment variable listed.

No settings available.

## Tool Options [​](https://mise.jdx.dev/dev-tools/backends/gem.html\#tool-options)

The following [tool-options](https://mise.jdx.dev/dev-tools/#tool-options) are available for the `gem` backend—these go in `[tools]` in `mise.toml`.

### `install_env` [​](https://mise.jdx.dev/dev-tools/backends/gem.html\#install-env)

Set environment variables for the `gem install` command. For gems that build native extensions, `MAKEFLAGS` controls parallel make jobs:

toml

```
[tools]
"gem:rubocop" = { version = "latest", install_env = { MAKEFLAGS = "-j4" } }
```

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)