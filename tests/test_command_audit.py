"""Tests for the command-audit transcript scanner (dotfiles_setup.command_audit).

Covers transcript discovery (env-aware, never hardcoded), defensive JSONL
parsing, attempt-to-result pairing (a denied Bash call is recorded exactly like
an executed one — only the result tells them apart), the
bypass/blocked/pre_rule/mise/diagnostic/one_off classifier (incl. cd-prefix
compound unwrapping), grouping, report rendering, and the ``--output`` path the
SessionEnd hook uses to refresh the report once per session.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "python" / "src"))

import pytest
from dotfiles_setup import command_audit as ca

# --------------------------------------------------------- discovery / encoding


def test_transcripts_base_uses_config_dir_env() -> None:
    base = ca.transcripts_base({"CLAUDE_CONFIG_DIR": "/x/cfg"}, Path("/home/u"))
    assert base == Path("/x/cfg/projects")


def test_transcripts_base_defaults_to_home_claude() -> None:
    base = ca.transcripts_base({}, Path("/home/u"))
    assert base == Path("/home/u/.claude/projects")


def test_encode_cwd_replaces_slashes_and_dots() -> None:
    assert ca.encode_cwd(Path("/Users/x/dev/dot.files")) == "-Users-x-dev-dot-files"


def test_project_transcripts_missing_dir_is_empty(tmp_path: Path) -> None:
    assert ca.project_transcripts(tmp_path, Path("/no/such/cwd"), limit=5) == []


def test_project_transcripts_limit_and_recency(tmp_path: Path) -> None:
    cwd = Path("/repo")
    proj = tmp_path / ca.encode_cwd(cwd)
    proj.mkdir()
    for i in range(4):
        f = proj / f"s{i}.jsonl"
        f.write_text("{}\n")
    # Make s3 the newest, s0 the oldest via mtime.
    for i in range(4):
        ts = 1_000 + i * 10
        os.utime(proj / f"s{i}.jsonl", (ts, ts))
    got = ca.project_transcripts(tmp_path, cwd, limit=2)
    assert [p.name for p in got] == ["s3.jsonl", "s2.jsonl"]


# ------------------------------------------------------------ defensive parsing


# Any date strictly after every rule's `since`, so seeded commands land in the
# live-rule era (the pre_rule cutoff is exercised separately, by classify).
_LIVE_TS = "2026-07-20T00:00:00Z"


def _assistant_bash(cmd: str, uid: str = "tu1", ts: str = _LIVE_TS) -> str:
    return json.dumps(
        {
            "type": "assistant",
            "sessionId": "sess1",
            "timestamp": ts,
            "message": {
                "content": [
                    {
                        "type": "tool_use",
                        "id": uid,
                        "name": "Bash",
                        "input": {"command": cmd},
                    }
                ]
            },
        }
    )


def _result(uid: str, *, executed: bool) -> str:
    """A tool_result line: dict-with-stdout when it ran, bare str when refused.

    Mirrors the real shapes probed 2026-07-14 — a refused call carries the
    guard's reason as a plain string, an executed one a stdout-bearing dict.
    """
    return json.dumps(
        {
            "type": "user",
            "toolUseResult": (
                {"stdout": "out", "stderr": "", "interrupted": False}
                if executed
                else "Error: Use `mise run ship` — …"
            ),
            "message": {
                "content": [{"type": "tool_result", "tool_use_id": uid}],
            },
        }
    )


def test_iter_bash_commands_extracts_and_skips_defensively(tmp_path: Path) -> None:
    f = tmp_path / "t.jsonl"
    f.write_text(
        "\n".join(
            [
                "not json at all",  # malformed -> skipped
                json.dumps(
                    {"type": "user", "message": {"content": "hi"}}
                ),  # not assistant
                json.dumps(
                    {
                        "type": "assistant",
                        "message": {"content": [{"type": "text", "text": "x"}]},
                    }
                ),  # not a Bash tool_use
                json.dumps(
                    {
                        "type": "assistant",
                        "message": {
                            "content": [
                                {"type": "tool_use", "name": "Read", "input": {}}
                            ]
                        },
                    }
                ),  # non-Bash tool
                json.dumps(
                    {
                        "type": "assistant",
                        "message": {
                            "content": [
                                {"type": "tool_use", "name": "Bash", "input": {}}
                            ]
                        },
                    }
                ),  # Bash but no command
                _assistant_bash("ls -la"),  # the only real one
                "",  # blank -> skipped
            ]
        )
    )
    cmds = list(ca.iter_bash_commands([f]))
    assert [c.command for c in cmds] == ["ls -la"]
    assert cmds[0].session == "sess1"
    # No tool_result for it: unproven execution never counts as executed.
    assert cmds[0].executed is False


def test_iter_bash_commands_unreadable_file_skipped(tmp_path: Path) -> None:
    assert list(ca.iter_bash_commands([tmp_path / "does-not-exist.jsonl"])) == []


def test_iter_bash_commands_pairs_results_to_attempts(tmp_path: Path) -> None:
    """The transcript records a denied attempt exactly like an executed one.

    Only the paired tool_result separates them, so this pairing is the whole
    basis for telling a guard bypass from the guard working.
    """
    f = tmp_path / "t.jsonl"
    f.write_text(
        "\n".join(
            [
                _assistant_bash("ls -la", uid="a"),
                _assistant_bash("gh pr create --fill", uid="b"),
                _assistant_bash("git status", uid="c"),
                # Results arrive on LATER lines, and out of order — the pairing
                # is by id, never by position.
                _result("b", executed=False),  # guard refused it
                _result("a", executed=True),
                # (no result for "c" — still in flight)
            ]
        )
    )
    got = {c.command: c.executed for c in ca.iter_bash_commands([f])}
    assert got == {
        "ls -la": True,
        "gh pr create --fill": False,
        "git status": False,
    }


# ------------------------------------------------------------- classification


@pytest.mark.parametrize(
    "command",
    [
        "mise run lint",
        "uv run --project python dotfiles-setup verify run",
        "uv run --project python pytest tests/",
        "cd /repo && mise run ship",
    ],
)
def test_is_mise_backed(command: str) -> None:
    assert ca.is_mise_backed(command)


@pytest.mark.parametrize(
    "command",
    [
        "ls -la",
        "cat x",
        "git status",
        "git log --oneline",
        "docker ps",
        "gh pr view 1 --json state",
        "cd /repo && cat x",
        "grep foo bar",
    ],
)
def test_diagnostic_reads(command: str) -> None:
    assert ca.is_diagnostic(command)


@pytest.mark.parametrize(
    "command",
    [
        "git commit -m x",
        "docker run --rm ubuntu",
        "gh pr merge 1",
        "chmod +x f",
        "cd /repo && git commit -m y",
        "docker exec c ls",
    ],
)
def test_not_diagnostic_mutations(command: str) -> None:
    assert not ca.is_diagnostic(command)


def _bc(command: str, *, ts: str = _LIVE_TS, executed: bool = True) -> ca.BashCommand:
    return ca.BashCommand(command, session="s", timestamp=ts, executed=executed)


def test_classify_precedence() -> None:
    # A guard rule wins even inside a cd compound.
    assert ca.classify(_bc("cd /repo && gh pr create --fill")) == "bypass"
    assert ca.classify(_bc("mise run lint")) == "mise"
    assert ca.classify(_bc("git status")) == "diagnostic"
    assert ca.classify(_bc("git commit -m x")) == "one_off"
    assert ca.classify(_bc("docker run --rm ubuntu bash -c 'x'")) == "one_off"


@pytest.mark.parametrize(
    ("ts", "executed", "expected"),
    [
        # Live rule (gh pr create landed 2026-07-07) + it really ran = evasion.
        ("2026-07-08T00:00:00Z", True, "bypass"),
        # Live rule but refused: the guard working, not a bypass.
        ("2026-07-08T00:00:00Z", False, "blocked"),
        # Before the rule existed — history, whether or not it ran.
        ("2026-07-01T00:00:00Z", True, "pre_rule"),
        ("2026-07-01T00:00:00Z", False, "pre_rule"),
        # The rule's own landing day counts as pre-rule: it may have merged
        # later that day, and a false alarm costs more than a missed one.
        ("2026-07-07T23:59:59Z", True, "pre_rule"),
        # No timestamp ⇒ no evidence ⇒ no alarm.
        ("", True, "pre_rule"),
    ],
)
def test_classify_rule_match_splits_by_era_and_outcome(
    ts: str, expected: str, *, executed: bool
) -> None:
    """A bare "matched a rule" verdict was 98% noise; these two axes fix it.

    Measured 2026-07-14 over 3,615 real commands: 155 matched a rule — 147
    predated it, 3 were denials, 0 were bypasses.
    """
    assert ca.classify(_bc("gh pr create --fill", ts=ts, executed=executed)) == expected


def test_classify_uses_the_matched_rules_own_since_date() -> None:
    """Rules landed on different dates, so the cutoff must be per-rule.

    `gh run watch` landed 2026-07-14, a week after `gh pr create` — on
    2026-07-10 the first is still history while the second is already live.
    """
    assert ca.classify(_bc("gh run watch 1", ts="2026-07-10T00:00:00Z")) == "pre_rule"
    assert ca.classify(_bc("gh pr create", ts="2026-07-10T00:00:00Z")) == "bypass"


def test_group_key_uses_operative_head_sub() -> None:
    # group_key exercises _operative: single + repeated cd-prefix, bare cd, plain.
    assert ca.group_key("cd /repo && docker exec c ls") == "docker exec"
    assert ca.group_key("cd /a && cd /b && ls -la") == "ls -la"
    assert ca.group_key("git commit -m 'x'") == "git commit"
    assert ca.group_key("cd /repo") == "cd /repo"


# -------------------------------------------------------------- audit + report


def _cmds(*commands: str) -> list[ca.BashCommand]:
    return [_bc(c) for c in commands]


def test_audit_counts_and_ranks() -> None:
    result = ca.audit(
        _cmds(
            "git commit -m a",
            "git commit -m b",  # one_off, grouped
            "docker run --rm x",  # one_off
            "ls",  # diagnostic
            "mise run lint",  # mise
            "gh pr create",  # bypass (live rule + executed)
        ),
        sessions=2,
    )
    assert result.total == 6
    assert result.sessions == 2
    assert result.counts["one_off"] == 3
    assert result.counts["diagnostic"] == 1
    assert result.counts["mise"] == 1
    assert result.counts["bypass"] == 1
    # "git commit" is the top one-off group with count 2
    assert result.one_off_groups[0][0] == "git commit"
    assert result.one_off_groups[0][1] == 2


def test_audit_groups_denials_by_rule_not_command_shape() -> None:
    """Denials group by the rule that fired — the command's own head is junk.

    Both commands here are the shape of the guard's one real denial (recovered
    verbatim 2026-07-14): a `cd` + `echo` preamble, then the operative `npx`
    reached through a genuine `||` fallback. Their head is `echo`, which names
    nothing a reader could act on; the rule identity is the thing to audit.

    The earlier fixture here used the quoted-regex FALSE positive
    (`grep -E "…|devcontainer up|…"`). #265 fixed that shape, so it is no longer
    denied and can no longer reach this path — the grouping rule it was written
    to prove still holds, and now rests on a denial that is actually correct.
    """
    preamble = "cd /repo\necho '===== validator ====='\n"
    result = ca.audit(
        [
            _bc(
                preamble + "mise exec -- rcv --strict || npx --yes rcv --strict",
                executed=False,
            ),
            _bc(
                preamble + "mise exec -- rcv | tail -20 || npx --yes rcv",
                executed=False,
            ),
        ],
        sessions=1,
    )
    assert result.counts["blocked"] == 2
    assert [(k, n) for k, n, _ex in result.blocked_groups] == [("npx", 2)]
    # The point of the rule-name grouping: the head names nothing useful.
    assert ca.group_key(preamble + "mise exec -- rcv || npx --yes rcv") == "echo '====="


def test_render_report_has_sections_and_counts() -> None:
    result = ca.audit(_cmds("git commit -m x", "gh pr create"), sessions=1)
    report = ca.render_report(result)
    assert "# Command audit" in report
    assert "One-off culprits" in report
    assert "Bypasses (ran despite a live guard rule)" in report
    assert "`git commit`" in report
    assert "mise-tasks-only.md" in report


def test_render_report_no_bypasses_says_so() -> None:
    """Zero bypasses is the expected steady state — report it, don't omit it."""
    report = ca.render_report(ca.audit(_cmds("ls", "git commit -m x"), sessions=1))
    assert "_None — nothing has evaded the guard since its rule landed._" in report
    # A clean run must not imply the guard was never exercised.
    assert "Guard denials" not in report


def test_render_report_no_one_offs() -> None:
    result = ca.audit(_cmds("ls", "git status"), sessions=1)
    report = ca.render_report(result)
    assert "_None — no un-wrapped one-off commands found._" in report


# ------------------------------------------- --output (the SessionEnd hook path)


def _seed_transcript(tmp_path: Path, project: Path, *commands: str) -> Path:
    """A CLAUDE_CONFIG_DIR holding one transcript for ``project``."""
    cfg = tmp_path / "cfg"
    proj = cfg / "projects" / ca.encode_cwd(project)
    proj.mkdir(parents=True)
    (proj / "s.jsonl").write_text("\n".join(_assistant_bash(c) for c in commands))
    return cfg


def test_write_report_resolves_relative_to_project_root(tmp_path: Path) -> None:
    """Relative output is repo-anchored (the hook must not depend on cwd)."""
    dest = ca.write_report("body", tmp_path, Path(".agent/command-audit.md"))
    assert dest == tmp_path / ".agent" / "command-audit.md"
    assert dest.read_text() == "body"  # parent created on demand


def test_write_report_honors_absolute_path(tmp_path: Path) -> None:
    target = tmp_path / "out" / "r.md"
    assert ca.write_report("body", tmp_path / "unused", target) == target
    assert target.read_text() == "body"


def test_main_output_writes_file_instead_of_stdout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    project = tmp_path / "repo"
    project.mkdir()
    monkeypatch.setenv(
        "CLAUDE_CONFIG_DIR",
        str(_seed_transcript(tmp_path, project, "git commit -m x", "ls")),
    )
    assert ca.command_audit_main(project, output=Path(".agent/command-audit.md")) == 0
    report = (project / ".agent" / "command-audit.md").read_text()
    assert "# Command audit" in report
    assert "`git commit`" in report
    out = capsys.readouterr().out
    assert "wrote" in out
    assert "# Command audit" not in out  # the body went to the file, not stdout


def test_main_without_output_prints_report(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    project = tmp_path / "repo"
    project.mkdir()
    monkeypatch.setenv(
        "CLAUDE_CONFIG_DIR", str(_seed_transcript(tmp_path, project, "git commit -m x"))
    )
    assert ca.command_audit_main(project) == 0
    assert "# Command audit" in capsys.readouterr().out


def test_main_no_transcripts_leaves_existing_report_intact(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A miss must not clobber a good report with an empty/notice file."""
    project = tmp_path / "repo"
    (project / ".agent").mkdir(parents=True)
    stale = project / ".agent" / "command-audit.md"
    stale.write_text("previous report")
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path / "empty"))
    assert ca.command_audit_main(project, output=Path(".agent/command-audit.md")) == 0
    assert stale.read_text() == "previous report"
    assert "no transcripts" in capsys.readouterr().out


def test_cli_accepts_the_session_end_output_flag() -> None:
    """The flag the SessionEnd hook passes must exist on the REAL CLI.

    The wiring check asserts settings.json names `--output`; this asserts
    argparse actually accepts it, so the hook cannot fail only at runtime.
    """
    res = subprocess.run(
        [
            "uv",
            "run",
            "--project",
            "python",
            "dotfiles-setup",
            "command-audit",
            "--help",
        ],
        capture_output=True,
        text=True,
        check=False,
        cwd=Path(__file__).parent.parent,
        timeout=120,
    )
    assert res.returncode == 0
    assert "--output" in res.stdout


class TestFalseSignals:
    """#289: shapes whose ANSWER cannot be trusted.

    Orthogonal to `classify` — a diagnostic command can still lie. Each shape
    is pinned in BOTH directions per
    `.claude/rules/probes-need-a-control-arm.md`: a detector that only ever
    fires is as useless as one that never does.
    """

    def test_grep_q_under_pipefail_is_flagged(self) -> None:
        """The shape that broke the #289 base build.

        `apt-cache policy clang-22 | grep -q 'apt.llvm.org'` returned 141:
        grep -q closed the pipe ON MATCH, apt-cache took SIGPIPE, pipefail
        propagated it. The check failed BECAUSE it succeeded.
        """
        assert "grep_q_pipefail" in ca.false_signals(
            "apt-cache policy clang-22 | grep -q 'apt.llvm.org'"
        )

    def test_the_grep_q_fix_is_not_flagged(self) -> None:
        """CONTROL: the prescribed fix must not trip the detector.

        A detector that flags its own remedy trains the reader to ignore it.
        """
        assert ca.false_signals('out="$(cmd)"; grep -q PAT <<<"$out"') == []

    def test_pipe_then_read_rc_is_flagged(self) -> None:
        """`cmd | head; echo rc=$?` reads head's rc, not cmd's."""
        assert "pipe_then_rc" in ca.false_signals('typos f | head -3; echo "rc=$?"')

    def test_rc_without_a_pipe_is_not_flagged(self) -> None:
        """CONTROL: reading $? is correct when no pipe can steal it."""
        assert ca.false_signals('typos f > /tmp/o 2>&1; echo "rc=$?"') == []

    def test_depth_bounded_find_is_flagged(self) -> None:
        """The probe that called `grill-with-docs` absent; it sat at depth 7."""
        assert "bounded_find" in ca.false_signals(
            "find ~/.claude/plugins -iname '*grill*' -maxdepth 4"
        )

    def test_unbounded_and_deep_find_are_not_flagged(self) -> None:
        """CONTROL: only a SHALLOW bound turns 'unreachable' into 'absent'."""
        assert ca.false_signals("find . -name '*.py'") == []
        assert ca.false_signals("find . -name '*.py' -maxdepth 8") == []

    def test_nested_quoting_via_docker_exec_is_flagged(self) -> None:
        """25x in one session; mangled an openmp probe into a false FAIL."""
        assert "nested_quote_exec" in ca.false_signals(
            'docker exec "$C" bash -lc "echo hi"'
        )

    def test_docker_cp_script_form_is_not_flagged(self) -> None:
        """CONTROL: the prescribed fix (write a file, cp it, run it) is clean."""
        assert ca.false_signals("docker exec $C bash /tmp/probe.sh") == []

    def test_every_shape_has_advice(self) -> None:
        """A finding without a remedy is noise; each shape must explain itself."""
        for shape in (
            "pipe_then_rc",
            "grep_q_pipefail",
            "bounded_find",
            "nested_quote_exec",
        ):
            assert len(ca.false_signal_advice(shape)) > 20

    def test_clean_commands_yield_nothing(self) -> None:
        """CONTROL: ordinary work must not be flagged at all."""
        for cmd in ("git status --short", "mise run lint", "ls -la"):
            assert ca.false_signals(cmd) == []
