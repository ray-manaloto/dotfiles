# Fix brief: coord-router free-text routing gap (2026-10-04, rev 2)

Rev 2 (after run 9c669e3f stopped on licensed dissent, report
`docs/research/kb/reports/agents/coord-router-freetext-2026-10-04.md`): the
transcript-representation premise is corrected below (§3.1, §7 E), and the S0
probe result changes where the decider runs (§3.3).

Ray (2026-10-04, verbatim): "/codex-sdlc-team to review and fix", answering
this finding about `docs/specs/coord-router-2026-10-04.md` (rev 2):

> In the router design, only messages that start with fixed keywords get
> rerouted. Everything else still goes to the coordinator … free-text lane
> reports and relays, which make up a lot of the coordinator's load today …
> the coordinator's workload drops less than you may expect, and lanes must
> learn the keywords. You wanted lanes to have less to think about.

## 1. Objective

Amend spec rev 2 (S1, S2, and anything they touch) so that the router moves
the MAJORITY of coordinator-bound traffic — including free-text lane reports,
relays and status updates — to the right specialist WITHOUT lanes learning a
keyword grammar, while never losing a message and keeping python as the
decider. Produce rev 3 of the spec plus a MEASURED basis for the choice.

## 2. Files (allowlist — edit only these)

- `docs/specs/coord-router-2026-10-04.md` (rev 3, in place; keep the "Ray
  rulings" section verbatim)
- `docs/research/kb/raw/coord-router/inbound-sample-2026-10-04.jsonl` (new: the
  labelled sample)
- `docs/research/kb/reports/agents/coord-router-freetext-2026-10-04.md` (new:
  the measurement + decision report, ending with `## GitHub repos touched`)

## 3. Interfaces / evidence to produce

1. **A labelled corpus of real inbound coordinator messages.** Source: the
   coordinator session transcripts under
   `~/.claude/projects/-Users-rmanaloto-dev-github-ray-manaloto-dotfiles/*.jsonl`,
   where a peer delivery is a record with `type=attachment`,
   `attachment.type=queued_command`, `attachment.origin.kind=peer`, body at
   `attachment.prompt` (measured by run 9c669e3f: e.g. recipient
   `a629f1c6-….jsonl:368`; `:348`/`:367` are enqueue/remove copies of the same
   message — DEDUPLICATE by message id). User-text records carrying
   `<cross-session-message>` tags are a second representation of some of the
   same messages; dedupe across both. Plus `.agent/plans/handoff-inbox/*.md`.
   Run 9c669e3f counted 377 unique peer attachments across 27 coordinator
   sessions of 2026-10-03/04 — label a stratified sample of at least 150. Sample at least 150 messages across at
   least 5 coordinator sessions of 2026-10-03/04. Store sender name, first 300
   chars, and a hand label from {slot-arbiter, shipper, question-batcher,
   handoff-scribe, coordinator}. Never store credentials; strip any line that
   looks like a token.
2. **Coverage numbers** for each candidate tier on that corpus:
   (a) keyword grammar (rev 2); (b) sender-derived default (a lane's role or
   brief declares where its reports go, e.g. "READY sha" lanes → shipper);
   (c) structured envelope written by a `submit`/skill helper instead of the
   lane's free text; (d) LLM classification (`$.model.classify` in-mod with
   fixed labels, or a python Anthropic-SDK haiku call) with a confidence
   threshold, "unsure → coordinator". Report % routed off-coordinator and %
   misrouted for each, and for the combined chain.
3. **The chosen chain** in S1/S2 interfaces. S0 (report §8) measured that
   readdressing inside the mod's `session.send` FAILS under auto mode
   (classifier "no verdict"), while a native PreToolUse settings hook on
   `SendMessage` returning `updatedInput` WORKS — so the decider runs in
   PYTHON inside that PreToolUse hook (the `scripts/pretooluse-guard.sh` →
   `hook_guard` entry point), not in TypeScript. `$.model.classify` returns
   `string | undefined` with no confidence (run 9c669e3f finding), so an LLM
   tier, if chosen, must be a python-side call with an explicit abstain label
   and a measured latency/cost inside the hook's time budget; say which auth
   it uses without printing any credential. State determinism controls (fixed label set, cached
   decision per message id, decision + confidence written to the PR2 event),
   cost per message, and the misroute recovery path (a specialist can
   "return to coordinator" with one call).

## 4. Constraints

- Rulings in the spec bind (Q3 "neither"; one shipper per repo; one heavy run
  host-wide; ruled slot order; build on PR2; batcher + watcher; containers out
  of scope v1). Python decides; TS transports. Mods are never sole enforcement.
- Lanes must NOT be required to learn keywords; a helper may emit structure.
- Never drop or silently misroute: low confidence → coordinator, and every
  routing decision is auditable.
- Do NOT implement S0–S5 code, do NOT run pytest/lint/verify/any mise gate,
  do NOT push, do NOT spawn Claude sessions, do NOT edit outside the allowlist.
  Reading transcripts and repo files is allowed; network research allowed.
- Print presence, never values, for any credential (secrets rule §7).

## 5. Verification

- The report states corpus size, sessions sampled, the label distribution, and
  per-tier coverage/misroute with the counting command shown.
- Control arm: the corpus extractor must find a known message (this lane's
  own delivery to the coordinator, summary "coord-router deliverable: report,
  ranked specs, Ray decisions", 2026-10-04) — if it does not, the extractor is
  blind.
- Spec rev 3 has no S1/S2 PREMISES row citing a line that does not exist.

## 6. Commit

caller (the coord-router lane commits after review).

## 7. PREMISES

- L rev-2 grammar and "unknown → coordinator" — `docs/specs/coord-router-2026-10-04.md` §S1.
- I `$.model.classify(text, labels)` — bundled types 2.1.289 :2551 (raw copy
  `docs/research/kb/raw/coord-router/mod-api-session-send-receive.d.ts.txt`, appended block).
- E peer deliveries are transcript `attachment` records (`queued_command`,
  origin `peer`, body `attachment.prompt`) — measured by run 9c669e3f,
  recipient `a629f1c6-a768-4d31-bfb0-554130b32258.jsonl:368`.
- E S0: PreToolUse `updatedInput` readdress delivered under auto mode; mod
  `session.send` readdress refused — `docs/research/kb/raw/coord-router/s0-probe/`.
- A the 2026-10-03/04 coordinator sessions are representative of load.
