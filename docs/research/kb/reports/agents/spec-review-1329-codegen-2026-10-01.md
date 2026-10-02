# Spec review (mattpocock code-review, Spec axis) — #1329 `64fd545e...a9e633d1`

Reviewer: general-purpose subagent (Opus), read-only. Persisted verbatim by the coordinator.

---

Spec-axis review of a9e633d1 (#1329, with the owner change making the drift-verdict enum the pilot). I made no edits. I ran one read-only check: `uv run --project python --locked --group codegen dotfiles-setup codegen-check` returned rc=0 ("every generated module matches its job"). That is the in-sync path only; I ran no failure case. I also read datamodel-codegen 0.83.0's own exit codes (`__main__.py:221`): OK=0, DIFF=1, ERROR=2, KeyboardInterrupt=3. They match how `check()` maps rc into the 0/1/2 verdict.

**(a) Missing or partial**
1. Spec: "FAIL arms: hand-editing the generated file fails lint; changing the schema without regenerating fails lint". Neither case runs against the real generator. `test_check_combines_the_native_rc_and_the_stale_scan` hard-codes the native rc (0, 1 or 2) through the `run` seam. Nothing in the diff shows `--all-jobs --check` actually returning 1 after a hand edit or an unregenerated schema change. Real-integration-evidence asks for a real invocation plus its failure case, so this is partial.
2. Spec: "generates a msgspec model" / "`output-model-type = msgspec.Struct`". The setting is configured, but the pilot is a bare integer enum, so the output is a plain `IntEnum` (`generated/drift_verdict.py`). The msgspec.Struct output path is never exercised. `use-annotated` and `field-constraints` are untested for the same reason. The owner change explains this, but the Struct half of the toolchain is still unproven.
3. Spec: "Gate matrix green". The diff can't show this, and I don't see lint, pytest, verify or lint-docs evidence. The suites.toml and docs changes mean `verify` and `lint-docs` both apply.

**(b) Scope creep (minor)**
- These generator options weren't in the issue's list: `use-standard-collections`, `use-schema-description`, `target-python-version = "3.14"`. They are harmless, but the comment justifies them as "mirrors knowledge-base" rather than by the spec.
- The new `workflow.codegen-toolchain-wired` contract in suites.toml and the `python/AGENTS.md` section are repo convention, not asked for. Acceptable.
- A test docstring says "refresh.yml and hk read these as raw rcs". Nothing in refresh.yml consumes `DriftVerdict` or codegen. Its drift steps are the image-lock checks at lines ~332-397, so the claim is unsupported.

**(c) Looks implemented but may be wrong**
1. Spec: "0 in sync / 1 drift / 2 error" (the schema `$comment` says these "must never collapse"). `codegen_check_main` only catches `OSError, KeyError, TOMLDecodeError, ValueError`. If `jobs` is the wrong type, the resulting TypeError or AttributeError goes uncaught, Python exits 1, and the gate reports drift. That is exactly the collapse the pilot exists to prevent (S29-00b F4). An outer `except Exception` → ERROR, or a type check on the config, would close it.
2. Spec: "plus a stale-generated-file scan". `stale_modules` only globs the top level of `generated/` (`glob("*.py")`). A module in a subpackage is never scanned, and any job whose `output` points outside `generated/` is never checked. That is fine for today's single job, but it is narrower than "generated file" in general.
3. Spec: "decodes a valid fixture". The test decodes inline byte literals (`b"1"`), not a fixture file. This is minor, and the rejection test (`b"3"`) does satisfy "rejects an invalid enum value".

The hk step runs with no glob, so it runs every time; that is correct for a gate that has to catch schema edits.
