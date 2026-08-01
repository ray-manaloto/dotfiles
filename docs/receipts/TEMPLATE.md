# Receipt template — copy to `docs/receipts/<issue>.md`

**Hand-written. There is no tool, and that is deliberate** — see
`docs/specs/ticket-bound-receipts.md` § "Decision". Three adversarial review rounds killed the
automation spine; this template is the pilot that runs in its place, on the next three
`wayfinder:*` tickets, to find out which fields are worth anything before anything is built.

**Fill it as you work, not at resolution time.** A receipt written from memory at close is the
failure mode the whole exercise exists to catch. This is the same discipline
`.claude/rules/notepad-enforcement.md` already requires.

Delete this header block when you copy it. Delete nothing else — **an empty section is an answer**,
and "none" written down is worth more than a section quietly removed.

---

# Receipt — #<n>: <ticket title>

**Verdict:** <one sentence — the answer. This exact text goes in the resolution comment.>

**Kind:** research | decision | task | none-required
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
**Control arm:** `<a term known present> → N hits` / `<a term known absent> → 0`
*(per `.claude/rules/probes-need-a-control-arm.md` — a 0-result search is not an answer until a
control has run)*

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
