# Copyright (c) 2026 Raymond Manaloto
"""Tests for the machine-readable ``claude doctor`` verdict.

The property under test is **which question the check refused to answer**, not
whether it can spot a stale version. Four states have to stay distinguishable:

* ``INVALID`` — an assertion was made and failed. Only this may enforce.
* ``UNKNOWN`` — the question could not be asked (binary gone, output reworded,
  oracle down, or mise already rewrote ``PATH`` so the wrong ``claude`` is
  visible).
* ``DRIFT`` — the host is healthy, but the repository's Claude Code pin is
  positively established as stale. It is reported but cannot enforce.
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
import subprocess
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

MISE_DEPRECATION_WARN = (
    "mise WARN  deprecated [python.uv_venv_auto.true]: "
    "python.uv_venv_auto=true is deprecated. Use "
    'python.uv_venv_auto="create|source" or "source" instead. '
    "This will be removed in mise 2027.7.0."
)

#: A root holding no ``doctor.toml``, so :func:`claude_doctor.load_baseline`
#: returns its documented default instead of this repo's real baseline.
NO_BASELINE = Path("/nonexistent/dotfiles-test-root")


def _fake_run(
    *,
    doctor: tuple[int, str] = (0, NATIVE_DOCTOR),
    oracle: tuple[int, str] = (0, "2.1.270\n"),
    seen: list[str | None] | None = None,
) -> Callable[..., tuple[int, str, str]]:
    """A ``_run`` stub that answers by argv, recording each call's ``path``."""

    def run(
        argv: list[str],
        *,
        extra_env: dict[str, str] | None = None,
        path: str | None = None,
        stdout_only: bool = False,
    ) -> tuple[int, str, str]:
        # `extra_env` is accepted and ignored on purpose: the stub must match
        # `_run`'s real signature, or a caller passing it would TypeError here
        # and the test would pass for the wrong reason.
        del extra_env, stdout_only
        if seen is not None:
            seen.append(path)
        rc, output = doctor if argv[0] == "claude" else oracle
        return rc, output, ""

    return run


def _stub_process_boundary(
    monkeypatch: pytest.MonkeyPatch,
    *,
    oracle_responses: list[tuple[int, str, str]],
    doctor_responses: list[tuple[int, str, str]] | None = None,
    calls: list[tuple[list[str], dict[str, object]]] | None = None,
) -> None:
    """Stub executable lookup and process launch, not our parsing functions."""
    scripted = {
        "claude": list(doctor_responses or [(0, NATIVE_DOCTOR, "")]),
        "mise": list(oracle_responses),
    }

    def which(command: str, *, path: str | None = None) -> str:
        del path
        return f"/test/bin/{command}"

    def run(
        argv: list[str],
        **kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        assert kwargs["capture_output"] is True
        assert kwargs["text"] is True
        if calls is not None:
            calls.append((list(argv), dict(kwargs)))
        command = Path(argv[0]).name
        assert command in scripted, f"unexpected subprocess command: {command!r}"
        responses = scripted[command]
        assert responses, f"unexpected subprocess call beyond script: {argv!r}"
        rc, stdout, stderr = responses.pop(0)
        return subprocess.CompletedProcess(argv, rc, stdout, stderr)

    monkeypatch.setattr(claude_doctor.shutil, "which", which)
    monkeypatch.setattr(claude_doctor.subprocess, "run", run)


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


def test_latest_version_reads_stdout_not_a_success_warning(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A diagnostic line must never become the successful oracle's value."""
    calls: list[tuple[list[str], dict[str, object]]] = []
    _stub_process_boundary(
        monkeypatch,
        oracle_responses=[(0, "2.1.277\n", MISE_DEPRECATION_WARN)],
        calls=calls,
    )

    assert claude_doctor.latest_version() == ("2.1.277", None)
    _, kwargs = calls[0]
    assert kwargs["timeout"] == 20.0
    env = kwargs["env"]
    assert isinstance(env, dict)
    assert env["MISE_FETCH_REMOTE_VERSIONS_CACHE"] == "0s"


def test_empty_oracle_stdout_is_unknown_even_when_stderr_has_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A warning is ABOUT an empty answer; it cannot make the answer INVALID."""
    diagnostic = f"{MISE_DEPRECATION_WARN} {'x' * 250} OMITTED"
    _stub_process_boundary(
        monkeypatch,
        oracle_responses=[
            (0, "", diagnostic),
            (0, "", diagnostic),
        ],
    )

    assert claude_doctor.latest_version() == (
        None,
        f"version oracle returned no version; stderr: {diagnostic[:200]!r}",
    )
    result = claude_doctor.evaluate(check_pin=False)
    assert result.verdict is Verdict.UNKNOWN
    assert result.enforcement_eligible is False


def test_non_version_oracle_stdout_is_unknown_never_invalid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Even the value channel remains untrusted until its shape is established."""
    stdout = "oracle prelude\nthe newest release is ready\n" + "x" * 250 + " OMITTED\n"
    _stub_process_boundary(
        monkeypatch,
        oracle_responses=[(0, stdout, "")],
    )

    result = claude_doctor.evaluate(check_pin=False)
    assert result.verdict is Verdict.UNKNOWN
    assert result.enforcement_eligible is False
    assert "non-version output" in result.findings[0]
    assert "oracle prelude" in result.findings[0]
    assert "the newest release is ready" in result.findings[0]
    assert "OMITTED" not in result.findings[0]


def test_running_version_shape_rejects_a_trailing_newline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A newline inside the captured token is content, not process framing."""
    doctor = "Running: native (2.1.277\n)\nNo installation issues found.\n"
    _stub_process_boundary(
        monkeypatch,
        doctor_responses=[(0, doctor, "")],
        oracle_responses=[(0, "2.1.277\n", "")],
    )

    result = claude_doctor.evaluate(check_pin=False)

    assert result.verdict is Verdict.UNKNOWN
    assert result.running_version == "2.1.277\n"


def test_claude_doctor_is_read_across_stdout_and_stderr(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The defensive default survives if upstream moves ``Running:`` to stderr.

    This is not the observed stream split: measured 2026-09-18, the real command
    wrote 655 bytes to stdout and zero to stderr. The synthetic split protects
    the documented merged default against a future upstream change.
    """
    _stub_process_boundary(
        monkeypatch,
        doctor_responses=[
            (
                0,
                "Claude Code doctor\nNo installation issues found.\n",
                "Running: native (2.1.270)\n",
            )
        ],
        oracle_responses=[(0, "2.1.270\n", "")],
    )

    result = claude_doctor.evaluate(check_pin=False)

    assert result.verdict is Verdict.OK
    assert result.running_version == "2.1.270"
    assert result.clean_marker_present is True


@pytest.mark.parametrize(
    ("running", "method", "clean_marker", "expected"),
    [
        (
            "unknown",
            "native",
            "No installation issues found.\n",
            (Verdict.UNKNOWN, ["non-version running value", "'unknown'"]),
        ),
        (
            "dev",
            "npm-global",
            "No installation issues found.\n",
            (
                Verdict.INVALID,
                ["non-version running value", "not the expected 'native'"],
            ),
        ),
        (
            "dev",
            "native",
            "",
            (Verdict.INVALID, ["non-version running value", "installation issues"]),
        ),
        (
            "dev-" + "x" * 250 + " OMITTED",
            "native",
            "No installation issues found.\n",
            (Verdict.UNKNOWN, ["non-version running value", "'dev-"]),
        ),
    ],
    ids=[
        "unknown-version",
        "wrong-method",
        "missing-clean-marker",
        "bounded-value",
    ],
)
def test_unreadable_running_version_is_unknown_but_keeps_known_facts(
    monkeypatch: pytest.MonkeyPatch,
    running: str,
    method: str,
    clean_marker: str,
    expected: tuple[Verdict, list[str]],
) -> None:
    """Unreadable currency skips only that comparison, not other assertions."""
    expected_verdict, expected_fragments = expected
    doctor = f"Running: {method} ({running})\n{clean_marker or 'Found 1 problem.\n'}"
    calls: list[tuple[list[str], dict[str, object]]] = []
    _stub_process_boundary(
        monkeypatch,
        doctor_responses=[(0, doctor, "")],
        oracle_responses=[(0, "2.1.277\n", "")],
        calls=calls,
    )

    result = claude_doctor.evaluate(check_pin=False)

    assert result.verdict is expected_verdict
    assert result.enforcement_eligible is (expected_verdict is Verdict.INVALID)
    assert result.running_version == running
    assert result.install_method == method
    assert result.clean_marker_present is bool(clean_marker)
    assert [Path(argv[0]).name for argv, _kwargs in calls] == ["claude", "mise"]
    for fragment in expected_fragments:
        assert any(fragment in finding for finding in result.findings)
    if "OMITTED" in running:
        assert all("OMITTED" not in finding for finding in result.findings)
        payload = json.loads(result.to_json())
        assert payload["running_version"] == running[:200]
        assert "OMITTED" not in payload["running_version"]


def test_release_suffix_is_unreadable_not_an_enforcing_mismatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No published tag needs a suffix, so ``-dev`` cannot become INVALID."""
    doctor = "Running: native (2.1.277-dev)\nNo installation issues found.\n"
    _stub_process_boundary(
        monkeypatch,
        doctor_responses=[(0, doctor, "")],
        oracle_responses=[(0, "2.1.277\n", "")],
    )

    result = claude_doctor.evaluate(check_pin=False)

    assert result.verdict is Verdict.UNKNOWN
    assert result.enforcement_eligible is False
    assert result.findings == [
        "`claude doctor` returned a non-version running value: '2.1.277-dev'"
    ]


def test_oracle_stderr_is_diagnostic_on_success_and_reason_on_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The same stream changes role only when the command itself fails."""
    failure = "mise failed to reach the release service"
    _stub_process_boundary(
        monkeypatch,
        oracle_responses=[
            (0, "2.1.277\n", MISE_DEPRECATION_WARN),
            (9, "", failure),
        ],
    )

    assert claude_doctor.latest_version() == ("2.1.277", None)
    latest, reason = claude_doctor.latest_version()
    assert latest is None
    assert reason is not None
    assert failure in reason


def test_a_current_native_install_is_ok(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(claude_doctor, "_run", _fake_run())
    result = claude_doctor.evaluate(check_pin=False)
    assert result.verdict is Verdict.OK
    assert result.findings == []
    assert result.enforcement_eligible is False


def test_a_stale_version_is_invalid(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(claude_doctor, "_run", _fake_run(oracle=(0, "2.1.271\n")))
    result = claude_doctor.evaluate(check_pin=False)
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
    result = claude_doctor.evaluate(check_pin=False)
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
    result = claude_doctor.evaluate(expected_method="", check_pin=False)
    assert result.verdict is Verdict.OK


def test_a_missing_binary_is_unknown_not_invalid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        claude_doctor, "_run", _fake_run(doctor=(127, "claude: not found on PATH"))
    )
    result = claude_doctor.evaluate(check_pin=False)
    assert result.verdict is Verdict.UNKNOWN
    assert result.enforcement_eligible is False


def test_reworded_output_is_unknown_not_a_silent_pass(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A parse failure remains UNKNOWN but retains the known clean-marker fact."""
    monkeypatch.setattr(
        claude_doctor, "_run", _fake_run(doctor=(0, "Now running: native 2.1.270"))
    )
    result = claude_doctor.evaluate(check_pin=False)
    assert result.verdict is Verdict.UNKNOWN
    assert result.enforcement_eligible is False
    assert "could not parse" in result.findings[0]
    assert "installation issues" in result.findings[1]


def test_an_oracle_failure_is_unknown_never_current(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Oracle failure stays UNKNOWN while listing established install failures."""
    doctor = "Running: npm-global (2.1.270)\nFound 1 problem.\n"
    _stub_process_boundary(
        monkeypatch,
        doctor_responses=[(0, doctor, "")],
        oracle_responses=[(1, "", "network unreachable")],
    )

    result = claude_doctor.evaluate(check_pin=False)

    assert result.verdict is Verdict.UNKNOWN
    assert result.enforcement_eligible is False
    assert "cannot determine latest" in result.findings[0]
    assert "not the expected 'native'" in result.findings[1]
    assert "installation issues" in result.findings[2]
    assert result.running_version == "2.1.270"


def test_a_missing_clean_marker_is_invalid(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        claude_doctor,
        "_run",
        _fake_run(doctor=(0, "Running: native (2.1.270)\nFound 1 problem.\n")),
    )
    result = claude_doctor.evaluate(check_pin=False)
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
    result = claude_doctor.evaluate(check_pin=False)
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
    claude_doctor.evaluate(check_pin=False)
    assert seen == []


def test_both_probes_run_against_the_ambient_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The regression arm: an inherited PATH resolves the wrong ``claude``."""
    seen: list[str | None] = []
    monkeypatch.setattr(claude_doctor, "_run", _fake_run(seen=seen))
    claude_doctor.evaluate(check_pin=False)
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
    payload = json.loads(claude_doctor.evaluate(check_pin=False).to_json())
    assert payload["verdict"] == "ok"
    assert payload["enforcement_eligible"] is False
    assert payload["disabled_by_baseline"] is False
    assert payload["baseline_path"] is None
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
    """UNKNOWN exits 0 on purpose: a question never asked must not block.

    ``project_root`` names a root with no ``doctor.toml`` so this asserts the
    exit-code mapping alone. Without it the call reads the REAL ``doctor.toml``
    and the case flips with whatever this repo currently expects - which is how
    the baseline-reading regression below was first caught.
    """
    monkeypatch.setattr(
        claude_doctor,
        "_run",
        _fake_run(doctor=(0, doctor_out), oracle=(0, oracle_out)),
    )
    assert claude_doctor.claude_doctor_main(project_root=NO_BASELINE) == expected_rc
    payload = json.loads(capsys.readouterr().out)
    assert payload["verdict"] is not None
    assert payload["baseline_path"] == str((NO_BASELINE / "doctor.toml").absolute())


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
    result = claude_doctor.evaluate(expected_method="homebrew", check_pin=False)
    assert result.verdict is Verdict.INVALID
    assert "not the expected 'homebrew'" in result.findings[0]
    assert "mise env -C" not in result.findings[0], (
        "the PATH-shadowing advice is only true when the NATIVE install is the "
        "one being displaced"
    )


# --------------------------------------------------------------------------- #
# the reviewed baseline must reach the ENFORCING path (#1044 regression)
# --------------------------------------------------------------------------- #


#: Current version, clean marker, non-native method: the ONLY deviation is the
#: install method. ``SHADOWED_DOCTOR`` is 2.1.269, so it goes INVALID on
#: staleness no matter what the baseline says - which made the control arm
#: below pass for the wrong reason on first run.
CURRENT_NON_NATIVE_DOCTOR = """Claude Code doctor

Running: npm-global (2.1.270)
Platform: darwin-arm64
No installation issues found.
"""


def _baseline(tmp_path: Path, body: str) -> Path:
    """Write a minimal ``doctor.toml`` and return its root."""
    (tmp_path / "doctor.toml").write_text(f"[claude]\n{body}\n")
    return tmp_path


def test_the_enforcing_cli_reads_expected_install_method_from_doctor_toml(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    """The lever documented in ``doctor.toml`` must move the blocking path.

    Regression for the 2026-09-13 disconnect: ``claude_doctor_main`` defaulted
    to ``NATIVE_METHOD`` and never opened the file, so editing
    ``expected_install_method`` silenced :func:`doctor.check_claude_doctor`'s
    advisory finding while ``classic.PreToolUse`` - the only path that can deny
    a tool call - kept enforcing the constant. Measured in one session: the
    doctor's finding disappeared and the hook's behaviour did not change.
    """
    monkeypatch.setattr(
        claude_doctor, "_run", _fake_run(doctor=(0, CURRENT_NON_NATIVE_DOCTOR))
    )
    root = _baseline(tmp_path, 'expected_install_method = "npm-global"')
    assert claude_doctor.claude_doctor_main(project_root=root) == 0
    assert json.loads(capsys.readouterr().out)["verdict"] == Verdict.OK


def test_the_enforcing_cli_still_blocks_when_the_baseline_disagrees(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    """The control arm: the same seam must still produce INVALID.

    A lever that can only relax is not a lever. Without this arm a
    ``load_baseline`` that always returned a matching method would pass the
    test above.
    """
    monkeypatch.setattr(
        claude_doctor, "_run", _fake_run(doctor=(0, CURRENT_NON_NATIVE_DOCTOR))
    )
    root = _baseline(tmp_path, 'expected_install_method = "native"')
    assert claude_doctor.claude_doctor_main(project_root=root) == 1
    assert json.loads(capsys.readouterr().out)["verdict"] == Verdict.INVALID


def test_the_baseline_off_switch_reaches_the_enforcing_path(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    """``enabled = false`` must stop the DENY, not just the advisory finding.

    UNKNOWN rather than OK, because ``doctor.toml`` warns that a disabled check
    "reports nothing, which reads exactly like a healthy host".
    """
    monkeypatch.setattr(
        claude_doctor, "_run", _fake_run(doctor=(0, CURRENT_NON_NATIVE_DOCTOR))
    )
    root = _baseline(tmp_path, 'enabled = false\nexpected_install_method = "native"')
    assert claude_doctor.claude_doctor_main(project_root=root) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["verdict"] == Verdict.UNKNOWN
    assert payload["enforcement_eligible"] is False
    assert payload["disabled_by_baseline"] is True
    assert payload["baseline_path"] == str((root / "doctor.toml").absolute())
    assert "not a clean bill of health" in payload["findings"][0].lower()


def _baseline_read_failure_finding(baseline_path: Path) -> str:
    return (
        f"claude-doctor could not read or parse {baseline_path}; asserted defaults: "
        "enabled = true and expected_install_method = 'native'."
    )


def test_a_missing_baseline_asserts_the_documented_default_silently(
    tmp_path: Path,
) -> None:
    """An absent baseline asserts ``native`` without diagnosing an error.

    The failure direction matters: falling back to "disabled" would turn a
    typo in ``doctor.toml`` into a check that reads exactly like a healthy host.
    """
    baseline_path = (tmp_path / "doctor.toml").absolute()
    findings: list[str] = []
    assert claude_doctor.load_baseline(tmp_path, findings=findings) == (
        True,
        claude_doctor.NATIVE_METHOD,
        baseline_path,
    )
    assert findings == []


def test_invalid_toml_asserts_defaults_with_a_finding(tmp_path: Path) -> None:
    baseline_path = (tmp_path / "doctor.toml").absolute()
    (tmp_path / "doctor.toml").write_text("this is not = valid toml [[[")
    findings: list[str] = []

    assert claude_doctor.load_baseline(tmp_path, findings=findings) == (
        True,
        claude_doctor.NATIVE_METHOD,
        baseline_path,
    )
    assert findings == [_baseline_read_failure_finding(baseline_path)]


def test_a_non_utf8_baseline_asserts_the_documented_default(tmp_path: Path) -> None:
    """A decode failure uses the same fail-safe fallback as missing or bad TOML."""
    baseline_path = (tmp_path / "doctor.toml").absolute()
    baseline_path.write_bytes(b"\xff")
    findings: list[str] = []

    assert claude_doctor.load_baseline(tmp_path, findings=findings) == (
        True,
        claude_doctor.NATIVE_METHOD,
        baseline_path,
    )
    assert findings == [_baseline_read_failure_finding(baseline_path)]


def test_an_os_error_asserts_defaults_with_a_finding(tmp_path: Path) -> None:
    baseline_path = (tmp_path / "doctor.toml").absolute()
    baseline_path.mkdir()
    findings: list[str] = []

    assert claude_doctor.load_baseline(tmp_path, findings=findings) == (
        True,
        claude_doctor.NATIVE_METHOD,
        baseline_path,
    )
    assert findings == [_baseline_read_failure_finding(baseline_path)]


def test_the_baseline_is_read_as_utf8(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    baseline_path = (tmp_path / "doctor.toml").absolute()
    baseline_path.write_text("[claude]\nenabled = true\n", encoding="utf-8")
    original_read_text = Path.read_text
    seen: list[tuple[str | None, str | None]] = []

    def read_text(
        path: Path, encoding: str | None = None, errors: str | None = None
    ) -> str:
        seen.append((encoding, errors))
        return original_read_text(path, encoding=encoding, errors=errors)

    monkeypatch.setattr(Path, "read_text", read_text)
    findings: list[str] = []

    assert claude_doctor.load_baseline(tmp_path, findings=findings) == (
        True,
        claude_doctor.NATIVE_METHOD,
        baseline_path,
    )
    assert seen == [("utf-8", None)]
    assert findings == []


def test_a_baseline_read_failure_is_non_enforcing_but_visible(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    """The diagnostic is added after evaluation and cannot become an assertion."""
    monkeypatch.setattr(claude_doctor, "_run", _fake_run())
    baseline_path = (tmp_path / "doctor.toml").absolute()
    baseline_path.write_bytes(b"\xff")

    assert claude_doctor.claude_doctor_main(project_root=tmp_path) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["verdict"] == Verdict.OK
    assert payload["enforcement_eligible"] is False
    assert payload["findings"] == [_baseline_read_failure_finding(baseline_path)]


def test_the_cli_hands_the_project_root_to_the_baseline_loader() -> None:
    """Wiring guard: the seam reverts to cwd silently if this argument is lost.

    ``load_baseline`` falls back to ``CLAUDE_PROJECT_DIR`` or ``"."``, so a
    dropped argument keeps every unit test green while the hook - which runs
    with its own cwd - reads the wrong file or none at all.
    """
    main_src = (REPO_ROOT / "python" / "src" / "dotfiles_setup" / "main.py").read_text()
    wired = (
        "claude_doctor_main(\n"
        "                force_refresh=not args.no_refresh, project_root=project_root\n"
        "            )"
    )
    assert wired in main_src, (
        "`claude-doctor` must pass project_root, or the enforcing path resolves "
        "doctor.toml against the process cwd instead of the repository"
    )


def _sources_with(version: str, tmp_path: Path) -> Path:
    """A minimal repo root whose sources.toml pins claude-code at `version`."""
    schemas = tmp_path / "schemas"
    schemas.mkdir(parents=True, exist_ok=True)
    (schemas / "sources.toml").write_text(
        "[[schema]]\n"
        'tool = "claude-code"\n'
        'file = ".claude/types/claude-code.d.ts"\n'
        f'version = "{version}"\n'
        f'source = "https://example.invalid/v{version}/claude-code.d.ts"\n'
        'pin_source = "schemas/sources.toml"\n'
        'sha256 = "0" \n',
        encoding="utf-8",
    )
    return tmp_path


def test_unreadable_running_value_does_not_make_pin_drift_enforcing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """A stale repo pin cannot turn an unanswered host question into a deny."""
    root = _sources_with("2.1.272", tmp_path)
    doctor = "Running: native (unknown)\nNo installation issues found.\n"
    _stub_process_boundary(
        monkeypatch,
        doctor_responses=[(0, doctor, "")],
        oracle_responses=[(0, "2.1.273\n", "")],
    )

    result = claude_doctor.evaluate(project_root=root)

    assert result.verdict is Verdict.UNKNOWN
    assert result.enforcement_eligible is False
    assert "non-version running value" in result.findings[0]
    assert "schemas/sources.toml pins claude-code at 2.1.272" in result.findings[1]
    assert not any("claude on PATH is unknown but" in item for item in result.findings)


@pytest.mark.parametrize(
    "case",
    [
        (False, False, False, "current", Verdict.OK),
        (False, False, True, "current", Verdict.DRIFT),
        (False, True, False, "current", Verdict.INVALID),
        (False, True, True, "current", Verdict.INVALID),
        (True, False, False, "current", Verdict.INVALID),
        (True, False, True, "current", Verdict.INVALID),
        (True, True, False, "current", Verdict.INVALID),
        (True, True, True, "current", Verdict.INVALID),
        (False, False, False, "mismatch", Verdict.INVALID),
        (False, False, True, "mismatch", Verdict.INVALID),
        (False, True, False, "mismatch", Verdict.INVALID),
        (False, True, True, "mismatch", Verdict.INVALID),
        (True, False, False, "mismatch", Verdict.INVALID),
        (True, False, True, "mismatch", Verdict.INVALID),
        (True, True, False, "mismatch", Verdict.INVALID),
        (True, True, True, "mismatch", Verdict.INVALID),
        (False, False, False, "unreadable", Verdict.UNKNOWN),
        (False, False, True, "unreadable", Verdict.UNKNOWN),
        (False, True, False, "unreadable", Verdict.INVALID),
        (False, True, True, "unreadable", Verdict.INVALID),
        (True, False, False, "unreadable", Verdict.INVALID),
        (True, False, True, "unreadable", Verdict.INVALID),
        (True, True, False, "unreadable", Verdict.INVALID),
        (True, True, True, "unreadable", Verdict.INVALID),
    ],
)
def test_verdict_matrix_preserves_host_enforcement_and_isolates_pin_drift(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    case: tuple[bool, bool, bool, str, Verdict],
) -> None:
    """Every valid combination of the five verdict axes has a pinned outcome."""
    method_failed, clean_failed, pin_drift, running, expected = case
    latest = "2.1.273"
    running_token = {
        "current": latest,
        "mismatch": "2.1.272",
        "unreadable": "dev-build",
    }[running]
    method = "npm-global" if method_failed else "native"
    clean_line = "Found 1 problem." if clean_failed else "No installation issues found."
    root = _sources_with("2.1.272" if pin_drift else latest, tmp_path)
    _stub_process_boundary(
        monkeypatch,
        doctor_responses=[
            (0, f"Running: {method} ({running_token})\n{clean_line}\n", "")
        ],
        oracle_responses=[(0, f"{latest}\n", "")],
    )

    result = claude_doctor.evaluate(project_root=root)

    assert result.verdict is expected
    assert result.enforcement_eligible is (expected is Verdict.INVALID)


def test_pin_only_is_reported_but_the_cli_returns_zero(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    """The 2026-09-21 ruling changes pin-only reporting, not its visibility."""
    root = _sources_with("2.1.272", tmp_path)
    (root / "doctor.toml").write_text(
        '[claude]\nenabled = true\nexpected_install_method = "native"\n',
        encoding="utf-8",
    )
    _stub_process_boundary(
        monkeypatch,
        doctor_responses=[
            (0, "Running: native (2.1.273)\nNo installation issues found.\n", "")
        ],
        oracle_responses=[(0, "2.1.273\n", "")],
    )

    assert claude_doctor.claude_doctor_main(project_root=root) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["verdict"] == "drift"
    assert payload["enforcement_eligible"] is False
    assert payload["findings"]


def test_pin_plus_method_failure_still_returns_one(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    """A repo finding must not mask an independently broken host install."""
    root = _sources_with("2.1.272", tmp_path)
    (root / "doctor.toml").write_text(
        '[claude]\nenabled = true\nexpected_install_method = "native"\n',
        encoding="utf-8",
    )
    doctor = "Running: npm-global (2.1.273)\nNo installation issues found.\n"
    _stub_process_boundary(
        monkeypatch,
        doctor_responses=[(0, doctor, "")],
        oracle_responses=[(0, "2.1.273\n", "")],
    )

    assert claude_doctor.claude_doctor_main(project_root=root) == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["verdict"] == "invalid"
    assert payload["enforcement_eligible"] is True


def test_unreadable_running_value_with_current_pin_remains_unknown(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Skipping the one unaskable comparison must never manufacture OK."""
    root = _sources_with("2.1.273", tmp_path)
    doctor = "Running: native (unknown)\nNo installation issues found.\n"
    _stub_process_boundary(
        monkeypatch,
        doctor_responses=[(0, doctor, "")],
        oracle_responses=[(0, "2.1.273\n", "")],
    )

    result = claude_doctor.evaluate(project_root=root)

    assert result.verdict is Verdict.UNKNOWN
    assert result.enforcement_eligible is False
    assert result.findings == [
        "`claude doctor` returned a non-version running value: 'unknown'"
    ]


def test_findings_keep_head_order_method_version_pin_then_clean(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """The hook prints item zero first, so order is part of its public output."""
    root = _sources_with("2.1.272", tmp_path)
    doctor = "Running: npm-global (2.1.270)\nFound 1 problem.\n"
    _stub_process_boundary(
        monkeypatch,
        doctor_responses=[(0, doctor, "")],
        oracle_responses=[(0, "2.1.273\n", "")],
    )

    result = claude_doctor.evaluate(project_root=root)

    assert result.verdict is Verdict.INVALID
    assert len(result.findings) == 4
    assert "not the expected 'native'" in result.findings[0]
    assert "claude on PATH is 2.1.270 but 2.1.273 is published" in result.findings[1]
    assert "schemas/sources.toml pins claude-code at 2.1.272" in result.findings[2]
    assert "installation issues" in result.findings[3]


def test_a_current_pin_reports_nothing(tmp_path: Path) -> None:
    """Control arm: without it the failing arm below proves nothing."""
    root = _sources_with("2.1.273", tmp_path)

    assert claude_doctor.pin_currency_findings("2.1.273", root) == []


def test_a_pin_behind_upstream_is_reported(tmp_path: Path) -> None:
    """The gap this closes: nothing else watches the repo's own pin.

    Renovate cannot see a tool with no mise entry, `currency.toml` excludes
    claude-code deliberately, and `schema_vendor.refresh` re-fetches at the
    version already recorded rather than resolving a newer one. Measured
    2026-09-15: the pin sat at 2.1.272 while 2.1.273 was published and every
    gate was green.
    """
    root = _sources_with("2.1.272", tmp_path)

    findings = claude_doctor.pin_currency_findings("2.1.273", root)

    assert len(findings) == 1, findings
    assert "2.1.272" in findings[0]
    assert "2.1.273" in findings[0]


def test_a_tree_without_sources_toml_is_not_this_repo(tmp_path: Path) -> None:
    """A non-repo root must not manufacture a host finding.

    Every other finding in this module is about the machine. Reporting one for
    a directory that simply has no `schemas/sources.toml` would make
    `claude_doctor_main(project_root=<anything>)` fail on a question that does
    not apply to it — which is how this seam was first caught.
    """
    assert claude_doctor.pin_currency_findings("2.1.273", tmp_path) == []


def test_an_unreadable_pin_is_a_finding_not_silence(tmp_path: Path) -> None:
    """A sources.toml that EXISTS but lacks the row is a real gap.

    Distinct from the case above: the file is this repo's, so the question
    applies — and a pin nothing can read is a pin nothing is checking.
    """
    schemas = tmp_path / "schemas"
    schemas.mkdir(parents=True)
    (schemas / "sources.toml").write_text(
        '[[schema]]\ntool = "mise"\nfile = "schemas/mise.json"\n'
        'version = "1"\nsource = "https://example.invalid/x"\n'
        'pin_source = "x"\nsha256 = "0"\n',
        encoding="utf-8",
    )

    findings = claude_doctor.pin_currency_findings("2.1.273", tmp_path)

    assert len(findings) == 1, findings
    assert "UNKNOWN" in findings[0]


@pytest.mark.parametrize(
    "body",
    [
        '[[schema]]\ntool = "claude-code"\nfile = "claude-code.d.ts"\n',
        'schema = "not-a-list-of-tables"\n',
    ],
    ids=["missing-key", "scalar-schema"],
)
def test_malformed_pin_shapes_emit_an_enforcing_verdict(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
    body: str,
) -> None:
    """Malformed pin structure must be a verdict, never an escaping exception."""
    schemas = tmp_path / "schemas"
    schemas.mkdir(parents=True)
    (schemas / "sources.toml").write_text(body, encoding="utf-8")
    (tmp_path / "doctor.toml").write_text(
        '[claude]\nenabled = true\nexpected_install_method = "native"\n',
        encoding="utf-8",
    )
    _stub_process_boundary(
        monkeypatch,
        doctor_responses=[
            (0, "Running: native (2.1.273)\nNo installation issues found.\n", "")
        ],
        oracle_responses=[(0, "2.1.273\n", "")],
    )

    assert claude_doctor.claude_doctor_main(project_root=tmp_path) == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["verdict"] == Verdict.INVALID
    assert payload["enforcement_eligible"] is True
    assert "cannot read the claude-code pin" in payload["findings"][0]
    assert "pin currency is UNKNOWN" in payload["findings"][0]


def test_an_unreadable_pin_keeps_its_prior_enforcement(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Only established stale-pin drift receives the 2026-09-21 exception."""
    schemas = tmp_path / "schemas"
    schemas.mkdir(parents=True)
    (schemas / "sources.toml").write_text(
        '[[schema]]\ntool = "mise"\nfile = "schemas/mise.json"\n'
        'version = "1"\nsource = "https://example.invalid/x"\n'
        'pin_source = "x"\nsha256 = "0"\n',
        encoding="utf-8",
    )
    _stub_process_boundary(
        monkeypatch,
        doctor_responses=[
            (0, "Running: native (2.1.273)\nNo installation issues found.\n", "")
        ],
        oracle_responses=[(0, "2.1.273\n", "")],
    )

    result = claude_doctor.evaluate(project_root=tmp_path)

    assert result.verdict is Verdict.INVALID
    assert result.enforcement_eligible is True
    assert "pin currency is UNKNOWN" in result.findings[0]


def test_the_pin_check_is_wired_into_evaluate(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Bind the CALL SITE, not just the helper.

    A helper with perfect arms that nothing calls is the classic way a gate
    stops biting while every logic test stays green — so this asserts
    `evaluate` reaches it, and that `check_pin=False` really suppresses it.
    """
    monkeypatch.setattr(
        claude_doctor,
        "_run",
        _fake_run(doctor=(0, NATIVE_DOCTOR), oracle=(0, "2.1.270\n")),
    )
    root = _sources_with("2.1.269", tmp_path)

    on = claude_doctor.evaluate(project_root=root)
    assert on.verdict is Verdict.DRIFT
    assert any("schemas/sources.toml pins claude-code" in item for item in on.findings)

    off = claude_doctor.evaluate(check_pin=False, project_root=root)
    assert off.verdict is Verdict.OK
    assert not any(
        "schemas/sources.toml pins claude-code" in item for item in off.findings
    )
