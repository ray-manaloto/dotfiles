---
name: token-check
description: Prove a candidate contract token binds exactly one site BEFORE writing the contract, via `mise run token-check -- <file> "<token>"...`. Use whenever adding or editing a `[[suite]]` in `python/verification/suites.toml`, choosing `per_path_tokens` for a new gate, or reacting to a `contract_token_uniqueness` / `token-audit` finding. Run it while picking the tokens, not after — a token matching more than once can be satisfied by a stand-in, so the contract silently asserts less than it claims, and that is how a deleted registration stayed green.
user-invocable: true
---

# token-check: pre-flighting a contract's tokens

```bash
mise run token-check -- <file> "<token>" ["<token>" ...]
mise run token-check -- <file> "<token>" --expect 2   # deliberate multiplicity
```

Same predicate as the `contract_token_uniqueness` gate, asked while the answer
still costs one edit. The gate can only speak once the contract exists, so its
finding arrives after the work. `python/src/dotfiles_setup/token_audit.py` holds
both scopes; the task is a thin caller.

Both arms print. `OK` lines are the point as much as the failures — you are
about to commit these strings into a gate, so "I checked" has to be visible
rather than inferred from silence.

## What a good token is

The count is necessary, not sufficient. A token that binds once and is still
worthless is the common failure, so choose on meaning first and *then* check.

**Bind a call site.** `if changes_apt_pin_inputs(paths):` asserts the function
is *wired*; `def changes_apt_pin_inputs(` asserts only that it exists. #299
shipped the definition form, and deleting the entire wiring line left the
contract green — the token survived in a comment and in a docstring.

**Prefer the line whose deletion is the realistic regression.** Ask what the
regression would actually look like, then bind that. Renaming a function is
rare; deleting the line that calls it is not.

**A definition or a bare name can be satisfied by prose.** Comments, docstrings
and the contract's own description all live in the same file the token is
counted against.

## Reading the three verdicts

| Verdict | Means | Do |
|---|---|---|
| `OK` | binds exactly the expected sites | use it |
| `AMBIGUOUS` (> expected) | a stand-in can satisfy the contract | lengthen it until it names one site |
| `MISSING` (0) | wrong path, or wrong spelling | check the path first — it is the more common of the two |

`MISSING` is worth a beat: a token counted against the wrong file reads exactly
like a token that is absent, and the pre-flight cannot tell them apart. Confirm
the path is the one the contract will name.

## When multiplicity is right

`--expect N` exists because some bindings legitimately match twice — the
`AMBIGUITY_ALLOWED` map in `token_audit.py` documents 18, each with a reason
(one clause computing a hash and a sibling clause re-checking it, for instance;
both clauses *are* the contract). Reach for it when the second site is part of
what you are asserting, not to quiet a token you would rather not rewrite.

A token you allow to match twice must also get an `AMBIGUITY_ALLOWED` entry, or
the whole-suite audit will report it on the next `mise run verify`.

## Then write the contract

The pre-flight checks one axis. Two others are the author's:

- **`per_path_tokens`, not bare `tokens`** — a bare list is a UNION across every
  named path, so one file carrying the token satisfies the contract for all of
  them. It is also invisible to the uniqueness audit.
- **`paths_required = true`** is the default and should stay so; a declared path
  that no longer exists must fail the suite rather than quietly drop out.

`python/AGENTS.md` § "Verification contracts" carries both in full.
