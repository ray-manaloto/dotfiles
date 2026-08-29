# fable-advisor — #808 wiring-contract verdict (2026-08-29)

Agent: `fable-orchestrator:fable-advisor`. Read-only. Verbatim.

## Brief (what was asked)

Should commit `8984826` additionally carry a `workflow.pytest-in-ci-wiring`
contract in `python/verification/suites.toml`, or ship without one? Session was
operating under an explicit YAGNI-extremist directive, so the bar for adding
anything was high. Verdict requested, not a survey. Evidence supplied: the three
levers of the #808 fix, the case for (ci.yml's own #354 quiet-gate comment, the
`workflow.*-wiring` precedent) and against (`require_tokens` is a substring
assert that cannot assert ORDER; a weak gate manufactures a feeling of coverage).
Second question: validate or refute the `conftest.py` `$CI` hook against the more
idiomatic `-m "not host_only"`.

## Verdict (verbatim)

> Verdict: ADD — but the minimal one-token form, not the house's usual multi-path chain. And the conftest `$CI` hook is correct; keep it.
>
> ## Contract: ADD, one path, ~one token
>
> The YAGNI test here is "which regressions are silent?" — and the three levers fail asymmetrically:
>
> - Drop `fetch-depth: 0` → the 7 merge-base tests FAIL loudly in CI. Self-enforcing.
> - Re-narrow `install_args` → the 7 tool-shelling tests FAIL loudly. Self-enforcing.
> - Delete `tests/conftest.py` → the 5 host_only tests RUN and fail loudly on the runner. Self-enforcing.
> - Delete the `Run pytest` step → **nothing anywhere goes red, ever.** This is the only silent path, and it is byte-for-byte the #778/#808 shape — plus your own `ci.yml` comment on the sibling KB-checkout step already declares "a gate that goes quiet when its own wiring disappears is the #354 bug one level up" as house doctrine *in this very job*.
>
> So the contract should bind exactly that one seam and nothing else. [one-token `[[suite]]` shape supplied]
>
> Description should state plainly (prune-scoping style) what it cannot do: presence not correctness — it proves the step exists, not that the install feeding it is full. That's acceptable because the other levers carry their own alarms (above); say so in the description so a future reader doesn't "strengthen" it.
>
> Two conditions before writing it: run `mise run token-check` first (the token must bind exactly one site — house rule, and there may be other pytest mentions in the file); and don't add tokens for conftest.py / pytest.ini / fetch-depth — every one would be decorative, and decorative tokens are the "feeling of coverage" failure you're worried about.
>
> ## conftest vs `-m`: your reasoning is correct
>
> Confirmed pytest semantics: `addopts` values are **prepended** to the command line, so a CI-side `-m` comes later and wins outright (`-m` is a plain store option, last-one-wins — no anding). A CI `-m` would have to restate `"not image_exec and not codex_exec and not host_only"` and would silently re-enable `codex_exec` (real money) the day the ini expression grows. Same defect applies to the `PYTEST_ADDOPTS` env-var route — it's inserted after ini addopts, so its `-m` also replaces. The `pytest_collection_modifyitems` hook is the pattern pytest's own docs give for env-conditional marker skipping; it composes with the ini `-m` instead of racing it, and the skip reason shows in `-rs`. The only lazier alternative — a module-level `skipif(os.environ.get("CI"))` decorator — saves the conftest file but loses the registered marker and repeats itself 5×. Ship the conftest as written.

## Disposition

ACCEPTED. Contract landed as `f798ec2`, one token, control-armed both directions
(token binds 1 site rc=0 / invented token rc=1; deleting the step's `run:` line
took `verify` 138→137 passed, naming the contract). Merged in PR #810.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the repo under advisement.
