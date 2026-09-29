[Skip to content](https://jdx.dev/posts/2023-04-08-10-rtx-features/#main)

On this page

Goal #1 with [rtx](https://rtx.pub/) was to be a drop-in replacement for [asdf](https://asdf-vm.com/).
We quickly
achieved parity with asdf and now thousands of people have moved to rtx and are loving how much
faster and easier to use it is.
Since then, though, we haven’t stopped and a lot more features have been added you might not
have seen.

## 1\. Arbitrary env vars [\#](https://jdx.dev/posts/2023-04-08-10-rtx-features/\#1-arbitrary-env-vars)

You can now set arbitrary environment variables in your `.rtx.toml` files so now you can use rtx
as a replacement for dotenv and common uses of direnv:

```toml
[env]
NODE_ENV = "production"
```

You can also modify PATH with `env_path`:

```toml
env_path = [\
    "~/.local/share/bin",  # absolute paths are fine of course\
    "./node_modules/.bin", # relative to the directory of the .rtx.toml file\
]
```

And if you prefer having a `.env` file you can do that too:

```toml
env_file = ".env"
```

_See [#441](https://github.com/jdx/rtx/issues/441) where we’re discussing ideas to take this_
_even further with things like having a secure directory and environments like `.rtx.staging.toml`_
_files._

## 2\. `rtx prune` [\#](https://jdx.dev/posts/2023-04-08-10-rtx-features/\#2-rtx-prune)

One of the major selling points of rtx is that you don’t need to manually specify specific patch
versions of your tools like `18.15.0` and can just use `18` in your `.tool-versions`/`.rtx.toml`
files. You can update to the newest version of a tool by running `rtx install`.

However this means you’ll leave some old versions lying around. If you want to clean these up,
run `rtx prune`. This will remove all versions of tools that are no longer referenced by any
`.tool-versions`/`.rtx.toml` files you’ve ever used.

If you’re curious how this works under the hood, rtx tracks all config files as symlinks in `~/.local/share/rtx/tracked_config_files`.
You shouldn’t ever have a need to interact with these but
it might be interesting to see how it works.

In the future, we plan to improve this workflow a bit more with an `rtx upgrade` command. Please
come and bikeshed on [#49](https://github.com/jdx/rtx/issues/49) if you want to see what we’re thinking about.

## 3\. Run rtx with GitHub Actions [\#](https://jdx.dev/posts/2023-04-08-10-rtx-features/\#3-run-rtx-with-github-actions)

You can use rtx to install software on GitHub Actions. Use the following example workflow to install rtx on a GitHub Actions runner.

_See more information about the action on [jdx/rtx-action](https://github.com/jdx/rtx-action)._

```yaml
# ...
jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: jdx/rtx-action@v1
        with:
          tool_versions: |
            shellcheck 0.9.0
      - run: shellcheck scripts/*.sh
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: jdx/rtx-action@v1
      # .tool-versions/.rtx.toml will be read from repo root
      - run: node ./my_app.js
```

### 4\. Shebangs [\#](https://jdx.dev/posts/2023-04-08-10-rtx-features/\#4-shebangs)

You can use rtx as a method to declare which version of a runtime is required for a particular
script, for example if you need to run something with ruby 3.0.x:

```ruby
#!/usr/bin/env -S rtx x ruby@3.0 -- ruby
puts "running with ruby version: #{RUBY_VERSION}"
```

Now anyone that has simply has rtx installed can run this script and it will automatically use the
right version of ruby. No need to even activate rtx in your shell or anything.

### 5\. Python Virtualenvs [\#](https://jdx.dev/posts/2023-04-08-10-rtx-features/\#5-python-virtualenvs)

In Python, typically you want a particular project to use its own set of dependencies. This is
managed via virtualenvs. This is now built into rtx so you can specify the virtualenv in your
`.rtx.toml` and it will automatically created/activated when entering the project directory:

```toml
[tools]
python = {version="3.11", virtualenv=".venv"}
```

_See [rtx-poetry](https://github.com/rtx-plugins/rtx-poetry) and \[rtx-pipenv\](https://github. com/rtx-plugins/rtx-pipenv)_
_for integrating virtualenvs created by poetry/pipenv._

### 6\. `rtx shell` [\#](https://jdx.dev/posts/2023-04-08-10-rtx-features/\#6-rtx-shell)

You can now run `rtx shell` to modify your current session to use different tool versions. For
example:

```sh-session
$ rtx shell nodejs@16
$ node --version
v16.13.0
$ rtx shell nodejs@18
$ node --version
v18.15.0
```

The way this actually works is interesting though. What happens when you run `rtx shell` is that it
creates an environment variable `RTX_NODEJS_VERSION=18` in the current session, but how does it
do that if `rtx` is an external binary?

The answer is that `rtx` is actually a shell function. When you activate rtx with, it creates a
bash/zsh function similar to the following:

```bash
rtx() {
  local command
  command="${{1:-}}"

  case "$command" in
  deactivate|shell)
    eval "$({exe} "$command" "$@")"
    ;;
  *)
    command {exe} "$command" "$@"
    ;;
  esac
}
```

That way the output of `rtx shell` is automatically eval’ed in the current session. Kudos to pyenv
where reading the source code showed me how to accomplish this. Technically this only matches
behavior that asdf has (and isn’t something _new_ to rtx), but I figured it was interesting
enough to showcase. In asdf this is easy since it’s already running bash.

### 7\. Minus syntax: `lts!2` [\#](https://jdx.dev/posts/2023-04-08-10-rtx-features/\#7-minus-syntax-lts2)

If you want to express that you want the latest 2 lts/latest versions of node and python installed,
you can now do this with the following syntax in `.rtx.toml`:

```toml
[tools]
nodejs = ["lts", "lts!2"]         # 18.x, 16.x
python = ["latest", "latest!0.1"] # 3.11.x, 3.10.x
```

_Note that this syntax is likely to change a bit but the functionality will definitely remain. We_
_will probably go with something like `minus!2:nodejs@latest` because it will fit better with_
_other directives like `path:` and `ref:`._

### 8\. Custom plugin repo urls in `.rtx.toml` [\#](https://jdx.dev/posts/2023-04-08-10-rtx-features/\#8-custom-plugin-repo-urls-in-rtxtoml)

A common problem for asdf users has been if they want people in an organization to share a
particular plugin, they would need to tell people to manually add it before they can run
`asdf install`. For example, if using a custom python plugin:

```sh-session
$ asdf plugin add python https://myorg/some-custom-python-plugin.git
$ asdf install
```

This is no longer necessary with rtx because you can specify the plugin url inside of `.rtx.toml`:

```toml
[tools]
python = "3.11"

[plugins]
python = "https://myorg/some-custom-python-plugin.git"
```

_Note that this only will be used if the plugin is not installed, so it won’t use the custom url if_
_the plugin is already installed. At least for the foreseeable future this behavior will need to_
_remain because there isn’t a way to have multiple plugins for “python” even in different projects._

### 9\. Custom shorthand repo [\#](https://jdx.dev/posts/2023-04-08-10-rtx-features/\#9-custom-shorthand-repo)

If you use rtx extensively in your organization, you can provide a custom shorthand repo to make
it easy to install new tools.

Here is an [example plugin](https://github.com/jdx/rtx-shorthands) that demonstrates this:

```sh-session
$ rtx plugin install rtx-shorthands PLUGIN_GIT_URL
$ rtx settings set shorthands_file ~/.local/share/rtx/plugins/rtx-shorthands/shorthands.toml
$ rtx plugin install CUSTOM_PLUGIN
```

However note that the plugin here is just being used to store the toml shorthand file. You can
distribute that toml file any way you like.

### 10\. `rtx plugins link` [\#](https://jdx.dev/posts/2023-04-08-10-rtx-features/\#10-rtx-plugins-link)

This one is helpful for plugin authors. If you want to work on a plugin like rtx-python, you can now
do that with the following:

```sh-session
$ git clone https://github.com/rtx-plugins/rtx-python ~/src/rtx-python
$ cd ~/src/rtx-python
$ rtx plugins link . -f # force will overwrite python if it's already installed
$ vim bin/install       # modify some plugin script
$ rtx install python    # will use the local version of the plugin
```