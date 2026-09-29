# omarchy-mise-install stubs recurse into themselves when the tool is not installed, forking until the machine stalls

- URL: https://github.com/omacom/omarchy/issues/13177
- state: open | author: rudivdm | created: 2026-09-24T20:16:15Z | closed: null | merged_pr: n/a
- labels: bug

## Body

**Affected:** `omarchy` 4.0.4-1 (`/usr/share/omarchy/version` reports `4.0.0.alpha`), `/usr/bin/omarchy-mise-install`

## Summary

The launcher stub that `omarchy-mise-install` writes re-executes itself, without
bound, for any tool that is named in a stub but not actually installed in mise.
There is no error message and nothing crashes — the machine simply becomes
progressively unresponsive, so the cause is easy to misattribute to whichever
application happens to invoke the stub.

## Mechanism

`omarchy-mise-install` writes:

```bash
#!/bin/bash
export MISE_MINIMUM_RELEASE_AGE=0
mise use -g --quiet "<tool>" || exit 1
exec mise x "<tool>" -- "<bin>" "$@"
```

`mise x <tool> -- <bin>` falls back to a **PATH lookup** for `<bin>` when the
tool does not provide a binary of that name. The stub lives in `~/.local/bin`,
which is on PATH. So mise re-executes the stub, the stub calls mise, and the two
recurse.

Crucially, **PATH ordering does not protect against this.** `~/.local/share/mise/shims`
is appended before `~/.local/bin` in `default/bash/env-bootstrap`, but a shim is
only created for a tool that is actually *installed*. For the failure case — the
tool is missing — no shim exists, so the stub is the only candidate on PATH and
wins regardless of order.

This makes the failure self-sustaining: the tool is missing, so `mise use -g`
cannot fix it on the next run either.

## Reproduction

Any tool whose install fails or has not yet run. `github:can1357/oh-my-pi` is a
convenient example because `install/user/mise.sh` and migrations
`1785617047.sh` / `1785846769.sh` all install it:

```bash
# with github:can1357/oh-my-pi absent from `mise ls --installed`
omarchy-mise-install github:can1357/oh-my-pi omp
omp --version
```

Measured on a 20-core i7-13800H:

| | |
|---|---|
| processes spawned | **20,938 in 20 s** (~1,000/sec) before being killed |
| return | never |
| system fork rate, sustained | 3,607/sec (idle baseline ~40/sec) |
| load average | 7.5 |

## Why it is hard to diagnose

The stub is invoked per shell, not in a loop, so each invocation is a fresh
detonation rather than one continuous spike. In our case an editor set an
environment variable that made every one of its terminal panes call `omp` for a
status line — so "terminals in this editor are slow, but terminals elsewhere are
instant" was the presenting symptom, and the editor looked like the culprit. A
native terminal opened in 194 ms throughout; the editor's panes were unusable.
Nothing logged an error.

`ulimit`'s per-user process cap (37,828 here) is what keeps this from taking the
machine down outright — it saturates instead.

## Suggested fix

Emit a re-entry guard in the generated stub. Naming the guard after the binary
rather than using one shared variable keeps a tool that legitimately shells out
to a *different* wrapped tool from being mistaken for recursion:

```diff
 rm -f "$HOME/.local/bin/$command"
+guard="_OMARCHY_MISE_GUARD_$(printf '%s' "$command" | tr -c 'A-Za-z0-9_' '_' | tr '[:lower:]' '[:upper:]')"
 cat >"$HOME/.local/bin/$command" <<EOF
 #!/bin/bash
+# mise resolves the command below by PATH when the tool does not provide it,
+# which finds this stub again. Fail fast rather than recursing until the machine
+# runs out of processes.
+if [ -n "\$$guard" ]; then
+  printf '%s: mise could not provide "%s" from tool "%s" (is it installed?)\n' "$command" "$bin" "$package" >&2
+  exit 127
+fi
+export $guard=1
 export MISE_MINIMUM_RELEASE_AGE=0
 mise use -g --quiet $package_arg || exit 1
 exec mise x $package_arg -- $bin_arg "\$@"
 EOF
```

An additional guard worth considering: have the stub verify the tool is installed
(`mise ls --installed <tool>` prints nothing when it is not) and fail with a
clear message rather than handing an unresolvable command to `mise x`.

## Secondary, minor

`mise use -g` runs on **every** launch, not just the first. Each invocation
rewrites `~/.config/mise/config.toml` and costs ~100 processes; measured with the
config file being rewritten every few seconds on an otherwise idle machine.
Making it conditional on the tool being absent took `gh --version` from 104
processes to 75, and stopped the config churn entirely. The comment in the script
explains the `MISE_MINIMUM_RELEASE_AGE=0` export as wanting fresh releases, which
a first-use-only install still satisfies for a newly installed tool — though it
would no longer auto-upgrade on every run, which may be the intended behaviour
and is the reason to treat this as separate from the bug above.


## Comments
