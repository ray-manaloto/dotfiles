# premise-verifier — hk v2 migration spec (rev 1), 2026-09-27

Verbatim final report (recovered from the subagent transcript `agent-aae1f4e242d33185c.jsonl`; the agent is read-only).

I only have read tools, so I couldn't write `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/docs/research/kb/reports/agents/premise-verifier-hk-v2-migration-2026-09-27.md`. The full report is below for you to save verbatim.

```
PREMISE REPORT
ROWS: 17 checked — 13 CONFIRMED (1 provenance corrected) / 0 REFUTED / 3 UNVERIFIABLE / 1 ASSUMED (0 checkable)
P1  — CONFIRMED — .config/mise/conf.d/shared.toml:37 `hk = "1.57.0"`
P2  — CONFIRMED — hk.pkl:1,8,11; hk-common.pkl:8(comment),17,18; hk-image.pkl:11,14. pin-parity.toml:78-80 regex `hk@(...)` collects EVERY match, so the comment at hk-common.pkl:8 must be bumped too (the spec does)
P3  — CONFIRMED — hk.pkl:19, hk-image.pkl:19
P4  — CONFIRMED — hk.pkl:42
P5  — CONFIRMED — mise.toml:15 (the line goes on with "— hk editorconfig_checker builtin (#154); host-only…")
P6  — CONFIRMED — mise.toml:180, under [hooks] at :176
P7  — CONFIRMED — tests/test_image_smoke.py:814
P8  — CONFIRMED — workflow_claude_code.py:104-134. The Flag field is `spellings`, not `names`, and there is a third field `optional_value` (:78-83), so spec §3's interface statement is wrong (positional construction still works)
P9  — CONFIRMED — renovate.json:20-27
P10 — CONFIRMED — AGENTS.md:151-154 (the sentence runs across :152-154)
P11 — CONFIRMED — .config/mise/mise.lock:412, .devcontainer/mise-system.lock:5050
P12 — CONFIRMED — mise.lock:6470,6472
P13 — UNVERIFIABLE — provenance fails: cites the research report, not code. The builtin lives only in ~/.pkl/cache/.../hk@2.3.0/hk@2.3.0.zip, which I can't open. Grepping the binary for "editorconfig-checker --fix" found 0 hits; the builtins are not stored as plain text, so that result settles nothing
P14 — CONFIRMED (provenance corrected) — ~/.local/share/mise/installs/hk/2.3.0/.mise-packslip/assets/hk.usage.kdl:283 ("any stale local hooks are cleaned up… Pass `--force-local`"), :285-290
P15 — UNVERIFIABLE — provenance fails: report. The 2.3.0 usage spec (:170) says fix mode "can modify and stage files". `hk fix` help (:247) says nothing about staging. `--stage`/`--no-stage` exist (:50,:61)
P16 — ASSUMED — not contradicted. Only a 4.0.1 cache dir exists (~/Library/Caches/mise/editorconfig-checker/4.0.1/, msgpack I can't read). 3.11.3 ships bin/ec-darwin-arm64
P17 — UNVERIFIABLE — a measurement with no file:line; I have no shell to re-run it
MISSING:
- docs/hk-builtins-audit.md is GENERATED from `hk --version` + `hk builtins` (hk_builtins_audit.py:109-125). :9 records "hk 1.57.0" and it lists 152 builtins, including 6 that v2 removes (:149-157). The committed doc is checked by the hk_audit step (hk.pkl:372-374), tests/test_hk_builtins_audit.py:15 and suites.toml `workflow.hk-builtins-audit` (:2183-2215). If it isn't regenerated, verify steps 4, 6 and 7 fail. Add it to the allowlist and regenerate with `mise run hk-audit`. New builtin names may also trip typos (precedent: typos.toml:41-46 `sherif`), so typos.toml may need an entry
- tests/test_workflow_claude_code.py:90-116 `_EXPECTED_FLAG_TABLES` must equal HK_RUN_FLAGS exactly (:306-314). Adding --junit-xml fails that test unless the table is updated too; name this in the spec
- 2.3.0 adds a hidden global flag `--hkrc <PATH>` that takes a value (usage.kdl:109). It is not in HK_GLOBAL_FLAGS
- P15 has no in-context test: verify step 5 runs fmt on a CLEAN tree, which can't show whether fixes get staged. Add a step: put a fixable defect in a file, run `mise run fmt`, then check that `git diff --cached` is empty
- .devcontainer/mise-runtime.lock has no hk entry (0 hk matches out of 21 tool blocks). The stated reason for regenerating it is wrong; non-blocking
- Stale `hk install --mise` mentions, none asserted by any test or contract: docs/adr/0001-hk-hooks-do-not-run-in-ci.md:7, workflow_hooks.py:4, hk.pkl:406, refresh.yml:77,289, gcc-sha-repair.yml:47. (b) Nothing asserts the postinstall string (suites.toml/tests: 0 hits) or the AGENTS.md fmt sentence (the only hit is AGENTS.md:153)
- (c) No test or contract pins the image-build matchFileNames list. The renovate.json contracts are suites.toml:894-895, :903-904, :1614, none of them on this rule
- The hk 1.57 string in suites.toml:2172 is description text, not a token; the ec comment at mise-system.toml:37-39 stays true
- The AGENTS.md size of 11,605 chars is unmeasured here; `lint-docs` (step 8) gates it
- HK_SKIP_HOOKS (ADR-0001) is still present in the 2.3.0 binary (control: a made-up name matched 0), but only the string was checked, not whether hk still honours it
VERDICT: correct the spec first — hk-builtins-audit.md regeneration and the _EXPECTED_FLAG_TABLES update are missing, and without them lint, pytest and verify go red. Also add a staging test for P15. Residuals that don't block: P13 and P16 are settled by verify steps 1, 4 and 5 plus the STOP rules in §4; P17 by the `ls-remote` confirmation the spec already requires.
```

Relevant paths:
- `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/hk_builtins_audit.py`
- `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/docs/hk-builtins-audit.md`
- `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/tests/test_hk_builtins_audit.py`
- `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/tests/test_workflow_claude_code.py`
- `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/pin-parity.toml`
- `/Users/rmanaloto/.local/share/mise/installs/hk/2.3.0/.mise-packslip/assets/hk.usage.kdl`

## GitHub repos touched

_None._
