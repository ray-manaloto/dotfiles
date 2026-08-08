# Copyright (c) 2026 Raymond Manaloto
"""Main entry point for the dotfiles-setup CLI."""

from __future__ import annotations

import argparse
import json
import logging
import os
import platform
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar

from kb_setup import evals

from dotfiles_setup import image_lock
from dotfiles_setup.ai import AIOrchestrator
from dotfiles_setup.apt_pins import apt_pins_main
from dotfiles_setup.apt_repo import LLVM_DEV, RepoQuery, apt_repo_main
from dotfiles_setup.audit import DevEnvironmentAuditor, ToolManager
from dotfiles_setup.autofix import autofix_apply_main
from dotfiles_setup.bash_budget import bash_budget_main
from dotfiles_setup.bootstrap_packages import gap_report_failures
from dotfiles_setup.classifier_tables import classifier_axes_main
from dotfiles_setup.codex_lane import run_lane_cli
from dotfiles_setup.command_audit import DEFAULT_SESSION_LIMIT, command_audit_main
from dotfiles_setup.config import DotfilesConfig
from dotfiles_setup.container import verify_latest_main
from dotfiles_setup.dag_project import run_project
from dotfiles_setup.dag_tick import (
    DEFAULT_MAX_AGE_SECONDS,
    DEFAULT_MAX_REWORK,
    DEFAULT_STALL_AFTER_SECONDS,
    run_tick,
)
from dotfiles_setup.doc_refs import (
    find_unresolved_refs,
    find_unresolved_skill_refs,
    find_unresolved_task_refs,
)
from dotfiles_setup.docker import DevContainerManager
from dotfiles_setup.doctor import doctor_main
from dotfiles_setup.env_blob_scan import env_blob_scan_main
from dotfiles_setup.eval_cases import cases as eval_cases_for
from dotfiles_setup.gcc_sha import gcc_sha_main
from dotfiles_setup.ghcr import validate_ghcr_prereqs
from dotfiles_setup.ghcr_cleanup import plan_cleanup
from dotfiles_setup.graph_bakeoff import (
    DEFAULT_REPEATS,
    DEFAULT_WORKBENCH,
    GOLD_CORPUS_RELPATH,
    bakeoff_main,
)
from dotfiles_setup.graphify import graphify_main
from dotfiles_setup.hk_builtins_audit import hk_builtins_audit_main
from dotfiles_setup.hook_guard import pretooluse_main
from dotfiles_setup.hook_selfcheck import hook_selfcheck_main
from dotfiles_setup.image import ImageCommand
from dotfiles_setup.image import main as image_main
from dotfiles_setup.image_lock import image_lock_main
from dotfiles_setup.lint import (
    DEFAULT_TIMEOUT_SECONDS,
    TIMEOUT_ENV_VAR,
    resolve_timeout,
    run_guarded,
)
from dotfiles_setup.lock_integrity import main as lock_integrity_main
from dotfiles_setup.lock_integrity import scoped_lock_main
from dotfiles_setup.lock_refresh import collect_system_lock, stage_system_lock_dir
from dotfiles_setup.memory_index import memory_index_main
from dotfiles_setup.p2996_hash import (
    compute_repo_base_hash,
    compute_repo_dev_hash,
    compute_repo_p2996_hash,
)
from dotfiles_setup.p2996_refresh import refresh as refresh_p2996_ref
from dotfiles_setup.parity import run as parity_run
from dotfiles_setup.path_drift import AMBIENT_PATH_ENV, path_drift_main
from dotfiles_setup.pr import automerge_main, land_main, ship_main
from dotfiles_setup.renovate import renovate_status_main
from dotfiles_setup.renovate_dryrun import renovate_dryrun_main
from dotfiles_setup.renovate_validate import renovate_validate_main
from dotfiles_setup.sync import SyncOptions, sync_main
from dotfiles_setup.token_audit import token_audit_main
from dotfiles_setup.verify import main as verify_main
from dotfiles_setup.workflow_hooks import workflow_hooks_main

if TYPE_CHECKING:
    from argparse import _SubParsersAction
    from collections.abc import Callable

    # argparse exposes no public type for what add_subparsers() returns, so a
    # helper that registers subcommands has to name the private one. Aliased
    # here, under TYPE_CHECKING, to keep that single unavoidable reference in
    # one place instead of in every helper signature.
    type _SubParsers = _SubParsersAction[argparse.ArgumentParser]

logger = logging.getLogger(__name__)


class EnvironmentValidator:
    """Validates the current execution environment."""

    SUPPORTED_PLATFORMS: ClassVar[list[str]] = ["linux", "darwin"]

    @classmethod
    def validate(cls) -> None:
        """Check if current environment meets project standards."""
        current_os = platform.system().lower()
        if current_os not in cls.SUPPORTED_PLATFORMS:
            msg = f"Platform {current_os} is not supported"
            raise RuntimeError(msg)


def _add_apt_repo_subcommand(subparsers: _SubParsers) -> None:
    """Register the apt-repo subcommand.

    Args:
        subparsers: The parent subparsers action to attach apt-repo to.
    """
    apt_repo_parser = subparsers.add_parser(
        "apt-repo",
        help="List the packages an apt repository publishes (reads the "
        "Packages index directly, so it needs neither the repo configured "
        "nor libapt). Defaults to apt.llvm.org for #251.",
    )
    apt_repo_parser.add_argument(
        "--llvm-version",
        default="22",
        help="apt.llvm.org major to enumerate, or 'dev' for the unnumbered "
        "development/trunk suite (2026-07-15: 21 stable, 22 qualification, "
        "dev == 23). Takes a version, not a channel label -- the labels "
        "shift every release cycle. (default: %(default)s)",
    )
    apt_repo_parser.add_argument(
        "--dist", default="resolute", help="Ubuntu codename (default: %(default)s)"
    )
    apt_repo_parser.add_argument(
        "--arch", default="amd64", help="Binary architecture (default: %(default)s)"
    )
    apt_repo_parser.add_argument(
        "--repo", help="Override the repository base URL (any apt repo, not just LLVM)"
    )
    apt_repo_parser.add_argument("--suite", help="Override the suite (implies --repo)")
    apt_repo_parser.add_argument(
        "--toml",
        action="store_true",
        help="Emit [bootstrap.packages] lines ready for mise-system.toml",
    )
    apt_repo_parser.add_argument(
        "--pin",
        action="store_true",
        help='With --toml, emit exact versions instead of "latest" (note: '
        "apt.llvm.org rotates its single build daily, so a pin goes stale)",
    )
    apt_repo_parser.add_argument(
        "--exclude-runtime",
        action="store_true",
        help="Drop Section: libs packages (they arrive via Depends:)",
    )


def _add_honesty_subcommands(subparsers: _SubParsers) -> None:
    """Register the gates that keep a claim and its reality in step.

    Grouped because they answer one question — does this artifact still say
    something true? A committed environment dump, a generated doc that has
    drifted from the tool it describes, and a contract token satisfied by a
    stand-in are the same failure wearing three costumes. Extracted into a
    helper for the reason `_add_consistency_subcommands` was: `setup_parser`
    sits at ruff's PLR0915 statement ceiling.

    Args:
        subparsers: The parent subparsers action to attach these to.
    """
    env_blob_parser = subparsers.add_parser(
        "env-blob-scan",
        help="Reject a committed environment dump — a __MISE_DIFF-shaped blob, "
        "any base64 run that decompresses to text naming secret variables, or a "
        "literal credential value. Covers what gitleaks and betterleaks cannot: "
        "measured, both are blind to the compressed form",
    )
    env_blob_parser.add_argument(
        "paths",
        nargs="*",
        help="Repo-relative files to scan (default: every tracked file)",
    )
    hk_audit_parser = subparsers.add_parser(
        "hk-builtins-audit",
        help="Regenerate docs/hk-builtins-audit.md from `hk builtins` + the hk "
        "configs. The hand-written version drifted to claiming 15 builtins were "
        "used that were not wired, one of them a security scanner",
    )
    hk_audit_parser.add_argument(
        "--check",
        action="store_true",
        help="Fail instead of writing when the committed doc is out of date",
    )
    subparsers.add_parser(
        "token-audit",
        help="Contract-token uniqueness: every per_path_tokens entry should "
        "match its target file exactly once, because a token matching twice can "
        "be satisfied by a stand-in (#394). Genuine multiplicity is allowlisted "
        "with a reason in token_audit.py",
    )
    subparsers.add_parser(
        "bash-budget",
        help="Enforce zero-bash-logic: every scripts/*.sh + "
        ".devcontainer/scripts/*.sh must be allowlisted and within its "
        "per-file line budget (new/grown scripts fail — move logic to python/)",
    )
    subparsers.add_parser(
        "renovate-validate",
        help="Validate renovate.json with the native renovate-config-validator, "
        "first asserting via a lookahead canary that it is really using RE2 — "
        "a missing OPTIONAL re2 dep makes it warn, fall back to JS RegExp and "
        "still exit 0, leaving every regex unchecked (#644)",
    )
    subparsers.add_parser(
        "classifier-axes",
        help="Enforce classifier axis enumeration: every registered "
        "classifier's declared axes must equal the set DERIVED from its own "
        "code (its params + every subject field its predicates read). #601 "
        "lost four review rounds to an axis a sibling predicate already "
        "consumed but the author's enumeration omitted",
    )
    subparsers.add_parser(
        "lock-check",
        help="Reject a lockfile that lost platform coverage vs HEAD. A bare "
        "`mise lock` or any `mise install` on macOS re-locks the whole file for "
        "this platform and drops the linux conda entries the amd64 image needs "
        "(#370, jdx/mise#7700) — measured: linux-x64 628 -> 80",
    )
    lock_tools_parser = subparsers.add_parser(
        "lock-tools",
        help="Re-lock ONLY the named tools (scoped `mise lock <tool>`), then "
        "assert coverage held. Refuses with no tool named, because the bare "
        "whole-file form is the destructive one",
    )
    lock_tools_parser.add_argument(
        "tools",
        nargs="*",
        help="Full backend-qualified tool keys as written in the config "
        "(a bare short name exits 0 having silently done nothing)",
    )
    doctor_parser = subparsers.add_parser(
        "doctor",
        help="Project doctor: does the declared setup in doctor.toml match "
        "reality on this host? Covers the seam every in-tree gate is blind to — "
        "MCP env interpolation, MCP scope vs the harness's roots, fnox env mode "
        "(#418). Silent when healthy; always exits 0 unless --strict",
    )
    doctor_parser.add_argument(
        "--live",
        action="store_true",
        help="Also spawn each stdio MCP server and compare its real tool set to "
        "the baseline. Off the SessionStart path: a spawn per server is real "
        "latency for drift that changes rarely",
    )
    doctor_parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit 1 on findings (for a gate). The default exits 0 so the "
        "SessionStart hook can never disrupt a session",
    )
    doctor_parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print a PASS line per clean check instead of staying silent",
    )
    image_lock_parser = subparsers.add_parser(
        "image-lock",
        help="Regenerate .devcontainer/mise-system.lock + mise-runtime.lock "
        "locally, with CI's recipe as a callable (#650): stage the merged "
        "config, install the image's PINNED mise, converge, then collect with "
        "platform coverage verified against HEAD. Routes into the amd64 "
        "devcontainer on a host that cannot write linux conda checksums",
    )
    image_lock_parser.add_argument(
        "--platform",
        action="append",
        default=[],
        dest="platforms",
        help="Platform to lock; repeatable. Defaults to every platform the "
        "committed lock already carries — a linux-x64-only pass drops a "
        "bumped tool's macos-x64 entry",
    )
    image_lock_parser.add_argument(
        "--stage",
        type=Path,
        help="Stage directory to reuse (default: a fresh temp dir, removed "
        "afterwards). Reuse one to resume a rate-limited run",
    )
    image_lock_parser.add_argument(
        "--passes",
        type=int,
        default=image_lock.DEFAULT_PASSES,
        help="Convergence passes; each fills what the previous could not "
        "resolve under GitHub rate limits",
    )
    container = image_lock_parser.add_mutually_exclusive_group()
    container.add_argument(
        "--container",
        dest="container",
        action="store_true",
        default=None,
        help="Always route into the devcontainer (default: only when this "
        "host cannot write a faithful lock)",
    )
    container.add_argument(
        "--no-container",
        dest="container",
        action="store_false",
        help="Never route; fail loudly on a host that cannot do the job",
    )
    drift_parser = subparsers.add_parser(
        "path-drift",
        help="Does THIS shell resolve the tools mise currently pins? A cached "
        "activation keeps the old install dir on PATH after a bump, so gates "
        "run a stale binary while `mise which` reports the new one (#596). "
        "Exits 2 when it cannot see the shell's own PATH — never 'clean'",
    )
    drift_parser.add_argument(
        "--ambient-path",
        help="The PATH to examine, captured before mise rewrote it. Defaults to "
        f"${AMBIENT_PATH_ENV}, then the inherited PATH",
    )
    drift_parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit 1 on drift (for a gate). The default warns and exits 0",
    )
    drift_parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print a line when the comparison is clean instead of staying silent",
    )


def _add_consistency_subcommands(subparsers: _SubParsers) -> None:
    """Register the doc/config consistency gates (#160 T13, #354 tier 0).

    Grouped because they answer one question from two angles — does every
    declaration in this repo's agent config still correspond to something real,
    here and in the sibling repo. Extracted into a helper for the reason
    `_add_apt_repo_subcommand` was: `setup_parser` sits at ruff's PLR0915
    statement ceiling.

    Args:
        subparsers: The parent subparsers action to attach these to.
    """
    subparsers.add_parser(
        "check-doc-refs",
        help="Verify every path, `mise run <task>`, and skill reference in "
        "the agent docs resolves to something real (#160 T13 validation J; "
        "task/skill refs added by #354 PR 1)",
    )
    parity_parser = subparsers.add_parser(
        "parity",
        help="Assert the declared cross-repo shared set (parity.toml) holds "
        "in both dotfiles and knowledge-base, and report every other "
        "divergence as advisory (#354 tier 0)",
    )
    parity_parser.add_argument(
        "--kb-path",
        type=Path,
        default=None,
        help="knowledge-base repo root; defaults to $KB_REPO_PATH, then the "
        "sibling directory beside this repo",
    )
    eval_parser = subparsers.add_parser(
        "eval",
        help="Eval harness, tiers 1+2 (#354): tier 0 asks whether a thing is "
        "DECLARED, tier 1 whether it RESOLVES (lanes, the shared engine, the "
        "graph), tier 2 whether the wired PreToolUse guard DECIDES correctly. "
        "Offline and gated; every gated case must carry a control arm that "
        "fails, or the runner refuses to count it",
    )
    eval_parser.add_argument(
        "--live",
        action="store_true",
        help="also run the fable-orchestrator plugin's doctor.sh, which has no "
        "offline mode and spends one real API call per installed lane CLI",
    )


def _add_docker_subcommands(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    """Register docker subcommands on the given subparsers action.

    Args:
        subparsers: The parent subparsers action to attach docker commands to.
    """
    docker_parser = subparsers.add_parser(
        "docker", help="Manage devcontainer for validation"
    )
    docker_subparsers = docker_parser.add_subparsers(
        dest="docker_command", help="Docker commands"
    )
    docker_subparsers.add_parser("build", help="Build local AMD64 image")
    docker_subparsers.add_parser("up", help="Bring the devcontainer up")
    docker_subparsers.add_parser("test", help="Run tests inside the container")
    docker_subparsers.add_parser("down", help="Bring the devcontainer down")
    docker_subparsers.add_parser(
        "initialize-host",
        help="Stage host-side authorized_keys for the container's R1 sshd login",
    )
    verify_latest_parser = docker_subparsers.add_parser(
        "verify-latest",
        help="Gate: running devcontainer is on the latest branch code + "
        "current base (smoke identity) + smoke green",
    )
    verify_latest_parser.add_argument(
        "--no-smoke",
        action="store_true",
        help="Skip the in-container smoke run (fast container/bind-mount check only)",
    )
    sync_parser = docker_subparsers.add_parser(
        "sync",
        help="Converge the devcontainer onto the latest CI-built image "
        "(digest fast-path, handles up/stopped/absent) and verify",
    )
    sync_parser.add_argument(
        "--tag",
        default="dev",
        help="Registry tag to sync to (default: dev; e.g. pr-169 for "
        "pre-merge validation)",
    )
    sync_parser.add_argument(
        "--force",
        action="store_true",
        help="Rebuild even when the local tag matches the registry digest",
    )
    sync_parser.add_argument(
        "--check",
        action="store_true",
        help="Dry-run: report staleness only (rc 1 if stale), change nothing",
    )
    sync_parser.add_argument(
        "--full",
        action="store_true",
        help="Verify with the whole verify-local chain (R1/R2/R3 + "
        "persistence + secrets) instead of the default smoke gate",
    )
    sync_parser.add_argument(
        "--wait",
        action="store_true",
        help="If a ci.yml run is in flight on the target branch, watch it "
        "to completion before syncing",
    )


def _add_verify_subcommands(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    """Register verify subcommands on the given subparsers action.

    Args:
        subparsers: The parent subparsers action to attach verify commands to.
    """
    verify_parser = subparsers.add_parser("verify", help="Run verification suites")
    verify_sub = verify_parser.add_subparsers(
        dest="verify_command", help="Verify commands"
    )
    run_parser = verify_sub.add_parser("run", help="Run verification suites")
    run_parser.add_argument("--suite", help="Run a specific suite by name")
    run_parser.add_argument(
        "--category",
        action="append",
        dest="categories",
        help="Filter by category (repeatable)",
    )
    run_parser.add_argument(
        "--json", action="store_true", dest="output_json", help="Output JSON"
    )
    list_parser = verify_sub.add_parser("list", help="List all verification suites")
    list_parser.add_argument(
        "--category",
        action="append",
        dest="categories",
        help="Filter by category (repeatable)",
    )


def _add_graphify_subcommands(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    """Register graphify subcommands (the deterministic query read path, #313).

    Args:
        subparsers: The parent subparsers action to attach graphify commands to.
    """
    graphify_parser = subparsers.add_parser(
        "graphify", help="Query the project knowledge graph (host-only, #310)"
    )
    graphify_sub = graphify_parser.add_subparsers(
        dest="graphify_command", help="graphify commands"
    )
    query_parser = graphify_sub.add_parser(
        "query", help="Deterministic source-cited query over graphify-out/graph.json"
    )
    query_parser.add_argument("question", help="The question to ask the graph")
    query_parser.add_argument(
        "--budget", type=int, default=2000, help="Token budget (default: 2000)"
    )
    query_parser.add_argument(
        "--context", type=int, default=None, help="Context depth around each hit"
    )
    query_parser.add_argument(
        "--dfs", action="store_true", help="Traverse depth-first instead of BFS"
    )
    bakeoff_parser = graphify_sub.add_parser(
        "bakeoff",
        help="Run the extraction bake-off (writes OUTSIDE the repo, to the workbench)",
    )
    bakeoff_parser.add_argument(
        "--corpus",
        default=None,
        help=f"Corpus dir (default: the versioned gold fixture, {GOLD_CORPUS_RELPATH})",
    )
    bakeoff_parser.add_argument(
        "--workbench",
        default=str(DEFAULT_WORKBENCH),
        help=f"Where runs and reports land (default: {DEFAULT_WORKBENCH})",
    )
    bakeoff_parser.add_argument(
        "--repeats",
        type=int,
        default=DEFAULT_REPEATS,
        help=f"Runs per arm (default: {DEFAULT_REPEATS}); variance needs >1",
    )
    bakeoff_parser.add_argument(
        "--run-id", default="manual", dest="run_id", help="Names the run subtree"
    )
    bakeoff_parser.add_argument(
        "--no-null",
        action="store_true",
        dest="no_null",
        help="Drop the null arm. Removes the noise floor, so no gap is interpretable",
    )


def _add_image_subcommands(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    """Register image subcommands on the given subparsers action.

    Args:
        subparsers: The parent subparsers action to attach image commands to.
    """
    image_parser = subparsers.add_parser("image", help="Image operations")
    image_sub = image_parser.add_subparsers(dest="image_command", help="Image commands")
    smoke_parser = image_sub.add_parser("smoke", help="Run smoke tests on an image")
    smoke_parser.add_argument(
        "--image-ref", required=True, help="Image reference to test"
    )
    smoke_parser.add_argument("--platform", default="linux/amd64/v2", help="Platform")
    size_parser = image_sub.add_parser("size-report", help="Report image size metrics")
    size_parser.add_argument(
        "--image-ref", required=True, help="Image reference to inspect"
    )
    size_parser.add_argument("--platform", default="linux/amd64/v2", help="Platform")
    benchmark_parser = image_sub.add_parser(
        "benchmark",
        help="Benchmark image smoke/report timings",
    )
    benchmark_parser.add_argument(
        "--image-ref", required=True, help="Image reference to benchmark"
    )
    benchmark_parser.add_argument(
        "--platform", default="linux/amd64/v2", help="Platform"
    )
    benchmark_parser.add_argument(
        "--output-path",
        help="Optional JSON output path for benchmark metrics",
    )
    smoke_script_parser = image_sub.add_parser(
        "smoke-script",
        help="Print a shared smoke core (tier 1: image identity + exact "
        "tool-set; tier 3: sanitizer + reflection compiler substrate) for "
        "scripts/devcontainer-smoke.sh to eval — the same core the CI no-mount "
        "smoke runs, so the two paths cannot diverge (#223)",
    )
    smoke_script_parser.add_argument(
        "--tier",
        type=int,
        required=True,
        choices=[1, 3],
        help="Smoke tier core to emit (1 = identity + tool-set; 3 = sanitizer "
        "+ reflection). Tier 2 stays fully bash — every tier-2 check is "
        "mount/env-dependent with no CI no-mount counterpart to unify",
    )
    compare_parser = image_sub.add_parser(
        "metrics-compare",
        help="Compare two benchmark JSON files",
    )
    compare_parser.add_argument("--baseline", required=True, help="Baseline JSON path")
    compare_parser.add_argument(
        "--candidate",
        required=True,
        help="Candidate JSON path",
    )
    summary_parser = image_sub.add_parser(
        "metrics-summary",
        help="Render a benchmark JSON (+ optional CI run timings) as a "
        "GitHub step-summary markdown report (#17)",
    )
    summary_parser.add_argument(
        "--metrics-path",
        required=True,
        help="Benchmark JSON produced by `image benchmark`",
    )
    summary_parser.add_argument(
        "--run-id",
        help="Upstream CI run id (github.event.workflow_run.id) for build-time "
        "metrics; omit to skip the CI-timing section",
    )
    summary_parser.add_argument(
        "--repo",
        help="owner/name for the gh jobs API (github.repository)",
    )
    summary_parser.add_argument(
        "--summary-path",
        help="File to append the rendered markdown to (e.g. $GITHUB_STEP_SUMMARY); "
        "always also printed to stdout",
    )
    summary_parser.add_argument(
        "--baseline-path",
        help="Prior benchmark JSON to render a trend section against (#231); "
        "a missing/unreadable path omits the trend rather than failing",
    )
    resolve_parser = image_sub.add_parser(
        "resolve-analysis-ref",
        help="Resolve the analyzable image ref for image-analysis.yml (#231): "
        "prints present=/ref= GitHub outputs to stdout, exits 1 on the loud "
        "FAIL (pull_request run whose PR number cannot be resolved)",
    )
    resolve_parser.add_argument(
        "--event",
        required=True,
        help="Upstream CI event (github.event.workflow_run.event): "
        "pull_request / schedule / workflow_dispatch",
    )
    resolve_parser.add_argument(
        "--head-sha",
        required=True,
        help="Upstream CI head sha (github.event.workflow_run.head_sha)",
    )
    resolve_parser.add_argument(
        "--repo",
        required=True,
        help="owner/name for the gh commits/<sha>/pulls lookup (github.repository)",
    )
    resolve_parser.add_argument(
        "--image",
        required=True,
        help="Untagged registry/name image base (CONTAINER_REGISTRY/IMAGE_NAME)",
    )


def _add_pr_subcommands(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    """Register pr subcommands (ship/land — the full PR loop).

    Args:
        subparsers: The parent subparsers action to attach pr commands to.
    """
    pr_parser = subparsers.add_parser(
        "pr",
        help="PR workflow: ship (gates → push → PR → watch) and land "
        "(merge → main CI → local validation)",
    )
    pr_sub = pr_parser.add_subparsers(dest="pr_command", help="PR commands")
    ship_parser = pr_sub.add_parser(
        "ship",
        help="Run the path-aware gate matrix, push, open/update the PR, "
        "watch checks to a verified-green terminal state",
    )
    ship_parser.add_argument(
        "--title", help="PR title (default: gh --fill from the commits)"
    )
    land_parser = pr_sub.add_parser(
        "land",
        help="Verify checks green, squash-merge pinned to the verified head "
        "SHA, watch main CI, then validate locally (sync; full tier when "
        "the devcontainer surface changed)",
    )
    land_parser.add_argument("number", type=int, help="PR number to land")
    land_parser.add_argument(
        "--resume",
        action="store_true",
        help="Replay the post-merge steps (main-CI watch, local validation) "
        "for an already-MERGED PR that failed after its merge",
    )
    # #369: bot-opened PRs never run ship, so nothing ever armed auto-merge on
    # them and land refuses an OPEN PR — the guard denied the only working
    # command and redirected to a task that could not do the job.
    automerge_parser = pr_sub.add_parser(
        "automerge",
        help="Arm GitHub-native auto-merge on a BOT-opened PR and exit "
        "(Renovate / refresh bot); a human PR is refused → use ship",
    )
    automerge_parser.add_argument(
        "number", type=int, help="Bot-opened PR number to arm auto-merge on"
    )


def _add_hook_subcommands(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    """Register the Claude Code hook entrypoints (wired in settings.json).

    Args:
        subparsers: The parent subparsers action to attach hook commands to.
    """
    hook_parser = subparsers.add_parser(
        "hook",
        help="Claude Code hook entrypoints (wired in .claude/settings.json)",
    )
    hook_sub = hook_parser.add_subparsers(dest="hook_command", help="Hook events")
    hook_sub.add_parser(
        "pretooluse",
        help="PreToolUse Bash guard: deny-with-redirect for one-off commands "
        "that have a canonical mise task (mise-tasks-only policy)",
    )
    hook_sub.add_parser(
        "selfcheck",
        help="Exercise the WIRED host-side hooks end-to-end (ship/land gate) — "
        "settings.json wiring, the real wrappers, and `bash -n` on the scripts",
    )


def _add_dag_tick_subcommand(subparsers: _SubParsers) -> None:
    """Register the launchd watchdog tick (#578): census -> classify -> act.

    Args:
        subparsers: The parent subparsers action to attach this to.
    """
    dag_tick_parser = subparsers.add_parser(
        "dag-tick",
        help="launchd watchdog tick: census this repo's background agents, "
        "classify ALIVE/DEAD/WEDGED/DONE, respawn DEAD nodes and stop "
        "lingering DONE ones. WEDGED is classify-and-log only in this "
        "slice — automated stall recovery is #590",
    )
    dag_tick_parser.add_argument(
        "--cwd",
        default=None,
        help="Scope the census to background sessions started under this "
        "path (default: the current working directory)",
    )
    dag_tick_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the planned actions and exit without spawning anything",
    )
    dag_tick_parser.add_argument(
        "--claude-bin",
        default=None,
        help="Path to the claude binary (default: `which claude`, falling "
        "back to ~/.local/bin/claude)",
    )
    dag_tick_parser.add_argument(
        "--stall-after",
        type=float,
        default=DEFAULT_STALL_AFTER_SECONDS,
        help="Seconds a tempo:active state.json may go unmodified before "
        f"classifying WEDGED (default {DEFAULT_STALL_AFTER_SECONDS:.0f}s)",
    )
    dag_tick_parser.add_argument(
        "--max-age",
        type=float,
        default=DEFAULT_MAX_AGE_SECONDS,
        help="Seconds a DEAD node's state.json may age before it is logged "
        "instead of auto-respawned — not crash recovery beyond this bound "
        f"(default {DEFAULT_MAX_AGE_SECONDS:.0f}s = 24h); an unreadable "
        "state.json age is treated as over-age too",
    )
    dag_tick_parser.add_argument(
        "--max-rework",
        type=int,
        default=DEFAULT_MAX_REWORK,
        help="How many revise/reject rounds one unit of work may take before "
        "the node escalates instead of reopening again (#573/#575 R7, "
        f"default {DEFAULT_MAX_REWORK}); an `approve` advances regardless",
    )
    dag_tick_parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print a line per classified node instead of only anomalies",
    )


def _add_dag_project_subcommand(subparsers: _SubParsers) -> None:
    """Register the tracker projection for escalated nodes (#602 phase 2).

    Its own registration function for the same reason `dag-tick` has one — the
    statement budget in :func:`setup_parser`.

    Args:
        subparsers: The parent subparsers action to attach this to.
    """
    dag_project_parser = subparsers.add_parser(
        "dag-project",
        help="project NEEDS_HUMAN background nodes to the tracker: the "
        "dag:needs-human label and one append-only escalation comment per "
        "(node, question). PHASE 2 is --dry-run only — the write path is "
        "#602 phase 3",
    )
    dag_project_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print exactly what would be posted and post nothing. Pass exactly "
        "one of --dry-run or --write: neither (or both) REFUSES rather than "
        "guessing, because --write is outward-facing and must never be what a "
        "bare invocation falls into",
    )
    dag_project_parser.add_argument(
        "--write",
        action="store_true",
        help="Actually post: ensure the dag:needs-human label, then one "
        "append-only comment per (node, question), deduped against the target "
        "issue's existing markers. Mutually exclusive with --dry-run",
    )
    dag_project_parser.add_argument(
        "--repo",
        default=None,
        help="owner/repo to project into (default: the tracker this repo uses)",
    )
    dag_project_parser.add_argument(
        "--jobs-dir",
        default=None,
        help="Where the background nodes live (default: ~/.claude/jobs)",
    )
    dag_project_parser.add_argument(
        "--stall-after",
        type=float,
        default=DEFAULT_STALL_AFTER_SECONDS,
        help="Seconds a tempo:active state.json may go unmodified before the "
        "comment also reports the node as stalled — the same threshold "
        f"`dag-tick` uses (default {DEFAULT_STALL_AFTER_SECONDS:.0f}s)",
    )
    dag_project_parser.add_argument(
        "--projected-at",
        default=None,
        help="Pin the rendered timestamp (ISO-8601). Exists so a gate can "
        "byte-compare this output against a known-good comment without the "
        "clock being the only difference",
    )


def _add_report_parsers(subparsers: _SubParsers) -> None:
    """Register the read-only scan-and-report commands, plus TWO that act.

    Extracted from :func:`setup_parser` to keep it under ruff's statement cap.
    Most of these share a shape (scan something, render markdown, change
    nothing) and group cleanly. (The daily tool-currency report moved to the
    shared `kb-setup currency daily` engine.)

    ⚠️ **Two members do NOT fit that shape, and the name under-describes them.**
    `dag-tick` (#578) can respawn and stop processes; `codex-lane` (#613) is the
    most side-effecting command in this file — it mkdirs, unlinks four
    artifacts, writes two and spawns a **paid** subprocess. Both live here for
    one reason only: the statement budget. Each has its own registration
    function (:func:`_add_dag_tick_subcommand`, :func:`_add_codex_lane_subcommand`)
    so the divergence is at least visible from the call list.

    **The obvious fix was tried and MEASURED to fail — do not retry it.** #578
    respec round 3 named the divergent-change smell and evaluated calling
    `dag-tick` from :func:`setup_parser` directly; that trips ruff's PLR0915
    (51 > 50 statements). The #613 review proposed the softer variant — a
    sibling grouping function called from :func:`setup_parser`, "one added
    statement, not four" — and that is exactly the statement there is no room
    for: adding it reproduced the same PLR0915 failure on the same function.
    Buying the split back therefore costs a real refactor of
    :func:`setup_parser`, not a one-liner, and is out of scope for #613.
    """
    command_audit_parser = subparsers.add_parser(
        "command-audit",
        help="Scan recent Claude Code transcripts for one-off Bash commands "
        "that should be mise tasks (self-learning mise-tasks-only loop)",
    )
    command_audit_parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_SESSION_LIMIT,
        help=f"Most-recent sessions to scan (default {DEFAULT_SESSION_LIMIT})",
    )
    command_audit_parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Write the report here instead of stdout (relative paths resolve "
        "against the repo root). Used by the SessionEnd hook to refresh "
        ".agent/command-audit.md once per session",
    )

    memory_index_parser = subparsers.add_parser(
        "memory-index",
        help="Check the auto-memory index (MEMORY.md) before trimming it: "
        "load-budget, dead links, and facts that live ONLY in an index hook "
        "and would be silently destroyed by shortening it",
    )
    memory_index_parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Write the report here instead of stdout (relative paths resolve "
        "against the repo root)",
    )
    memory_index_parser.add_argument(
        "--refs",
        metavar="NAME",
        default=None,
        help="Instead of auditing, list the memories citing NAME (with or "
        "without .md) — run this before DELETING a memory, so a citation "
        "cannot rot unnoticed",
    )

    renovate_parser = subparsers.add_parser(
        "renovate-status",
        help="Report Mend-hosted Renovate app install + privileges + open "
        "update PRs (read-only; replaces ad-hoc gh/git polling)",
    )
    renovate_parser.add_argument(
        "--json", action="store_true", help="Emit the raw status as JSON"
    )

    dryrun_parser = subparsers.add_parser(
        "renovate-dryrun",
        help="Run Renovate locally and report the updates it would raise "
        "(read-only; opens no PRs)",
    )
    dryrun_parser.add_argument(
        "--json", action="store_true", help="Emit the raw dry-run result as JSON"
    )
    dryrun_parser.add_argument(
        "--check",
        action="store_true",
        help="Exit 1 when any update is pending (gate mode, per sync --check)",
    )

    _add_dag_tick_subcommand(subparsers)
    _add_dag_project_subcommand(subparsers)
    _add_codex_lane_subcommand(subparsers)


def _add_codex_lane_subcommand(subparsers: _SubParsers) -> None:
    """Register the Codex review-lane producer (#613).

    The half #580 left unbuilt: it shipped the reaper, and nothing wrote the
    reaper's inputs, so `reap_codex_lanes` found no run directory for any node
    and was silent.

    Args:
        subparsers: The parent subparsers action to attach this to.
    """
    parser = subparsers.add_parser(
        "codex-lane",
        help="Launch one Codex review lane for a node: write the lane record "
        "and the verdict schema, run `codex exec` with both --output-schema "
        "and -o, and settle the lane so the dag-tick reaper can consume it",
    )
    parser.add_argument(
        "--node",
        required=True,
        help="The background node id that OWNS this lane — the reaper's CAS "
        "refuses a lane whose owner is not the node it is reaping for",
    )
    parser.add_argument(
        "--prompt-file",
        type=Path,
        default=None,
        help="Read the review prompt from this file (default: stdin, so a "
        "long diff can be piped without risking ARG_MAX)",
    )
    parser.add_argument(
        "--cwd",
        type=Path,
        default=None,
        help="Where codex runs — the repo under review, so its own git-repo "
        "check passes (default: the current working directory)",
    )
    parser.add_argument(
        "--rework-count",
        type=int,
        default=None,
        help="Rounds this unit of work has already spent, recorded in the "
        "lane record and bounded by dag-tick's --max-rework (#573). Omit for "
        "the normal path: CARRY FORWARD the previous round's count and CHARGE "
        "a round when that round's verdict was revise/reject (#616). A "
        "relaunch rewrites the very file that holds the count, so defaulting "
        "to 0 would silently reset the budget; never charging would leave it "
        "unspendable. An explicit value is taken as stated, not incremented",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Optional `codex exec --model` override (default: codex's own "
        "configured default)",
    )
    parser.add_argument(
        "--jobs-dir",
        type=Path,
        default=None,
        help="The jobs root to launch under (default: ~/.claude/jobs, the "
        "same tree dag-tick scans)",
    )


def setup_parser() -> argparse.ArgumentParser:
    """Configure the argument parser."""
    parser = argparse.ArgumentParser(description="Reproducible Dotfiles Orchestrator")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # validate command
    subparsers.add_parser(
        "validate", help="Check if environment meets project standards"
    )

    # audit command
    audit_parser = subparsers.add_parser("audit", help="Audit development environment")
    audit_parser.add_argument("--all", action="store_true", help="Run all audit checks")

    # ensure-ssh command
    subparsers.add_parser(
        "ensure-ssh", help="Synchronize SSH authorization and ensure sshd is running"
    )

    # ai-setup command
    subparsers.add_parser("ai-setup", help="Install Claude Code and AI extensions")

    # query-latest command
    query_parser = subparsers.add_parser(
        "query-latest", help="Query latest version of a tool"
    )
    query_parser.add_argument("tool", help="Tool name")

    # sync-versions command
    subparsers.add_parser(
        "sync-versions", help="Sync tool versions from config to pyproject.toml"
    )

    # install command
    subparsers.add_parser("install", help="Execute toolchain installation")

    # lint command — hk check (read-only, ≡ CI) under a hard timeout
    lint_parser = subparsers.add_parser(
        "lint",
        help="Run hk check --all (read-only, ≡ CI) under a hard timeout "
        "(default 600s) so a hung lint self-aborts instead of wedging",
    )
    lint_parser.add_argument(
        "--timeout",
        type=int,
        default=None,
        help=f"Timeout in seconds; overrides ${TIMEOUT_ENV_VAR} "
        f"(default {DEFAULT_TIMEOUT_SECONDS})",
    )

    _add_docker_subcommands(subparsers)
    _add_verify_subcommands(subparsers)
    _add_graphify_subcommands(subparsers)
    _add_image_subcommands(subparsers)
    _add_pr_subcommands(subparsers)

    subparsers.add_parser(
        "p2996-hash",
        help="Print the content-addressed hash of P2996 cache inputs",
    )
    subparsers.add_parser(
        "base-hash",
        help="Print the content-addressed hash of devcontainer-base inputs",
    )
    subparsers.add_parser(
        "dev-hash",
        help="Print the content-addressed hash of the final dev-image inputs "
        "(base + p2996 hashes + whole Dockerfile + dev bake target)",
    )
    lock_stage_parser = subparsers.add_parser(
        "lock-stage",
        help="Stage the image's merged mise config into a throwaway project "
        "dir for pinned-mise `mise lock` (#160 T8); prints the pinned "
        "MISE_VERSION to run it with",
    )
    lock_stage_parser.add_argument(
        "--dir", required=True, help="Staging directory (created if needed)"
    )
    lock_collect_parser = subparsers.add_parser(
        "lock-collect",
        help="Validate + copy the regenerated stage mise.lock back to "
        ".devcontainer/mise-system.lock (#160 T8)",
    )
    lock_collect_parser.add_argument(
        "--dir", required=True, help="Staging directory used by lock-stage"
    )
    gap_parser = subparsers.add_parser(
        "bootstrap-gap-report",
        help="Assert a `mise bootstrap packages status --json` report shows "
        "the declared [bootstrap.packages] set fully installed (#160 T7)",
    )
    gap_parser.add_argument(
        "--status-json",
        required=True,
        help="Path to the captured status --json output",
    )
    subparsers.add_parser(
        "p2996-refresh",
        help="Bump CLANG_P2996_REF in docker-bake.hcl to the latest "
        "bloomberg/clang-p2996 p2996-branch HEAD (writes only on change)",
    )
    _add_consistency_subcommands(subparsers)
    gcc_sha_parser = subparsers.add_parser(
        "gcc-sha",
        help="Recompute GCC_LATEST_DEB_SHA256 from the pinned gcc-latest "
        ".deb and rewrite it on drift (kayari publishes no checksum; the "
        "gcc-sha-repair workflow greens a Renovate gcc bump, #249)",
    )
    gcc_sha_parser.add_argument(
        "--check",
        action="store_true",
        help="Report drift without writing; exit 1 if the pinned sha is "
        "stale (still downloads the .deb to compare)",
    )
    _add_apt_repo_subcommand(subparsers)
    apt_pins_parser = subparsers.add_parser(
        "apt-pins",
        help="Prove every pinned [bootstrap.packages] version still resolves, "
        "by running apt's solver in a throwaway base container (~30s; "
        "replaces a ~2.5h CI base rebuild)",
    )
    apt_pins_parser.add_argument(
        "--json", action="store_true", help="Emit the probe result as JSON"
    )
    _add_honesty_subcommands(subparsers)
    subparsers.add_parser(
        "workflow-hooks",
        help="Enforce ADR-0001: every CI job that commits or pushes must set "
        "HK_SKIP_HOOKS: pre-commit,pre-push at job level, or hk's git hooks "
        "run on the runner and fail",
    )
    ghcr_cleanup_parser = subparsers.add_parser(
        "ghcr-cleanup",
        help="Plan (default) or execute GHCR retention cleanup for the "
        "hash-family cache tags (#160 T12.5); reads `gh api` package-"
        "versions JSON from --versions-json",
    )
    ghcr_cleanup_parser.add_argument(
        "--versions-json",
        required=True,
        help="Path to the `gh api --paginate` package versions JSON array",
    )
    ghcr_cleanup_parser.add_argument(
        "--keep-per-family",
        type=int,
        default=3,
        help="Newest-N window kept per hash-tag family (default 3)",
    )
    ghcr_cleanup_parser.add_argument(
        "--emit-delete-ids",
        action="store_true",
        help="Print only the deletable version ids (one per line) for the "
        "workflow's delete loop; default prints the human plan",
    )
    ghcr_parser = subparsers.add_parser(
        "ghcr-check",
        help="Validate local GHCR publish prerequisites exposed via GitHub CLI",
    )
    ghcr_parser.add_argument(
        "--owner",
        default="ray-manaloto",
        help="GitHub org/user owner",
    )
    ghcr_parser.add_argument("--repo", default="dotfiles", help="Repository name")
    ghcr_parser.add_argument(
        "--package-name",
        default="dotfiles-devcontainer",
        help="GHCR container package name",
    )

    _add_hook_subcommands(subparsers)

    autofix_parser = subparsers.add_parser(
        "autofix-apply",
        help="Apply a run's autofix.ci artifact to the working tree (the "
        "manual fallback when the App cannot push back, #94)",
    )
    autofix_parser.add_argument("run_id", help="Workflow run id with the artifact")

    _add_report_parsers(subparsers)

    # version command
    subparsers.add_parser("version", help="Show the version of the library")

    return parser


def handle_docker(
    args: argparse.Namespace,
    project_root: Path,
    config: DotfilesConfig | None = None,
) -> None:
    """Handle docker subcommands.

    Args:
        args: The parsed arguments.
        project_root: The project root path.
        config: Optional config; defaults to a fresh DotfilesConfig.
    """
    docker_manager = DevContainerManager(project_root, config=config)
    if args.docker_command == "build":
        docker_manager.build()
    elif args.docker_command == "up":
        docker_manager.up()
    elif args.docker_command == "test":
        docker_manager.test()
    elif args.docker_command == "down":
        docker_manager.down()
    elif args.docker_command == "initialize-host":
        docker_manager.initialize_host()
    elif args.docker_command == "verify-latest":
        sys.exit(verify_latest_main(project_root, run_smoke=not args.no_smoke))
    elif args.docker_command == "sync":
        sys.exit(
            sync_main(
                project_root,
                SyncOptions(
                    tag=args.tag,
                    force=args.force,
                    check_only=args.check,
                    full=args.full,
                    wait=args.wait,
                ),
            )
        )


def handle_pr(args: argparse.Namespace, project_root: Path) -> None:
    """Handle pr subcommands.

    Args:
        args: The parsed arguments.
        project_root: The project root path.
    """
    if args.pr_command == "ship":
        sys.exit(ship_main(project_root, title=args.title))
    elif args.pr_command == "land":
        sys.exit(land_main(project_root, args.number, resume=args.resume))
    elif args.pr_command == "automerge":
        sys.exit(automerge_main(project_root, args.number))


def handle_hook(args: argparse.Namespace, project_root: Path) -> None:
    """Dispatch a Claude Code hook subcommand (wired in .claude/settings.json).

    Each hook main returns a process exit code; ``selfcheck`` is the ship/land
    gate. Unknown/absent subcommand is a no-op (never bricks a hook).
    """
    command = getattr(args, "hook_command", None)
    if command == "pretooluse":
        sys.exit(pretooluse_main())
    elif command == "selfcheck":
        sys.exit(hook_selfcheck_main(project_root))


def handle_graphify(args: argparse.Namespace, project_root: Path) -> None:
    """Dispatch a graphify subcommand (the deterministic query read path, #313).

    Args:
        args: The parsed arguments.
        project_root: The project root path (the graph lives under it).
    """
    if getattr(args, "graphify_command", None) == "query":
        sys.exit(
            graphify_main(
                project_root,
                question=args.question,
                budget=args.budget,
                context=args.context,
                dfs=args.dfs,
            )
        )
    if getattr(args, "graphify_command", None) == "bakeoff":
        corpus = (
            Path(args.corpus) if args.corpus else project_root / GOLD_CORPUS_RELPATH
        )
        sys.exit(
            bakeoff_main(
                corpus=corpus,
                workbench=Path(args.workbench),
                repeats=args.repeats,
                run_id=args.run_id,
                no_null=args.no_null,
            )
        )


def handle_audit(config: DotfilesConfig | None = None) -> None:
    """Handle audit command.

    Args:
        config: Optional config; defaults to a fresh DotfilesConfig.
    """
    auditor = DevEnvironmentAuditor(config=config)
    if not auditor.run_all():
        raise SystemExit(1)


def handle_install(project_root: Path) -> None:
    """Handle toolchain commands.

    Args:
        project_root: The project root path.
    """
    manager = ToolManager()
    EnvironmentValidator.validate()
    manager.install()
    manager.sync_versions(project_root)


def handle_sync_versions(project_root: Path) -> None:
    """Handle sync-versions command.

    Args:
        project_root: The project root path.
    """
    ToolManager().sync_versions(project_root)


def handle_verify(args: argparse.Namespace) -> None:
    """Handle verify subcommands.

    Args:
        args: The parsed arguments.
    """
    sys.exit(
        verify_main(
            suite_filter=getattr(args, "suite", None),
            category_filter=getattr(args, "categories", None),
            output_json=getattr(args, "output_json", False),
            list_only=getattr(args, "verify_command", None) == "list",
        )
    )


def handle_image(args: argparse.Namespace) -> None:
    """Handle image subcommands.

    Args:
        args: The parsed arguments.
    """
    if args.image_command == "smoke-script":
        cmd = ImageCommand("", command="smoke-script", tier=args.tier)
        sys.exit(image_main(cmd))
    if args.image_command == "smoke":
        cmd = ImageCommand(args.image_ref, platform=args.platform)
        sys.exit(image_main(cmd))
    if args.image_command == "size-report":
        cmd = ImageCommand(
            args.image_ref,
            platform=args.platform,
            command="size-report",
        )
        sys.exit(image_main(cmd))
    if args.image_command == "benchmark":
        output_path = Path(args.output_path) if args.output_path else None
        cmd = ImageCommand(
            args.image_ref,
            platform=args.platform,
            command="benchmark",
            output_path=output_path,
        )
        sys.exit(image_main(cmd))
    if args.image_command == "metrics-compare":
        cmd = ImageCommand(
            "",
            command="metrics-compare",
            baseline_path=Path(args.baseline),
            candidate_path=Path(args.candidate),
        )
        sys.exit(image_main(cmd))
    if args.image_command == "metrics-summary":
        cmd = ImageCommand(
            "",
            command="metrics-summary",
            metrics_path=Path(args.metrics_path),
            run_id=args.run_id,
            repo=args.repo,
            summary_path=Path(args.summary_path) if args.summary_path else None,
            baseline_path=Path(args.baseline_path) if args.baseline_path else None,
        )
        sys.exit(image_main(cmd))
    if args.image_command == "resolve-analysis-ref":
        cmd = ImageCommand(
            "",
            command="resolve-analysis-ref",
            event=args.event,
            head_sha=args.head_sha,
            repo=args.repo,
            image_base=args.image,
        )
        sys.exit(image_main(cmd))


def handle_lock_stage(args: argparse.Namespace, project_root: Path) -> None:
    """Handle lock-stage: prepare the staging dir, print the pinned version."""
    stage_dir = Path(args.dir)
    stage_dir.mkdir(parents=True, exist_ok=True)
    version = stage_system_lock_dir(project_root, stage_dir)
    sys.stdout.write(version + "\n")


def handle_lock_collect(args: argparse.Namespace, project_root: Path) -> None:
    """Handle lock-collect: validate + copy the stage lock back."""
    collect_system_lock(project_root, Path(args.dir))
    logger.info("mise-system.lock collected from stage")


def handle_bootstrap_gap_report(args: argparse.Namespace, project_root: Path) -> None:
    """Handle the bootstrap-gap-report command (#160 T7).

    Args:
        args: The parsed arguments (carries --status-json).
        project_root: The project root path.
    """
    failures = gap_report_failures(
        Path(args.status_json).read_text(),
        project_root / ".devcontainer" / "mise-system.toml",
    )
    if failures:
        for failure in failures:
            logger.error("gap-report FAIL: %s", failure)
        sys.exit(1)
    logger.info("gap-report OK: declared [bootstrap.packages] set fully installed")


def handle_apt_repo(args: argparse.Namespace) -> int:
    """Handle apt-repo: list what an apt repository publishes.

    `--repo`/`--suite` address any apt repo; without them the query is built
    for apt.llvm.org from `--llvm-version` (#251).
    """
    if args.repo or args.suite:
        if not (args.repo and args.suite):
            logger.error("--repo and --suite must be given together")
            return 2
        query = RepoQuery(repo=args.repo, suite=args.suite, arch=args.arch)
    else:
        version: int | str = (
            LLVM_DEV if args.llvm_version == LLVM_DEV else int(args.llvm_version)
        )
        query = RepoQuery.for_llvm(version, dist=args.dist, arch=args.arch)
    return apt_repo_main(
        query,
        toml=args.toml,
        pin=args.pin,
        exclude_runtime=args.exclude_runtime,
    )


def handle_check_doc_refs(project_root: Path) -> None:
    """Handle check-doc-refs: fail loud on any unresolved doc reference.

    Three kinds, one gate. Paths were the original scope (#160 T13); `mise run
    <task>` and skill names were added by #354 PR 1 because they are
    structurally invisible to the path checker — a span with whitespace or no
    file extension is never a path candidate — while being the two things this
    repo's docs cite most. Each kind names its own kind in the error so a
    failure says which resolver disagreed.
    """
    failures = [
        ("path", find_unresolved_refs(project_root)),
        ("mise task", find_unresolved_task_refs(project_root)),
        ("skill", find_unresolved_skill_refs(project_root)),
    ]
    unresolved = [(kind, ref) for kind, refs in failures for ref in refs]
    if unresolved:
        for kind, ref in unresolved:
            logger.error(
                "%s:%d: unresolved %s ref `%s`", ref.doc, ref.line, kind, ref.ref
            )
        sys.exit(1)
    logger.info("check-doc-refs OK: all doc path, task, and skill references resolve")


def handle_parity(args: argparse.Namespace, project_root: Path) -> None:
    """Handle parity: gate the declared cross-repo set, report the rest.

    Writes the whole report — advisory divergence included — before exiting, so
    a failure says what diverged rather than only that something did
    (`.claude/rules/verify-before-advancing.md`, "a gate must report the status
    it saw").
    """
    rc, report = parity_run(project_root, kb_path=args.kb_path)
    sys.stdout.write(report + "\n")
    sys.exit(rc)


def handle_eval(args: argparse.Namespace, project_root: Path) -> None:
    """Handle eval: run this repo's tier-1 cases through the SHARED runner.

    The runner is ``kb_setup.evals`` — one implementation, both repos, consumed
    as the SHA-pinned ``kb-setup`` dependency. Only the cases are ours.
    """
    rc, report = evals.run(eval_cases_for(project_root), live=args.live)
    sys.stdout.write(report + "\n")
    sys.exit(rc)


def handle_ghcr_cleanup(args: argparse.Namespace) -> None:
    """Handle ghcr-cleanup: print the retention plan (never deletes itself).

    Deletion stays in the workflow as an explicit, separately-gated loop
    over --emit-delete-ids output — this command is read-only by design.
    """
    versions = json.loads(Path(args.versions_json).read_text())
    plan = plan_cleanup(versions, keep_per_family=args.keep_per_family)
    if args.emit_delete_ids:
        for version in plan.delete:
            sys.stdout.write(f"{version['id']}\n")
        return
    logger.info(
        "GHCR cleanup plan: %d deletable, %d kept",
        len(plan.delete),
        len(plan.keep_reasons),
    )
    for version in plan.delete:
        tags = version.get("metadata", {}).get("container", {}).get("tags", [])
        logger.info(
            "DELETE %s %s %s", version.get("id"), version.get("created_at"), tags
        )
    for version_id, reason in plan.keep_reasons.items():
        logger.info("KEEP   %s — %s", version_id, reason)


def handle_ghcr_check(args: argparse.Namespace, project_root: Path) -> None:
    """Handle GHCR prerequisite validation."""
    result = validate_ghcr_prereqs(
        repo_root=project_root,
        owner=args.owner,
        repo=args.repo,
        package_name=args.package_name,
    )
    sys.stdout.write(json.dumps(result, indent=2) + "\n")


def _hash_command_handlers(project_root: Path) -> dict[str, Any]:
    """Dispatch entries for the three content-hash CLI commands.

    Extracted from `_build_command_handlers` so the three near-identical
    stdout-emitting handlers don't push that function over the McCabe
    complexity cap as tiers are added (base → p2996 → dev).
    """

    def _emit(compute: Callable[[Path], str]) -> None:
        sys.stdout.write(compute(project_root) + "\n")

    # Phase D (#120): an on-demand "build this exact upstream SHA" run
    # exports CLANG_P2996_REF (mirroring docker bake's own variable
    # override). The p2996/dev hashes must reflect it so the
    # content-addressed cache tags track the overridden ref and never
    # poison the canonical pinned-ref cache. Empty/unset => the committed
    # pin, byte-identical to the canonical build.
    p2996_ref = os.environ.get("CLANG_P2996_REF") or None

    def _emit_p2996() -> None:
        sys.stdout.write(
            compute_repo_p2996_hash(project_root, clang_p2996_ref=p2996_ref) + "\n"
        )

    def _emit_dev() -> None:
        sys.stdout.write(
            compute_repo_dev_hash(project_root, clang_p2996_ref=p2996_ref) + "\n"
        )

    return {
        "base-hash": lambda: _emit(compute_repo_base_hash),
        "p2996-hash": _emit_p2996,
        "dev-hash": _emit_dev,
    }


def _build_command_handlers(
    args: argparse.Namespace,
    project_root: Path,
    config: DotfilesConfig,
) -> dict[str, Any]:
    """Build a dispatch table of command handlers.

    Args:
        args: The parsed arguments.
        project_root: The project root path.
        config: The resolved DotfilesConfig instance.

    Returns:
        Mapping from command name to a callable handler.
    """

    def _validate() -> None:
        EnvironmentValidator.validate()
        logger.info("Environment is valid.")

    def _ensure_ssh() -> None:
        EnvironmentValidator.validate()
        DevEnvironmentAuditor(config=config).ensure_ssh()

    def _ai_setup() -> None:
        EnvironmentValidator.validate()
        AIOrchestrator().run_all()

    def _version() -> None:
        sys.stdout.write("0.1.0\n")

    def _p2996_refresh() -> None:
        sys.stdout.write(refresh_p2996_ref(project_root).as_json() + "\n")

    def _lint() -> None:
        sys.exit(run_guarded(resolve_timeout(getattr(args, "timeout", None))))

    return {
        "validate": _validate,
        "audit": lambda: handle_audit(config=config),
        "ensure-ssh": _ensure_ssh,
        "ai-setup": _ai_setup,
        "docker": lambda: handle_docker(args, project_root, config=config),
        "pr": lambda: handle_pr(args, project_root),
        "command-audit": lambda: sys.exit(
            command_audit_main(project_root, limit=args.limit, output=args.output)
        ),
        "memory-index": lambda: sys.exit(
            memory_index_main(project_root, output=args.output, refs=args.refs)
        ),
        "renovate-status": lambda: sys.exit(
            renovate_status_main(json_output=args.json)
        ),
        "renovate-dryrun": lambda: sys.exit(
            renovate_dryrun_main(json_output=args.json, check=args.check)
        ),
        "autofix-apply": lambda: sys.exit(
            autofix_apply_main(args.run_id, project_root)
        ),
        "hook": lambda: handle_hook(args, project_root),
        "graphify": lambda: handle_graphify(args, project_root),
        "version": _version,
        "install": lambda: handle_install(project_root),
        "verify": lambda: handle_verify(args),
        "image": lambda: handle_image(args),
        "ghcr-check": lambda: handle_ghcr_check(args, project_root),
        "ghcr-cleanup": lambda: handle_ghcr_cleanup(args),
        "check-doc-refs": lambda: handle_check_doc_refs(project_root),
        "parity": lambda: handle_parity(args, project_root),
        "eval": lambda: handle_eval(args, project_root),
        "gcc-sha": lambda: sys.exit(gcc_sha_main(project_root, check=args.check)),
        "apt-repo": lambda: sys.exit(handle_apt_repo(args)),
        "apt-pins": lambda: sys.exit(
            apt_pins_main(project_root, json_output=args.json)
        ),
        "bash-budget": lambda: sys.exit(bash_budget_main(project_root)),
        "renovate-validate": lambda: sys.exit(renovate_validate_main(project_root)),
        "image-lock": lambda: sys.exit(
            image_lock_main(
                project_root,
                platforms=tuple(args.platforms),
                stage=args.stage,
                container=args.container,
                passes=args.passes,
            )
        ),
        "path-drift": lambda: sys.exit(
            path_drift_main(
                ambient_path=args.ambient_path,
                strict=args.strict,
                verbose=args.verbose,
            )
        ),
        "classifier-axes": lambda: sys.exit(classifier_axes_main(project_root)),
        "dag-tick": lambda: sys.exit(run_tick(args)),
        "dag-project": lambda: sys.exit(run_project(args)),
        "codex-lane": lambda: sys.exit(run_lane_cli(args)),
        "doctor": lambda: sys.exit(
            doctor_main(
                project_root,
                live=args.live,
                strict=args.strict,
                verbose=args.verbose,
            )
        ),
        "lock-check": lambda: sys.exit(lock_integrity_main(project_root)),
        "lock-tools": lambda: sys.exit(scoped_lock_main(project_root, args.tools)),
        "token-audit": lambda: sys.exit(token_audit_main(project_root)),
        "env-blob-scan": lambda: sys.exit(
            env_blob_scan_main(project_root, args.paths or None)
        ),
        "hk-builtins-audit": lambda: sys.exit(
            hk_builtins_audit_main(project_root, check=args.check)
        ),
        "workflow-hooks": lambda: sys.exit(workflow_hooks_main(project_root)),
        "bootstrap-gap-report": lambda: handle_bootstrap_gap_report(args, project_root),
        "lock-stage": lambda: handle_lock_stage(args, project_root),
        "lock-collect": lambda: handle_lock_collect(args, project_root),
        "sync-versions": lambda: handle_sync_versions(project_root),
        "p2996-refresh": _p2996_refresh,
        "lint": _lint,
        **_hash_command_handlers(project_root),
    }


def run_command(
    args: argparse.Namespace,
    project_root: Path,
    config: DotfilesConfig | None = None,
) -> None:
    """Execute the specified command.

    Args:
        args: The parsed arguments.
        project_root: The project root path.
        config: Optional config; defaults to a fresh DotfilesConfig.
    """
    if config is None:
        config = DotfilesConfig()
    handlers = _build_command_handlers(args, project_root, config)
    handler = handlers.get(args.command)
    if handler is not None:
        handler()


def main() -> None:
    """Main entry point for the dotfiles-setup CLI."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
        stream=sys.stderr,
    )
    parser = setup_parser()
    args = parser.parse_args()
    project_root = Path(__file__).parent.parent.parent.parent
    config = DotfilesConfig()

    try:
        run_command(args, project_root, config=config)
    except RuntimeError, SystemExit:
        raise
    except Exception:
        logger.exception("Unexpected command failure")
        sys.exit(1)


if __name__ == "__main__":
    main()
