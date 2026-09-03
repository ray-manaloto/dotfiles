# Copyright (c) 2026 Raymond Manaloto
"""Tests for the rule registry (#918).

Covers the three-way `load_class` partition (scoped / eager / malformed),
C2's real-repo agreement with `instructions_report.scoped_rules_on_disk`
(a synthetic-corpus check, the two swallow-divergence control arms, and a
documented BOM-handling divergence), C2b's real-corpus three-way tripwire
against `kb_setup.md_budget.has_paths_frontmatter` (four divergent
frontmatter shapes) and its enumeration axis (git-aware, so the normal
authoring workflow does not turn it red), C5's heading-anchored
eager-reason extraction (incl. its fence and frontmatter-YAML-comment
hazards, and the never-empty-string interface pin), C6's inject set, C6a's
`body_bytes` (disk-accurate, incl. a CRLF regression), the T3
`KNOWN_UNDETECTED_EAGER_REASONS` debt list, `by_id`'s collision detection,
`by_load_class`, and C1's traversal/path-spelling parity.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "python" / "src"))

from dotfiles_setup import instructions_report as report
from dotfiles_setup import rule_registry as registry

# W3: kept at MODULE level so a knowledge-base API change surfaces as a loud
# ImportError, never a silently-skipped test. A red run of the tests below
# may therefore be KB-side, not dotfiles-side — check `kb_setup`'s pinned SHA
# first (python/pyproject.toml) before assuming this module regressed.
from kb_setup.md_budget import classify, has_paths_frontmatter, tracked_files

REPO_ROOT = Path(__file__).parent.parent
REAL_RULES_DIR = REPO_ROOT / ".claude" / "rules"


def _write_rule(
    rules_dir: Path,
    name: str,
    *,
    paths: list[str] | None,
    eof_frontmatter: bool = False,
) -> None:
    rules_dir.mkdir(parents=True, exist_ok=True)
    if paths is None:
        body = f"# {name}\n\nno frontmatter.\n"
    elif eof_frontmatter:
        globs = "\n".join(f'  - "{g}"' for g in paths)
        body = f"---\npaths:\n{globs}\n---"
    else:
        globs = "\n".join(f'  - "{g}"' for g in paths)
        body = f"---\npaths:\n{globs}\n---\n\n# {name}\n\nscoped rule body.\n"
    (rules_dir / f"{name}.md").write_text(body, encoding="utf-8")


def _git_untracked_or_ignored(root: Path, subdir: str) -> set[str]:
    """T2 helper for the W2 enumeration test.

    Repo-relative paths `git status --porcelain --ignored` reports as
    untracked (`??`) or ignored (`!!`) under `subdir`. Lets the enumeration
    assertion tolerate the normal authoring workflow — a newly written,
    not-yet-staged rule file — instead of reading it as a classifier
    disagreement.
    """
    result = subprocess.run(
        ["git", "-C", str(root), "status", "--porcelain", "--ignored", "--", subdir],
        capture_output=True,
        text=True,
        check=False,
    )
    paths: set[str] = set()
    for line in result.stdout.splitlines():
        if len(line) < 4:
            continue
        code, rel = line[:2], line[3:]
        if code in ("??", "!!"):
            paths.add(rel)
    return paths


# --------------------------------------------------------------------------
# C4 — three-way partition basics
# --------------------------------------------------------------------------


def test_scoped_record_carries_globs(tmp_path: Path) -> None:
    rules_dir = tmp_path / ".claude" / "rules"
    _write_rule(rules_dir, "scoped-a", paths=["hk.pkl", "**/CLAUDE.md"])
    reg = registry.build_registry(rules_dir)
    record = reg.by_id("scoped-a")
    assert record is not None
    assert record.load_class == "scoped"
    assert record.globs == ("hk.pkl", "**/CLAUDE.md")
    assert record.eager_reason is None
    assert record.eager_reason_heading is None
    assert record.malformed_detail is None


def test_no_frontmatter_is_eager_not_malformed(tmp_path: Path) -> None:
    rules_dir = tmp_path / ".claude" / "rules"
    _write_rule(rules_dir, "plain", paths=None)
    reg = registry.build_registry(rules_dir)
    record = reg.by_id("plain")
    assert record is not None
    assert record.load_class == "eager"
    assert record.globs == ()
    assert record.malformed_detail is None


def test_frontmatter_without_paths_key_is_eager(tmp_path: Path) -> None:
    """C4: frontmatter that parses but lacks `paths` is eager, not malformed."""
    rules_dir = tmp_path / ".claude" / "rules"
    rules_dir.mkdir(parents=True)
    (rules_dir / "other-frontmatter.md").write_text(
        "---\ntitle: something\n---\n\nbody\n", encoding="utf-8"
    )
    reg = registry.build_registry(rules_dir)
    record = reg.by_id("other-frontmatter")
    assert record is not None
    assert record.load_class == "eager"
    assert record.malformed_detail is None


def test_paths_not_a_list_is_eager_not_malformed(tmp_path: Path) -> None:
    """C4: `paths:` present but not a list — still eager, never malformed."""
    rules_dir = tmp_path / ".claude" / "rules"
    rules_dir.mkdir(parents=True)
    (rules_dir / "string-paths.md").write_text(
        "---\npaths: not-a-list\n---\n\nbody\n", encoding="utf-8"
    )
    reg = registry.build_registry(rules_dir)
    record = reg.by_id("string-paths")
    assert record is not None
    assert record.load_class == "eager"
    assert record.globs == ()
    assert record.malformed_detail is None


def test_eof_terminated_frontmatter_still_scoped(tmp_path: Path) -> None:
    """C4: matches `instructions_report.py:59`'s tolerated EOF-terminated shape."""
    rules_dir = tmp_path / ".claude" / "rules"
    _write_rule(rules_dir, "eof-rule", paths=["hk.pkl"], eof_frontmatter=True)
    reg = registry.build_registry(rules_dir)
    record = reg.by_id("eof-rule")
    assert record is not None
    assert record.load_class == "scoped"
    assert record.globs == ("hk.pkl",)


def test_paths_null_is_eager_not_malformed(tmp_path: Path) -> None:
    """C3/C4: a fourth divergent shape — `paths:` with a YAML null value.

    A `paths:` key followed by nothing (an empty value) parses to
    `None`, so `isinstance(None, list)` is False and this is EAGER, not
    malformed — the most likely real-world typo of the four W1 shapes,
    since deleting the last glob from a scoped rule leaves exactly this.
    """
    rules_dir = tmp_path / ".claude" / "rules"
    rules_dir.mkdir(parents=True)
    (rules_dir / "null-paths.md").write_text(
        "---\npaths:\n---\n\nbody\n", encoding="utf-8"
    )
    reg = registry.build_registry(rules_dir)
    record = reg.by_id("null-paths")
    assert record is not None
    assert record.load_class == "eager"
    assert record.globs == ()
    assert record.malformed_detail is None


def test_empty_paths_list_is_scoped_but_distinguishable_by_empty_globs(
    tmp_path: Path,
) -> None:
    """C2: `paths: []` stays `scoped`, distinguishable via `globs == ()`.

    Syntactically this IS a scoped rule (isinstance-of-list, matching
    `scoped_rules_on_disk`'s predicate exactly per C1/C4) — but a scoped
    rule with zero globs can never match a written path, almost certainly
    an authoring mistake. It is NOT reclassified to a new `load_class`
    (that would break predicate parity with `scoped_rules_on_disk`, C1's
    core invariant): it is already distinguishable, because `load_class ==
    "scoped" and globs == ()` can ONLY happen for a `paths: []` rule —
    every other reachable path to `globs == ()` has a DIFFERENT
    `load_class` (eager or malformed).
    """
    rules_dir = tmp_path / ".claude" / "rules"
    rules_dir.mkdir(parents=True)
    (rules_dir / "empty-paths.md").write_text(
        "---\npaths: []\n---\n\nbody\n", encoding="utf-8"
    )
    reg = registry.build_registry(rules_dir)
    record = reg.by_id("empty-paths")
    assert record is not None
    assert record.load_class == "scoped"
    assert record.globs == ()
    # The distinguishing check a downstream consumer would use:
    assert record.load_class == "scoped"
    assert not record.globs


def test_non_string_glob_item_is_malformed(tmp_path: Path) -> None:
    """C4: a non-string `paths:` item is `malformed`, not silently accepted.

    A list item that is not a string breaks the `tuple[str, ...]` contract
    (and a dict item makes the record unhashable), so it is recorded as
    `malformed` rather than coerced or silently let through.
    """
    rules_dir = tmp_path / ".claude" / "rules"
    rules_dir.mkdir(parents=True)
    (rules_dir / "bad-glob-item.md").write_text(
        "---\npaths:\n  - 42\n  - a: b\n---\n\nbody\n", encoding="utf-8"
    )
    reg = registry.build_registry(rules_dir)
    record = reg.by_id("bad-glob-item")
    assert record is not None
    assert record.load_class == "malformed"
    assert record.malformed_detail
    assert record.globs == ()


def test_load_class_partition_is_exhaustive_and_exclusive(tmp_path: Path) -> None:
    rules_dir = tmp_path / ".claude" / "rules"
    _write_rule(rules_dir, "scoped-a", paths=["hk.pkl"])
    _write_rule(rules_dir, "eager-a", paths=None)
    (rules_dir / "malformed-a.md").write_text(
        "---\npaths: [unterminated\n---\n\nbody\n", encoding="utf-8"
    )
    reg = registry.build_registry(rules_dir)
    assert len(reg.records) == 3
    classes = {r.load_class for r in reg.records}
    assert classes <= {"scoped", "eager", "malformed"}
    for record in reg.records:
        assert record.load_class in {"scoped", "eager", "malformed"}


# --------------------------------------------------------------------------
# C3 — both swallows must become malformed records, never silently dropped
# --------------------------------------------------------------------------


def test_unparsable_frontmatter_is_malformed_with_detail(tmp_path: Path) -> None:
    rules_dir = tmp_path / ".claude" / "rules"
    rules_dir.mkdir(parents=True)
    (rules_dir / "bad-yaml.md").write_text(
        "---\npaths: [unterminated\n---\n\nbody\n", encoding="utf-8"
    )
    reg = registry.build_registry(rules_dir)
    record = reg.by_id("bad-yaml")
    assert record is not None
    assert record.load_class == "malformed"
    assert record.malformed_detail
    assert record.globs == ()


def test_unreadable_file_is_malformed_with_detail(tmp_path: Path) -> None:
    if os.geteuid() == 0:
        pytest.skip("running as root: file mode has no read-permission effect")
    rules_dir = tmp_path / ".claude" / "rules"
    rules_dir.mkdir(parents=True)
    target = rules_dir / "unreadable.md"
    target.write_text("---\npaths:\n  - hk.pkl\n---\n\nbody\n", encoding="utf-8")
    target.chmod(0o000)
    try:
        reg = registry.build_registry(rules_dir)
    finally:
        target.chmod(0o644)
    record = reg.by_id("unreadable")
    assert record is not None
    assert record.load_class == "malformed"
    assert record.malformed_detail


def test_invalid_utf8_is_malformed_not_a_crash(tmp_path: Path) -> None:
    """B2: undecodable UTF-8 becomes a malformed record, never a crash.

    `UnicodeDecodeError` is a `ValueError`, not an `OSError` — a bare
    `except OSError` around the read would miss it and let one bad byte
    crash the whole registry build, falsifying the module docstring's
    promise that an unreadable/undecodable file becomes a malformed record
    rather than taking down every other record with it. This is INHERITED
    from `scoped_rules_on_disk` (which crashes identically); fixed HERE
    only — that file is READ-only per the spec.
    """
    rules_dir = tmp_path / ".claude" / "rules"
    rules_dir.mkdir(parents=True)
    target = rules_dir / "bad-utf8.md"
    target.write_bytes(b"---\npaths:\n  - hk.pkl\n---\n\n\xff\xfe not valid utf-8\n")
    good = rules_dir / "good.md"
    good.write_text("---\npaths:\n  - hk.pkl\n---\n\nbody\n", encoding="utf-8")

    reg = registry.build_registry(rules_dir)  # must not raise

    bad_record = reg.by_id("bad-utf8")
    assert bad_record is not None
    assert bad_record.load_class == "malformed"
    assert bad_record.malformed_detail
    # The file WAS opened and read; only decoding failed, so the on-disk
    # byte count is still knowable — not the "unreadable" 0.
    assert bad_record.body_bytes == target.stat().st_size

    good_record = reg.by_id("good")
    assert good_record is not None
    assert good_record.load_class == "scoped"


def test_utf8_bom_does_not_hide_a_scoped_rule(tmp_path: Path) -> None:
    r"""C1: a BOM'd file must still be detected as scoped.

    A UTF-8 BOM makes `\A---\n` fail to match under plain `utf-8`
    decoding, silently turning a scoped rule into an indistinguishable
    "eager" record. This registry reads with `utf-8-sig` (BOM-aware) and
    so stays correct; `scoped_rules_on_disk` stays BOM-blind by contrast —
    see `test_scoped_agreement_against_real_repo`'s docstring for why that
    is a deliberate, documented divergence rather than a C1 violation.
    """
    rules_dir = tmp_path / ".claude" / "rules"
    rules_dir.mkdir(parents=True)
    raw = "---\npaths:\n  - hk.pkl\n---\n\nbody\n".encode("utf-8-sig")
    assert raw.startswith(b"\xef\xbb\xbf")
    (rules_dir / "bom-rule.md").write_bytes(raw)

    reg = registry.build_registry(rules_dir)
    record = reg.by_id("bom-rule")
    assert record is not None
    assert record.load_class == "scoped"
    assert record.globs == ("hk.pkl",)


# --------------------------------------------------------------------------
# C2 — the registry-vs-scoped_rules_on_disk agreement is ASSERTED
# --------------------------------------------------------------------------


def test_scoped_agreement_against_real_repo() -> None:
    """C2 first bullet: set-equality against the live function.

    Strictly stronger than pinning a hardcoded filename list — it survives
    a rule being added or scoped without a test edit, and it is what
    closes the class #917 hit: two parsers of the same frontmatter
    silently disagreeing on path spelling.

    C1 note: this registry reads with `utf-8-sig` (BOM-aware, see
    `test_utf8_bom_does_not_hide_a_scoped_rule`) while `scoped_rules_on_disk`
    stays BOM-blind (plain `utf-8`) — a deliberate divergence, this
    registry being the more correct of the two on that one shape. It does
    not break THIS test because the real corpus has no BOM'd file today.
    An agreement oracle like this one structurally cannot catch that class
    of bug at all: both parsers share the byte-identical `_FRONTMATTER_RE`,
    so a case where they are BOTH wrong the same way would still "agree".
    Parity is not correctness — it is a floor, not a ceiling.
    """
    reg = registry.build_registry(REAL_RULES_DIR)
    registry_scoped = {r.path for r in reg.records if r.load_class == "scoped"}
    disk_scoped = set(report.scoped_rules_on_disk(REAL_RULES_DIR))
    assert registry_scoped == disk_scoped


def test_diverges_from_scoped_rules_on_disk_on_unparsable_frontmatter(
    tmp_path: Path,
) -> None:
    """C2 second bullet: the control arm proving the swallow is actually fixed.

    `scoped_rules_on_disk` drops this file via `except yaml.YAMLError:
    continue`; the registry must record it as `malformed` instead. A test
    that only ever shows agreement cannot distinguish a working registry
    from a copy of the old function.
    """
    rules_dir = tmp_path / ".claude" / "rules"
    rules_dir.mkdir(parents=True)
    (rules_dir / "bad-yaml.md").write_text(
        "---\npaths: [unterminated\n---\n\nbody\n", encoding="utf-8"
    )
    disk_scoped = set(report.scoped_rules_on_disk(rules_dir))
    assert ".claude/rules/bad-yaml.md" not in disk_scoped

    reg = registry.build_registry(rules_dir)
    record = reg.by_id("bad-yaml")
    assert record is not None
    assert record.load_class == "malformed"


def test_diverges_from_scoped_rules_on_disk_on_unreadable_file(
    tmp_path: Path,
) -> None:
    """C2 third bullet: the same divergence, second arm — an OSError swallow."""
    if os.geteuid() == 0:
        pytest.skip("running as root: file mode has no read-permission effect")
    rules_dir = tmp_path / ".claude" / "rules"
    rules_dir.mkdir(parents=True)
    target = rules_dir / "unreadable.md"
    target.write_text("---\npaths:\n  - hk.pkl\n---\n\nbody\n", encoding="utf-8")
    target.chmod(0o000)
    try:
        disk_scoped = set(report.scoped_rules_on_disk(rules_dir))
        assert ".claude/rules/unreadable.md" not in disk_scoped

        reg = registry.build_registry(rules_dir)
    finally:
        target.chmod(0o644)
    record = reg.by_id("unreadable")
    assert record is not None
    assert record.load_class == "malformed"


# --------------------------------------------------------------------------
# C2b — the third classifier is a tripwire, never pinned as a contract
# --------------------------------------------------------------------------


def test_three_classifiers_agree_on_the_real_corpus() -> None:
    """A live tripwire, not a frozen contract (C2b).

    If this fails, the corpus moved under us — someone added a rule with
    `paths: "a-string"` or a typo'd frontmatter block — and that is a
    finding to report, not a reason to adjust this test. Encoding the known
    synthetic divergence as expected behaviour here would mean the correct
    upstream fix (reconciling all three) breaks this suite, which is the
    exact trap #917 hit.

    W1: the FOUR shapes where this registry and `has_paths_frontmatter`
    diverge are (a) `paths:` holding a string, (b) `paths:` holding a dict,
    (c) `paths:` holding a YAML null (see
    `test_paths_null_is_eager_not_malformed`), and (d) unparsable YAML
    that merely CONTAINS a `paths:` line — `has_paths_frontmatter` answers
    True for all four (it never parses YAML), while this registry answers
    "eager" for (a)/(b)/(c) and "malformed" for (d). None of those four
    fixtures is exercised HERE, in this real-corpus tripwire test: each one
    IS the bug-as-contract this spec rejects, and each is already proven
    individually elsewhere in this file against `scoped_rules_on_disk` and
    this registry directly (`test_diverges_from_*`,
    `test_paths_null_is_eager_not_malformed`) — so the registry side of
    every divergence is independently proven; only the THIRD classifier's
    agreement/disagreement on these four synthetic shapes is deliberately
    left unexercised here. The reconciliation of all three classifiers is
    tracked by **issue #951**; this test is the tripwire that forces
    someone to open it, not a substitute for it.

    W2: also asserts the ENUMERATION axis, not just the predicate. The real
    `md_size_budget` hk gate does not walk `rglob` — it reaches its corpus
    via `tracked_files()` (`git ls-files`) -> `classify()` ->
    `DEFAULT_EXCLUDED_PREFIXES`, so an untracked rule or one under a
    symlinked subdirectory is invisible to the gate even though it is
    visible to this registry's `rglob` traversal. The assertion below
    tolerates the normal authoring workflow: writing a NEW, not-yet-staged
    `.claude/rules/*.md` file must not turn this test red (control-armed:
    `touch`ing one and reverting proved exactly that failure mode before
    this was fixed) — the real invariant is that `rglob_corpus -
    gate_corpus` is EXACTLY the set `git status` reports as untracked or
    ignored under `.claude/rules/`, not that the two corpora are always
    identical.

    If THIS test fails and the failing files are not accounted for by an
    untracked/ignored file in `git status`, that is a real classifier
    disagreement — the corpus moved under us, or the gate's own
    enumeration diverged from this registry's for a tracked file. That is
    a finding to report, not a reason to adjust this test.
    """
    reg = registry.build_registry(REAL_RULES_DIR)
    registry_scoped = {r.path for r in reg.records if r.load_class == "scoped"}
    disk_scoped = set(report.scoped_rules_on_disk(REAL_RULES_DIR))

    md_budget_scoped = set()
    for path in sorted(REAL_RULES_DIR.rglob("*.md", recurse_symlinks=True)):
        rel = str(path.relative_to(REAL_RULES_DIR.parent.parent))
        raw = path.read_text(encoding="utf-8")
        if has_paths_frontmatter(raw):
            md_budget_scoped.add(rel)

    assert registry_scoped == disk_scoped == md_budget_scoped
    assert registry_scoped == {
        ".claude/rules/ci-local-parity.md",
        ".claude/rules/md-size-budgets.md",
    }
    assert not any(r.load_class == "malformed" for r in reg.records)

    # W2 — the enumeration axis: the gate's own tracked_files -> classify
    # corpus must agree with this registry's rglob corpus for rule files,
    # MODULO whatever git itself reports as untracked or ignored (T2: the
    # normal authoring workflow — writing a new, not-yet-staged rule file —
    # must not turn this test red).
    root = REAL_RULES_DIR.parent.parent
    rglob_corpus = {
        str(p.relative_to(root))
        for p in REAL_RULES_DIR.rglob("*.md", recurse_symlinks=True)
    }
    gate_corpus = {
        f
        for f in tracked_files(root)
        if classify(f) in ("rule_unscoped", "rule_scoped")
    }
    untracked_or_ignored = _git_untracked_or_ignored(root, ".claude/rules")
    assert rglob_corpus - gate_corpus == untracked_or_ignored
    assert gate_corpus <= rglob_corpus


# --------------------------------------------------------------------------
# C5 — heading-anchored eager reason only
# --------------------------------------------------------------------------


def test_eager_reason_extracted_from_qualifying_heading(tmp_path: Path) -> None:
    rules_dir = tmp_path / ".claude" / "rules"
    rules_dir.mkdir(parents=True)
    (rules_dir / "eager-with-reason.md").write_text(
        "# Some Rule\n\n"
        "Some intro text.\n\n"
        "## Why this rule is eager (never `paths:`-scoped)\n\n"
        "Reason body line one.\n"
        "Reason body line two.\n\n"
        "## Applies to\n\n"
        "Everything.\n",
        encoding="utf-8",
    )
    reg = registry.build_registry(rules_dir)
    record = reg.by_id("eager-with-reason")
    assert record is not None
    assert record.load_class == "eager"
    assert record.eager_reason_heading == (
        "## Why this rule is eager (never `paths:`-scoped)"
    )
    assert record.eager_reason == "Reason body line one.\nReason body line two."


def test_why_this_rule_exists_heading_does_not_qualify(tmp_path: Path) -> None:
    """C5/A2: a bare content-reason heading simply doesn't CONTAIN a marker.

    Not an exclusion list — see `_EAGER_HEADING_MARKERS`'s docstring (A2).
    """
    rules_dir = tmp_path / ".claude" / "rules"
    rules_dir.mkdir(parents=True)
    (rules_dir / "content-reason-only.md").write_text(
        "# Some Rule\n\n## Why this rule exists\n\nBecause reasons.\n",
        encoding="utf-8",
    )
    reg = registry.build_registry(rules_dir)
    record = reg.by_id("content-reason-only")
    assert record is not None
    assert record.load_class == "eager"
    assert record.eager_reason is None
    assert record.eager_reason_heading is None


def test_why_this_rule_exists_heading_qualifies_when_it_also_says_eager(
    tmp_path: Path,
) -> None:
    """A2: the match is positive, so a heading asserting BOTH still qualifies."""
    rules_dir = tmp_path / ".claude" / "rules"
    rules_dir.mkdir(parents=True)
    (rules_dir / "both.md").write_text(
        "# Some Rule\n\n"
        "## Why this rule exists (and is eager)\n\n"
        "Because reasons, and also eagerness.\n",
        encoding="utf-8",
    )
    reg = registry.build_registry(rules_dir)
    record = reg.by_id("both")
    assert record is not None
    assert record.eager_reason_heading == "## Why this rule exists (and is eager)"
    assert record.eager_reason == "Because reasons, and also eagerness."


def test_indented_eager_heading_is_still_detected(tmp_path: Path) -> None:
    """A3: CommonMark tolerates up to 3 leading spaces before ATX `#`s."""
    rules_dir = tmp_path / ".claude" / "rules"
    rules_dir.mkdir(parents=True)
    (rules_dir / "indented-heading.md").write_text(
        "# Some Rule\n\n"
        "   ## Why this rule is eager (never `paths:`-scoped)\n\n"
        "Indented but real.\n",
        encoding="utf-8",
    )
    reg = registry.build_registry(rules_dir)
    record = reg.by_id("indented-heading")
    assert record is not None
    assert record.eager_reason_heading == (
        "## Why this rule is eager (never `paths:`-scoped)"
    )
    assert record.eager_reason == "Indented but real."


def test_four_space_indented_heading_is_not_a_heading(tmp_path: Path) -> None:
    """Control arm for A3: 4+ leading spaces is an indented CODE block, not ATX."""
    rules_dir = tmp_path / ".claude" / "rules"
    rules_dir.mkdir(parents=True)
    (rules_dir / "four-space.md").write_text(
        "# Some Rule\n\n"
        "    ## Why this rule is eager (never `paths:`-scoped)\n\n"
        "Should not qualify.\n",
        encoding="utf-8",
    )
    reg = registry.build_registry(rules_dir)
    record = reg.by_id("four-space")
    assert record is not None
    assert record.eager_reason_heading is None
    assert record.eager_reason is None


def test_eager_reason_section_stops_at_same_level_heading(tmp_path: Path) -> None:
    rules_dir = tmp_path / ".claude" / "rules"
    rules_dir.mkdir(parents=True)
    (rules_dir / "sectioned.md").write_text(
        "# Rule\n\n"
        "## Why this rule cannot be `paths:`-scoped\n\n"
        "Body content.\n\n"
        "## Next Section\n\n"
        "Not part of the reason.\n",
        encoding="utf-8",
    )
    reg = registry.build_registry(rules_dir)
    record = reg.by_id("sectioned")
    assert record is not None
    assert record.eager_reason == "Body content."


def test_fenced_heading_lookalike_is_not_treated_as_heading(tmp_path: Path) -> None:
    """C5 fence hazard: a bash comment inside a fence must not truncate the body."""
    rules_dir = tmp_path / ".claude" / "rules"
    rules_dir.mkdir(parents=True)
    (rules_dir / "fenced.md").write_text(
        "# Rule\n\n"
        "## Why this rule is eager (never `paths:`-scoped)\n\n"
        "Before the fence.\n\n"
        "```bash\n"
        "## this looks like a heading but is a bash comment\n"
        "echo hi\n"
        "```\n\n"
        "After the fence.\n",
        encoding="utf-8",
    )
    reg = registry.build_registry(rules_dir)
    record = reg.by_id("fenced")
    assert record is not None
    assert record.eager_reason is not None
    assert "Before the fence." in record.eager_reason
    assert "After the fence." in record.eager_reason
    assert "this looks like a heading" in record.eager_reason


def test_frontmatter_yaml_comment_is_not_mistaken_for_a_heading(
    tmp_path: Path,
) -> None:
    """T1 correction: guards a YAML-comment hazard, not a setext one.

    `_strip_frontmatter` exists because the parser is ATX-only with NO
    setext detection anywhere in this module — it was never at risk of
    reading the closing `---` as a setext H2 underline. The real hazard it
    guards against is a `#`-prefixed YAML COMMENT inside the frontmatter
    block being misread as an ATX heading if the frontmatter were scanned
    along with the body.

    This fixture reaches the EAGER branch (frontmatter parses but has no
    `paths:` list) so `_find_eager_reason` actually runs. Its frontmatter
    contains a `# eager ...` comment line that WOULD register as a
    (wrongly) qualifying heading if `_strip_frontmatter` were replaced
    with a no-op — mutation-proven: this test fails under that mutation,
    where the prior `test_setext_frontmatter_boundary_is_not_a_phantom_heading`
    (a scoped-rule fixture) did not, because a scoped record never calls
    `_find_eager_reason` at all — `eager_reason is None` was true by
    construction for every scoped record, forever, regardless of whether
    stripping worked.
    """
    rules_dir = tmp_path / ".claude" / "rules"
    rules_dir.mkdir(parents=True)
    (rules_dir / "commented-frontmatter.md").write_text(
        "---\n"
        "# eager - a YAML comment that looks like a qualifying heading\n"
        "title: something\n"
        "---\n\n"
        "# Rule\n\n"
        "## Why this rule is eager (never `paths:`-scoped)\n\n"
        "Real reason body.\n",
        encoding="utf-8",
    )
    reg = registry.build_registry(rules_dir)
    record = reg.by_id("commented-frontmatter")
    assert record is not None
    assert record.load_class == "eager"
    assert record.eager_reason_heading == (
        "## Why this rule is eager (never `paths:`-scoped)"
    )
    assert record.eager_reason == "Real reason body."


def test_eager_reason_never_empty_string_when_heading_has_no_body(
    tmp_path: Path,
) -> None:
    """B1: no body before the next heading normalises to `None`, not `""`.

    A qualifying heading immediately followed by a same-level heading (no
    body text between them) must report `eager_reason=None` — the pinned
    interface says the field is never an empty string.
    """
    rules_dir = tmp_path / ".claude" / "rules"
    rules_dir.mkdir(parents=True)
    (rules_dir / "empty-reason.md").write_text(
        "# Rule\n\n"
        "## Why this rule is eager (never `paths:`-scoped)\n\n"
        "## Next Section\n\n"
        "Unrelated content.\n",
        encoding="utf-8",
    )
    reg = registry.build_registry(rules_dir)
    record = reg.by_id("empty-reason")
    assert record is not None
    assert record.eager_reason_heading == (
        "## Why this rule is eager (never `paths:`-scoped)"
    )
    assert record.eager_reason is None


def test_eager_reason_never_empty_string_when_heading_is_last_thing_in_file(
    tmp_path: Path,
) -> None:
    """B1, second arm: a qualifying heading at EOF, nothing after it."""
    rules_dir = tmp_path / ".claude" / "rules"
    rules_dir.mkdir(parents=True)
    (rules_dir / "trailing-heading.md").write_text(
        "# Rule\n\n## Why this rule is eager (never `paths:`-scoped)\n",
        encoding="utf-8",
    )
    reg = registry.build_registry(rules_dir)
    record = reg.by_id("trailing-heading")
    assert record is not None
    assert record.eager_reason_heading is not None
    assert record.eager_reason is None


def test_real_corpus_known_non_qualifying_eager_rules() -> None:
    """C5: known-and-accepted non-detections, PAIRED with the positive arm.

    Rule ids are derived from `KNOWN_UNDETECTED_EAGER_REASONS` (T3) rather
    than a second hardcoded list, so the two constants cannot drift apart.

    A4: a pure negative here survives a gutted extractor (an
    `_find_eager_reason` that always returns `(None, None)` makes every
    known-undetected rule pass trivially). Asserting the QUALIFYING set
    (moved here from the now-removed standalone positive test) in the same
    test closes that gap: gutting the extractor kills this test via the
    positive arm even though the negative arm alone would not notice.
    """
    reg = registry.build_registry(REAL_RULES_DIR)

    qualifying = {r.path for r in reg.records if r.eager_reason_heading is not None}
    assert qualifying == {
        ".claude/rules/clean-git-state.md",
        ".claude/rules/zero-skip-policy.md",
        ".claude/rules/agent-artifact-conventions.md",
    }

    known_paths = {
        entry.rsplit(":", 1)[0] for entry in registry.KNOWN_UNDETECTED_EAGER_REASONS
    }
    assert known_paths == {
        ".claude/rules/ai-cli-invocation.md",
        ".claude/rules/clarify-before-acting.md",
    }
    for path in known_paths:
        record = reg.by_id(Path(path).stem)
        assert record is not None
        assert record.path == path
        assert record.load_class == "eager"
        assert record.eager_reason is None
        assert record.eager_reason_heading is None


def test_known_undetected_eager_reasons_cites_a_real_line() -> None:
    """T3: each pinned `file:line` must cite a REAL line naming eagerness.

    A stale citation (the line moved under an unrelated edit) is itself a
    finding, not something to relax.
    """
    for entry in registry.KNOWN_UNDETECTED_EAGER_REASONS:
        rel_path, lineno = entry.rsplit(":", 1)
        lines = (REPO_ROOT / rel_path).read_text(encoding="utf-8").splitlines()
        cited_line = lines[int(lineno) - 1]
        assert "eager" in cited_line.lower()


# --------------------------------------------------------------------------
# C6 — inject set
# --------------------------------------------------------------------------


def test_inject_true_only_for_seeded_pilot_rules() -> None:
    reg = registry.build_registry(REAL_RULES_DIR)
    injected = {r.path for r in reg.records if r.inject}
    assert injected == {
        ".claude/rules/ci-local-parity.md",
        ".claude/rules/md-size-budgets.md",
    }


def test_inject_false_for_non_seeded_rule(tmp_path: Path) -> None:
    rules_dir = tmp_path / ".claude" / "rules"
    _write_rule(rules_dir, "not-in-inject-set", paths=["hk.pkl"])
    reg = registry.build_registry(rules_dir)
    record = reg.by_id("not-in-inject-set")
    assert record is not None
    assert record.inject is False


# --------------------------------------------------------------------------
# C6a — body_bytes: whole-file bytes, frontmatter included
# --------------------------------------------------------------------------


def test_body_bytes_is_whole_file_including_frontmatter(tmp_path: Path) -> None:
    rules_dir = tmp_path / ".claude" / "rules"
    _write_rule(rules_dir, "scoped-a", paths=["hk.pkl"])
    raw = (rules_dir / "scoped-a.md").read_bytes()
    reg = registry.build_registry(rules_dir)
    record = reg.by_id("scoped-a")
    assert record is not None
    assert record.body_bytes == len(raw)
    # Sanity: the frontmatter block itself must be counted, i.e. this is
    # strictly larger than the body-only text would measure.
    assert record.body_bytes > len(b"scoped rule body.\n")


def test_body_bytes_counts_crlf_bytes_correctly(tmp_path: Path) -> None:
    r"""C5: CRLF line endings must not be undercounted.

    `read_text`'s universal-newline translation collapses `\r\n` to `\n`
    before `len(text.encode())` would ever see it, undercounting a CRLF
    file by one byte per line. `body_bytes` must report the real on-disk
    size (`stat().st_size`), not the post-translation size.
    """
    rules_dir = tmp_path / ".claude" / "rules"
    rules_dir.mkdir(parents=True)
    target = rules_dir / "crlf-rule.md"
    raw = b"---\r\npaths:\r\n  - hk.pkl\r\n---\r\n\r\nbody\r\n"
    target.write_bytes(raw)
    reg = registry.build_registry(rules_dir)
    record = reg.by_id("crlf-rule")
    assert record is not None
    assert record.load_class == "scoped"
    assert record.body_bytes == len(raw)
    # The bug this guards: measuring the DECODED (LF-only) text instead of
    # the disk bytes would report a strictly smaller number here.
    assert record.body_bytes > len(raw.replace(b"\r\n", b"\n"))


def test_body_bytes_is_zero_for_unreadable_file(tmp_path: Path) -> None:
    if os.geteuid() == 0:
        pytest.skip("running as root: file mode has no read-permission effect")
    rules_dir = tmp_path / ".claude" / "rules"
    rules_dir.mkdir(parents=True)
    target = rules_dir / "unreadable.md"
    target.write_text("---\npaths:\n  - hk.pkl\n---\n\nbody\n", encoding="utf-8")
    target.chmod(0o000)
    try:
        reg = registry.build_registry(rules_dir)
    finally:
        target.chmod(0o644)
    record = reg.by_id("unreadable")
    assert record is not None
    assert record.body_bytes == 0


# --------------------------------------------------------------------------
# C1 — traversal and path spelling, mirroring instructions_report's own tests
# --------------------------------------------------------------------------


def test_recurses_into_nested_subdirs(tmp_path: Path) -> None:
    rules_dir = tmp_path / ".claude" / "rules"
    _write_rule(rules_dir, "top-level", paths=["hk.pkl"])
    nested = rules_dir / "shared"
    _write_rule(nested, "nested-rule", paths=["mise.toml"])
    reg = registry.build_registry(rules_dir)
    paths = {r.path for r in reg.records}
    assert ".claude/rules/top-level.md" in paths
    assert ".claude/rules/shared/nested-rule.md" in paths


def test_recurses_into_symlinked_subdirs(tmp_path: Path) -> None:
    """S3 parity: `Path.rglob` defaults `recurse_symlinks=False` on 3.13+."""
    real_target = tmp_path / "elsewhere"
    real_target.mkdir()
    _write_rule(real_target, "shared-rule", paths=["mise.toml"])
    rules_dir = tmp_path / ".claude" / "rules"
    rules_dir.mkdir(parents=True)
    (rules_dir / "shared").symlink_to(real_target, target_is_directory=True)
    reg = registry.build_registry(rules_dir)
    paths = {r.path for r in reg.records}
    assert ".claude/rules/shared/shared-rule.md" in paths


# --------------------------------------------------------------------------
# A1 — a missing/non-directory rules_dir must be LOUD, never a silent empty
# registry indistinguishable from a real corpus with zero rules.
# --------------------------------------------------------------------------


def test_missing_rules_dir_raises_not_a_directory_error(tmp_path: Path) -> None:
    missing = tmp_path / "does" / "not" / "exist"
    with pytest.raises(NotADirectoryError):
        registry.build_registry(missing)


def test_file_path_as_rules_dir_raises_not_a_directory_error(tmp_path: Path) -> None:
    """Control arm for A1: a real directory (below) must NOT raise."""
    not_a_dir = tmp_path / "a-file.md"
    not_a_dir.write_text("not a directory", encoding="utf-8")
    with pytest.raises(NotADirectoryError):
        registry.build_registry(not_a_dir)


def test_a_real_directory_does_not_raise_not_a_directory_error(
    tmp_path: Path,
) -> None:
    """Positive control arm for A1 — a genuine (even empty) dir is fine."""
    rules_dir = tmp_path / ".claude" / "rules"
    rules_dir.mkdir(parents=True)
    reg = registry.build_registry(rules_dir)
    assert reg.records == ()


def test_records_sorted_by_path(tmp_path: Path) -> None:
    rules_dir = tmp_path / ".claude" / "rules"
    _write_rule(rules_dir, "zzz-last", paths=None)
    _write_rule(rules_dir, "aaa-first", paths=None)
    reg = registry.build_registry(rules_dir)
    paths = [r.path for r in reg.records]
    assert paths == sorted(paths)


def test_by_id_raises_on_cross_subdir_collision(tmp_path: Path) -> None:
    """D1: same-stem files in different subdirs must not silently collide.

    `by_id` must not silently answer about whichever one sorts first.
    """
    rules_dir = tmp_path / ".claude" / "rules"
    _write_rule(rules_dir / "team-a", "shared-rule", paths=["hk.pkl"])
    _write_rule(rules_dir / "team-b", "shared-rule", paths=["mise.toml"])
    reg = registry.build_registry(rules_dir)
    with pytest.raises(ValueError, match="ambiguous"):
        reg.by_id("shared-rule")


def test_by_load_class_partitions_records(tmp_path: Path) -> None:
    """D3: `by_load_class` had zero callers and zero tests before this."""
    rules_dir = tmp_path / ".claude" / "rules"
    _write_rule(rules_dir, "scoped-a", paths=["hk.pkl"])
    _write_rule(rules_dir, "eager-a", paths=None)
    (rules_dir / "malformed-a.md").write_text(
        "---\npaths: [unterminated\n---\n\nbody\n", encoding="utf-8"
    )
    reg = registry.build_registry(rules_dir)
    assert {r.rule_id for r in reg.by_load_class("scoped")} == {"scoped-a"}
    assert {r.rule_id for r in reg.by_load_class("eager")} == {"eager-a"}
    assert {r.rule_id for r in reg.by_load_class("malformed")} == {"malformed-a"}


def test_rule_id_matches_declared_rules_stem_spelling() -> None:
    """C6b: same `.stem` spelling as `doc_refs._declared_rules`."""
    reg = registry.build_registry(REAL_RULES_DIR)
    declared = {p.stem for p in REAL_RULES_DIR.glob("*.md")}
    non_nested_ids = {
        r.rule_id
        for r in reg.records
        if r.path.count("/") == 2  # ".claude/rules/<name>.md"
    }
    assert non_nested_ids == declared
