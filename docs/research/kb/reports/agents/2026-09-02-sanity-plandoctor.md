# Independent verification (before reading prior report)

Versions cached: 3.12.0, 3.12.1, 3.13.0, 3.14.0 — plan-doctor.sh byte-identical
across all four (md5 2276ef724...). Using 3.14.0.

## Claim under test: CONFIRMED, reproduced live

Repro dir: scratchpad/repro/proj (task_plan.md body contains literal
"PLAN TAMPERED" text, NO attestation file exists — legacy mode, opt-in).

Result: plan-doctor.sh emits
  WARN  injection: plan is attested but the hash mismatches — run /plan-attest...
immediately followed by
  info  attestation: none (opt-in in legacy mode...)
— a directly self-contradictory pair of lines: it claims an attestation
mismatch while its own next line says no attestation exists at all.

Control arm (scratchpad/repro/proj_control, same setup minus the literal
string): PASS injection: emits plan context (996 bytes). Confirms the
substring match, not real tamper state, drives the WARN.

Root cause confirmed at inject-plan.sh:1200-1211 (frame_file / userprompt
healthy path): the plan body is `cat`'d verbatim, unescaped, into $OUT
between ===BEGIN-PWF-DATA/END markers. plan-doctor.sh:78
`*'PLAN TAMPERED'*)` then substring-matches over the WHOLE of $OUT,
including the embedded plan body — not just inject-plan.sh's own banner
line.

## Angle 3 (does this generalize to other arms?): YES, same defect class,
   reproduced

Tested a plan body containing "Ambiguous plan", "Session isolation is
armed", "requires attested plan", "PWF_PLAN_ROOT is not a directory" as
plain text (scratchpad/repro/proj_ambig). Result: matched the FIRST
case arm in source order ("requires attested plan") with a false WARN.
All 4 remaining arms (lines 78/81/84/89, i.e. PLAN TAMPERED, requires
attested plan, Session isolation is armed, Ambiguous plan) share the
identical unanchored-substring defect. A fix touching only the PLAN
TAMPERED arm is INCOMPLETE.

## NEW independent finding — second, distinct, more severe defect

plan-doctor.sh:92's arm `*'PWF_PLAN_ROOT is not a directory'*)` matches
against inject-plan.sh's ACTUAL emitted text at inject-plan.sh:101:
  "[planning-with-files] PWF_PLAN_ROOT is not a supported absolute local
   directory: ${PWF_PLAN_ROOT} — nothing injected."
"is not a directory" is NOT a contiguous substring of "is not a
supported absolute local directory" (extra words interposed) — the
pattern can NEVER match. This is DEAD/STALE code — the literal drifted
from inject-plan.sh's real wording (version skew between the two
scripts, both cached at 3.14.0, still present).

Reproduced live: `PWF_PLAN_ROOT=/nonexistent/path sh plan-doctor.sh`
→ real inject-plan.sh output is the refusal notice above (nothing
injected) — but plan-doctor reports:
  PASS  injection: emits plan context (120 bytes)
This is a FALSE PASS masking a genuine dark-hooks refusal — the exact
class of bug the code comment right above the case block (plan-doctor.sh,
"Refusal notice, not plan context: reporting its byte count as PASS
told a dark user their hooks were fine") explicitly says it exists to
prevent. It is currently failing to prevent it for this one arm.
This is arguably WORSE than the false-WARN under review, because a false
PASS is silent (nobody investigates a PASS) while a false WARN just
gets a human to re-run /plan-attest needlessly.

## Angle 1: is the proposed fix (anchor to full banner literal) correct?

For the ONE arm it touches: yes, mechanically correct. $OUT for a real
TAMPERED userprompt fire is exactly:
  [planning-with-files] [PLAN TAMPERED — injection blocked]
  expected=...
  actual=...
  Run /plan-attest to re-approve current contents, or restore the file from git.
(inject-plan.sh exits right after echoing these 4 lines — no plan body
ever gets appended in the tampered path.) So anchoring the case pattern
to start-of-string (dropping the leading `*`) correctly excludes any
mid-blob match while still matching the real refusal, because the real
refusal's FIRST bytes are exactly that literal and only the real refusal
produces those first bytes — an embedded plan body always occurs after
the `===BEGIN-PWF-DATA` line for a healthy fire, never as $OUT's own
first line.

No i18n mechanism exists for inject-plan.sh's own banners (checked:
"translat" appears exactly once in inject-plan.sh, and it is about
progress.md USER-TEMPLATE markers like "**Status:** complete", not
about inject-plan.sh's own hardcoded English banners). So the
"silent false negative from a future rewording" risk is real but is
ordinary version-skew risk (already independently demonstrated to have
ALREADY HAPPENED for the PWF_PLAN_ROOT arm above), not a live i18n risk.

Better structural fix: anchor ALL FIVE arms to start-of-string (not just
literal-copy one arm), and fix the PWF_PLAN_ROOT arm's stale literal in
the same change:

    case "${OUT}" in
        '[planning-with-files] [PLAN TAMPERED — injection blocked]'*)
            ...
        '[planning-with-files] v3 mode requires attested plan; run attest-plan'*)
            ...
        '[planning-with-files] Session isolation is armed'*)
            ...
        '[planning-with-files] Ambiguous plan:'*)
            ...
        '[planning-with-files] PWF_PLAN_ROOT is not a supported absolute local directory:'*)
            ...
        *)
            ok ...
    esac

This fixes the false-positive class structurally (anchor to start, not
embed-and-hope) rather than only patching the one arm that happened to
get filed, and it separately fixes the dead PWF_PLAN_ROOT arm (a real,
previously-unknown bug found independently in this pass).

## Comparison with prior report (dd-plandoctor.md), read AFTER independent work

Prior report converges on the same root cause and the same minimal fix
(anchor plan-doctor.sh:78 to the exact banner literal, start-of-string).
Agree fully on: bug is real, reproducible, not "misuse" (their steelman-
for-misuse section reaches the same conclusion I would independently
reach — a legitimate checkbox referencing the bug's own name still
triggers it, so no correct usage avoids the false positive).

Disagreement / additions:
1. Prior report frames this as "which one arm to fix" and stops there —
   does not check whether the other 4 case arms (lines 81/84/89/92) share
   the same unanchored-substring defect. I tested this directly and they
   do (angle 3): a plan body containing "Session isolation is armed" etc.
   as plain prose triggers the same false-WARN class on the FIRST
   matching arm in source order. A fix touching only line 78 is
   SUSTAINED-BUT-INCOMPLETE, not SUSTAINED-BUG-FULLY-ADDRESSED.
2. Prior report does not find the PWF_PLAN_ROOT arm (line 92) is DEAD
   CODE — its literal `'PWF_PLAN_ROOT is not a directory'` never matches
   inject-plan.sh's real text ("...is not a supported absolute local
   directory..."), so a genuine PWF_PLAN_ROOT refusal currently falls
   through to the default arm and prints a FALSE PASS ("emits plan
   context (120 bytes)") on a hook that injected NOTHING. This is a
   second, independently-discovered, more severe defect (false PASS,
   not false WARN) in the same case block, same file, same session's
   diagnostic-tool-robustness question.
