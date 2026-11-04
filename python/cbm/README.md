# cbm commands

`cbm install` installs and verifies the live agent setup. `cbm verify` checks it.

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
