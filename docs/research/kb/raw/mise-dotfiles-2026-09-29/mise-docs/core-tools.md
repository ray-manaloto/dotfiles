[Skip to content](https://mise.jdx.dev/core-tools.html#VPContent)

On this page

# Core Tools [​](https://mise.jdx.dev/core-tools.html\#core-tools)

Core tools have installation logic built into mise. They do not require a separately installed plugin. Their language guides explain platform support, compilation options, virtual environments, and other runtime-specific behavior.

List the current core entries with:

sh

```
mise registry -b core
```

## Language guides [​](https://mise.jdx.dev/core-tools.html\#language-guides)

- [Bun](https://mise.jdx.dev/lang/bun.html)
- [Deno](https://mise.jdx.dev/lang/deno.html)
- [.NET](https://mise.jdx.dev/lang/dotnet.html)
- [Elixir](https://mise.jdx.dev/lang/elixir.html)
- [Erlang](https://mise.jdx.dev/lang/erlang.html)
- [Go](https://mise.jdx.dev/lang/go.html)
- [Java](https://mise.jdx.dev/lang/java.html)
- [Node.js](https://mise.jdx.dev/lang/node.html)
- [Python](https://mise.jdx.dev/lang/python.html)
- [Ruby](https://mise.jdx.dev/lang/ruby.html)
- [Rust](https://mise.jdx.dev/lang/rust.html)
- [Swift](https://mise.jdx.dev/lang/swift.html)
- [Zig](https://mise.jdx.dev/lang/zig.html)

## Selecting another implementation [​](https://mise.jdx.dev/core-tools.html\#selecting-another-implementation)

Installing an external plugin with the same name can override a core tool. Use that only when you need behavior provided by the plugin; it also changes the installation and trust requirements. See [plugins](https://mise.jdx.dev/plugins.html) and [backend selection](https://mise.jdx.dev/dev-tools/backends/) for how mise chooses an implementation.

To select the built-in implementation explicitly, use the `core:` prefix, for example `mise use core:python@3.14`. The [registry](https://mise.jdx.dev/registry.html) covers tools beyond the core set.

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)