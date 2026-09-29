# gh upgrades leave Git credential helper pointing to a deleted versioned binary

- URL: https://github.com/omacom/omarchy/issues/7712
- author: hemagome state: open created: 2026-08-21T22:19:20Z merged: n/a
- fetched: 2026-09-29 via gh api (lane X)

## Body

### System details

- Omarchy: `4.0.0-1`
- mise: `2026.8.6`
- Git: `2.55.0`
- Previous GitHub CLI: `2.97.0`
- Current GitHub CLI: `2.98.0`
- Git remote protocol: HTTPS

### Summary

A `gh` upgrade managed by mise left Git’s HTTPS credential helper pointing to a deleted, version-specific GitHub CLI executable.

Changing the helper to Omarchy’s stable `~/.local/bin/gh` wrapper did not solve the problem because the wrapper runs `mise use -g "gh"` without quiet mode. Its informational output is written to standard output and Git attempts to parse it as part of the credential protocol.

The working configuration is:

```text
!mise exec --quiet gh -- gh auth git-credential
```

This resolves the currently selected mise-managed `gh` version without referencing a disposable installation path and without contaminating the credential-helper output.

### Initial failure after the `gh` upgrade

After `gh` was upgraded by mise from 2.97.0 to 2.98.0, a normal `git push` failed with:

```text
/home/user/.local/share/mise/installs/gh/2.97.0/gh_2.97.0_linux_amd64/bin/gh auth git-credential get: line 1: /home/user/.local/share/mise/installs/gh/2.97.0/gh_2.97.0_linux_amd64/bin/gh: No such file or directory
Username for 'https://github.com':
```

Git had retained this credential-helper configuration:

```text
credential.https://github.com.helper=
credential.https://github.com.helper=!/home/user/.local/share/mise/installs/gh/2.97.0/gh_2.97.0_linux_amd64/bin/gh auth git-credential
```

The referenced 2.97.0 installation no longer existed. The active version was:

```text
/home/user/.local/share/mise/installs/gh/2.98.0/gh_2.98.0_linux_amd64/bin/gh
```

Git therefore could not execute the configured credential helper and fell back to requesting an HTTPS username.

### Failure when using Omarchy’s stable wrapper

As an attempted workaround, the credential helper was changed to:

```text
!/home/user/.local/bin/gh auth git-credential
```

Authentication was then refreshed successfully:

```text
✓ Authentication complete.
✓ Configured git protocol
✓ Logged in as user
```

However, `git push` still failed:

```text
warning: invalid credential line: mise ~/.config/mise/config.toml tools: gh@2.98.0
Username for 'https://github.com':
```

The Omarchy wrapper installed at `~/.local/bin/gh` contains:

```bash
#!/bin/bash
export MISE_MINIMUM_RELEASE_AGE=0
mise use -g "gh" || exit 1
exec mise x "gh" -- "gh" "$@"
```

The `mise use -g "gh"` invocation emits an informational status line. This is normally harmless for interactive `gh` usage, but a Git credential helper must write only valid credential-protocol fields to standard output.

Git interprets the mise status line as credential data, rejects it as an invalid credential line, and falls back to requesting a username.

The locally installed Omarchy source confirms that the wrapper is generated without quiet mode:

```text
/usr/share/omarchy/bin/omarchy-mise-install
```

Relevant lines:

```bash
export MISE_MINIMUM_RELEASE_AGE=0
mise use -g "$package" || exit 1
exec mise x "$package" -- "$bin" "$@"
```

### Why this appears related to Omarchy

Omarchy installs `gh` through the lazy mise wrapper at:

```text
~/.local/bin/gh
```

Its global mise configuration tracks:

```toml
[tools]
gh = "latest"
```

This creates two related failure modes for GitHub HTTPS authentication:

1. `gh auth setup-git` can record the resolved physical executable path, which contains a specific mise-managed version.
2. After that version is replaced or removed, Git retains a credential helper pointing to a nonexistent executable.
3. Replacing the disposable path with Omarchy’s stable wrapper is not currently safe because the wrapper writes mise status information to standard output.
4. Git then rejects that output because it is not valid credential-protocol data.

Relevant Omarchy code:

- [[omarchy-mise-install](https://github.com/basecamp/omarchy/blob/quattro/bin/omarchy-mise-install)](https://github.com/basecamp/omarchy/blob/quattro/bin/omarchy-mise-install)
- [[mise installation configuration](https://github.com/basecamp/omarchy/blob/quattro/install/user/mise.sh)](https://github.com/basecamp/omarchy/blob/quattro/install/user/mise.sh)

GitHub CLI normally configures an absolute credential-helper path:

- [[cli/cli#8678](https://github.com/cli/cli/issues/8678)](https://github.com/cli/cli/issues/8678)
- [[cli/cli#3796](https://github.com/cli/cli/issues/3796)](https://github.com/cli/cli/issues/3796)

Related but distinct Omarchy issue involving the mise-backed `gh` wrapper:

- [[basecamp/omarchy#6887](https://github.com/basecamp/omarchy/issues/6887)](https://github.com/basecamp/omarchy/issues/6887)

### Steps to reproduce

1. Use the Omarchy-provided mise installation and wrapper for `gh`.

2. Authenticate with GitHub over HTTPS and allow GitHub CLI to configure Git:

```bash
gh auth login --hostname github.com --git-protocol https --web
gh auth setup-git
```

3. Inspect the resulting credential helper:

```bash
git config --show-origin --get-all credential.https://github.com.helper
```

4. Confirm that it points inside a version-specific mise installation:

```text
!/home/user/.local/share/mise/installs/gh/<version>/.../bin/gh auth git-credential
```

5. Upgrade `gh` through the Omarchy/mise workflow so that the previous version is no longer installed.

6. Run:

```bash
git push
```

7. Git attempts to execute the deleted binary and falls back to an interactive username prompt.

8. Change the helper to Omarchy’s stable wrapper:

```text
!/home/user/.local/bin/gh auth git-credential
```

9. Run `git push` again.

10. Git rejects the mise status line emitted by the wrapper:

```text
warning: invalid credential line: mise ~/.config/mise/config.toml tools: gh@<version>
```

### Expected behavior

Updating a mise-managed `gh` installation should not invalidate GitHub HTTPS authentication.

The credential helper should use a stable, silent command that resolves the currently configured mise version:

```text
!mise exec --quiet gh -- gh auth git-credential
```

The helper must not:

- Reference a disposable version-specific path.
- Print mise installation or selection messages to standard output.
- Trigger an interactive tool installation or update during a credential request.
- Modify unrelated credential-helper entries selected by the user.

### Actual behavior

After a mise-managed `gh` update, Git can remain configured with a path to a removed executable.

Using the stable Omarchy wrapper as the helper causes a second failure because the wrapper emits non-protocol text before executing `gh auth git-credential`.

In both cases, `git push` falls back to requesting a GitHub username even though `gh auth login` completed successfully.

### Confirmed workaround

Replacing only the affected GitHub and Gist helper entries with a silent mise invocation resolves both failure modes:

```bash
git config --global --replace-all \
  credential.https://github.com.helper \
  '!mise exec --quiet gh -- gh auth git-credential' \
  '^!\(.*/mise/installs/gh/.*/gh\|.*/\.local/bin/gh\) auth git-credential$'

git config --global --replace-all \

## Comments
