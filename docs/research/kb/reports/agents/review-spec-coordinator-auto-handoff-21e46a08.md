# Spec review (mattpocock) — coordinator-auto-handoff 21e46a08

## Brief

Read-only Spec review. Repo: /Users/rmanaloto/dev/github/ray-manaloto/dotfiles.worktrees/coordinator-auto-handoff-20261002. Diff: `git diff c6b8e825...HEAD` (commit 21e46a08 "feat(coordinator-handoff): auto-handoff at a context limit + session-start mod"). Do not edit anything; do not run tests, lint or any heavy gate.

Spec: docs/specs/coordinator-auto-handoff-2026-10-02.md (read all of it: §0 rulings 1-13 + "Coordinator ruling 2026-10-02b", §1-§8) and the approved requirements list docs/specs/coordinator-auto-handoff-2026-10-02-requirements.md (items 1-23). Known, accepted departures reported by the implementer (do not re-report unless the departure itself breaks a requirement): dataclass-bundled signatures for launch/retire/successor_brief; `retire` wired in the CLI; added `session-start renamed`, `coordinator-handoff name --project/--feature`, `--jobs-dir/--state-dir`, `census(root_pid=)`; census records the outermost process per heavy run; a foreground `claude -n` session has no job record and is treated as unnamed.

Report: (a) requirements the spec asked for that are missing or partial; (b) behaviour in the diff that wasn't asked for (scope creep); (c) requirements that look implemented but where the implementation looks wrong. Quote the spec line for each finding. Under 400 words.

## Report (verbatim)

Spec review of 21e46a08 against `docs/specs/coordinator-auto-handoff-2026-10-02.md` and the requirements list. This was a read-only pass: I edited nothing and ran no gates, and I persisted nothing, so the coordinator needs to save this report.

**(c) Looks implemented, but the implementation looks wrong**

1. **Re-fire does not check whether the handoff failed.** Req 2 says: "Re-fire every +5% over threshold *if the handoff fails*". `decide`/`_judge` (`coordinator_handoff.py:246-260`) never reads `state["launch"]`, which `launch` writes at :641. So a `/coordinator-handoff` that is still running, or has already succeeded, gets a second submit once context grows another 5%. The unattended `/session-handoff` with cold review can easily use that much. The second submit can launch a second successor. Fix: `decide` should answer `fire:false` (for example `"launched"`) once a launch record exists.

2. **The status line misleads in non-coordinator sessions.** Req 1 says "active only in coordinator sessions (by name)". The hook's pre-filter (`register.ts:150-153`) shows `handoff 23%/30%` in every session, lanes included. It only switches to `n/a (not coordinator)` above 30%. Past that point every turn of every session runs `uv run … decide`. P8 assumed this cost was "coordinators only after the role check", but the role check happens inside that process, so the cost is paid everywhere.

**(a) Missing or partial**

3. **The probe and teardown requirements are unmet.** Req 4: "Prove the real submit path with a probe arg before relying on it". Req 19 / ruling 9: "live-probe `claude stop` teardown first". The code has the PROBE path, but the implementer's report (`…-lane2.md:100`) lists every §5.4 live arm as still to do: dry-run, heartbeat, the ERROR arm, PROBE, teardown and the session-start live arm. P2 (`command.run` from `session.measure`) is still ASSUMED. Until those arms run, treat both requirements as unmet.

4. **The early-PR requirement lives only in the coordinator-handoff skill.** Req 8: "push with ssh keepalive … ship that docs branch as a PR early". The coordinator-handoff skill covers it, but the session-handoff skill's "Unattended run" section doesn't mention shipping the PR. The keepalive is claimed ("its push carries the ssh keepalive"), not shown.

5. **Possible unproven assumption in session-start.** §8 says `rename` applies only when there is "no `-n` name". If a bg job record gets an auto-generated `name` even without `-n`, every unnamed bg session would be classed `nonconforming` and never renamed. I can't settle this from the diff; the session-start live arm in §5 would.

**(b) Not asked for**

6. **Unrelated trim in the session-handoff skill.** `.claude/skills/session-handoff/SKILL.md` rewrites the md-size constraints paragraph (the AGM-003/Windsurf text). §2 only asked for "a short 'run by coordinator-handoff' section". It is probably a size-budget offset, but that isn't recorded anywhere.

7. **Small extras worth stating.** Two refusal cases go beyond the spec. `launch` refuses with rc 2 when the census cannot be taken, including under `--dry-run`; §3c lists only two refusal causes. `decide` also adds two reasons the spec doesn't define: `invalid-session-id` and `invalid-percent`. The hook sends both to the ERROR status, which is defensible but should be said.

**Checked and consistent**

- Req 9-12 (name format, launch argv, census contents) and req 13-18 / 20-22 (brief contents) match.
- Retire matches: same-argv liveness, independent inFlight block plus `--accept-inflight`, rc 2 with no launch record.
- The DRY_RUN and PROBE env handling matches, and so do the status strings.
- §8's keep/rename/defer/nonconforming, once per session, and reloading in order all match.

One latent dependency: both the state directory and the main checkout are derived from the python package path, not from the coordinator's cwd. Retire finds the launch record only if `launch` and `retire` run from the same checkout. The brief and skill imply both run from the main checkout, but nothing enforces it.
