# Receipt template — copy to `docs/receipts/<issue>.md`

**Hand-written. There is no tool, and that is deliberate** — see
`docs/specs/ticket-bound-receipts.md` § "Decision". Three adversarial review rounds killed the
automation spine, and the three-ticket pilot that ran in its place (#437, #438, #440) was **judged
on 2026-08-01**: keep the practice, **still build nothing** (§12). This template carries the pilot's
three edits — `Kind` dropped, the control arm promoted to a required field, the one-sentence Verdict
cap dropped. **Use it for every `wayfinder:*` ticket.**

**Fill it as you work, not at resolution time.** A receipt written from memory at close is the
failure mode the whole exercise exists to catch. This is the same discipline
`.claude/rules/notepad-enforcement.md` already requires.

**If a review finding can be settled by running something, run it before writing the disposition.**
Across the pilot's 87 findings exactly one was refuted, and it is the only one settled by a probe
rather than by argument — the probe also produced a better measurement than the claim it defended.
See § 12.5 of `docs/specs/ticket-bound-receipts.md`.

Delete this header block when you copy it. Delete nothing else — **an empty section is an answer**,
and "none" written down is worth more than a section quietly removed.

---

# Receipt — #<n>: <ticket title>

**Verdict:** <the answer, stated so a reader who opens only this line is not misled. Keep it as
short as the truth allows, and no shorter — the pilot's four verdicts all needed their conditions
attached, so a length cap was dropped rather than kept and ignored.>

**Resolved:** <YYYY-MM-DD>

## Sources — what I actually opened

<Every primary source. A path in this repo, a URL, a doc page. If a decision is about a third-party
tool and this list does not contain that tool's own docs, that is the miss #449 was filed about,
visible on the page.>

- `path/or/URL` — one line on what it settled
- …

**None opened:** <required if the list is empty — say why in a sentence.>

## Prior art — the search I ran

**Query:** `<the actual command or search terms>`
**Corpus:** `docs/research/kb/reports/`, `docs/specs/`, …

### Control arm — REQUIRED, and run it before you believe any result

**Known-present term:** `<term>` → **N** hits
**Known-absent term:** `<term>` → **0** hits

Both lines, with real numbers, or the search below is not evidence
(`.claude/rules/probes-need-a-control-arm.md`).

**This is the field that has earned its place.** In #440 the whole search was *broken* — zsh does
not word-split an unquoted variable, so the corpus collapsed to one nonexistent path, `2>/dev/null`
ate the error, and every query returned 0. A thin search and a blind one look identical; only this
field tells them apart. If the known-present arm returns 0, **your probe is broken, not the world** —
fix it and re-run before writing anything below.

| Hit | What I did with it |
|---|---|
| `path` | read — <what it changed> **or** dismissed — <why it does not apply> |

**Every hit gets a row.** Finding the prior art and not reading it is the exact failure this field
exists to catch, and it is invisible unless the dismissal is written down.

## Adversarial review

**Lens:** codex-reviewer | grok-reviewer | /mattpocock-skills:code-review | none
**Verdict:** clean | needs-attention | not-run
**Findings:** <n> — <where the full report is persisted>
**Disposition:** <accepted / refuted, and where the reasoning lives>

**Not run:** <required if `lens: none` — say why in a sentence. "Not run" is a legitimate answer;
a silently absent section is not.>

## Notes

<Anything the next reader needs: dead ends, what was nearly done and why it wasn't, what to
re-check if this is revisited.>
