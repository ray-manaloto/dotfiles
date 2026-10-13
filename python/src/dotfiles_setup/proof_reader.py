# Copyright (c) 2026 Raymond Manaloto
"""Read retained evidence against independently bound authoritative inputs.

These readers never execute product code, discover native journals, or infer an
oracle from a receipt's own expected/count fields. C1 supplies independently
reviewed normative inputs and pins their hashes before START. ``baseline`` inputs
are exclusively for historical cache/transport comparisons; they cannot define
coverage. Paths are explicit absolute originals, optionally mapped by the caller
for portable fixtures. Descriptive labels and quoted commands are not paths or
execution evidence. ALLOW means this reader's bounded checks passed, not that a
native proof attempt or aggregate delivery completed.

The dataclasses below are in-memory reader values, not new serialization models.
External schemas remain native mappings; serialization uses the project codec.
"""

from __future__ import annotations

import hashlib
import re
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Literal, Never

from dotfiles_setup import codec

MAX_COMMAND_SECONDS = 120


def _reject(message: str) -> Never:
    raise ValueError(message)


type Decision = Literal["ALLOW", "PENDING", "DENY"]
type InputRole = Literal["normative", "baseline"]


@dataclass(frozen=True)
class BoundInput:
    """Caller-pinned bytes with an explicit independent authority role."""

    path: Path
    sha256: str
    role: InputRole
    content: bytes


@dataclass(frozen=True)
class CommandExpectation:
    """Typed normative command identity; never constructed from checked output."""

    control_id: str
    argv: tuple[str, ...]
    cwd: Path
    actual_rc: int
    expected_rc: int


@dataclass(frozen=True)
class CommandPlan:
    """Compiled independent command contract retained with its authoritative bytes."""

    authority: BoundInput
    execution: Literal["fresh", "historical"]
    commands: tuple[CommandExpectation, ...]
    fixture_git_roots: tuple[Path, ...]
    actor: tuple[tuple[str, str], ...]
    window: tuple[float, float]

    @property
    def command_ids(self) -> tuple[str, ...]:
        """Return the normative membership without reading receipt files."""
        return tuple(command.control_id for command in self.commands)


@dataclass(frozen=True)
class ReadResult:
    """Small observation; detailed evidence remains at its bound path."""

    status: Decision
    count: int = 0
    reasons: tuple[str, ...] = ()


def bind_input(path: Path, sha256: str, *, role: InputRole) -> BoundInput:
    """Pin an independent input; the expected hash must come from the caller."""
    if not isinstance(path, Path) or not path.is_absolute():
        _reject("authority must be a typed absolute path")
    if role not in {"normative", "baseline"}:
        _reject("unknown authority role")
    content = path.read_bytes()
    if hashlib.sha256(content).hexdigest() != sha256:
        _reject("authority byte binding differs")
    return BoundInput(path, sha256, role, content)


def _object(value: object) -> dict[str, object]:
    if not isinstance(value, dict) or any(not isinstance(k, str) for k in value):
        _reject("expected an object")
    return value


def _list(value: object) -> list[object]:
    if not isinstance(value, list):
        _reject("expected a list")
    return value


def _strings(value: object) -> list[str]:
    items = _list(value)
    if any(not isinstance(item, str) or not item for item in items):
        _reject("expected nonempty strings")
    return [str(item) for item in items]


def _authority(
    value: BoundInput, *, role: InputRole = "normative"
) -> dict[str, object]:
    if value.role != role or hashlib.sha256(value.content).hexdigest() != value.sha256:
        _reject("independent input role or byte binding differs")
    return _object(codec.decode(value.content, dict))


def _deny(error: ValueError | UnicodeError | KeyError | TypeError) -> ReadResult:
    return ReadResult("DENY", reasons=(str(error),))


def _collection_nodes(raw: bytes) -> list[str]:
    module = None
    observed: list[str] = []
    for line in raw.decode("utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("<Module "):
            match = re.fullmatch(r"<Module (test_[A-Za-z0-9_]+\.py)>", stripped)
            if match is None:
                _reject("invalid module context")
            module = "tests/" + match[1]
        elif stripped.startswith("<Function "):
            match = re.fullmatch(r"<Function (.+)>", stripped)
            if module is None or match is None:
                _reject("function has no valid module context")
            observed.append(module + "::" + match[1])
        elif stripped.startswith("<") and not stripped.startswith(
            ("<Dir ", "<Package ")
        ):
            _reject("unknown collection family")
    return observed


def read_collection(raw: bytes, expected: BoundInput) -> ReadResult:
    """Reconcile actual pytest Module/Function collections with normative nodes."""
    try:
        oracle = _authority(expected)
        nodes = _strings(oracle["nodes"])
        observed = _collection_nodes(raw)
        if not nodes or len(nodes) != len(set(nodes)):
            _reject("normative collection is empty or duplicated")
        if len(observed) != len(set(observed)) or set(observed) != set(nodes):
            _reject("collection membership differs or is duplicated")
        families = dict(Counter(node.split("[", 1)[0] for node in observed))
        if families != _object(oracle["family_counts"]):
            _reject("collection family counts differ")
        return ReadResult("ALLOW", len(observed))
    except (ValueError, UnicodeError, KeyError, TypeError) as error:
        return _deny(error)


def read_global_groups(observed: object, expected: BoundInput) -> ReadResult:
    """Compare complete global-group objects including all axis fields."""
    try:
        groups = [_object(row) for row in _list(observed)]
        required = [
            _object(row) for row in _list(_authority(expected)["global_groups"])
        ]
        fields = {"mode", "source", "selected_repositories"}
        for group in [*groups, *required]:
            if (
                set(group) != fields
                or group["mode"] not in {"--json", "--issue-plan"}
                or group["source"] not in {"plan", "inbox"}
                or type(group["selected_repositories"]) is not int
                or group["selected_repositories"] not in {1, 2}
            ):
                _reject("invalid global-group object")
        keys = [tuple(row[key] for key in sorted(fields)) for row in groups]
        normative = [tuple(row[key] for key in sorted(fields)) for row in required]
        if not normative or len(normative) != len(set(normative)):
            _reject("empty or duplicated normative groups")
        if len(keys) != len(set(keys)) or set(keys) != set(normative):
            _reject("global-group membership differs or is duplicated")
        return ReadResult("ALLOW", len(keys))
    except (ValueError, UnicodeError, KeyError, TypeError) as error:
        return _deny(error)


def _stamp(value: object) -> float:
    if not isinstance(value, str):
        _reject("timestamp is not a string")
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        _reject("timestamp has no timezone")
    return parsed.timestamp()


def _absolute(value: object) -> Path:
    if not isinstance(value, str) or not Path(value).is_absolute():
        _reject("expected an absolute original path")
    return Path(value)


def _command_plan(
    expected: BoundInput, execution: str
) -> tuple[
    list[dict[str, object]], list[str], list[str], dict[str, object], float, float
]:
    oracle = _authority(expected)
    planned = [_object(row) for row in _list(oracle["commands"])]
    ids = [str(row["control_id"]) for row in planned]
    roots = _strings(oracle["fixture_git_roots"])
    if (
        not ids
        or len(ids) != len(set(ids))
        or len(roots) != len(set(roots))
        or type(oracle["command_count"]) is not int
        or oracle["command_count"] != len(ids)
        or type(oracle["root_count"]) is not int
        or oracle["root_count"] != len(roots)
        or oracle["execution"] != execution
    ):
        _reject("normative command plan membership or execution role differs")
    actor = _object(oracle["actor"])
    if set(actor) != {"agent_id", "agent_role", "agent_path", "parent_id"} or any(
        not isinstance(value, str) or not value for value in actor.values()
    ):
        _reject("normative actor identity is incomplete")
    bindings = _object(oracle["bindings"])
    if (
        not _object(bindings["source_hashes_before"])
        or bindings["source_hashes_before"] != bindings["source_hashes_after"]
    ):
        _reject("normative source bindings differ")
    start, deadline = (
        _stamp(oracle["issued_at"]),
        _stamp(oracle["outer_deadline_utc"]),
    )
    if start >= deadline:
        _reject("normative execution window is empty")
    return planned, ids, roots, {**actor, **bindings}, start, deadline


def _validate_timing(record: dict[str, object], start: float, deadline: float) -> None:
    timeout, elapsed = record["timeout_s"], record["elapsed_s"]
    if (
        not isinstance(timeout, (float, int))
        or not isinstance(elapsed, (float, int))
        or isinstance(timeout, bool)
        or isinstance(elapsed, bool)
    ):
        _reject("command timing is not numeric")
    if not 0 <= elapsed <= timeout <= MAX_COMMAND_SECONDS or timeout == 0:
        _reject("command timing is outside its bound")
    if (
        not start
        < _stamp(record["launched_at"])
        <= _stamp(record["completed_at"])
        < deadline
    ):
        _reject("command is outside the independently bound execution window")


def _validate_logs(record: dict[str, object], path: Path) -> None:
    for stream in ["stdout", "stderr"]:
        if (
            hashlib.sha256((path.parent / f"{stream}.log").read_bytes()).hexdigest()
            != record[f"{stream}_sha256"]
        ):
            _reject("command captured bytes differ")


def _validate_command(
    record: dict[str, object],
    plan: dict[str, object],
    path: Path,
    bindings: dict[str, object],
    window: tuple[float, float],
) -> str | None:
    control = str(record["control_id"])
    argv = _strings(record["argv"])
    if not argv:
        _reject("command argv is empty")
    _absolute(record["cwd"])
    for key in ["control_id", "argv", "cwd", "actual_rc", "expected_rc"]:
        if record[key] != plan[key]:
            _reject(f"command {control}: normative {key} differs")
    if type(record["actual_rc"]) is not int or type(record["expected_rc"]) is not int:
        _reject("exit status must be an integer")
    if any(record[key] != value for key, value in bindings.items()):
        _reject(f"command {control}: actor or independent bindings differ")
    if (
        record["timed_out"] is not False
        or _object(record["cleanup"])["quiescent"] is not True
    ):
        _reject("command timed out or cleanup is incomplete")
    _validate_timing(record, *window)
    if record["fixture_git"] is not (argv[0] == "git"):
        _reject("command execution type differs from argv")
    _validate_logs(record, path)
    if argv[0] == "git" and "-C" in argv:
        index = argv.index("-C") + 1
        if index >= len(argv):
            _reject("Git command is missing its root")
        return str(_absolute(argv[index]))
    return None


def _command_expectation(row: dict[str, object]) -> CommandExpectation:
    argv = _strings(row["argv"])
    if (
        not argv
        or type(row["actual_rc"]) is not int
        or type(row["expected_rc"]) is not int
    ):
        _reject("normative command argv or exit status is invalid")
    return CommandExpectation(
        _strings([row["control_id"]])[0],
        tuple(argv),
        _absolute(row["cwd"]),
        int(row["actual_rc"]),
        int(row["expected_rc"]),
    )


def load_command_plan(
    expected: BoundInput, *, execution: Literal["fresh", "historical"]
) -> CommandPlan:
    """Compile a caller-pinned independent plan; malformed plans raise ValueError.

    A compiled plan retains its authoritative bytes. ``read_commands`` rechecks
    that binding rather than trusting mutable projections or receipt counts.
    """
    planned, _ids, roots, _bindings, start, deadline = _command_plan(
        expected, execution
    )
    actor = _object(_authority(expected)["actor"])
    return CommandPlan(
        expected,
        execution,
        tuple(_command_expectation(row) for row in planned),
        tuple(_absolute(root) for root in roots),
        tuple((key, str(value)) for key, value in actor.items()),
        (start, deadline),
    )


def _plan_input(
    expected: BoundInput | CommandPlan, execution: Literal["fresh", "historical"]
) -> BoundInput:
    if isinstance(expected, CommandPlan):
        if expected.execution != execution:
            _reject("compiled plan execution role differs")
        expected = expected.authority
    load_command_plan(expected, execution=execution)
    return expected


def read_commands(
    receipt_paths: list[Path],
    expected: BoundInput | CommandPlan,
    *,
    execution: Literal["fresh", "historical"],
) -> ReadResult:
    """Reconcile exact command IDs, argv, actor, bindings, window, logs and roots.

    The normative input contains ``commands`` (control_id/argv/cwd/actual_rc/
    expected_rc), explicit command_count/root_count/fixture_git_roots, the four
    native ``actor`` keys, ``bindings``, and an execution window
    issued_at/outer_deadline_utc. The generic bindings require equal, nonempty
    before/after source mappings; capture/spec/START hashes are also checked
    when the caller's normative input requires them. C1's stronger contract is
    separate. Every receipt is read from its own control directory. Both fresh
    and historical observations must match the plan's actual_rc and expected_rc
    independently; those two values may differ. ALLOW reports matching evidence,
    not a successful command or completed proof.
    The caller must independently enumerate the complete command plan; an output
    count, glob, or receipt-derived list is never a normative input.
    """
    try:
        expected = _plan_input(expected, execution)
        planned, ids, roots, bindings, start, deadline = _command_plan(
            expected, execution
        )
        records: list[dict[str, object]] = []
        actual_roots: set[str] = set()
        for path in receipt_paths:
            if (
                not isinstance(path, Path)
                or not path.is_absolute()
                or path.resolve() == expected.path.resolve()
            ):
                _reject("receipt must have a separate typed absolute path")
            record = _object(codec.decode(path.read_bytes(), dict))
            control = record["control_id"]
            if (
                not isinstance(control, str)
                or path.parent.name != control
                or control not in ids
            ):
                _reject("unexpected command or control directory")
            plan = planned[ids.index(control)]
            if root := _validate_command(
                record, plan, path, bindings, (start, deadline)
            ):
                actual_roots.add(root)
            records.append(record)
        actual_ids = [row["control_id"] for row in records]
        if len(actual_ids) != len(set(actual_ids)) or set(actual_ids) != set(ids):
            _reject("actual command membership differs or is duplicated")
        if actual_roots != set(roots):
            _reject("actual Git root membership differs")
        return ReadResult("ALLOW", len(records))
    except (ValueError, UnicodeError, KeyError, TypeError) as error:
        return _deny(error)
    except OSError as error:
        return ReadResult("DENY", reasons=(str(error),))


def read_representation(
    transport: bytes,
    decoded_content: object,
    baseline: BoundInput,
    *,
    extra_lf: Literal[0, 1],
    required: bool = True,
) -> ReadResult:
    """Compare exact UTF8 transport and decoded text with the declared 0/1 LF.

    ``baseline`` binds the sealed UTF8 text, not an enclosing JSON serialization.
    Native text content may be a string or text/output_text blocks. Missing
    encrypted/internal
    decoded content stays PENDING when optional and DENY when required; a parent
    paraphrase cannot replace genuine text. No trim or newline normalization runs.
    """
    try:
        if (
            baseline.role != "baseline"
            or hashlib.sha256(baseline.content).hexdigest() != baseline.sha256
        ):
            _reject("transport baseline role or binding differs")
        text = baseline.content.decode("utf-8")
        transport.decode("utf-8")
        if type(extra_lf) is not int or extra_lf not in {0, 1}:
            _reject("transport declaration must be zero or one LF")
        if transport != baseline.content + (b"\n" if extra_lf else b""):
            _reject("literal UTF8 transport differs from its declaration")
        if decoded_content is None:
            return ReadResult(
                "DENY" if required else "PENDING",
                reasons=("decoded content unavailable",),
            )
        if isinstance(decoded_content, str):
            decoded = decoded_content
        else:
            blocks = [_object(block) for block in _list(decoded_content)]
            if not blocks or any(
                block.get("type") not in {"text", "output_text"}
                or not isinstance(block.get("text"), str)
                for block in blocks
            ):
                _reject("native decoded text blocks are invalid")
            decoded = "".join(str(block["text"]) for block in blocks)
        if decoded != text:
            _reject("decoded content differs from independently sealed text")
        return ReadResult("ALLOW", 1)
    except (ValueError, UnicodeError, KeyError, TypeError) as error:
        return _deny(error)


def read_cache_transition(
    observed: object,
    baseline: BoundInput,
    *,
    mode: Literal["rebuild", "reuse"],
) -> ReadResult:
    """Apply distinct native rebuild/reuse contracts to cache snapshots.

    Reuse requires complete cache equality (including pointer identity/mtime).
    Rebuild requires equal counts and the six retained source-binding fields.
    This does not prove the separate object/manifest files exist or match their
    hashes: compose ``read_references`` over an independent artifact manifest.
    """
    try:
        before, after = _authority(baseline, role="baseline"), _object(observed)
        a, b = _object(before["cache"]), _object(after["cache"])
        if before["counts"] != after["counts"]:
            _reject("cache public counts differ")
        if mode == "reuse":
            if a != b:
                _reject("reuse requires exact cache equality")
        elif mode == "rebuild":
            sources_a, sources_b = _object(a["sources"]), _object(b["sources"])
            if not sources_a or set(sources_a) != set(sources_b):
                _reject("rebuild source membership differs")
            fields = (
                "source_key",
                "prefix_sha256",
                "byte_count",
                "line_count",
                "parser_fingerprint",
                "policy_fingerprint",
            )
            for source, row in sources_a.items():
                old = _object(_object(row)["source_binding"])
                new = _object(_object(sources_b[source])["source_binding"])
                if any(old[field] != new[field] for field in fields):
                    _reject("rebuild stable source binding differs")
        else:
            _reject("unknown cache transition")
        return ReadResult("ALLOW", len(_object(b["sources"])))
    except (ValueError, UnicodeError, KeyError, TypeError) as error:
        return _deny(error)


def _reference_present(
    path: Path, reference: dict[str, object], *, listed: bool
) -> bool:
    if type(reference["required"]) is not bool:
        _reject("reference requirement is not boolean")
    if listed and path.is_file():
        return True
    if reference["required"]:
        _reject("required proof reference is absent")
    return False


def read_references(observed: object, expected: BoundInput) -> ReadResult:
    """Hash only explicit absolute original paths in independently required refs.

    Normative ``references`` rows contain path/sha256/required. Native manifest
    rows identify originals with ``absolute_path`` (or an absolute ``path``).
    Descriptive provenance labels are never traversed. An optional future path
    absent from the manifest OR disk yields PENDING; a required absent reference
    or artifact yields DENY. All present originals must match the independent
    binding as well as the observed hash. Unknown/duplicate references deny.
    An independently authorized empty reference domain allows count0, proving
    only that explicit empty scope.
    """
    try:
        required = [_object(row) for row in _list(_authority(expected)["references"])]
        paths = [str(_absolute(row["path"])) for row in required]
        if len(paths) != len(set(paths)):
            _reject("duplicate normative reference")
        rows = [_object(row) for row in _list(observed)]
        names = [
            str(_absolute(row.get("absolute_path", row.get("path")))) for row in rows
        ]
        if len(names) != len(set(names)) or not set(names) <= set(paths):
            _reject("unknown or duplicate observed reference")
        pending = False
        for name, reference in zip(paths, required, strict=True):
            path = Path(name)
            if not _reference_present(path, reference, listed=name in names):
                pending = True
                continue
            row = rows[names.index(name)]
            if path.resolve() == expected.path.resolve():
                _reject("checked reference cannot be its own normative input")
            if (
                row["sha256"] != reference["sha256"]
                or hashlib.sha256(path.read_bytes()).hexdigest() != reference["sha256"]
            ):
                _reject("proof reference byte binding differs")
        return ReadResult("PENDING" if pending else "ALLOW", len(rows))
    except (ValueError, UnicodeError, KeyError, TypeError) as error:
        return _deny(error)
    except OSError as error:
        return ReadResult("DENY", reasons=(str(error),))


def read_issue_plan(observed: object, expected: BoundInput) -> ReadResult:
    """Require independently planned intentions and exact member/source refs.

    The expected ``intentions`` define stable_key/member_session_ids/source_refs
    and any additional normative fields. Native descriptive body/title text is
    accepted without promoting it to command execution or a filesystem path.
    An independently authorized empty intention domain allows count0; this does
    not establish completeness beyond that explicit empty scope.
    """
    try:
        plans = [_object(row) for row in _list(_authority(expected)["intentions"])]
        rows = [_object(row) for row in _list(_object(observed)["intentions"])]
        keys = _strings([row["stable_key"] for row in rows])
        planned_keys = _strings([row["stable_key"] for row in plans])
        if (
            len(keys) != len(set(keys))
            or len(planned_keys) != len(set(planned_keys))
            or set(keys) != set(planned_keys)
        ):
            _reject("issue-plan intention membership differs or is duplicated")
        for key, plan in zip(planned_keys, plans, strict=True):
            row = rows[keys.index(key)]
            for field in ["member_session_ids", "source_refs"]:
                values = _strings(plan[field])
                if len(values) != len(set(values)):
                    _reject("duplicate normative issue-plan reference")
                if field == "source_refs":
                    for value in values:
                        _absolute(value)
            if any(row.get(field) != value for field, value in plan.items()):
                _reject("issue-plan member, source or normative field differs")
        return ReadResult("ALLOW", len(rows))
    except (ValueError, UnicodeError, KeyError, TypeError) as error:
        return _deny(error)
