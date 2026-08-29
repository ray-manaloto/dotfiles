# Advisor verdict — #803, commitment boundary before shipping

`fable-advisor` (Fable 5, read-only). Consulted per the orchestration doctrine's
"once before declaring a multi-step deliverable done".

**Brief (persisted per clear-prep §3c):** given branch head `c232d67`, the exact
files to read, the four options already rejected *with reasons* (the issue's own
`grep "vsc-dotfiles-${_hash}"` one-liner; emitting bare image ids; `docker rmi
-f`; a guard keyed on RepoDigest presence), the safety model, and the accepted
gap — with an explicit instruction to attack the accepted gap as the judgement
call the architect was least sure of. All evidence pasted: live probe output with
its control arm, the three sharp-mutation results, the full-suite rc with its one
pre-existing failure bisected to bot PR #778, and `verify`/`lint` rcs. Three
worries stated honestly rather than only the green results: three review rounds
each finding something real; the untagged-overlay path having no live arm; and
`mise run prune` never having been executed end to end. Later amended by
SendMessage with the live four-arm probe that closed the third worry and
sharpened the residual (an untagged base variant is indistinguishable from an
untagged overlay by tags, digests *or* OCI labels).

---

## Verdict: SHIP

> The risk that decides it is failure **DIRECTION**, and I verified it points the
> safe way.

Re-read the safety core (`devcontainer_names.py:774-960`) and the task glue
(`mise.toml [tasks.prune]`) rather than taking the architect's summary.

**The structural fact that settles the decision: every residual unknown fails
toward refusal-or-loud-abort, never toward foreign deletion.**

- Admission requires positive proof (own workspace label, or a
  fixed-length-hash-prefixed / full-sha256-derived tag shape — neither can
  prefix-collide with another clone, since `workspace_hash` is fixed length).
  Unknown image id → warn + skip. `/` in any tag OR digest → skip. `docker rmi`
  without `-f` on a wrong bare id → non-zero → `set -euo pipefail` aborts the
  whole task. So the two things flagged as untested — the untagged-overlay path
  and the never-executed `mise run prune` — can only manifest as "prune removes
  nothing / aborts loudly," which is annoying and recoverable, not destructive.
  The destructive direction runs only through the trust predicate, and that is
  exactly the path the three mutations armed.
- **On three productive review rounds:** not evidence a fourth would find a
  *destructive-direction* defect. Rounds 2–3 found dead code and a mispathed
  control arm, i.e. defects in the **evidence**, and the current evidence
  postdates those fixes. Diminishing class, safe-direction residue. **Stop.**
- **On `mise run prune` never run end-to-end:** the two new capture lines were
  exercised live in exactly the form the task uses; the remaining glue
  (`xargs docker rmi`, plan print) fails loud under pipefail. Acceptable — and
  unavoidable, since running it is the destructive act itself. Its first real
  execution prints the plan first, so a wrong set is visible before anyone
  reports a bug blind.
- **On the accepted gap, attacked as requested: it holds, for a reason the
  writeup understated.** The leaked image is untagged and referenced only by a
  stale pre-#677 container — so recovery is generic docker hygiene (`docker rm`
  the stale container, then `docker image prune`), needing nothing from this
  code. A gap whose worst case is bounded disk with a stock recovery path,
  versus a widened predicate whose worst case is the ticket's own bug — correct
  trade. **Don't reopen it.**

**One non-blocking nit:** `_removal_args` skips a slash-guarded candidate
silently while the C1 branch warns; a matching `logger.warning` there would make
the "(no overlay image resolved)" message diagnosable. Fine as a follow-up, not
worth a fourth round.

## Disposition

Shipped as PR #809. The nit was **not** deferred — it is the same D1 defect class
in the sibling branch of the same function, so it was fixed inline in `f52e85a`
with its own sharp mutation (deleting only the new `logger.warning` takes the
suite 70 → 1 failed).

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the repo advised on.

---

# Addendum — second consult, after the live four-arm probe

Sent mid-flight with new evidence: the architect had reported "the
untagged-overlay path has no live arm", then built one (real
`docker image inspect` over all 43 local images, supplying only the
container→trust pair) and asked two questions about the residual it exposed.

**Verdict unchanged: SHIP.** The four-arm probe "retires the untagged worry
properly (both positive and negative arms on real data — that is the control-arm
shape the rules demand)."

## Q1 — is "unreachable by construction" good enough here?

> **Yes, but not for your reason.**

- **"Unreachable by construction" is the WEAK leg.** It rests on `mise run up`
  being the sole label-stamper forever, and "a future task or a hand-run
  `docker run --label` breaks it silently."
- **What actually carries the decision is blast radius of the REACHED case.** A
  container carrying THIS clone's workspace label that references the untagged
  base variant is, by definition, **this clone's own container** — so deleting
  the image behind it deletes something only this clone was using, and a dangling
  base variant is fully recoverable by re-pull (`mise run sync`). **The invariant
  #803 exists to protect — never delete another clone's image — does not depend
  on this scenario at all.** Worst case is your own clone paying a re-pull,
  triggered only by a configuration nothing currently creates. That is time, not
  loss, and it is self-inflicted.

> State it that way in the receipt: **the construction argument is the
> probability bound, the blast-radius argument is the safety bound.**

## Q2 — what discriminator is left, given tags, digests and OCI labels are all non-discriminating?

The only discriminator you control is **one you stamp yourself**: a `LABEL` on
the overlay image at overlay-build time (the thin host-user Dockerfile / bake
target), which the trust predicate could then require. Tags, digests and
inherited OCI labels are all base-derived — "nothing existing discriminates, you
measured that correctly."

> **Do NOT add it now:** it protects a path whose worst case is a recoverable
> re-pull of your own image, it only covers future builds anyway, and it widens
> the change past the ticket. Note it in the docstring beside the accepted-gap
> paragraph as the upgrade path if the scenario ever materializes, and ship.

## Disposition

Shipped as PR #809 without the label. **The upgrade path is recorded here rather
than in the docstring** — the addendum arrived after the branch had merged. If
the scenario ever materializes, the fix is an overlay-build-time `LABEL` plus a
trust-predicate requirement, not a widened tag heuristic.
