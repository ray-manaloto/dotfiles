# Copyright (c) 2026 Raymond Manaloto
"""Renovate config validation that refuses to run with a degraded regex engine.

``renovate-config-validator`` compiles every regex in ``renovate.json`` with
**RE2** — the engine Renovate itself uses at runtime. RE2 has no lookahead, no
lookbehind and no backreferences, so a pattern using them is valid JS
``RegExp`` and *invalid* Renovate config.

The problem this module exists for (#644): ``re2`` is an **optional** npm
dependency, and npm optional deps fail silently. When it is missing, Renovate
falls back to JS ``RegExp``::

    # renovate/dist/util/regex.js
    try { const RE2 = re2(); ...; RegEx = RE2; status = {type: "available"} }
    catch (err) { status = {type: "unavailable", err} }   # RegEx stays RegExp

    # renovate/dist/config-validator.js
    if (regexEngineStatus.type === "unavailable")
        logger.warn(..., "RE2 not usable, falling back to RegExp: ...")

It **warns and still exits 0**. So the validator keeps reporting success while
checking strictly less than it claims — the worst possible shape, because every
automated consumer (hk, CI, an agent reading ``rc``) is told the config is fine.
Measured on this host: with the degraded engine a ``matchStrings`` entry
carrying ``(?!latest)`` produced *"Config validated successfully"*, ``rc=0``.
With RE2 present the same file exits ``rc=1`` with ``Invalid regExp for
customManagers``.

Why custom code at all (``.claude/rules/use-tool-builtins.md`` requires this in
writing): the validation itself is **100% the native tool** — nothing here
parses a regex or maintains a blacklist of RE2-unsupported constructs, because
reimplementing an engine we can actually run is exactly what that rule refuses.
The only thing added is an assertion that the native tool was not silently
degraded, and no tool provides that: ``regexEngineStatus`` is internal, and the
one env var that touches it (``RENOVATE_X_IGNORE_RE2``) only logs at *debug*.

How the assertion works — a **canary**, not a log-string sniff. Grepping stderr
for ``"RE2 not usable"`` is a proxy for the thing we care about: reword the
message upstream and the check silently becomes a no-op that can only pass,
which is the failure class ``.claude/rules/probes-need-a-control-arm.md``
exists to refuse. Instead :func:`engine_rejects_lookahead` feeds the validator a
config whose *only* flaw is a negative lookahead and **requires it to fail**. If
that passes, the engine is degraded. The gate therefore carries its own control
arm at runtime, is immune to message rewording, and tests the capability we
depend on rather than a symptom of its loss.

Control-armed both ways against the two renovate installs on disk (the old
version IS a control arm):

===================  ==================  ==============
renovate             canary exit         verdict
===================  ==================  ==============
44.13.2 (no re2)     ``rc=0``            degraded
44.14.10 (re2)       ``rc=1``            healthy
===================  ==================  ==============

The hk step ``renovate_config_validate`` and the ``renovate-validate`` CLI
subcommand are thin wrappers over :func:`renovate_validate_main`.
"""

from __future__ import annotations

import json
import logging
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

VALIDATOR = "renovate-config-validator"
CONFIG_NAME = "renovate.json"

# `--no-global` validates the named file AS A REPO CONFIG; without it the
# validator applies the global self-hosted schema. `--strict` is warnings-as-
# errors. Both mirror the hk step this replaces.
VALIDATOR_FLAGS = ("--strict", "--no-global")

# A config that is valid JSON, valid against Renovate's repo schema, and whose
# ONLY defect is a negative lookahead — accepted by JS `RegExp`, rejected by
# RE2. `managerFilePatterns` deliberately matches nothing, so even if this were
# ever evaluated for real it could not touch a file.
RE2_CANARY_CONFIG: dict[str, object] = {
    "$schema": "https://docs.renovatebot.com/renovate-schema.json",
    "customManagers": [
        {
            "customType": "regex",
            "managerFilePatterns": ["/^dotfiles-re2-canary-never-matches$/"],
            "matchStrings": ["(?!never)(?<currentValue>[0-9.]+)"],
            "depNameTemplate": "dotfiles/re2-canary",
            "datasourceTemplate": "github-releases",
        }
    ],
}


@dataclass(frozen=True)
class ValidatorRun:
    """One ``renovate-config-validator`` invocation: its rc and merged output."""

    returncode: int
    output: str


def run_validator(config_path: Path) -> ValidatorRun:
    """Run the native validator against ``config_path``, capturing rc + output."""
    result = subprocess.run(
        [VALIDATOR, *VALIDATOR_FLAGS, str(config_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    return ValidatorRun(result.returncode, result.stdout + result.stderr)


def engine_rejects_lookahead() -> ValidatorRun:
    """Validate the RE2 canary; a **non-zero** rc means the engine really is RE2.

    Inverted on purpose: this asks the validator to *fail*. A zero exit means a
    negative lookahead was accepted, i.e. the JS ``RegExp`` fallback is in
    force and every regex in the real config is going unchecked.
    """
    with tempfile.TemporaryDirectory() as tmp:
        canary = Path(tmp) / CONFIG_NAME
        canary.write_text(json.dumps(RE2_CANARY_CONFIG, indent=2))
        return run_validator(canary)


def renovate_validate_main(repo_root: Path) -> int:
    """CLI entry: assert the engine is RE2, then validate the real config.

    Order matters. The engine check runs **first** so a degraded run can never
    be reported as a passing validation — otherwise the very failure mode this
    module exists for would print a green line before the diagnosis.
    """
    canary = engine_rejects_lookahead()
    if canary.returncode == 0:
        logger.error(
            "%s accepted a negative lookahead, so it is NOT using RE2 — it has "
            "fallen back to JS RegExp and every regex in %s is going UNCHECKED "
            "(#644). Renovate compiles with RE2 at runtime, which has no "
            "lookahead/lookbehind/backreferences, so this gate is currently "
            "weaker than CI. Fix: reinstall renovate so its OPTIONAL `re2` "
            "dependency is present (`mise install npm:renovate`) — re2 builds "
            "fine on macOS arm64. Validator output:\n%s",
            VALIDATOR,
            CONFIG_NAME,
            canary.output.strip(),
        )
        return 1

    config_path = repo_root / CONFIG_NAME
    if not config_path.is_file():
        logger.error("%s not found at %s", CONFIG_NAME, config_path)
        return 1

    real = run_validator(config_path)
    if real.returncode != 0:
        logger.error(
            "%s failed validation (rc=%d):\n%s",
            CONFIG_NAME,
            real.returncode,
            real.output.strip(),
        )
        return real.returncode

    logger.info("%s validated with the RE2 engine confirmed live", CONFIG_NAME)
    return 0
