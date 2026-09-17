# AgentsView Product Handoff — 2026-09-16

This handoff records four defects observed while AgentsView reviewed the
dotfiles `/session-handoff` workflow. AgentsView is another project's product:
these defects are evidence for that project's agents and are deliberately not
fixed in dotfiles.

Source:
`docs/research/kb/reports/agents/agentsview-session-handoff-review-2026-09-16.md`.
The pass used the remote daemon at `http://127.0.0.1:8080`, passed the token
file by path, and excluded its own review session from searches.

## D1 — Semantic search unavailable and stalled

**Verbatim evidence:** `--hybrid` exits **rc=1**:
`fatal: semantic search not available: enable [vector] in config.toml and run 'agentsview embeddings build': index is building: 9% complete`.
The brief records the same **9%** measured hours earlier; it had not moved.

Evidence artifact: probe D, `av/hyb.err`.

Impact: every prose probe in the pass was FTS and therefore matched literal
tokens only. A learning phrased without those exact words was invisible.

## D2 — Default corpus silently excludes most sessions

**Verbatim evidence:** `session list` printed
`Excluded 3515 sessions by default: 3296 one-shot, 219 automated`, and
`session search --help` showed `--include-one-shot`,
`--include-automated`, and `--include-children` all default off. Subagent
sessions were therefore excluded from search by default.

Evidence artifacts: `av/list.json` line 1 and `av/help_search.txt` lines
21–23.

Impact: a search omitting every subagent transcript cannot answer what
delegates found. The result output did not announce that evidentiary gap.

## D3 — Claude sessions have duplicate Codex mirror records

**Verbatim evidence:** each Claude session had a byte-identical `codex:…`
mirror record, and both were returned as separate sessions.
`d5e77df3` @1074 and `codex:01a0a4e4…` @1265 carried the same sentence;
`1a35b247` @352 and `codex:019ffa2f…` @426 did likewise.

Evidence artifacts: probes 5, 6, 20, and 22.

Impact: hit counts and claims about distinct sessions were inflated roughly
twofold. The review manually restricted multi-session claims to distinct
`claude` session IDs.

## D4 — `--exclude-system` invalid JSON was not reproduced

**Verbatim evidence:**
`session search "session-handoff" --fts --json --limit 3 --exclude-system`
returned **rc=0** and well-formed JSON.

Evidence artifact: probe E, `av/exsys.json`.

Impact: this is **not reproduced**, not fixed. The earlier failing command
shape may have differed, so the defect should remain open until the original
shape is recovered and replayed with both a failing and a passing control.

## Requested disposition by AgentsView maintainers

- D1: expose embedding-build progress/failure state and make a stalled build
  distinguishable from a live one.
- D2: surface corpus exclusions in every result envelope, especially child
  session exclusion.
- D3: deduplicate mirror records or identify canonical/mirror lineage in
  machine-readable output.
- D4: recover the original failing invocation before closing; retain the
  successful command above as the negative reproduction.

No dotfiles implementation is requested by this handoff.
