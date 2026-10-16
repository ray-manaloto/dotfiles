# Copyright (c) 2026 Raymond Manaloto
"""Portable proof-consumer controls with independently pinned normative inputs."""

from __future__ import annotations

import copy
import hashlib
import sys
from pathlib import Path
from typing import Literal

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python/src"))

from dotfiles_setup import codec, proof_reader

FIXTURES = Path(__file__).parent / "fixtures/proof_reader"


@pytest.mark.parametrize(
    "collection",
    [
        (
            "<Dir example>\n  <Dir tests>\n    <Dir nested>\n"
            "      <Module test_example.py>\n        <Function test_literal[café]>\n"
            "        <Function test_other>\n"
        ),
        (
            "<Dir example>\n  <Dir tests>\n    <Package nested>\n"
            "      <Module test_example.py>\n        <Function test_literal[café]>\n"
            "        <Function test_other>\n"
        ),
        (
            "<Dir example>\n  <Dir other>\n    <Module test_example.py>\n"
            "      <Function test_literal[café]>\n      <Function test_other>\n"
        ),
        (
            "<Dir example>\n  <Dir tests>\n    <Module test_example.py>\n"
            "  <Function test_literal[café]>\n  <Function test_other>\n"
        ),
        (
            "<Dir example>\n  <Dir tests>\n    <Module test_example.py>\n"
            "      <Function test_literal[café]>\n<Function test_other>\n"
        ),
        (
            "<Dir example>\n  <Dir tests>\n    <Module test_example.py>\n"
            "      <Function test_literal[café]>\n===== end =====\n"
            "      <Function test_other>\n"
        ),
        (
            "<Dir example>\n  <Dir tests>\n    <Module test_example.py>\n"
            "      <Function test_literal[café]>\n    <Dir outside>\n"
            "      <Function test_other>\n"
        ),
        (
            "<Dir example>\n  <Dir tests>\n    <Module nested/test_example.py>\n"
            "      <Function test_literal[café]>\n      <Function test_other>\n"
        ),
        (
            "<Dir example>\n  <Dir tests>\n    <Module test_example.py>\n"
            "      <Function test_literal[café]> junk\n      <Function test_other>\n"
        ),
        (
            "<Dir example>\n  <Dir tests>\n    <Module test_example.py>\n"
            "      <Class TestOther>\n      <Function test_literal[café]>\n"
            "      <Function test_other>\n"
        ),
        (
            "    <Module test_example.py>\n      <Function test_literal[café]>\n"
            "      <Function test_other>\n"
        ),
    ],
)
def test_collection_hierarchy_cannot_acquire_a_flat_modules_identity(
    collection: str,
) -> None:
    authority = FIXTURES / "collection-oracle.json"
    expected = proof_reader.bind_input(
        authority, hashlib.sha256(authority.read_bytes()).hexdigest(), role="normative"
    )
    assert proof_reader.read_collection(collection.encode(), expected).status == "DENY"
    assert (
        proof_reader.read_collection(
            (FIXTURES / "collection.txt").read_bytes(), expected
        ).status
        == "ALLOW"
    )


def test_collection_accepts_native_module_function_shape() -> None:
    """An authoritative node manifest independently admits native collections."""
    authority = FIXTURES / "collection-oracle.json"
    expectation = proof_reader.bind_input(
        authority, hashlib.sha256(authority.read_bytes()).hexdigest(), role="normative"
    )
    result = proof_reader.read_collection(
        (FIXTURES / "collection.txt").read_bytes(), expectation
    )
    assert result.status == "ALLOW"
    assert result.count == 2


@pytest.mark.parametrize(
    ("container", "status"),
    [
        ("  <Package tests>", "ALLOW"),
        ("  <Package other>", "DENY"),
        (" <Dir tests>", "DENY"),
        ("\t<Dir tests>", "DENY"),
    ],
)
def test_collection_tests_container_requires_its_canonical_scope(
    container: str,
    status: str,
) -> None:
    authority = FIXTURES / "collection-oracle.json"
    expected = proof_reader.bind_input(
        authority, hashlib.sha256(authority.read_bytes()).hexdigest(), role="normative"
    )
    raw = (FIXTURES / "collection.txt").read_bytes()
    observed = raw.replace(b"  <Dir tests>", container.encode())
    assert observed != raw
    assert proof_reader.read_collection(observed, expected).status == status


def test_global_groups_preserve_complete_objects(tmp_path: Path) -> None:
    """The public eight-axis group object is compared without scalar flattening."""
    groups = [
        {"mode": mode, "source": source, "selected_repositories": count}
        for mode in ["--issue-plan", "--json"]
        for source in ["inbox", "plan"]
        for count in [1, 2]
    ]
    expected = bound(tmp_path, "groups.json", {"global_groups": groups})
    assert proof_reader.read_global_groups(groups, expected).status == "ALLOW"
    assert proof_reader.read_global_groups(groups[:-1], expected).status == "DENY"
    assert (
        proof_reader.read_global_groups([*groups, groups[0]], expected).status == "DENY"
    )


def bound(
    tmp_path: Path,
    name: str,
    payload: object,
    *,
    role: proof_reader.InputRole = "normative",
) -> proof_reader.BoundInput:
    """Import only an independent normative or independently retained baseline input."""
    path = tmp_path / name
    path.write_bytes(codec.encode(payload))
    return proof_reader.bind_input(
        path, hashlib.sha256(path.read_bytes()).hexdigest(), role=role
    )


def command_packet(tmp_path: Path) -> tuple[proof_reader.BoundInput, Path]:
    """A real receipt file cannot shrink the separately bound command membership."""
    actor = {
        "agent_id": "worker-1",
        "agent_role": "python",
        "agent_path": "/root/python",
        "parent_id": "caller-1",
    }
    recipe = {
        "commands": [
            {
                "control_id": "git-init",
                "argv": ["git", "-C", str(tmp_path / "fixture"), "init"],
                "cwd": str(tmp_path),
                "actual_rc": 0,
                "expected_rc": 0,
            }
        ],
        "command_count": 1,
        "fixture_git_roots": [str(tmp_path / "fixture")],
        "root_count": 1,
        "actor": actor,
        "bindings": {
            "source_hashes_before": {"source.py": "a" * 64},
            "source_hashes_after": {"source.py": "a" * 64},
        },
        "execution": "fresh",
        "issued_at": "2026-10-12T00:00:00Z",
        "outer_deadline_utc": "2026-10-12T01:00:00Z",
    }
    authority = bound(tmp_path, "command-plan.json", recipe)
    directory = tmp_path / "commands/git-init"
    directory.mkdir(parents=True)
    (directory / "stdout.log").write_bytes(b"initialized\n")
    (directory / "stderr.log").write_bytes(b"")
    receipt = {
        "control_id": "git-init",
        "argv": ["git", "-C", str(tmp_path / "fixture"), "init"],
        "cwd": str(tmp_path),
        "actual_rc": 0,
        "expected_rc": 0,
        **actor,
        "source_hashes_before": {"source.py": "a" * 64},
        "source_hashes_after": {"source.py": "a" * 64},
        "fixture_git": True,
        "timed_out": False,
        "cleanup": {"quiescent": True},
        "timeout_s": 120,
        "elapsed_s": 1,
        "launched_at": "2026-10-12T00:01:00Z",
        "completed_at": "2026-10-12T00:01:01Z",
        "stdout_sha256": hashlib.sha256(b"initialized\n").hexdigest(),
        "stderr_sha256": hashlib.sha256(b"").hexdigest(),
    }
    path = directory / "receipt.json"
    path.write_bytes(codec.encode(receipt))
    return authority, path


def test_commands_accept_exact_independent_ids_and_native_receipt_shape(
    tmp_path: Path,
) -> None:
    """A real receipt file cannot shrink the separately bound command membership."""
    authority, path = command_packet(tmp_path)
    assert (
        proof_reader.read_commands([path], authority, execution="fresh").status
        == "ALLOW"
    )
    assert proof_reader.read_commands([], authority, execution="fresh").status == "DENY"


def test_transport_preserves_literal_declared_lf_and_decoded_blocks(
    tmp_path: Path,
) -> None:
    """The independent sealed text cannot be normalized at transport boundaries."""
    path = tmp_path / "ack.txt"
    path.write_bytes("ACK café".encode())
    baseline = proof_reader.bind_input(
        path, hashlib.sha256(path.read_bytes()).hexdigest(), role="baseline"
    )
    blocks = [{"type": "text", "text": "ACK café"}]
    assert (
        proof_reader.read_representation(
            b"ACK \x63\x61\x66\xc3\xa9", blocks, baseline, extra_lf=0
        ).status
        == "ALLOW"
    )
    assert (
        proof_reader.read_representation(
            b"ACK \x63\x61\x66\xc3\xa9\n", blocks, baseline, extra_lf=1
        ).status
        == "ALLOW"
    )
    assert (
        proof_reader.read_representation(
            b"ACK \x63\x61\x66\xc3\xa9\n", blocks, baseline, extra_lf=0
        ).status
        == "DENY"
    )


def test_cache_rebuild_and_reuse_have_distinct_contracts(tmp_path: Path) -> None:
    """Rebuilt pointers may change while reused complete caches must remain exact."""
    source = {
        "source_binding": {
            "source_key": "key",
            "prefix_sha256": "hash",
            "byte_count": 2,
            "line_count": 1,
            "parser_fingerprint": "parser",
            "policy_fingerprint": "policy",
        },
        "pointer_sha256": "old",
    }
    baseline_value = {
        "counts": {"attempted": 1},
        "cache": {"sources": {"root": source}},
    }
    baseline = bound(tmp_path, "cache-before.json", baseline_value, role="baseline")
    replacement = copy.deepcopy(source)
    replacement["pointer_sha256"] = "new"
    rebuilt = {"counts": {"attempted": 1}, "cache": {"sources": {"root": replacement}}}
    assert (
        proof_reader.read_cache_transition(
            baseline_value, baseline, mode="reuse"
        ).status
        == "ALLOW"
    )
    assert (
        proof_reader.read_cache_transition(rebuilt, baseline, mode="rebuild").status
        == "ALLOW"
    )
    assert (
        proof_reader.read_cache_transition(rebuilt, baseline, mode="reuse").status
        == "DENY"
    )


def test_references_distinguish_optional_precreation_from_required_proof(
    tmp_path: Path,
) -> None:
    """Missing future outputs remain pending; missing required receipts deny."""
    future = tmp_path / "not-created.json"
    optional = bound(
        tmp_path,
        "optional.json",
        {"references": [{"path": str(future), "sha256": "a" * 64, "required": False}]},
    )
    required = bound(
        tmp_path,
        "required.json",
        {"references": [{"path": str(future), "sha256": "a" * 64, "required": True}]},
    )
    assert proof_reader.read_references([], optional).status == "PENDING"
    assert proof_reader.read_references([], required).status == "DENY"
    path = tmp_path / "proof.txt"
    path.write_bytes(b"sealed")
    digest = hashlib.sha256(b"sealed").hexdigest()
    expected = bound(
        tmp_path,
        "proof-plan.json",
        {"references": [{"path": str(path), "sha256": digest, "required": True}]},
    )
    observed = [{"absolute_path": str(path), "sha256": digest}]
    assert proof_reader.read_references(observed, expected).status == "ALLOW"
    path.write_bytes(b"stale!")
    assert proof_reader.read_references(observed, expected).status == "DENY"


def test_issue_plan_keeps_exact_typed_source_references(tmp_path: Path) -> None:
    """Issue intention membership and source refs come from an independent plan."""
    intent = {
        "stable_key": "lane:one",
        "member_session_ids": ["claude:one"],
        "source_refs": [str(tmp_path / "task_plan.md")],
    }
    expected = bound(tmp_path, "issue-plan.json", {"intentions": [intent]})
    assert (
        proof_reader.read_issue_plan({"intentions": [intent]}, expected).status
        == "ALLOW"
    )
    assert (
        proof_reader.read_issue_plan(
            {"intentions": [{**intent, "source_refs": []}]}, expected
        ).status
        == "DENY"
    )


@pytest.mark.parametrize(
    "variant",
    [
        "duplicate",
        "wrong-actor",
        "historical",
        "argv",
        "narration",
        "bad-rc",
        "stale-log",
        "malformed",
    ],
)
def test_hostile_command_receipts_deny(tmp_path: Path, variant: str) -> None:
    """Changing an observation cannot edit the independently pinned plan."""
    authority, path = command_packet(tmp_path)
    receipt = codec.decode(path.read_bytes(), dict)
    paths = [path]
    if variant == "duplicate":
        paths.append(path)
    elif variant == "wrong-actor":
        receipt["agent_id"] = "other-agent"
    elif variant == "historical":
        receipt["launched_at"] = "2026-10-11T00:00:00Z"
    elif variant == "argv":
        receipt["argv"] = ["echo", "git init"]
    elif variant == "narration":
        receipt.pop("argv")
        receipt["description"] = "I executed git init"
    elif variant == "bad-rc":
        receipt["actual_rc"] = False
    elif variant == "stale-log":
        (path.parent / "stdout.log").write_bytes(b"new bytes")
    else:
        receipt["cleanup"] = []
    path.write_bytes(codec.encode(receipt))
    assert (
        proof_reader.read_commands(paths, authority, execution="fresh").status == "DENY"
    )


@pytest.mark.parametrize(
    "variant", ["omit", "duplicate", "unknown", "context", "invalid-utf8"]
)
def test_hostile_collection_copies_cannot_shrink_normative_membership(
    variant: str,
) -> None:
    """A retained node list remains the oracle when raw collection bytes change."""
    authority = FIXTURES / "collection-oracle.json"
    expected = proof_reader.bind_input(
        authority, hashlib.sha256(authority.read_bytes()).hexdigest(), role="normative"
    )
    raw = (FIXTURES / "collection.txt").read_bytes()
    if variant == "omit":
        raw = raw.replace(b"      <Function test_other>\n", b"")
    elif variant == "duplicate":
        raw += b"<Function test_other>\n"
    elif variant == "unknown":
        raw += b"<Mystery opaque>\n"
    elif variant == "context":
        raw = raw.replace(b"    <Module test_example.py>\n", b"")
    else:
        raw += b"\xff"
    assert proof_reader.read_collection(raw, expected).status == "DENY"


@pytest.mark.parametrize(
    "variant",
    [
        "double-lf",
        "crlf",
        "json-transport",
        "decoded-prose",
        "encrypted-required",
        "encrypted-optional",
    ],
)
def test_hostile_transport_representation(tmp_path: Path, variant: str) -> None:
    """Each byte representation is literal; unavailable decoded content is typed."""
    path = tmp_path / "native-ack.txt"
    path.write_bytes(b"ACK")
    baseline = proof_reader.bind_input(
        path, hashlib.sha256(b"ACK").hexdigest(), role="baseline"
    )
    transport, decoded = b"ACK", "ACK"
    if variant == "double-lf":
        transport = b"ACK\n\n"
    elif variant == "crlf":
        transport = b"ACK\r\n"
    elif variant == "json-transport":
        transport = codec.encode([{"type": "text", "text": "ACK"}])
    elif variant == "decoded-prose":
        decoded = "The child acknowledged."
    else:
        decoded = None
    result = proof_reader.read_representation(
        transport,
        decoded,
        baseline,
        extra_lf=0,
        required=variant != "encrypted-optional",
    )
    assert result.status == ("PENDING" if variant == "encrypted-optional" else "DENY")


def test_baseline_does_not_supply_normative_coverage(tmp_path: Path) -> None:
    """Explicit fixture imports retain their independently assigned oracle role."""
    baseline = bound(
        tmp_path,
        "untrusted-baseline.json",
        {"nodes": [], "family_counts": {}},
        role="baseline",
    )
    assert proof_reader.read_collection(b"", baseline).status == "DENY"


def test_authority_changed_bytes_refuse_rebinding(tmp_path: Path) -> None:
    """The caller's pinned hash cannot silently advance with a changed source."""
    path = tmp_path / "normative.json"
    path.write_bytes(b"{}")
    pinned = hashlib.sha256(b"{}").hexdigest()
    path.write_bytes(b"[]")
    with pytest.raises(ValueError, match="byte binding"):
        proof_reader.bind_input(path, pinned, role="normative")


def test_normative_37_roots_and_305_commands_cannot_shrink_with_outputs(
    tmp_path: Path,
) -> None:
    """The independent control recipe binds coverage before captured output exists."""
    authority, _single = command_packet(tmp_path)
    base = codec.decode(authority.content, dict)
    recipe = codec.decode((FIXTURES / "coverage-recipe.json").read_bytes(), dict)
    roots = [str(tmp_path / "fixtures" / label) for label in recipe["roots"]]
    planned = [
        {
            "control_id": f"root-{index}-{action}",
            "argv": ["git", "-C", root, action],
            "cwd": str(tmp_path),
            "actual_rc": 0,
            "expected_rc": 0,
        }
        for index, root in enumerate(roots)
        for action in recipe["git_actions"]
    ]
    planned.extend(
        {
            "control_id": f"public-{index}",
            "argv": ["dotfiles-setup", "synthetic-control", str(index)],
            "cwd": str(tmp_path),
            "actual_rc": 0,
            "expected_rc": 0,
        }
        for index in range(recipe["supplemental_commands"])
    )
    normative = bound(
        tmp_path,
        "complete-command-plan.json",
        {
            **base,
            "commands": planned,
            "fixture_git_roots": roots,
            "command_count": recipe["command_count"],
            "root_count": recipe["root_count"],
        },
    )
    # Observations are independently generated synthetic capture records. The
    # oracle is bound above, never derived by counting or collecting these files.
    template = codec.decode(_single.read_bytes(), dict)
    paths = []
    captured: list[tuple[str, list[str]]] = [
        (f"root-{index}-{action}", ["git", "-C", root, action])
        for index, root in enumerate(roots)
        for action in [
            "init",
            "rev-parse",
            "hook-pre-commit",
            "hook-pre-push",
            "hook-post-commit",
            "config",
            "commit",
        ]
    ]
    captured.extend(
        (f"public-{index}", ["dotfiles-setup", "synthetic-control", str(index)])
        for index in range(46)
    )
    for control, argv in captured:
        directory = tmp_path / "captured" / control
        directory.mkdir(parents=True)
        (directory / "stdout.log").write_bytes(b"initialized\n")
        (directory / "stderr.log").write_bytes(b"")
        record = {
            **template,
            "control_id": control,
            "argv": argv,
            "fixture_git": argv[0] == "git",
        }
        path = directory / "receipt.json"
        path.write_bytes(codec.encode(record))
        paths.append(path)
    result = proof_reader.read_commands(paths, normative, execution="fresh")
    assert result.status == "ALLOW"
    assert result.count == 305
    assert (
        proof_reader.read_commands(paths[1:], normative, execution="fresh").status
        == "DENY"
    )
    assert (
        proof_reader.read_commands(
            [*paths, paths[0]], normative, execution="fresh"
        ).status
        == "DENY"
    )
    without_root = [
        path for path in paths if not path.parent.name.startswith("root-0-")
    ]
    assert (
        proof_reader.read_commands(without_root, normative, execution="fresh").status
        == "DENY"
    )


def test_reference_labels_are_not_paths_or_execution(tmp_path: Path) -> None:
    """Narrative metadata may remain present without becoming a hashed path."""
    path = tmp_path / "actual-proof.txt"
    path.write_bytes(b"proof")
    digest = hashlib.sha256(b"proof").hexdigest()
    expected = bound(
        tmp_path,
        "typed-paths.json",
        {"references": [{"path": str(path), "sha256": digest, "required": True}]},
    )
    record = {
        "absolute_path": str(path),
        "sha256": digest,
        "provenance": "historical packet; do not execute git init",
    }
    assert proof_reader.read_references([record], expected).status == "ALLOW"
    assert (
        proof_reader.read_references(
            [{**record, "absolute_path": "historical packet"}], expected
        ).status
        == "DENY"
    )


def test_historical_commands_require_explicit_historical_plan(tmp_path: Path) -> None:
    """Historical execution is accepted under its own independently pinned window."""
    authority, path = command_packet(tmp_path)
    historical = codec.decode(authority.content, dict)
    historical["execution"] = "historical"
    expected = bound(tmp_path, "historical-plan.json", historical)
    assert (
        proof_reader.read_commands([path], expected, execution="historical").status
        == "ALLOW"
    )
    assert (
        proof_reader.read_commands([path], expected, execution="fresh").status == "DENY"
    )


def test_empty_command_argv_denies_without_crashing(tmp_path: Path) -> None:
    """A malformed command remains a denial, never an unhandled reader failure."""
    authority, path = command_packet(tmp_path)
    plan = codec.decode(authority.content, dict)
    plan["commands"][0]["argv"] = []
    expected = bound(tmp_path, "bad-argv-plan.json", plan)
    receipt = codec.decode(path.read_bytes(), dict)
    receipt["argv"] = []
    path.write_bytes(codec.encode(receipt))
    assert (
        proof_reader.read_commands([path], expected, execution="fresh").status == "DENY"
    )


def test_caller_can_compile_a_typed_independent_command_plan(tmp_path: Path) -> None:
    """The plan handle exposes typed argv, actor, roots and window before reads."""
    authority, path = command_packet(tmp_path)
    plan = proof_reader.load_command_plan(authority, execution="fresh")
    assert plan.command_ids == ("git-init",)
    assert plan.fixture_git_roots == (tmp_path / "fixture",)
    assert plan.commands[0].argv == ("git", "-C", str(tmp_path / "fixture"), "init")
    assert dict(plan.actor)["agent_id"] == "worker-1"
    assert proof_reader.read_commands([path], plan, execution="fresh").status == "ALLOW"


@pytest.mark.parametrize("shape", [{}, {"commands": [{}]}, {"commands": None}, []])
def test_malformed_bound_command_plan_keeps_public_value_error_contract(
    tmp_path: Path,
    shape: object,
) -> None:
    path = tmp_path / "malformed-plan.json"
    raw = codec.encode(shape)
    path.write_bytes(raw)
    expected = proof_reader.bind_input(
        path, hashlib.sha256(raw).hexdigest(), role="normative"
    )
    with pytest.raises(
        ValueError,
        match=r"malformed normative command plan|expected a list|Expected `object`",
    ):
        proof_reader.load_command_plan(expected, execution="fresh")
    authority, receipt = command_packet(tmp_path)
    compiled = proof_reader.load_command_plan(authority, execution="fresh")
    assert (
        proof_reader.read_commands([receipt], compiled, execution="fresh").status
        == "ALLOW"
    )


@pytest.mark.parametrize("kind", ["text", "output_text"])
def test_native_decoded_text_block_forms(tmp_path: Path, kind: str) -> None:
    """Claude tool text and Codex assistant output_text retain their literal text."""
    path = tmp_path / "sealed-output.txt"
    path.write_bytes(b"ACK")
    baseline = proof_reader.bind_input(
        path, hashlib.sha256(b"ACK").hexdigest(), role="baseline"
    )
    assert (
        proof_reader.read_representation(
            b"ACK", [{"type": kind, "text": "ACK"}], baseline, extra_lf=0
        ).status
        == "ALLOW"
    )


@pytest.mark.parametrize(
    "field",
    [
        "source_key",
        "prefix_sha256",
        "byte_count",
        "line_count",
        "parser_fingerprint",
        "policy_fingerprint",
    ],
)
def test_rebuild_refuses_changed_stable_source_binding(
    tmp_path: Path, field: str
) -> None:
    """Every native rebuild binding field remains tied to its own baseline."""
    binding = {
        "source_key": "key",
        "prefix_sha256": "hash",
        "byte_count": 2,
        "line_count": 1,
        "parser_fingerprint": "parser",
        "policy_fingerprint": "policy",
    }
    baseline_value = {
        "counts": {"attempted": 1},
        "cache": {"sources": {"root": {"source_binding": binding}}},
    }
    baseline = bound(tmp_path, "cache-baseline.json", baseline_value, role="baseline")
    changed = {**binding, field: "changed"}
    observed = {
        "counts": {"attempted": 1},
        "cache": {"sources": {"root": {"source_binding": changed}}},
    }
    assert (
        proof_reader.read_cache_transition(observed, baseline, mode="rebuild").status
        == "DENY"
    )


def test_listed_missing_references_preserve_optional_pending(tmp_path: Path) -> None:
    """A manifest row does not make an absent optional artifact required."""
    missing = tmp_path / "missing-proof.txt"
    row = {"path": str(missing), "sha256": hashlib.sha256(b"proof").hexdigest()}
    optional = bound(
        tmp_path, "optional.json", {"references": [{**row, "required": False}]}
    )
    required = bound(
        tmp_path, "required.json", {"references": [{**row, "required": True}]}
    )
    assert proof_reader.read_references([row], optional).status == "PENDING"
    assert proof_reader.read_references([row], required).status == "DENY"
    missing.write_bytes(b"proof")
    assert proof_reader.read_references([row], required).status == "ALLOW"


def test_empty_domains_allow_only_independently_declared_empty_scope(
    tmp_path: Path,
) -> None:
    """Empty outputs cannot erase a nonempty reference or issue authority."""
    empty_refs = bound(tmp_path, "empty-refs.json", {"references": []})
    empty_issues = bound(tmp_path, "empty-issues.json", {"intentions": []})
    reference = {
        "path": str(tmp_path / "proof.txt"),
        "sha256": "a" * 64,
        "required": True,
    }
    refs = bound(tmp_path, "refs.json", {"references": [reference]})
    intention = {"stable_key": "required", "member_session_ids": [], "source_refs": []}
    issues = bound(tmp_path, "issues.json", {"intentions": [intention]})
    result = proof_reader.read_references([], empty_refs)
    assert (result.status, result.count) == ("ALLOW", 0)
    result = proof_reader.read_issue_plan({"intentions": []}, empty_issues)
    assert (result.status, result.count) == ("ALLOW", 0)
    assert proof_reader.read_references([], refs).status == "DENY"
    assert proof_reader.read_issue_plan({"intentions": []}, issues).status == "DENY"


@pytest.mark.parametrize("malformed", [b"{", b"\xff"])
def test_exactly_bound_malformed_serialization_denies_at_public_readers(
    tmp_path: Path, malformed: bytes
) -> None:
    """Malformed bytes reach decoding with their own hash and become DENY."""
    authority, receipt = command_packet(tmp_path)
    assert (
        proof_reader.read_commands([receipt], authority, execution="fresh").status
        == "ALLOW"
    )
    valid_refs = bound(tmp_path, "refs.json", {"references": []})
    assert proof_reader.read_references([], valid_refs).status == "ALLOW"
    path = tmp_path / "malformed.json"
    path.write_bytes(malformed)
    malformed_authority = proof_reader.bind_input(
        path, hashlib.sha256(malformed).hexdigest(), role="normative"
    )
    assert malformed_authority.content == malformed
    assert (
        proof_reader.read_commands(
            [receipt], malformed_authority, execution="fresh"
        ).status
        == "DENY"
    )
    assert proof_reader.read_references([], malformed_authority).status == "DENY"
    receipt.write_bytes(malformed)
    assert (
        proof_reader.read_commands([receipt], authority, execution="fresh").status
        == "DENY"
    )


@pytest.mark.parametrize("execution", ["fresh", "historical"])
def test_command_matching_does_not_promote_actual_failure_to_success(
    tmp_path: Path, execution: Literal["fresh", "historical"]
) -> None:
    """The independent plan binds both rc fields; ALLOW reports matching evidence."""
    authority, receipt = command_packet(tmp_path)
    recipe = codec.decode(authority.content, dict)
    recipe["commands"][0]["actual_rc"] = 1
    recipe["execution"] = execution
    expected = bound(tmp_path, "failed-command-plan.json", recipe)
    assert (
        proof_reader.read_commands([receipt], expected, execution=execution).status
        == "DENY"
    )
    observation = codec.decode(receipt.read_bytes(), dict)
    observation["actual_rc"] = 1
    receipt.write_bytes(codec.encode(observation))
    assert (
        proof_reader.read_commands([receipt], expected, execution=execution).status
        == "ALLOW"
    )
