# Advisor Verdict: #919 (hook-selfcheck PostToolUse wiring) — ship decision

**VERDICT: SHIP**

No third respec round warranted. Read `check_settings_wiring`
(`hook_selfcheck.py:186-253`) at `73e6e77` directly: the for/else logic
requires ALL required substrings AND ALL required matcher tokens to hold in
the SAME entry to pass — a genuine one-entry rule, no pooling, no
matcher-token donation via a decoy. Ran `tests/test_hook_selfcheck.py`
independently: 31 passed, rc=0, including
`test_sibling_entry_matcher_does_not_satisfy_the_owning_entry`,
`test_matcher_tokens_split_across_two_owning_entries_fails`,
`test_session_start_split_across_two_entries_fails`. `test_real_settings_wiring_passes`
and `test_selfcheck_main_passes_on_real_repo` confirm the stricter rule does
not break the real `.claude/settings.json`.

Combined with the architect's 10-shape adversarial battery (3 shapes beyond
lane coverage: qualifying entry in last position, duplicate qualifying
entries, matcher widened to a superset) and three green gates
(lint/pytest/verify), this closes the defect class the ticket was opened for.

**On #954** (no `suites.toml` contract binds the dispatcher): defer. It is a
second, independent gate on top of a check that is now itself correct — not
required to call this class closed.
