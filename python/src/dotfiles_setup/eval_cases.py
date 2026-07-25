"""This repo's tier-1 eval cases (#354 PR 2).

The RUNNER is :mod:`kb_setup.evals`, shared with knowledge-base and consumed
here as the SHA-pinned ``kb-setup`` dependency — the ``kb_setup.currency`` /
``kb_setup.md_budget`` precedent (D2/G4: one implementation, never a second copy
that drifts). Only the CASES are per-repo, because what "resolves" means differs.

Tier 0 (``suites.toml`` ``orchestration.*`` / ``eval.*``) asks *is it declared?*
These ask the next question: **does it resolve?** The two are genuinely
different, and #354 is what the gap costs — a lane can be named in doctrine, in
both repos, with a passing contract, while its CLI is not installed and nothing
says what happens instead.

Every gated case carries a ``control`` that must come back FAIL, and the runner
refuses to count a gated case whose control does not fail. Note the trap the KB
side hit first: **a control that returns SKIP is not armed.** Pointing a probe
at something absent usually yields SKIP by design, so the controls below build a
genuinely broken fixture and drive the same code path against it.
"""

from __future__ import annotations

import importlib
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

from kb_setup import evals

if TYPE_CHECKING:
    from collections.abc import Sequence

#: Lane CLIs the orchestration doctrine names in `.claude/CLAUDE.md`. `grok` is
#: deliberately included and is NOT installed (control-armed: `codex`, `agy`,
#: `claude`, `graphify` all resolve; `grok` does not). The doctrine's position is
#: that availability is discovered at run time, so the case asserts the
#: DEGRADATION PATH IS DECLARED — not that grok exists.
DECLARED_LANES = ("codex", "agy", "grok")

#: Tokens whose presence in the doctrine doc constitutes a declared degradation
#: path. `.claude/CLAUDE.md` says grok "is NOT installed, so `codex` is the only
#: viable fixed mode and cross-family review falls to antigravity or Claude".
FALLBACK_TOKENS = ("NOT installed", "fall")

#: The fable-orchestrator plugin's own lane doctor. Version-pinned inside the
#: plugin cache, so it can vanish on plugin GC — hence a LOUD skip, never silent.
DOCTOR_SCRIPT = Path.home().joinpath(
    ".claude/plugins/cache/fable-orchestrator/fable-orchestrator/1.14.0/scripts/doctor.sh"
)

#: A liveness question for the local graph. Deliberately not phrased by echoing
#: node labels — that grades lexical overlap and reports a win that isn't there.
CANARY_QUESTION = "how does the devcontainer get built?"

_MISSING_BINARY = "definitely-not-a-real-binary-xyz"


def _broken_graph_canary() -> evals.Outcome:
    """Control arm: drive the canary against a graph that cannot answer.

    A directory holding a present-but-meaningless ``graph.json`` passes the
    existence gate — so this is NOT a skip — and then makes the real
    ``graphify query`` fail, which is the branch the canary must be shown to
    reach.
    """
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        graph = root / "graphify-out" / "graph.json"
        graph.parent.mkdir(parents=True)
        graph.write_text("not a graph")
        return evals.graphify_canary(root, CANARY_QUESTION, timeout=30)


def _broken_doctor() -> evals.Outcome:
    """Control arm: a doctor script that reports a failing lane.

    Deliberately distinct from the absent-script case. "We could not look"
    (SKIP) and "we looked and a lane is broken" (FAIL) must never collapse into
    each other — the first is the inert declaration wearing a green badge.
    """
    with tempfile.TemporaryDirectory() as tmp:
        script = Path(tmp) / "doctor.sh"
        script.write_text(
            "#!/usr/bin/env bash\necho '0 ok, 0 warnings, 1 failures'\nexit 1\n"
        )
        return evals.doctor_health(script, timeout=30)


def cases(repo_root: Path, *, doctor_script: Path | None = None) -> list[evals.Case]:
    """Build this repo's tier-1 cases."""
    doctor = doctor_script if doctor_script is not None else DOCTOR_SCRIPT
    fallback_doc = repo_root / ".claude" / "CLAUDE.md"

    return [
        evals.Case(
            name="tier1.lanes-declared-or-degraded",
            description=(
                "every lane the doctrine names either resolves on PATH, or its "
                "degradation path is written down"
            ),
            probe=lambda: evals.declared_lanes_reconcile(
                DECLARED_LANES,
                fallback_doc=fallback_doc,
                fallback_tokens=FALLBACK_TOKENS,
            ),
            # The fallback doc pointed at a file that does not exist: "we cannot
            # read the fallback" must never resolve to "the fallback is declared".
            control=lambda: evals.declared_lanes_reconcile(
                (_MISSING_BINARY,),
                fallback_doc=repo_root / ".claude" / "does-not-exist.md",
                fallback_tokens=FALLBACK_TOKENS,
            ),
        ),
        evals.Case(
            name="tier1.shared-engine-resolves",
            description=(
                "the SHARED kb_setup engine this repo depends on is importable — "
                "md_budget and the eval runner both come from it, so a broken pin "
                "silently disarms two gates at once"
            ),
            probe=_kb_setup_importable,
            control=_kb_setup_import_control,
        ),
        evals.Case(
            name="tier1.graph-answers",
            description=(
                "the local graph does not merely exist — it returns a non-empty "
                "answer (rc=0 with empty output is a graph that reads as healthy "
                "and knows nothing)"
            ),
            probe=lambda: evals.graphify_canary(repo_root, CANARY_QUESTION),
            control=_broken_graph_canary,
        ),
        evals.Case(
            name="tier1.lane-health",
            description=(
                "the plugin's own doctor.sh reports every installed lane "
                "authenticated with model access"
            ),
            probe=lambda: evals.doctor_health(doctor),
            control=_broken_doctor,
            # doctor.sh has NO offline mode: whenever a lane's CLI is present it
            # fires a real API call, and it exits `[ FAIL -eq 0 ]` so warnings
            # pass. It is the live half ENTIRELY and can never join the free
            # gated tier — the offline probes above are that tier.
            live=True,
        ),
    ]


#: The shared entry points this repo consumes from the pinned kb_setup package.
#: Both gates depend on them: `md_size_budget` shells out to `kb-setup
#: md-budget`, and `mise run eval` imports the runner.
SHARED_MODULES = ("kb_setup.evals", "kb_setup.md_budget")


def _importable(names: Sequence[str]) -> evals.Outcome:
    """FAIL naming every module in ``names`` that cannot be imported."""
    missing = []
    for name in names:
        try:
            importlib.import_module(name)
        except ImportError:
            missing.append(name)
    if missing:
        return evals.fail(f"kb_setup module(s) not importable: {', '.join(missing)}")
    return evals.ok(f"{len(names)} shared module(s) import: {', '.join(names)}")


def _kb_setup_importable() -> evals.Outcome:
    """Both shared entry points must actually be reachable, not just pinned.

    Asserting the pin exists is tier 0's job and is not the same question: a pin
    can name a commit that predates the module, and then `md_size_budget` and
    `mise run eval` both fail at the seam rather than at the declaration.
    """
    return _importable(SHARED_MODULES)


def _kb_setup_import_control() -> evals.Outcome:
    """Control arm: the same probe against a module that cannot exist."""
    return _importable(("kb_setup.definitely_not_a_module",))
