# Coding standards

The reviewer reads this file; `mise run review:python` hands it to a read-only Codex reviewer.
Rules that a tool can check live in that tool (ruff ALL, ty, coverage, `codegen --check`); this
file holds the judgement calls. Each finding cites the rule number and `path:line`.

## Python

1. **Generated code stays generated.** Models, types and enums come from the JSON Schema through
   `codegen`; a needed change goes into the schema or the codegen flags. Hand-written code around a
   generated model is a finding unless it says why the library cannot take the model as it is.
2. **Real seams.** Tests run the real tools (git, cmake, mise, usage, compilers). A stand-in
   executable is for a tool that cannot run in a test (hours long, paid, networked) and does the
   same observable job: same arguments in, same files and output out. `monkeypatch` touches only the
   environment and `PATH`, never package internals.
3. **Tests assert what a user sees**: exit code, JSON events, files on disk. A test that only
   reaches a line for coverage, or restates a third-party tool's behaviour, is a finding.
4. **Errors are named events.** A step catches only the errors it turns into one JSON error event;
   everything else propagates. A broad `except` names in a comment what it is there to catch.
5. **Latest, unless written down.** A version cap or pin carries a comment with its decision id and
   the condition that removes it.
6. **Suppressions carry their reason.** Every `noqa`, `ty: ignore` and per-file ignore says why, on
   its line or the line above; fixing the code beats suppressing it.
7. **Long waits stay off the event loop** where ruff's ASYNC rules do not reach: child processes,
   network calls and sleeps inside `async def` go through AnyIO (`run_process`, `to_thread`). Quick
   local file operations and test setup may stay synchronous.
8. **Match the surrounding code**: its comment density, naming, one-line module docstrings and
   idiom.
