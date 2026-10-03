# Codex review lens: #1502 saved searches, commit 13c34367 (2026-10-03)

Command:

```
mise exec -- codex exec -s read-only --ignore-rules review --commit 13c34367 -c 'sandbox_mode="read-only"' -m gpt-6-astra -c 'review_model="gpt-6-astra"' -c 'model_reasoning_effort="xhigh"'
```

rc=0, captured to a file. Below is the lens's final message, verbatim apart from removed ANSI codes and a de-duplicated repeat.

> Pagination and failure handling can produce incomplete or missed search diffs and misleading counts. Runtime checks were blocked because uv requires writes unavailable in the read-only sandbox.
>
> Full review comments:
>
> - [P2] Check the result cap on every collected page — python/src/dotfiles_setup/saved_searches.py:593-596
>   If `total_count` rises above 1000 after the first page, this guard stops checking it. Collection then exhausts ten pages and returns `ok, complete=True` despite omitting results, allowing false GONE entries and missed NEW entries. Check the cap on every response and return `uncollectable` when exceeded, consistent with the bounded-search rule (.claude/rules/probes-need-a-control-arm.md#L65-L67).
>
> - [P2] Preserve an answered baseline across failed reruns — python/src/dotfiles_setup/saved_searches.py:905-911
>   A failed snapshot overwrites the last successful observation here. For a sequence of successful collection `{A}`, rate-limit failure, then successful collection `{A,B}`, `_row` reports NEW/GONE as `n/a` on recovery because the previous status failed. The following run compares against `{A,B}`, so B never appears as NEW. Retain the latest comparable observation for URL diffs while tracking the latest failure separately for status reporting.
>
> - [P2] Store failed fan-out rerun counts as minus one — python/src/dotfiles_setup/saved_searches.py:820-822
>   When a repository-scoped issues, discussions, or releases fetch fails or is skipped, `result.items` is empty and this writes `count=0`. The snapshot and report therefore show a measured drop to zero despite no successful measurement. `_fanout_record` and direct searches already use `-1` for this case; apply that convention here too, preserving the failure-is-not-absence distinction (.claude/rules/probes-need-a-control-arm.md#L99-L100).

## Disposition (coordinator annotation)

I checked each finding against the cited lines. All three are confirmed and fixed in the follow-up commit, each with a test:
`test_collect_all_cap_rechecked_on_every_page`, `test_failed_rerun_keeps_last_answered_baseline` and
`test_failed_fanout_rerun_counts_minus_one`.
