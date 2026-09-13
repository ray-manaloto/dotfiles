# Copyright (c) 2026 Raymond Manaloto
"""Tests for the machine-readable ``claude doctor`` verdict.

The property under test is **which question the check refused to answer**, not
whether it can spot a stale version. Three states have to stay distinguishable:

* ``INVALID`` — an assertion was made and failed. Only this may enforce.
* ``UNKNOWN`` — the question could not be asked (binary gone, output reworded,
  oracle down, or mise already rewrote ``PATH`` so the wrong ``claude`` is
  visible).
* ``OK`` — every assertion was made and passed.

Collapsing ``UNKNOWN`` into either neighbour is the real defect this guards.
Folded into ``OK`` it becomes a check that can only pass the day upstream
rewords a string it does not own; folded into ``INVALID`` it blocks a session on
a fact nobody established.

The ambient-``PATH`` tests exist because the check shipped measuring the wrong
binary: ``uv run`` executes under mise's activated environment, so the inherited
``PATH`` resolved mise's pinned ``claude`` rather than the native install the
operator actually runs. That produced a false ``INVALID`` on 2026-09-13 — and
would produce a false ``OK`` whenever the pin happens to match the newest
release.

``tests/test_path_drift.py::test_the_session_start_hook_captures_the_ambient_path``
is the other half of that guard and is deliberately not duplicated here: this
check reaches the shell's ``PATH`` through the same captured
``DOTFILES_AMBIENT_PATH``, so if that hook ever stops capturing, both checks go
blind together and that test is what fails.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "python" / "src"))

from dotfiles_setup import claude_doctor
from dotfiles_setup.claude_doctor import Verdict
from dotfiles_setup.path_drift import Provenance

if TYPE_CHECKING:
    from collections.abc import Callable

REPO_ROOT = Path(__file__).parent.parent

NATIVE_DOCTOR = """Claude Code doctor

Running: native (2.1.270)
Commit: 97ecbf7abeb4
Platform: darwin-arm64
Config install method: native
No installation issues found.
"""

SHADOWED_DOCTOR = """Claude Code doctor

Running: npm-global (2.1.269)
Platform: darwin-arm64
No installation issues found.
"""

AMBIENT = "/ambient/bin:/usr/bin"


def _fake_run(
    *,
    doctor: tuple[int, str] = (0, NATIVE_DOCTOR),
    oracle: tuple[int, str] = (0, "2.1.270\n"),
    seen: list[str | None] | None = None,
) -> Callable[..., tuple[int, str]]:
    """A ``_run`` stub that answers by argv, recording each call's ``path``."""

    def run(
        argv: list[str],
        *,
        extra_env: dict[str, str] | None = None,
        path: str | None = None,
    ) -> tuple[int, str]:
        # `extra_env` is accepted and ignored on purpose: the stub must match
        # `_run`'s real signature, or a caller passing it would TypeError here
        # and the test would pass for the wrong reason.
        del extra_env
        if seen is not None:
            seen.append(path)
        return doctor if argv[0] == "claude" else oracle

    return run


@pytest.fixture(autouse=True)
def _ambient(monkeypatch: pytest.MonkeyPatch) -> None:
    """Default every test to a captured, trustworthy ambient PATH."""
    monkeypatch.setattr(
        claude_doctor,
        "resolve_ambient_path",
        lambda _environ: (AMBIENT, Provenance.EXPLICIT),
    )


# --------------------------------------------------------------------------- #
# parse_doctor
# --------------------------------------------------------------------------- #


def test_parse_doctor_extracts_version_method_and_marker() -> None:
    assert claude_doctor.parse_doctor(NATIVE_DOCTOR) == ("2.1.270", "native", True)


def test_parse_doctor_reads_a_hyphenated_install_method() -> None:
    r"""``npm-global`` is the shadowing case a ``\w+``-only pattern would miss."""
    assert claude_doctor.parse_doctor(SHADOWED_DOCTOR) == (
        "2.1.269",
        "npm-global",
        True,
    )


def test_parse_doctor_returns_none_when_the_running_line_is_reworded() -> None:
    """A ``None`` version is the caller's signal to report UNKNOWN, not failure."""
    version, method, _ = claude_doctor.parse_doctor("Now running: native 2.1.270")
    assert version is None
    assert method is None


def test_parse_doctor_reports_a_missing_clean_marker() -> None:
    assert claude_doctor.parse_doctor("Running: native (2.1.270)\n") == (
        "2.1.270",
        "native",
        False,
    )


# --------------------------------------------------------------------------- #
# evaluate — the three verdicts
# --------------------------------------------------------------------------- #


def test_a_current_native_install_is_ok(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(claude_doctor, "_run", _fake_run())
    result = claude_doctor.evaluate()
    assert result.verdict is Verdict.OK
    assert result.findings == []
    assert result.enforcement_eligible is False


def test_a_stale_version_is_invalid(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(claude_doctor, "_run", _fake_run(oracle=(0, "2.1.271\n")))
    result = claude_doctor.evaluate()
    assert result.verdict is Verdict.INVALID
    assert result.enforcement_eligible is True
    assert any("2.1.271 is published" in f for f in result.findings)


def test_a_shadowed_install_is_invalid_and_names_the_shadowing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The version mismatch is a SYMPTOM; the finding must name the cause.

    Captured-but-unasserted ``install_method`` is why this class recurred within
    a day of first being observed, so the assertion is the point of the test.
    """
    monkeypatch.setattr(
        claude_doctor,
        "_run",
        _fake_run(doctor=(0, SHADOWED_DOCTOR), oracle=(0, "2.1.269\n")),
    )
    result = claude_doctor.evaluate()
    assert result.verdict is Verdict.INVALID
    assert result.install_method == "npm-global"
    # The version assertion PASSES here (2.1.269 == 2.1.269), so this finding
    # can only come from the install-method assertion.
    assert len(result.findings) == 1
    assert "not the expected 'native'" in result.findings[0]
    # The PATH advice is only appended when NATIVE is the displaced install, so
    # its presence here also pins that branch.
    assert "mise env -C" in result.findings[0]


def test_an_accepted_non_native_install_can_opt_out(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``expected_method=""`` skips the assertion rather than standing-finding."""
    monkeypatch.setattr(
        claude_doctor,
        "_run",
        _fake_run(doctor=(0, SHADOWED_DOCTOR), oracle=(0, "2.1.269\n")),
    )
    result = claude_doctor.evaluate(expected_method="")
    assert result.verdict is Verdict.OK


def test_a_missing_binary_is_unknown_not_invalid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        claude_doctor, "_run", _fake_run(doctor=(127, "claude: not found on PATH"))
    )
    result = claude_doctor.evaluate()
    assert result.verdict is Verdict.UNKNOWN
    assert result.enforcement_eligible is False


def test_reworded_output_is_unknown_not_a_silent_pass(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The whole reason the verdict is three-way rather than a boolean."""
    monkeypatch.setattr(
        claude_doctor, "_run", _fake_run(doctor=(0, "Now running: native 2.1.270"))
    )
    result = claude_doctor.evaluate()
    assert result.verdict is Verdict.UNKNOWN
    assert result.enforcement_eligible is False


def test_an_oracle_failure_is_unknown_never_current(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Grilling decision Q14: 'cannot determine latest', never 'current'."""
    monkeypatch.setattr(
        claude_doctor, "_run", _fake_run(oracle=(1, "network unreachable"))
    )
    result = claude_doctor.evaluate()
    assert result.verdict is Verdict.UNKNOWN
    assert any("cannot determine latest" in f for f in result.findings)
    assert result.running_version == "2.1.270"


def test_a_missing_clean_marker_is_invalid(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        claude_doctor,
        "_run",
        _fake_run(doctor=(0, "Running: native (2.1.270)\nFound 1 problem.\n")),
    )
    result = claude_doctor.evaluate()
    assert result.verdict is Verdict.INVALID
    assert any("installation issues" in f for f in result.findings)


# --------------------------------------------------------------------------- #
# the ambient PATH — the bug this check shipped with
# --------------------------------------------------------------------------- #


def test_a_rewritten_path_is_blind_and_therefore_unknown(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Blindness must never render as OK — that is a check that can only pass."""
    monkeypatch.setattr(
        claude_doctor,
        "resolve_ambient_path",
        lambda _environ: ("/rewritten", Provenance.BLIND),
    )
    monkeypatch.setattr(claude_doctor, "_run", _fake_run())
    result = claude_doctor.evaluate()
    assert result.verdict is Verdict.UNKNOWN
    assert "BLIND" in result.findings[0]
    assert result.enforcement_eligible is False


def test_blindness_short_circuits_before_any_subprocess(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A blind check must not spend a ``claude doctor`` it cannot interpret."""
    seen: list[str | None] = []
    monkeypatch.setattr(
        claude_doctor,
        "resolve_ambient_path",
        lambda _environ: ("/rewritten", Provenance.BLIND),
    )
    monkeypatch.setattr(claude_doctor, "_run", _fake_run(seen=seen))
    claude_doctor.evaluate()
    assert seen == []


def test_both_probes_run_against_the_ambient_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The regression arm: an inherited PATH resolves the wrong ``claude``."""
    seen: list[str | None] = []
    monkeypatch.setattr(claude_doctor, "_run", _fake_run(seen=seen))
    claude_doctor.evaluate()
    assert seen == [AMBIENT, AMBIENT], (
        "every probe must resolve against the captured ambient PATH; an "
        "inherited one finds mise's pinned claude shim, not the operator's"
    )


# --------------------------------------------------------------------------- #
# serialisation and the CLI seam
# --------------------------------------------------------------------------- #


def test_to_json_is_parseable_and_carries_the_verdict(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(claude_doctor, "_run", _fake_run())
    payload = json.loads(claude_doctor.evaluate().to_json())
    assert payload["verdict"] == "ok"
    assert payload["enforcement_eligible"] is False
    assert payload["install_method"] == "native"


@pytest.mark.parametrize(
    ("doctor_out", "oracle_out", "expected_rc"),
    [
        (NATIVE_DOCTOR, "2.1.270\n", 0),
        (NATIVE_DOCTOR, "2.1.271\n", 1),
        ("Now running: native 2.1.270", "2.1.270\n", 0),
    ],
    ids=["ok", "invalid", "unknown"],
)
def test_the_cli_exit_code_tracks_enforcement_eligibility_only(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    doctor_out: str,
    oracle_out: str,
    expected_rc: int,
) -> None:
    """UNKNOWN exits 0 on purpose: a question never asked must not block."""
    monkeypatch.setattr(
        claude_doctor,
        "_run",
        _fake_run(doctor=(0, doctor_out), oracle=(0, oracle_out)),
    )
    assert claude_doctor.claude_doctor_main() == expected_rc
    assert json.loads(capsys.readouterr().out)["verdict"] is not None


# --------------------------------------------------------------------------- #
# real-repo guards a fixture cannot pin
# --------------------------------------------------------------------------- #


def test_the_cli_subcommand_is_registered() -> None:
    """Green gates certify logic, not wiring — the seam must actually exist."""
    main_src = (REPO_ROOT / "python" / "src" / "dotfiles_setup" / "main.py").read_text()
    assert "_add_claude_doctor_subcommand(subparsers)" in main_src, (
        "the subcommand helper is defined but never called, so `dotfiles-setup "
        "claude-doctor` does not exist and the function hook has nothing to call"
    )
    assert '"claude-doctor": lambda' in main_src


def test_a_non_native_expectation_does_not_blame_the_mise_shim(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Advice must not contradict the fact beside it.

    Appending the shim advice unconditionally made the finding blame a mise pin
    for shadowing the native build in the very case where the install on PATH
    *was* native. Caught by arming the doctor check with an expectation no host
    here satisfies, which is the only way that branch is reachable.
    """
    monkeypatch.setattr(claude_doctor, "_run", _fake_run())
    result = claude_doctor.evaluate(expected_method="homebrew")
    assert result.verdict is Verdict.INVALID
    assert "not the expected 'homebrew'" in result.findings[0]
    assert "mise env -C" not in result.findings[0], (
        "the PATH-shadowing advice is only true when the NATIVE install is the "
        "one being displaced"
    )
