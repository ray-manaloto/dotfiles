Implemented §9 only on HEAD `0a908d9e`; no dissent on any item.

### §9 disposition

1. **Done** — bounded post-SIGKILL drain; escaped pipe holder returns within budget. Real-process test: [test_research_fanout.py:575](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/tests/test_research_fanout.py:575).
2. **Done** — `ProcessLookupError`/`PermissionError` tolerated around both `killpg` calls; direct child reaped. [research_fanout.py:276](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/research_fanout.py:276).
3. **Done** — live-child tracking, TERM→KILL cancellation, executor cleanup, and `main()` rc=130. Real-child test: [test_research_fanout.py:659](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/tests/test_research_fanout.py:659).
4. **Done** — total HTTP body deadline enforced using public response APIs; real loopback trickle tests cover Exa and Firecrawl. [research_fanout.py:365](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/research_fanout.py:365).
5. **Done** — short `Content-Length` bodies report `incomplete response`. [test_research_fanout.py:405](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/tests/test_research_fanout.py:405).
6. **Done** — context7 canary independently resolves `library python`, then queries Python docs. [test_research_fanout.py:1125](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/tests/test_research_fanout.py:1125).
7. **Done** — added fail arms for Firecrawl credential validation, ≥3-character release terms, both context7 error sites, and Firecrawl body reading.
8. **Done** — subprocess stderr newlines collapse to ` | `, preserving one summary line per source. [research_fanout.py:544](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/research_fanout.py:544).
9. **Done** — releases now require every retained query term as a whole word. Exact `"is python fixed"` control: [test_research_fanout.py:1020](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/tests/test_research_fanout.py:1020).
10. **Done** — no-repo context7 behavior remains query-based and covered. [test_research_fanout.py:1056](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/tests/test_research_fanout.py:1056).

### §5 verification

- `uv run --project python pytest tests/test_research_fanout.py -q` — **rc=0**, 62 passed.
- `uv run --project python ruff check python/src/dotfiles_setup/research_fanout.py tests/test_research_fanout.py` — **rc=0**.
- `uv run --project python ty check python/src/dotfiles_setup/research_fanout.py` — **rc=0**.
- `mise run research-fanout -- --list-sources` — **rc=0**, all eight sources listed.
- `mise run lint` — initial **rc=1** exposed formatting and test typing issues; after correction, final **rc=0**.

Additional repository gates:

- `uv run --project python pytest tests/ -x -q` — **rc=0**, 3,940 passed, 11 deselected.
- `mise run verify` — **rc=0**, 165 passed, 0 failed, 4 human-only policies skipped.
- `git diff --check` — **rc=0**.

Changed and left unstaged:

- [research_fanout.py](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/research_fanout.py)
- [test_research_fanout.py](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/tests/test_research_fanout.py)

The caller’s three staged documentation files remain staged and untouched. No commit was created. Graphify health/query both returned rc=3 because the graph is stale; I did not rebuild it outside the allowlist and used the cited on-disk findings instead.

`★ Insight ─────────────────────────────────────`
The correction distinguishes inactivity timeouts from total deadlines, and process exit from pipe closure—two boundaries that mocks had previously hidden.
`─────────────────────────────────────────────────`