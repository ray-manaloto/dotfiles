Implemented all §8 corrections with no dissent. The caller’s staged changes remain staged and untouched; no commit was created.

§8 status:

1. Done — transport exceptions are isolated per source; GraphQL shapes and socket timeouts are classified correctly.
2. Done — credential headers reject CR/LF and non-Latin-1 values without exposing secrets.
3. Done — chunked HTTP reads enforce the shared deadline and 8 MiB limit.
4. Done — timed-out subprocess groups receive SIGTERM, then SIGKILL.
5. Done — nonzero exits include redacted stderr tails.
6. Done — GitHub items prefer web `html_url`.
7. Done — Context7 resolves from the repository name.
8. Done — reused output directories clear every owned filename only.
9. Done — releases fetch 100, filter whole-word query terms, and honor `--limit`.
10. Done — every child environment has credential-scrubbing coverage; `LAST30DAYS_TRUST_PROJECT_CONFIG` is removed.
11. Done — added the complete hermetic/F9 branch coverage.
12. Dissent — none.

Changed paths:

- [research_fanout.py](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/research_fanout.py)
- [test_research_fanout.py](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/tests/test_research_fanout.py)

§5 final results:

| Command | Exit |
|---|---:|
| Focused pytest — 50 passed | 0 |
| Ruff check | 0 |
| Ty check | 0 |
| `mise run research-fanout -- --list-sources` | 0 |
| `mise run lint` | 1 |

Lint’s sole final failure is an E501 in the caller’s staged [test_workflows_js.py](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/tests/test_workflows_js.py:561). Fixing it would violate the allowlist.

Additional gates:

- Full pytest: exit 0 — 3928 passed, 11 deselected.
- `mise run verify`: exit 0 — 165 passed, 0 failed, 4 policy skips.
- Ruff format and `git diff --check`: exit 0.
- Graphify was queried first but reported its graph stale, so the live source and cited review reports were used as authority.