[Skip to content](https://mise.jdx.dev/mise-cookbook/ruby.html#VPContent)

On this page

# Ruby Cookbook [​](https://mise.jdx.dev/mise-cookbook/ruby.html\#ruby-cookbook)

Use mise to select Ruby and tasks to run the application's Bundler and Rails commands. This recipe assumes an existing Rails project with `Gemfile`, `Gemfile.lock`, and `bin/rails`. Add RuboCop to the development bundle before using the lint task. Install Ruby's platform dependencies as described in the [Ruby guide](https://mise.jdx.dev/lang/ruby.html).

## A Ruby on Rails Project [​](https://mise.jdx.dev/mise-cookbook/ruby.html\#a-ruby-on-rails-project)

mise.toml

toml

```
min_version = "2024.9.5"

[env]
# Project information
PROJECT_NAME = "{{ config_root | basename }}"

[tools]
# Install Ruby with the specified version
ruby = "{{ get_env(name='RUBY_VERSION', default='3.3.3') }}"

[tasks."bundle:install"]
description = "Install gem dependencies"
run = "bundle install"

[tasks.server]
description = "Start the Rails server"
alias = "s"
run = "bundle exec rails server"

[tasks.test]
description = "Run tests"
alias = "t"
run = "bundle exec rails test"

[tasks.lint]
description = "Run lint using Rubocop"
alias = "l"
run = "bundle exec rubocop"
```

Run `mise run bundle:install` after cloning, then `mise run test` or `mise run server`. `bundle exec` selects the executables from the project's bundle, including its locked Rails and RuboCop versions. Application setup such as database creation remains part of the Rails project's own instructions.

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)