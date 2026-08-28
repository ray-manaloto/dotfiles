# Copyright (c) 2026 Raymond Manaloto
"""Public contracts for the issue #766 takeover and admission records."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from jsonschema import Draft202012Validator, ValidationError

if TYPE_CHECKING:
    from jsonschema.protocols import Validator

ROOT = Path(__file__).parent.parent
STATUS_SCHEMA = ROOT / "docs/specs/orchestration-status.v1.schema.json"
ADMISSION_SCHEMA = ROOT / "docs/specs/orchestration-admission.v1.schema.json"
TAKEOVER = ROOT / "docs/specs/orchestration-takeover.v1.json"
SKILL = ROOT / ".agents/skills/codex-task-orchestration/SKILL.md"


def _validator(path: Path) -> Validator:
    schema = json.loads(path.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def _admission(*, decision: str, heavy_available: bool) -> dict[str, object]:
    admission: dict[str, object] = {
        "schema_version": "dotfiles.orchestration-admission.v1",
        "decision_rule": "dotfiles.shared-resource-fit.v1",
        "request_id": "docker-amd64-gate",
        "repository_id": "ray-manaloto/dotfiles",
        "git_common_dir": "/repo/.git",
        "resource_class": "shared_docker",
        "architectures": ["amd64"],
        "capacity": {
            "cpu_weight": 6,
            "memory_mib": 8192,
            "docker_engines": 1,
            "ports": [26233],
            "cache_keys": ["docker-desktop"],
        },
        "safety": {
            "capacity_available": heavy_available,
            "arch_scoped_sync_state": True,
            "arch_scoped_lookups": True,
            "arch_scoped_receipts": True,
            "arch_scoped_caches": True,
            "arch_scoped_ports": True,
            "arch_scoped_volumes": True,
            "dynamic_capacity": True,
        },
        "decision": decision,
        "reasons": [] if decision == "admit" else ["shared Docker capacity is busy"],
    }
    return admission


def test_unsafe_shared_heavy_work_must_wait() -> None:
    validator = _validator(ADMISSION_SCHEMA)
    validator.validate(_admission(decision="wait", heavy_available=False))

    with pytest.raises(ValidationError):
        validator.validate(_admission(decision="admit", heavy_available=False))


def test_identical_inputs_have_only_one_valid_decision() -> None:
    validator = _validator(ADMISSION_SCHEMA)
    available = _admission(decision="admit", heavy_available=True)
    validator.validate(available)
    available["decision"] = "wait"
    available["reasons"] = ["caller tried to delay safe work"]
    with pytest.raises(ValidationError):
        validator.validate(available)

    unavailable = _admission(decision="wait", heavy_available=False)
    validator.validate(unavailable)
    unavailable["decision"] = "admit"
    with pytest.raises(ValidationError):
        validator.validate(unavailable)


def test_admission_rejects_an_unverified_digest_claim() -> None:
    validator = _validator(ADMISSION_SCHEMA)
    admission = _admission(decision="admit", heavy_available=True)
    admission["inputs_digest"] = "a" * 64
    with pytest.raises(ValidationError):
        validator.validate(admission)


@pytest.mark.parametrize(
    "resource_class",
    ["read_only", "repo_write", "network_provider"],
)
def test_host_broker_rejects_repository_local_resource_classes(
    resource_class: str,
) -> None:
    validator = _validator(ADMISSION_SCHEMA)
    admission = _admission(decision="admit", heavy_available=True)
    admission["resource_class"] = resource_class
    with pytest.raises(ValidationError):
        validator.validate(admission)


@pytest.mark.parametrize(
    "unsafe_boundary",
    [
        "arch_scoped_sync_state",
        "arch_scoped_lookups",
        "arch_scoped_receipts",
        "arch_scoped_caches",
        "arch_scoped_ports",
        "arch_scoped_volumes",
        "dynamic_capacity",
    ],
)
def test_dual_local_work_waits_until_every_boundary_is_safe(
    unsafe_boundary: str,
) -> None:
    validator = _validator(ADMISSION_SCHEMA)
    admission = _admission(decision="admit", heavy_available=True)
    admission["architectures"] = ["amd64", "arm64"]
    safety = admission["safety"]
    assert isinstance(safety, dict)
    safety[unsafe_boundary] = False
    with pytest.raises(ValidationError):
        validator.validate(admission)

    admission["decision"] = "wait"
    admission["reasons"] = [f"{unsafe_boundary} is false"]
    validator.validate(admission)


def test_handoff_and_land_require_zero_stale_and_unknown_containers() -> None:
    validator = _validator(STATUS_SCHEMA)
    status = {
        "schema_version": "dotfiles.orchestration-status.v1",
        "generated_at": "2026-08-15T00:47:51Z",
        "active_goal": {
            "issue": "https://github.com/ray-manaloto/dotfiles/issues/766",
            "outcome": "test",
            "coordinator": "test",
            "writer": "test",
            "worktree": "/repo",
            "branch": "test",
            "handoff_sha256": "b" * 64,
        },
        "repository": {
            "id": "ray-manaloto/dotfiles",
            "path": "/repo",
            "git_common_dir": "/repo/.git",
            "head": "1a648f1d6b2846eebc28bed4c0c402e32c380784",
            "protected_status_sha256": "c" * 64,
            "protected_settings_sha256": "d" * 64,
            "skill_roots": 30,
            "untracked_skill_roots": 27,
            "omc_manifest_sha256": "e" * 64,
        },
        "knowledge_base": {
            "canonical_sha": "0c15267e82012f80ba76cdca702e76dc6789f8ac",
            "issue": "https://github.com/ray-manaloto/knowledge-base/issues/301",
            "coordinator": "test",
            "structural_complete": True,
            "state": "incomplete",
            "execution_authorized": False,
            "unauthorized_reasons": ["plan-authority-unset"],
            "provider_issue_302_authorized": False,
        },
        "worktrees": [],
        "branches": [],
        "clones": [],
        "containers": [],
        "completion_gate": {
            "phase": "handoff",
            "stale_container_count": 0,
            "unknown_container_count": 0,
        },
        "decisions": [
            {"question": f"Q{index}", "decision": "test", "status": "accepted"}
            for index in range(1, 14)
        ],
        "research": [
            {"path": "/example/research/a", "sha256": "f" * 64},
            {"path": "/example/research/b", "sha256": "0" * 64},
        ],
        "dependencies": {
            "gh_skill": "test",
            "advise_project_approach": "test",
            "firecrawl": "test",
            "deferred_issues": [],
        },
        "next_safe_commands": [],
        "authority_required": [],
        "successor_issue": "https://github.com/ray-manaloto/dotfiles/issues/769",
    }
    validator.validate(status)

    status["completion_gate"] = {
        "phase": "land",
        "stale_container_count": 1,
        "unknown_container_count": 0,
    }
    with pytest.raises(ValidationError):
        validator.validate(status)


@pytest.mark.parametrize("classification", ["stale", "unknown"])
def test_container_ledger_cannot_hide_blockers_behind_zero_counts(
    classification: str,
) -> None:
    takeover = json.loads(TAKEOVER.read_text(encoding="utf-8"))
    takeover["completion_gate"]["phase"] = "handoff"
    takeover["containers"] = [
        {
            "id": "hostile",
            "name": "duplicate",
            "state": "running",
            "architecture": "amd64",
            "workspace_labels": {},
            "bind_mount_source": "/missing",
            "expected_identity": None,
            "owner_worktree": None,
            "classification": classification,
        }
    ]
    with pytest.raises(ValidationError):
        _validator(STATUS_SCHEMA).validate(takeover)


def test_takeover_rejects_unknown_or_wrongly_typed_authority_fields() -> None:
    validator = _validator(STATUS_SCHEMA)
    takeover = json.loads(TAKEOVER.read_text(encoding="utf-8"))
    takeover["active_goal"]["unexpected"] = True
    with pytest.raises(ValidationError):
        validator.validate(takeover)


def test_takeover_rejects_loose_inventory_and_duplicate_decisions() -> None:
    validator = _validator(STATUS_SCHEMA)

    takeover = json.loads(TAKEOVER.read_text(encoding="utf-8"))
    takeover["worktrees"][0]["unexpected"] = True
    with pytest.raises(ValidationError):
        validator.validate(takeover)

    takeover = json.loads(TAKEOVER.read_text(encoding="utf-8"))
    takeover["branches"][0]["purpose"] = 7
    with pytest.raises(ValidationError):
        validator.validate(takeover)

    takeover = json.loads(TAKEOVER.read_text(encoding="utf-8"))
    takeover["clones"][0].pop("cleanup_precondition")
    with pytest.raises(ValidationError):
        validator.validate(takeover)

    takeover = json.loads(TAKEOVER.read_text(encoding="utf-8"))
    takeover["research"][0]["sha256"] = "short"
    with pytest.raises(ValidationError):
        validator.validate(takeover)

    takeover = json.loads(TAKEOVER.read_text(encoding="utf-8"))
    takeover["dependencies"]["unexpected"] = True
    with pytest.raises(ValidationError):
        validator.validate(takeover)

    takeover = json.loads(TAKEOVER.read_text(encoding="utf-8"))
    takeover["decisions"][1]["question"] = "Q1"
    with pytest.raises(ValidationError):
        validator.validate(takeover)

    takeover = json.loads(TAKEOVER.read_text(encoding="utf-8"))
    takeover["knowledge_base"]["coordinator"] = 7
    with pytest.raises(ValidationError):
        validator.validate(takeover)


def test_orchestration_skill_requires_resource_admission_before_dispatch() -> None:
    skill = SKILL.read_text(encoding="utf-8")
    assert "**Resource admission:** Before parallel execution" in skill
    assert "one coordinator to\neach repository" in skill
    assert "one writer to each Git common directory" in skill
    assert "stale\nor unknown containers as handoff and land blockers" in skill
    assert "Before dispatch, write a\nread-only container census" in skill
    assert "Classify every duplicate" in skill
    assert "Block any known stale" in skill
    assert "block unknown ownership" in skill
    assert "docs/specs/orchestration-takeover.md" in skill


def test_tracked_takeover_records_every_emergency_decision() -> None:
    validator = _validator(STATUS_SCHEMA)
    takeover = json.loads(TAKEOVER.read_text(encoding="utf-8"))
    validator.validate(takeover)

    assert [item["question"] for item in takeover["decisions"]] == [
        f"Q{index}" for index in range(1, 14)
    ]
    assert takeover["completion_gate"] == {
        "phase": "checkpoint",
        "stale_container_count": 0,
        "unknown_container_count": 0,
    }
    assert takeover["knowledge_base"]["execution_authorized"] is False
    assert takeover["successor_issue"].endswith("/769")

    for field in (
        "active_goal",
        "knowledge_base",
        "decisions",
        "research",
        "dependencies",
        "next_safe_commands",
        "authority_required",
        "successor_issue",
    ):
        missing = dict(takeover)
        missing.pop(field)
        with pytest.raises(ValidationError):
            validator.validate(missing)
