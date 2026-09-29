[Skip to content](https://mise.jdx.dev/cli/ssh.html#VPContent)

On this page

# `mise ssh` [​](https://mise.jdx.dev/cli/ssh.html\#mise-ssh)

- **Usage:**`mise ssh [FLAGS] [DESTINATION] [COMMAND]…`
- **Source code:** [`src/cli/ssh.rs`](https://github.com/jdx/mise/blob/main/src/cli/ssh.rs)

Open an SSH session, optionally borrowing read-only GitHub access

## Arguments [​](https://mise.jdx.dev/cli/ssh.html\#arguments)

- **`[DESTINATION]`** — OpenSSH destination or SSH-config alias
- **`[COMMAND]…`** — Command to execute after --; omit for an interactive shell

## Flags [​](https://mise.jdx.dev/cli/ssh.html\#flags)

- **`-i --identity-file <IDENTITY_FILE>`** — SSH identity file
- **`-p --port <PORT>`** — SSH port
- **`-o --ssh-option <SSH_OPTION>`** — OpenSSH option; repeat for multiple options
- **`--github-relay-read-only`** — Borrow read-only GitHub access for this session only
- **`--github-relay-repo <OWNER/REPO>`** — Approved GitHub repository; repeat to authorize more repositories
- **`--github-relay-all-repos`** — Explicitly authorize reads of all repositories accessible locally
- **`--github-relay-log-requests`** — Log sanitized relay requests on local stderr
- **`--github-relay-no-log-requests`** — Disable request logging, overriding the saved preference
- **`--github-relay-log-format <FORMAT>`** — Relay log and summary format: text or jsonl
- **`--github-relay-max-duration <DURATION>`** — Expire borrowed access after a duration such as 1h (0s: session lifetime)
- **`-h --help`** — Print help

## Related documentation [​](https://mise.jdx.dev/cli/ssh.html\#related-documentation)

- [Git provider authentication](https://mise.jdx.dev/dev-tools/github-tokens.html).
- [All commands](https://mise.jdx.dev/cli/).
- [Global flags and argument syntax](https://mise.jdx.dev/cli/#global-flags).

sponsors

[![Entire](https://jdx.dev/sponsors/entire-lockup.svg)](https://entire.io/)[![Omacom Foundation](https://jdx.dev/sponsors/omacom-foundation.svg)](https://omarchy.org/patrons/)[![CodeRabbit](https://jdx.dev/sponsors/coderabbit.svg)](https://coderabbit.link/mise)

[View all sponsors](https://jdx.dev/sponsors.html)