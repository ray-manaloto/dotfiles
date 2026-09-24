# Due diligence: plan-doctor "PLAN TAMPERED" substring bug vs misuse

Task from team-lead. Investigating whether plan-doctor.sh's substring match
on inject-plan.sh output (case *'PLAN TAMPERED'*) is a genuine plugin bug
or our misuse of task_plan.md.

## Plugin location

## Versions checked
Installed cache has 3.12.0, 3.12.1, 3.13.0, 3.14.0 (latest). Bug identical
in ALL FOUR — `grep -n "PLAN TAMPERED" scripts/plan-doctor.sh:78` present,
unchanged, in every version. CHANGELOG.md (3.14.0) documents a closely
related, ALREADY-FIXED bug in the same tool: v-unstated entry "plan-doctor
reports a refusal as its own state with the remedy. It previously counted
the refusal notice as bytes of plan context and printed PASS" — i.e. the
project has fixed one false-POSITIVE in this exact function before, but not
this false-WARN.

## Real vs prose disambiguation — VERIFIED both arms
`inject-plan.sh` userprompt path:
- REAL tamper (attestation hash mismatch): output is EXACTLY 4 lines,
  starts with `[planning-with-files] [PLAN TAMPERED — injection blocked]`,
  ZERO `BEGIN-PWF-DATA` markers (script `exit 0`s immediately after echo,
  before any `frame_file` call — inject-plan.sh:1034 region).
- Prose containing the literal string "PLAN TAMPERED" 4x inside
  `task_plan.md`, attestation VALID: output contains the phrase but wrapped
  inside `===BEGIN-PWF-DATA kind=plan ...=== ... ===END-PWF-DATA...===`
  framing, TWO such blocks present (plan + progress).
Reproduced live in /tmp/pwf-repro with 3.12.0's real scripts (not
simulated): first with valid attestation (prose case) -> 2 BEGIN-PWF-DATA
markers in output; then corrupted the file post-attestation to trigger a
REAL mismatch -> 0 BEGIN-PWF-DATA markers, output = the 4-line tamper
notice verbatim.

So the information plan-doctor.sh needs to disambiguate IS present in
inject-plan.sh's own output (the DATA-ONLY framing markers, designed
specifically for delimiter-confusion defense per the "canonical context
framing" comment at inject-plan.sh:927-928). plan-doctor.sh's case-glob
substring match just doesn't use it.

## No test covers this
`find $P/3.14.0/tests -iname '*doctor*'` -> empty. No test_plan_doctor*.py
exists anywhere in the plugin. Two test files mention "plan-doctor" only in
passing (test_nested_plan_isolation.py, test_script_location_parity.py) --
neither exercises the WARN branch's string-match logic. Control arm: grep
-rl PLAN_PREFIX (a symbol I know appears, used throughout inject-plan.sh)
DID return hits in the same tests dir, so the search mechanism works and
the absence for plan-doctor is real, not a broken grep.
Conclusion: oversight, not deliberate untested-by-design.

## Upstream awareness
Repo: OthmanAdi/planning-with-files (from CITATION.cff / README).
gh api search over issues:
- q="plan-doctor" -> 6 hits, none about false-positive matching (they're
  i18n consolidation refactors + a CRLF bug + issue #19 generic usage Q).
- q="TAMPERED" -> 3 hits: #234 (attest-plan.sh silently attests wrong file
  when run from inside .planning/<slug>/, closed) -- SAME CLASS (silent
  misdiagnosis in the attestation tooling) but NOT this bug; #157 (Pi hook
  parity, irrelevant); #150 (the original P1 that added attestation itself).
Control arm: q="217" style direct-number lookup on a KNOWN issue (#217,
"Add protection against stale or conflicting planning files") returned it
correctly via `gh api repos/.../issues/217`, confirming the API/search path
works before trusting a 0-hit query.
Verdict: upstream does NOT appear to know about this specific defect yet.
No open or closed issue/PR matches it.

## README's documented file split
README.md:107-109, :125-127: task_plan.md is documented as "phases +
checkboxes", findings.md as "research notes and decisions, appended as you
go", progress.md as "session log and test results". Incident-narrative
prose describing the plan-doctor bug (what our fixture put in task_plan.md
to reproduce it) is exactly the kind of content the plugin's own docs say
belongs in findings.md, not task_plan.md. This is real evidence for the
misuse side -- but it doesn't reach the diagnostic-tool robustness question:
even a phase/checkbox-shaped task_plan.md line can legitimately contain the
words "plan tampered" (e.g. a checkbox: "- [ ] fix the plan-tampered
false-warning") without being incident narrative at all.

## VERDICT: BOTH (bug dominant)

## codex xhigh verdict (gpt-5.6-sol, rc=0) — full text at codex-verdict.md
BOTH — bug dominant. Strongest evidence: real-tamper output and valid-plan
output have unambiguous, disjoint structures (banner-only-no-frames vs
DATA-ONLY-framed) that plan-doctor.sh's whole-output substring search
discards. Steelman for misuse (README's task_plan.md=phases/findings.md=
narrative split) does not survive: a legitimate checkbox like
"- [ ] fix the false PLAN TAMPERED warning in plan-doctor" is documented-
correct content that still triggers the false WARN, so no amount of correct
usage prevents it.

Minimal fix (plan-doctor.sh only, anchors the case pattern on the real
banner instead of an unanchored substring):
  case "${OUT}" in
      '[planning-with-files] [PLAN TAMPERED — injection blocked]'*)
          warn ...
Three test arms: (1) real tamper (corrupt post-attest) -> WARN; (2) prose/
checkbox containing "PLAN TAMPERED" with VALID attestation -> PASS; (3) no
plan -> unaffected. All three via the real inject-plan.sh path, not a
synthetic OUT string.

Upstream: not filed. No existing issue/PR matches (searches + control arm
above). A filing is warranted.

## FINAL VERDICT: BOTH — BUG dominant, MISUSE minor/contributing only
