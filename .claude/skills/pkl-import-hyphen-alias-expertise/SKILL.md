---
name: pkl-import-hyphen-alias-expertise
description: "Use when a Pkl file imports a module whose filename contains a hyphen (e.g. `hk-common.pkl`): the import needs an `as` alias."
---

# Pkl: alias hyphenated imports

A Pkl import binds the module to a name taken from its filename, and a hyphen
is not legal in that name, so `import "hk-common.pkl"` fails with an
identifier/syntax error that does not point at the import. Alias it:

```pkl
import "hk-common.pkl" as common

hooks { ["pre-commit"] { steps { ...common.hygiene } } }
```

`hk.pkl` and `hk-image.pkl` both use exactly this form. Validate any pkl
change with `mise run lint`.
