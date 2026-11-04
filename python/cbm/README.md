# cbm commands

`cbm install` installs and verifies the live agent setup. `cbm verify` checks it.

Install runs only when both the current directory and the loaded Python package are in primary
Git checkouts on `main`. Running a linked worktree's CLI from a primary checkout does not bypass the guard.
Linked worktrees (including one on `main`), other branches, detached HEADs, and directories
outside a checkout are refused before any setup change, with `install_checkout_refused`,
exit code 1 and a final `failed` Done event. If Git cannot identify the checkout, install
also refuses, and the error message reports Git's startup, timeout or exit failure.
Running `mise run //cbm:install` from the main checkout works as before.
Empty repositories without a commit are refused with the same checkout guidance.

Each Git command used for checkout discovery has a 10-second timeout.
`CBM_INSTALL_GIT_TIMEOUT_SECONDS` can shorten it to a number of seconds greater than zero and at most 10.
Invalid values produce `invalid_setting`
with exit 2 and a message naming the variable, before Git discovery. Actual Git failures remain
checkout refusals with exit 1. SIGINT or SIGTERM during discovery emits the refusal and failed Done
events without setup changes, then exits with status `128 + signal`.

For a deliberate install from another checkout, opt in for that invocation:

```text
CBM_INSTALL_ALLOW_NON_MAIN=1 mise run //cbm:install
```

The same variable works with `cbm install`; only the exact value `1` opts in. This permits
changes to the live setup; it does not isolate the installer. `cbm verify` remains read-only
and works from any directory without an opt-in.

The upgrade interface currently recognizes these forms but returns a `command_failed`
error with exit code 1; execution arrives in later tickets of #412:

```text
cbm upgrade
cbm upgrade check|trial|review|prepare
cbm upgrade trial --candidate VERSION
cbm accept CHANGE_ID --reason TEXT --public-reason TEXT
```

Both acceptance reasons are required. For values beginning with a hyphen, use the equals
form, for example `--reason=-x --public-reason=-y`. Invalid syntax returns `invalid_usage`
with exit code 2. Existing install/verify usage messages remain unchanged.
