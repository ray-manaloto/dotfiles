STATUS: dissent — `mise run lint` is blocked by caller-owned, out-of-allowlist `tests/test_workflows_js.py` formatting errors at lines 204, 206, 207, and 511.

Verification:

```text
uv run --project python pytest tests/test_research_fanout.py -q
EXIT=0

uv run --project python ruff check python/src/dotfiles_setup/research_fanout.py tests/test_research_fanout.py
EXIT=0

uv run --project python ty check python/src/dotfiles_setup/research_fanout.py
EXIT=0

mise run research-fanout -- --list-sources
EXIT=0

mise run lint
EXIT=1
```

Changed paths:

```text
mise.toml
python/src/dotfiles_setup/research_fanout.py
tests/test_research_fanout.py
```

Premises re-probed: none.

I did not run live fanout against real sources beyond `--list-sources`. All tests used injected fake HTTP/process boundaries.

Changes remain uncommitted.

`★ Insight ─────────────────────────────────────`
The implementation keeps exact raw responses separate from normalized results, while a shared per-source deadline bounds multi-call adapters and their canaries.
The public test seams cover all transports without patching internal module behavior.
`─────────────────────────────────────────────────`